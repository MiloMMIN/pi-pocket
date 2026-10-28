# 启动 Pi Pocket 并通过腾讯云首尔服务器映射到 https://piming.youmeansi.com
param(
    [switch]$Background
)

$POCKET_DIR = "D:\Desktop\share\script\pi-pocket"
$FRP_CONFIG = "$POCKET_DIR\frpc_piming.toml"
$PORT = 8797

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Pi Pocket 公网协同服务 (piming.youmeansi.com)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. 确保 frpc 运行中
$frpProc = Get-Process -Name frpc -ErrorAction SilentlyContinue
if (-not $frpProc) {
    Write-Host "[1/3] 正在启动 FRP 穿透客户端连接腾讯云首尔服务器..." -ForegroundColor Yellow
    Start-Process -FilePath "frpc.exe" -ArgumentList "-c `"$FRP_CONFIG`"" -WindowStyle Hidden
    Start-Sleep -Milliseconds 800
    Write-Host "      ✓ FRP 隧道已建立 (本地 :$PORT <-> 首尔 :18787 <-> piming.youmeansi.com:443)" -ForegroundColor Green
} else {
    Write-Host "[1/3] ✓ FRP 隧道已经在运行中" -ForegroundColor Green
}

# 2. 读取 Owner Token
$configPath = "$env:USERPROFILE\.pi-pocket\config.json"
$token = ""
if (Test-Path $configPath) {
    try {
        $json = Get-Content $configPath -Raw | ConvertFrom-Json
        $token = $json.ownerToken
    } catch {}
}

# 3. 打印专属访问地址
Write-Host "[2/3] 双重鉴权公网入口信息：" -ForegroundColor Yellow
Write-Host "      公网主页: https://piming.youmeansi.com" -ForegroundColor Cyan
Write-Host "      第一道门禁 (Nginx Basic Auth): 用户名 ming / 密码 PiMing2026!" -ForegroundColor DarkGray
if ($token) {
    Write-Host "      手机一键直连(带Owner令牌): https://piming.youmeansi.com/?token=$token" -ForegroundColor Green
}
Write-Host "----------------------------------------------------------"
Write-Host "[3/3] 正在启动 Pi Pocket 主服务 (端口 :$PORT)..." -ForegroundColor Yellow

Set-Location $POCKET_DIR
node bin\pi-pocket.js -y --access local --port $PORT
