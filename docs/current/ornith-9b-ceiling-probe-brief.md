# Brief: where does bare Pi on Ornith 1.5 9B stop?

**Written 2026-09-13 by Fable, for a fresh agent. Self-contained.** It
authorizes preparation, one pre-run record, one bounded Baseline-only live
probe of at most twelve cells, and a result document. Nothing else. The
maintainer's budget grant is recorded at the end of this file; do not run a
cell until it is present.

## Why this probe exists

The [pathology probe](ornith-9b-pathology-probe-result.md) found that bare Pi
on Ornith 1.5 9B does not exhibit the three mechanical pathologies release one
was going to remedy: 0, 1 and 0 of 8. The maintainer's decision on reading it,
2026-09-13: **Ornith 9B is the release-one target anyway**, because it fits
the 16 GB contributor laptops, solves what it is given, and does so in under a
minute per repair. The release-one claim therefore changes shape, from
"the Engine removes gemma's pathologies" to **"the Engine takes Ornith 9B past
the complexity at which bare Pi stalls."** Nobody has measured where that is.
Every Ornith run so far was `misleading-locus` at rung `R1`, a single-seam
repair with the failing check named, plus four `complaint-lifecycle` sessions.

This probe locates the first ceiling. It does not build anything toward it.

**Informed selection, disclosed.** The blocks below were chosen because gemma
Baseline demonstrably fails on them (`ROADMAP.md`, "State and dependencies":
`depth-3` at `R1`, "no baseline attempt passes in any recorded batch"), or
because the first Ornith cells already cracked there (`complaint-lifecycle`
phase 4: two `fail` receipts in four `COMPLETE` sessions on 2026-09-13). None
of those counts pools with this probe's denominator.

## The three blocks, and why these rungs

The repair tasks ship four prompt rungs. `R0` shows nothing about the failing
checks; `R1` names the failing checks and quotes their assertion text but not
the defect's location; `R3` names the location and the fix. For a ceiling
probe **`R1` is the only informative rung**:

- `R3` is the guided rung. gemma Baseline passes `depth-3` at `R3` 6 of 6. A
  pass there says nothing about a ceiling.
- `R0` on `depth-2` and `depth-3` is unobservable by construction: the
  workspace's public suite sees only the redirect seam, so the model fixes
  what it can see, finishes on a green suite, and the hidden checks fail. No
  developer wrote anything down that an Engine could carry. A failure at `R0`
  is not a ceiling the Engine can address; it is a task with missing
  information.
- `R1` is what a developer actually has: a CI report naming the failing
  checks and their assertions. gemma Baseline is 0 for N here on `depth-3`,
  while 33 of 36 one rung down in complexity (`misleading-locus` `R1`). That
  gap is the ceiling shape release one needs, if Ornith has it too.

| Block | Task | Rung | Cells | What a failure here means |
|---|---|---|---|---|
| A | `agentclinic-repair-depth-3` | `R1` | 4 | Three seams across `models.py`, `app.py`, a template; two are invisible to the workspace suite. The gemma wall. |
| B | `agentclinic-repair-depth-2` | `R1` | 4 | Two seams, one invisible. The rung between `misleading-locus` and `depth-3`. |
| C | `agentclinic-complaint-lifecycle` | none | 4 | Four ordered build phases over one growing checkout; the maintainer's real use case. Phase 4 adds identity and lifecycle to existing code. |

The maintainer's approved sketch had Block A at `R3` and Block B at `R0`. Both
were changed to `R1` for the reasons above; the change is Fable's and is
recorded here so the maintainer can reverse it before the grant is used.

## Question and decision rule (frozen here, before any inference)

**Question.** In each block, how many of four Baseline cells on Ornith 1.5 9B
fail?

**A cell fails** when, read from retained evidence only:

| Kind | Fails when | Read from |
|---|---|---|
| repair (A, B) | `receipt.json` `verdict` is not `pass`, **or** `attempt.json` `code` is not `OK` | the cell's attempt directory |
| session (C) | any step's `feature_verdict` is `fail`, **or** any step's `outcome` is not `settled`, **or** `session-record.json` `code` is not `COMPLETE` | `session-record.json` |

A `MODEL_ERROR` (5xx, out of memory) is an infrastructure event: the cell is
reported as **unscored**, not as a failure, the cause is diagnosed and
recorded, and the cell is not re-run (`n = 12` is frozen). Denominators in the
rule below count scored cells only, and the result states every unscored cell.

**Decision rule.** A block is a **ceiling** if **2 or more of its 4 scored
cells fail**. Report per block. Then:

- If one or more blocks is a ceiling, the **lowest-complexity ceiling block**
  (B before A before C, by the ordering in the table) is the recommended
  release-one workload, because it is the smallest gap an Engine has to
  close. Name it; do not design toward it.
- If no block is a ceiling, say so plainly. Ornith 9B has no measured ceiling
  on this task fleet, and the next probe needs harder tasks; list candidates
  by name only. Do not run any.

**Also record, per cell, as measures (not diagnostics).** These are the
budget side of the maintainer's question ("it isn't just 6/6, it's also
budget") and the release-one eval will need the same columns:

| Measure | Read from |
|---|---|
| wall clock, seconds | the launcher's `run.log` start/end per cell |
| turns | `turn_start` events in the transcript (repair) / sum of steps' `turn_count` (session) |
| tool calls | `tool_execution_start` events, one per call, payload-unwrapped for session cells |
| input and output tokens | `scripts/usage_totals.py <transcript>` for repair cells. For session cells the stream is wrapped (`event` / `session_started` / `step_finished`) and `usage_totals` refuses it; unwrap each `event` payload and sum `message.usage` over `message_end` events exactly once each, per that script's docstring. Record the unwrap as instrument debt in the result |

**Diagnostics, kept apart from the measures.** The pathology probe's reviewer
noticed **same-file mutation churn** in the session cells: `app.py` edited or
written 8 to 16 times per session with every payload distinct, and churn did
not predict the phase-4 failures. Record per cell: number of `edit` plus
`write` calls per target path, and the count of failed tool results. Carry the
recompute script. State in the result that these are exploratory, that they
did not enter the rule, and that nothing here says whether churn is a problem.

**Not asked.** Any comparison with gemma or between arms; any Engine arm; any
Fisher test or interval; any sentence about why Ornith fails where it fails.
Twelve cells support per-block presence/absence of a ceiling and nothing finer.

## Frozen conditions

| Field | Value |
|---|---|
| Model | `omlx/Ornith-1.5-9B-MLX-8bit`, served at `127.0.0.1:8001` — **verify with a live completion, never `/v1/models`**; if `message.model` in any transcript is not `Ornith-1.5-9B-MLX-8bit`, **stop and report — do not substitute** |
| Inference | the model's own settings from `arms/baseline-ornith15-9b.json` (context 262,144; max tokens 32,000; temperature 0.6 …). Record them; do not normalise |
| Arm | Baseline only, `satyrn-evals-attempt-pi` / `satyrn-evals-session-pi`, tools `read,bash,edit,write`, pi `0.85.1` |
| Repeat limit | **off**, as in the pathology probe; a limit would change the condition between the two probes |
| Block A | `satyrn-evals run agentclinic-repair-depth-3 --n 1 --rung R1 --timeout 900 --attempt-timeout 1200` |
| Block B | `satyrn-evals run agentclinic-repair-depth-2 --n 1 --rung R1 --timeout 900 --attempt-timeout 1200` |
| Block C | `satyrn-evals session agentclinic-complaint-lifecycle --step-timeout 600` |
| Order | A1 B1 C1 A2 B2 C2 A3 B3 C3 A4 B4 C4, serial, one at a time |
| Output root | `~/satyrn-smokes/2026-09-14-ornith9b-ceiling-probe/` (must not exist) |
| Wall-clock stop | 2 h from the first cell; unreached cells reported as not-run. Expected use: about 1 h (session cells ran 542–663 s each on 2026-09-13; repair cells 34–71 s, though `depth-3` may run longer) |

The exact argv shapes are in the retained
`~/satyrn-smokes/2026-09-13-ornith9b-pathology-probe/schedule.json` and
`launch.sh`; reuse that launcher with the three blocks substituted. Verify
flags against the adapter parsers, not `--help` (both adapters reject
`--help`; see the pathology probe's pre-run record, "Preflight performed").

## Operate here

Main checkout `/Users/pauleveritt/projects/pauleveritt/satyrn-evals`, `main`
at the commit that carries this brief. All three tasks, both adapters and the
Ornith arm file exist there. Create a worktree per
`superpowers:using-git-worktrees` at `.claude/worktrees/ornith-ceiling-probe`,
branch `worktree-ornith-ceiling-probe`, base `main`. Commit the pre-run record
and the result there. **Do not touch** `.claude/worktrees/release-one`,
`.claude/worktrees/ornith-pathology-probe`, any other worktree, or
`satyrn-engine`. **No merge to `main`.** Phase 0 of the restart is running
concurrently in `release-one`; it uses no inference and shares no files with
this probe.

## Sequence

1. **Preflight, before the record.** Clean tree; recompute all three
   task-tree digests with the walk in the pathology probe's result ("Task-tree
   digests, re-verified"); confirm both adapters resolve; one live completion
   from the model; no measurement-shaped Pi process running
   (`scripts/preflight_processes.py`); output root absent.
2. **Pre-run record**, `docs/current/ornith-9b-ceiling-probe-pre-run-record.md`,
   in the shape of `docs/current/ornith-9b-pathology-probe-pre-run-record.md`:
   this file's question, rule, conditions and digests, the exact commands, the
   evals revision, retention paths. Add it to `docs/current/index.md`. Commit.
   **Stop until the budget grant below is present.**
3. **Run** the twelve cells serially with the launcher: `schedule.json`
   first, per-cell start/end timestamps in `run.log`, model loadability check
   by live completion, wall-clock stop, refusal to overwrite a non-empty cell
   directory.
4. **Read** the measures per cell from retained artifacts. Count from events,
   never `grep -c`. Carry the recompute command beside every number.
5. **Result**, `docs/current/ornith-9b-ceiling-probe-result.md`: a 12-row
   table (cell, block, task, rung, outcome code, verdict or per-phase
   verdicts, seconds, turns, tool calls, input tokens, output tokens), the
   per-block fail counts of 4, the rule applied verbatim, the diagnostics
   table, missingness, "what this does not establish", digests re-verified.
   Add it to the toctree. Commit. Report to the maintainer in under 200 words:
   the three block counts, which block if any is the recommended workload,
   anything that stopped the run.

## Loop rules

- **Established infrastructure failure only** stops launches: model not
  loadable, wrong observed `message.model`, missing executable, broken
  artifact path. A fail verdict, a timeout, a refusal or a scope violation is
  the observation this probe exists for; it is kept and counted, never
  replaced.
- `n = 12` is frozen. No extension, re-run or replacement for any result.
- Do not start any other inference on this machine while the launcher runs.

## Review

Sonnet implements; Opus reviews the pre-run record before cell 1 and the
result before it is called accepted. **No Fable review unless the maintainer
asks.** Opus's review checks: the rule was applied as written; every count has
its recompute command; the rungs are `R1` in both repair blocks; the
diagnostics are labelled as such; no sentence compares Ornith with gemma or
one arm with another.

## Hard stops

- No Engine arm, no engine change, no architecture claim, no design rewrite.
- No pooling with the pathology probe, the 2026-09-09 Ornith run, or any
  gemma run.
- No instrument change larger than reading the evidence; where `census`,
  `usage_totals` or V10 refuse a stream, count by hand from events and record
  the debt.
- The run ends with the result document.

## Budget grant

**Granted 2026-09-13 by the maintainer, in session** ("I approve all 3 of
your points", approving the ceiling probe, the spend, and running it
alongside Phase 0): `n = 12` cells under the frozen conditions above, on
**exclusive GPU** for the duration of the run, unattended overnight. Cell 1
may start once the pre-run record is committed and reviewed.
