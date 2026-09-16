<!-- evals e606b24d8f0dbc8a2eb3aa19a0c7adffdba85ced; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-16-census-selfhost-speed-probe --record records/2026-09-16-census-selfhost-speed-probe.json -->

| task | attempt | code | verdict | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-speed-probe | 529092 | COMMAND_TIMEOUT | - | - | - | 65 | 44948 | 0 | 22 | t8:9462 | 21% | 2967.5 | 3002.7 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 691593 | NO_PATCH | - | - | - | 5 | 16764 | 1 | - | t5:16000 | 95% | 45.4 | 868.9 | 5 | 16764 | - | - | - | - | - |
| selfhost-speed-probe | 941646 | COMMAND_TIMEOUT | - | - | - | 42 | 36293 | 0 | 10 | t6:11621 | 32% | 2426.7 | 3002.7 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 944467 | COMMAND_TIMEOUT | - | - | - | 37 | 35177 | 0 | 35 | t30:9195 | 26% | 2910.4 | 3002.7 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 123802 | BUDGET_EXCEEDED | - | - | fail | 48 | 48025 | 0 | 20 | t7:13222 | 28% | 2369.6 | 2415.8 | - | - | - | - | - | - | - |
| selfhost-speed-probe | 524583 | NO_PATCH | - | - | - | 6 | 26639 | 1 | - | t6:16000 | 60% | 693.4 | 1564.1 | 6 | 26639 | - | - | - | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|
| selfhost-speed-probe | run1 | 6 | 0 | 0 | 0 | - |
| selfhost-speed-probe | run2 | 6 | 0 | 0 | 0 | - |
