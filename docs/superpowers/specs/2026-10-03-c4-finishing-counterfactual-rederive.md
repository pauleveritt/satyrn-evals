# Pre-registration: C4, the finishing counterfactual re-derived on the C3 census

**Approved by the maintainer in session, 2026-10-03** ("Approve"). The text below is the draft he was shown, unchanged; it was not committed before this approval. Drafted 2026-10-03 by an agent from `docs/superpowers/plans/2026-10-03-c4-counterfactual.md` (Task 1) and the maintainer's rulings of 2026-10-03 (plan "Rulings, 2026-10-03"; ledger "2026-10-03 — C4's decisions ruled; the C4 plan approved"). Section numbers follow `2026-09-15-release-two-finishing-counterfactual.md`, which binds where this page says "unchanged".

**Order (D1 = A).** This page is approved and committed before C3's daylight freeze (C3 plan Task 3), so before night A. No `classify.py` run on a C3 cell happens before that commit (C3 D8). Nothing in sections 2–5 changes after the decision run. A bug found afterwards is fixed and re-run only with the bug and both results recorded beside each other.

**What its author read.** Its author opened no C3 cell, result, night directory, grade output or tally: none exists. At phase-c1 `df3b68f` no C3 sitting has run. There is no `records/2026-10-02-c1-*.result.json`, no `evidence/*-c3-census/` and no "C3 frozen" ledger line. Earlier evidence the author did read:
- the 2026-09-15 counterfactual pre-registration, in full;
- the decision ledger's entries from C0 (2026-10-02) through "2026-10-03 — C3 D5";
- the approved C3 plan and the C4 plan;
- the 2026-10-03 decision sheet behind these rulings, which quotes EB0 aggregate counts (see section 7);
- R0 constraints §2 and §4; census design §7 and §8; `ROADMAP.md`'s R0 row;
- code only, no data: `confinement.py`, `confinement.ts`, `summary.py`, `rescore.py`, and `classify.py`'s per-cell row fields.

It opened no census transcript, census `cells.json`, result JSON or `classes.md` per-cell row. It opened no C2 `cells.json` or `table.md`, and no EB0 cell, summary or transcript.

## 1. Question (unchanged)

Suppose a Baseline cell had stopped at the first point the Engine could observe as green. How many passes inside the 32,000-token / 48-turn line would that add, and how many would it break? This is asked now of the C3 census, run under confinement. It is taken offline from retained cells only, with no GPU, no new tasks, and no Engine or `satyrn_evals` code.

## 2. Scope (D6 = A, D4 = A)

**Records:** the six `records/2026-10-02-c1-<task>.json`, run in C3's two sittings. They are Baseline, `confinement: extension`, n = 6, k = 3, 48,000 tokens / 72 turns. The cells are each record's finished slots, as listed in its night's `summary.json`.

| task | C3 night | role |
|---|---|---|
| selfhost-run-record-gate | A | decides |
| selfhost-docs-linter | A | decides |
| selfhost-preflight-quiet | A | decides; its own row, never pooled |
| agentclinic-repair-depth-3 | B | decides |
| selfhost-cell-loop | B | decides |
| selfhost-speed-probe | B | reported outside the decision |

speed-probe was dropped from the ceiling set for a prompt ambiguity, and R0 §2 never claims against one. Its row is computed and printed, and it never enters the verdict.

**Denominator: admitted cells only.** A cell is admitted when `confinement.Finding.admitted` holds, as the code stands at `df3b68f`. That needs refusals 0 (no `confinement_refused` entry) and reaches 0. `reaches` counts only reaches that leave the cell's worktree. A hidden basename inside the cell's own worktree is reported as `confinement_reaches_in_worktree` and does not un-admit a cell (C3 D5). The per-cell source is `evidence[<attempt_dir>].confinement_admitted` in `~/satyrn-runs/2026-10-02-c1-<task>/baseline/summary.json`. Only `true` admits; `false` or absent does not. The following cells are listed and never count as a rescue, a harm or an unmeasured cell:
- flagged cells (a finding, not admitted);
- unmeasured-by-confinement cells (no finding);
- infrastructure-replaced cells.

**Two counts beside the denominator.** Both are reported per task with their cells listed. They may overlap, and neither decides.
- **Flagged after trigger.** A flagged cell whose `cells.json` row has a non-null `own_green_turn` (the trigger turn), where the earlier of its first `confinement_refused` entry and its first reach that `finding` counts falls at a turn greater than `own_green_turn`. An event's turn is the number of `turn_start` events at or before it.
- **Flagged only by non-protected refusals.** The cell's transcript yields a `confinement.finding` with `reaches` 0 and `refusals` ≥ 1. In addition, every `confinement_refused` entry (`entry_appended` with `entry.customType == "confinement_refused"`) must meet all of these:
  - `entry.data.toolName` is `read`, `edit` or `write`;
  - `entry.data.path` is a string;
  - `confinement._reaches(path, cwd, confinement.protected(task_dir.parent, task_dir.name))` is `None`, using the terms admission uses and `cwd` from the transcript's first event.

  A bash refusal never qualifies, because the extension refuses bash only when the command names a protected root (`confinement.ts` `namesRoot`). An example that qualifies is a `write` to `/tmp/test_guard.py`. These cells stay outside the denominator. The count exists so that a non-leak refusal never shrinks it silently.

**Pooled with nothing.** Isolated census nights 1–3, the 2026-09-15 counterfactual (runs 1 and 2), EB0 and every Engine cell are out. Tasks are never summed. Night A and night B are never pooled.

## 3. Definitions (unchanged)

Source edit, own-green and the counterfactual policy are as defined in 2026-09-15 §3. The trigger counts only within the line: cumulative output tokens at that turn ≤ 32,000 and the turn number ≤ 48 (`census_classify.TOKEN_LINE`, `TURN_LINE`).

## 4. Counting (D2 = A, D3 = A)

**Method.** `evidence/2026-09-16-census/classify.py` gives two readings, unchanged, run by path and unmodified (C3 D8):
- run 1 is §3–§5 with amendments 7.1–7.4 (`cf.unmeasured_reasons`, `cf.counterfactual_pass`);
- run 2 is the hidden-suite verdict of the tree at the end of the trigger turn, by `classify.py`'s std replay. The `ext` replay is not carried over.

**Actual outcome:** the row's `actual_32k`, which is a pass inside the line. **Rescue:** actual not-pass, counterfactual pass. **Harm:** actual pass, counterfactual not-pass. **Net** per task = rescues − harms, on admitted cells.

**Deciding reading: run 2,** with the fidelity amendment. An admitted cell is unmeasured under run 2 when its row's `raised` is set, or when any of its `unmeasured` reasons begins `fidelity:` or `raised:`. That is §4's fidelity rule, which `classify.py`'s run 2 column does not apply. Any other reason (for example `unverified-rescue`) does not withhold under run 2.

**Beside: run 1.** An admitted cell with any `unmeasured` reason, or a raise, is unmeasured, as in §4 and 7.4. Run 1's verdict is computed and printed beside run 2's, and any disagreement is stated on the result page. Run 1 never decides.

An unmeasured cell counts as no change and is listed with its reason (§4).

## 5. The decision (D5 = A, §5 with 7.1, D7)

**Task kinds**, from admitted cells. A task is **budget-shaped** when it has at least 3 admitted cells and at least half of them (`⌈admitted / 2⌉`) are not a pass at the line. Every other deciding task is **floor**, in scope for harm. Kinds come from `actual_32k` and admission, so both readings share them.

**Thresholds, as written:**
- A task is `insufficient` with more than 1 unmeasured admitted cell. It is also `insufficient` with fewer than 3 admitted cells.
- A budget-shaped task **qualifies** when it is not `insufficient` and its net is ≥ 1.
- **Floor harm** is the harm count over all floor tasks together, as in §5.

**Verdict**, on the deciding reading and the five deciding tasks, applied in this order:
1. **go**: at least 2 qualifying tasks, floor harm < 2, and no floor task `insufficient`.
2. **verify**: otherwise, when at least one task qualifies.
3. **not-the-lever**: otherwise, when no budget-shaped task, sufficient or not, has net ≥ 1. This includes the case of no budget-shaped task at all.
4. **verify**: otherwise (7.1's gap: an `insufficient` budget-shaped task has net ≥ 1).

**What each verdict opens.** This is fixed now and not re-argued after the read.

| verdict | opens | does not open |
|---|---|---|
| **go** | The R0 sitting under census design §8: the claim row, the ceiling set, the budget from C3's self-stop distribution, and the win rule and power. The stipulated effect is C4's per-task net / admitted (R0 §2). Then **a finish-on-green Engine spec only** | any Engine build before §8.3 fixes the rule and its power |
| **verify** | The R0 sitting asks whether a one-task claim is worth a release. On 2026-09-15, power 0.26 at n = 12 was judged too small. If yes, size n first | Engine spec |
| **not-the-lever** | R0 §5 question 3 (is 9B at 48k the honest setting?), and another Engine-addressable class from C3's table (for example runaway's completion-gate trigger), each with its own offline estimate (R0 §1.4) | finish-on-green spec |

Under any verdict:
- EB2 remedies need offline estimates on EB0 cells.
- The Engine's inner-Pi `SATYRN_CONFINEMENT_ROOT` fix lands before the first post-C4 Engine read.
- `derive-new-top-level-module` stays parked. This instrument scores a stop rule on Baseline cells and cannot name a derive remedy.

## 6. Deliverables, the one run, and what is not read

- **Script:** `evidence/<c4-date>-c4-counterfactual/decide.py` (plan Task 2). It is tested on synthetic data only, and it adds nothing per cell. It reads `classify.py`'s per-task `cells.json` and each night's `summary.json` admission, and the transcripts for the two beside counts.
- **The one run** (plan Task 3) writes `decision.txt` and `table.md` once, each stamped with the evals commit, the dirty state and the argv. The script refuses a second run while `decision.txt` exists. A `dirty=True` stamp is a review failure.
- **Result** (D8, as C3 D9 was ruled): an agent drafts `evidence/<c4-date>-c4-counterfactual/README.md`, and the maintainer writes `docs/results/<date>-c4-counterfactual.md` (≤ 120 lines, fenced recompute). The page carries:
  - both readings' verdicts;
  - the per-task table;
  - the two beside counts;
  - every unmeasured cell with its reason;
  - the D7 row for the verdict;
  - section 7;
  - the replay limits.
- **Ledger** (D9 = A): marks re-derived here are **SUPERSEDED** for building, and the isolated reading stays evidence for the isolated condition. Marks not re-derived are **KEPT**. There is no post-hoc "agrees or disagrees" judgment.

**Not read, before or at the decision:**
- Before this page is committed: any C3 cell, `summary.json`, `classify.py` output or tally.
- At the read, none of these enter the verdict:
  - the isolated census cells or their class columns;
  - the 2026-09-15 counterfactual cells;
  - EB0 or any Engine cell;
  - speed-probe's row;
  - flagged, unmeasured-by-confinement and replaced cells;
  - `actual_48k`;
  - C3's class columns, flags and `hunting`.

  C3's table is read for not-the-lever's next class only after the verdict exists.

## 7. Disclosure

The author knew the following before drafting, from the documents listed in the header, and from no cell:
- The isolated census found medium builds finishing-bound. ROADMAP's R0 row records that run-record-gate and docs-linter had 9 of 12 cells reach green inside the 32k line on night 1, and that depth-3 at R2 is floor. The C3 plan quotes 8 of 9 run-record-gate cells and 4 of 6 docs-linter holding a pass inside the line. This is UNCONFIRMED (35c298d), per C0.
- The 2026-09-15 counterfactual's run 2 read Verify, with docs-linter net +1, on release-one cells under isolation.
- The C2 re-read (signed 2026-10-03) found `hunting` True in 4 of 45 census cells. It also found in-worktree hidden-basename reaches on 17 of 39 cells and on 6 of 6 night-3 cells. Process classes stand only to each cell's first divergence turn.
- The decision sheet quotes these EB0 counts. They come from EB0's own records, run at `61bc0d1`, which are outside this census:
  - review-script, both arms: 12 of 12 cells flagged by in-worktree reaches before `df3b68f`, with 10 passes un-admitted;
  - guard-prefixes Baseline: 2 of 6 cells refused for `/tmp` scratch writes, 1 of them a pass;
  - depth-3 Baseline: 6 of 6 admitted.

  The guard-prefixes count is what prompted the second beside count.

None of these is a C3 tally. The kinds in section 5 are computed from C3's admitted cells and are not named from the census (D5 option C was rejected).
