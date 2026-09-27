/**
 * The eval's shared confinement extension.
 *
 * Both arms load it (design C1). It confines the file tools to the attempt
 * worktree and refuses a `bash` command whose text names a protected root.
 * The screen is lexical: it is a condition and an evidence source, never a
 * boundary. `src/satyrn_evals/confinement.py`'s audit is the backstop.
 *
 * The worktree root and the protected roots come from the environment the
 * harness exports (`SATYRN_CONFINEMENT_ROOT`, `SATYRN_CONFINEMENT_ROOTS`,
 * colon-separated), so no grader filename or content is baked into this file.
 */

import { isAbsolute, relative, resolve } from "node:path";

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const FILE_TOOLS = new Set(["read", "edit", "write"]);

function isRecord(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function splitRoots(raw: string | undefined): string[] {
	if (raw === undefined) return [];
	return raw
		.split(":")
		.map((entry) => entry.trim())
		.filter((entry) => entry.length > 0);
}

/** Whether `path` resolves inside `root`; lexical only, symlinks are not followed. */
export function inside(root: string, path: string): boolean {
	const resolved = resolve(root, path);
	const rel = relative(root, resolved);
	return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

/** The first protected root the command's text names, or null. */
export function namesRoot(roots: readonly string[], command: string): string | null {
	for (const root of roots) {
		if (command.includes(root)) return root;
	}
	return null;
}

export default function confinementExtension(
	pi: ExtensionAPI,
	environment: Readonly<Record<string, string | undefined>> = process.env,
): void {
	const root = resolve(environment["SATYRN_CONFINEMENT_ROOT"] ?? process.cwd());
	const roots = splitRoots(environment["SATYRN_CONFINEMENT_ROOTS"]);
	const record = async (data: Record<string, unknown>): Promise<void> => {
		try {
			await pi.appendEntry("confinement_refused", data);
		} catch {
			// Telemetry is evidence, not permission.
		}
	};
	pi.on("tool_call", async (event) => {
		if (!isRecord(event.input)) return undefined;
		if (FILE_TOOLS.has(event.toolName)) {
			const path = event.input.path;
			if (typeof path !== "string") return undefined;
			if (inside(root, path)) return undefined;
			await record({ toolName: event.toolName, toolCallId: event.toolCallId, path });
			return {
				block: true,
				reason:
					`Path outside the attempt worktree: ${path}. ` +
					`Read and write only inside ${root}.`,
			};
		}
		if (event.toolName === "bash") {
			const command = event.input.command;
			if (typeof command !== "string") return undefined;
			const named = namesRoot(roots, command);
			if (named === null) return undefined;
			await record({ toolName: event.toolName, toolCallId: event.toolCallId, command, root: named });
			return {
				block: true,
				reason: `Command names a protected path (${named}). Work only inside ${root}.`,
			};
		}
		return undefined;
	});
}
