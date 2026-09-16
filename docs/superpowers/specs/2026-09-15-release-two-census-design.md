# Release two, R0 — the pathology census (design)

**Status:** design approved by the maintainer 2026-09-15 on all six
decisions listed in section 9; drafted by Fable at the maintainer's request.
Bound by `2026-09-15-release-two-r0-constraints.md` (harness validity, then
task validity, then diagnosed admission, then the offline counterfactual,
then a build). This document supersedes the 2026-09-15 direction "ship the
Engine as a product with no outcome claim" recorded in `STATE.md` and
`ROADMAP.md`; the maintainer withdrew that direction the same day because a
release whose page says the Engine does nothing good is not worth shipping.
Whether release two ships anything is decided after this census, not before.

## 1. Question

On the fixed harness, where and why does bare Ornith 1.5 9B fail on five
medium tasks, and where does it stop on its own?

Baseline only. No Engine cell runs. The Engine's targets for release two are
re-derived from these cells, so nothing about the Engine is designed, planned
or built until section 7 has run.

## 2. Why this and not a comparison

Release one's negative (`2026-09-15-release-one-outcome.md`) rests on three
ceiling tasks of which two measured task defects. The whole valid evidence
for "is there an Engine-reachable failure class" is five docs-linter cells
across both arms, of which two reached a hidden-suite pass and kept working
until the budget tripped (`evidence/2026-09-15-finishing-counterfactual/run-2/`).
Harm from stopping at green was 0 across 43 cells graded at every turn. The
pathologies the Engine was built for (read-lock, no verification, scope
violation) appeared on Ornith at 0 of 8, 1 of 8 and 0 of 8, and guards 1–3
never fired on a live ceiling cell. The clean-harness failure shapes are
different: one whole-budget runaway turn, 8–18 exploration turns before the
first edit, one 4–12k planning think, one-hunk edits, and 10–20 turns of
ceremony after a passing state. None was measured at a denominator.

A census with a denominator is the R0 §1.3 step ("admission with
diagnosis"). It decides which of three release-two shapes is honest:

| the census shows | release-two claim | Engine work |
|---|---|---|
| finishing or ceremony in ≥ 30% of build cells on ≥ 3 tasks, and Baseline within 32k at ≤ 2 of 6 | outcome within 32k, finish-on-green plus hygiene | built only after the offline counterfactual clears the win threshold at the stated power |
| Baseline stops on its own with a pass by 48k on most build cells | cost at equal outcome (turns, tokens, seconds), no losses; outcome within 32k as a declared secondary | finish-on-green, guard 4, context seeding; a paired test per task |
| capability-bound failures dominate at 48k on valid prompts | 9B is the wrong model for medium work; the honest release is the harness plus a numbered ceiling | none at 9B |

## 3. Harness changes before the night (R0 §1.1)

Each item lands with fixture tests both directions in the default tier (no
model, network or subprocess), Opus-reviewed, committed on its own, before
the first record is written. Nothing else changes in the harness.

1. **Per-turn output cap: 16,000 tokens, both arms.** `inference.max_tokens`
   in `arms/*-ornith15-9b.json`, mirrored into the cell's Pi `models.json`
   and the oMLX entry; `scripts/preflight_settings.py` already refuses a
   disagreement. Semantics, verified in Pi 0.85.1's agent loop and declared
   here: a length-cut turn that contains tool calls fails them all with a
   truncation notice and the loop continues; a length-cut turn with no tool
   call ends the session; Pi's compact-and-retry path cannot trigger because
   the server cap equals Pi's. Why 16k: every passing retained cell's
   biggest turn was ≤ 6k, every failed build cell's 9–14k, and the two
   runaway turns were 32,000; 16k removes the whole-budget runaway and cuts
   no observed productive turn. Fixture: a fake transcript with a
   length-stop plus tool calls is counted and continues; the tripwire still
   sums `usage.output`.
2. **Tripped worktrees are graded.** At `BUDGET_EXCEEDED` teardown the diff
   against `workspace_base_sha` is harvested and graded into
   `tripped_verdict`, a declared secondary that is never a pass. Fixture: a
   tripped worktree holding a passing state grades `tripped_verdict: pass`
   with `verdict` still null; a tripped worktree with no patch grades
   `unavailable`.
3. **The wall-clock backstop is a record field.** Today `COMMAND_BACKSTOP =
   1800.0` in `launch_cell.py`; it becomes `command_backstop_s` on the run
   record, gated like the other fields, default 1800. The census records
   3,000.
4. **k = 3** stays: run 2 measured 41 tok/s per stream at k = 1 and about 89
   tok/s total at k = 3 on 1,932 live completions.

Under "Evidence has a harness", item 1 re-opens every retained decision whose
cell had a length-stop (the two depth-3 runaways); item 2 re-opens none (it
adds a field). The re-opened decisions are re-derived by this census.

## 4. Task changes and task validity (R0 §1.2)

| task | shape | rung for the census | change before the night |
|---|---|---|---|
| agentclinic-repair-depth-3 | repair, 3 seams | **R2**, new | R1 text plus pytest's own explanation of the third failure: "assert None is not None, where None = first.timestamp.tzinfo". Assertion text, not location; R1 stays in the manifest as evidence |
| selfhost-run-record-gate | build | R1-plan, fixed | two prompt edits through the mechanism below: `RunRecordError` is defined in `run_record.py` and subclasses `UsageError` imported from `errors.py`; the "Gate rules" heading becomes validation rules enforced by `load_run_record` and re-checked by `gate` |
| selfhost-docs-linter | build | R1-plan | none expected; the validity check decides whether `pyproject.toml` (cell 147562's allowlist trip) joins `ignored_paths` or `source_paths` |
| selfhost-cell-loop | build, held-out in release one | R1-plan | validity check only |
| selfhost-speed-probe | build, held-out in release one | R1-plan | validity check only |

**Prompt-edit mechanism.** The task spec under `tools/task_specs/` gains
`prompt_edits`: a list of `{old, new, reason}` applied to the cut R1-plan
prompt in order, each `old` required to occur exactly once. `cut_task.py`
records the applied edits in the manifest beside the plan's path, heading and
commit, so the prompt's provenance is the historical plan plus a named
patch. The plan document is never edited. Qualification refuses a manifest
whose recorded edits do not reproduce the prompt from the plan.

**Task validity check, recorded per task in the manifest as
`validity: {by, commit, passed}`.** A Sonnet agent receives the census prompt
and the base tree only, never the plan's code, the overlay or the known-good
patch, and writes a solution; the hidden suite is run against it offline.
A task whose prompt-only solution fails the hidden suite is a generator
defect and does not run in the census until fixed. The check runs for all
five tasks, including the two the release-one review called defective, so
the fixes are proven rather than assumed. No model inference on the GPU:
the agent is a cloud model working from text.

After the changes: re-cut the two edited tasks, `cut_task.py check` exit 0
for all five, `satyrn-evals qualify` ok for all five, digests recorded in the
census records. The floor tasks and `agentclinic-repair-depth-2` are not
re-cut and do not run.

## 5. The night

Five records, one per task, Baseline arm, `--purpose admission`, isolated,
`mode: batch`, chained through `--previous-result` from the last committed
result, launched in sequence by a script of the `admit.sh` shape. Frozen and
committed in daylight; the maintainer starts the script.

| task | rung | n | token budget | turn budget | backstop | k |
|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | R2 | 6 | 48,000 | 72 | 3,000 s | 3 |
| selfhost-run-record-gate | R1-plan | 6 | 48,000 | 72 | 3,000 s | 3 |
| selfhost-docs-linter | R1-plan | 6 | 48,000 | 72 | 3,000 s | 3 |
| selfhost-cell-loop | R1-plan | 6 | 48,000 | 72 | 3,000 s | 3 |
| selfhost-speed-probe | R1-plan | 6 | 48,000 | 72 | 3,000 s | 3 |

Thirty cells. **Why 48,000 and not 32,000:** a 48k cell contains the 32k cell
as a prefix, and the run-2 trajectory tooling grades every mutation turn, so
the 32k reading is recovered offline at no extra cells; what 48k adds is
where Baseline stops on its own, which decides the claim shape in section 2.
The budget is a census setting declared here before any cell runs; the
release-two comparison budget is chosen in section 8 from the census, before
any Engine cell.

**Schedule.** From the retained nights: at 32k a tripping ceiling cell ran
about 1,780 s of wall clock at k = 3 and four cells took 40–47 minutes. At
48k a tripping cell runs about 1.5× longer, so about 15 minutes effective
per cell and 30 cells in 7–8 hours. If a record caps, the launcher resumes
it on the next launch of the same record; nothing restarts from zero and no
cell is replaced.

**Stop rule:** established infrastructure failure only (server unreachable,
wrong served model, preflight hunt hit, missing executable). Outcome-shaped
signals — budget trips, length-stops, timeouts, refusals — are the
measurement and never stop a record.

**Decision rule on the record:** none for outcomes. Admission for release two
is decided in section 8 from the classified table, not from a pass count.

**Not in the night:** floor cells (the cap cannot touch a cell whose biggest
turn is 5k; the fixtures prove the mechanism), Engine cells, a thinking-budget
condition (held until the census says big-think cells dominate; about 8
cells if wanted later), the warm condition.

## 6. What every cell records

Beyond the existing evidence block: `tripped_verdict`; length-stops (assistant
messages with `stopReason: length`); seconds from first to last tool event and
whole-attempt seconds; exploration turns before the first source mutation;
biggest turn's output tokens and its share; turns and tokens at the first
hidden-suite pass state (offline); own-green turn (offline); spend after the
pass state; self-stop turn and tokens when the cell ends on its own. All
counted from `tool_execution_start`, `message_end` and `turn_start` events,
one per event, with the recompute command beside every number.

## 7. The day after: classification and the counterfactual (R0 §1.3–1.4)

Every cell gets a turn-by-turn reconstruction (the run-2 scripts
`audit.py`, `trajectory.py`, `triggers.py`, `q3stats.py`, pointed at the new
night) and one binding-constraint class:

| class | meaning |
|---|---|
| information | the prompt omits a fact the hidden suite requires; no cell finds it |
| ambiguity | the prompt admits a reading the hidden suite rejects |
| capability | the cell has the facts, spends its budget and never reaches a pass state |
| budget | a pass state is reached late and the 32k line falls before it |
| finishing | a pass state is reached within 32k and the cell keeps working past the line |
| runaway | a length-stop turn precedes the failure |
| hunting | a root search or a bounded command precedes the failure |
| allowlist | a passing state exists but a file outside `source_paths` voids the patch |

A cell can carry a primary class and secondaries; the primary is the one
whose removal would have changed the verdict at 32k, argued from the
reconstruction and cited by turn. Information and ambiguity are task defects
under R0 §2 and are fixed or the task leaves the set; they are never claimed
against.

Then the finish-on-green counterfactual from `2026-09-15-release-two-finishing-counterfactual.md`
runs over the census cells at the 32k line, both readings recorded as before:
run 1's pre-registered rules and run 2's replay method, giving rescues, harms
and net per task under each.
Only remedies whose effect begins at or after the measured point are scored
offline; context seeding, edit batching and the per-turn cap are not, and
are measured on development cells later if built.

Output: one result page per task, written by the launcher into the results
directory, and one census page in `evidence/2026-09-16-census/` with the
classified table, its scripts and a recompute block. Nothing pools across
tasks.

## 8. The decision, taken by the maintainer in the R0 sitting after section 7

1. Pick the row of section 2's table the census supports, or state that none
   does.
2. Fix the release-two ceiling set: tasks whose Baseline within-32k rate is
   ≤ 2 of 6 and whose primary classes are budget, finishing, runaway or
   hunting. A task whose primary class is information or ambiguity is fixed
   and re-admitted or dropped.
3. Fix the comparison budget from the self-stop distribution, and the win
   rule and its power against a stipulated effect taken from the
   counterfactual, never from a hoped-for rate.
4. Only then: the Engine remediation list, each item naming the class it
   targets, the census cells that justify it, and its offline estimate.

## 9. Decisions approved 2026-09-15

1. Census before any Engine work; the claim shape is decided after it.
2. Per-turn cap 16,000; census budget 48,000 tokens, 72 turns, 3,000 s.
3. run-record-gate fixed through the recorded prompt-edit mechanism.
4. depth-3 kept, at a new rung R2.
5. The thinking-budget probe is held until the census motivates it.
6. Fable drafts this spec; Opus writes the plan and reviews; Sonnet
   implements; no haiku.

## 10. Rules carried

Two-uid isolation for every cell; the launcher is the only path to a model;
records frozen and committed in daylight; no Docker, sandbox or wrapper
process; results and reviews written only by their tools; commits at task
boundaries with explicit paths; never push, merge or amend. Unattended is for
building and for this pre-registered night; deciding happens attended.
