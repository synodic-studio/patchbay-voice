import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import * as fs from "fs";
import * as path from "path";

export default function extension(pi: ExtensionAPI) {
	const savePath = process.env.VOICE_SAVE_PATH || "docs/patchbay";
	const savePathDisplay = savePath.replace(/\/$/, "");

	pi.registerTool({
		name: "write_file",
		description:
			`Save text content to a file inside ${savePathDisplay}/ in the current project directory. ` +
			"Use this to persist notes, plans, summaries, or anything the user asks you to record. " +
			"Do not use it to communicate information you could say aloud in your reply.",
		parameters: {
			type: "object",
			properties: {
				filename: {
					type: "string",
					description:
						`Filename relative to ${savePathDisplay}/ — e.g. 'notes.md'. No path traversal.`,
				},
				content: {
					type: "string",
					description: "Full text content to write.",
				},
			},
			required: ["filename", "content"],
		},
		handler: async (params: { filename: string; content: string }) => {
			const { filename, content } = params;

			if (filename.includes("..") || path.isAbsolute(filename)) {
				return { error: "Filename must be relative with no path traversal." };
			}

			const projectDir = pi.getProjectDir();
			const targetDir = path.join(projectDir, savePathDisplay);
			fs.mkdirSync(targetDir, { recursive: true });

			const targetPath = path.join(targetDir, filename);
			fs.writeFileSync(targetPath, content, "utf8");

			return { written: path.relative(projectDir, targetPath) };
		},
	});
}
