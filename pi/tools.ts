// Pi extension for patchbay-voice: custom coding-assistant tools.
//
// Replaces pi's builtin read/grep/find/ls/write with parameterized,
// injection-safe equivalents. write_file is restricted to the configured save
// path (VOICE_SAVE_PATH, default docs/patchbay/) at the tool layer — not just
// the system prompt.
//
// All exec calls use argv arrays (never shell strings) so metacharacters like
// &&, ;, |, $() are inert — passed as literal argument bytes.
//
// History: originally patchbay-relay voice-demo/pi-extension/tools.ts (12
// injection-safe tools); lost when voice-demo/ was rm-rf'd in the move to
// patchbay-voice, leaving only write_file. Recovered and restored 2026-07-05,
// ported to the pi 0.80.x API (execute() + AgentToolResult + raw JSON schema).

import type {
	AgentToolResult,
	ExtensionAPI,
	ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import * as fs from "fs";
import { readFile } from "node:fs/promises";
import * as path from "path";

// Allowlist for git refs: hashes, branch names, tags, colon for ref:path.
const REF_RE = /^[a-zA-Z0-9_./:@^~-]+$/;

function ok(text: string): AgentToolResult {
	return { content: [{ type: "text", text }] };
}

function safeProjectPath(cwd: string, rel: string): string {
	if (path.isAbsolute(rel)) throw new Error(`Absolute paths not allowed: ${rel}`);
	const resolved = path.resolve(cwd, rel);
	const base = cwd.endsWith(path.sep) ? cwd : cwd + path.sep;
	if (resolved !== cwd && !resolved.startsWith(base)) {
		throw new Error(`Path escapes project directory: ${rel}`);
	}
	return resolved;
}

function safeRef(ref: string): string {
	if (!REF_RE.test(ref)) throw new Error(`Invalid git ref: ${ref}`);
	return ref;
}

function safeTreePath(p: string): string {
	if (path.isAbsolute(p) || p.split("/").includes("..")) {
		throw new Error(`Invalid tree path: ${p}`);
	}
	return p;
}

export default function extension(pi: ExtensionAPI) {
	const savePath = process.env.VOICE_SAVE_PATH || "docs/patchbay";
	const savePathDisplay = savePath.replace(/\/$/, "");

	const exec = (cmd: string, args: string[], cwd: string, signal?: AbortSignal) =>
		pi.exec(cmd, args, { cwd, signal, timeout: 30_000 });

	pi.registerTool({
		name: "read_file",
		label: "Read file",
		description: "Read the contents of a file in the project.",
		parameters: {
			type: "object",
			properties: {
				path: { type: "string", description: "File path relative to project root" },
			},
			required: ["path"],
		} as any,
		async execute(_id: string, params: { path: string }, _signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const p = safeProjectPath(ctx.cwd, params.path);
				const content = await readFile(p, "utf-8");
				return ok(content);
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "grep_search",
		label: "Grep search",
		description: "Search for a pattern in file contents. Pattern is a POSIX extended regex.",
		parameters: {
			type: "object",
			properties: {
				pattern: { type: "string", description: "Search pattern (extended regex)" },
				path: { type: "string", description: "File or directory to search (default: project root)" },
				case_insensitive: { type: "boolean", description: "Case-insensitive match" },
			},
			required: ["pattern"],
		} as any,
		async execute(_id: string, params: { pattern: string; path?: string; case_insensitive?: boolean }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const searchPath = params.path ? safeProjectPath(ctx.cwd, params.path) : ctx.cwd;
				const args = ["-r", "-n", "--include=*"];
				if (params.case_insensitive) args.push("-i");
				args.push("--", params.pattern, searchPath);
				const r = await exec("grep", args, ctx.cwd, signal);
				return ok(r.stdout || "(no matches)");
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "glob_find",
		label: "Glob find",
		description: "Find tracked (and untracked non-ignored) files by glob pattern via git ls-files. Examples: '*.ts', 'src/**/*.py'.",
		parameters: {
			type: "object",
			properties: {
				pattern: { type: "string", description: "Glob pattern, e.g. '*.ts' or 'src/**/*.py'" },
			},
			required: ["pattern"],
		} as any,
		async execute(_id: string, params: { pattern: string }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const r = await exec(
					"git",
					["ls-files", "--cached", "--others", "--exclude-standard", "--", params.pattern],
					ctx.cwd,
					signal,
				);
				return ok(r.stdout || "(no matches)");
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "list_dir",
		label: "List directory",
		description: "List the contents of a directory.",
		parameters: {
			type: "object",
			properties: {
				path: { type: "string", description: "Directory path relative to project root (default: project root)" },
			},
		} as any,
		async execute(_id: string, params: { path?: string }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const dirPath = params.path ? safeProjectPath(ctx.cwd, params.path) : ctx.cwd;
				const r = await exec("ls", ["-la", dirPath], ctx.cwd, signal);
				return ok(r.stdout);
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "tree",
		label: "Directory tree",
		description: "Show recursive directory structure, excluding .git.",
		parameters: {
			type: "object",
			properties: {
				path: { type: "string", description: "Path relative to project root (default: project root)" },
				depth: { type: "integer", minimum: 1, maximum: 10, description: "Max depth (default: 3)" },
			},
		} as any,
		async execute(_id: string, params: { path?: string; depth?: number }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const dirPath = params.path ? safeProjectPath(ctx.cwd, params.path) : ctx.cwd;
				const depth = String(params.depth ?? 3);
				const r = await exec(
					"find",
					[dirPath, "-maxdepth", depth, "-not", "-path", "*/.git/*", "-print"],
					ctx.cwd,
					signal,
				);
				return ok(r.stdout);
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "git_log",
		label: "Git log",
		description: "Show recent commits.",
		parameters: {
			type: "object",
			properties: {
				n: { type: "integer", minimum: 1, maximum: 100, description: "Number of commits (default: 20)" },
				path: { type: "string", description: "Show only commits touching this path" },
				ref: { type: "string", description: "Branch or ref to log (default: HEAD)" },
			},
		} as any,
		async execute(_id: string, params: { n?: number; path?: string; ref?: string }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const args = ["log", "--oneline", `--max-count=${params.n ?? 20}`];
				if (params.ref) args.push(safeRef(params.ref));
				if (params.path) {
					args.push("--");
					args.push(safeProjectPath(ctx.cwd, params.path));
				}
				const r = await exec("git", args, ctx.cwd, signal);
				return ok(r.stdout || "(no commits)");
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "git_show",
		label: "Git show",
		description: "Show the diff and message for a specific commit.",
		parameters: {
			type: "object",
			properties: {
				ref: { type: "string", description: "Commit hash, branch name, or tag" },
			},
			required: ["ref"],
		} as any,
		async execute(_id: string, params: { ref: string }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const r = await exec("git", ["show", "--stat", "-p", safeRef(params.ref)], ctx.cwd, signal);
				return ok(r.code === 0 ? r.stdout : `Error: ${r.stderr}`);
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "git_blame",
		label: "Git blame",
		description: "Show who last modified each line of a file.",
		parameters: {
			type: "object",
			properties: {
				path: { type: "string", description: "File path relative to project root" },
			},
			required: ["path"],
		} as any,
		async execute(_id: string, params: { path: string }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const p = safeProjectPath(ctx.cwd, params.path);
				const r = await exec("git", ["blame", "--", p], ctx.cwd, signal);
				return ok(r.code === 0 ? r.stdout : `Error: ${r.stderr}`);
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "git_diff",
		label: "Git diff",
		description: "Show differences between commits, branches, or working tree.",
		parameters: {
			type: "object",
			properties: {
				from_ref: { type: "string", description: "Base ref (omit for working tree vs index)" },
				to_ref: { type: "string", description: "Target ref (omit for index vs working tree)" },
				path: { type: "string", description: "Limit diff to this path" },
			},
		} as any,
		async execute(_id: string, params: { from_ref?: string; to_ref?: string; path?: string }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const args = ["diff"];
				if (params.from_ref) args.push(safeRef(params.from_ref));
				if (params.to_ref) args.push(safeRef(params.to_ref));
				if (params.path) {
					args.push("--");
					args.push(safeProjectPath(ctx.cwd, params.path));
				}
				const r = await exec("git", args, ctx.cwd, signal);
				return ok(r.stdout || "(no differences)");
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "git_branch",
		label: "Git branches",
		description: "List all local and remote branches, showing which is current.",
		parameters: { type: "object", properties: {} } as any,
		async execute(_id: string, _params: unknown, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const r = await exec("git", ["branch", "-a", "-v"], ctx.cwd, signal);
				return ok(r.stdout || "(no branches)");
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "git_show_file",
		label: "Git show file",
		description: "Read a file from a specific branch or commit without checking it out.",
		parameters: {
			type: "object",
			properties: {
				ref: { type: "string", description: "Branch name, tag, or commit hash (e.g. 'main', 'feature/foo', 'abc123')" },
				path: { type: "string", description: "File path within the repository (relative to repo root)" },
			},
			required: ["ref", "path"],
		} as any,
		async execute(_id: string, params: { ref: string; path: string }, signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				const ref = safeRef(params.ref);
				const filePath = safeTreePath(params.path);
				const r = await exec("git", ["show", `${ref}:${filePath}`], ctx.cwd, signal);
				return ok(r.code === 0 ? r.stdout : `Error: ${r.stderr}`);
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});

	pi.registerTool({
		name: "write_file",
		label: "Write file",
		description:
			`Save text content to a file inside ${savePathDisplay}/ in the current project directory. ` +
			"Use this to persist notes, plans, summaries, or anything the user asks you to record. " +
			`Only paths inside ${savePathDisplay}/ are permitted — all others are rejected at the tool layer.`,
		parameters: {
			type: "object",
			properties: {
				path: { type: "string", description: `File path relative to project root — must be inside ${savePathDisplay}/` },
				content: { type: "string", description: "Content to write" },
			},
			required: ["path", "content"],
		} as any,
		async execute(_id: string, params: { path: string; content: string }, _signal: AbortSignal | undefined, _update: unknown, ctx: ExtensionContext): Promise<AgentToolResult> {
			try {
				if (path.isAbsolute(params.path)) {
					return ok("Error: absolute paths not allowed");
				}
				const docsBase = path.join(ctx.cwd, savePathDisplay);
				const resolved = path.resolve(ctx.cwd, params.path);
				const base = docsBase.endsWith(path.sep) ? docsBase : docsBase + path.sep;
				if (resolved !== docsBase && !resolved.startsWith(base)) {
					return ok(`Error: path must be inside ${savePathDisplay}/ (got ${params.path})`);
				}
				fs.mkdirSync(path.dirname(resolved), { recursive: true });
				fs.writeFileSync(resolved, params.content, "utf-8");
				return ok(`Wrote ${path.relative(ctx.cwd, resolved)}`);
			} catch (e: any) {
				return ok(`Error: ${e.message}`);
			}
		},
	});
}
