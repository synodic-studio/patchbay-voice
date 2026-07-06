// Regression tests for the patchbay-voice pi extension (tools.ts).
//
// Why this exists: this extension has been lost/broken THREE times — twice by
// being silently reduced to a write_file-only stub, and once by pi's API
// drifting out from under it (handler -> execute, label became required). A
// green server test suite never caught any of it because the extension is
// TypeScript that pi loads at runtime, not Python.
//
// This suite guards the failure modes we can check without a live pi:
//   1. The full set of 12 tools is registered (catches re-stubbing).
//   2. Every tool uses the current pi API shape — execute() fn, not handler;
//      label/description/parameters present (catches the stub AND anyone who
//      registers a tool the old way).
//   3. Reads, path-traversal rejection, and the write_file save-path boundary
//      actually behave.
//   4. exec is called with argv arrays, so shell metacharacters stay inert.
//
// What it CANNOT catch: if pi itself renames `execute` or changes registerTool,
// this suite stays green because it validates against a fixed mock. That drift
// only shows up in a real pi turn — run one after touching this file (see
// pi/README.md).
//
// Run: node --test pi/tools.test.mts   (Node >= 23.6 strips the TS types)

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import extension from "./tools.ts";

const EXPECTED = [
	"read_file", "grep_search", "glob_find", "list_dir", "tree",
	"git_log", "git_show", "git_blame", "git_diff", "git_branch",
	"git_show_file", "write_file",
];

function makeMockPi() {
	const tools = new Map<string, any>();
	const execCalls: Array<{ cmd: string; args: string[] }> = [];
	const pi = {
		registerTool(def: any) {
			tools.set(def.name, def);
		},
		async exec(cmd: string, args: string[]) {
			execCalls.push({ cmd, args });
			return { stdout: `MOCK ${cmd} ${args.join(" ")}`, stderr: "", code: 0, killed: false };
		},
	};
	return { pi, tools, execCalls };
}

function register() {
	const m = makeMockPi();
	extension(m.pi as any);
	return m;
}

// Call a tool's execute() with the pi 0.80.x signature:
// execute(toolCallId, params, signal, onUpdate, ctx)
function run(def: any, params: any, cwd: string) {
	return def.execute("test-id", params, undefined, undefined, { cwd });
}

test("registers exactly the 12 expected tools", () => {
	const { tools } = register();
	assert.equal(tools.size, 12, `expected 12 tools, got ${tools.size}: ${[...tools.keys()].join(", ")}`);
	for (const name of EXPECTED) {
		assert.ok(tools.has(name), `missing tool: ${name}`);
	}
});

test("every tool matches the current pi API shape (execute fn, not handler)", () => {
	const { tools } = register();
	for (const [name, def] of tools) {
		assert.equal(typeof def.execute, "function", `${name}: execute must be a function`);
		assert.ok(!("handler" in def), `${name}: uses stale 'handler' key — pi wants 'execute'`);
		assert.equal(typeof def.label, "string", `${name}: label required by pi`);
		assert.ok(def.label.length > 0, `${name}: label empty`);
		assert.equal(typeof def.description, "string", `${name}: description required`);
		assert.ok(def.description.length > 0, `${name}: description empty`);
		assert.ok(def.parameters && def.parameters.type === "object", `${name}: parameters must be a JSON-schema object`);
	}
});

test("read_file reads a real file and returns AgentToolResult shape", async () => {
	const dir = mkdtempSync(join(tmpdir(), "pbv-"));
	writeFileSync(join(dir, "note.txt"), "hello from disk");
	const { tools } = register();
	const res = await run(tools.get("read_file"), { path: "note.txt" }, dir);
	assert.deepEqual(res, { content: [{ type: "text", text: "hello from disk" }] });
});

test("read_file rejects path traversal outside the project", async () => {
	const dir = mkdtempSync(join(tmpdir(), "pbv-"));
	const { tools } = register();
	const res = await run(tools.get("read_file"), { path: "../../etc/passwd" }, dir);
	assert.match(res.content[0].text, /^Error:/, "traversal should be rejected");
});

test("write_file writes inside the save path and rejects outside it", async () => {
	const dir = mkdtempSync(join(tmpdir(), "pbv-"));
	const { tools } = register();
	const wf = tools.get("write_file");

	const inside = await run(wf, { path: "docs/patchbay/plan.md", content: "notes" }, dir);
	assert.match(inside.content[0].text, /^Wrote /, "write inside save path should succeed");
	assert.ok(existsSync(join(dir, "docs/patchbay/plan.md")), "file should exist on disk");
	assert.equal(readFileSync(join(dir, "docs/patchbay/plan.md"), "utf-8"), "notes");

	const outside = await run(wf, { path: "src/evil.py", content: "x" }, dir);
	assert.match(outside.content[0].text, /^Error:/, "write outside save path must be rejected");
	assert.ok(!existsSync(join(dir, "src/evil.py")), "rejected write must not touch disk");
});

test("exec tools pass args as an argv array so shell metacharacters are inert", async () => {
	const dir = mkdtempSync(join(tmpdir(), "pbv-"));
	const { tools, execCalls } = register();
	const evil = "foo; rm -rf / && echo pwned";
	await run(tools.get("grep_search"), { pattern: evil }, dir);
	assert.equal(execCalls.length, 1, "grep_search should make exactly one exec call");
	assert.equal(execCalls[0].cmd, "grep");
	assert.ok(execCalls[0].args.includes(evil), "the raw pattern must be a single argv element, never spliced into a shell string");
});
