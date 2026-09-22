<!-- evals 059968d9484d9e20022dac18761f666d69866fa6; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-17-census2-selfhost-run-record-gate --record records/2026-09-17-census2-selfhost-run-record-gate.json --out evidence/2026-09-17-census-2 --grade-root /Users/pauleveritt/satyrn-census-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-run-record-gate | 891860 | BUDGET_EXCEEDED | - | not-pass | - | pass | 73 | 36602 | 0 | 9 | t8:7065 | 19% | 2148.7 | 2159.7 | 17.9 | 177 | 3 | - | - | 16 | 12576 | 33 | 57 | 24026 |
| selfhost-run-record-gate | 949626 | BUDGET_EXCEEDED | - | not-pass | - | pass | 73 | 46077 | 0 | 13 | t12:8218 | 18% | 2537.5 | 2545.4 | 18.2 | 197 | 3 | - | - | 18 | 13154 | 46 | 55 | 32923 |
| selfhost-run-record-gate | 016509 | OK | pass | not-pass | - | - | 53 | 39166 | 0 | 7 | t7:13360 | 34% | 2369.2 | 2419.4 | 18.0 | 191 | 3 | 53 | 39166 | 12 | 17570 | 31 | 41 | 21596 |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-run-record-gate | run1 | 3 | 0 | 1 | 0 | 0 | 0 | 891860, 949626, 016509 |
| selfhost-run-record-gate | run2 | 3 | 0 | 1 | 3 | 0 | 3 | - |
