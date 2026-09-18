# The pathology census — nights 1, 2 and 3 (2026-09-16 through 2026-09-18)

Signed by the maintainer 2026-09-17 for nights 1 and 2; the night-3 additions of 2026-09-18 await the
maintainer's signature. The mechanical fields are the
classifier's (`classify.py` at `6a95720`); the eight class columns in each
`<task>/classes.md` were drafted by Opus from the reconstructions, cited by
turn, and signed by the maintainer; the cross-task reading is
`classes-summary.md`. Nothing
below pools across tasks. Design: `docs/superpowers/specs/2026-09-15-release-two-census-design.md`
and `2026-09-17-release-two-census-night-2-design.md`.

## What ran

| night | records | cells | budget | backstop | machine |
|---|---|---|---|---|---|
| 1, 2026-09-16 | five, one per task, n = 6 | 30 | 48,000 tokens, 72 turns | 3,000 s | shared by the maintainer's other work; 9 cells wall-clock-cut |
| 2, 2026-09-17 | three replacement records, n = 3 | 9 | same | 4,800 s | quiet; launched by Fable under the maintainer's recorded one-time authorization |
| 3, 2026-09-18 | one authored record, n = 6 | 6 | same | 4,800 s | shared; interrupted 20:50 and resumed; decode 13.7–14.2 tok/s |

Night 2 replaces the nine timed-out cells of night 1 and is reported beside
them, never in their place. Per-turn output cap 16,000 on both arms, k = 3,
Baseline only, Ornith 1.5 9B, isolated as `satyrn-cell`.

## The reading at the pre-registered 32,000-token, 48-turn line

"Reached" is a hidden-suite pass state inside the line, from the turn-by-turn
reconstruction. "Finishing" is reached and not stopped at. "Runaway" is a
cell ended by one 16,000-token turn with no tool call.

| task | night | cells | pass at 32k/48 | reached | finishing | runaway | pass at 48k | timed out |
|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3, R2 | 1 | 6 | 6 | 6 | 0 | 0 | 6 | 0 |
| selfhost-run-record-gate | 1 | 6 | 1 | 5 | 4 | 0 | 2 | 3 |
| selfhost-run-record-gate | 2 | 3 | 0 | 3 | 3 | 0 | 1 | 0 |
| selfhost-docs-linter | 1 | 6 | 1 | 4 | 3 | 0 | 4 | 0 |
| selfhost-cell-loop | 1 | 6 | 0 | 0 | 0 | 3 | 0 | 3 |
| selfhost-cell-loop | 2 | 3 | 0 | 0 | 0 | 2 | 0 | 0 |
| selfhost-speed-probe | 1 | 6 | 0 | 0 | 0 | 2 | 0 | 3 |
| selfhost-speed-probe | 2 | 3 | 0 | 0 | 0 | 1 | 0 | 0 |
| selfhost-preflight-quiet (authored, not cut) | 3 | 6 | 1 | 2 | 1 | 0 | 2 | 0 |

**Finish-on-green counterfactual at the line**, per task, both readings
(`<task>/table.md`, "Per task"):

| task | night | run 1 (pre-registered rules) rescues | run 2 (replay method) rescues | harms |
|---|---|---|---|---|
| selfhost-run-record-gate | 1 | 0 (2 unmeasured) | 2 | 0 |
| selfhost-run-record-gate | 2 | 0 (3 unmeasured) | 3 | 0 |
| selfhost-docs-linter | 1 | 0 (2 unmeasured) | 2 | 0 |
| the other three tasks | 1 and 2 | 0 | 0 | 0 |
| selfhost-preflight-quiet | 3 | 0 | 0 | 0 |

Harm is zero in all 39 cells. The night-2 design's first draft said "5 of
12"; the producer says 4 of 12 under run 2 and 0 under run 1, corrected
2026-09-17.

## What the two nights say, with the class columns signed

1. **depth-3 at R2 is a floor task.** 6 of 6 in a median 11 turns. The
   release-one depth-3 leg measured a rung defect. The claim table in the
   census design is judged over the four build tasks.
2. **Medium builds are finishing-bound.** On run-record-gate, 8 of 9 cells
   held a hidden-suite pass inside the line and 1 stopped there; on
   docs-linter, 4 of 6 and 1. Cells that reach green then run the plan's
   remaining steps until the budget or the turn cap ends them. Under run
   2's method, stopping at own-green rescues 5 of 9 and 2 of 6; under run
   1's rules the cells are unmeasured rather than counted.
3. **Large builds are out of reach at 9B.** cell-loop and speed-probe reached
   no pass state in any of 18 cells, quiet machine or not; the tripped
   trees grade `fail`. The signed columns read all 18 as capability (11
   primary, 7 behind a runaway), every runaway turn a design think that
   opened on one detail; speed-probe carries a prompt ambiguity beside it,
   below.
4. **Runaway is a real class, 8 of 33 build cells over both nights (5 of 24
   on night 1),** and every one ended at
   `agent_end` with no tool call, which is the Engine completion gate's
   trigger. The per-turn cap converted these from whole-budget burns into
   early stops with no patch.
5. **Baseline rarely stops on its own by 48k.** Of night 2's nine cells, one
   stopped with a pass, three stopped on a runaway, five ran to the token
   budget. The cost-at-equal-outcome claim is not supported on this tier.
6. **Contention was smaller than first reported.** Night 2's quiet decode
   ran 17–20 tok/s per stream at k = 3; night 1's ran 12–19. The night-1
   timeouts came mostly from a 3,000 s backstop that was too tight for
   suite-heavy tasks, not from the shared machine. The `decode tok/s`
   column is the machine's rate while the cell ran, shared across the
   overlapping cells named in `decode overlap`, never a private stream.
7. **The authored third medium task is mixed, and the claim stays two tasks
   wide.** `selfhost-preflight-quiet` ran 6 Baseline cells at 48,000/72 on a
   shared machine: 1 passed at the 32,000-token line (566024), 1 more passed
   only at 48,000 (758561, the finishing shape), 1 failed, and 3 ran to the
   budget. Four of six never reached a pass state, so it is not a comfortable
   floor task; two did, so it is not "no pass state"; and one finishing cell
   whose own-green stop is not rescued at the line (rescues 0 under both
   readings) is not run-record-gate's 8-of-9 shape. None of the design's
   section 5 branches fits cleanly, so the task is recorded as **authored and
   mixed**, with a prompt ambiguity named below, and kept as the development
   task Engine design section 7 anticipated. It is never pooled with the cut
   tasks.

## Deviations, stated

- The R0 §1.2 validity check ran on `deepseek-v4-flash`, the harness's only
  selectable model, ratified 2026-09-16; read those certifications as
  slightly weaker than the design's named instrument.
- Night 2 was launched by Fable, not the maintainer, under the maintainer's
  recorded authorization and its five conditions
  (`.superpowers/sdd/2026-09-17-release-two-census-night-2/maintainer-authorization-2026-09-17.md`).
- The third medium-build task was not found in any plan on the branch; it is
  authored under `2026-09-17-release-two-authored-task-design.md`.
- **speed-probe is dropped from the ceiling set, maintainer's decision
  2026-09-17.** Its cut prompt carries the plan's Steps 4 and 6, an attended
  checklist and a preflight a cell cannot run; ambiguity is argued on 6 of 9
  cells (never primary, since no cell reached a pass state on the build
  alone). Under R0 §2 that is fix-or-drop. Its 9 cells stay in the
  large-tier evidence as capability with the defect named; they are never
  claimed against.
- **Night 3 was interrupted and resumed.** The launcher refills slots as they
  free, so there was no wave: the first three cells ran 19:27–20:22 and three
  more started at 19:55, 20:15 and 20:22. At 20:50 the controller halted the
  three running cells on an OS indexing spike (load 10.25 against the plan's
  9.0 ceiling); the launcher recorded `interrupted` / `SignalAbort: SIGTERM`
  and the record resumed at 21:19, completing 22:15. The result's `replaced`
  is `[]` and names none of the three killed attempts
  (`…-235514-554672`, `…-001558-428836`, `…-002204-910356`), which stood at
  58 / 27 / 23 turns and 45,114 / 30,407 / 24,633 tokens when killed. The
  19:55 cell was past the 32,000-token / 48-turn line and about three minutes
  from its budget; read it at the line as a **supplementary row, never
  pooled** with the six.
- **The machine was not quiet by the plan's own instrument.** Night 3's
  decode ran 13.7–14.2 tok/s per stream against night 2's 18.5. No cell was
  cut by the 4,800 s backstop, so the token/turn readings are unaffected, but
  the quiet precondition was not met.
- **`selfhost-preflight-quiet` carries a prompt ambiguity, found by the
  night-3 class review** (`src/satyrn_evals/tasks/KNOWN_DEFECTS.md`): the
  prompt never says when `decode` is null, and three cells read it as "record
  decode only when it is a problem". Capability is primary on the four
  non-pass cells and the ambiguity secondary on three. The recorded prompt
  edit ("decode is null only when the rate is None") is deferred because
  applying it moves `tree_digest(task_dir)`, which the frozen night-3 record
  pins.
- **The night-3 class review was drafted by Kimi K3, by the maintainer's
  direction**, after GLM 5.3's provider returned `429 Insufficient balance`.
  This is a maintainer-directed substitution for the standing Opus review
  role, not an agent substitution.
- **Three route-proof records are excluded from every comparison denominator,** by the
  maintainer's choice of §7's first option on 2026-09-17:
  `records/2026-09-17-route-proof-engine-selfhost-run-record-gate.json` (n = 2),
  `…-selfhost-docs-linter.json` (n = 2) and `…-selfhost-cell-loop.json` (n = 3), all Engine at
  the release-two commit, `--purpose route-proof`. **This night is void as a behavioural read:
  trigger unreachable, Engine defect.** The Engine's `self_test` could not go green on this repo
  — its second collection collected the `tests/data` and `tests/integration/data` fixture trees
  that the repo's `norecursedirs` excludes, and exited 2 — so the finish-on-green steer's trigger
  could not fire and "steer 0 of 4" is not a finding. The two facts that remain: 2 of 2 resumes
  produced a tool call (a thin denominator); both docs-linter cells passed inside 32,000 tokens
  against Baseline's 1 of 6 (n = 2, a hint at most). A second route proof on the fixed harness is
  reported beside this one.

## Recompute

```bash
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals
for T in agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-docs-linter selfhost-cell-loop selfhost-speed-probe; do
  uv run --project . python evidence/2026-09-16-census/classify.py \
    --night "$HOME/satyrn-runs/2026-09-16-census-$T" --record "records/2026-09-16-census-$T.json" \
    --out "$PWD/tmp-census-1" --grade-root "$HOME/satyrn-census-grades"; done
for T in selfhost-run-record-gate selfhost-cell-loop selfhost-speed-probe; do
  uv run --project . python evidence/2026-09-16-census/classify.py \
    --night "$HOME/satyrn-runs/2026-09-17-census2-$T" --record "records/2026-09-17-census2-$T.json" \
    --out "$PWD/tmp-census-2" --grade-root "$HOME/satyrn-census-grades"; done
uv run --project . python evidence/2026-09-16-census/classify.py \
  --night "$HOME/satyrn-runs/2026-09-18-census3-selfhost-preflight-quiet" \
  --record records/2026-09-18-census3-selfhost-preflight-quiet.json \
  --out "$PWD/tmp-census-3" --grade-root "$HOME/satyrn-census-grades"
diff -r tmp-census-1 evidence/2026-09-16-census --exclude README.md --exclude classify.py --exclude validity --exclude __pycache__
diff -r tmp-census-2 evidence/2026-09-17-census-2 --exclude validity
```
