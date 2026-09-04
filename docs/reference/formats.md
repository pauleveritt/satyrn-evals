# Task and artifact formats

Reference for the on-disk formats: what a {term}`task` directory contains and
what each command writes. Command flags and exit codes live in the [CLI
reference](usage.md); goal-oriented instructions live in the
[guides](../guides/index.md).

## The task directory

```text
<task>/
  manifest.json
  base/                  # the un-done base state a patch applies to
  fixtures/
    known-good.patch     # always present
    known-broken.patch   # when the task ships one
  engine-contract.yaml   # when the manifest declares engine_contract
```

`manifest.json` fields:

| Field | Meaning |
|------|---------|
| `name` | the {term}`task` name; must match its directory |
| `contract` | the task statement, handed to the {term}`attempt command` as `SATYRN_TASK_CONTRACT` |
| `oracle` | the {term}`oracle` command; its {term}`hook result` — never its stdout or exit code — decides the {term}`verdict` |
| `expected_test_ids` | the test IDs the {term}`oracle` must execute, no more and no fewer |
| `source_paths` | the {term}`allowlist`: the only paths a {term}`patch` may touch |
| `fixtures` | `known_good` (required) and `known_broken` (optional) patch paths |
| `provenance` | captured tasks only: `repo`, `base_sha`, `fix_sha` |
| `engine_contract` | optional and engine-owned: Evals validates only its safe task-relative path and never parses its contents |

Tasks resolve from a tasks root: the bundled tasks that ship in the wheel by
default, or a directory of captured tasks via `--tasks-root`. A captured task
writes its {term}`capture record` beside the task directory, as
`<tasks-root>/<name>.capture.json`.

## Receipt

Written by `grade`, and by `attempt` and `run` for every gradeable patch:

```json
{
  "task": "format_number",
  "patch_digest": "251a3d81e289f932d69bb1d93116fda757f47b9dcbdb11e9bc68aab7dd687ebc",
  "verdict": "pass",
  "reason": "",
  "evidence": {
    "executed_test_ids": ["test_solution.py::test_large", "test_solution.py::test_negative", "test_solution.py::test_small", "test_solution.py::test_zero"],
    "outcomes": {"test_solution.py::test_small": "passed", "test_solution.py::test_large": "passed", "test_solution.py::test_negative": "passed", "test_solution.py::test_zero": "passed"},
    "counts": {"passed": 4, "failed": 0, "error": 0, "skipped": 0}
  }
}
```

`patch_digest` is the sha256 of the {term}`patch` file, so a {term}`receipt`
names the exact input it graded — re-scoreable without re-running anything.
`evidence` is the {term}`hook result` verbatim: the executed test IDs are
exactly the manifest's `expected_test_ids`, and the counts name every
outcome class.

## Capture record

Written by `capture` as `<output>/<name>.capture.json`, for captures and
refusals alike:

```json
{
  "version": 1,
  "outcome": "captured",
  "code": "OK",
  "message": "task captured",
  "repo": "/src/app",
  "base_sha": "…",
  "fix_sha": "…",
  "task_dir": "tasks/fix-off-by-one",
  "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook", "test_solution.py::test_one"],
  "expected_test_ids": ["test_solution.py::test_one"],
  "check_outcomes": {
    "source_preflight": "passed",
    "base_oracle": "passed",
    "un_done_at_base": "passed",
    "winnable": "passed"
  }
}
```

The record is the authoritative result; the exit code is coarse by design.
A refusal writes the same shape with `outcome: refused` and a precise
`code` (e.g. `REPO_DIRTY`, `NO_DISCRIMINATING_TESTS`, `ARTIFACT_FAILED`,
`CLEANUP_FAILED`). An existing task/record is a usage error and is never
overwritten.

## Attempt directory and record

`attempt` creates one timestamped directory beneath `--output`
(`<output>/<task>-<timestamp>/`, the timestamp UTC with microsecond
resolution):

```text
patch.diff        # the delivered patch, when the command wrote one
transcript.txt    # the delivered transcript, when the command wrote one
receipt.json      # written only when grading ran
attempt.json      # always
```

`attempt.json` — the {term}`attempt record`:

```json
{
  "version": 1,
  "outcome": "attempted",
  "code": "OK",
  "message": "attempt recorded and graded",
  "task": "format_number",
  "command": ["python", "…/tests/integration/fake_attempt.py", "--patch", "…/src/satyrn_evals/tasks/format_number/fixtures/known-good.patch"],
  "command_exit": 0,
  "patch_path": "patch.diff",
  "transcript_path": "transcript.txt",
  "patch_digest": "251a3d81e289f932d69bb1d93116fda757f47b9dcbdb11e9bc68aab7dd687ebc",
  "transcript_digest": "68b680be59b044860a88a04d273ef8df0a3482539ba133c8154d2c4880a56c17",
  "verdict": "pass",
  "receipt_path": "receipt.json",
  "workspace_base_sha": "…",
  "retained_path": null
}
```

The record is authoritative; the exit code is coarse. `command_exit` is
recorded as diagnostic context and never trusted — a command that exits
nonzero with complete artifacts is still attempted and graded. It is null if
no normal child exit was observed. `patch_digest` is the sha256 of the
persisted `patch.diff`, the same value the {term}`receipt` records — one
source, no drift.

A refusal keeps the same shape with `outcome: refused`, a precise `code`,
`verdict` and `receipt_path` null, and `patch_path`/`transcript_path` null
for an artifact that never existed; artifacts that do exist are persisted
even on refusal, so the record names exactly what was preserved.

Refusal is a preservation failure; `unavailable` is a grading failure.
Refusal = the artifacts were incomplete (`NO_PATCH`, `PATCH_INVALID`,
`TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY`) or the run failed outside the
command (`WORKSPACE_FAILED`, `COMMAND_TIMEOUT`, `CLEANUP_FAILED`) — no
{term}`receipt`, nothing complete to grade. `unavailable` = the patch was
well-formed but couldn't be graded (doesn't apply, touches non-allowlisted
paths, no trustworthy {term}`hook result`) — the receipt names the cause.

## Run summary

`run` writes `<output>/summary.json` after all `n` attempts complete,
including refusals:

| Field | Meaning |
|------|---------|
| `n` | the requested attempt count; `attempted + refused = n` |
| `attempted` | attempts that delivered a complete, gradeable patch — each has a verdict |
| `refused` | attempts refused (artifact, workspace, timeout, or cleanup) |
| `code_counts` | one key per attempt code (`OK` plus every refusal code), counting outcomes |
| `verdict_counts` | one key per verdict (`pass`, `fail`, `unavailable`) |
| `timeouts` | equals `code_counts["COMMAND_TIMEOUT"]` |

The summary is counts-only by design: outcome tallies, never wall-clock
times, confidence intervals, or publication claims. It is the authoritative
result of a run.

## Hook result

The JSON the {term}`oracle` writes through the pytest plugin at a path only
grading knows — reserved, unlinked before the run, and rejected as stale.
It records executed test IDs, per-test outcomes, and counts. `verdict.py`
treats a missing, stale, unparseable, or internally inconsistent file as
`unavailable`, never `pass`.
