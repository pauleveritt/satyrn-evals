# Finishing counterfactual — result

If a retained cell had stopped at the first point the Engine could observe as
green, how many within-budget passes would that add, and how many would it break
(spec section 1)? Answered offline from retained cells: no GPU, no new tasks, no
Engine or `satyrn_evals` change. Pre-registration
`docs/superpowers/specs/2026-09-15-release-two-finishing-counterfactual.md` at
`3f5a8a9` (amendments 7.1-7.4 added before the decision phase ran, 7.4 at
`0e33034`); reviewed script `07e1142`; outputs `1688dc2`.

## Decision

```
decision: not-the-lever
qualifying budget-shaped tasks none; floor harm cells 0; insufficient floor tasks ['selfhost-guard-prefixes', 'selfhost-review-script']
```

Section 5's consequence, copied: **Finishing is not the lever** "returns R0 to its
question 3 (is 9B the honest model and budget?) and to finding another
Engine-addressable class first." With 4 cells per task, one net rescue is 25 points.

## Per task

| task | kind | rescues | harms | net | unmeasured | insufficient |
|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | budget-shaped | 0 | 0 | 0 | 0 | no |
| selfhost-run-record-gate | budget-shaped | 0 | 0 | 0 | 2 | yes |
| selfhost-docs-linter | budget-shaped | 0 | 0 | 0 | 1 | no |
| selfhost-guard-prefixes | floor | 0 | 0 | 0 | 3 | yes |
| selfhost-review-script | floor | 0 | 0 | 0 | 2 | yes |
| agentclinic-repair-depth-2 | floor | 0 | 0 | 0 | 0 | no |

## Per cell — verbatim from `table.md` (stamped `07e1142`)

| task | group | attempt | code | trigger turn | tokens at trigger | actual | counterfactual | rescue | harm | fidelity | unmeasured |
|---|---|---|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | decision | 971281 | COMMAND_TIMEOUT | - | - | not-pass | not-pass |  |  | unverifiable |  |
| agentclinic-repair-depth-3 | decision | 021584 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| agentclinic-repair-depth-3 | decision | 082295 | OK-fail | 23 | 23230 | not-pass | not-pass |  |  | pass |  |
| agentclinic-repair-depth-3 | decision | 700050 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-run-record-gate | decision | 388294 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-run-record-gate | decision | 448568 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-run-record-gate | decision | 519278 | BUDGET_EXCEEDED | 35 | 23522 | not-pass | not-pass |  |  | unverifiable | skipped bash writer at turn 29; skipped bash writer at turn 30; skipped bash writer at turn 31 |
| selfhost-run-record-gate | decision | 028222 | BUDGET_EXCEEDED | 33 | 21594 | not-pass | not-pass |  |  | unverifiable | skipped bash writer at turn 29 |
| selfhost-docs-linter | decision | 147562 | BUDGET_EXCEEDED | 32 | 30992 | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-docs-linter | decision | 204433 | OK-pass | 35 | 21708 | pass | pass |  |  | pass |  |
| selfhost-docs-linter | decision | 270586 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-docs-linter | decision | 970283 | BUDGET_EXCEEDED | 40 | 27892 | not-pass | not-pass |  |  | unverifiable | skipped bash writer at turn 29; skipped bash writer at turn 37; skipped bash writer at turn 38; unverified-rescue: bash at turns 6, 7, 8, 18, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36, 37, 38 |
| selfhost-guard-prefixes | decision | 812248 | OK-pass | - | - | pass | pass |  |  | pass |  |
| selfhost-guard-prefixes | decision | 870439 | OK-pass | - | - | pass | pass |  |  | fail | fidelity: harness pass, replay unavailable |
| selfhost-guard-prefixes | decision | 937944 | OK-pass | - | - | pass | pass |  |  | fail | fidelity: harness pass, replay fail |
| selfhost-guard-prefixes | decision | 424626 | OK-pass | - | - | pass | pass |  |  | fail | fidelity: harness pass, replay fail |
| selfhost-review-script | decision | 688090 | OK-pass | 18 | 8309 | pass | pass |  |  | pass | skipped bash writer at turn 15 |
| selfhost-review-script | decision | 746232 | OK-pass | 10 | 3822 | pass | pass |  |  | pass |  |
| selfhost-review-script | decision | 816670 | OK-pass | 17 | 7138 | pass | pass |  |  | pass |  |
| selfhost-review-script | decision | 501161 | OK-pass | 23 | 8828 | pass | pass |  |  | pass | skipped bash writer at turn 11; skipped bash writer at turn 18 |
| agentclinic-repair-depth-2 | decision | 523251 | OK-pass | 7 | 3134 | pass | pass |  |  | pass |  |
| agentclinic-repair-depth-2 | decision | 575297 | OK-pass | 8 | 3636 | pass | pass |  |  | pass |  |
| agentclinic-repair-depth-2 | decision | 634454 | OK-pass | - | - | pass | pass |  |  | pass |  |
| agentclinic-repair-depth-2 | decision | 616367 | OK-pass | 9 | 3009 | pass | pass |  |  | pass |  |

## Engine column (outside the decision, spec section 2)
| task | attempt | trigger turn | tokens | actual | counterfactual | change |
|---|---|---|---|---|---|---|
| depth-3 route-proof-b | 808698 | - | - | not-pass | not-pass | none |
| run-record-gate route proof | 296145 | - | - | not-pass | not-pass | none |
| docs-linter route proof | 859943 | 34 | 27954 | not-pass | not-pass | none (unverified-rescue) |
| misleading-locus | 117091 | 5 | 1738 | pass | pass | none |
| misleading-locus | 172304 | 4 | 910 | pass | pass | none |
| misleading-locus | 140540 | 9 | 2254 | pass | pass | none |
| misleading-locus | 201516 | 4 | 583 | pass | pass | none |

859943 reached a hidden-suite pass at its trigger — a rescue under sections 3-5
as first written; 7.4 withholds it (11 earlier bash commands were neither replayed
nor provably read-only). Full rows: `debug/table.md`.

## Notes

- **Fidelity.** 14 decision cells carry a harness verdict; 11 reproduce. Misses:
  guard-prefixes 870439 (pass vs unavailable), 937944 and 424626 (pass vs fail). The
  other 10 ended `BUDGET_EXCEEDED`/`COMMAND_TIMEOUT`: `unverifiable`, counted.
- **Unmeasured (8).** 870439, 937944, 424626 (fidelity); 519278 (skipped bash
  writers 29-31), 028222 (29), 970283 (29, 37, 38 plus `unverified-rescue`), 688090
  (15), 501161 (11, 18). Each is no change; >1 makes a task `insufficient`.
- **The one cell that could have been a rescue.** docs-linter 970283 graded `pass`
  at its trigger (turn 40, 27,892 tokens) against an actual `BUDGET_EXCEEDED`, but is
  unmeasured on two independent grounds — section 4's skipped-writer rule and 7.4 —
  so the decision does not rest on 7.4. The other two triggered budget-exceeded cells
  graded `unavailable` (519278) and `fail` (028222). No cell changed outcome.
- **Rulings that touched a counted cell** (plan `Rulings`). Ruling 6 (evals' own
  count at the green's end event) fixed every trigger turn and token figure; Ruling
  12 (skips count through the end of the trigger turn, where the spec says "before"),
  applied to 7.4 too, made 519278, 028222, 970283, 688090 and 501161 unmeasured;
  Ruling 14 the three guard-prefixes cells; Ruling 9 / amendment 7.2 grades outside
  the checkout (else AgentClinic grades return `unavailable`).
- **Disclosure (7.3).** This pre-registration was written after the release-one
  review (`evidence/2026-09-15-release-one-outcome/fable-review.md`), which reported
  hidden-suite pass-states for some decision cells (docs-linter, run-record-gate)
  but did not measure own-green triggers, which are what sections 3-5 count.
- **Remaining replay limits (7.4).** The replay lands `write`/`edit` calls and two
  bash write forms (heredoc; one `sed -i`/`printf`/`echo` redirect); other bash
  writes are detected lexically, so it can miss `patch -p1 < x`, `python fix.py` or
  `Path(...)` writes, and files left outside `source_paths` by an unreplayed command
  are absent though the harness allowlist judged them. 7.4 answers both: a
  reconstructed pass is a rescue only when every bash command through the trigger
  turn was replayed or provably read-only. Harm counting is unaffected.
- **2026-09-14 nights.** Review-script 770940, 840545 and 624725 fail fidelity in
  `debug/table.md`: they ran under a task tree that did not yet ignore
  `PROVENANCE.md`, so the harness answered `unavailable`; their `task_tree_sha256`
  no longer matches the current tree. Every decision record's does.

## Recompute

```bash
git clone --branch release-one /Users/pauleveritt/projects/pauleveritt/satyrn-evals "$HOME/satyrn-counterfactual-recompute"
cd "$HOME/satyrn-counterfactual-recompute" && git checkout 07e1142 && uv sync
mv evidence/2026-09-15-finishing-counterfactual/cells.json cells.committed.json
uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase decision --grade-root "$HOME/satyrn-counterfactual-grades-recompute"
uv run python -c "import json; a, b = (json.load(open(p))['cells'] for p in ('cells.committed.json', 'evidence/2026-09-15-finishing-counterfactual/cells.json')); print('identical' if a == b else 'DIFFERENT')"
```
