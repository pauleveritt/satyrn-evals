# The numbers — release two

<div class="record-metadata" markdown="1">

Drafted by Fable 2026-09-20 from the committed results under `records/` and the
retained cells under `~/satyrn-runs/`. Nothing here pools across tasks or arms.
The comparison was pre-registered on 2026-09-19 (the `decision_rule` of each
`records/2026-09-21-comparison-*.json`, frozen at `cdae9b1` before any cell
ran) and read once, when complete.

</div>

## What was compared

| | Baseline | Engine |
|---|---|---|
| agent | bare Pi 0.85.1 | Pi 0.85.1 with `/implement`, satyrn-engine `78ab87d` |
| model | Ornith 1.5 9B, MLX 8-bit, served by oMLX | the same |
| sampling, context, per-turn cap | temperature 0.6, top-p 0.95, top-k 20; 262,144; 16,000 | the same |
| task prompt | the task's R1-plan text (R2 for depth-3) | the same text, inside the Engine's contract |
| budget | 48,000 output tokens, 72 turns, 4,800 s backstop | the same, stopped by the harness alone |
| isolation | model runs as a second user with no view of grader material | the same |

One machine, arms interleaved three cells at a time on the same nights
(2026-09-19 14:37 to 2026-09-20 10:01). 108 cells, 0 infrastructure failures,
0 wall-clock timeouts, 0 replaced cells. A **delivered pass** is a cell that
stopped by itself with a patch the hidden test suite passes; running out of
budget, a rejected patch and a failing patch all count as not delivered.

## The claim, and the test that decides it

> On medium-build tasks, `/implement` delivers a passing candidate within the
> task's budget more often than bare Pi, on Ornith 1.5 9B, and stops when the
> developer's tests are green.

Primary, pre-registered: `selfhost-run-record-gate`, 24 cells per arm (two
records of 12, read together), one-sided Fisher exact test at 0.05.

| reading | Baseline | Engine | p |
|---|---|---|---|
| delivered pass, as graded | 2 of 24 | 16 of 24 | 0.000029 |
| pre-registered sensitivity: stray non-source files stripped, both arms | 3 of 24 | 17 of 24 | 0.000044 |
| part A alone (reported, not tested) | 2 of 12 | 8 of 12 | |
| part B alone (reported, not tested) | 0 of 12 | 8 of 12 | |

**The win rule is met.** What the Engine changed is delivery, not ability: 21
of Baseline's 24 cells ran out of budget, and at least 18 of those 21 held a
tree that passes the hidden suite. Bare Pi builds the change, keeps working
(coverage runs, lint, provenance, commits, re-verification) and never hands
it over. The Engine's 8 non-deliveries: 6 out of budget, 1 with no patch, 1
with a patch rejected for a stray `record.json`.

## Where it did not help, and what it costs

| task | kind | Baseline delivered | Engine delivered | one-sided p |
|---|---|---|---|---|
| `selfhost-docs-linter` | medium build, secondary, n = 12 | 7 of 12 | 8 of 12 | 0.50 |
| `agentclinic-repair-depth-3` (R2) | small repair, floor, n = 6 | 6 of 6 | 6 of 6 | |
| `selfhost-guard-prefixes` | small build, floor, n = 6 | 4 of 6 | 4 of 6 | |
| `selfhost-review-script` | small build, floor, n = 6 | 2 of 6 | 5 of 6 | 0.12, not tested |

1. **The effect was shown on one of two medium-build tasks.** On docs-linter
   bare Pi finishes by itself often enough that the Engine adds nothing
   measurable at n = 12; the record said in advance it was underpowered.
2. **The declared floor-parity secondary fails.** On tasks both arms pass,
   the Engine costs more, not the same:

| floor task | Baseline, median per delivered pass | Engine |
|---|---|---|
| depth-3 | 5,682 tokens, 13 turns, 3 min | 8,066 tokens, 16 turns, 5 min |
| guard-prefixes | 8,042 tokens, 14 turns, 5 min | 18,740 tokens, 24 turns, 15 min |
| review-script | 6,682 tokens, 24 turns, 5 min | 10,737 tokens, 17 turns, 11 min |

   The Engine's self-test runs and guard messages are real overhead, and on
   a ten-turn fix they do not pay for themselves. `/implement` is for a
   build, not a small repair.
3. **Large builds are not claimed.** In the census, 18 of 18 Baseline cells on
   the two large tasks reached no passing state; the Engine refuses requests
   above the medium class with an advisory (at most 2 non-test files and 10
   produced symbols). Of guards 1 to 3, the loop breaker and symbol preservation
   never fired and scope refusal fired five times in 36 cells; none is claimed.

## Cost on the primary task

| per cell, median (range) | Baseline | Engine |
|---|---|---|
| turns | 73 (39 to 73) | 52 (25 to 72) |
| output tokens | 40,108 (26,596 to 48,125) | 39,125 (24,684 to 48,743) |
| minutes, three cells sharing the GPU | 43 (26 to 50) | 44 (23 to 57) |
| tool calls | 72 | 51 |

| per delivered pass | Baseline | Engine |
|---|---|---|
| machine time | 8.5 cell-hours | 1.1 cell-hours |
| output tokens | about 473,000 | about 58,000 |
| delivered inside 32,000 tokens and 48 turns | 1 | 7 |

An attempt is not faster with the Engine; a usable result is about eight
times cheaper, because most attempts end in one.

## How the Engine behaved (Engine arm only)

| | run-record-gate, 24 cells | docs-linter, 12 cells |
|---|---|---|
| cells steered at own-green | 20 | 11 |
| steered twice or more | 5 | 0 |
| median turns from first steer to stop (range) | 5 (2 to 25) | 2 (1 to 11) |
| stopped within three turns of the first steer | 7 of 17 | 7 of 9 |
| steered and delivered a pass | 16 | 8 |
| runaway resumes, followed by a tool call | 1, 1 | 1, 1 |
| test runs detected in bash output | 52 | 28 |
| scope refusals | 4 | 1 |
| receipts with the live budget counter intact | all | all |

The steer is a brake, not a stop: models read it and often do a few more
turns of forbidden finishing work (full-suite runs, `just` recipes) before
stopping. It is a nudge by design; release one's cell 511653 fixed its last
failing case five turns after its own suite went green.

**Pass state at the 32,000-token / 48-turn line, harvested** (secondary; the
raw tree at the crossing on both arms, or the final verdict for a cell that
never crossed; always read with its exclusion column):

| task | Baseline, passing at the line | excluded | Engine | excluded |
|---|---|---|---|---|
| run-record-gate, parts A and B | 16 of 18 | 6 | 22 of 24 | 0 |
| docs-linter | 11 of 12 | 0 | 9 of 11 | 1 |

Both arms mostly hold a passing tree at the line; this reading cannot show a
finishing remedy working and is not the claim. The excluded cells are trees
the grader refuses for a stray non-source file, six of seven on Baseline.

## Disclosures

- **The Engine's own messages are the product and differ between arms by
  design:** the contract prompt, compact self-test results with pytest's `E`
  lines, the finish-on-green steer, the runaway resume, the fenced
  bounded-command note (first bash result and timeouts only), and the note
  appended when the Engine detects a test run in bash output and runs its own
  self-test. Task text, tools available, model, sampling and budgets are
  identical.
- **Route to this claim.** Release one ended in a stated negative
  (`docs/superpowers/specs/2026-09-15-release-one-outcome.md`). Release two ran
  a 45-cell Baseline census first, then three route proofs (one void), a
  12-cell pilot and this comparison. Route-proof and pilot cells are excluded
  from every count above. The claim's reading (delivered within the budget,
  not within 32,000 tokens) was chosen on 2026-09-19 after the route proofs
  and before the pilot and the comparison; the input sheet is
  `evidence/2026-09-19-r0-inputs/README.md`.
- **One model, one machine, tasks cut from this project's own history.** The
  hidden suites are in this repository from the day it is published, so later
  models may have seen them.
- **Known instrument gap:** for Engine cells stopped at the budget, the
  harvested tree is read from the wrong worktree, so "held a passing tree" is
  unavailable for those six cells. It touches no count on this page.

<div class="record-recompute" markdown="1">

## Recompute

```bash
cd satyrn-evals
G=$HOME/satyrn-comparison-grades; R=records/2026-09-21-comparison; N=$HOME/satyrn-runs/2026-09-21-comparison
uv run satyrn-evals grade-sensitivity $N-selfhost-run-record-gate-a --record $R-selfhost-run-record-gate-a.json \
  --combine $N-selfhost-run-record-gate-b --record2 $R-selfhost-run-record-gate-b.json --grade-root $G
uv run satyrn-evals grade-line $N-selfhost-docs-linter --record $R-selfhost-docs-linter.json --grade-root $G
```

</div>
