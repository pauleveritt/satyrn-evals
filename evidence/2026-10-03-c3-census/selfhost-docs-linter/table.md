<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-docs-linter --record records/2026-10-02-c1-selfhost-docs-linter.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->
<!-- decode tok/s: the per-stream rate while this many (`decode overlap`) cell spans shared the machine -- not this cell's private stream, and not the machine's aggregate throughput (which is higher by roughly `decode overlap`); decode n is that shared completion count, counted once per overlapping cell (Ruling 7) -->

| task | attempt | code | verdict | verdict@32k | raised | tripped | turns | tokens | length stops | exploration turns | biggest turn | biggest share | tool span s | whole-attempt s | decode tok/s | decode n | decode overlap | self-stop turn | self-stop tokens | pass turn | pass tokens | own-green turn | post-pass turns | post-pass tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-docs-linter | 593944 | OK | pass | pass | - | - | 48 | 28564 | 0 | 8 | t8:6612 | 23% | 2308.4 | 2365.7 | 16.4 | 147 | 5 | 48 | 28564 | 32 | 24591 | 33 | 16 | 3973 |
| selfhost-docs-linter | 646828 | OK | pass | not-pass | - | - | 44 | 35739 | 0 | 10 | t10:7348 | 21% | 2179.5 | 2222.6 | 16.3 | 132 | 4 | 44 | 35739 | 19 | 24051 | 25 | 25 | 11688 |
| selfhost-docs-linter | 708458 | OK | fail | not-pass | - | - | 42 | 30833 | 0 | 11 | t9:7573 | 25% | 1918.3 | 1985.5 | 16.4 | 105 | 3 | 42 | 30833 | - | - | 31 | - | - |
| selfhost-docs-linter | 556770 | OK | pass | pass | - | - | 44 | 29742 | 0 | 10 | t6:4509 | 15% | 1947.1 | 2000.0 | 15.0 | 139 | 5 | 44 | 29742 | - | - | 36 | - | - |
| selfhost-docs-linter | 125810 | OK | pass | pass | - | - | 42 | 21453 | 0 | 8 | t6:3789 | 18% | 1423.2 | 1506.3 | 14.9 | 97 | 4 | 42 | 21453 | 20 | 13464 | 22 | 22 | 7989 |
| selfhost-docs-linter | 007105 | OK | pass | pass | - | - | 42 | 31082 | 0 | 12 | t7:5506 | 18% | 1866.9 | 1907.9 | 14.9 | 113 | 3 | 42 | 31082 | - | - | 35 | - | - |

## Per task (nothing pools across tasks)

| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |
|---|---|---|---|---|---|---|---|---|
| selfhost-docs-linter | run1 | 6 | 4 | 5 | 0 | 0 | 0 | 646828, 708458, 556770, 007105 |
| selfhost-docs-linter | run2 | 6 | 4 | 5 | 1 | 2 | -1 | - |
