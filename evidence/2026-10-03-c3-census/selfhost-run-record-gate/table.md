<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-run-record-gate --record records/2026-10-02-c1-selfhost-run-record-gate.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-run-record-gate | 922721 | OK | pass | not-pass | - | - | 69 | 34085 | 0 | 7 | t7:8068 | 24% | 2491.3 | 2540.0 | 14.9 | 181 | 3 | 69 | 34085 | 13 | 11866 | 42 | 56 | 22219 |
| selfhost-run-record-gate | 977901 | OK | pass | not-pass | - | - | 71 | 39330 | 0 | 6 | t5:10163 | 26% | 3316.7 | 3431.5 | 14.5 | 233 | 5 | 71 | 39330 | 50 | 30464 | 40 | 21 | 8866 |
| selfhost-run-record-gate | 035436 | BUDGET_EXCEEDED | - | not-pass | - | pass | 73 | 36861 | 0 | 14 | t12:7488 | 20% | 3149.1 | 3159.0 | 14.8 | 213 | 4 | - | - | 26 | 14644 | 50 | 47 | 22217 |
| selfhost-run-record-gate | 688591 | OK | pass | not-pass | - | - | 60 | 32469 | 0 | 6 | t6:8957 | 28% | 2468.7 | 2563.6 | 12.9 | 160 | 5 | 60 | 32469 | 27 | 22400 | 34 | 33 | 10069 |
| selfhost-run-record-gate | 427312 | OK | pass | not-pass | - | - | 61 | 33422 | 0 | 12 | t11:4801 | 14% | 2621.8 | 2722.4 | 13.1 | 166 | 4 | 61 | 33422 | 22 | 13829 | 36 | 39 | 19593 |
| selfhost-run-record-gate | 547893 | BUDGET_EXCEEDED | - | not-pass | - | pass | 73 | 45095 | 0 | 12 | t12:8475 | 19% | 3067.5 | 3081.9 | 14.1 | 170 | 3 | - | - | 28 | 16749 | 36 | 45 | 28346 |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-run-record-gate | run1 | 6 | 0 | 4 | 0 | 0 | 0 | 922721, 977901, 688591, 427312, 547893 |
| selfhost-run-record-gate | run2 | 6 | 0 | 4 | 4 | 0 | 4 | - |
