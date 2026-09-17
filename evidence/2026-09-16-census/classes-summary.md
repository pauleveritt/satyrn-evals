# The class columns, read across both nights

Reviewer's cross-task reading of the 39 filled `classes.md` tables, 2026-09-17,
for the maintainer's sign-off. Nothing pools across tasks. The primary is the class
whose removal would have changed the verdict at the 32,000-token, 48-turn line;
per-cell arguments and turn citations are in each `<task>/classes.md`.

## Counts per task and night: True columns, then primary distribution

| task | night | cells | info | ambig | capab | budg | finish | runaway | hunt | allow | primaries |
|---|---|---|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | `-` 6 |
| selfhost-run-record-gate | 1 | 6 | 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | finishing 4, budget 1, `-` 1 |
| selfhost-run-record-gate | 2 | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | finishing 3 |
| selfhost-docs-linter | 1 | 6 | 0 | 0 | 1 | 1 | 3 | 0 | 0 | 0 | finishing 3, budget 1, capability 1, `-` 1 |
| selfhost-cell-loop | 1 | 6 | 0 | 0 | 6 | 0 | 0 | 3 | 1 | 0 | capability 3, runaway 3 |
| selfhost-cell-loop | 2 | 3 | 0 | 0 | 3 | 0 | 0 | 2 | 0 | 0 | capability 1, runaway 2 |
| selfhost-speed-probe | 1 | 6 | 0 | 4 | 6 | 0 | 0 | 2 | 1 | 0 | capability 4, runaway 2 |
| selfhost-speed-probe | 2 | 3 | 0 | 2 | 3 | 0 | 0 | 1 | 0 | 0 | capability 2, runaway 1 |
| **all** | **1+2** | **39** | **0** | **6** | **19** | **2** | **10** | **8** | **3** | **0** | capability 11, finishing 10, runaway 8, `-` 8, budget 2 |

`information` and `allowlist` are False on all 39; `raised` is `-` on all 39; no cell
has a task defect as its primary. **One correction to the draft census page:** README
bullet 4 says runaway is "8 of 30 build cells" — 8 is the count over both nights
(33 build cells), night 1 alone being 5 of 24. The eight are cell-loop 442168, 346861,
332393, 225004, 507079 and speed-probe 691593, 524583, 771490.

## The medium tier: which cells are finishing, and what they did after green

Ten finishing primaries — 7 of 9 run-record-gate, 3 of 6 docs-linter. All reached
a hidden-suite pass state inside the line and none stopped there. The post-green
work is one narrow family, and none of it touches the graded contract:

- **Gates the task never asked for.** 275888 chased `fail_under = 100` on modules
  it had not written (t29–t39), then ruff (t40–t43) and pyrefly (t44); 016509 did
  the same and established at t41 and t45 that every missing line was pre-existing
  `cli.py` dispatch; 891860 spent t46–t61 on ruff import order and pyrefly; 949626
  spent t51–t67 hunting one missing branch arrow, `162->172`, in its own coverage
  report, writing debug output from inside `gate` at t66 to prove the gate ran.
- **The cell's own test scaffolding.** 609675 spent 42 turns and 23,194 tokens —
  the widest gap in the census — on the `str("")` predicate footgun (t28), a digest
  fixture (t43) and `capsys`/`types` imports (t54–t57), its own green arriving only
  at t52. 533788 and 470484 are the same shape; 470484 at t47 and t50 stashed its
  own `cli.py` and overwrote its own `test_cli.py` from `HEAD` for a baseline.
- **Counting its own tests to the prompt's number.** The docs-linter prompt's "→ 9
  passed" reads as a requirement: 453263 deleted three of its own tests from t51 to
  t63 to reach exactly nine, leaving one body empty at t62, and at t69 an unrelated
  tidy removed `SKIP_PARTS`. 782306 (passing at 32k) deleted its tenth at t24–t25.
- **Post-green work that moved the tree backwards.** 374751, 453263 and 845472
  hold a pass state inside the line and grade not-pass at 32k: the work after green
  carried the tree across the line, and back again by 48k for 374751 and 845472.
  891860 destroyed its own `_cadence_cap` at t62–t64 and repaired it.

Nothing in the 39 was voided by a file outside `source_paths`: the `PROVENANCE.md`
rows three docs-linter cells wrote are in `ignored_paths`, and 845472's `Justfile`
edit (t33–t34) was dropped from the patch.

## The large tier: capability, with a named prompt defect beside it

cell-loop and speed-probe reached no pass state in any of 18 cells and `capability`
is True on all 18 (19 with docs-linter 312540). Eleven are capability primary, eight
runaway primary, six of those carrying capability too. One pattern, both nights:

- **The runaway turn is always a design think, never a tool call.** All eight end
  at exactly 16,000 tokens with no tool call, each opening on one detail the cell
  decides to reason out instead of act on: `identity` (442168 t14, 225004 t18), the
  provenance gate (332393 t22), the `opener` contract (771490 t10), the interface
  list re-transcribed (346861 t8, 691593 t5, 507079 t9), Step 4's preflight (524583 t6).
- **Non-runaway cells spend the budget in their own harness.** 631530 wrote the
  module and all 22 tests in two turns of 13.8k and 14.2k tokens and the clock ended
  it at t15; 918779 spent 23 exploration turns on ungraded reconnaissance then
  repaired fakes (`Protocol` from `collections.abc` t30, `AttemptCode.COMMAND` t38);
  529092 spent some thirty turns (t27–t64) bisecting one regex; 067362 hit the same
  `%f`-versus-three-digits defect.
- **Own-green without a pass state.** 897261's own 17 tests were green at t35 and the
  tripped tree still graded fail; docs-linter 312540 is the same at t51 — the
  capability signature: the suite the cell writes does not exercise the hidden one.

**Ambiguity is True on 6 of 9 speed-probe cells and on no others** (941646, 944467,
123802, 524583, 897261, 067362). The reading: Step 4 ("preflight an isolated
admission record … a minute of `find` as the cell") and Step 6 (the maintainer's
ten-line attended checklist, "each line is Paul's, in daylight") sit as numbered
steps inside the cell's own task text, while the hidden suite grades
`test_speed_probe.py` alone and `source_paths` is `scripts/speed_probe.py`,
`ROADMAP.md`, `tests`. Cells commit to executing them: 944467 built an admission
record (t22), found it cannot `sudo -n -u satyrn-cell` because it *is* satyrn-cell
(t23), and ran the preflight's root hunt over `/` for over a minute (t25–t30) — 35
exploration turns before its first source mutation at t35. Argued, never counted:
secondary on all six, primary on none, and under R0 §2 a task defect to fix or drop.

## Cells where I was unsure, with both readings

- **150526 / 862332 (depth-3), `hunting`.** I set 862332 True, 150526 False,
  departing from the mechanical flag on 150526. A (mine): the class needs a search
  that *cost* the cell, and 150526's `site-packages` grep at t7 paid — it found this
  Starlette's 307 default. B: any search outside the worktree is hunting whatever it
  returned. Neither changes a primary; both passed inside the line.
- **944467, primary.** I set capability, ambiguity secondary. A (mine): the rule is
  counterfactual on the verdict, and no speed-probe cell reached a pass state even
  spending its whole budget on the build, so returning t15–t34 changes nothing.
  B: 20 of 37 turns went to ungraded steps, a bigger single cause than any build
  defect — which would make speed-probe a task-defect task under §8 decision 2.
- **442168 and 225004, `information`.** Both ended their runaway turn on `identity`,
  left as an opaque mapping. A (mine): no fact is omitted — the hidden ledger test
  accepts any dict, so the cells over-read a term needing no reading. B: a named
  parameter with no stated domain is an omission, making `information` True on both
  and cell-loop a task-defect task.
- **906198, budget vs capability.** Its pass state is 481 tokens past the line.
  A (mine): budget, the line fell between the work and the pass. B: those 481 tokens
  exist only because of three self-inflicted defects (t18/t26 edit tool, t32 relative
  `Path` constants, t39 `rstrip` escaping) — capability with a budget coincidence.
- **897261, `finishing`.** False, there being no pass state to stop at — but t36–t42
  is ruff ceremony after its own green and reads like the medium tier; counting
  own-green ceremony would need a class the design does not have.
- **374751, 453263, 845472, finishing vs budget.** All hold a pass state inside the
  line and grade not-pass at 32k. A (mine): finishing, the class as written. B: what
  the line cut was a *regressed* tree, so the binding constraint was the regression;
  the design has no class for that and finishing is the closest.
