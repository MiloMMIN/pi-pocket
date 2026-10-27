import {
    type App,
    cleanUp,
    home,
    lastText,
    owner,
    root,
    say,
    scriptedModel,
    until,
    work,
} from "./helpers.ts";
import { PocketApp } from "../src/server/app.ts";
import type { FauxResponseStep } from "@earendil-works/pi-ai";
import { fauxAssistantMessage, fauxText } from "@earendil-works/pi-ai/providers/faux";
import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { SessionManager } from "@earendil-works/pi-coding-agent";

let app: App;
const sessionsDir = join(process.env.PI_CODING_AGENT_DIR!, "sessions");

const route: FauxResponseStep = (request) => {
    return fauxAssistantMessage([fauxText(`echo: ${lastText(request as never).text}`)]);
};

before(async () => {
    const faux = scriptedModel(route);
    app = await PocketApp.open({
        dataDir: join(root, "pi-sync-data"),
        defaultCwd: work,
        supervised: false,
        log: () => {},
        configureModels: (models) => models.registerNativeProvider(faux.provider),
        home,
    });
    app.config.lastModel = { provider: "faux", modelId: "faux-1", thinkingLevel: "off" };
});

after(async () => {
    await app?.close();
    cleanUp();
});

function safeFolderName(cwd: string): string {
    return `--${cwd.replace(/^[\/\\]/, "").replace(/[:\\\/]/g, "-")}--`;
}

function messageText(m: unknown): string {
    const msg = m as { content?: unknown };
    if (typeof msg.content === "string") return msg.content;
    if (Array.isArray(msg.content)) {
        return msg.content.map((p: { text?: string }) => p?.text ?? "").join("");
    }
    return "";
}

test("syncBack appends new messages from Pi Pocket to the terminal Pi session file", async () => {
    // 1. Create a Pi CLI session file as Pi does
    const folder = join(sessionsDir, safeFolderName(work));
    mkdirSync(folder, { recursive: true });
    const sessionFile = join(folder, "test-sync-session.jsonl");
    const initialManager = SessionManager.create(work);
    initialManager.appendModelChange("faux", "faux-1");
    initialManager.appendThinkingLevelChange("off");
    initialManager.appendMessage({
        role: "user",
        content: [{ type: "text", text: "Task started on PC terminal" }],
        timestamp: Date.now(),
    });
    initialManager.appendMessage(
        fauxAssistantMessage([fauxText("Working on it from PC")]),
    );
    initialManager.appendModelChange("faux", "faux-2");
    writeFileSync(
        sessionFile,
        [initialManager.getHeader(), ...initialManager.getEntries()]
            .map((entry) => JSON.stringify(entry))
            .join("\n") + "\n",
    );

    // 2. Continue this session in Pi Pocket
    const { id } = await app.commands.continuePiSession(owner(app), sessionFile);
    assert.ok(id, "Session continued in Pi Pocket");

    // 3. User sends a message in Pi Pocket on mobile phone
    await say(app, id, "Follow-up instruction from mobile phone");

    // Wait until run.ended has fired and syncBack completed
    await until(async () => {
        const opened = SessionManager.open(sessionFile);
        return opened.getEntries().length >= 6;
    }, "synced back to session file");

    // 4. Verify that the terminal Pi session file now contains the mobile turn!
    const updatedManager = SessionManager.open(sessionFile);
    const entries = updatedManager.getEntries();
    assert.ok(entries.length >= 6, `Expected at least 6 entries, got ${entries.length}`);
    const projected = updatedManager.buildSessionContext();
    const texts = projected.messages.map(messageText);

    assert.ok(
        texts.some((t) => t.includes("Task started on PC terminal")),
        "PC terminal prompt kept",
    );
    assert.ok(
        texts.some((t) => t.includes("Follow-up instruction from mobile phone")),
        "Mobile prompt synced back",
    );
    assert.ok(
        texts.some((t) => t.includes("echo: Follow-up instruction from mobile phone")),
        "Mobile answer synced back",
    );

    // 5. Test manual sync API (sync again is a no-op, 0 messages)
    const syncResult = await app.piSessions.sync(owner(app), id as unknown as number);
    assert.equal(syncResult.count, 0, "No new messages to sync (idempotent)");

    // 6. Test a second mobile turn
    await say(app, id, "Second instruction from mobile phone");
    await until(async () => {
        const opened = SessionManager.open(sessionFile);
        return opened.getEntries().length >= 9;
    }, "second turn synced back");

    const multiTurnManager = SessionManager.open(sessionFile);
    assert.equal(multiTurnManager.getEntries().length, 9);
    const multiProjected = multiTurnManager.buildSessionContext();
    const multiTexts = multiProjected.messages.map(messageText);
    assert.ok(multiTexts.some((t) => t.includes("Second instruction from mobile phone")));
    assert.ok(multiTexts.some((t) => t.includes("echo: Second instruction from mobile phone")));
});
