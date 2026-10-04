<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-agentclinic-repair-depth-3 --record records/2026-10-02-c1-agentclinic-repair-depth-3.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | 107978 | OK | pass | pass | - | - | 7 | 2094 | 0 | 3 | t4:856 | 41% | 56.9 | 72.6 | 30.7 | 17 | 3 | 7 | 2094 | 4 | 1162 | 5 | 3 | 932 |
| agentclinic-repair-depth-3 | 152067 | OK | pass | pass | - | - | 12 | 3442 | 0 | 5 | t4:1078 | 31% | 105.2 | 127.7 | 29.4 | 26 | 4 | 12 | 3442 | 8 | 2241 | 9 | 4 | 1201 |
| agentclinic-repair-depth-3 | 197431 | OK | pass | pass | - | - | 11 | 8052 | 0 | 8 | t8:2621 | 33% | 299.6 | 337.7 | 23.9 | 55 | 6 | 11 | 8052 | 9 | 7202 | 10 | 2 | 850 |
| agentclinic-repair-depth-3 | 550946 | OK | pass | pass | - | - | 14 | 4875 | 0 | 5 | t4:1290 | 26% | 194.8 | 220.5 | 22.9 | 29 | 4 | 14 | 4875 | 11 | 3920 | 12 | 3 | 955 |
| agentclinic-repair-depth-3 | 810657 | OK | pass | pass | - | - | 12 | 7895 | 0 | 7 | t8:2777 | 35% | 350.0 | 381.8 | 20.7 | 37 | 4 | 12 | 7895 | 9 | 6998 | 10 | 3 | 897 |
| agentclinic-repair-depth-3 | 499793 | COMMAND_TIMEOUT | - | not-pass | - | - | 11 | 5373 | 0 | - | t10:1688 | 31% | 286.9 | 4800.5 | 21.1 | 17 | 3 | - | - | - | - | - | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | run1 | 6 | 5 | 5 | 0 | 0 | 0 | - |
| agentclinic-repair-depth-3 | run2 | 6 | 5 | 5 | 0 | 0 | 0 | - |
