# Phase V — claim reconciliation

**HEAD:** `add85b0c004e0a1da6953ff99ef95ee0d08f6c3d`

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
| 2026-09-10-completionrate-engine-01/grading/receipts/01-phase-1-home.json | 83df7f7ae6f5a04c7d6fb6393303bb7d3329390718a725c8b4b4d6b622793be0 |
| 2026-09-10-completionrate-engine-01/grading/receipts/02-phase-2-board.json | 3932c5730618ba14af2c69bfbf4147ea53756cab3ad59932aafb8249f62ee7a5 |
| 2026-09-10-completionrate-engine-01/grading/receipts/03-phase-3-add.json | f68df2326f906bdac18c03722c0247c184ffeae0104674b2e3205da07b3777e6 |
| 2026-09-10-completionrate-engine-01/grading/receipts/04-phase-4-resolve-reopen.json | d9f4683398980fabfde3f62b6b3ffe588577aeccb99d04f4bdb3825ec0c3123f |
| 2026-09-10-guardrail-reverify-engine-01/grading/receipts/01-phase-1-home.json | 7dc434518855b9626e280a3ae1c2d12c981f2409382349d7196961f296dba4a7 |
| 2026-09-10-guardrail-reverify-engine-01/grading/receipts/02-phase-2-board.json | ca144f6adac33a213314e7a6b5bf14b9cf6d0b91e9e1fdbc30af614b5a1677dd |
| 2026-09-10-guardrail-reverify-engine-01/grading/receipts/03-phase-3-add.json | 9b3f1345a42e052d42ce6976a47397bf16d0d765dcedce9c587d0a1f871d96b7 |
| 2026-09-10-guardrail-reverify-engine-01/grading/receipts/04-phase-4-resolve-reopen.json | 6a45d5299e3ad47703197bc18443ca8d80724579555d2822b073d757381ffcce |
| 2026-09-10-guardrail-reverify-engine-02/grading/receipts/01-phase-1-home.json | 2133f46b5156567eaa729e84ed22431ce4bdeb8ee6fe956ea2448378adfed14c |
| 2026-09-10-guardrail-reverify-engine-02/grading/receipts/02-phase-2-board.json | c8b860307372c7d009b186644959adb95ed718b41ba3aa1010424c2304500618 |
| 2026-09-10-guardrail-reverify-engine-02/grading/receipts/03-phase-3-add.json | 3661da71d1e5a64e197831beafec9ebc992b945a57daa6e7215cc1e00435cfda |
| 2026-09-10-p4guardrail-engine-01/grading/receipts/01-phase-1-home.json | 7e366ee9dfe26191d19c43c8b2f669056a23d997855e0977504ba67a21f442f8 |
| 2026-09-10-p4guardrail-engine-01/grading/receipts/02-phase-2-board.json | 7613e06edeecef1d8c166e35838c189b6547a188149441c2651ee7a45f3324c3 |
| 2026-09-10-p4guardrail-engine-01/grading/receipts/03-phase-3-add.json | 9396b22631ddad86d7a73baecb6657828d43c475122aff9cffe00aa5ed2a24f6 |
| 2026-09-10-p4guardrail-engine-02/chain.json | d299f2e85fb478ad115389103ee0c87006ba435462fd282191e29908097dcdcc |
| 2026-09-10-p4guardrail-engine-02/grading/receipts/01-phase-1-home.json | d96ada98cde33cd7c7adfcf211cbf634c6ca866e8508b48e556ed48ec20d53f5 |
| 2026-09-10-p4guardrail-engine-03/grading/receipts/01-phase-1-home.json | be9a318f0ef7549c05094352e55986a7c8eb9b967666d12a694c400f68ac5555 |
| 2026-09-10-p4guardrail-engine-03/grading/receipts/02-phase-2-board.json | 54cb767c713f9b9269bedb74a2ffd566a0bbc2af38802ef7f2c687b780bd7d65 |
| 2026-09-10-p4guardrail-engine-03/grading/receipts/03-phase-3-add.json | 4f3b6a561220fda7979954832863f3af07e2e81e17c45544bef1a107c659435f |
| 2026-09-10-te4-route-engine-01/chain.json | 91123edaf09ef47a971ae27377e352a4e43628fcecab0cd41c88285b2967c558 |
| 2026-09-10-te4-route-engine-01/grading/receipts/01-phase-1-home.json | c152ee4b1f7194dc3f4b1698fb56cae8b10df8d6c79df70ec0533fea9b4286c4 |
| 2026-09-10-tightening3-engine-01/grading/receipts/01-phase-1-home.json | be88f08fae468f49cdd414ca671dff65d05571d364163c9ac2f8c807cdf96b62 |
| 2026-09-10-tightening3-engine-01/grading/receipts/02-phase-2-board.json | 5d61332bdf9f31fb66069b51641c4e6b662adacc88479e58989df57bd41f7a78 |
| 2026-09-10-tightening3-engine-01/grading/receipts/03-phase-3-add.json | ab81cac87cc072cb5a24b4c92f23a4663e511040edafdf0b17905d7dec5eca47 |
| 2026-09-10-tightening3-engine-02/grading/receipts/01-phase-1-home.json | 4ef802659fa8c1e89e1e137a9d7d9c71e4874a4ef415b47c8d9ae1d7ac5be304 |
| 2026-09-10-tightening3-engine-02/grading/receipts/02-phase-2-board.json | bb33f52362b2f419f2beb71c3f804f2185b6d295b4d9d926861ae3df5cdcbde3 |
| 2026-09-10-tightening3-engine-02/grading/receipts/03-phase-3-add.json | 3cfedfe9b50a2d0c7cca949d66e871aed37cd878471aaaf1f45a46241ffecf82 |
| 2026-09-10-tightening3-engine-02/grading/receipts/04-phase-4-resolve-reopen.json | dd57dfb528f82f35cc76dfb9ec9493310a72bfece9e5e0c065f03555f713cadb |
| 2026-09-10-tightening4-engine-01/grading/receipts/01-phase-1-home.json | 5fb2540e1ec1f734d0d4bbb6813b69f76e4d9d4a44e64a73ce10bb0989777962 |
| 2026-09-10-tightening4-engine-01/grading/receipts/02-phase-2-board.json | 6f94618f29363449f367ce32350ee6af9e5dcb9e429cbc49a6b5421a3015a82d |
| 2026-09-10-tightening4-engine-01/grading/receipts/03-phase-3-add.json | 64adff929fbf4741901608a7023b5f7fd215ac173c8abce68b25cb1c0535374b |
| 2026-09-10-tightening4-engine-02/grading/receipts/01-phase-1-home.json | 5c80078059daef0a5a904a45455760f4b111bdf56ff13fd13bf7ac2389942880 |
| 2026-09-10-tightening4-engine-02/grading/receipts/02-phase-2-board.json | a8c6a6580346875244eeeab7258e6137262c2d70955be48fabea053bf0ce2729 |
| 2026-09-10-tightening4-engine-02/grading/receipts/03-phase-3-add.json | 3b05533b3bf6ad488c42b819af5ddccd9cd738b5fd6b6cb241b7ce843c9590b0 |
| 2026-09-10-tightening4-engine-02/grading/receipts/04-phase-4-resolve-reopen.json | 22c0630be3cee34c51f82ff9d3522d85be7f93cdcf4e4887dc5d4f47fcb055c5 |
| 2026-09-11-p4guardrail-round2-engine-01/grading/receipts/01-phase-1-home.json | 966965eac0ed003ce48bd995e28e3bee6061a61c2c3212cb883eeda4f3d2cc4f |
| 2026-09-11-p4guardrail-round2-engine-01/grading/receipts/02-phase-2-board.json | 65b14de91b076622a760428c120a44eac4393a1a336cd814a3e0a25c5e53c6b5 |
| 2026-09-11-p4guardrail-round2-engine-01/grading/receipts/03-phase-3-add.json | d5a5d692dc7941baaec4df18ee448c5e6fbfe1e1ed0910bdfcf4ce91b683899b |
| 2026-09-11-p4guardrail-round2-engine-01/grading/receipts/04-phase-4-resolve-reopen.json | 88054bf5d76a82bf8c0717f0520b680e6891b43197853a6efeac6744f6e54106 |
| 2026-09-11-p4guardrail-round2-engine-02/grading/receipts/01-phase-1-home.json | 04ea50845f97fe48ffd1022c453cc976fdc318467355d1bd11efb38f0805f1d5 |
| 2026-09-11-p4guardrail-round2-engine-02/grading/receipts/02-phase-2-board.json | 05d6393aac8df54aa3fc78af37eb01009ef9c86e7461b69b615b73547aec7e77 |
| 2026-09-11-p4guardrail-round2-engine-02/grading/receipts/03-phase-3-add.json | ff749dd184d803743cf7ce78e54b4c1d317d8dedafe8608fc5942ed34d6a24c2 |
| 2026-09-11-p4guardrail-round2-engine-02/grading/receipts/04-phase-4-resolve-reopen.json | 23e9d6e18a893fe4592253f7cfbee1d853722adc00cf9bef425c384ad8ca80c3 |
| 2026-09-11-recurrence-engine-01/grading/receipts/01-phase-1-home.json | ec6d5dd56ff771fd6e70369bfaca419de3fb075a2c30e1f8e6362578cc86f84e |
| 2026-09-11-recurrence-engine-01/grading/receipts/02-phase-2-board.json | 522af2364d4d522266e5d2a8ccf18050ff37db4f5ed2c14168d64a0631c2bacc |
| 2026-09-11-recurrence-engine-01/grading/receipts/03-phase-3-add.json | a7938b618ec449435b53a2f3ec3b88219e33287d014f816d935e3d52c1cc3e1e |
| 2026-09-11-recurrence-engine-01/grading/receipts/04-phase-4-resolve-reopen.json | bac260ba9e5fd36707d0693c68d4227ddbe5835895bb5875d542666dc75d55de |
| 2026-09-11-recurrence-engine-02/chain.json | 6a9eb64f069a8638b4d5cc552370fe2be5257ade6874b6edd2aa364ae85c48ba |
| 2026-09-11-recurrence-engine-02/grading/receipts/01-phase-1-home.json | 0306de7c7febd59adfaee7a2083c4614e7f8669f42eb14e942fbdd265ba03b64 |
| 2026-09-11-recurrence-engine-03/grading/receipts/01-phase-1-home.json | 894178844b2f982cea0ca2a05139ad4ce1b2d4222991158b49c78a909274ee50 |
| 2026-09-11-recurrence-engine-03/grading/receipts/02-phase-2-board.json | 088d3715404f31da19bc5bfbc915d5984f445b1b8e6f553bec64a01abc393f8f |
| 2026-09-11-recurrence-engine-03/grading/receipts/03-phase-3-add.json | f14064840b8f368fad25695d788b74a8537996467f8678c8c79c0720b72fdf00 |
| 2026-09-11-recurrence-engine-03/grading/receipts/04-phase-4-resolve-reopen.json | 6da68450d316a2b51a84bbae7615c8ce2b8a13294a51629c8a13d736019ad687 |
| 2026-09-11-te4-screen-engine-01/grading/receipts/01-phase-1-home.json | 709fd3c1abb2a977050cd40aed4610f3c3d41a2d9c7f837abb9e747f7e817986 |
| 2026-09-11-te4-screen-engine-01/grading/receipts/02-phase-2-board.json | f83d091261bc8ee4518e91d8e73b6c447dbffe60ac7c315c4a43be2c8c3ee389 |
| 2026-09-11-te4-screen-engine-01/grading/receipts/03-phase-3-add.json | bccaf411b494b669d525c547bfe191170af70aca286ffbad702296dbd22a2c6b |
| 2026-09-11-te4-screen-engine-01/grading/receipts/04-phase-4-resolve-reopen.json | 3511701cbba28407ddbef27407d0129af180b1e38aea8c92eef35088425f5ece |
| 2026-09-11-te4-screen-engine-02/grading/receipts/01-phase-1-home.json | 6f4d7e9fc8da4cdae0795f21cab4bfecb48f46235efc71bbf6e7348c10688c4f |
| 2026-09-11-te4-screen-engine-02/grading/receipts/02-phase-2-board.json | a452c9d646a2e862acadf69c80d24e9c0df3975963b2523e04f477b89bc23df1 |
| 2026-09-11-te4-screen-engine-02/grading/receipts/03-phase-3-add.json | 259d608426c4693ec2d6d533219821e27393b82a659820a294ae6d2100ec90ab |
| 2026-09-11-te4-screen-engine-02/grading/receipts/04-phase-4-resolve-reopen.json | 74e8d9890eb3b1faa2236af9995cbd614113ab8bcc5738cccb41f24423e7179e |
| 2026-09-10-te4-route-baseline-01/agentclinic-complaint-lifecycle-session-20260910-204226-768961/session-record.json | a94e7471be05213a2022a6645a13fc50f9b09ad0c73b0494fbf43d58abf38e07 |

## Claim measures

| claim_id | measure | population | result | evidence |
|---|---|---|---|---|
| c-engine-population | population statement | agentclinic-complaint-lifecycle attempts named by the grader's retained receipts and session records | yes | derived 18 Engine attempts and 3 Baseline attempts (published 18 Engine attempts and 3 Baseline attempts) |
| c-baseline-3-of-3 | completion_rate | 3 Baseline attempts on agentclinic-complaint-lifecycle | yes | derived 3 yes, 0 undecidable, of 3 Baseline sessions on agentclinic-complaint-lifecycle completed the task (published 3 of 3); operationalization gap: the session `code` names completion; the final step's hidden- grader `feature_verdict` is a separate signal |
| c-contemporaneous-screen-tie-2-of-2 | completion_rate | the final screen, both configurations fresh on the identical prompt | undecidable | no classifier covers this measure in V2a |
| c-completion-6-of-18 | completion_rate | 18 Engine attempts on agentclinic-complaint-lifecycle | yes | derived 6 yes, 0 undecidable, of 18 Engine attempts on agentclinic-complaint-lifecycle completed the task (published 6 of 18); operationalization gap: a chain shorter than the declared four phases is a phase-2-board runaway (a non-completion), not an ungradeable record |
| c-completion-4-of-16 | completion_rate | 16 Engine attempts before the 2026-09-11 screen | yes | derived 4 yes, 0 undecidable, of 16 pre-screen Engine attempts on agentclinic-complaint-lifecycle completed the task (published 4 of 16); operationalization gap: a chain shorter than the declared four phases is a phase-2-board runaway (a non-completion), not an ungradeable record |
| c-destroyed-13-of-15 | destructive_edit | 15 phase-4-reaching Engine attempts | yes | derived 15 yes, 0 undecidable, of 15 phase-4-reaching Engine attempts applied a destructive edit (published 13 of 15); operationalization gap: the classifier counts any content-changing edit, not the source's route-specific destruction (2 of 15 never touched the route) |
| c-restored-9-of-15 | restoration | 15 phase-4-reaching Engine attempts | yes | derived 3 yes, 0 undecidable, of 15 phase-4-reaching Engine attempts restored removed content (published 9 of 15); operationalization gap: the classifier counts any removed content re-added, not the source's route-specific restoration before the phase ended |
| c-redirect-fixed-1-of-9 | redirect_trap_resolution | 9 attempts showing the redirect-trap signature | undecidable | no classifier covers this measure in V2a |
| c-nonrestore-0-of-6 | completion_rate | 6 non-restoring phase-4-reaching Engine attempts | undecidable | the completion verdict is readable from chain.json, but the restoring/non-restoring split is the route-specific restoration the transcript-level `restoration` measure cannot reproduce; enumerating the subset would reopen the 9-of-15 decision |
| c-restore-4-of-7 | completion_rate | 7 restoring phase-4-reaching Engine attempts | undecidable | the completion verdict is readable from chain.json, but the restoring/non-restoring split is the route-specific restoration the transcript-level `restoration` measure cannot reproduce; enumerating the subset would reopen the 9-of-15 decision |
| c-phase4-denominator-6-of-10 | denominator_binding | 8 of 10 attempts under the current prompt (phase-4-reaching subset enumerable; pre-phase-4 chains not enumerable) | undecidable | all pre-phase-4 chains are non-enumerable from retained artifacts (the published correction counts two of them); a chain that stopped before phase 4 retained only phase-1/phase-2 packets, whose content is byte-identical between the superseded guardrail prompt and the current prompt, so its current-prompt membership is not derivable from retained artifacts |
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
| c-engine-population | claim | confirmed | population statement | agentclinic-complaint-lifecycle, Phase TE sequence | 18 Engine attempts and 3 Baseline attempts | docs/current/te6-explain-and-decide.md:38 | — |
| c-baseline-3-of-3 | claim | confirmed | completion_rate | 3 Baseline attempts on agentclinic-complaint-lifecycle | Baseline: **3 of 3 complete** | docs/current/te6-explain-and-decide.md:51 | ROADMAP.md:292 |
| c-contemporaneous-screen-tie-2-of-2 | claim | not_derivable | completion_rate | the final screen, both configurations fresh on the identical prompt | 2/2 vs 2/2 | docs/current/te6-explain-and-decide.md:67 | docs/current/te6-explain-and-decide.md:251 |
| c-completion-6-of-18 | claim | confirmed | completion_rate | 18 Engine attempts on agentclinic-complaint-lifecycle | 6 of 18 | docs/current/te6-explain-and-decide.md:54 | ROADMAP.md:292, docs/current/index.md:234, docs/current/te4-screen-result.md:43 |
| c-completion-4-of-16 | claim | confirmed | completion_rate | 16 Engine attempts before the 2026-09-11 screen | 4 of 16 | docs/current/te4-completion-recurrence-check-result.md:22 | ROADMAP.md:275, docs/current/index.md:208 |
| c-destroyed-13-of-15 | claim | claim_measure_mismatch | destructive_edit | 15 phase-4-reaching Engine attempts | destroyed in 13 of 15 | docs/current/te6-explain-and-decide.md:147 | — |
| c-restored-9-of-15 | claim | claim_measure_mismatch | restoration | 15 phase-4-reaching Engine attempts | 9 of 15 | docs/current/te6-explain-and-decide.md:169 | — |
| c-redirect-fixed-1-of-9 | claim | not_derivable | redirect_trap_resolution | 9 attempts showing the redirect-trap signature | 1 of 9 | docs/current/te6-explain-and-decide.md:174 | — |
| c-nonrestore-0-of-6 | claim | not_derivable | completion_rate | 6 non-restoring phase-4-reaching Engine attempts | 0 of 6 | docs/current/te4-completion-recurrence-check-result.md:178 | docs/current/index.md:204, ROADMAP.md:272 |
| c-restore-4-of-7 | claim | not_derivable | completion_rate | 7 restoring phase-4-reaching Engine attempts | 4 of 7 | docs/current/te4-completion-recurrence-check-result.md:179 | docs/current/index.md:205, ROADMAP.md:272 |
| c-phase4-denominator-6-of-10 | claim | not_derivable | denominator_binding | 10 attempts under the current prompt, not 8 | 6 of 8 | docs/current/te6-explain-and-decide.md:87 | docs/current/te6-explain-and-decide.md:93 |
| c-redirect-6-of-9 | claim | not_derivable | redirect_trap_occurrence | 9 phase-4-reaching Engine attempts at that round | 6 of 9 | docs/current/te4-phase4-guardrail-reverification-result.md:30 | docs/current/index.md:164 |
| c-fabricated-report-n1 | claim | confirmed | verification_claim | 1 Engine screen attempt (screen-engine-01) | fabricated a fully invented passing pytest transcript | docs/current/te6-explain-and-decide.md:110 | docs/current/te4-screen-result.md:20, ROADMAP.md:282 |
