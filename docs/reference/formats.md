# Task and artifact formats

Reference for the on-disk formats: what a {term}`task` directory contains and
what each command writes. Command flags and exit codes live in the [CLI
reference](../usage.md); goal-oriented instructions live in the
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
| `contracts` | optional {term}`contract rung` map, `{rung key: text}`; an open map with no enum of rung names in code |
| `oracle` | the {term}`oracle` command; its {term}`hook result` — never its stdout or exit code — decides the {term}`verdict` |
| `expected_test_ids` | the test IDs the {term}`oracle` must execute, no more and no fewer |
| `source_paths` | the {term}`allowlist`: the only paths a {term}`patch` may touch |
| `fixtures` | `known_good` (required) and `known_broken` (optional) patch paths |
| `provenance` | captured tasks only: `repo`, `base_sha`, `fix_sha` |
| `engine_contract` | optional and engine-owned: Evals validates only its safe task-relative path and never parses its contents. A task without it gets a **generated** contract instead (below) |

### Contract rungs

`contracts` is an **open** map from a rung key to the contract text that rung
exports:

```json
"contracts": {
  "R1": "… the failing check names and the assertion text …",
  "R3": "… plus the file the defect sits in, and what to change …"
}
```

- Absent means the task has no rungs; `--rung` against it is a usage error
  naming the task.
- Keys and values are non-empty strings. No rung name is enumerated in
  production code, so a new rung is an authoring change, not a code change.
- `contract` stays the default and is what an attempt without `--rung`
  exports. On the six `agentclinic-repair-*` tasks it is equal to `R3`.
- For a hidden-{term}`oracle` task, the grader-only path check runs over
  `contract` **and every rung value**: a rung naming the overlay directory or
  one of its files is refused at load, with the message naming the rung. This
  is why an R1 digest carries **bare** hidden function names
  (`test_post_complaint_redirects_to_complaints_board`) and never the
  `<file>::<test>` node-id form `expected_test_ids` uses.

**A stated limit.** The rung labels are *unverified authoring claims*. Only
R1 and R3 ship, so the R0→R3 monotonicity gate collapses to a two-point
`R1 ≤ R3` check, and no run in this phase measures it. R0 and R2, and the
restored four-point check, are a V12 entry gate.

### The generated Engine contract

A task that does **not** declare `engine_contract` gets one rendered from its
own manifest plus the selected rung, so the text the model sees is the text
on record:

```yaml
id: "agentclinic-repair-plausible-wrong-fix@R1+…"
task: "… the selected contract text …"
writable_paths:
  - "app.py"
  - "templates/*"
```

- Both `id` and `task` are required — Engine requires `id` as well as `task`.
- `id` is stable for the same (task, rung, contract digest) and changes when
  the rung text changes.
- `writable_paths` derives from `source_paths`: a **file** entry stays exact;
  a **directory** entry becomes an fnmatch pattern over its descendants. An
  entry with nothing at that path in `base/` is a creation target and stays
  exact.
- The rendered bytes are written once under the run's output root at
  `engine-contracts/<sha256 of the bytes>.yaml`, and that absolute path is
  appended to the command. The path is deterministic on purpose: a fresh
  per-attempt path would change the recorded command, and a summary refuses
  mixed commands, so the batch would not summarize.

Engine's acceptance of the generated shape is proven by an integration-tier
row that runs the real `satyrn-engine check` over all six tasks at both
rungs; `id` stability is a claim about this generator, not about Engine.

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
  "timeout": 900.0,
  "patch_path": "patch.diff",
  "transcript_path": "transcript.txt",
  "patch_digest": "251a3d81e289f932d69bb1d93116fda757f47b9dcbdb11e9bc68aab7dd687ebc",
  "transcript_digest": "68b680be59b044860a88a04d273ef8df0a3482539ba133c8154d2c4880a56c17",
  "verdict": "pass",
  "receipt_path": "receipt.json",
  "rung": "R1",
  "contract_digest": "c4ca…",
  "workspace_base_sha": "…",
  "retained_path": null
}
```

The record is authoritative; the exit code is coarse. `command_exit` is
recorded as diagnostic context and never trusted — a command that exits
nonzero with complete artifacts is still attempted and graded. It is null if
no normal child exit was observed. `patch_digest` is the sha256 of the
persisted `patch.diff`, the same value the {term}`receipt` records — one
source, no drift. `timeout` is the attempt command's timeout in seconds;
records written by V9 always carry it, and older generations load without
it. `rung` is the selected {term}`contract rung` key, null when the default
`contract` was exported; `contract_digest` is the sha256 of the exact
selected text and is **always** present on a new record, including the
default contract. Records from before V11a load with both null and
re-summarize preserving those explicit unknowns — a new record generation,
not a rewrite of history (`version` stays `1`).

A refusal keeps the same shape with `outcome: refused`, a precise `code`,
`verdict` and `receipt_path` null, and `patch_path`/`transcript_path` null
for an artifact that never existed; artifacts that do exist are persisted
even on refusal, so the record names exactly what was preserved.

An admitted attempt whose grading did not complete is recorded with code
`GRADE_FAILED`: outcome `attempted`, no verdict, no receipt — the patch and
transcript are preserved and the cell is visible to `regrade`. The record is
written before grading starts, so a grading failure never leaves an invisible
cell:

```json
{
  "version": 1, "outcome": "attempted", "code": "GRADE_FAILED",
  "message": "attempt preserved and admitted; grading did not complete: <exception>",
  "patch_path": "patch.diff", "transcript_path": "transcript.txt",
  "verdict": null, "receipt_path": null
}
```

Refusal is a preservation failure; `unavailable` is a grading failure.
Refusal = the artifacts were incomplete (`NO_PATCH`, `PATCH_INVALID`,
`TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY`) or the run failed outside the
command (`WORKSPACE_FAILED`, `COMMAND_TIMEOUT`, `CLEANUP_FAILED`) — no
{term}`receipt`, nothing complete to grade. `unavailable` = the patch was
well-formed but couldn't be graded (doesn't apply, touches non-allowlisted
paths, no trustworthy {term}`hook result`) — the receipt names the cause.

## Run summary

`run` writes `<output>/summary.json` only when all `n` attempts complete
(including refusals):

| Field | Meaning |
|------|---------|
| `n` | the requested attempt count; `attempted + refused = n` |
| `attempted` | attempts whose command ran and delivered a complete, gradeable patch (an admitted cell, whether grading completed or was recorded as `GRADE_FAILED`) |
| `refused` | attempts refused (artifact, workspace, timeout, or cleanup) |
| `code_counts` | one key per attempt code (`OK` plus every refusal code, counting outcomes) |
| `verdict_counts` | one key per verdict (`pass`, `fail`, `unavailable`) |
| `timeouts` | equals `code_counts["COMMAND_TIMEOUT"]` |
| `task` | the task name from the attempt records |
| `command` | the effective attempt command from the records (including any engine-contract suffix) |
| `timeout` | the attempt timeout in seconds |
| `rung` | the {term}`contract rung` every cell ran at, null for the default contract or a pre-V11a batch |
| `contract_digest` | the sha256 of the exact contract text every cell exported, null for a pre-V11a batch |
| `pathology` | per-cell block keyed by the cell names in `cells` order: each a measured count set or `{"measured": false, "reason": …}`; absent or unparseable/unknown-vocabulary/structurally-unsound transcripts are `unmeasured`, never zero. Measured cells include `loop_broken`, the number of Engine `entry_appended` events whose `entry.customType` is `loop_broken`. Hidden-oracle runs add `overlay_windows` to measured cells; visible-oracle runs carry no overlay key. Count definitions and the reason set: the V10 spec (`docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md` §3) |

A summary refuses a mixed batch: cells at different rungs, or cells at the
same rung whose contract digests differ, are refused exactly as mixed tasks,
commands and timeouts are. The rung label is an authoring claim; the digest
is the text itself.

The summary is counts-only by design: outcome tallies, never wall-clock
times, confidence intervals, or publication claims. It is the authoritative
result of a completed run.

An aborted run is never presented as complete. If the loop stops early — an
exception or Ctrl-C — `run` writes `<output>/aborted.json` instead of
`summary.json`, carrying the requested attempt count, the completed count,
the error, and the tallies over the completed cells; a later completed run
in the same directory replaces the marker with its `summary.json`.

A summary can be rebuilt from disk: `satyrn-evals summarize OUTPUT_DIR`
recomputes `summary.json` from the preserved attempt records and
transcripts through the same tally `run` uses, so a rebuilt summary is
byte-identical to the run's own under the same code and artifacts. The
rebuild is anchored on the exact cells the run's `summary.json` names — a
stray sibling directory or an un-appended crash cell can never change it —
and it refuses a directory whose run aborted (exit `3`, message pointing
at `aborted.json`). A summary written before V10 carries no `pathology`
block; re-running `summarize` over such a run *enriches* it, computing the
block from the preserved transcripts — the retroactive mechanism that
applies V10 to runs already on disk. `satyrn-evals regrade ATTEMPT_DIR`
re-runs the grader over a preserved patch and rewrites its receipt and
record — the executable form of re-scoring without re-running an attempt.

A preserved transcript outside the V10 vocabulary (a fake command's
arbitrary text, a session's mapped transcript) makes that cell
`{"measured": false, "reason": …}` — a reporting state, never an error
and never a change to any exit code.

## Hook result

The JSON the {term}`oracle` writes through the pytest plugin at a path only
grading knows — reserved, unlinked before the run, and rejected as stale.
It records executed test IDs, per-test outcomes, and counts. `verdict.py`
treats a missing, stale, unparseable, or internally inconsistent file as
`unavailable`, never `pass`.
