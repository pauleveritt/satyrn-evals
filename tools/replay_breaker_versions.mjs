// Cycle 2: does the SHIPPING breaker decide differently on the recorded prefix?
//
// A whole-run replay would be invalid: the breaker changes which calls exist,
// so after the first differing decision the recorded sequence is no longer a
// sequence that breaker would have seen. This therefore replays in lockstep
// and STOPS each cell at the first divergence, reporting only decisions both
// breakers actually faced.
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { createLoopBreaker } from "/Users/pauleveritt/projects/pauleveritt/satyrn-engine/packages/engine/engine.ts";

const SHA256 = /^[0-9a-f]{64}$/;
const isRecord = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
function* walk(dir) {
	let es; try { es = readdirSync(dir, { withFileTypes: true }); } catch { return; }
	for (const e of es) {
		const p = join(dir, e.name);
		if (e.isDirectory()) yield* walk(p);
		else if (e.name === "transcript.txt" && p.includes("engine")) yield p;
	}
}

let cells = 0, recorded = 0, agreedRefusals = 0, cellsDiverged = 0;
let shipAdmits = 0, shipRefuses = 0, prefixDecisions = 0, cellsWithRefusals = 0;
for (const file of walk(join(homedir(), "satyrn-smokes"))) {
	cells += 1;
	const breaker = createLoopBreaker();
	const lines = readFileSync(file, "utf8").split("\n");
	// map each tool call to whether the OLD breaker refused it: a refused call
	// is followed by a loop_broken entry and no tool_execution_end for its id.
	// Ground truth for "the recorded breaker refused this call": its
	// tool_execution_end carries the refusal text as the tool result. A refused
	// call is still ended -- pi returns the block reason to the model.
	const refusedIds = new Set();
	for (const line of lines) {
		if (!line.trim()) continue;
		let e; try { e = JSON.parse(line); } catch { continue; }
		if (e.type !== "tool_execution_end") continue;
		const texts = ((e.result ?? {}).content ?? [])
			.map((c) => (c && typeof c.text === "string" ? c.text : ""))
			.join(" ");
		if (texts.includes("already appeared")) refusedIds.add(e.toolCallId);
	}
	let pendingStart = null, diverged = false, cellRefusals = 0;
	for (const line of lines) {
		if (!line.trim()) continue;
		let e; try { e = JSON.parse(line); } catch { continue; }
		if (e.type === "tool_execution_start") {
			pendingStart = e;
			if (diverged) continue;
			let d; try { d = breaker.inspect({ toolName: e.toolName, input: e.args }); } catch { d = undefined; }
			const oldRefused = refusedIds.has(e.toolCallId);
			const newRefused = Boolean(d?.block);
			prefixDecisions += 1;
			if (oldRefused) { recorded += 1; cellRefusals += 1; }
			if (oldRefused === newRefused) { if (oldRefused) agreedRefusals += 1; }
			else {
				diverged = true; cellsDiverged += 1;
				if (oldRefused && !newRefused) shipAdmits += 1; else shipRefuses += 1;
			}
		} else if (e.type === "tool_execution_end" && e.toolName === "edit") {
			const details = (e.result ?? {}).details;
			if (isRecord(details) && details.satyrn === true && details.ok === true && isRecord(details.result)) {
				const { path, sha256 } = details.result;
				if (typeof path === "string" && typeof sha256 === "string" && SHA256.test(sha256)) {
					breaker.noteChange(path, sha256);
				}
			}
		}
	}
	if (cellRefusals) cellsWithRefusals += 1;
}
console.log(`cells scanned:                              ${cells}`);
console.log(`cells whose transcript records a refusal:   ${cellsWithRefusals}`);
console.log(`decisions compared before divergence:       ${prefixDecisions}`);
console.log(`recorded refusals inside those prefixes:    ${recorded}`);
console.log(`  the shipping breaker agrees (refuses):    ${agreedRefusals}`);
console.log(`cells that diverge at all:                  ${cellsDiverged} of ${cells}`);
console.log(`  first divergence = shipping ADMITS it:    ${shipAdmits}`);
console.log(`  first divergence = shipping REFUSES it:   ${shipRefuses}`);
