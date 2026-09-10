/**
 * The pure logic behind the `run_self_test` pi extension tool --
 * deliberately free of any pi-specific import (no `typebox`, no
 * `ExtensionAPI`) so it can be exercised directly via plain Node, against
 * real child processes, with no pi runtime and no model involved.
 *
 * A launch failure or a timeout throws (the extension wrapper maps that
 * to the tool result's `isError: true`, per pi's own documented
 * contract: throwing from `execute()` is the only way to set it). A
 * command that actually ran -- exit code 0 or not -- returns normally:
 * the ordinary tool-result path, the same shape a passing or failing
 * `bash` call already produces every turn.
 */

export type ExecResult = {
  stdout: string;
  stderr: string;
  code: number | null;
  killed: boolean;
};

export type ExecFn = (
  command: string,
  args: string[],
  options: { timeout: number; signal?: AbortSignal },
) => Promise<ExecResult>;

export type RunSelfTestResult = {
  isError: boolean;
  text: string;
};

function combinedOutput(result: ExecResult, maxChars: number): string {
  const combined = result.stdout + result.stderr;
  if (combined.length <= maxChars) {
    return combined;
  }
  const kept = combined.slice(combined.length - maxChars);
  return `[truncated to the last ${maxChars} characters]\n${kept}`;
}

export async function runSelfTest(
  argv: string[],
  timeoutMs: number,
  exec: ExecFn,
  maxOutputChars: number,
): Promise<RunSelfTestResult> {
  if (argv.length === 0) {
    throw new Error("run_self_test: no self_test_command was declared");
  }
  const [command, ...args] = argv;
  const result = await exec(command, args, { timeout: timeoutMs });
  if (result.killed) {
    throw new Error(
      `run_self_test: the command timed out after ${timeoutMs}ms: ${argv.join(" ")}`,
    );
  }
  if (result.code === null) {
    throw new Error(
      `run_self_test: the command could not be launched: ${argv.join(" ")}`,
    );
  }
  return {
    isError: false,
    text: `exit code ${result.code}\n${combinedOutput(result, maxOutputChars)}`,
  };
}
