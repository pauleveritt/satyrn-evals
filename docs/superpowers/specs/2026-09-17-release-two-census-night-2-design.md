# Release two, R0 — census night 2: the third task and the replacements (design)

**Status:** design approved by the maintainer on the four decisions in
section 8; drafted by Fable at the maintainer's request. Bound by
`2026-09-15-release-two-r0-constraints.md` and by the census design
`2026-09-15-release-two-census-design.md`, whose harness, budget line and
classification scheme this night reuses unchanged. Baseline only. No Engine
cell runs; the Engine night is the one after this, once finish-on-green is
built under R0 §1.4's estimate (section 2).

## 1. Question

Does a third medium-build task show the finishing shape night 1 found on
run-record-gate and docs-linter, and where does Baseline stop on its own
when the machine is quiet?

## 2. What night 1 settled, and what it left

Night 1 (`records/2026-09-16-census-*.result.json`, classifier outputs under
`evidence/2026-09-16-census/<task>/`, evals `ebfd5f1`) read at the
pre-registered 32,000-token, 48-turn line:

| task | pass at 48k | pass at 32k/48 | reached a pass state within the line | finishing | runaway | timed out |
|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3, R2 | 6/6 | 6/6 | 6 | 0 | 0 | 0 |
| selfhost-run-record-gate | 2/6 | 1/6 | 5 | 4 | 0 | 3 |
| selfhost-docs-linter | 4/6 | 1/6 | 4 | 3 | 0 | 0 |
| selfhost-cell-loop | 0/6 | 0/6 | 0 | 0 | 3 | 3 |
| selfhost-speed-probe | 0/6 | 0/6 | 0 | 0 | 2 | 3 |

"Finishing": a hidden-suite pass state inside the line, not stopped at.
"Runaway": the cell ended on one 16,000-token turn with no tool call.
Stopping at own-green harmed no cell in 30. Under run 2's method at the 32k
line it rescues 4 of the 12 medium-build cells against a Baseline of 2 (run 1's pre-registered rules count 0, with 4 cells unmeasured). *Corrected 2026-09-17: the first draft said 5, a hand count made before the classifier read the 32k line; the regenerated tables at `evidence/2026-09-16-census/<task>/table.md` are the producer.*

Three consequences bind this night:

1. **depth-3 at R2 is a floor task.** The release-one depth-3 leg was a rung
   defect. The claim table in the census design is now judged over build
   tasks only, and the census page says so rather than letting the
   denominator shrink silently.
2. **The claim table's first row is met on two build tasks, not three.** A
   third medium-build task is the missing input to the R0 sitting; without it
   no outcome claim is sized.
3. **Nine cells were cut by the 3,000 s backstop before the token budget,
   on a machine the maintainer reports was shared.** Decode ran at 14–26
   tok/s per stream against run 2's 30 on a quiet machine. Every timed-out
   cell had passed 30,000 tokens, so the 32k-line reading is complete; what
   is lost is the self-stop distribution beyond it. Under the comparison
   policy those nine cells stay in their denominators as recorded; a
   replacement is a separately authorized record reported beside them.

The Engine work R0 §1.4 now permits, and this night does not run: a
finish-on-green steer keyed on `self_test` green after a source mutation
(offline estimate: 4 rescues of 12 under run 2's method, 0 under run 1's, harm 0; corrected 2026-09-17), and reading the completion gate
against the five runaway cells, whose `agent_end` without a tool call is the
gate's trigger. Both are built and measured after this night, on their own
spec.

## 3. Day work before the night (attended, no GPU)

1. **The third candidate.** Opus surveys the Phase 2a, 2b and 2c plans under
   `docs/superpowers/plans/` for build-shaped tasks not yet cut, in the
   run-record-gate size class: one source module plus its test module, 15 to
   20 hidden tests, a public suite that runs in under 40 s, no file creation
   outside `Files:`. Proposes two with the plan heading, base and good
   commits, and hidden-test count; the maintainer picks one. Cut with
   `tools/cut_task.py`, `check` exit 0, `satyrn-evals qualify` ok, then the
   R0 §1.2 validity check exactly as the census ran it: base tree and prompt
   only, leak tells, artefacts preserved under
   `evidence/2026-09-17-census-2/validity/<task>/`, `validity` block in the
   manifest naming the model that ran. A candidate that fails validity gets
   a recorded prompt edit only for a fact the plan's stripped code stated;
   otherwise it is dropped and the second proposal is cut.
2. **Classifier: the 32k-line actual.** `evidence/2026-09-16-census/classify.py`
   compares own-green triggers at the 32k/48 line against the harness
   verdict at the record's 48k budget, so a cell that passed between the two
   lines counts as no rescue. Fix: `actual` at the line is `verdict == pass`
   and `tokens <= 32,000` and `turns <= 48`; the 48k verdict stays as a
   second column. Both readings printed; fixture tests both directions;
   night 1's five tables regenerated and recommitted with the change named.
3. **Decode rate per cell, offline.** No harness change. The classifier
   gains a `decode_tok_s` column read from the oMLX server log by the cell's
   time span, the way `run-2/serverlog.py` did, so contention is a number on
   the row. Night 1's tables carry it too.
4. **No other change to the harness, the arms, the five night-1 task trees,
   or the launcher.** The per-turn cap, tripped harvest, backstop field and
   evidence fields run as frozen at `b2720a4`.

## 4. The night

**Amendment 2026-09-17, maintainer's decision.** The Task 1 survey found no
candidate in any plan on the branch (`.superpowers/sdd/2026-09-17-release-two-census-night-2/task-1-report.md`
and `task-1-extended-report.md`). The third task is authored under
`2026-09-17-release-two-authored-task-design.md` and admitted on its own
later night; record 1 below is withdrawn from this night, which runs the
three replacement records only, nine cells, in the order 2, 3, 4. Section
1's question is answered by that later night; this night answers the
self-stop question and completes the contended denominators.

Four records as first written (record 1 withdrawn by the amendment), Baseline arm, `--purpose admission`, isolated, `mode: batch`,
k = 3, 48,000 tokens, 72 turns, **backstop 4,800 s**, chained from
`records/2026-09-16-census-selfhost-speed-probe.result.json`, launched in
this order by `scripts/census_night_2.sh` (the night-1 script with the task
list and record prefix as its only differences):

| order | record | task | n | why |
|---|---|---|---|---|
| 1 | `2026-09-17-census2-<candidate>` | the third candidate | 6 | admission with diagnosis |
| 2 | `2026-09-17-census2-selfhost-run-record-gate` | run-record-gate | 3 | replaces the three contended timeouts (470484, 533788, 609675) |
| 3 | `2026-09-17-census2-selfhost-cell-loop` | cell-loop | 3 | replaces 631530, 918779, 320931 |
| 4 | `2026-09-17-census2-selfhost-speed-probe` | speed-probe | 3 | replaces 529092, 941646, 944467 |

Nine cells after the amendment. **Why 4,800 s:** on a quiet machine 48,000 tokens decode in
about 1,600 s and the suite-heavy tasks spend 1,000–1,700 s in their own
test runs, so 3,000 s bound the wall clock before the token budget; 4,800
lets the budget bind first with margin. The gate holds: 4,800 + 300 ≤ 240 ×
60. Estimated wall clock about five hours at k = 3.

**Replacement records** carry `authority: "replacement for contended cells
<ids> of 2026-09-16-census-<task>; originals stand in their denominator and
this record is reported beside them, never in their place"`, and the same
`decision_rule` as night 1 (none for outcomes). The census page reports
each task's night-1 six and night-2 three as two rows.

**Order and reach.** Records run in the order above. A record the night does
not reach stays unlaunched and is launched, if at all, in a later sitting
under its own authority line; nothing is resumed silently.

**Stop rule:** established infrastructure failure only. Timeouts, budget
trips, length-stops and refusals are the measurement.

**Precondition, the maintainer's:** nothing else runs on the machine from
launch until the script exits. If that cannot be promised for the whole
night, only record 1 is launched and records 2–4 wait for a night that can.
The decode-rate column is how the census page shows whether the precondition
held.

## 5. What every cell records

As night 1, plus the offline `decode_tok_s` column. Nothing new in the
launcher.

## 6. The day after (attended, no GPU)

1. Classify the four records with the fixed classifier; the eight class
   columns are filled by the reviewer from the reconstruction, cited by
   turn, for these 15 cells and for night 1's 30.
2. The census page, `evidence/2026-09-16-census/README.md`, ≤ 120 lines with
   a recompute block, covering both nights: the classified table per task at
   the 32k line, the 48k reading beside it, depth-3's move to the floor and
   the resulting denominator, the nine contended cells and their
   replacements as separate rows, the finish-on-green counterfactual per
   task under both readings, and the runaway count with the gate's trigger
   named.
3. The R0 sitting, with these inputs: the build-task set with finishing as
   the primary class (two or three tasks); the Baseline rate at the 32k line
   per task; the counterfactual's rescue rate per task; and from those, the
   win rule and n for an Engine comparison, powered against the stipulated
   effect the counterfactual gives, not a hoped-for one. Then the Engine
   spec: finish-on-green and the completion gate, each naming its class and
   its cells.

## 7. What this night can and cannot decide

It can add a third medium-build task to the finishing tier or show the tier
is two tasks wide. It can give the self-stop distribution on a quiet machine
for run-record-gate and the large-build pair. It cannot say anything about
the Engine, and it does not change night 1's 32k-line reading, which is
complete.

## 8. Decisions approved 2026-09-17

1. Baseline-only night 2 before any Engine night.
2. Replacement scope: all nine contended cells.
3. Backstop 4,800 s.
4. Opus surveys the plans for the candidate; the maintainer picks.

## 9. Rules carried

Two-uid isolation for every cell; the launcher is the only path to a model;
records frozen and committed in daylight; no Docker, sandbox or wrapper
process; results and reviews written only by their tools; Opus steers and
reviews, Sonnet implements, no haiku; a whole-path reviewer traces one cell
end to end before launch; commits at task boundaries with explicit paths;
never push, merge or amend.
