<!-- evals e6b75b02bc4fb03850a3faaa431e341388533231; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-17-census2-selfhost-cell-loop --record records/2026-09-17-census2-selfhost-cell-loop.json --out evidence/2026-09-17-census-2 --grade-root /Users/pauleveritt/satyrn-census-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-cell-loop | 225004 | NO_PATCH | - | not-pass | - | - | 18 | 22915 | 1 | - | t18:16000 | 70% | 432.0 | 1256.8 | 18.1 | 45 | 3 | 18 | 22915 | - | - | - | - | - |
| selfhost-cell-loop | 352753 | BUDGET_EXCEEDED | - | not-pass | - | fail | 36 | 48214 | 0 | 17 | t12:13831 | 29% | 2040.5 | 2125.6 | 20.4 | 63 | 3 | - | - | - | - | - | - | - |
| selfhost-cell-loop | 507079 | NO_PATCH | - | not-pass | - | - | 9 | 17180 | 1 | - | t9:16000 | 93% | 101.5 | 977.1 | 17.1 | 42 | 3 | 9 | 17180 | - | - | - | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-cell-loop | run1 | 3 | 0 | 0 | 0 | 0 | 0 | - |
| selfhost-cell-loop | run2 | 3 | 0 | 0 | 0 | 0 | 0 | - |
