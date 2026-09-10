/**
 * The pi extension exposing `run_self_test`: a zero-argument tool that
 * runs exactly the packet's own declared `self_test_command`, crossed in
 * via `SATYRN_SELF_TEST_COMMAND` (a JSON array of argv tokens) -- never a
 * command the model supplies, matching the same boundary
 * `self_test_command` naming the hidden oracle hook is already refused
 * for (`packet.py`, `build_packet`).
 *
 * Loaded explicitly (`pi -e <this file>`), alongside `--no-extensions`:
 * pi's own `--help` states an explicit `-e` path still loads under
 * `--no-extensions` -- this is what keeps any ambient satyrn-engine guard
 * extension from also loading while this one narrow tool does.
 *
 * `pi_implementer.py` adds this file to `-e` and `run_self_test` to
 * `--tools` only when a packet declares a `self_test_command`; when it
 * does not, neither this file nor the env var below is passed, so there
 * is nothing for this extension to do if it were ever loaded anyway.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { runSelfTest } from "./self_test_tool_core.ts";

const TIMEOUT_MS = 600_000; // matches DEFAULT_SELF_TEST_TIMEOUT_SECONDS (route.py)
// PROVISIONAL: no real Engine-phase self-test failure output exists yet
// to calibrate against (HP7 has not run live) -- 20_000 is a placeholder,
// picked as the right rough order (a few screens of pytest -v output),
// not a number checked against representative evidence. Revisit once the
// live-verification smoke or a real HP7 run produces one, per this
// project's own rule against guessed figures presented as considered
// (`BRIEF.md`).
const MAX_OUTPUT_CHARS = 20_000; // a context-economy cap, not an evidence cap --
// see the design's "Output is bounded and legible" section for why this
// differs from SelfTestOutcome's own deliberately uncapped retention.

export default function (pi: ExtensionAPI) {
  const raw = process.env.SATYRN_SELF_TEST_COMMAND;
  if (!raw) {
    // No command declared: register nothing. An absent capability, not
    // one that reliably throws when called.
    return;
  }
  const argv: string[] = JSON.parse(raw);

  pi.registerTool({
    name: "run_self_test",
    label: "Run self-test",
    description:
      "Run this task's declared public test command and report the result.",
    promptSnippet: "Run the declared public test command and see the result",
    promptGuidelines: [
      "Use run_self_test to check your work before finishing, and after any edit meant to fix a failure it reported.",
    ],
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, signal) {
      const result = await runSelfTest(
        argv,
        TIMEOUT_MS,
        (command, args, options) =>
          pi.exec(command, args, { ...options, signal: signal ?? options.signal }),
        MAX_OUTPUT_CHARS,
      );
      return { content: [{ type: "text", text: result.text }], details: {} };
    },
  });
}
