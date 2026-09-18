<!-- evals f680a4f3dca60fea6977a9ba86e08d4bd524046d; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-18-census3-selfhost-preflight-quiet --record records/2026-09-18-census3-selfhost-preflight-quiet.json --out evidence/2026-09-18-census-3 --grade-root /Users/pauleveritt/satyrn-census-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-preflight-quiet | 566024 | OK | pass | pass | - | - | 42 | 24743 | 0 | 10 | t10:8026 | 32% | 1554.1 | 1684.3 | 17.0 | 102 | 3 | 42 | 24743 | 20 | 17595 | 24 | 22 | 7148 |
| selfhost-preflight-quiet | 091987 | BUDGET_EXCEEDED | - | not-pass | - | fail | 69 | 48079 | 0 | 8 | t8:14359 | 30% | 3185.9 | 3294.2 | 15.3 | 201 | 3 | - | - | - | - | 51 | - | - |
| selfhost-preflight-quiet | 689196 | BUDGET_EXCEEDED | - | not-pass | - | fail | 73 | 43342 | 0 | 25 | t12:14739 | 34% | 2906.2 | 2926.6 | 15.5 | 189 | 3 | - | - | - | - | 46 | - | - |
| selfhost-preflight-quiet | 717272 | OK | fail | not-pass | - | - | 58 | 47186 | 0 | 10 | t12:9594 | 20% | 3226.6 | 3304.6 | 14.6 | 171 | 3 | 58 | 47186 | - | - | 44 | - | - |
| selfhost-preflight-quiet | 166645 | BUDGET_EXCEEDED | - | not-pass | - | fail | 73 | 42466 | 0 | 31 | t6:8517 | 20% | 2998.1 | 3018.2 | 14.4 | 162 | 3 | - | - | - | - | 65 | - | - |
| selfhost-preflight-quiet | 758561 | OK | pass | not-pass | - | - | 41 | 42305 | 0 | 18 | t11:14004 | 33% | 2915.3 | 3069.4 | 14.4 | 164 | 3 | 41 | 42305 | 19 | 27403 | 25 | 22 | 14902 |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-preflight-quiet | run1 | 6 | 1 | 2 | 0 | 0 | 0 | 689196 |
| selfhost-preflight-quiet | run2 | 6 | 1 | 2 | 0 | 0 | 0 | - |
