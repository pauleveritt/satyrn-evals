<!-- evals e6b75b02bc4fb03850a3faaa431e341388533231; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-17-census2-selfhost-speed-probe --record records/2026-09-17-census2-selfhost-speed-probe.json --out evidence/2026-09-17-census-2 --grade-root /Users/pauleveritt/satyrn-census-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-speed-probe | 771490 | NO_PATCH | - | not-pass | - | - | 10 | 17867 | 1 | - | t10:16000 | 90% | 109.3 | 924.1 | 19.2 | 32 | 3 | 10 | 17867 | - | - | - | - | - |
| selfhost-speed-probe | 897261 | BUDGET_EXCEEDED | - | not-pass | - | fail | 43 | 48428 | 0 | 11 | t4:10153 | 21% | 2508.6 | 2546.6 | 19.5 | 81 | 3 | - | - | - | - | 35 | - | - |
| selfhost-speed-probe | 067362 | BUDGET_EXCEEDED | - | not-pass | - | fail | 30 | 48300 | 0 | 15 | t4:11393 | 24% | 2253.0 | 2492.5 | 19.4 | 77 | 3 | - | - | - | - | - | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-speed-probe | run1 | 3 | 0 | 0 | 0 | 0 | 0 | - |
| selfhost-speed-probe | run2 | 3 | 0 | 0 | 0 | 0 | 0 | - |
