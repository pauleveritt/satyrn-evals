<!-- evals 4b8fc430daf77f55992ddb232c712ea92716fd60; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-16-census-selfhost-speed-probe --record records/2026-09-16-census-selfhost-speed-probe.json --grade-root /Users/pauleveritt/satyrn-census-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-speed-probe | 529092 | COMMAND_TIMEOUT | - | not-pass | - | - | 65 | 44948 | 0 | 22 | t8:9462 | 21% | 2967.5 | 3002.7 | 15.2 | 144 | 4 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 691593 | NO_PATCH | - | not-pass | - | - | 5 | 16764 | 1 | - | t5:16000 | 95% | 45.4 | 868.9 | 18.9 | 29 | 3 | 5 | 16764 | - | - | - | - | - |
| selfhost-speed-probe | 941646 | COMMAND_TIMEOUT | - | not-pass | - | - | 42 | 36293 | 0 | 10 | t6:11621 | 32% | 2426.7 | 3002.7 | 15.2 | 144 | 4 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 944467 | COMMAND_TIMEOUT | - | not-pass | - | - | 37 | 35177 | 0 | 35 | t30:9195 | 26% | 2910.4 | 3002.7 | 13.6 | 127 | 5 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 123802 | BUDGET_EXCEEDED | - | not-pass | - | fail | 48 | 48025 | 0 | 20 | t7:13222 | 28% | 2369.6 | 2415.8 | 18.5 | 55 | 3 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 524583 | NO_PATCH | - | not-pass | - | - | 6 | 26639 | 1 | - | t6:16000 | 60% | 693.4 | 1564.1 | 16.6 | 20 | 3 | 6 | 26639 | - | - | - | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-speed-probe | run1 | 6 | 0 | 0 | 0 | 0 | 0 | - |
| selfhost-speed-probe | run2 | 6 | 0 | 0 | 0 | 0 | 0 | - |
