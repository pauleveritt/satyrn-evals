# Size targets for `selfhost-preflight-quiet`, measured before admission

Spec section 2, "size targets, measured before admission" (Ruling 10:
measured on the artefacts the census uses, never on the worktree). Round 2:
re-measured on the re-cut task. All three targets pass.

Shas for this cut: `base` = `3f7a561931e4c4fabb79991756359d6d6c9c9aac`,
`good` = `f7459ef5a4ccece490c8a7cb48a8e0dfea713d6b` (parent exactly `base`).
Where a command reads the heading document
`docs/superpowers/plans/2026-09-18-preflight-quiet.md`, it is read at
`plan.commit` = `3cd88a6ce1e6987293dfa638337d8594535bffd3` — deliberately not
equal to `base` on a re-cut — so the check is about the cut, not the
working tree.

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
direction or an edge the spec names. Unchanged from round 1's measurement.

**Pass.**

## Target 2: public suite under 40 s, no failures

Two measurements are taken: the `base` git worktree (what round 1
measured), and the cut `base/` directory under the task tree itself
(`src/satyrn_evals/tasks/selfhost-preflight-quiet/base`, what a cell
actually gets), copied to scratch and `uv sync`'d there. The round-2 re-cut
exists because an interim `base` was red (5 failed, 2487 passed); **any
failure is a missed target and a stop**, so both figures' pass/fail counts
are reported, not only wall clock.

Commands:

```bash
cd "$EVALS"   # repository root, e.g. /Users/pauleveritt/projects/pauleveritt/satyrn-evals
SCRATCH="$HOME/satyrn-authored-task-scratch"   # do not use /tmp or /private/tmp

# (a) the base worktree
BASE=3f7a561931e4c4fabb79991756359d6d6c9c9aac
git worktree add --detach "$SCRATCH/base-preflight-quiet" "$BASE"
( cd "$SCRATCH/base-preflight-quiet" && uv sync -q && time uv run pytest -q -m "not integration" )
git worktree remove --force "$SCRATCH/base-preflight-quiet"

# (b) the cut base/ tree itself
rm -rf "$SCRATCH/cut-base-preflight-quiet"
cp -R src/satyrn_evals/tasks/selfhost-preflight-quiet/base "$SCRATCH/cut-base-preflight-quiet"
( cd "$SCRATCH/cut-base-preflight-quiet" && rm -rf __pycache__ && uv sync -q && time uv run pytest -q -m "not integration" )
rm -rf "$SCRATCH/cut-base-preflight-quiet"
```

Machine: `US-BOS-UNIT-0045`, macOS 27.0 (build 26A428), arm64, 18 logical
CPUs. Date: 2026-09-17, ~14:13–14:15 America/New_York. Before the first run,
`uptime` showed load average 4.32/5.14/5.40; by the second run it had risen
to 5.83/5.71/5.61 (`top -l 1`: 929 processes, 6 running, 18.1% user / 12.2%
sys / 69.7% idle). The machine was carrying other work throughout, not
quiet.

The target names **wall clock**, so `time`'s total elapsed figure leads;
pytest's own internal suite-time figure is kept alongside it, labelled:

- (a) `base` worktree: `time` wall clock **34.9 s** total elapsed
  (`uv run pytest -q -m "not integration"` command: 34.851 s, the
  elapsed/total field of zsh `time`'s output — not a sum of the user
  (3.40 s) and system (3.19 s) fields it reports beside it; pytest's own
  internal figure: `2462 passed, 336 deselected in 34.16s`). **2462
  passed, 0 failed, 336 deselected.**
- (b) cut `base/` tree: `time` wall clock **34.8 s** total elapsed
  (pytest's own internal figure: `2462 passed, 336 deselected in 34.38s`).
  **2462 passed, 0 failed, 336 deselected.**

Both figures agree with the controller's independent measurement of the
committed `base/` (2462 passed, 0 failed, 336 deselected, 33.24 s) and the
Task 3 re-reviewer's (2462 / 0 / 336 in 33.04 s) to within about a second —
consistent with this run's higher contention.

Contention inflates wall clock, never deflates it: at a load average of
roughly 4-6 on an 18-core, otherwise-busy machine (this page's own two
readings span 4.32 to 5.83), both measured figures
are a **ceiling**, not a best case. A quiet machine would run this suite no
slower than what is reported here, so a passing figure taken under this
contention is a strictly stronger pass than the same figure on a quiet
machine would be. One decimal place is what the ~34.8-34.9 s spread across
the two runs supports; read it honestly as **roughly 35 s, an upper bound,
against the 40 s target** — inside it, but with less headroom than round
1's ~31-33 s figure (measured on a different cut, at lower contention; the
round-1 figure is not comparable to this one).

The scratch worktree was removed with `git worktree remove --force`, and
the scratch copy of the cut `base/` tree removed with `rm -rf`, after each
measurement; neither is one of the seven historical worktrees under
`.claude/worktrees/`, and neither is left behind.

**Pass** — both measured trees: no failures, wall clock under 40 s.

## Target 3: the diff's reach — one new module, one new test module

Commands:

```bash
grep '^diff --git' src/satyrn_evals/tasks/selfhost-preflight-quiet/fixtures/known-good.patch
git show --name-only --format= f7459ef5a4ccece490c8a7cb48a8e0dfea713d6b
git diff --name-only 3f7a561931e4c4fabb79991756359d6d6c9c9aac f7459ef5a4ccece490c8a7cb48a8e0dfea713d6b
```

Measured:

- `known-good.patch`'s only `diff --git` line: `a/scripts/preflight_quiet.py b/scripts/preflight_quiet.py`
  — the graded patch touches exactly `scripts/preflight_quiet.py`.
- The good commit's `--name-only` listing: `PROVENANCE.md`,
  `scripts/preflight_quiet.py`, `tests/test_preflight_quiet.py`.
- `git diff --name-only` from base to good: the same three paths.
- The good commit's parent is exactly `base` (`git log --format=%P -1
  f7459ef5a4ccece490c8a7cb48a8e0dfea713d6b` → `3f7a561931e4c4fabb79991756359d6d6c9c9aac`).

Read per Ruling 12: one new module (`scripts/preflight_quiet.py`), one new
test module (`tests/test_preflight_quiet.py`), and the convention row
`PROVENANCE.md` requires (`AGENTS.md`, listed in `ignored_paths` and
excluded from `base/`). No third source module.

**Pass.**

## Overlay identity re-confirmation (Ruling 13)

Read at `plan.commit` = `3cd88a6ce1e6987293dfa638337d8594535bffd3`, not the
working tree, so the check is about the cut:

```bash
uv run python - <<'PY'
import re, subprocess
from pathlib import Path
doc = subprocess.run(
    ["git", "show", "3cd88a6:docs/superpowers/plans/2026-09-18-preflight-quiet.md"],
    capture_output=True, text=True, check=True,
).stdout
body = doc[doc.index("### Task 1: The machine-quiet preflight"):]
want = re.search(r"```python\n(.*?)\n```", body, re.S).group(1) + "\n"
got = Path("src/satyrn_evals/tasks/selfhost-preflight-quiet/overlay/test_preflight_quiet.py").read_text(encoding="utf-8")
print("overlay identical to the heading:", want == got)
raise SystemExit(0 if want == got else 1)
PY
```

Measured: `overlay identical to the heading: True`, exit code `0`
(`unedited=0`). The overlay the grader runs is byte-identical to the suite
written from the spec before any implementation existed, at `plan.commit`
— the basis for "authored, not cut."

**Pass.**

## What these targets do and do not establish

`selfhost-preflight-quiet` **meets all three size targets pre-registered
for it** in the approved design spec,
`docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md`
section 2, "The task" ("Size targets, measured before admission": hidden
tests 15-20; public suite under 40 s; the good commit's diff touches one
new module and one new test module only), measured here on the round-2
re-cut's own artefacts (`manifest.json`, `known-good.patch`, the good
commit, the cut `base/` tree).

**Ruling T5-1 (carried from round 1, upheld on review): this pre-registered
band is not, and must not be read as, a size class attributed to the
census's signed reading.** `evidence/2026-09-16-census/README.md` and
`evidence/2026-09-16-census/classes-summary.md` were read again for this
round and contain **no size figures anywhere** — no hidden-test counts, no
module counts, no suite-second figures, for any task. Their medium/large
split is an **outcome** class, built on pass states and finishing
behaviour ("Medium builds are finishing-bound", README, "What the two
nights say" point 2, line 58; "Large builds are out of reach at 9B", point
3, line 64), never on a size measurement. The 15-20 band measured above
comes only from the approved design spec, section 2, which pre-registers
it **for this task alone**.

That band does not discriminate the two outcome tiers, either. Two
columns — hidden-test count and `known-good.patch` file count — were
re-measured from the committed manifests and `known-good.patch` files of
all six census tasks; every number below was re-run for this round and is
unchanged from round 1's measurement:

| task | hidden tests | files in `known-good.patch` |
|---|---|---|
| agentclinic-repair-depth-3 | 13 | 3 (`app.py`, `models.py`, `templates/base.html`) |
| selfhost-docs-linter | 15 | 1 (`tools/lint_docs.py`) |
| selfhost-run-record-gate | 20 | 2 (`src/satyrn_evals/cli.py`, `src/satyrn_evals/run_record.py`) |
| selfhost-speed-probe | 17 | 2 (`ROADMAP.md`, `scripts/speed_probe.py`) |
| selfhost-cell-loop | 22 | 1 (`src/satyrn_evals/launch.py`) |
| **selfhost-preflight-quiet** | **20** | **1 (`scripts/preflight_quiet.py`)** |

Hidden-test counts interleave across the outcome tiers (13, 15, 17 below
the large tier's 20 and 22; this task's own 20 ties run-record-gate's
medium-tier count) and the file-count sets are identical (1 or 2) on both
sides. No threshold on either of these two columns separates the medium
tier from the large tier. (Only these two columns are re-measured here;
public-suite wall-clock seconds are not measured for the other five tasks
on this page — all five self-hosted tasks among them share the same public
suite in any case, so a per-task seconds figure would not add a third,
separating column even if it were measured.)

`selfhost-run-record-gate` (medium, outcome-classed) has a two-module
graded patch; `selfhost-cell-loop` (large, outcome-classed) has a
one-module patch and a hidden-test count above this task's. Unlike
speed-probe, cell-loop carries no *deviation* entry dropping it from the
census's large-tier ceiling set. But it is not uncaveated either:
`classes-summary.md`'s "Cells where I was unsure, with both readings"
records a reservation on cells 442168 and 225004, both classed
`information` **False** under reading A ("no fact is omitted... the cells
over-read a term needing no reading"; `information` is False on all 39
census cells, `classes-summary.md:22`, and 442168's own row in
`evidence/2026-09-16-census/selfhost-cell-loop/classes.md` shows
`information=False`), where reading B is the alternative reading that
would make it True on both: "a named parameter with no stated domain is an
omission, making `information` True on both and cell-loop a task-defect
task" (classes-summary.md, that entry). Neither reading changes a primary
class, and this page takes no position between them; it only reports that
the reservation exists. `selfhost-speed-probe`'s
17 hidden tests sit inside the 15-20 band despite `speed-probe` itself
being dropped from the census's large-tier ceiling set for a named prompt
defect (README, "Deviations, stated": cut prompt carries an attended
checklist and a preflight a cell cannot run, "never claimed against"). No
combination of the two measured columns in this table separates the
medium tier from the large tier.

Which tier `selfhost-preflight-quiet` actually belongs to is not decided
here. Per design spec section 5, "What it decides": that is what the
task's own admission night (night 3) decides, from its cells' finishing
shape — a finishing shape puts the medium tier three wide; comfortable
passes make it a floor task and the tier stays two wide; no pass state
means the size class was misjudged and the task is re-scoped, not claimed
against.
