#!/usr/bin/env node
import { SessionManager } from "@earendil-works/pi-coding-agent";

const action = process.argv[2] || "list";
const cwd = process.cwd();

if (action === "list") {
    SessionManager.list(cwd).then((items) => {
        if (!items || !items.length) {
            console.log("\n当前目录暂无 Pi 会话。直接输入 pi 开启新会话。\n");
            return;
        }
        console.log("\n==================== 当前项目的历史会话 (按更新时间排序) ====================");
        items.slice(0, 10).forEach((s, i) => {
            const isLatest = i === 0;
            const marker = isLatest ? "  <-- [默认继续/手机同步]" : "";
            const time = new Date(s.modified).toLocaleString();
            const title = (s.name || s.firstMessage.split("\n")[0] || "未命名会话").slice(0, 45);
            console.log(`  [${i + 1}] ID: ${s.id.slice(0, 8)} | ${time} | ${title}${marker}`);
        });
        console.log("=============================================================================");
        console.log("使用方式:");
        console.log("  pic              继续最新会话 (即标有 [默认继续] 的那场)");
        console.log("  pic -r           打开交互式 TUI 菜单，用键盘方向键选择");
        console.log("  pic <ID前缀>     直接恢复指定 ID 的会话 (例如: pic " + items[0].id.slice(0, 8) + ")");
        console.log("");
    });
}
