import { test } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { runSelfTest, type ExecFn, type ExecResult } from "./self_test_tool_core.ts";

// A real exec function, matching pi.exec's documented {stdout, stderr,
// code, killed} shape exactly (verified against Node's own execFile
// during planning: a timeout yields code=null/killed=true, a missing
// binary yields code=null/killed=false, a real exit yields a real code).
// No mocks anywhere in this file -- every test here drives a real child
// process, the same standard test_pi_implementer_ordering.py already
// holds this repository to.
const realExec: ExecFn = (command, args, options) =>
  new Promise<ExecResult>((resolve) => {
    execFile(
      command,
      args,
      { timeout: options.timeout, signal: options.signal },
      (error, stdout, stderr) => {
        resolve({
          stdout: stdout?.toString() ?? "",
          stderr: stderr?.toString() ?? "",
          code:
            error && typeof (error as unknown as { code?: number }).code === "number"
              ? (error as unknown as { code: number }).code
              : error
                ? null
                : 0,
          killed: !!(error && (error as NodeJS.ErrnoException).killed),
        });
      },
    );
  });

const MAX_OUTPUT = 10_000;

test("a command that exits 0 returns normally with its output", async () => {
  const result = await runSelfTest(["/bin/echo", "ok"], 2000, realExec, MAX_OUTPUT);
  assert.equal(result.isError, false);
  assert.match(result.text, /exit code 0/);
  assert.match(result.text, /ok/);
});

test("a command that exits non-zero still returns normally, not an error", async () => {
  const result = await runSelfTest(["/bin/sh", "-c", "exit 3"], 2000, realExec, MAX_OUTPUT);
  assert.equal(result.isError, false);
  assert.match(result.text, /exit code 3/);
});

test("a command that cannot launch throws, driven by a real ENOENT", async () => {
  await assert.rejects(
    () => runSelfTest(["satyrn-nonexistent-binary-xyz"], 2000, realExec, MAX_OUTPUT),
    /satyrn-nonexistent-binary-xyz/,
  );
});

test("a command exceeding the timeout throws, driven by a real kill", async () => {
  await assert.rejects(
    () =>
      runSelfTest(
        ["node", "-e", "setTimeout(() => {}, 5000)"],
        200,
        realExec,
        MAX_OUTPUT,
      ),
    /timed out/,
  );
});

test("output longer than the cap is truncated, not silently dropped", async () => {
  const result = await runSelfTest(
    ["node", "-e", "console.log('x'.repeat(500))"],
    2000,
    realExec,
    100,
  );
  assert.equal(result.isError, false);
  assert.ok(result.text.length < 500);
  assert.match(result.text, /truncated/);
});

test("stdout and stderr are both present in the returned text", async () => {
  const result = await runSelfTest(
    ["node", "-e", "console.log('out-marker'); console.error('err-marker')"],
    2000,
    realExec,
    MAX_OUTPUT,
  );
  assert.match(result.text, /out-marker/);
  assert.match(result.text, /err-marker/);
});
