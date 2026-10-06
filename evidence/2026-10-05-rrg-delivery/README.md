# The run-record-gate comparison on delivery: holds (2026-10-06)

The deciding read of the pre-registered comparison: `docs/superpowers/specs/2026-10-05-run-record-gate-delivery-comparison.md`, approved at `e9b3aa9` and amended in §10 at `9a5e668`. It was made once, after all three pieces completed, by `decide.py` in this directory. That reader is frozen at sha256 `44573d17ab2ac87f643a20cecfecebdac6d878fe3646aa5f6182626b582c9aad` (`7b2d60a`), and the digest was checked immediately before the run. The tree was clean apart from one untracked draft file unrelated to this read. Its output is `decision.txt`.

```
R=~/satyrn-runs/2026-10-05-campaign-selfhost-run-record-gate
P=records/2026-10-05-campaign-selfhost-run-record-gate
uv run python evidence/2026-10-05-rrg-delivery/decide.py $R-a $P-a.json $R-b $P-b.json $R-c $P-c.json
```

## What ran

There were three `campaign` records, identical apart from `authority` and `decision_rule` (`25b4dd6`). Each was n = 12 per arm, with the arms interleaved at k = 3, on `selfhost-run-record-gate` R1-plan (task tree `068f216e…`):
- **Arms:** Baseline `arms/baseline-ornith15-9b.json`; Engine `arms/engine-ornith15-9b.json` at engine `23a0ef6`.
- **Model and hardware:** Ornith 1.5 9B on oMLX, Apple M5 Max.
- **Condition:** `confinement: extension`.
- **Budgets:** 48,000 tokens and 72 turns; the line declared at 32,000 and 48; backstop 4,800 s.

| piece | sitting (EDT) | result commit | status | replaced | infrastructure |
|---|---|---|---|---|---|
| a | 2026-10-05 15:23–21:02 | `1ddc1dd` | complete | 0 | 0 |
| b | 2026-10-05 21:06 – 10-06 02:47 | `36fc1c4` | complete | 0 | 0 |
| c | 2026-10-06 02:51–07:57 | `c908919` | complete | 0 | 0 |

The chain launched each piece only after the previous result was committed on green gates. No wall-clock cut, no stop, no resume. Piece a's operational facts were reported in session before piece b ran, and no verdict was read before the deciding read.

## The decision (pre-registered §4–§5)

| reading | Baseline delivered | Engine delivered | one-sided Fisher p | rejects |
|---|---|---|---|---|
| **primary** (`unavailable` Baseline-favouring; reach cells excluded) | **10 / 36** | **22 / 36** | **0.0043** | yes |
| **admitted only** | 10 / 35 | 22 / 36 | 0.0056 | yes |
| beside (`unavailable` excluded from both) | 10 / 36 | 22 / 34 | 0.0020 | yes (not deciding) |

**Verdict: holds.** The primary and the admitted-only readings both reject at α = 0.05.
- **Reclassified under D2:** two Engine `unavailable` cells count as not delivered: `20261005-200221-102589` in piece a and `20261006-054648-457847` in piece b.
- **Excluded from the admitted count:** one Baseline cell with a confinement refusal, `20261006-055606-066842` in piece b.
- **Reach cells:** none.

**The claim (§1):** on one medium self-hosted task under confinement, the pinned Engine (`satyrn-engine` `23a0ef6`) driving Ornith 1.5 9B delivers a passing patch within 48,000 output tokens and 72 turns more often than bare Pi with the same model. One task, one model, one budget. It does not pool with any other read.

## Secondaries (§5, reported, never deciding)

| figure | Baseline | Engine | source |
|---|---|---|---|
| attempt codes | `BUDGET_EXCEEDED` 26, `OK` 10 | `OK` 25, `BUDGET_EXCEEDED` 8, `NO_PATCH` 3 | `read.txt` |
| harness verdicts | pass 10, none 26 | pass 22, none 11, unavailable 2, fail 1 | `read.txt` |
| pass at the 32k/48 line (`grade-line`, `unavailable` excluded) | 29 of 33 (a 11/12, b 10/12, c 8/9; 3 excluded) | 28 of 34 (a 9/12, b 8/11, c 11/11; 2 excluded) | `grade-line-{a,b,c}.json` |
| total output tokens ÷ delivered passes | 1,438,481 ÷ 10 = 143,848 | 1,328,806 ÷ 22 = 60,400 | transcripts, see below |
| median output tokens per delivered pass | 36,800 (31,532–42,852) | 32,902 (21,192–46,850) | `read.txt` |
| turns, median over all cells; cells ending at 72 turns | 72; 20 of 36 | 46.5; 3 of 36 | transcripts, see below |
| confinement refusals; reaches | 1 cell; 0 | 0; 0 | `read.txt` |
| Engine scope refusals | — | 7 entries in 7 cells | `read.txt` |

Reading them together: at the line both arms usually hold a passing tree (29 of 33 against 28 of 34). The difference is finishing. Baseline keeps working past a passing state until the budget stops it, in 26 of 36 cells, so it delivers 10. The Engine stops and delivers in 22. Per delivered pass, Baseline spends about 2.4 times the Engine's output tokens.

The totals and turns come from `transcript.txt` (the `usage.output` of each assistant `message_end`, and the count of assistant `message_end` events), over the 36 finished slots per arm. They were computed with a short stdlib loop in session and are reproducible from the retained nights. They are not in a frozen instrument, which is allowed for secondaries (§5).

## Limits

- One task, one model, one budget, one machine. The claim is that and no more.
- The Engine's three `NO_PATCH` cells are discarded candidates, and its two `unavailable` cells are stray files. Under D2 all five count against it.
- The planning inputs (§6) were a Baseline delivery of about 1 in 3 and an Engine delivery of 0.67. The observed rates, 10/36 (0.28) and 22/36 (0.61), sit close to those inputs.
- The endpoint was chosen after the development reads were seen, and the pre-registration discloses that (§2). The replay-based at-line readings of C3 and C4 remain unconfirmed and play no part here.
