# Phase V — claim reconciliation

**HEAD:** `17764cd1396824359c5e2607cddb2321dd84a150`

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
| 2026-09-10-completionrate-engine-01/harness/.satyrn-implementer-transcript.jsonl | 36604cf798cd0b96415323818191ec5a666b07162c139788c26d2ece2e08aae7 |
| 2026-09-10-completionrate-engine-01/chain.json | b09f77b06787e1fbcbd691b7a20af09af7c4805edb6dbb62baf8674374c84f6a |
| 2026-09-10-guardrail-reverify-engine-01/harness/.satyrn-implementer-transcript.jsonl | bc43e2cd28308efe1c0b00858676784b7fcf91d3d533135051895730ea8ac885 |
| 2026-09-10-guardrail-reverify-engine-01/chain.json | f1054c2579cd77a76fdb839ef1f741507fa9b308ab26775831cd759febdba7d1 |
| 2026-09-10-guardrail-reverify-engine-02/harness/.satyrn-implementer-transcript.jsonl | d6b49c7662c6ab073e91d36846860de0074fbbde25ccf450e739a7fd7d35313c |
| 2026-09-10-guardrail-reverify-engine-02/chain.json | 605db6ba83b88857d1119b34afcbbac07893cc2a173c3e2f87722d12f19bfb5b |
| 2026-09-10-p4guardrail-engine-01/harness/.satyrn-implementer-transcript.jsonl | 9c1cd77b53b23f7e094aa1e3f2d5433dd641a4bfb2bb2492afd359b02925cddc |
| 2026-09-10-p4guardrail-engine-01/chain.json | 0ea6dfb32a4fe269a18d3dd89fd9e62f44e10dc53dcf09011eaa71144a4739f9 |
| 2026-09-10-p4guardrail-engine-03/harness/.satyrn-implementer-transcript.jsonl | 6746350feb9ffec22639d410d98d96ad5159cc0daccbf44da8f8eea94a44754d |
| 2026-09-10-p4guardrail-engine-03/chain.json | 3ddf7f86a7fa05cfa5b861ee16683ba9ee1036af6ec505bf3c019f02b48ad405 |
| 2026-09-10-tightening3-engine-01/harness/.satyrn-implementer-transcript.jsonl | 94f8259ac56afbe4d2a39d7607fccc38ce7ebaaf23fecf12c7fd318b7edb5b51 |
| 2026-09-10-tightening3-engine-01/chain.json | 430ef939d87ffc5f03423bbdee399e2d2c757884dc6be0545233e15c24fa3e2f |
| 2026-09-10-tightening3-engine-02/harness/.satyrn-implementer-transcript.jsonl | f2dd775df87c90e10a7f75a0c883ffd8ad13b32de638c3ad3f3b70fffb994e96 |
| 2026-09-10-tightening3-engine-02/chain.json | 2e968b806f455d5ab95fb24e6f18408792f88e97c5e556965c23a905cb9d7892 |
| 2026-09-10-tightening4-engine-01/harness/.satyrn-implementer-transcript.jsonl | 399e895bc47a7e86715ab443a8ab4554dd7f416399fe2ba122751f9bab5cae91 |
| 2026-09-10-tightening4-engine-01/chain.json | f4298acebad80b0765a0d25d995b3943d5ae6a331536155e53d2b27148d603b0 |
| 2026-09-10-tightening4-engine-02/harness/.satyrn-implementer-transcript.jsonl | 0031bddc7c3965428d37859400351fedfd3738b94f6f1f09ac4dd1e8e370a64d |
| 2026-09-10-tightening4-engine-02/chain.json | c170c0c0adb779a73bea2b6a0121bbeee93a63ea8c8ffcd9e9f89820d16736a7 |

## Claim measures

| claim_id | measure | population | result | evidence |
|---|---|---|---|---|
| c-engine-population | population statement | agentclinic-complaint-lifecycle, Phase TE sequence | undecidable | no classifier covers this measure in V2a |
| c-baseline-3-of-3 | completion_rate | 3 Baseline attempts on agentclinic-complaint-lifecycle | undecidable | no classifier covers this measure in V2a |
| c-contemporaneous-screen-tie-2-of-2 | completion_rate | the final screen, both configurations fresh on the identical prompt | undecidable | no classifier covers this measure in V2a |
| c-completion-6-of-18 | completion_rate | 18 Engine attempts on agentclinic-complaint-lifecycle | undecidable | no classifier covers this measure in V2a |
| c-completion-4-of-16 | completion_rate | 16 Engine attempts before the 2026-09-11 screen | undecidable | no classifier covers this measure in V2a |
| c-destroyed-13-of-15 | destructive_edit | 15 phase-4-reaching Engine attempts | yes | derived 15 yes, 0 undecidable, of 15 phase-4-reaching Engine attempts applied a destructive edit (published 13 of 15); operationalization gap: the classifier counts any content-changing edit, not the source's route-specific destruction (2 of 15 never touched the route) |
| c-restored-9-of-15 | restoration | 15 phase-4-reaching Engine attempts | yes | derived 3 yes, 0 undecidable, of 15 phase-4-reaching Engine attempts restored removed content (published 9 of 15); operationalization gap: the classifier counts any removed content re-added, not the source's route-specific restoration before the phase ended |
| c-redirect-fixed-1-of-9 | redirect_trap_resolution | 9 attempts showing the redirect-trap signature | undecidable | no classifier covers this measure in V2a |
| c-nonrestore-0-of-6 | completion_rate | 6 non-restoring phase-4-reaching Engine attempts | undecidable | no classifier covers this measure in V2a |
| c-restore-4-of-7 | completion_rate | 7 restoring phase-4-reaching Engine attempts | undecidable | no classifier covers this measure in V2a |
| c-phase4-denominator-6-of-10 | denominator_binding | 10 attempts under the current prompt, not 8 | undecidable | no classifier covers this measure in V2a |
| c-redirect-6-of-9 | redirect_trap_occurrence | 9 phase-4-reaching Engine attempts at that round | undecidable | no classifier covers this measure in V2a |
| c-fabricated-report-n1 | verification_claim | 1 Engine screen attempt (screen-engine-01) | no | screen-engine-01's final summary claimed a passing test run while its last retained run_self_test returned exit code 1 |

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
| c-engine-population | claim | not_derivable | population statement | agentclinic-complaint-lifecycle, Phase TE sequence | 18 Engine attempts and 3 Baseline attempts | docs/current/te6-explain-and-decide.md:38 | — |
| c-baseline-3-of-3 | claim | not_derivable | completion_rate | 3 Baseline attempts on agentclinic-complaint-lifecycle | Baseline: **3 of 3 complete** | docs/current/te6-explain-and-decide.md:51 | ROADMAP.md:292 |
| c-contemporaneous-screen-tie-2-of-2 | claim | not_derivable | completion_rate | the final screen, both configurations fresh on the identical prompt | 2/2 vs 2/2 | docs/current/te6-explain-and-decide.md:67 | docs/current/te6-explain-and-decide.md:251 |
| c-completion-6-of-18 | claim | not_derivable | completion_rate | 18 Engine attempts on agentclinic-complaint-lifecycle | 6 of 18 | docs/current/te6-explain-and-decide.md:54 | ROADMAP.md:292, docs/current/index.md:234, docs/current/te4-screen-result.md:43 |
| c-completion-4-of-16 | claim | not_derivable | completion_rate | 16 Engine attempts before the 2026-09-11 screen | 4 of 16 | docs/current/te4-completion-recurrence-check-result.md:22 | ROADMAP.md:275, docs/current/index.md:208 |
| c-destroyed-13-of-15 | claim | claim_measure_mismatch | destructive_edit | 15 phase-4-reaching Engine attempts | destroyed in 13 of 15 | docs/current/te6-explain-and-decide.md:147 | — |
| c-restored-9-of-15 | claim | claim_measure_mismatch | restoration | 15 phase-4-reaching Engine attempts | 9 of 15 | docs/current/te6-explain-and-decide.md:169 | — |
| c-redirect-fixed-1-of-9 | claim | not_derivable | redirect_trap_resolution | 9 attempts showing the redirect-trap signature | 1 of 9 | docs/current/te6-explain-and-decide.md:174 | — |
| c-nonrestore-0-of-6 | claim | not_derivable | completion_rate | 6 non-restoring phase-4-reaching Engine attempts | 0 of 6 | docs/current/te4-completion-recurrence-check-result.md:178 | docs/current/index.md:204, ROADMAP.md:272 |
| c-restore-4-of-7 | claim | not_derivable | completion_rate | 7 restoring phase-4-reaching Engine attempts | 4 of 7 | docs/current/te4-completion-recurrence-check-result.md:179 | docs/current/index.md:205, ROADMAP.md:272 |
| c-phase4-denominator-6-of-10 | claim | not_derivable | denominator_binding | 10 attempts under the current prompt, not 8 | 6 of 8 | docs/current/te6-explain-and-decide.md:87 | docs/current/te6-explain-and-decide.md:93 |
| c-redirect-6-of-9 | claim | not_derivable | redirect_trap_occurrence | 9 phase-4-reaching Engine attempts at that round | 6 of 9 | docs/current/te4-phase4-guardrail-reverification-result.md:30 | docs/current/index.md:164 |
| c-fabricated-report-n1 | claim | confirmed | verification_claim | 1 Engine screen attempt (screen-engine-01) | fabricated a fully invented passing pytest transcript | docs/current/te6-explain-and-decide.md:110 | docs/current/te4-screen-result.md:20, ROADMAP.md:282 |
