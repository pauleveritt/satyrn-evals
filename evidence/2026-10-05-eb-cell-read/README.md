# EB cell read at engine 23a0ef6 — both floor tasks, 12 cells per arm (2026-10-04/05)

Development cells, never deciding, not EB3. Drafted by an agent (Opus, 2026-10-05) from the maintainer's two-stage brief of 2026-10-04 ("Go for stage 2" after reading stage 1). The purpose was twofold. EB2 needs fresh Engine cells at the current pin to estimate remedies on, because EB0's Engine cells are `1869397`, from before edit parity (ledger "Engine re-pin 6d30479", (d)). EB3 needs enough cells per arm to state a power for its parity rule. Nothing below pools across tasks or with EB0's cells.

```
R=~/satyrn-runs/2026-10-04-eb
uv run python evidence/2026-10-05-eb-cell-read/read_cells.py \
  $R-s1-engine-selfhost-guard-prefixes $R-s2-engine-selfhost-guard-prefixes $R-s2-baseline-selfhost-guard-prefixes \
  $R-s1-engine-selfhost-review-script $R-s2-engine-selfhost-review-script $R-s2-baseline-selfhost-review-script --combine
uv run satyrn-evals grade-line $R-<stage>-<arm>-selfhost-<task> --record records/2026-10-04-eb-<stage>-<arm>-selfhost-<task>.json \
  --grade-root <dir outside any Python project> --out <report.json>
```

The reader is `read_cells.py` (stdlib only, read-only, no model or network), and its output is in `read.txt`. It takes its definitions from `evidence/2026-10-02-engine-budget/cells.py` on branch `worktree-engine-budget`, and the reader's docstring cites them line by line.
- A delivered pass is `verdict == "pass"`.
- Tokens are `usage.output` summed over the assistant `message_end` events.
- Calls are counted from `tool_execution_start`, one per call.
- A schema rejection is a rejected `edit`/`write` whose text starts "Validation failed".
- A cell is admitted when `attempt.json` shows 0 confinement refusals and 0 reaches.

On EB0's two nights the reader reproduces EB0's published medians exactly (`eb0-validation.txt`; records read from the `worktree-engine-budget` worktree). The `grade-line` reports are in `grade-line/`, one per night. "Pass at the line" is `grade-line`'s `line_verdict`. The classifier's replay is diagnostic only and is not used here.

## What ran

Six frozen records on `main`, all with EB0's settings:
- `confinement: extension`, purpose `development`, k = 3, rung R1-plan
- 48,000 tokens and 72 turns, with the line declared at 32,000 tokens and 48 turns
- backstop 4,800 s, Ornith 1.5 9B on oMLX, Apple M5 Max

The Engine arm file pins `23a0ef6` (`arms/engine-ornith15-9b.json`, sha256 `a79fa458…`), checked out at `../satyrn-engine` with `SATYRN_ENGINE_REPO` unset. The Baseline arm is `arms/baseline-ornith15-9b.json` (sha256 `e98db028…`, the same digest as EB0's Baseline). Both task-tree digests equal EB0's. Each record had a clean preflight with no problems and both self-tests at exit 0. Every sitting is `complete`, with one sitting, 0 replaced and 0 infrastructure cells. The stage-2 records were launched by a detached chain that committed each result only after `just gates` exited 0.

| stage | record | arm | n | evals head | sitting (EDT) | record / result commit |
|---|---|---|---|---|---|---|
| 1 | eb-s1-engine-selfhost-guard-prefixes | Engine | 6 | `cd8fedc` | 19:27–20:28 | `cd8fedc` / `64d95d1` |
| 1 | eb-s1-engine-selfhost-review-script | Engine | 6 | `cd8fedc` | 20:31–20:58 | `cd8fedc` / `64d95d1` |
| 2 | eb-s2-baseline-selfhost-guard-prefixes | Baseline | 12 | `7ca02ea` | 21:45–22:41 | `7ca02ea` / `8b12cc2` |
| 2 | eb-s2-engine-selfhost-guard-prefixes | Engine | 6 | `8b12cc2` | 22:45–23:39 | `7ca02ea` / `84ed348` |
| 2 | eb-s2-baseline-selfhost-review-script | Baseline | 12 | `84ed348` | 23:41–00:27 | `7ca02ea` / `e11efa0` |
| 2 | eb-s2-engine-selfhost-review-script | Engine | 6 | `e11efa0` | 00:31–01:00 | `7ca02ea` / `a2ef909` |

The stage-2 Engine records name their stage-1 results as `previous_result`. The reader combines stage 1 and stage 2 Engine cells only because they share the task, the arm digest and the contract digest (`read.txt`, "COMBINED").

## The decider: output tokens per delivered pass

Medians are given with min–max. The denominator is 12 cells per arm per task, with no cells missing.

| task | arm | delivered | tokens per delivered pass | admitted-only (secondary) |
|---|---|---|---|---|
| guard-prefixes | Engine | 9 / 12 | **28,463** (11,681–41,909) | 28,463, n = 9 |
| guard-prefixes | Baseline | 8 / 12 | **5,510** (2,308–19,599) | 4,052, n = 6 |
| review-script | Engine | 6 / 12 | **10,828** (7,352–20,944) | 10,828, n = 6 |
| review-script | Baseline | 11 / 12 | **10,970** (8,194–27,976) | 10,970, n = 11 |

Cross-arm pass pairs:
- guard-prefixes: the Engine is higher in 66 of 72 (92 %).
- review-script: the Engine is higher in 32 of 66 (48 %), and Baseline in 34.

The Engine stage-1 and stage-2 medians agree on guard-prefixes: 28,463 (n = 5) and 27,793 (n = 4). On review-script they are 15,044 (n = 2) and 10,416 (n = 4).

A secondary figure, not the EB decider, counts the spend of the cells that did not deliver. It is all output tokens across the 12 cells divided by delivered passes, from the per-cell `out_tok` column of `read.txt`:
- guard-prefixes: Engine 346,476 / 9 = 38,497, against Baseline 191,100 / 8 = 23,888.
- review-script: Engine 149,080 / 6 = 24,847, against Baseline 144,983 / 11 = 13,180.

**Reading.** At `23a0ef6`, guard-prefixes still shows the floor cost gap, at about 5.2× Baseline per pass. EB0 at `1869397` showed about 3.3×, but the two ratios are different pins on a moved harness and are not compared as a change. On review-script the per-pass cost is at parity, but the Engine delivers half its cells against Baseline's 11 of 12. Baseline's own review-script median is 10,970, against EB0's 8,047 on the older harness.

## Schema-rejected edit calls (what parity removed)

| task | arm | schema-rejected | cells with ≥ 1 | all rejected edit/write, by shape |
|---|---|---|---|---|
| guard-prefixes | Engine | 10 | 4 / 12 | 26: schema 10, ANCHOR_MISSING 7, scope 5, NO_CHANGE_REQUESTED 2, ANCHOR_ALREADY_APPLIED 2 |
| guard-prefixes | Baseline | 9 | 4 / 12 | 22: schema 9, Pi anchor 6, Pi no-change 4, confinement 3 |
| review-script | Engine | 0 | 0 / 12 | 8: ANCHOR_MISSING 3, NO_CHANGE_REQUESTED 2, INVALID_REQUEST 2, REVISION_STALE 1 |
| review-script | Baseline | 4 | 3 / 12 | see `read.txt` |

At EB0's harness and pin (`1869397`) the Engine had 6 schema rejections on each task. At `23a0ef6` it has 0 on review-script, against Pi's own 4 under Baseline. On guard-prefixes its 10 are level with Pi's own 9 under Baseline, so the rejections that remain are shapes Pi also refuses. That fits the corrected parity claim (Pi 0.85.1's `edit` never hoists; hoisting is an EB2 remedy).

## Admission, refusals, cuts

| task | arm | admitted | confinement refusals (cells) | Engine scope refusals (cells) | wall-clock cut | other non-verdict codes |
|---|---|---|---|---|---|---|
| guard-prefixes | Engine | 12 / 12 | 0 | 5 (4) | 0 | — |
| guard-prefixes | Baseline | 9 / 12 | 3 (3) | — | 0 | BUDGET_EXCEEDED 3 (72 turns) |
| review-script | Engine | 12 / 12 | 0 | 0 | 0 | NO_PATCH 1 |
| review-script | Baseline | 12 / 12 | 0 | — | 0 | — |

Baseline's three refusals are `write` calls to `/tmp/patch.py`, `/tmp/test_lead.py` and `/tmp/build_regex.py`. This is the known asymmetry: confinement refuses Baseline's scratch writes outside the worktree. Two of those cells delivered passes. They count under the decider, and are left out of the admitted-only column. No wall-clock cut occurred on any night, so none is named.

## Pass at the 32,000-token, 48-turn line (`grade-line`)

| task | arm | line pass | excluded (`unavailable`) |
|---|---|---|---|
| guard-prefixes | Engine | 6 / 10 (s1 3/5, s2 3/5) | 2 |
| guard-prefixes | Baseline | 8 / 9 | 3 |
| review-script | Engine | 6 / 12 (s1 2/6, s2 4/6) | 0 |
| review-script | Baseline | 10 / 12 | 0 |

Each exclusion is a crossing whose harvested tree the grader scored `unavailable`. `grade-line` leaves its `line_unavailable_reason` empty, and the reasons below come from each line grade's own `receipt.json`.
- **Two "patch touches non-source path" (Baseline):** the scratch files `tools/hooks/_t10.py` and `_tmp_build_regex.py`.
- **Three "executed tests mismatch expected" with 0 tests executed:** Engine cells `234629-787857` and `024539-666254`, and Baseline cell `014535-299258`.

The second kind is the instrument defect `docs/lessons.md` records ("The model wrote tests, edited them twice, and never ran one"). When the solver's own code fails test collection, the grader scores `unavailable`, not `fail`. One Engine guard-prefixes cell (`024539-558164`) was also graded `unavailable` this way at its final verdict.

These exclusions change line denominators only, not any delivered pass or the decider. Line rates here are development readings at n = 12, never pooled with C3 or the run-record-gate development read.

## Stage-1 review-script diagnosis (2 of 6 against EB0's 5 of 6)

This was diagnosed offline by a Sonnet agent from the hook-written evidence. Two claims were spot-checked against the receipts by the drafting agent: `005058-171727`'s `engine-receipt.json` (`discarded`, `COMMAND_CHANGED_HEAD`) and `003128-881600`'s `receipt.json` reason. Stage 1's four non-passes:

- **`003128-881600`, `unavailable`.** The model's own test writes `docs/reviews/already-there.md` by relative path, and running it from the worktree root put that file in the patch. The task code never writes this path.
- **`005058-171727`, `NO_PATCH`.** After the finish nudge, the model ran `git commit`, following the contract's "Record and commit" step. The Engine discards a candidate whose command moved HEAD. This rule is unchanged between `1869397` and `23a0ef6`.
- **`003922-224067` and `004222-519596`, fail.** Both fail the hidden test `test_review_path_encodes_range_and_model`. The contract does not say whether `review_path` prefixes `root`; one cell made it an orchestrator and the other dropped `root` and rewrote its own test to agree. EB0's single Engine fail on this task was the same test.

The agent's verdict was variance and model behaviour, with no visible pin mechanism, at a one-sided Fisher p = 0.12 for 5/6 against 2/6. Stage 2's Engine cells went 4 of 6. They also had one more stray-file `unavailable` (`docs/reviews/abc123..def456-zai-glm-5.3.md`), and so did Baseline (`docs/reviews/a..b-zai-glm-5.3.md`). The stray-file exclusion therefore hits both arms.

The agent also re-ran the current `confinement.audit` on EB0's review-script transcripts. Every EB0 "reach" there is the cell's own `tests/test_review.py`, which the current rule (`df3b68f`) marks in-worktree and ignores. Under that rule, EB0's review-script cells are admitted.

## Open for the maintainer (nothing here rules)

1. **The floor set.** EB1 set it to {guard-prefixes, review-script} from EB0's `1869397` cells, with the rule "both arms deliver ≥ 4 of 6, and one arm higher in ≥ 3 of 4 pass pairs". At `23a0ef6`, review-script would not meet that rule read as proportions: the Engine delivers 6 of 12, and it is higher in 32 of 66 pairs. guard-prefixes would (9 and 8 of 12; 66 of 72). Under AGENTS.md "Evidence has a harness", EB1's floor set rests on old-pin cells. Whether review-script stays in the floor set at this pin is a ruling.
2. **Is the review-script contract a prompt defect?** Its ambiguity over `review_path` prefixing `root` caused two of the stage-1 non-passes. It applies to both arms and is not in `KNOWN_DEFECTS.md`.
3. **EB1's "admission is arm-asymmetric".** EB0's review-script reaches are stale-instrument artifacts. Whether that EB1 finding rests on them is not checked here.
4. **The collection-error `unavailable`** (`docs/lessons.md`) excluded three line crossings and one final verdict on guard-prefixes. The strip-rule sensitivity read would answer the stray-file exclusions offline.
5. **EB3's power** for its parity rule can now be computed at 12 per arm from these cells. It is not computed here.
