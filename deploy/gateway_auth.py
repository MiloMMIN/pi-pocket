#!/usr/bin/env python3
import http.server
import urllib.parse
import hashlib
import hmac
import time
import os
import json
from http.cookies import SimpleCookie

CONFIG_FILE = "/etc/gateway-auth/config.json"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

def generate_sig(username, exp):
    msg = f"{username}:{exp}".encode("utf-8")
    return hmac.new(CONFIG["secret_key"].encode("utf-8"), msg, hashlib.sha256).hexdigest()

def verify_cookie(raw_cookie_header):
    if not raw_cookie_header:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(raw_cookie_header)
    except Exception:
        return None
    morsel = cookie.get(CONFIG["cookie_name"])
    if not morsel:
        return None
    val = morsel.value
    parts = val.split(":")
    if len(parts) != 3:
        return None
    username, exp_str, sig = parts
    try:
        exp = int(exp_str)
    except ValueError:
        return None
    if exp < time.time():
        return None
    expected_sig = generate_sig(username, exp)
    if not hmac.compare_digest(sig, expected_sig):
        return None
    if username not in CONFIG["users"]:
        return None
    return username

LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Pi Pocket · 安全网关</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #0f141c;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            background: #182232;
            border: 1px solid #2a3b53;
            border-radius: 16px;
            width: 100%;
            max-width: 400px;
            padding: 32px 28px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        }
        .header {
            text-align: center;
            margin-bottom: 28px;
        }
        .logo {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 52px;
            height: 52px;
            border-radius: 12px;
            background: #2563eb;
            color: #ffffff;
            font-size: 26px;
            font-weight: 700;
            margin-bottom: 14px;
            box-shadow: 0 0 15px rgba(37, 99, 235, 0.4);
        }
        h1 {
            font-size: 20px;
            font-weight: 600;
            color: #f8fafc;
            letter-spacing: -0.02em;
        }
        p.subtitle {
            font-size: 13px;
            color: #94a3b8;
            margin-top: 6px;
        }
        .field {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: #cbd5e1;
            margin-bottom: 8px;
        }
        input {
            width: 100%;
            padding: 12px 14px;
            background: #0b1017;
            border: 1px solid #334155;
            border-radius: 10px;
            color: #ffffff;
            font-size: 15px;
            outline: none;
            transition: all 0.2s ease;
        }
        input:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
        }
        button {
            width: 100%;
            padding: 12px;
            background: #2563eb;
            color: #ffffff;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s ease, transform 0.1s ease;
            margin-top: 8px;
        }
        button:hover { background: #1d4ed8; }
        button:active { transform: scale(0.99); }
        .error {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #fca5a5;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
            margin-bottom: 20px;
            text-align: center;
        }
        .footer {
            margin-top: 24px;
            text-align: center;
            font-size: 12px;
            color: #64748b;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="logo">π</div>
            <h1>Pi Pocket 网关认证</h1>
            <p class="subtitle">请输入凭据以访问私有工作台 (支持 Bitwarden)</p>
        </div>
        {ERROR_PLACEHOLDER}
        <form method="POST" action="/__auth/login">
            <input type="hidden" name="redirect" value="{REDIRECT_VALUE}">
            <div class="field">
                <label for="username">账号 / Username</label>
                <input id="username" type="text" name="username" autocomplete="username" required autofocus placeholder="用户名">
            </div>
            <div class="field">
                <label for="password">密码 / Password</label>
                <input id="password" type="password" name="password" autocomplete="current-password" required placeholder="••••••••">
            </div>
            <button type="submit">登 录</button>
        </form>
        <div class="footer">
            受保护的专属私有节点 · youmeansi.com
        </div>
    </div>
</body>
</html>
"""

class GatewayHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_GET()
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/__auth/verify":
            user = verify_cookie(self.headers.get("Cookie"))
            if user:
                self.send_response(200)
                self.send_header("X-Auth-User", user)
                self.end_headers()
            else:
                self.send_response(401)
                self.end_headers()
            return

        if path == "/__auth/login":
            query = urllib.parse.parse_qs(url.query)
            redirect_to = query.get("redirect", ["/"])[0]
            user = verify_cookie(self.headers.get("Cookie"))
            if user:
                self.send_response(302)
                self.send_header("Location", redirect_to)
                self.end_headers()
                return

            self.render_login(redirect_to)
            return

        if path == "/__auth/logout":
            cookie_domain = CONFIG.get("cookie_domain", "")
            domain_part = f"; Domain={cookie_domain}" if cookie_domain else ""
            self.send_response(302)
            self.send_header("Set-Cookie", f"{CONFIG['cookie_name']}=; Path=/{domain_part}; Max-Age=0; HttpOnly; Secure; SameSite=Lax")
            self.send_header("Location", "/__auth/login")
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/__auth/login":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            params = urllib.parse.parse_qs(post_data)

            username = params.get("username", [""])[0].strip()
            password = params.get("password", [""])[0]
            redirect_to = params.get("redirect", ["/"])[0]

            expected_password = CONFIG["users"].get(username)
            if expected_password and hmac.compare_digest(password, expected_password):
                max_age = CONFIG.get("max_age_days", 365) * 86400
                exp = int(time.time()) + max_age
                sig = generate_sig(username, exp)
                cookie_val = f"{username}:{exp}:{sig}"
                cookie_domain = CONFIG.get("cookie_domain", "")
                domain_part = f"; Domain={cookie_domain}" if cookie_domain else ""

                self.send_response(302)
                self.send_header("Set-Cookie", f"{CONFIG['cookie_name']}={cookie_val}; Path=/{domain_part}; Max-Age={max_age}; HttpOnly; Secure; SameSite=Lax")
                self.send_header("Location", redirect_to)
                self.end_headers()
            else:
                self.render_login(redirect_to, error="用户名或密码错误，请重新输入")
            return

        self.send_response(404)
        self.end_headers()

    def render_login(self, redirect_to, error=None):
        error_html = f'<div class="error">{error}</div>' if error else ""
        safe_redirect = urllib.parse.quote(redirect_to, safe="/:?&=#-_")
        html = LOGIN_HTML.replace("{ERROR_PLACEHOLDER}", error_html).replace("{REDIRECT_VALUE}", safe_redirect)
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server_address = ("127.0.0.1", 9099)
    httpd = http.server.ThreadingHTTPServer(server_address, GatewayHandler)
    httpd.serve_forever()
