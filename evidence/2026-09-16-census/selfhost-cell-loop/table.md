<!-- evals be7ba898221b8f04baa3c6b566e8b0a148a30c5d; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-16-census-selfhost-cell-loop --record records/2026-09-16-census-selfhost-cell-loop.json --grade-root /Users/pauleveritt/satyrn-census-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-cell-loop | 442168 | NO_PATCH | - | not-pass | - | - | 14 | 18965 | 1 | - | t14:16000 | 84% | 336.1 | 1458.1 | 13.0 | 48 | 3 | 14 | 18965 | - | - | - | - | - |
| selfhost-cell-loop | 631530 | COMMAND_TIMEOUT | - | not-pass | - | - | 15 | 37843 | 0 | 10 | t12:14216 | 38% | 2939.6 | 3003.0 | 12.9 | 84 | 5 | - | - | - | - | 12 | - | - |
| selfhost-cell-loop | 918779 | COMMAND_TIMEOUT | - | not-pass | - | - | 43 | 36474 | 0 | 23 | t14:9209 | 25% | 2852.0 | 3002.9 | 12.9 | 84 | 5 | - | - | - | - | - | - | - |
| selfhost-cell-loop | 346861 | NO_PATCH | - | not-pass | - | - | 8 | 17214 | 1 | - | t8:16000 | 93% | 125.6 | 1296.6 | 12.9 | 25 | 3 | 8 | 17214 | - | - | - | - | - |
| selfhost-cell-loop | 320931 | COMMAND_TIMEOUT | - | not-pass | - | - | 33 | 46351 | 0 | 14 | t18:11777 | 25% | 2981.8 | 3004.3 | 17.7 | 55 | 4 | - | - | - | - | - | - | - |
| selfhost-cell-loop | 332393 | NO_PATCH | - | not-pass | - | - | 22 | 21438 | 1 | - | t22:16000 | 75% | 383.2 | 1311.5 | 16.5 | 30 | 2 | 22 | 21438 | - | - | - | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-cell-loop | run1 | 6 | 0 | 0 | 0 | 0 | 0 | - |
| selfhost-cell-loop | run2 | 6 | 0 | 0 | 0 | 0 | 0 | - |
