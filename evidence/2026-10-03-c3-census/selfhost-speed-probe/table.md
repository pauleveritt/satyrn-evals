<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-speed-probe --record records/2026-10-02-c1-selfhost-speed-probe.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-speed-probe | 540863 | BUDGET_EXCEEDED | - | not-pass | - | fail | 52 | 48403 | 0 | 7 | t3:7033 | 14% | 3505.5 | 3567.3 | 13.7 | 118 | 3 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 600883 | BUDGET_EXCEEDED | - | not-pass | - | fail | 41 | 48071 | 0 | 18 | t7:9000 | 19% | 3517.0 | 3575.7 | 13.7 | 119 | 4 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 663676 | BUDGET_EXCEEDED | - | not-pass | - | fail | 30 | 52632 | 0 | 8 | t8:12766 | 24% | 3426.2 | 3819.1 | 13.6 | 128 | 5 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 342376 | BUDGET_EXCEEDED | - | not-pass | - | fail | 39 | 48597 | 0 | 10 | t4:11698 | 24% | 2561.1 | 2638.0 | 18.7 | 77 | 5 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 465243 | BUDGET_EXCEEDED | - | not-pass | - | fail | 36 | 48012 | 0 | 19 | t16:12271 | 26% | 2524.2 | 2604.8 | 18.7 | 75 | 4 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 443058 | NO_PATCH | - | not-pass | - | - | 4 | 16603 | 1 | - | t4:16000 | 96% | 31.9 | 858.1 | 16.8 | 18 | 3 | 4 | 16603 | - | - | - | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-speed-probe | run1 | 6 | 0 | 0 | 0 | 0 | 0 | - |
| selfhost-speed-probe | run2 | 6 | 0 | 0 | 0 | 0 | 0 | - |
