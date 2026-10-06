# Does the Engine deliver more often than bare Pi on run-record-gate? — yes

**Result page, 2026-10-06.** The evidence page is [`evidence/2026-10-05-rrg-delivery/README.md`](../../evidence/2026-10-05-rrg-delivery/README.md). The rule was pre-registered before any cell existed ([pre-registration](../superpowers/specs/2026-10-05-run-record-gate-delivery-comparison.md): approved `e9b3aa9`, amended `9a5e668`). The reader was built and frozen on synthetic cells before launch, and the one deciding read ran after all 72 cells finished.

## The question

On `selfhost-run-record-gate`, a medium self-hosted build task, under confinement: does the pinned Engine deliver a passing patch within the run budget (48,000 output tokens, 72 turns) more often than bare Pi, with the same model (Ornith 1.5 9B)?

## The answer

| | Baseline (bare Pi) | Engine (`23a0ef6`) |
|---|---|---|
| cells | 36 | 36 |
| delivered a passing patch | **10** | **22** |
| one-sided Fisher exact p | | **0.0043** |
| admitted cells only | 10 of 35 | 22 of 36 (p = 0.0056) |

**It holds:** the pre-registered rule rejects on both the primary and the admitted-only count. The claim is that and no more: on this one task, with this model and this budget, under confinement, the Engine delivers more often than bare Pi.

## Why

This is a finishing result, not a capability result. Both arms usually reach a passing tree; the Engine stops holding it more often.

| | Baseline | Engine |
|---|---|---|
| passes the hidden tests at the 32,000-token line (`unavailable` excluded) | 29 of 33 | 28 of 34 |
| cut off by the budget | 26 of 36 | 8 of 36 |
| held a passing tree when the budget cut it | 22 of 26 | not measured (the harness does not harvest the Engine arm at the cut) |
| delivered | 10 of 36 | 22 of 36 |

Bare Pi keeps working past a passing state until the budget cuts it off; 32 of its 36 cells ended holding a passing tree. The Engine's finish nudge fired in 34 of 36 cells, and the delivered cells stopped a median of four turns after it. Per delivered pass, bare Pi spent 143,848 output tokens against the Engine's 60,400 (total output tokens divided by delivered passes).

## Limits

- One task, one model, one budget, one machine (Apple M5 Max); nothing pools with other reads.
- The delivery endpoint was chosen after the development reads were seen. The pre-registration discloses this, and the readings it used are committed.
- The Engine's two stray-file `unavailable` cells and three discarded candidates count against it.
- One harness asymmetry runs against the Engine: when the model runs `git commit` in its worktree (the task's last step says to), Baseline's harvest keeps the work and the Engine discards it. Baseline committed in 9 cells, 6 of them among its 10 passes; the Engine's 3 discards are exactly its in-worktree commits. The claim is conservative with respect to it ([review](../../evidence/2026-10-06-eb-replan/README.md) §1.6, §2).
- That asymmetry is fixed at engine `9aecfb5`: the Engine now keeps the candidate when the model leaves a detached HEAD that moved ([ledger](../../evidence/2026-09-15-release-one-decision-ledger.md), "Engine re-pin for head tolerance"). The comparison stays decided at `23a0ef6` and is not re-read. Cells at `9aecfb5` are a new Engine condition and never pool with these.
- Earlier at-line readings from the classifier's replay (C3, C4) are unconfirmed and play no part here.

## Recompute

```
R=~/satyrn-runs/2026-10-05-campaign-selfhost-run-record-gate
P=records/2026-10-05-campaign-selfhost-run-record-gate
uv run python evidence/2026-10-05-rrg-delivery/decide.py $R-a $P-a.json $R-b $P-b.json $R-c $P-c.json
```
