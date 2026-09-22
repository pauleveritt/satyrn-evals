# Release two, knowledge stage — the finishing counterfactual (pre-registration)

**Status:** pre-registration, committed before any counterfactual number
exists. Approved by the maintainer in the R0 design sitting, 2026-09-15.
Bound by `2026-09-15-release-two-r0-constraints.md`. Nothing in sections 2–5
changes after the decision run; a bug found afterwards is fixed and re-run
only with the bug and both results recorded beside each other.

## 1. Question and purpose

R0 chose knowledge first: before release two decides between a defensible
claim and a better product, find out whether an Engine-addressable failure at
9B is large enough to build for. Fable's reconstruction of release one
(`evidence/2026-09-15-release-one-outcome/`) suggests one: cells reach a
passing state and keep working until the budget ends.

**Question:** if a cell had stopped at the first point the Engine could
observe as green, how many within-budget passes would that add, and how many
would it break?

The answer is taken offline from retained cells only. No GPU, no new tasks,
no Engine or `satyrn_evals` code.

## 2. Scope

All cells are under `~/satyrn-runs/`, on release one's isolated harness with
declared sampling and a 32,000-token / 48-turn budget. Records and results
are under `records/`.

**Decision cells: Baseline admission on each task's current prompt.**

| task | record | attempt ids (suffix) | recorded codes |
|---|---|---|---|
| agentclinic-repair-depth-3 | 2026-09-14-admission | 971281, 021584, 082295, 700050 | COMMAND_TIMEOUT, BUDGET_EXCEEDED, OK-fail, BUDGET_EXCEEDED |
| selfhost-run-record-gate | 2026-09-15-admission | 388294, 448568, 519278, 028222 | BUDGET_EXCEEDED ×4 |
| selfhost-docs-linter | 2026-09-15-admission | 147562, 204433, 270586, 970283 | BUDGET_EXCEEDED, OK-pass, BUDGET_EXCEEDED, BUDGET_EXCEEDED |
| selfhost-guard-prefixes | 2026-09-15-admission | 812248, 870439, 937944, 424626 | OK-pass ×4 |
| selfhost-review-script | 2026-09-15-admission | 688090, 746232, 816670, 501161 | OK-pass ×4 |
| agentclinic-repair-depth-2 | 2026-09-14-admission | 523251, 575297, 634454, 616367 | OK-pass ×4 |

**Budget-shaped tasks** are fixed from recorded codes alone: a task counts if
at least 2 of its 4 decision cells ended `BUDGET_EXCEEDED` or
`COMMAND_TIMEOUT`. That selects depth-3, run-record-gate and docs-linter.
**Floor tasks** are guard-prefixes, review-script and depth-2; they are in
scope for harm.

**Reported, outside the decision:** the 2026-09-14 self-hosted admission
nights (run-record-gate, guard-prefixes, review-script; prompt defects since
fixed), and the Engine cells — route proofs `route-proof-b` depth-3,
run-record-gate, docs-linter, and the four misleading-locus development
cells. Engine cells appear in their own column.

**Excluded:** the calc-build first-turn smoke; the first depth-3 route proof
(719334, the engine crash since fixed); the complaint-lifecycle development
cells (no tests or hidden suite through `launch`).

## 3. Definitions

**Source edit.** A landed mutation of a file inside the task manifest's
`source_paths` that is not a test file (basename `test_*.py` or `*_test.py`,
or a path under a `tests` directory): a `write`, an `edit` whose tool result
is not an error, or a file-writing bash command the reconstruction replays.

**Own-green**, the Engine-observable trigger: the first test run after the
first source edit whose recorded result is green —

- a `self_test` result with `ok` true and no failed ids (Engine cells), or
- a bash command for which `satyrn_evals.cell_evidence.runs_pytest` is true,
  whose `tool_execution_end` is not an error, and whose output contains a
  pytest summary line reporting at least one pass and no `failed` or `error`
  count. A run whose summary line is absent from the output is not green.

The trigger counts only if it falls within the budget: cumulative output
tokens at that turn ≤ 32,000 and the turn number ≤ 48.

**Counterfactual policy:** the cell stops at the trigger turn.

## 4. Counting rules

**Actual outcome:** pass within budget, from the harness result (code `OK`
and verdict `pass`); anything else is not-pass.

**Counterfactual outcome:** the hidden-suite verdict of the reconstructed
worktree as it stood at the end of the trigger turn, graded as the harness
grades — `satyrn-evals grade`, the task's hidden suite, its allowlist and its
current manifest (including `ignored_paths`). A cell with no trigger keeps its
actual outcome.

**Rescue:** actual not-pass, counterfactual pass. **Harm:** actual pass,
counterfactual not-pass. **Net rescues** per task = rescues − harms.

**Fidelity.** For every decision cell the harness graded (a verdict of
`pass`, `fail` or `unavailable`), the reconstructed final worktree is graded
first and must reproduce the harness verdict. Cells without a harness verdict
(`BUDGET_EXCEEDED`, `COMMAND_TIMEOUT`) are marked `unverifiable` and still
count.

**Unmeasured.** A decision cell is unmeasured when its fidelity check fails,
or when the reconstruction skipped a bash command before the trigger turn that
could have written inside `source_paths`, or when replay or grading raises.
An unmeasured cell counts as no change and is listed with its reason. A task
with more than one unmeasured decision cell is `insufficient`.

## 5. Decision (pre-registered)

- **Go** — at least two budget-shaped tasks that are not `insufficient` each
  have net rescues ≥ 1, **and** the floor tasks together have fewer than 2
  harm cells, **and** no floor task is `insufficient`.
- **Verify on clean tasks** — exactly one budget-shaped task qualifies; or
  two or more qualify but floor harm is ≥ 2 or a floor task is
  `insufficient`.
- **Finishing is not the lever** — no budget-shaped task has net rescues ≥ 1.

With 4 cells per task, one net rescue is 25 points. Even **Go** therefore
earns only the next stage, a Baseline-only diagnostic batch on
validity-checked build tasks; it never authorizes Engine work. **Verify**
leads to the same batch sized to the qualifying task's shape. **Not the
lever** returns R0 to its question 3 (is 9B the honest model and budget?) and
to finding another Engine-addressable class first.

## 6. Deliverables and order of work

1. **This pre-registration is committed** before step 2 begins.
2. **The analysis script**
   `evidence/2026-09-15-finishing-counterfactual/counterfactual.py`, extending
   the release-one `reconstruct.py` replay. Interface:
   - `--phase debug` runs only cells outside the decision set (section 2) and
     refuses any decision attempt id; used to develop and check the trigger
     and counting code.
   - `--phase decision` runs exactly the 24 decision cells once and writes
     `cells.json`, `table.md` and `decision.txt`, each stamped with the evals
     commit and the command line.
   - No model, no network, nothing under `/Users/Shared`; scratch worktrees
     under the script's own directory, git-ignored.
   Sonnet implements; Opus reviews the trigger and counting code line by
   line against sections 3–5 before the decision phase runs.
3. **The decision run.** One run; outputs committed.
4. **The result:** `evidence/2026-09-15-finishing-counterfactual/README.md`,
   at most 120 lines: the per-cell table (trigger turn, tokens at trigger,
   actual, counterfactual, rescue, harm, fidelity, unmeasured reason), the
   per-task net rescues, the Engine column, the decision, and a fenced
   recompute command. `docs/results/` stays launcher-only. The R0 row of
   `ROADMAP.md` records the decision.

**Out of scope:** Engine code; new task cuts; the release-two design spec;
a tested reconstruction module in `satyrn_evals` (deferred until an
admission design needs it).

## 7. Pre-run amendment (2026-09-15, before the decision phase ran)

Recorded by the maintainer's decision after the analysis plan
(`docs/superpowers/plans/2026-09-15-finishing-counterfactual.md`) was verified
on debug cells only. No decision cell had been replayed or graded.

1. **Section 5 gap.** When no budget-shaped task qualifies for **Go** or
   **Verify**, but a budget-shaped task that is `insufficient` has net
   rescues ≥ 1, the decision is **Verify on clean tasks**, not **Finishing is
   not the lever**. **Not the lever** therefore requires that no budget-shaped
   task, sufficient or not, has net rescues ≥ 1.
2. **Section 6 grade location.** Grading inside the evals checkout lets its
   pytest configuration reach the task's suite (every AgentClinic grade came
   back `unavailable`), so grade receipts are written under
   `~/satyrn-counterfactual-grades/`, and the script refuses a grade root with
   any pytest configuration or `conftest.py` above it. Replay worktrees stay
   under the script's directory, git-ignored. The counting rules are unchanged.
3. **Disclosure.** This pre-registration was written after the release-one
   review (`evidence/2026-09-15-release-one-outcome/fable-review.md`), which
   reported hidden-suite pass-states for some decision cells (docs-linter,
   run-record-gate). It did not measure own-green triggers, which are what
   sections 3–5 count. The result page states this.

4. **Conservative rescues (recorded 2026-09-15, still before the decision
   phase ran).** The review gate found that a bash command the replay skips
   can leave files outside `source_paths` that change the harness grade
   (for example to `unavailable`), and that lexical writer detection misses
   some writers (`patch`, `python fix.py`, `Path(...)` writes). Either can turn
   a real not-pass into a reconstructed pass. Therefore a cell whose
   counterfactual outcome is pass counts as a **rescue** only if every bash
   command up to and including the trigger step was either replayed or is
   provably read-only: `cat`, `ls`, `pwd`, `echo` or `printf` without
   redirection, `grep`/`rg`, `find` without `-exec`/`-delete`/`-fprint`,
   `head`, `tail`, `wc`, `sort`, `uniq`, `diff`, `sed` without `-i`,
   `git status`/`diff`/`log`/`show`, and test runs for which `runs_pytest` is
   true, possibly joined with `cd` into the worktree, pipes into those
   commands, or `2>&1`. Otherwise the cell is unmeasured with reason
   `unverified-rescue`. Harm counting is unchanged. The replay's remaining
   limits are disclosed on the result page.

## 8. Run 2 (recorded after the decision run)

The header's clause applies: a bug found afterwards is fixed and re-run only
with the bug and both results recorded beside each other. A deep review of
run 1 (`evidence/2026-09-15-finishing-counterfactual/run-2/fable-review.md`)
found that three pre-registered rules — plan Ruling 11's `write_text`
heuristic, a BSD `sed -i` error counted as a skipped write, and 7.4's
read-only list rejecting `2>/dev/null`, `od`, `xxd`, `python3 -c` — withheld
the one real rescue and made 8 of 24 cells unmeasured. Run 1's outputs stand
unedited; run 2 records the corrected reading beside them:
**Verify on clean tasks** (section 5 as amended by 7.1), docs-linter net +1,
0 harms, 0 unmeasured, fidelity 14 of 14. The class is still small (power
0.26 at n = 12), so the maintainer's decision on 2026-09-15 was to build no
finish-on-green Engine and to ship the Engine as a product with honest
before-and-after numbers instead. That direction was withdrawn later the same
day: a Baseline-only pathology census ran first, and the claim shape was then
chosen from its classified table (`STATE.md`, ROADMAP R0). Run 2's page:
`evidence/2026-09-15-finishing-counterfactual/run-2/README.md`.
