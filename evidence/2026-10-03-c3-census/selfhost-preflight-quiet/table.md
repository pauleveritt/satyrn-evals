<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-preflight-quiet --record records/2026-10-02-c1-selfhost-preflight-quiet.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-preflight-quiet | 274281 | OK | fail | not-pass | - | - | 53 | 39933 | 0 | 17 | t12:5020 | 13% | 2814.2 | 2883.5 | 14.0 | 169 | 5 | 53 | 39933 | - | - | 41 | - | - |
| selfhost-preflight-quiet | 343289 | OK | pass | not-pass | - | - | 40 | 33629 | 0 | 15 | t14:12712 | 38% | 2329.7 | 2422.2 | 14.5 | 149 | 4 | 40 | 33629 | 21 | 23748 | 30 | 19 | 9881 |
| selfhost-preflight-quiet | 420082 | OK | pass | not-pass | - | - | 60 | 32822 | 0 | 12 | t10:3893 | 12% | 2198.4 | 2301.1 | 14.7 | 142 | 3 | 60 | 32822 | 19 | 18287 | 37 | 41 | 14535 |
| selfhost-preflight-quiet | 731480 | OK | fail | not-pass | - | - | 47 | 40509 | 0 | 12 | t8:12945 | 32% | 3001.5 | 3095.6 | 13.7 | 146 | 5 | 47 | 40509 | 17 | 26261 | 29 | 30 | 14248 |
| selfhost-preflight-quiet | 329119 | OK | pass | not-pass | - | - | 64 | 44345 | 0 | 13 | t10:14617 | 33% | 3135.8 | 3236.6 | 14.0 | 150 | 4 | 64 | 44345 | 32 | 28631 | 51 | 32 | 15714 |
| selfhost-preflight-quiet | 035112 | BUDGET_EXCEEDED | - | not-pass | - | pass | 57 | 48290 | 0 | 15 | t10:13887 | 29% | 3059.0 | 3120.0 | 14.1 | 149 | 3 | - | - | 47 | 42253 | - | 10 | 6037 |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-preflight-quiet | run1 | 6 | 0 | 3 | 0 | 0 | 0 | 343289, 420082 |
| selfhost-preflight-quiet | run2 | 6 | 0 | 3 | 2 | 0 | 2 | - |
