<!-- evals f8c1ab89399d49e15a264e6ba79e067d2c2065cf; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-16-census-agentclinic-repair-depth-3 --record records/2026-09-16-census-agentclinic-repair-depth-3.json --grade-root /Users/pauleveritt/satyrn-census-grades -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | 150526 | OK | pass | pass | - | - | 12 | 5734 | 0 | 8 | t5:2538 | 44% | 223.1 | 249.7 | 23.2 | 45 | 12 | 5734 | 9 | 5051 | 10 | 3 | 683 |
| agentclinic-repair-depth-3 | 210129 | OK | pass | pass | - | - | 8 | 2511 | 0 | 4 | t4:723 | 29% | 74.4 | 98.0 | 27.0 | 22 | 8 | 2511 | 5 | 1726 | 6 | 3 | 785 |
| agentclinic-repair-depth-3 | 282198 | OK | pass | pass | - | - | 10 | 2486 | 0 | 4 | t5:617 | 25% | 75.4 | 97.0 | 27.0 | 22 | 10 | 2486 | 7 | 1573 | 8 | 3 | 913 |
| agentclinic-repair-depth-3 | 750280 | OK | pass | pass | - | - | 12 | 3532 | 0 | 6 | t7:1800 | 51% | 167.8 | 204.6 | 18.7 | 30 | 12 | 3532 | 9 | 2613 | 10 | 3 | 919 |
| agentclinic-repair-depth-3 | 862332 | OK | pass | pass | - | - | 38 | 15764 | 0 | 30 | t6:2755 | 18% | 605.1 | 635.1 | 22.6 | 67 | 38 | 15764 | 33 | 14281 | 34 | 5 | 1483 |
| agentclinic-repair-depth-3 | 555775 | OK | pass | pass | - | - | 11 | 3017 | 0 | 5 | t5:920 | 30% | 133.6 | 165.1 | 18.7 | 20 | 11 | 3017 | 8 | 2207 | 9 | 3 | 810 |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | run1 | 6 | 6 | 6 | 0 | 0 | 0 | - |
| agentclinic-repair-depth-3 | run2 | 6 | 6 | 6 | 0 | 0 | 0 | - |
