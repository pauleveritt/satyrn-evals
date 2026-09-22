<!-- evals 07e11428426ab77bfefc812a3c84ae145560b81b; counterfactual.py --phase decision -->

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
