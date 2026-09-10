# Self-test tool implementation plan (offline scope)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `run_self_test`, a pi extension tool giving the packet-route
implementer the same test-then-correct loop a continuous session already
has via `bash` — proven entirely offline. **This plan does not invoke a
real `pi` process anywhere.** Its last task writes a live-verification
proposal document; it does not execute one.

**Architecture:** A pure, dependency-free TypeScript core
(`self_test_tool_core.ts`) that any real exec function can drive, tested
directly via Node against real subprocesses (`/bin/true`, a nonexistent
binary, a real timeout) — no pi, no mocks. A thin pi extension wrapper
(`self_test_tool.ts`) that only pi's own loader can fully resolve (it
imports `typebox` and pi's `ExtensionAPI`, both supplied by pi's runtime,
not by plain Node), kept intentionally small so its correctness follows
from the core's own proof plus inspection. Python-side wiring in
`adapters/pi_implementer.py` only.

**Tech Stack:** Node 22+ (already installed via volta; this repo's first
Node/TypeScript files — Node runs `.ts` directly, no build step, no
`package.json`, no npm dependency, confirmed by direct probe during
planning). Python 3.14 for the wiring half.

**Spec:** [docs/superpowers/specs/2026-09-10-self-test-tool-design.md](../specs/2026-09-10-self-test-tool-design.md)

## Global Constraints

- No task in this plan invokes a real `pi` process.
- `run_self_test` takes zero model-supplied parameters.
- Throwing (`isError`) is reserved for a launch failure or a timeout
  (`killed`); a real exit code, zero or not, returns normally.
- The tool's own returned `content` is capped; `SelfTestOutcome`'s
  harness-side retention (already shipped, `route.py`) is untouched and
  stays uncapped.
- `command_implementer` (`route.py`) is not modified by this plan. All
  wiring is in `adapters/pi_implementer.py`.

---

## Task 1: `self_test_tool_core.ts` — the pure, testable logic

**Files:**
- Create: `src/satyrn_evals/adapters/self_test_tool_core.ts`
- Test: `src/satyrn_evals/adapters/self_test_tool_core.test.ts`

**Interfaces:**
- Produces: `type ExecResult = { stdout: string; stderr: string; code:
  number | null; killed: boolean }`, `type ExecFn = (command: string, args:
  string[], options: { timeout: number; signal?: AbortSignal }) =>
  Promise<ExecResult>`, `type RunSelfTestResult = { isError: boolean;
  text: string }`, `async function runSelfTest(argv: string[], timeoutMs:
  number, exec: ExecFn, maxOutputChars: number): Promise<RunSelfTestResult>`.
  Task 2's extension wrapper supplies `exec` (bound to `pi.exec`) and
  imports `runSelfTest`.

- [ ] **Step 1: Write the failing tests**

Create `src/satyrn_evals/adapters/self_test_tool_core.test.ts`:

```typescript
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
          code: error && typeof (error as NodeJS.ErrnoException & { code?: number }).code === "number"
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test src/satyrn_evals/adapters/self_test_tool_core.test.ts`
Expected: fails to resolve `./self_test_tool_core.ts` (module does not
exist yet).

- [ ] **Step 3: Implement `self_test_tool_core.ts`**

Create `src/satyrn_evals/adapters/self_test_tool_core.ts`:

```typescript
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test src/satyrn_evals/adapters/self_test_tool_core.test.ts`
Expected: PASS, all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/adapters/self_test_tool_core.ts \
  src/satyrn_evals/adapters/self_test_tool_core.test.ts
git commit -m "self_test_tool_core: pure test-execution logic, proven against real processes"
```

---

## Task 2: `self_test_tool.ts` — the pi extension wrapper

**Files:**
- Create: `src/satyrn_evals/adapters/self_test_tool.ts`

**Interfaces:**
- Consumes: `runSelfTest` (Task 1).
- Produces: a pi extension file, loadable via `pi -e
  src/satyrn_evals/adapters/self_test_tool.ts`, registering one tool named
  `run_self_test`.

**Why this file has no offline test of its own:** it imports `typebox`
and `@earendil-works/pi-coding-agent`'s `ExtensionAPI` type, both supplied
by pi's own extension loader, not resolvable by plain `node
self_test_tool.ts` (verified during planning: pi's docs list these as
"Available Imports" specifically inside its extension-loading context).
All the logic that matters is already proven in Task 1; this file is thin
wiring, kept small enough to verify by inspection against pi's own
documented `registerTool`/`pi.exec` contracts
(`extensions.md`, "Tool Definition" and "pi.exec"), plus a syntax-only
check that does not need those imports to resolve.

- [ ] **Step 1: Write the file**

Create `src/satyrn_evals/adapters/self_test_tool.ts`:

```typescript
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
// live-verification smoke (Task 4) or a real HP7 run produces one, per
// this project's own rule against guessed figures presented as
// considered (`BRIEF.md`).
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
```

- [ ] **Step 2: Syntax-check the file**

Run: `node --check src/satyrn_evals/adapters/self_test_tool.ts`
Expected: no output (Node's type-stripping accepts the syntax; this does
not resolve `typebox` or `@earendil-works/pi-coding-agent`, so it cannot
catch a wrong import path or a wrong `ExtensionAPI` field name — full
behavioral proof is the live-verification smoke proposed in Task 4, not
run by this plan).

- [ ] **Step 3: Re-read against pi's documented contract**

Confirm by inspection, against
`~/.volta/tools/image/packages/@earendil-works/pi-coding-agent/lib/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md`
("Tool Definition", "pi.exec", "Signaling errors"):
- `parameters: Type.Object({})` matches the documented `Type.Object(...)`
  pattern for a schema with no fields.
- `execute`'s signature `(toolCallId, params, signal, onUpdate, ctx)` is
  used positionally here as `(_toolCallId, _params, signal)` — confirm the
  docs' own example uses the same first-three-positional-parameters
  pattern before relying on it (`extensions.md` "Tool Definition" example
  does).
- Throwing inside `runSelfTest` (Task 1) propagates out of `execute`
  uncaught, which `extensions.md`'s "Signaling errors" states sets
  `isError: true` — no explicit try/catch is added here specifically so
  that documented behavior does the work, rather than this file
  duplicating it.

- [ ] **Step 4: Commit**

```bash
git add src/satyrn_evals/adapters/self_test_tool.ts
git commit -m "self_test_tool: the pi extension wrapper, wired to the proven core"
```

---

## Task 3: Wire `pi_implementer.py` to declare the tool only when it applies

**Files:**
- Modify: `src/satyrn_evals/adapters/pi_implementer.py`
- Modify: `tests/test_pi_implementer.py`

**Interfaces:**
- Produces: `build_pi_argv(model, tools, prompt, pi_bin="pi", *,
  self_test_command: tuple[str, ...] | None = None) -> list[str]` (adds a
  keyword parameter to the existing function); `main()` reads
  `projection.get("self_test_command")` and passes it through, and sets
  `SATYRN_SELF_TEST_COMMAND` in the child's environment only when present.

- [ ] **Step 1: Write the failing tests**

Find `tests/test_pi_implementer.py`'s existing `build_pi_argv` tests (`grep
-n "build_pi_argv" tests/test_pi_implementer.py`) and add alongside them:

```python
def test_no_self_test_command_adds_no_extension_or_tool() -> None:
    argv = build_pi_argv("model", ("read", "write"), "prompt", "pi")
    assert "-e" not in argv
    assert "run_self_test" not in ",".join(argv)


def test_an_empty_self_test_command_adds_no_extension_or_tool() -> None:
    argv = build_pi_argv(
        "model", ("read", "write"), "prompt", "pi", self_test_command=()
    )
    assert "-e" not in argv


def test_a_declared_self_test_command_adds_the_extension_and_tool() -> None:
    argv = build_pi_argv(
        "model",
        ("read", "write"),
        "prompt",
        "pi",
        self_test_command=("uv", "run", "pytest"),
    )
    assert "-e" in argv
    extension_path = argv[argv.index("-e") + 1]
    assert extension_path.endswith("self_test_tool.ts")
    tools_value = argv[argv.index("--tools") + 1]
    assert "run_self_test" in tools_value.split(",")
```

Find `main()`'s existing integration tests (search for how
`SATYRN_HANDOFF_PACKET`/environment is asserted in that file — likely via
`monkeypatch.setattr(pi_implementer.subprocess, "run", fake)`, matching
the file's existing pattern for `main()` tests) and add one in the same
style:

```python
def test_main_sets_the_self_test_env_var_only_when_declared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_env: dict[str, str] = {}

    def fake(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        captured_env.update(kwargs["env"])  # type: ignore[arg-type]
        (tmp_path / "result.json").write_text(
            '{"changed_files": [], "reported_outcome": "refused", '
            '"message": null, "version": 1}'
        )
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    monkeypatch.setenv(pi_implementer.PACKET_ENV, str(tmp_path / "packet.json"))
    monkeypatch.setenv(pi_implementer.RESULT_ENV, str(tmp_path / "result.json"))
    (tmp_path / "packet.json").write_text(
        json.dumps(
            {
                "objective": "do the thing",
                "self_test_command": ["uv", "run", "pytest"],
            }
        )
    )
    monkeypatch.setattr(sys, "argv", ["pi_implementer", "--model", "m"])
    pi_implementer.main()
    assert pi_implementer.SELF_TEST_COMMAND_ENV in captured_env
    assert json.loads(captured_env[pi_implementer.SELF_TEST_COMMAND_ENV]) == [
        "uv", "run", "pytest",
    ]
```

Check the file's existing imports (`json`, `subprocess`, `sys`, `pytest`,
`Path`) are already present before adding this test — match whatever is
already imported rather than assuming.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_pi_implementer.py -k self_test`
Expected: FAIL (`build_pi_argv` has no `self_test_command` parameter yet;
`SELF_TEST_COMMAND_ENV` does not exist).

- [ ] **Step 3: Implement**

In `src/satyrn_evals/adapters/pi_implementer.py`, add near the existing
`DEFAULT_TOOLS`/`DEFAULT_TIMEOUT_SECONDS` constants:

```python
RUN_SELF_TEST_TOOL_NAME = "run_self_test"
SELF_TEST_COMMAND_ENV = "SATYRN_SELF_TEST_COMMAND"
SELF_TEST_EXTENSION_PATH = Path(__file__).parent / "self_test_tool.ts"
```

Replace `build_pi_argv`:

```python
def build_pi_argv(
    model: str,
    tools: tuple[str, ...],
    prompt: str,
    pi_bin: str = "pi",
    *,
    self_test_command: tuple[str, ...] | None = None,
) -> list[str]:
    """One Pi process invocation, not one model turn -- see the module
    docstring's 2026-09-10 correction. Space-form model flag, matching
    every other adapter in this repository (pi 0.84.4 rejects the equals
    form).

    When ``self_test_command`` is declared, adds ``-e
    self_test_tool.ts`` -- an explicit extension path, which pi's own
    ``--help`` confirms still loads under ``--no-extensions`` -- and
    ``run_self_test`` to the tool allowlist. Neither is added when no
    command is declared: an absent capability, not one that reliably
    throws when called.
    """
    if not prompt.strip():
        raise AdapterError("refusing to launch pi with an empty prompt")
    effective_tools = tools
    argv = [
        pi_bin,
        "--print",
        "--mode",
        "json",
        "--no-session",
        "--model",
        model,
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-context-files",
        "--no-approve",
    ]
    if self_test_command:
        argv += ["-e", str(SELF_TEST_EXTENSION_PATH)]
        effective_tools = (*tools, RUN_SELF_TEST_TOOL_NAME)
    argv += ["--tools", ",".join(effective_tools), prompt]
    return argv
```

In `main()`, after `projection = read_projection(packet_path)`, add
parsing for the declared command:

```python
    raw_self_test_command = projection.get("self_test_command")
    if raw_self_test_command is not None and not (
        isinstance(raw_self_test_command, list)
        and all(isinstance(token, str) for token in raw_self_test_command)
    ):
        raise AdapterError(
            f"{PACKET_ENV} self_test_command must be a list of strings or null"
        )
    self_test_command = (
        tuple(raw_self_test_command) if raw_self_test_command else None
    )
```

Then update the `subprocess.run` call's `env=` and `build_pi_argv` call:

```python
        child_env = session_child_environment(os.environ)
        if self_test_command:
            child_env = {
                **child_env,
                SELF_TEST_COMMAND_ENV: json.dumps(list(self_test_command)),
            }
        subprocess.run(
            build_pi_argv(
                model, tools, prompt, pi_bin, self_test_command=self_test_command
            ),
            cwd=workspace,
            stdout=transcript,
            stderr=stderr_log,
            check=True,
            timeout=timeout,
            env=child_env,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_pi_implementer.py`
Expected: PASS, all tests including the new ones and the existing
`build_pi_argv`/`main` suite (no regression).

- [ ] **Step 5: Run the full default-tier suite and lint**

Run: `uv run pytest -q`
Expected: PASS.

Run: `uv run ruff check src/satyrn_evals/adapters/pi_implementer.py tests/test_pi_implementer.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/adapters/pi_implementer.py tests/test_pi_implementer.py
git commit -m "pi_implementer: declare run_self_test only when self_test_command exists"
```

---

## Task 4: Write the live-verification proposal (do not run it)

**Files:**
- Create: `docs/current/self-test-tool-live-verification-pre-run-record.md`
- Modify: `docs/development/index.md` (toctree entry)

**Interfaces:** none — this is a document, not code. **This task does not
invoke `pi`.**

- [ ] **Step 1: Write the pre-run record**

Following `hp7-live-route-proof-pre-run-record.md`'s shape (frozen
conditions, what the run establishes and does not, preconditions, what
voids it), draft a record proposing exactly one bounded `pi` invocation:

- A trivial fixture workspace and a packet whose `self_test_command` is
  engineered to fail once (a test asserting a value the workspace's
  starting file does not yet have) and pass after one obvious one-line
  fix.
- A prompt asking the implementer to make the declared test pass.
- The only question: does Pi discover and call `run_self_test`, and does
  a real failure's content reach it legibly enough to act on. Not whether
  it improves anything — matching HP7's own "operability, not
  superiority" framing exactly.
- `n = 1`, frozen, not extended after reading the result — the same rule
  every other pre-run record in this repository holds itself to.
- Explicit budget: state the exact model, one bounded turn ceiling for
  this single phase, and a wall-clock cap, chosen the same way HP7's own
  record chose its figures (checked against representative retained
  traces where any exist, not invented).
- States plainly: this stays outside every TE confirmation denominator,
  the same discipline `HP7`/`HP8` results already hold to.

- [ ] **Step 2: Register it in the toctree**

Add `current/self-test-tool-live-verification-pre-run-record` (or its
project-relative path from `docs/development/index.md`, matching how
other pre-run records are already listed there) to `docs/development/index.md`'s
toctree block.

- [ ] **Step 3: Run the docs gates**

Run: `just lint-docs`
Expected: clean.

Run: `just docs`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add docs/current/self-test-tool-live-verification-pre-run-record.md \
  docs/development/index.md
git commit -m "Propose one bounded live smoke for run_self_test, not run by this commit"
```

- [ ] **Step 5: Report back**

Bring the finished pre-run record and its stated budget back for explicit
authorization before any `pi` process runs. This plan's own scope ends
here.
