# R0 sitting — input sheet (2026-09-19)

Drafted by Fable at the maintainer's request. Inputs only; every decision below
is the maintainer's. Nothing pools across tasks, arms, nights or engine commits.
Engine cells are route-proof cells: excluded from every denominator, read for
direction only. Sources: `evidence/2026-09-16-census/` (signed), the three
route-proof results under `records/`, `$HOME/satyrn-route-proof-2-analysis/`.

## 1. Three readings of "the Engine helps", per claim task

| reading | what counts | instrument |
|---|---|---|
| A. delivered inside the line | the cell ends by itself with a pass at or under 32,000 tokens and 48 turns | `verdict` plus where the cell stopped |
| B. pass state at the line | the tree passes the hidden suite when the cell crosses the line, whether or not it stops | harvested `line_verdict` (new, direct) |
| C. delivered inside the budget | the cell ends by itself with a pass within 48,000 tokens and 72 turns | `verdict`, no reconstruction at all |

### selfhost-run-record-gate

| arm, night | cells | A | B | C | passing tree never delivered |
|---|---|---|---|---|---|
| Baseline, census 1 | 6 | 1 | 5 (replay) | 2 | 1 tripped pass; 3 wall-clock-cut |
| Baseline, census 2 | 3 | 0 | 3 (replay) | 1 | 2 tripped pass |
| Engine `0b496d8`, void night | 2 | 0 | not measured | 0 | trigger unreachable; read nothing from it |
| Engine `2cccef1`, proof 2 | 2 | 0 | 1 (replay) | 0 of 2 recorded; 1 clean stop with a passing tree discarded by the pipe defect, 1 budget-exceeded with a passing final tree | 2 |

### selfhost-docs-linter

| arm, night | cells | A | B | C | passing tree never delivered |
|---|---|---|---|---|---|
| Baseline, census 1 | 6 | 1 | 4 (replay) | 4 | 1 tripped pass |
| Engine `0b496d8`, void night | 2 | 0 (both stopped by the Engine's own 32,000 stop at about 32,200, pass) | not measured | 2 | 0 |
| Engine `2cccef1`, proof 2 | 2 | 0 | 2 (replay) | 0 of 2 recorded; both clean stops with passing trees, discarded by the pipe defect | 2 |
| Engine `0a6e5df`, proof 3 | 2 | 0 | not harvested | 2 | 0 |

B for Baseline comes from the transcript replay, which drops bash-made source
changes (11 of 45 census cells) and can only understate it.

## 2. What the numbers say, plainly

1. **Reading A is not supported for the Engine.** No Engine cell of ten has
   delivered inside the line. Engine cells that stop cleanly stop at 36,339 to
   41,298 tokens. Baseline delivers inside the line in 2 of 15.
2. **Reading B gives the Engine no room.** Baseline already holds a pass state
   at the line in 8 of 9 and 4 of 6 cells. That was the finishing finding: the
   trees pass, the cells do not stop. B cannot show a finishing remedy working.
3. **Reading C is where the Engine's direction shows.** Cells with a passing
   final tree that was never delivered: Baseline 4 of 15 (tripped pass) plus 3
   wall-clock cuts; Engine, once the pipe defect is fixed, 0 of 2. With the
   defect's three discards counted as the deliveries they would have been,
   Engine docs-linter is 6 of 6 and run-record-gate 1 of 2 plus one passing
   tree at the budget. This is ten excluded cells over three engine commits:
   a direction, not a rate.
4. **The Engine may reach a pass state later than Baseline.** First hidden-suite
   pass, output tokens: Baseline run-record-gate 9,081 to 39,873, median near
   13,000; Engine 21,085 and none. Baseline docs-linter 11,676 to 32,481;
   Engine 25,680 and 30,136. Two cells per task; the pilot must check it,
   because an Engine that slows the build can lose on C as well.
5. **Cost secondary.** Baseline rarely stops by itself before the budget (one of
   nine night-2 cells). Steered Engine cells stopped 2 to 3 turns after the
   steer. Tokens-to-candidate is a plausible declared secondary under C.

## 3. Decision 1: which reading the claim uses

| option | claim text | Baseline rate to beat | risk |
|---|---|---|---|
| C, recommended | delivers a passing candidate within the record's budget more often than bare Pi, and stops when the developer's tests are green | 3 of 9; 4 of 6 | docs-linter has little headroom |
| A | the same, within 32,000 tokens and 48 turns | 1 of 9; 1 of 6 | Engine is 0 of 10 so far; needs green to arrive much earlier |
| B | holds a passing tree at 32,000 tokens | 8 of 9; 4 of 6 | no room; measures the wrong thing |

Under C the primary instrument is the final `verdict`, which needs no replay and
no harvest, with the harness alone stopping both arms at the budget. The
harvested line stays a declared secondary (it shows where the pass state sits)
and the replay a flagged tertiary.

## 4. Sizing (one-sided Fisher exact, alpha 0.05, n per arm, per task)

| reading, task | Baseline | Engine assumed | n=12 | n=16 | n=20 | n=24 | n=30 |
|---|---|---|---|---|---|---|---|
| C, run-record-gate | 0.33 | 0.60 | 0.30 | 0.33 | 0.37 | 0.49 | 0.56 |
| C, run-record-gate | 0.33 | 0.70 | 0.49 | 0.56 | 0.63 | 0.77 | 0.84 |
| C, run-record-gate | 0.33 | 0.80 | 0.71 | 0.79 | 0.87 | 0.94 | 0.97 |
| C, docs-linter | 0.67 | 0.90 | 0.26 | 0.31 | 0.43 | 0.53 | 0.61 |
| C, docs-linter | 0.67 | 0.95 | 0.40 | 0.48 | 0.65 | 0.76 | 0.83 |
| A, either | 0.13 | 0.30 | 0.15 | 0.17 | 0.25 | 0.31 | 0.36 |
| A, either | 0.13 | 0.50 | 0.52 | 0.61 | 0.75 | 0.82 | 0.91 |

A cell is about 50 minutes at k = 3, so n = 24 per arm on one task is about
13 hours of GPU: two nights per task, four for both. docs-linter is
underpowered at any affordable n unless the Engine is near-perfect; a
run-record-gate-only claim at n = 24 is the cheapest honest comparison, with
docs-linter reported as a secondary.

## 5. Decision 2: the pilot (drafted, not frozen)

`records/2026-09-20-pilot-selfhost-run-record-gate.json` and
`…-selfhost-docs-linter.json`: both arms interleaved, n = 3 per arm, k = 3,
48,000 / 72, line 32,000 / 48 declared, backstop 4,800 s, isolated, purpose
development, excluded from every comparison denominator. About 3.5 hours.
It answers, before any deciding night: the exclusion rate of `line_verdict`
on the Engine arm; the sharper steer's first live read (turns from steer to
stop, and whether lint cleanup recurs); whether the Engine reaches a pass
state later than Baseline (item 4 above); the first same-night, same-machine
Baseline and Engine rates under reading C; and the line harvest live on both
arms. Stop rule for going on: if the Engine's C rate on run-record-gate is
not above Baseline's in the pilot's own cells, the design returns to the
maintainer before any comparison spend.

## 6. Decision 3: win rule and n, after the pilot

To pre-register: the reading (section 3), per-task one-sided Fisher at 0.05,
how many tasks must win (one named primary task, or both), n per arm from the
pilot's rates and section 4, the secondaries (tokens and turns to candidate,
`line_verdict` with its exclusion column, floor parity), and the rule that a
cell replaced for infrastructure is reported beside its replacement.

## 7. Open items that do not block the sitting

The authored task `selfhost-preflight-quiet` stays the development task (prompt
ambiguity recorded); census "reached" figures are replay-based and can only be
understated; speed-probe stays dropped; the large tier stays unclaimed.
