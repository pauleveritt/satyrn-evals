# EB2 offline remedy estimates at engine 23a0ef6, both floor tasks, 12 cells per arm (2026-10-05)

Development estimates, never deciding, not EB3. Drafted by an agent (Sonnet, 2026-10-05) from `eb2.txt`. No number below is computed by hand: each is copied from `eb2.txt`, from `evidence/2026-10-05-eb-cell-read/read.txt`, or from EB1's README where it says so. Sources are the committed files `eb2.txt`, `eb2.py`, `evidence/2026-10-05-eb-cell-read/{README.md,read.txt}`, `evidence/2026-10-03-eb1-read/README.md`, the plan (`docs/superpowers/plans/2026-10-05-eb2-offline-estimates.md`, whose decisions D2-D4 are named below) and the decision-ledger entry "2026-10-05 — EB2 executed" (`evidence/2026-09-15-release-one-decision-ledger.md`), which records the rulings made during execution. Nothing is pooled across tasks, across arms, or with EB0's `1869397` cells. Every figure is output tokens per delivered pass unless it says otherwise. Two kinds of figure appear in §4. An *upper bound* uses a zero floor: a remedy removes at most every token of its category. A *central estimate* uses the Baseline median of the category as the floor and is not an upper bound. Only a build and EB3 can measure an effect.

## 1. What was read

Six nights from `~/satyrn-runs`, engine `23a0ef6`, read offline with no model and no network: `2026-10-04-eb-s1-engine-selfhost-{guard-prefixes,review-script}`, `…-eb-s2-engine-…` and `…-eb-s2-baseline-…` for the same two tasks. Each (task, arm) has 12 finished cells and none is missing. For Engine the 12 are stage 1's 6 plus stage 2's 6, which share the arm digest `a79fa458…`. `eb2.py` reuses EB1's classifier (`evidence/2026-10-03-eb1-read/eb1.py`) and the cell read's slot enumeration (`evidence/2026-10-05-eb-cell-read/read_cells.py`) unchanged; both are digest-frozen in `tests/test_frozen_instruments.py`.

```
uv run python evidence/2026-10-05-eb2-estimates/eb2.py > evidence/2026-10-05-eb2-estimates/eb2.txt
```

The first run is commit `a300683`. `eb2.txt` was regenerated after the final-review fix recorded in the ledger entry (bullet 4); only its "Required cut and remedy bounds" section changed. The power simulation uses seed 20261005 and 4,000 repetitions.

**Denominators.** The delivered pass is `verdict == "pass"`, as in the cell read.

| task | arm | cells | delivered | not delivered |
|---|---|---|---|---|
| guard-prefixes | Baseline | 12 | 8 | 1 fail, 3 `BUDGET_EXCEEDED` |
| guard-prefixes | Engine | 12 | 9 | 2 fail, 1 `unavailable` |
| review-script | Baseline | 12 | 11 | 1 `unavailable` |
| review-script | Engine | 12 | 6 | 3 fail, 2 `unavailable`, 1 `NO_PATCH` |

Verdict counts per task and arm are those of `evidence/2026-10-05-eb-cell-read/read.txt`. The cells with no verdict are labelled with their attempt code, not dropped: the 3 guard-prefixes Baseline cells `BUDGET_EXCEEDED` (72 turns, per the cell read) and the 1 review-script Engine cell `NO_PATCH`. EB1's frozen `section3` formats the verdict as a string and crashed on them, so `eb2.load` writes the attempt code into the verdict (ledger entry "2026-10-05 — EB2 executed", bullet 3; `eb1.py` stays frozen). They are inside the 12-cell denominators and never count as passes. The counts of delivered passes are the denominators of every estimate below: guard-prefixes Baseline n = 8, Engine n = 9; review-script Baseline n = 11, Engine n = 6. The spend of the cells that did not deliver is not in any figure here.

**Regression on EB0.** Before the run, the slot loader was checked against EB1's own directory loader on EB0's nights (`2026-10-02-eb0-selfhost-guard-prefixes` and `…-review-script`, 6 cells per arm, 4 task-arm sets) with the plan's Task 4 Step 4 command. At commit `a300683` it printed four lines, each "identical" (that commit's subject records that the loader reproduces EB1's section 2 on EB0). Section 2's printed output is therefore the same for guard-prefixes Baseline, guard-prefixes Engine, review-script Baseline and review-script Engine on EB0, and the loader reads cells the way EB1 did.

**Two labels in `eb2.txt` are wrong for this run.**
- Section 3's "events per cell (all 6)" is EB1's frozen label. The count is 12 cells per task.
- The power header says "section 4's rule". It means the engine-budget design spec section 4 (the floor-parity rule), not `eb2.txt`'s own section 4 (context and wall clock), which sits above it.

## 2. Attribution per floor task

EB1 §2's method, run on the 23a0ef6 cells. Each assistant turn goes into exactly one category by EB1's first-match rule, and the retry figures are upper bounds because a retry turn also re-emits the plan and the edit. Medians are over different cells, so the category rows do not sum to the total.

**guard-prefixes** (Baseline n = 8, Engine n = 9; `eb2.txt` section 2):

| category | B median | E median | d median | B mean | E mean | d mean | E cells > 0 | B cells > 0 |
|---|---|---|---|---|---|---|---|---|
| pre-edit | 40 | 6,391 | +6,351 | 1,735 | 6,387 | +4,652 | 9/9 | 8/8 |
| test file | 0 | 3,352 | +3,352 | 225 | 6,356 | +6,131 | 7/9 | 1/8 |
| retry:schema | 0 | 0 | +0 | 620 | 854 | +234 | 3/9 | 3/8 |
| retry:ANCHOR_MISSING | 0 | 0 | +0 | 0 | 59 | +59 | 2/9 | 0/8 |
| retry:NO_CHANGE_REQUESTED | 0 | 0 | +0 | 0 | 65 | +65 | 2/9 | 0/8 |
| retry:NO_CHANGE (pi) | 0 | 0 | +0 | 198 | 0 | -198 | 0/9 | 1/8 |
| retry:Could not find (pi) | 0 | 0 | +0 | 10 | 0 | -10 | 0/9 | 1/8 |
| retry:confinement | 0 | 0 | +0 | 124 | 0 | -124 | 0/9 | 2/8 |
| retry:scope (engine) | 0 | 0 | +0 | 0 | 161 | +161 | 2/9 | 0/8 |
| post-steer | 0 | 0 | +0 | 0 | 40 | +40 | 2/9 | 0/8 |
| src edit | 2,354 | 3,969 | +1,614 | 2,779 | 3,643 | +864 | 9/9 | 8/8 |
| test run | 0 | 132 | +132 | 0 | 520 | +520 | 6/9 | 0/8 |
| probe | 876 | 4,192 | +3,316 | 2,955 | 9,013 | +6,058 | 8/9 | 8/8 |
| final | 418 | 653 | +236 | 408 | 676 | +268 | 9/9 | 8/8 |
| **total** | 5,510 | 28,463 | +22,954 | 9,054 | 27,785 | +18,731 | | |

The residual of the medians (total d minus the sum of the category d) is +7,953. Turns before the first landed edit: Baseline 1 (1-11), Engine 6 (1-26). Calls before it: Baseline 1 (1-11), Engine 7 (1-27); calls touching tests before it: Baseline 0 (0-0), Engine 4 (0-8). Passes creating a test file: Baseline 1/8, Engine 7/9. Retry turns: Baseline 0 (0-7), Engine 1 (0-6).

**review-script** (Baseline n = 11, Engine n = 6):

| category | B median | E median | d median | B mean | E mean | d mean | E cells > 0 | B cells > 0 |
|---|---|---|---|---|---|---|---|---|
| pre-edit | 3,697 | 5,576 | +1,880 | 3,195 | 6,114 | +2,920 | 6/6 | 11/11 |
| test file | 3,345 | 1,636 | -1,710 | 4,025 | 2,381 | -1,644 | 6/6 | 11/11 |
| retry:schema | 0 | 0 | +0 | 155 | 0 | -155 | 0/6 | 3/11 |
| retry:NO_CHANGE_REQUESTED | 0 | 0 | +0 | 0 | 30 | +30 | 1/6 | 0/11 |
| retry:NO_CHANGE (pi) | 0 | 0 | +0 | 10 | 0 | -10 | 0/6 | 1/11 |
| retry:Could not find (pi) | 0 | 0 | +0 | 69 | 0 | -69 | 0/6 | 5/11 |
| retry:other | 0 | 0 | +0 | 0 | 138 | +138 | 1/6 | 0/11 |
| post-steer | 0 | 0 | +0 | 0 | 77 | +77 | 1/6 | 0/11 |
| src edit | 2,200 | 1,461 | -739 | 2,519 | 1,758 | -761 | 6/6 | 11/11 |
| test run | 211 | 0 | -211 | 326 | 0 | -326 | 0/6 | 11/11 |
| probe | 949 | 0 | -949 | 1,409 | 1,012 | -397 | 2/6 | 11/11 |
| final | 488 | 866 | +378 | 531 | 898 | +367 | 6/6 | 11/11 |
| **total** | 10,970 | 10,828 | -142 | 12,239 | 12,436 | +197 | | |

The residual of the medians is +1,208. Turns before the first landed edit: Baseline 9 (4-11), Engine 8 (6-12). Calls before it: Baseline 9 (4-11), Engine 13 (6-16); calls touching tests before it: Baseline 4 (1-7), Engine 4 (3-7). Passes creating a test file: Baseline 11/11, Engine 6/6. Retry turns: Baseline 1 (0-4), Engine 0 (0-3).

**Rejected `edit`/`write` calls, all cells, not only passes** (`eb2.txt` section 2):
- guard-prefixes Baseline: 22 in 5 of 12 cells (schema 9, Pi "Could not find" 6, Pi no-change 4, confinement 3). Engine: 26 in 9 of 12 cells (schema 10, `ANCHOR_MISSING` 7, Engine scope 5, `NO_CHANGE_REQUESTED` 2, `ANCHOR_ALREADY_APPLIED` 2).
- review-script Baseline: 13 in 7 of 12 cells (Pi "Could not find" 8, schema 4, Pi no-change 1). Engine: 8 in 6 of 12 cells (`ANCHOR_MISSING` 3, `NO_CHANGE_REQUESTED` 2, `REVISION_STALE` 1, other 2).

**What changed direction against EB1** (EB0 cells, engine `1869397`; EB1 §2 values are quoted as printed there, side by side, and no difference across pins is taken). "Direction" here means the sign of the Engine-minus-Baseline median d, or an Engine median that fell to zero. EB1's tables differ in grouping: its review-script table merges test run and probe, and its guard-prefixes table merges some retry shapes.
- **guard-prefixes: one category.** *Retry: schema.* The Engine median was 536 (4 of 5 cells above zero) in EB1. It is 0 here (3 of 9 cells above zero). Every other category with a non-zero median d keeps its sign: pre-edit +5,883 in EB1 against +6,351 here, test file +1,769 against +3,352, src edit +756 against +1,614, test run +156 against +132, probe +1,868 against +3,316, final +174 against +236.
- **review-script: two rows.** *Test file:* d median +1,152 in EB1 (Baseline 2,320, Engine 3,472) and -1,710 here (Baseline 3,345, Engine 1,636). *Total:* d median +5,055 in EB1 (8,047 against 13,102) and -142 here (10,970 against 10,828). Baseline's own median moved between the pins, so neither flip is an Engine-only change. *Retry: schema*: the Engine median is 0 in both, but the Engine mean was 1,176 (2 of 5 cells) in EB1 and is 0 (0 of 6) here. Pre-edit (+1,740 against +1,880), src edit (-645 against -739) and final (+511 against +378) keep their signs. EB1's merged test run and probe row was -497, and here they are -211 and -949.
- Test files created by passes: guard-prefixes Engine 3 of 5 in EB1 and 7 of 9 here; Baseline 1 of 4 in EB1 and 1 of 8 here.

The two pins are different harness states, and the Engine in the EB0 cells predates edit parity (ledger, "Engine re-pin 6d30479"). These are directional notes, not a measured change.

## 3. The parity rule's power at the delivered counts and at twice them

**Rule** (spec section 4): parity holds when the Engine median is at most margin times Baseline's and an exact one-sided rank-sum test of "Engine ≤ Baseline" does not reject at 0.05. **Simulation:** both arms draw from the observed Baseline passes (*resample*: with replacement from them; *log-normal*: fitted to their logs), the Engine draws are multiplied by the true ratio, and each figure is 4,000 repetitions at seed 20261005. Doubling the counts draws more cells from the same 8 or 11 Baseline passes. It describes the rule at that count, and no cells exist at it. The 95th-percentile ratio (q95) is the median(Engine)/median(Baseline) under true parity that would pass 95% of the time, and it does not depend on the margin.

P(rule declares parity), by the true Engine-to-Baseline ratio (`eb2.txt`, power section):

**guard-prefixes**

| counts (E / B) | margin | draw | 1.0 | 1.25 | 1.5 | 2.0 | q95 |
|---|---|---|---|---|---|---|---|
| 9 / 8 (delivered) | 1.25 | resample | 0.655 | 0.528 | 0.393 | 0.343 | 3.993 |
| 9 / 8 | 1.25 | log-normal | 0.671 | 0.499 | 0.391 | 0.188 | 2.347 |
| 9 / 8 | 1.35 | resample | 0.702 | 0.563 | 0.420 | 0.354 | 3.993 |
| 9 / 8 | 1.35 | log-normal | 0.720 | 0.560 | 0.446 | 0.227 | 2.347 |
| 18 / 16 (twice) | 1.25 | resample | 0.700 | 0.464 | 0.274 | 0.201 | 3.080 |
| 18 / 16 | 1.25 | log-normal | 0.722 | 0.496 | 0.312 | 0.106 | 1.829 |
| 18 / 16 | 1.35 | resample | 0.725 | 0.488 | 0.315 | 0.202 | 3.080 |
| 18 / 16 | 1.35 | log-normal | 0.793 | 0.582 | 0.387 | 0.145 | 1.829 |

**review-script**

| counts (E / B) | margin | draw | 1.0 | 1.25 | 1.5 | 2.0 | q95 |
|---|---|---|---|---|---|---|---|
| 6 / 11 (delivered) | 1.25 | resample | 0.888 | 0.402 | 0.038 | 0.000 | 1.311 |
| 6 / 11 | 1.25 | log-normal | 0.854 | 0.462 | 0.141 | 0.007 | 1.372 |
| 6 / 11 | 1.35 | resample | 0.932 | 0.442 | 0.060 | 0.000 | 1.311 |
| 6 / 11 | 1.35 | log-normal | 0.906 | 0.566 | 0.195 | 0.011 | 1.372 |
| 12 / 22 (twice) | 1.25 | resample | 0.939 | 0.175 | 0.002 | 0.000 | 1.226 |
| 12 / 22 | 1.25 | log-normal | 0.916 | 0.393 | 0.051 | 0.000 | 1.266 |
| 12 / 22 | 1.35 | resample | 0.954 | 0.178 | 0.002 | 0.000 | 1.226 |
| 12 / 22 | 1.35 | log-normal | 0.945 | 0.451 | 0.065 | 0.000 | 1.266 |

**Finding: spec section 4's rule cannot reliably separate parity from 2× on guard-prefixes at these counts.** The Baseline passes are bimodal: `eb2.txt` prints them as [2308, 2663, 2898, 5206, 5813, 16178, 17764, 19599], five from 2.3k to 5.8k and three from 16k to 20k (median 5,510). At the delivered counts the rule declares parity 0.655-0.720 of the time when the Engine is truly 1.0× Baseline, and 0.188-0.354 of the time when it is truly 2.0×. The true-parity q95 ratio is 2.347-3.993, against margins of 1.25 and 1.35. At twice the counts the rule declares parity 0.700-0.793 of the time at 1.0× and 0.106-0.202 at 2.0×, and the q95 ratio is 1.829-3.080. Doubling the counts does not bring a truly equal Engine near the 0.95 that a usable margin would need. This bears on EB3's pre-registration: at these counts a pre-registered margin and rank-sum clause on guard-prefixes gives similar declared-parity rates for an Engine at 1.0× and one at 2.0× (the ranges above), so the margin, the counts or the statistic need a ruling before EB3, not after its cells are read.

**review-script's rule behaves.** At the delivered counts parity is declared 0.854-0.932 at 1.0×, and 0.000-0.011 at 2.0×. At twice the counts it is 0.916-0.954 at 1.0× and 0.000 at 2.0×. The true-parity q95 ratio is 1.311 (resample) and 1.372 (log-normal) at 6 / 11, and 1.226 and 1.266 at 12 / 22. A truly 1.25× Engine is declared at parity 0.175-0.566 of the time, so the rule does not separate 1.0 from 1.25 on either task at these counts.

## 4. Required cut and remedy bounds

**The bounds are not EB1 §5's formula.** EB1 §5 scored a remedy by a median of category tokens (for example, the Engine median of pre-edit plus test file, minus the Baseline median). A median of category tokens does not bound the decider, which is the median of per-pass totals, because medians do not subtract (ledger entry "2026-10-05 — EB2 executed", bullet 1; spec section 7, "EB1 §5's remedy figures are not upper bounds"). Each row here is instead a per-cell counterfactual: remove the remedy's tokens from every Engine pass (never below zero), and the figure is the median of the Engine totals minus the median of the totals after removal. Hoisting removes all of an Engine pass's schema and `ANCHOR_MISSING` retry tokens under both references. The categories are disjoint per turn, so the combined row applies the per-cell removals together, and it is not a sum of the rows. The EB1-style figures are still printed by `eb1.section5` in `eb2.txt` and are listed below for comparison.

**Two references, both shown.** The stop rule is defined on upper bounds, so it reads the **upper bounds** (reference zero): test lines remove all of a pass's pre-edit and test-file tokens, and the scratch path removes all of its probe tokens. The **central estimates** (reference Baseline median of the category: remove only the excess over the Baseline median, clamped at 0) are shown beside them but are not upper bounds. The guard-prefixes Baseline is bimodal (the totals above, and per category in section 2), so its median is a central value that a remedy can beat, and a counterfactual that clamps each Engine pass to it does not bound what a remedy can remove. The first draft of this README used the median reference as its bound; the ledger entry (bullet 4) records that as an instrument defect and its correction.

**Required cut.** The output tokens per delivered pass that the Engine median must lose to meet the median clause, at the screening margin 1.25 (plan D4) and at 1.35:
- guard-prefixes: **21,576** at 1.25 and **21,025** at 1.35. The rank-sum p (Engine ≤ Baseline) is 0.0012.
- review-script: no cut is needed at either margin (section 5).

**Replay-scorable** copies EB1 §5's column: "no" means the remedy changes calls from an earlier turn than the measured point, so a replay of the recordings cannot score it (R0 section 1.4); "partly" means the recorded call can be checked and the saving is an upper bound. The scratch row is new in EB2 under D3 and has no EB1 §5 entry; see the note under the tables.

**guard-prefixes, upper bounds** (reference zero; Engine n = 9, Baseline n = 8; read by the stop rule):

| remedy | class targeted | replay-scorable | upper bound | clears at 1.25 (cut 21,576) | clears at 1.35 (cut 21,025) |
|---|---|---|---|---|---|
| light path for small requests | everything the Engine adds on a modify-only task | no | 22,954 (the whole Engine-Baseline median gap; not an estimate) | not counted | not counted |
| contract test lines (pre-edit + test file) | pre-edit survey of `tests/` and writing the test file | no | 17,059 | no | no |
| edit-shape hoisting (all schema + `ANCHOR_MISSING` retries) | schema-rejection and anchor-miss retries | no (EB1 3b; the unambiguous-shape normalizer alone is "partly") | 2,679 | no | no |
| scratch path (probe; new in EB2 under D3) | probe turns, inline regex experiments | no (not rated in EB1 §5; see note) | 11,226 | no | no |
| all estimable remedies combined (the three rows above, per cell) | the three above together | no | 23,278 | **yes (upper bound)** | **yes (upper bound)** |

The "clears" columns are read from the printed verdict lines at margin 1.25 and 1.35, which both say "no remedy clears alone; the estimable remedies combined can clear (upper bound)". The rank clause on the combined upper-bound counterfactual: `eb2.txt` prints a rank-sum p of **0.7596** for the combined counterfactual totals against Baseline, which does not reject "Engine ≤ Baseline" at 0.05.

**guard-prefixes, central estimates** (reference Baseline median of the category; not upper bounds; same cells):

| remedy | central estimate | clears at 1.25 (cut 21,576) | clears at 1.35 (cut 21,025) |
|---|---|---|---|
| light path | 22,954 (the whole gap; not an estimate) | not counted | not counted |
| contract test lines (pre-edit + test file) | 16,120 | no | no |
| edit-shape hoisting | 2,679 | no | no |
| scratch path (probe) | 10,350 | no | no |
| all estimable remedies combined | 21,463 | **no** (21,463 against 21,576) | **yes, as a central estimate** (21,463 against 21,025) |

`eb2.txt` prints the central combined estimate against each cut with no verdict wording; the "clears" cells quote those printed pairs. A central estimate is not an upper bound, so the 1.35 "yes" is not a clearing call under the stop rule. No single row's central estimate reaches either cut.

- **The light path is reported and never counted as clearing.** Its figure is the whole Engine-Baseline gap by definition, so it cannot fail to cover the cut. It is not estimable offline. Excluding it reverses the plan's Task 3 expectation (ledger entry, bullet 2).
- **Overlaps.** The categories are disjoint per turn, so the combined row's per-cell removals add; whether the remedies overlap causally cannot be scored offline. The rows are never added to each other.
- **Scratch-row replay note.** EB1 §7 named inline probing as the largest guard-prefixes cost with no listed remedy, and flagged that estimating a scratch path needs a ruling (D3: yes). This README rates it "no" because it changes the calls that make up the probe turns, so the effect begins before the measured point. This is this README's reading, not a copy of EB1's column.

**EB1-style figures for comparison** (`eb2.txt` section 5, guard-prefixes; not used for any clearing call):

| figure | value |
|---|---|
| R2 normalizer, unambiguous schema shapes, Engine passes | 0 (0-4,685); mean 854 |
| R2 all schema + `ANCHOR_MISSING` retries | 0 (0-4,685); mean 912 |
| contract test lines, Engine pre-edit + test file | 8,827 (3,830-29,118); mean 12,743 |
| same, minus the Baseline median | +7,888 |
| light path, whole Engine-Baseline gap | +22,954 |

**Self-test and echo trimming** (`eb2.txt` section 5). No output-token saving is measurable for either, so neither can clear the decider:
- guard-prefixes: dedup after a red model run saves 34 s per pass (0-131), dropping the second suite run 62 s (31-124), and the dot filter plus `VIRTUAL_ENV` strip removes 6,422 note bytes (4,211-10,844). Echo trimming is 1,006 context tokens at the peak (521-2,778).
- review-script: 64 s (0-194), 77 s (31-125) and 7,528 bytes (4,211-10,844). Echo trimming is 240 tokens (0-947).
- The self-test path ran 27 events in 12 of 12 guard-prefixes Engine cells and 38 in 12 of 12 review-script cells (`eb2.txt` section 3).

**review-script** (Engine n = 6, Baseline n = 11), a no-harm task (D2):

| remedy | class targeted | replay-scorable | upper bound (zero) | central estimate (Baseline median) | clears 1.25 / 1.35 |
|---|---|---|---|---|---|
| light path | does not qualify (review-script creates files) | n.a. | n.a. | n.a. | n.a. |
| contract test lines | pre-edit survey and test file | no | 8,270 | 1,934 | no cut needed |
| edit-shape hoisting | retries | no | 0 | 0 | no cut needed |
| scratch path | probe turns | no (as above) | 1,056 | 582 | no cut needed |
| all estimable remedies combined | the three together | no | 8,270 | 1,934 | no cut needed |

The review-script EB1-style figures are 0 for both R2 rows, 6,890 (5,080-13,503) for the test-lines category and +493 minus the Baseline median, and -142 for the whole gap. The rank-sum p of the combined upper-bound counterfactual against Baseline is 1.0000.

## 5. Review-script, no-harm

The rank-sum p (Engine ≤ Baseline) is **0.5582**, which does not reject, so the rank clause is met. The Engine median (10,828) is below Baseline's (10,970), and `eb2.py` prints **within margin (no-harm)** at both 1.25 and 1.35. The only figures printed for headroom are the central-estimate lines' required cuts, which are negative (-2,885 at 1.25 and -3,982 at 1.35), meaning no cut is needed. The delivered denominator is 6 of 12 Engine cells against 11 of 12, and that rate is reported and is not the decider.

The bounds are reductions, and a reduction cannot push the median above the margin. **The real no-harm risk is a remedy that adds tokens on review-script's path**, for example a longer finish step or a new survey, and an offline reduction bound cannot measure it. Any remedy that touches review-script's path needs an Engine-arm measurement on review-script (EB3) before it is called harmless. The light path does not apply to this task.

## 6. Outcome

Read at the screening margin 1.25 (plan D4), from the upper-bound verdict line in `eb2.txt`. The required cut is 21,576 on guard-prefixes.

**Remedies whose upper bound clears: the three estimable remedies combined (contract test lines, edit-shape hoisting, scratch path). No single remedy clears.** The combined upper bound is 23,278 against the cut of 21,576, and the rank clause on the combined counterfactual is met (printed p 0.7596). The same verdict is printed at 1.35 (combined 23,278 against 21,025).

**Beside it, the central estimate.** The combined central estimate is 21,463 against the required cut of 21,576 at 1.25, and 21,463 against 21,025 at 1.35. It is not an upper bound. `eb2.txt` does not print the combined bound without the scratch path (the scratch row is new in EB2 under D3), so this README states no figure for it.

The light path is not estimable offline: its figure is the whole gap by definition, so it is reported and never counted. Excluding it reverses the plan's Task 3 expectation (ledger entry "2026-10-05 — EB2 executed", bullet 2). review-script is within margin and needs no cut (section 5).

Each is an upper bound; only a build and EB3 can measure the effect. Next: the maintainer picks which to specify.
