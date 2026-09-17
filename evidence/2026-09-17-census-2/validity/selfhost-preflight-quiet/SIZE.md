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
BASE=3f7a561931e4c4fabb79991756359d6d6c9c9aac
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
both figures are reported (not the best of the two):

- Run 1: `2462 passed, 336 deselected in 32.16s` (wall clock per `time`:
  32.768s total elapsed)
- Run 2: `2462 passed, 336 deselected in 31.19s` (wall clock per `time`:
  31.421s total elapsed)

Both figures are under 40 s. The scratch worktree was removed with
`git worktree remove --force` after each pass/fail determination; it was
never one of the seven historical worktrees under `.claude/worktrees/` and
is not left behind (`git worktree list` after removal shows only the main
checkout and the seven historical worktrees).

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

## Tier placement

All three measured targets — 20 hidden tests (band 15–20), a public suite
of 31–32 s (under 40 s), and a diff touching exactly one new module plus
one new test module — place `selfhost-preflight-quiet` in the medium-build
tier: the `selfhost-run-record-gate` size class described by the census's
signed reading (`evidence/2026-09-16-census/README.md`,
`evidence/2026-09-16-census/classes-summary.md`), not the large tier that
`selfhost-cell-loop` and `selfhost-speed-probe` occupy. The signed reading
calls run-record-gate and docs-linter "the medium tier" (finishing-bound,
8 of 9 and 4 of 6 cells reaching a hidden-suite pass inside the pre-
registered line) and cell-loop and speed-probe "the large tier" (0 of 18
cells reaching any pass state at 9B, out of reach on this tier). This task
is sized and measured to sit with the former, not the latter.
