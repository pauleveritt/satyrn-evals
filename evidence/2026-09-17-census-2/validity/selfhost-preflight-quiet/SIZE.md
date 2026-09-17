# Size targets for `selfhost-preflight-quiet`, measured before admission

Spec section 2, "size targets, measured before admission" (Ruling 10:
measured on the artefacts the census uses, never on the worktree). All
three targets pass.

## Target 1: hidden tests, 15–20

Command:

```bash
uv run python -c "
import json
b = json.load(open('src/satyrn_evals/tasks/selfhost-preflight-quiet/manifest.json'))
ids = b['expected_test_ids']
print('hidden tests:', len(ids))
print('in 15..20:', 15 <= len(ids) <= 20)
"
```

Measured: **20** ids in `manifest.json`'s `expected_test_ids` — the ids the
grader actually executes, collected at `good` by the generator. `in 15..20:
True`. Twenty is the top of the band; every one of the twenty is a
direction or an edge the spec names.

**Pass.**

## Target 2: public suite at `base`, under 40 s

Commands:

```bash
cd "$EVALS"   # repository root, e.g. /Users/pauleveritt/projects/pauleveritt/satyrn-evals
BASE=3f7a561931e4c4fabb79991756359d6d6c9c9aac
SCRATCH="$HOME/satyrn-authored-task-scratch"   # do not use /tmp or /private/tmp
mkdir -p "$SCRATCH"
git worktree add --detach "$SCRATCH/base-preflight-quiet" "$BASE"
( cd "$SCRATCH/base-preflight-quiet" && uv sync -q && time uv run pytest -q -m "not integration" )
git worktree remove --force "$SCRATCH/base-preflight-quiet"
```

Machine: `US-BOS-UNIT-0045`, Darwin 25.6.0, arm64, 18 logical CPUs. Date:
2026-09-17, ~08:48 America/New_York. Before timing, `top -l 1` showed load
average 7.46/6.97/6.52 and CPU usage 21.55% user / 13.1% sys / 65.42% idle
— the machine was carrying other work (1070 processes, 6 running), not
quiet. Because the first figure was not close to the 40 s line but was not
trivially far from it either, the suite was run twice rather than once, and
both figures are reported (not the best of the two). The target is wall
clock, so wall clock (from `time`) leads; pytest's own internal suite time
is kept alongside it:

- Run 1: `time` wall clock **32.768 s** total elapsed (pytest's internal
  figure: `2462 passed, 336 deselected in 32.16s`)
- Run 2: `time` wall clock **31.421 s** total elapsed (pytest's internal
  figure: `2462 passed, 336 deselected in 31.19s`)

Contention inflates wall clock, never deflates it: at load average 7.46 on
an 18-core machine the measured figure is a **ceiling**, not a best case. A
quiet machine would run this suite no slower than what is reported here, so
a passing figure taken under contention is a strictly stronger pass than
the same figure would be on a quiet machine. Two decimal places on a
contended run with a ~1.3 s spread between the two attempts claims more
precision than the measurement has; read it honestly as **roughly 31-33 s,
an upper bound, against the 40 s target** — comfortably clear of it.

The scratch worktree was removed with `git worktree remove --force` after
each pass/fail determination; it was never one of the seven historical
worktrees under `.claude/worktrees/` and is not left behind (`git worktree
list` after removal shows only the main checkout and the seven historical
worktrees).

**Pass.**

## Target 3: the diff's reach — one new module, one new test module

Commands:

```bash
grep '^diff --git' src/satyrn_evals/tasks/selfhost-preflight-quiet/fixtures/known-good.patch
git show --name-only --format= d3a97ec64833f1e9b9682211e50342d2d71b705c
git diff --name-only 3f7a561931e4c4fabb79991756359d6d6c9c9aac d3a97ec64833f1e9b9682211e50342d2d71b705c
```

Measured:

- `known-good.patch`'s only `diff --git` line: `a/scripts/preflight_quiet.py b/scripts/preflight_quiet.py`
  — the graded patch touches exactly `scripts/preflight_quiet.py`.
- The good commit's `--name-only` listing: `PROVENANCE.md`,
  `scripts/preflight_quiet.py`, `tests/test_preflight_quiet.py`.
- `git diff --name-only` from base to good: the same three paths.

Read per Ruling 12: one new module (`scripts/preflight_quiet.py`), one new
test module (`tests/test_preflight_quiet.py`), and the convention row
`PROVENANCE.md` requires (`AGENTS.md`, listed in `ignored_paths` and
excluded from `base/`). No third source module.

**Pass.**

## Overlay identity re-confirmation (Ruling 13)

```bash
uv run python - <<'PY'
import re
from pathlib import Path
doc = Path("docs/superpowers/plans/2026-09-18-preflight-quiet.md").read_text(encoding="utf-8")
body = doc[doc.index("### Task 1: The machine-quiet preflight"):]
want = re.search(r"```python\n(.*?)\n```", body, re.S).group(1) + "\n"
got = Path("src/satyrn_evals/tasks/selfhost-preflight-quiet/overlay/test_preflight_quiet.py").read_text(encoding="utf-8")
print("overlay identical to the heading:", want == got)
raise SystemExit(0 if want == got else 1)
PY
```

Measured: `overlay identical to the heading: True`, exit code `0`
(`unedited=0`). The overlay the grader runs is byte-identical to the suite
written from the spec before any implementation existed — the basis for
"authored, not cut."

**Pass.**

## What these targets do and do not establish

`selfhost-preflight-quiet` **meets all three size targets pre-registered
for it** in the approved design spec,
`docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md`
section 2, "The task" ("Size targets, measured before admission": hidden
tests 15-20; public suite under 40 s; the good commit's diff touches one
new module and one new test module only), measured here on the census's
own artefacts (`manifest.json`, `known-good.patch`, the good commit).

That pre-registration is a band chosen **for this task alone**; it is not
a description of, and does not discriminate, the census's existing
medium/large split. `evidence/2026-09-16-census/README.md` and
`evidence/2026-09-16-census/classes-summary.md` contain no hidden-test
counts, module counts, or suite-second figures for any task — their
medium/large split is an **outcome** class, built on pass states and
finishing behaviour ("Medium builds are finishing-bound", README §"What
the two nights say" point 2; "Large builds are out of reach at 9B", point
3), not on size. And the three size figures do not separate the two
outcome classes in the committed artefacts: measured the same way as
above, across all six census tasks,

| task | hidden tests | files in `known-good.patch` |
|---|---|---|
| agentclinic-repair-depth-3 | 13 | 3 (`app.py`, `models.py`, `templates/base.html`) |
| selfhost-docs-linter | 15 | 1 (`tools/lint_docs.py`) |
| selfhost-run-record-gate | 20 | 2 (`src/satyrn_evals/cli.py`, `run_record.py`) |
| selfhost-speed-probe | 17 | 2 (`ROADMAP.md`, `scripts/speed_probe.py`) |
| selfhost-cell-loop | 22 | 1 (`src/satyrn_evals/launch.py`) |
| **selfhost-preflight-quiet** | **20** | **1 (`scripts/preflight_quiet.py`)** |

`selfhost-run-record-gate` (medium, outcome-classed) has a two-module
graded patch; `selfhost-cell-loop` (large, outcome-classed, carries no
caveat in the signed reading) has a one-module patch and a hidden-test
count above this task's; `selfhost-speed-probe`'s 17 hidden tests sit
inside the 15-20 band despite `speed-probe` itself being dropped from the
census's large-tier ceiling set for a named prompt defect (README,
"Deviations, stated": cut prompt carries an attended checklist and a
preflight a cell cannot run, "never claimed against"). No combination of
the three targets, taken from this table, separates the medium tier from
the large tier.

Which tier `selfhost-preflight-quiet` actually belongs to is not decided
here. Per design spec section 5, "What it decides": that is what the
task's own admission night (night 3) decides, from its cells' finishing
shape — a finishing shape puts the medium tier three wide; comfortable
passes make it a floor task and the tier stays two wide; no pass state
means the size class was misjudged and the task is re-scoped, not claimed
against.
