<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-cell-loop --record records/2026-10-02-c1-selfhost-cell-loop.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-cell-loop | 133224 | NO_PATCH | - | not-pass | - | - | 9 | 16955 | 1 | - | t9:16000 | 94% | 99.5 | 1165.3 | 12.3 | 44 | 3 | 9 | 16955 | - | - | - | - | - |
| selfhost-cell-loop | 196867 | NO_PATCH | - | not-pass | - | - | 22 | 22847 | 1 | - | t22:16000 | 70% | 619.2 | 1646.8 | 13.5 | 78 | 5 | 22 | 22847 | - | - | - | - | - |
| selfhost-cell-loop | 263141 | NO_PATCH | - | not-pass | - | - | 15 | 17485 | 1 | - | t15:16000 | 92% | 270.2 | 1296.8 | 13.2 | 53 | 4 | 15 | 17485 | - | - | - | - | - |
| selfhost-cell-loop | 546222 | NO_PATCH | - | not-pass | - | - | 13 | 17346 | 1 | - | t13:16000 | 92% | 178.2 | 1102.7 | 14.9 | 45 | 5 | 13 | 17346 | - | - | - | - | - |
| selfhost-cell-loop | 119056 | NO_PATCH | - | not-pass | - | - | 21 | 17913 | 1 | - | t21:16000 | 89% | 202.4 | 1046.6 | 16.8 | 37 | 4 | 21 | 17913 | - | - | - | - | - |
| selfhost-cell-loop | 389181 | COMMAND_TIMEOUT | - | not-pass | - | - | 12 | 7687 | 0 | - | t11:6334 | 82% | 489.8 | 4801.0 | 15.5 | 12 | 3 | - | - | - | - | - | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-cell-loop | run1 | 6 | 0 | 0 | 0 | 0 | 0 | - |
| selfhost-cell-loop | run2 | 6 | 0 | 0 | 0 | 0 | 0 | - |
