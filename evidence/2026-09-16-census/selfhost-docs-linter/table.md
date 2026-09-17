<!-- evals be7ba898221b8f04baa3c6b566e8b0a148a30c5d; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-16-census-selfhost-docs-linter --record records/2026-09-16-census-selfhost-docs-linter.json --grade-root /Users/pauleveritt/satyrn-census-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-docs-linter | 312540 | OK | fail | not-pass | - | - | 59 | 21906 | 0 | 7 | t11:3236 | 15% | 1161.9 | 1212.3 | 19.2 | 148 | 3 | 59 | 21906 | - | - | 51 | - | - |
| selfhost-docs-linter | 374751 | OK | pass | not-pass | - | - | 52 | 24059 | 0 | 6 | t7:4954 | 21% | 1271.3 | 1338.6 | 18.8 | 158 | 4 | 52 | 24059 | 11 | 11676 | 21 | 41 | 12383 |
| selfhost-docs-linter | 453263 | BUDGET_EXCEEDED | - | not-pass | - | pass | 73 | 36505 | 0 | 6 | t4:5640 | 15% | 2172.7 | 2182.4 | 17.4 | 203 | 5 | - | - | 46 | 27113 | 63 | 27 | 9392 |
| selfhost-docs-linter | 906198 | OK | pass | not-pass | - | - | 66 | 38476 | 0 | 20 | t10:3666 | 10% | 2745.5 | 2797.5 | 14.7 | 165 | 5 | 66 | 38476 | 47 | 32481 | 52 | 19 | 5995 |
| selfhost-docs-linter | 782306 | OK | pass | pass | - | - | 40 | 27509 | 0 | 11 | t8:8996 | 33% | 1943.9 | 2007.5 | 14.2 | 114 | 4 | 40 | 27509 | 17 | 20672 | 23 | 23 | 6837 |
| selfhost-docs-linter | 845472 | OK | pass | not-pass | - | - | 54 | 38999 | 0 | 10 | t9:8529 | 22% | 2338.5 | 2374.8 | 15.6 | 138 | 3 | 54 | 38999 | 14 | 22017 | 30 | 40 | 16982 |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-docs-linter | run1 | 6 | 1 | 4 | 0 | 0 | 0 | 374751, 845472 |
| selfhost-docs-linter | run2 | 6 | 1 | 4 | 2 | 0 | 2 | - |
