<!-- evals 07e11428426ab77bfefc812a3c84ae145560b81b; counterfactual.py --phase debug -->

| task | group | attempt | code | trigger turn | tokens at trigger | actual | counterfactual | rescue | harm | fidelity | unmeasured |
|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-run-record-gate | nights-2026-09-14 | 490384 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-run-record-gate | nights-2026-09-14 | 549012 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-run-record-gate | nights-2026-09-14 | 618278 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-run-record-gate | nights-2026-09-14 | 511653 | BUDGET_EXCEEDED | 34 | 24834 | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-guard-prefixes | nights-2026-09-14 | 249635 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-guard-prefixes | nights-2026-09-14 | 305323 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-guard-prefixes | nights-2026-09-14 | 372105 | OK-pass | - | - | pass | pass |  |  | pass |  |
| selfhost-guard-prefixes | nights-2026-09-14 | 309486 | OK-pass | - | - | pass | pass |  |  | pass |  |
| selfhost-review-script | nights-2026-09-14 | 714610 | OK-unavailable | 15 | 7479 | not-pass | not-pass |  |  | pass |  |
| selfhost-review-script | nights-2026-09-14 | 770940 | OK-unavailable | 18 | 7541 | not-pass | not-pass |  |  | fail | fidelity: harness unavailable, replay pass; unverified-rescue: bash at turns 1, 5, 6, 9, 15, 17, 18 |
| selfhost-review-script | nights-2026-09-14 | 840545 | OK-unavailable | 12 | 5203 | not-pass | not-pass |  |  | fail | fidelity: harness unavailable, replay pass; unverified-rescue: bash at turns 1 |
| selfhost-review-script | nights-2026-09-14 | 624725 | OK-unavailable | 14 | 7992 | not-pass | not-pass |  |  | fail | fidelity: harness unavailable, replay fail |
| agentclinic-repair-depth-3 | engine | 808698 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-run-record-gate | engine | 296145 | BUDGET_EXCEEDED | - | - | not-pass | not-pass |  |  | unverifiable |  |
| selfhost-docs-linter | engine | 859943 | BUDGET_EXCEEDED | 34 | 27954 | not-pass | not-pass |  |  | unverifiable | unverified-rescue: bash at turns 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12 |
| agentclinic-repair-misleading-locus | engine | 117091 | OK-pass | 5 | 1738 | pass | pass |  |  | pass |  |
| agentclinic-repair-misleading-locus | engine | 172304 | OK-pass | 4 | 910 | pass | pass |  |  | pass |  |
| agentclinic-repair-misleading-locus | engine | 140540 | OK-pass | 9 | 2254 | pass | pass |  |  | pass |  |
| agentclinic-repair-misleading-locus | engine | 201516 | OK-pass | 4 | 583 | pass | pass |  |  | pass |  |
