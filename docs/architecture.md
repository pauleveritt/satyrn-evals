# Architecture

V1's grading seam remains the foundation. Capture and attempt add repository
and process lifecycles around it without changing how a verdict is computed.

## Data flow

```
PATCH ──► parse ──► allowlist ──► copy base ──► git apply ──► oracle ──► hook result ──► verdict ──► receipt
              │                                                        (unique path)
              ▼
         manifest
```

`grade()` in `src/satyrn_evals/grade.py`:

1. **Load the manifest** — `manifest.py` validates the {term}`task`'s
   `manifest` (`manifest.json`): contract, oracle command,
   expected test IDs, source {term}`allowlist`, fixture patch
   paths.
2. **Read and vet the patch** — `patch.py` parses the unified diff,
   extracts the touched paths, and checks the {term}`allowlist`; a
   patch touching anything else is rejected before anything runs.
3. **Materialize and apply** — the {term}`task`'s base state is copied to a
   temp directory, `git init` + `git apply` apply the patch.
4. **Run the oracle** — the `manifest`'s oracle command (for
   `format_number`, `python -m pytest -p satyrn_evals.oracle_hook`) runs
   in the workspace with a *unique, reserved-but-unlinked* hook-result
   path in its environment. The hook's `pytest_sessionfinish` writes the
   {term}`hook result` JSON.
5. **Load and validate the hook result** — `verdict.py` rejects a missing,
   stale, unparseable, or internally inconsistent file as `unavailable`.
6. **Compute the verdict** — executed test IDs must equal the
   `manifest`'s expected IDs; any skip means `unavailable`; any
   failure or error means `fail`; all pass means `pass`.
7. **Write the receipt** — `receipt.py`; the CLI maps the {term}`verdict`
   to an exit code (0 / 2 / 3).

The oracle's stdout and exit code are discarded. The
{term}`receipt` — not the process result — is what a caller reads.

## Why the verdict comes from a hook file

Predecessor graders were defeated twice by a clean zero that proved
nothing: `addopts = --collect-only` made pytest collect without running a
single test, and an import-time `os._exit(0)` killed the process before
anything ran. Both produce exit code 0.

The defense checks the evidence it receives rather than trusting a process
status:

- the oracle command and expected IDs are fixed in the `manifest`; the
  {term}`allowlist` limits patch writes to declared paths, but does not make
  tests immutable when a manifest deliberately allows `tests/`;
- the hook result path is reserved and unlinked before the oracle runs, so a
  silent oracle leaves *no* file. The oracle process receives the path, which
  is a documented authorship limit rather than a claim that a patch cannot
  forge it;
- a missing, stale, empty, or inconsistent file is `unavailable`, never
  `pass`;
- the executed-vs-expected-ID guard means "tests ran" is checked, not
  assumed.

## Modules

| Module | Responsibility |
|--------|----------------|
| `cli.py` | argparse and exit-code mapping for `grade`, `capture`, `attempt`, `run`, `summarize`, `regrade`, `session`, and `census` |
| `grade.py` | orchestration: materialize, apply, run oracle, write receipt |
| `capture.py` | orchestration: pin, preflight, derive, worktree, materialize, verify, cleanup, record |
| `capture_record.py` | the durable capture artifact (E3-shaped JSON) |
| `attempt.py` | orchestration: invoke the workspace, preserve, refuse, grade, record |
| `attempt_record.py` | the durable attempt artifact (E3-shaped JSON) |
| `run.py` | orchestration: repeat the attempt seam `n` times, then write the counts-only summary |
| `summary.py` | the durable run artifact: `summary.json` computed from attempt records |
| `workspace.py` | reconstruct a private Git repository; own detached-worktree, process, and cleanup lifecycles |
| `diff_filter.py` | parse NUL-safe Git change metadata; classify both rename paths with the test-path rule |
| `discriminating.py` | the discriminating set and the recorded oracle |
| `manifest.py` | load/validate the {term}`task` `manifest`; resolve tasks by name |
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
3. **Un-done at base** — the discriminating set (fail at base ∩
   pass with the fix) is non-empty.
4. **Winnable** — the recorded oracle (the discriminating IDs
   baked in) passes every one of them.

A failed check writes a capture record with `outcome: refused` and
a precise `code`; the exit code stays coarse (`0` captured, `2` usage, `3`
refusal). The three oracle runs reuse V1's hook-result machinery: a unique
reserved-but-unlinked hook path, the run-start timestamp, and the
stale-file rejection.

## Attempt: the seam

`attempt()` exercises the seam the roadmap is built around: an executable
command produces a patch for a {term}`task`, and evals preserves and grades
what the command delivered.

```
BASE ──► private Git repo ──► detached worktree at exact synthetic BASE
      ──► run COMMAND once ──► preserve patch + transcript ──► cleanup
      ──► refuse on incomplete artifacts ──► grade() ──► attempt record
```

`attempt()` in `src/satyrn_evals/attempt.py` asks `workspace.py` to turn the
task base into one deterministic commit and run the command in a clean,
detached linked worktree. Repository-local Git routing variables are removed,
hooks and fsmonitor are disabled for eval-owned Git commands, and normal Git
filters remain active. The command receives the env seam
(`SATYRN_TASK_NAME` and `SATYRN_TASK_CONTRACT` as inputs;
`SATYRN_ATTEMPT_PATCH` and `SATYRN_ATTEMPT_TRANSCRIPT` as reserved delivery
paths inside the attempt directory), reads the delivered patch and
transcript from those paths, refuses on incomplete artifacts with one of
four codes (`NO_PATCH`, `PATCH_INVALID`, `TRANSCRIPT_MISSING`,
`TRANSCRIPT_EMPTY`), grades the delivered patch with the same `grade()` V1
uses, and writes the attempt record. The outcome is artifact-driven:
the command's exit code is recorded as `command_exit` but never trusted.
Preservation precedes cleanup — the delivered artifacts live in the attempt
directory, outside the workspace, so a grading defect can be fixed and
re-scored without re-running the attempt.

An Engine-capable manifest may name a task-relative `engine_contract`.
Evals validates that it is a regular file reached without symlinks, then
appends its absolute path to the executable argv. The file contents remain
opaque: Engine owns their schema. A task without the field gets a contract
**generated** from its own manifest plus the selected contract rung,
written once under the output root at a path keyed by the sha256 of the
rendered bytes and appended the same way. Generating it keeps the text the
model sees equal to the text on record; keying the path by content keeps
every cell of a run recording one command, which is what lets the batch
summarize. When the command times out, evals terminates
and reaps its POSIX process group before Git cleanup. If cleanup cannot prove
the worktree registration absent before grading, the attempt is refused as
`CLEANUP_FAILED` and the record names the retained recovery path. Cleanup is
normally later than the final record and receipt: a late retention keeps an
`OK` or `GRADE_FAILED` record, its hook-derived evidence, and its regrade path,
then records the retained recovery path separately. The command reports that
retention as operational failure. This is process and workspace hygiene, not a
security sandbox; Windows is outside the V4 proof.

## Testing: two tiers and the tripwire

- **Default tier** — no model, no network, no subprocess, enforced by the
  tripwire: a CPython audit hook in `tests/conftest.py` that
  raises on any spawn. Weakening it fails the build.
- **Integration tier** — marked `integration` and excluded from the
  default run: real Git/worktree operations, oracle subprocesses, process
  groups, and the real Engine seam. The evidence-floor requirement from
  BRIEF invariant 5 accepts a bundled {term}`task`'s known-good
  patch and rejects its known-broken patch, each asserted by
  naming the fixture.

Every refusal test has a sibling success test, so rejection cannot pass
vacuously.

## Current boundary

The diagnostic loop and session evaluation are available. Current work
qualifies task conditions and a recoverable execution route before another
engine comparison. See [the roadmap](https://github.com/pauleveritt/satyrn-evals/blob/main/ROADMAP.md) for the active milestone.
