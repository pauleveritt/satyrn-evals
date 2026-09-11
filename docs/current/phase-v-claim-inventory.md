# Phase V1 — per-phase ledger

**HEAD:** `82da3401fa4b4e812e717ab5b6366f7ff0ca5dbf`

| attempt | arm | state | reason | phases | per-phase turns | per-phase tool calls |
|---|---|---|---|---|---|---|
| baseline-01 | baseline | measured | — | phase-1-home, phase-2-board, phase-3-add, phase-4-resolve-reopen | 7, 22, 6, 8 | 6, 21, 5, 7 |
| baseline-02 | baseline | measured | — | phase-1-home, phase-2-board, phase-3-add, phase-4-resolve-reopen | 9, 8, 9, 6 | 8, 7, 8, 5 |
| engine-01 | engine | measured | — | phase-1-home, phase-2-board, phase-3-add, phase-4-resolve-reopen | 6, 8, 10, 23 | 5, 7, 9, 22 |
| engine-02 | engine | measured | — | phase-1-home, phase-2-board, phase-3-add, phase-4-resolve-reopen | 6, 7, 9, 23 | 5, 6, 8, 22 |
| round2-01 | engine | measured | — | phase-1-home, phase-2-board, phase-3-add, phase-4-resolve-reopen | 6, 8, 8, 21 | 5, 7, 7, 20 |
| round2-02 | engine | measured | — | phase-1-home, phase-2-board, phase-3-add, phase-4-resolve-reopen | 6, 8, 7, 28 | 5, 7, 6, 27 |
| recurrence-01 | engine | measured | — | phase-1-home, phase-2-board, phase-3-add, phase-4-resolve-reopen | 6, 8, 11, 19 | 5, 7, 10, 18 |
| recurrence-03 | engine | measured | — | phase-1-home, phase-2-board, phase-3-add, phase-4-resolve-reopen | 6, 8, 8, 14 | 5, 7, 7, 13 |

**Runs root:** `/Users/pauleveritt/satyrn-smokes`

## Artifact digests (sha256)

| artifact | sha256 |
|---|---|
| 2026-09-11-te4-screen-baseline-01/agentclinic-complaint-lifecycle-session-20260911-065642-596280/transcript.jsonl | 41d1c43ca8066b75bbe1d43e5c086204d7d9c867d07b9cccff5e438225c4a2a9 |
| 2026-09-11-te4-screen-baseline-01/agentclinic-complaint-lifecycle-session-20260911-065642-596280/session-record.json | 227c2b4b603fd68d81434391cca2becdb50368c56cc6ffb3ae9218545bf7d465 |
| 2026-09-11-te4-screen-baseline-02/agentclinic-complaint-lifecycle-session-20260911-070435-208494/transcript.jsonl | 35fe14d91319c7f3a4797fc4478aa822e73c6bdc585a2de11cc3512a81fecb9e |
| 2026-09-11-te4-screen-baseline-02/agentclinic-complaint-lifecycle-session-20260911-070435-208494/session-record.json | 723c8e8be597164e37a6833ce7b283a06672a134b91a702cc0554b07608924f7 |
| 2026-09-11-te4-screen-engine-01/harness/.satyrn-implementer-transcript.jsonl | aca6a3683304e98ca1d853e31e25d9200fb21509de8392a64d8cc90ff128b801 |
| 2026-09-11-te4-screen-engine-01/chain.json | 6f7495e92b90eef048dca89408397ca41d4871f6d3134afe53785a3e132bcad3 |
| 2026-09-11-te4-screen-engine-02/harness/.satyrn-implementer-transcript.jsonl | 23fc91b209d78fa17d085fce0c83a0752b9b40aa7069ec508439970a35d10eeb |
| 2026-09-11-te4-screen-engine-02/chain.json | eba577880492dcc4214b4b31cdd27d9d58f01c31940386e0b11f507b01f92e1f |
| 2026-09-11-p4guardrail-round2-engine-01/harness/.satyrn-implementer-transcript.jsonl | 8da786e4c9968d8d03cc80195599422d2917b8cb818aed7c144fdc8c627d4ccc |
| 2026-09-11-p4guardrail-round2-engine-01/chain.json | 35ede8df83d1d421d9e2da80fab67d3cbb2b77a27eec41d8c89b54c842bf0c46 |
| 2026-09-11-p4guardrail-round2-engine-02/harness/.satyrn-implementer-transcript.jsonl | e92242827f3678699ce9ea4d202aa5bd21c0b1828ad8d03adb1c114f4ec08470 |
| 2026-09-11-p4guardrail-round2-engine-02/chain.json | 536ea941c12f8293c6602baf5f277480c7dedc010c5fd12b6f9a7b05fea2c36a |
| 2026-09-11-recurrence-engine-01/harness/.satyrn-implementer-transcript.jsonl | d087fc73d65464461b598b487298e21400cad6a636d5da35eec2d80e65f1f02a |
| 2026-09-11-recurrence-engine-01/chain.json | 699bd22e6f0ca4872279e42cee366bfaeeecbbef8750ea54c92b03eb55a48359 |
| 2026-09-11-recurrence-engine-03/harness/.satyrn-implementer-transcript.jsonl | 69f7d230581484fd89d0fc98d17685b6d8d4ac01d9b8790c05648d752b09b903 |
| 2026-09-11-recurrence-engine-03/chain.json | 9f7f6e67fe93731af426ea0a788b377fb458d17ecc4dbc4a2938e8a6d9e114ea |

## Claim inventory

| id | level | status | measure | population | quote | source | carriers |
|---|---|---|---|---|---|---|---|
| u-baseline-01-per-phase-turns | unit | confirmed | turns per step_id | Baseline-01, 2026-09-11-te4-screen-baseline-01 | 43 (7/22/6/8) | docs/current/te4-screen-result.md:28 | ROADMAP.md:289 |
| u-baseline-02-per-phase-turns | unit | confirmed | turns per step_id | Baseline-02, 2026-09-11-te4-screen-baseline-02 | 32 (9/8/9/6) | docs/current/te4-screen-result.md:29 | ROADMAP.md:289 |
| u-engine-01-per-phase-turns | unit | confirmed | turns per session | Engine-01, 2026-09-11-te4-screen-engine-01 | 47 (6/8/10/23) | docs/current/te4-screen-result.md:30 | — |
| u-engine-02-per-phase-turns | unit | confirmed | turns per session | Engine-02, 2026-09-11-te4-screen-engine-02 | 45 (6/7/9/23) | docs/current/te4-screen-result.md:31 | — |
| u-completion-turn-distribution | unit | confirmed | whole-attempt turns | the 4 recorded Engine completions | 43, 49, 44, 36 | docs/current/te4-completion-recurrence-check-result.md:181 | — |
| u-recurrence-01-per-phase-turns | unit | confirmed | turns per session | 2026-09-11-recurrence-engine-01 | 44 (6/8/11/19) | docs/current/te4-completion-recurrence-check-result.md:12 | — |
| u-recurrence-03-per-phase-turns | unit | confirmed | turns per session | 2026-09-11-recurrence-engine-03 | 36 (6/8/8/14) | docs/current/te4-completion-recurrence-check-result.md:14 | — |
| c-engine-population | claim | unreconciled | population statement | agentclinic-complaint-lifecycle, Phase TE sequence | 18 Engine attempts and 3 Baseline attempts | docs/current/te6-explain-and-decide.md:38 | — |
| c-baseline-3-of-3 | claim | unreconciled | completion_rate | 3 Baseline attempts on agentclinic-complaint-lifecycle | Baseline: **3 of 3 complete** | docs/current/te6-explain-and-decide.md:51 | ROADMAP.md:292 |
| c-contemporaneous-screen-tie-2-of-2 | claim | unreconciled | completion_rate | the final screen, both configurations fresh on the identical prompt | 2/2 vs 2/2 | docs/current/te6-explain-and-decide.md:67 | docs/current/te6-explain-and-decide.md:251 |
| c-completion-6-of-18 | claim | unreconciled | completion_rate | 18 Engine attempts on agentclinic-complaint-lifecycle | 6 of 18 | docs/current/te6-explain-and-decide.md:54 | ROADMAP.md:292, docs/current/index.md:234, docs/current/te4-screen-result.md:43 |
| c-completion-4-of-16 | claim | unreconciled | completion_rate | 16 Engine attempts before the 2026-09-11 screen | 4 of 16 | docs/current/te4-completion-recurrence-check-result.md:22 | ROADMAP.md:275, docs/current/index.md:208 |
| c-destroyed-13-of-15 | claim | unreconciled | destructive_edit | 15 phase-4-reaching Engine attempts | destroyed in 13 of 15 | docs/current/te6-explain-and-decide.md:147 | — |
| c-restored-9-of-15 | claim | unreconciled | restoration | 15 phase-4-reaching Engine attempts | 9 of 15 | docs/current/te6-explain-and-decide.md:169 | — |
| c-redirect-fixed-1-of-9 | claim | unreconciled | redirect_trap_resolution | 9 attempts showing the redirect-trap signature | 1 of 9 | docs/current/te6-explain-and-decide.md:174 | — |
| c-nonrestore-0-of-6 | claim | unreconciled | completion_rate | 6 non-restoring phase-4-reaching Engine attempts | 0 of 6 | docs/current/te4-completion-recurrence-check-result.md:178 | docs/current/index.md:204, ROADMAP.md:272 |
| c-restore-4-of-7 | claim | unreconciled | completion_rate | 7 restoring phase-4-reaching Engine attempts | 4 of 7 | docs/current/te4-completion-recurrence-check-result.md:179 | docs/current/index.md:205, ROADMAP.md:272 |
| c-phase4-denominator-6-of-10 | claim | unreconciled | denominator_binding | 10 attempts under the current prompt, not 8 | 6 of 8 | docs/current/te6-explain-and-decide.md:87 | docs/current/te6-explain-and-decide.md:93 |
| c-redirect-6-of-9 | claim | unreconciled | redirect_trap_occurrence | 9 phase-4-reaching Engine attempts at that round | 6 of 9 | docs/current/te4-phase4-guardrail-reverification-result.md:30 | docs/current/index.md:164 |
| c-fabricated-report-n1 | claim | unreconciled | verification_claim | 1 Engine screen attempt (screen-engine-01) | fabricated a fully invented passing pytest transcript | docs/current/te6-explain-and-decide.md:110 | docs/current/te4-screen-result.md:20, ROADMAP.md:282 |
