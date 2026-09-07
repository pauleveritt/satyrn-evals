> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V9 — Loop integrity and re-scoring: design spec

**Date:** 2026-09-04.
**Status:** design proposal accepted by the maintainer's standing
instruction to take this phase through spec → plan → review →
implementation without a per-phase confirm round; the decisions in §0 are
the accepted recommendations.

**Amendment (2026-09-04, post-implementation review):** B1/B2 — an aborted
run writes `aborted.json` (requested/completed/error + the completed cells'
tallies), never `summary.json` (completion only); `summarize` is anchored
on the run's own summary cells and refuses aborted directories. B3 — a git
probe failure is one `UNAVAILABLE` cell, not a batch abort.

**Amends:** V5b's run summary (data shapes §3; CLI/exit codes keep their
meaning, extended not replaced) and V7's stored-file mode check (§4, a
recorded correction to `2026-09-04-v7-task-visibility-leak-detection-design.md`
§5). Supersession notes go into those files, not edited away.

## 0. Defects and accepted recommendations
Every batch downstream (V11's ladder, V12's profile, V13's probe) runs
through `run`/`grade`, which cannot survive a batch today. The deep review
enumerated T1–T14 (`2026-09-04-v5-v8-deep-review-and-agentclinic-ladder.md`
§3); the kickoff brief confirms V9 = T1–T9 + T14.

| # | Defect (anchor at HEAD `dd7a65e`) | Accepted design |
|---|---|---|
| T1 | `run` has no per-cell failure boundary (`run.py:35-50`) | attempt records every cell-level outcome incl. grade failure (new code `GRADE_FAILED`); `run` writes the completed summary before any abort |
| T2 | `attempt.json` written only after `grade()` returns (`attempt.py:226,229,247`) | **record-before-grade**: the admitted cell's record is written before grading as `GRADE_FAILED` (outcome `attempted`, no verdict/receipt); success rewrites `OK` + verdict + receipt; a grading `SatyrnError` returns the standing record with the exception in `message` |
| T3 | no production caller of `load_attempt_record` (`attempt_record.py:277`) | `regrade ATTEMPT_DIR` and `summarize OUTPUT_DIR` ship on preserved `attempt.json` via the **same** `compute_summary`/`write_summary` path as `run` |
| T4 | summary names cells but not task/command/timeout (`summary.py:25-34`) | `Summary` gains required task/command/timeout; the attempt record gains `timeout` (a V9 record generation) so the from-disk rebuild is complete |
| T5 | auto-overlay hijacks the V6 preservation grade when `base_preservation_selectors` ≠ `expected_test_ids` (`grade.py:67-70`, `session_grader.py:122-128`); masked: both bundled session fixtures' lists coincide | `grade()` gains `auto_overlay: bool = True`; the preservation call passes `False` |
| T6 | `mode & 0o022` stored-file check refuses hidden tasks on umask-002 checkouts (`overlay.py:74-79`) | the load-time writability refusal is removed (recorded V7 §5 correction); materialization `0o444` + the absence invariant carry the protection |
| T7 | oracle `PYTHONPATH` = evals install location, ahead of the locked env (`grade.py:211-213`) — wrong attestation off a wheel install | oracle hook imports through a shim dir holding only a symlink to the running evals package |
| T8 | grading's `git init`/`git apply` run in the ambient environment (`grade.py:185-190`) | they run under `clean_git_environment` + the safety config (workspace's own probe + clean, exported for grade) |
| T9 | model code at oracle collection can forge the result file (env `grade.py:208`; loader checks shape/consistency/freshness only, `verdict.py:37-40`) | stated limit beside BRIEF rule 4 and in the trust-boundaries topic; not fixed (no-model phase) |
| T14 | default attempt timeout 30 s (`workspace.py:28`) cost one V8 smoke | `DEFAULT_TIMEOUT` = **900 s** (the corrected probes' 2–15 min/cell ceiling); longer paths pass `--timeout` |

`contamination.py`, `patch.py`, `taskenv.py` are in the kickoff's file
list only because the review's audits crossed them — **V9 changes none**
(T10/T13 are out of V9's list).

## 1. T1 — per-cell boundary, and what "continue" means
A cell-level failure must never lose the completed cells' tallies or
force a model re-run. "Record a cell's exception as a cell outcome and
continue to n" is delivered by T2: a grading `SatyrnError` becomes a
returned `GRADE_FAILED` record, so the loop continues to n.

What still escapes attempt is the internal-bug class (non-`SatyrnError`: an
`OSError`, a defect in evals). `run` does **not** synthesize a cell for it:
there is no legitimate identity (run names cells from the record's
`attempt_dir`, never a directory listing — V7 pin, `run.py:3-5`), and a
guessed one would break summarize's byte-identical rebuild (a cell the
rebuild cannot find = the absence-as-signal shape). Run records the partial
batch under `aborted.json` — never `summary.json` — and re-raises.

```python
# run.py shape
try:
    for _ in range(n):
        record = attempt(...)            # every cell-level outcome returns a
        if record.attempt_dir is None:   # record; usage raises pre-dir (whole-run
            raise RuntimeError(...)      # 2); bugs raise post-dir
        cells.append((record.attempt_dir, record, receipt))
except BaseException as exc:
    _write_aborted(output, requested=n, cells=cells,
                   error=f"{type(exc).__name__}: {exc}",
                   oracle_visibility=manifest.oracle_visibility)
    raise  # summary.json is written only by a completed run
write_summary(output / SUMMARY_NAME, compute_summary(
    cells, oracle_visibility=manifest.oracle_visibility))
```

**Mid-batch failure representation (the kickoff's open question), decided:**
a new `AttemptCode.GRADE_FAILED`, outcome `attempted`, verdict and receipt
absent, patch and transcript present. Not folded into verdict counts (there
is no verdict); not a refusal (the command ran; artifacts were preserved and
admitted). It gets its own `code_counts` row; `attempted + refused == n`
keeps its meaning — `attempted` = command ran and delivered artifacts
admitted to grading, whether grading completed (`OK`) or not
(`GRADE_FAILED`); refused = never admitted.

## 2. T2 — record-before-grade

In `_finish_attempt` (`attempt.py:154`) V9 reorders the admitted path
(today: `grade()` at `:229`, write after at `:247`):

1. Build the admitted-cell record `code=GRADE_FAILED`, `outcome=ATTEMPTED`,
   `verdict=None`, `receipt_path=None`, `message="attempt preserved and
   admitted; grading did not complete"`, artifacts/digests/base-sha/
   command/timeout in hand; write it.
2. `receipt = grade(...)`.
3. Success: rewrite `code=OK`, verdict + `receipt_path="receipt.json"`,
   `message="attempt recorded and graded"`.
4. `SatyrnError` from grade (any subclass — usage-class task/overlay
   corruption is a *task* defect that should cost one cell and its message,
   not the night): rewrite the standing record's `message` with the
   exception and **return** it. The cell is visible, code-counted,
   `regrade`-able.
5. Non-`SatyrnError` (bug/`OSError`) propagates as today; the standing
   record is the recovery artifact.

`attempt` returns a record for every invocation past its usage checks. The
single-attempt CLI maps a returned `GRADE_FAILED` record to exit 3 (verdict
`None`) and prints `record.message` to stderr (parity with today's
`SatyrnError` printing). The CLI's exit-2 class narrows to pre-grade usage
errors — recorded semantic shift.

Schema: `AttemptCode.GRADE_FAILED` (`attempt_record.py:39-49`); a policy row
in `_ATTEMPT_POLICIES`: outcome `ATTEMPTED`, `command_exit` +
`workspace_base_sha` required, `retained_path` forbidden, patch +
transcript required. Verdict/receipt presence — implied by outcome in
`__post_init__` today — becomes explicit `_Presence` fields on
`_AttemptPolicy`: `GRADE_FAILED` forbids them under outcome `ATTEMPTED`,
`OK` keeps them required. No `version` bump (generations = field sets, the
V4/V7 pattern); the loader maps the code through `AttemptCode(...)`.

## 3. T3/T4 — record generation, named summary, disk callers

**`AttemptRecord` gains `timeout: float | None = None`**
(`attempt_record.py:51-70`); `_V9_FIELDS = _V7_FIELDS | {"timeout"}`;
`current_fields` grows by it (`attempt_record.py:285-294`). Every V9
attempt writes its actual timeout; legacy/V4/V7 field sets load with
`timeout=None`; a present timeout validates positive-finite. This makes
summarize-from-disk complete — the record is the single durable per-cell
truth (a `run.json` sidecar would be a second artifact to keep in sync —
rejected on this project's two-systems-under-one-name history; W1 later
collapses generations).

**`Summary` gains required `task: str`, `command: list[str]`, `timeout:
float`.** `compute_summary` derives them from cells — non-empty cells
required — and validates single-valued consistency (one task/command/
timeout; mismatch is a `ValueError` naming cells → operational error).
Task/command come from the *records*, not the `run` request: a cell
directory is `<manifest.name>-<stamp>` (`attempt.py:75-78`), so the
record's task is the operative identity, and the command is the effective
command including any engine-contract suffix — the arm identity T4 wants.
Default-tier fake doubles must carry the requested task/command/timeout;
they are updated with the schema.

**`summarize OUTPUT_DIR`** (`--tasks-root`, default bundled) rebuilds
`OUTPUT_DIR/summary.json` over the exact cells the run's `summary.json`
names — anchored, never a directory scan — so a stray sibling or an
un-appended crash cell cannot change the rebuilt artifact. A directory
whose run aborted is refused: an aborted run writes `aborted.json`
(requested/completed/error plus the completed cells' tallies), never
`summary.json`. A named cell missing from disk, an unreadable anchor,
record, or receipt, or mixed/unresolvable identity is operational (3) —
receipts are never silently re-summarized from the record's verdict
repeat. The rebuild uses the same `compute_summary`/`write_summary` as
`run`; a test asserts run-then-summarize is byte-identical.

**`regrade ATTEMPT_DIR`** (`--tasks-root`) loads `attempt.json`, resolves
the task, re-runs `grade(task_dir, patch, receipt_path)` with defaults
(the same auto-overlay/contamination semantics as the original attempt
grade on hidden tasks), and rewrites `receipt.json` + `attempt.json`
(`code=OK`, new verdict, `message="attempt re-graded"`). Re-scoring
overwrites the receipt (recorded decision: rule 3's point is fixing the
grader and re-scoring the preserved patch; the new receipt names the same
`patch_digest`). Gradeable codes: `OK`
(re-score) and `GRADE_FAILED` (finish); a refusal code is a no-op with a
stderr note and exit 0 (nothing was graded, so nothing re-scores). No
`attempt.json` → not an attempt directory (2); unparseable → corruption
(3); record `attempt_dir` disagreeing with the directory name → refused
(2) — the identity pin keeps regrade from grading a moved/renamed cell.

## 4. T5–T8

### T5 — preservation grading stops auto-overlaying

`grade()` (`grade.py:36`) gains `auto_overlay: bool = True`; the overlay
load + selector swap (`grade.py:67-70`) run only when True. The V6
preservation call (`session_grader.py:122-128`) passes `False`:
preservation = run the declared public selectors on the captured patch with
no overlay (the session grader's own docstring) — hidden tests never
materialized, selectors never swapped. Feature grading passes an explicit
overlay and is untouched. A bare `grade`/`attempt` on a hidden task keeps
auto-overlay (V7's intended behavior; V8's gate depends on it).

Tests (integration — a real grade is a subprocess, per the kickoff
guardrail). Refusal sibling: a new `tests/integration/data/
mini-session-divergent` fixture (hidden session task whose manifest
`expected_test_ids` include a hidden id while `session.json` preservation
selectors name the public test) — under the old call shape (default True)
the preservation grade returns `UNAVAILABLE` (executed hidden ids ⊄
expected preservation set). Success sibling: the same grade with
`auto_overlay=False` returns `PASS` on preserved public
behavior; a bare grade on the divergent fixture still auto-overlays and
annotates contamination; bundled `session-mechanics` preservation stays
green (coinciding lists — unchanged semantics, now without overlay
materialization).

### T6 — stored-file mode check removed (recorded correction)

Delete the `mode & 0o022` refusal in `load_overlay` (`overlay.py:74-79`).
Recorded rationale (V7 §5 amendment + docstring): git stores regular files
as `100644`/`100755` only — group/other bits never reach the index — so the
on-disk mode at load is a property of the checkout umask (002 on
Debian/Ubuntu yields `664` for a clean store), not of the store — the check
refused clean checkouts and could catch nothing git would not normalize.
Real protection stays: overlays never materialize in executor-reachable
paths (absence invariant, `overlay.py:30-47`); materialization chmods
`0o444` after digest verification (`overlay.py:95`). The remaining
stored-file checks — regular file, no symlink, UTF-8, source-path overlap,
safe rel paths, digests — stay.

Tests (default tier — pure filesystem). Success sibling: an overlay tree
chmod'd `0o664` (umask-002 simulation) loads, digests, and materializes
`0o444`. Refusal direction: the remaining checks still refuse (symlink,
non-UTF-8, digest mismatch at materialize, source-path overlap).

### T7 — oracle finds the hook without shadowing the locked env

For a dependency-bearing task today `PYTHONPATH` =
`Path(satyrn_evals.__file__).resolve().parent.parent` (`grade.py:211-213`)
— evals' install location (`src` editable / installer `site-packages`
wheel), which precedes the materialized env in the oracle's `sys.path`. Any
package the installer env shares with the locked env would import from the
wrong place while `resolved_versions` attests the locked env.

Fix: beside the materialized env, grading creates `tmp/hookpath/`
containing **one symlink** `satyrn_evals → Path(satyrn_evals.__file__).parent`
and sets `PYTHONPATH=tmp/hookpath`. `-p satyrn_evals.oracle_hook` resolves
through the symlink to the running evals (editable or wheel — correct in
both); nothing else is on `PYTHONPATH`, so task dependencies resolve from
the locked env exactly as attested. The ambient branch sets no `PYTHONPATH`
(the oracle python is evals' own) — unchanged.

Tests. Default tier: the shim builder is pure — given the package path and
a target dir it lays exactly one symlink; assert the dir's contents.
Integration: two scratch environments — an "evals" package carrying a
sentinel, and a "locked env" whose `site-packages` carries a conflicting
version of a sentinel dependency; an oracle subprocess under
`PYTHONPATH=shim` imports the dependency from the locked env and the hook
from the evals package. Recorded verification (run once at V9
verification, not CI): `uv build` a real wheel into a scratch venv that
also carries a conflicting fastapi; run `grade` on
`agentclinic-repair-plausible-wrong-fix` known-good; assert
`resolved_versions` matches the locked env and the verdict is correct.

### T8 — grading's git runs get the cleaned environment

`git init`/`git apply` (`grade.py:185-190`) are the one place V4's
environment-cleaning discipline was skipped. They now run under the new
`workspace.clean_git_environment` wrapper — it probes Git's routing
variables (`git rev-parse --local-env-vars`, the workspace runner's own
probe at `workspace.py:398-410`) and removes them, pinning
`GIT_TERMINAL_PROMPT=0` — plus the same safety-config argv prefix
(`workspace.py:31-46`). A caller's ambient `GIT_DIR`/`GIT_WORK_TREE`/
`GIT_INDEX_FILE` cannot redirect where grading initializes/applies.
`GIT_SAFETY_CONFIG` is exported for the import (W1 owns the eventual
consolidation).

Tests. Default tier: capture the subprocess env (monkeypatched
`subprocess.run`) — assert no `GIT_*` variable survives and the safety
config is present (ambient Git environment is refused as an influence).
Integration (real git): hostile ambient `GIT_DIR`/`GIT_WORK_TREE`/
`GIT_INDEX_FILE` — known-good grades `PASS` on the graded tree and the
redirected work-tree path is never materialized.

## 5. CLI surface

    satyrn-evals run TASK [--n N] [--tasks-root DIR] [--output DIR] [--timeout S] -- COMMAND...
    satyrn-evals summarize OUTPUT_DIR [--tasks-root DIR]
    satyrn-evals regrade ATTEMPT_DIR [--tasks-root DIR]
    satyrn-evals attempt TASK ...       # surface unchanged (exit-2 class narrows, §2)
    satyrn-evals grade TASK PATCH ...   # unchanged

`summarize`/`regrade` take no `-- COMMAND...` split; they join
`grade`/`capture` under the argparse subparsers (`cli.py:129` pattern), not
the manual `argv[:1]` dispatch used by `attempt`/`run`/`session`. Pure
logic lives in a new focused module `rescore.py` (`summarize_output`,
`regrade_attempt`) so the default tier tests it without argparse.

## 6. Exit codes

`attempt`/`grade`/`run`/`session` keep theirs. New/changed:

- **`summarize`**: `0` wrote `summary.json`; `2` usage — not a dir, not a
  run output dir (no `summary.json`), unknown task, moved cell; `3`
  operational — aborted batch, unreadable anchor/record/receipt, missing
  named cell, mixed cells.
- **`regrade`**: `0` every target graded `PASS`/`FAIL`, or nothing to grade
  (stderr note); `2` no `attempt.json` (not an attempt dir), record
  `attempt_dir` mismatch, unknown task; `3` a target graded `UNAVAILABLE`
  or an unparseable `attempt.json`.
- **`run`**: unchanged. A batch with `GRADE_FAILED` cells completes exit 0,
  the failure visible in `code_counts` (BRIEF rule 4); an abort writes
  `aborted.json`, never `summary.json` (B1).
- **`attempt`**: `GRADE_FAILED` exits `3`, message printed; usage-class
  grading errors surface as `GRADE_FAILED` (3), not as 2 — recorded shift (§2).

## 7. Data shapes

```json
// attempt.json, V9 generation (prior fields plus):
{ "timeout": 900.0,
  "outcome": "attempted", "code": "GRADE_FAILED",
  "message": "attempt preserved and admitted; grading did not complete: <exc>",
  "verdict": null, "receipt_path": null,
  "patch_path": "patch.diff", "transcript_path": "transcript.txt" }

// summary.json, V9 adds (always):
{ "task": "agentclinic-repair-plausible-wrong-fix",
  "command": ["satyrn-engine", "attempt", "…engine-contract.yaml"],
  "timeout": 900.0, "code_counts": { "…": 0, "GRADE_FAILED": 1, "OK": 7 } }
```

House style: `type` aliases for recurred shapes; `GRADE_FAILED` flows
through the enum-keyed tallies (`code_counts` keys every `AttemptCode`
value — adding it updates every Summary constructor mechanically).

## 8. Non-goals

- V10–V13 and W1 — none start; V9 touches only the loop-integrity files.
- Session re-scoring: `regrade`/`summarize` operate on attempt cells;
  `load_session_record` gains no caller (its re-score story belongs to the
  phase that consumes sessions).
- T10/T11/T13 fixes; run-resume (partial summary + V5d smoke is the
  recovery story); any model run, run-time seam change, or new task
  fixture; the claims layer.
- `regrade` of a refused cell (nothing graded, nothing to re-score) —
  stated in CLI semantics, not a recovery path.
- W1's consolidation (git runners, env cleaning, record generations): V9
  reuses what exists and leaves consolidation to W1, which depends on V9.

## 9. Done-when

1. `GRADE_FAILED` exists with its policy; a grading `SatyrnError` yields a
   returned `GRADE_FAILED` record (message carries the exception, no
   receipt, regrade-able) and a successful grade rewrites `OK` with verdict
   + receipt — refusal/success siblings, default tier.
2. Records carry `timeout`; legacy generations load with `timeout=None`;
   stored-record fixtures still parse.
3. `run` writes `summary.json` only on completion (an abort writes
   `aborted.json`); a batch with one grading failure completes with all n
   cells and a correct `GRADE_FAILED` count (default tier, doubles).
4. `Summary` names task/command/timeout; `compute_summary` refuses
   inconsistent/empty cells; all constructors updated.
5. `summarize` rebuilds `summary.json` byte-identically over the run's own
   cells (strays ignored, aborted runs refused); each refusal has a
   success sibling.
6. `regrade` re-grades and rewrites receipt + record; `GRADE_FAILED` → OK;
   refusal code = no-op; identity mismatch refused. Default tier + one
   real fake-seam integration pass.
7. T5 pair green (divergent fixture: `UNAVAILABLE` under old shape, `PASS`
   under `auto_overlay=False`); bare auto-overlay and bundled fixtures stay
   green.
8. T6: a `0o664` tree loads and materializes `0o444`; remaining refusals
   fire; V7 §5 amendment note recorded.
9. T7: shim holds exactly one symlink; two-env subprocess test;
   wheel-install demonstration recorded, output in the V9 record.
10. T8: grading's git subprocesses run under the cleaned environment (no
    ambient routing vars) with the safety config; hostile ambient git
    leaves grading correct.
11. `DEFAULT_TIMEOUT == 900.0`; no test asserts 30.
12. T9 stated (BRIEF rule 4 note, trust-boundaries, this spec); a
    default-tier test refuses a stale forged result file.
13. Default tier no-model/no-network/no-subprocess (tripwire green); every
    refusal test has its success sibling; 100% branch gate; ruff/pyrefly/
    lint-docs/`git diff --check` clean. Docs current: formats.md, usage.md,
    the run guide, ROADMAP row, V7 §5 + V5b notes.

## 10. Reviewable slices (plan files)

1. **Record schema + attempt path** (P1, P2) — `GRADE_FAILED` code/policy/
   presence; `timeout` generation; record-before-grade; `DEFAULT_TIMEOUT`;
   CLI + schema ripple.
2. **Summary + run** (P3) — Summary arm naming; `compute_summary`
   consistency; run boundary + partial-summary abort.
3. **Disk commands** (P4, P4b) — `summarize_output`, `regrade_attempt`,
   `rescore.py`, CLI wiring, exit codes, fake-seam round trip.
4. **Grade-path fixes** (P5, P5b) — T5 auto-overlay opt-out + divergent
   fixture; T6 mode-check removal + V7 amendment; T7 shim; T8 git env.
5. **Docs + record** (P6) — T9 statement (BRIEF, trust-boundaries, spec);
   formats/usage/guide updates; ROADMAP row; V5b + V7 amendments;
   verification record in `docs/sdd.md`.

## 11. Verification record shape

V4/V6 pattern (`docs/sdd.md`): default-tier counts; integration-tier
command; 100% statement-and-branch gate; ruff/pyrefly/lint-docs/`git diff
--check`; named evidence — T7 wheel demo, T5 divergent pair, and a
`regrade`/`summarize` round trip over a real fake-seam run.

## 12. Evidence and recomputation

Anchors (HEAD `dd7a65e`): run loop `run.py:35-50`; writes/grade call
`attempt.py:226,229,247`; refusal `attempt.py:100-121`; policy/loader
`attempt_record.py:15-33,39-49,277-294`; summary `summary.py:25-34,74,116`;
auto-overlay `grade.py:67-70`; git runs `:185-190`; oracle env `:208`;
PYTHONPATH `:211-213`; mode check `overlay.py:74-79`, absence `:30-47`,
materialize `:95`; preservation call `session_grader.py:122-128`; hook
loader/freshness `verdict.py:37-40`; default timeout `workspace.py:28`;
env cleaning `workspace.py:213-224`; safety config `workspace.py:31-46`;
CLI dispatch `cli.py:64,129`.

One-command checks (repo root): `grep -n "GRADE_FAILED"
src/satyrn_evals/attempt_record.py`; `git diff --stat` (uncommitted per
maintainer-controlled commits); the T5 pair and T7 wheel demo per §9.