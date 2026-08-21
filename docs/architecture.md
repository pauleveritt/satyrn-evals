# Architecture

V1 is the grading seam the rest of the roadmap builds on. One command,
seven small modules, two test tiers.

## Data flow

```
PATCH ──► parse ──► allowlist ──► copy base ──► git apply ──► oracle ──► hook result ──► verdict ──► receipt
              │                                                        (unique path)
              ▼
         manifest
```

`grade()` in `src/satyrn_evals/grade.py`:

1. **Load the manifest** — `manifest.py` validates the {term}`task`'s
   {term}`manifest` (`manifest.json`): contract, {term}`oracle` command,
   expected test IDs, source {term}`allowlist`, fixture {term}`patch`
   paths.
2. **Read and vet the patch** — `patch.py` parses the unified diff,
   extracts the touched paths, and checks the {term}`allowlist`; a
   {term}`patch` touching anything else is rejected before anything runs.
3. **Materialize and apply** — the {term}`task`'s base state is copied to a
   temp directory, `git init` + `git apply` apply the {term}`patch`.
4. **Run the oracle** — the {term}`manifest`'s {term}`oracle` command (for
   `format_number`, `python -m pytest -p satyrn_evals.oracle_hook`) runs
   in the workspace with a *unique, reserved-but-unlinked* hook-result
   path in its environment. The hook's `pytest_sessionfinish` writes the
   {term}`hook result` JSON.
5. **Load and validate the hook result** — `verdict.py` rejects a missing,
   stale, unparseable, or internally inconsistent file as `unavailable`.
6. **Compute the verdict** — executed test IDs must equal the
   {term}`manifest`'s expected IDs; any skip means `unavailable`; any
   failure or error means `fail`; all pass means `pass`.
7. **Write the receipt** — `receipt.py`; the CLI maps the {term}`verdict`
   to an exit code (0 / 2 / 3).

The {term}`oracle`'s stdout and exit code are discarded. The
{term}`receipt` — not the process result — is what a caller reads.

## Why the verdict comes from a hook file

Predecessor graders were defeated twice by a clean zero that proved
nothing: `addopts = --collect-only` made pytest collect without running a
single test, and an import-time `os._exit(0)` killed the process before
anything ran. Both produce exit code 0.

The defense is structural, not behavioral:

- the {term}`oracle` command is fixed in the {term}`manifest`, and the
  {term}`allowlist` stops a {term}`patch` from adding `addopts` or
  replacing the hook;
- the hook writes to a path the {term}`patch` cannot predict — and the
  path is unlinked before the oracle runs, so a silent oracle leaves *no*
  file;
- a missing, stale, empty, or inconsistent file is `unavailable`, never
  `pass`;
- the executed-vs-expected-ID guard means "tests ran" is checked, not
  assumed.

## Modules

| Module | Responsibility |
|--------|----------------|
| `cli.py` | argparse, `grade`, `capture`, and `attempt` commands, exit-code mapping |
| `grade.py` | orchestration: materialize, apply, run oracle, write receipt |
| `capture.py` | orchestration: pin, preflight, derive, worktree, materialize, verify, cleanup, record |
| `capture_record.py` | the durable capture artifact (E3-shaped JSON) |
| `attempt.py` | orchestration: materialize workspace, run the seam, preserve, refuse, grade, record |
| `attempt_record.py` | the durable attempt artifact (E3-shaped JSON) |
| `diff_filter.py` | parse NUL-safe Git change metadata; classify both rename paths with the test-path rule |
| `discriminating.py` | the {term}`discriminating set` and the recorded oracle |
| `manifest.py` | load/validate the {term}`task` {term}`manifest`; resolve tasks by name |
| `patch.py` | parse unified diffs; enforce the source {term}`allowlist` |
| `verdict.py` | load/validate the hook result; compute the verdict |
| `receipt.py` | the durable grading artifact (JSON) |
| `oracle_hook.py` | pytest plugin writing the trusted hook result (including collection errors) |
| `errors.py` | error hierarchy carrying exit codes (usage 2, operational 3) |

## Capture: the four deterministic checks

`capture()` turns a fixing commit into a {term}`task` without changing
pre-existing source files or the source repository's index, branch, or
`HEAD` — the pattern re-earned from the satyrn-engine E3 delivery spec.
Declared artifacts below `--output` are the sole write exception. Its
lifecycle:

```
FIX commit ──► pin PARENT ──► preflight clean ──► select source changes ──► worktree add --detach ──► materialize complete base ──► verify ──► cleanup ──► record
                  (usage errors write nothing)       (NUL-safe Git metadata)       (safe temp parent)                      (3 oracle runs)
```

Four deterministic checks prove the captured task is valid (un-done at
base, and winnable):

1. **Source preflight** — the tree is clean; `PARENT` exists; the fix diff
   has a non-test source path.
2. **Base oracle runs** — a full-suite run in the worktree at `PARENT`
   produces a hook result with no collection errors (missing dependencies
   refuse honestly as `ORACLE_ENV`).
3. **Un-done at base** — the {term}`discriminating set` (fail at base ∩
   pass with the fix) is non-empty.
4. **Winnable** — the recorded {term}`oracle` (the discriminating IDs
   baked in) passes every one of them.

A failed check writes a {term}`capture record` with `outcome: refused` and
a precise `code`; the exit code stays coarse (`0` captured, `2` usage, `3`
refusal). The three oracle runs reuse V1's hook-result machinery: a unique
reserved-but-unlinked hook path, the run-start timestamp, and the
stale-file rejection.

## Attempt: the seam

`attempt()` exercises the seam the roadmap is built around: an executable
command produces a patch for a {term}`task`, and evals preserves and grades
what the command delivered.

```
BASE ──► copy to disposable workspace ──► run COMMAND (env seam) ──► read patch + transcript
         from reserved paths ──► refuse on incomplete artifacts ──► grade() ──► attempt record
```

`attempt()` in `src/satyrn_evals/attempt.py` materializes the task's base
into a disposable workspace, runs the command there with the env seam
(`SATYRN_TASK_NAME` and `SATYRN_TASK_CONTRACT` as inputs;
`SATYRN_ATTEMPT_PATCH` and `SATYRN_ATTEMPT_TRANSCRIPT` as reserved delivery
paths inside the attempt directory), reads the delivered patch and
transcript from those paths, refuses on incomplete artifacts with one of
four codes (`NO_PATCH`, `PATCH_INVALID`, `TRANSCRIPT_MISSING`,
`TRANSCRIPT_EMPTY`), grades the delivered patch with the same `grade()` V1
uses, and writes the {term}`attempt record`. The outcome is artifact-driven:
the command's exit code is recorded as `command_exit` but never trusted.
Preservation precedes cleanup — the delivered artifacts live in the attempt
directory, outside the workspace, so a grading defect can be fixed and
re-scored without re-running the attempt.

## Testing: two tiers and the tripwire

- **Default tier** — no model, no network, no subprocess, enforced by the
  {term}`tripwire`: a CPython audit hook in `tests/conftest.py` that
  raises on any spawn. Weakening it fails the build.
- **Integration tier** — marked `integration` and excluded from the
  default run: real `git apply`, real oracle subprocesses, and the
  {term}`evidence floor`: the bundled {term}`task`'s known-good
  {term}`patch` is accepted and its known-broken {term}`patch` rejected,
  each asserted by naming the fixture.

Every refusal test has a sibling success test, so rejection cannot pass
vacuously.

## What is not here yet

- the real engine seam — V4
- the diagnostic loop — V5
- the {term}`baseline probe` — with the attempt loop

One phase at a time; no machinery ahead of the contract it serves.
