# Pre-registered post-hoc read: four parked literals, `selfhost-preflight-quiet`

Written 2026-09-18, **before** night 3 runs, under the maintainer's
2026-09-18 ruling that parked two whole-path-review findings against the
frozen `selfhost-preflight-quiet` cut — I2 (the `ps`-line split rule) and
three further literals P1/P3/P4 — as *disclosed and instrumented*, not
fixed, because fixing any of them means editing the heading document,
which would move `base`, orphan `good`, and re-open the R0 §1.2
certificate. The disclosure, the re-measured evidence (two 20-passed runs
and the `busy_processes(...) -> []` consequence), and the four literals'
full description live at
`evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/README.md`;
this page is that disclosure's pre-registered counterpart — the read that
will actually run once night 3's cells exist, committed before any of them
do.

## What is read, and from what

For each retained night-3 cell, from that cell's **harvested patch** —
never from stdout, never from an exit status; this repository grades from
hook-written evidence only — four boolean columns, one per parked literal:

| column | question |
|---|---|
| `maxsplit` | does the cell's `busy_processes` split each `ps` line into at most three fields (`split(maxsplit=2)` or equivalent), rather than a bare `split()`? |
| `one_decimal` | are the `load` and `decode` messages formatted to one decimal place (`:.1f` or equivalent), rather than a bare `f"{x}"`? |
| `inputs_keys` | does `as_dict()["inputs"]` carry exactly the specified key set (`load`, `busy`, `decode`, `floor_tok_s`, `model`, `last`) and no more? |
| `cli_last` | is the `last` passed to `certificate` the parsed `--last` value, rather than a hardcoded `DEFAULT_LAST`? |

Each is read by inspecting the patch's own diff of `scripts/preflight_quiet.py`
(source text, not behavior inferred from a run) for the pattern named in
its row above.

## Denominator and population

**Every retained night-3 cell for `selfhost-preflight-quiet`** — all six
Baseline cells the night runs, per `records/2026-09-18-census3-selfhost-preflight-quiet.json`
(a later commit in this task creates that record). This explicitly
**includes cells that did not reach a pass state**: a cell's harvested
patch exists regardless of its verdict (a torn-down worktree's cumulative
patch, or `tripped.diff` for a `BUDGET_EXCEEDED` cell), and all four
columns are source-pattern reads over that patch, not reads of a passing
run. A cell with no patch at all (no source touched) is recorded as `n/a`
in all four columns, not silently dropped from the denominator.

## The reporting rule — never changes a verdict

**Each column is reported beside the cell's classification, as a count out
of its stated denominator (six), and is never used to change a verdict, a
pass count, or a classification.** The night's verdict comes from the
hidden suite via the receipt, exactly as it does for the other five census
tasks, and nothing in this read may alter it. This is the load-bearing
sentence of this page: the four columns are a disclosure about what the
*grading suite* does not check, not a re-grading of the cells it graded.

## What each column can and cannot support

A `maxsplit` miss means that cell's check would, on a real snapshot with a
space in a busy process's `comm` (routine on macOS, and exactly the shape
of the prompt's own `/Applications/oMLX.app/` entry in `IGNORE_PREFIXES`),
declare a loud machine quiet — the one failure mode the task exists to
prevent. The measured direction (`evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/README.md`)
is leniency, so a `maxsplit` miss rate here is, if anything, an
under-count of how many built checks would fail this way in the field. It
does **not** make the missing cell's grade wrong: the grade is what the
developer's tests said, and the developer's tests do not grade this rule.
The same reasoning holds for `one_decimal`, `inputs_keys` and `cli_last`:
each names a real gap between the prompt's prose and what the suite
checks, none of them a defect in the cell's grade.

## The recompute command

Night 3's retained cells live under
`$HOME/satyrn-runs/2026-09-18-census3-selfhost-preflight-quiet/`; the
frozen record this read is checked against is
`records/2026-09-18-census3-selfhost-preflight-quiet.json` (created by a
later commit in this same task, not this one). `evidence/2026-09-16-census/classify.py`
shows the shape of how this repository reads a night — `cells()` from
`launch.json` and the record, one harvested patch per finished slot,
read-only on `~/satyrn-runs`. The read for this page is a short script, to
be committed alongside the record, or — if not committed — this documented
command, complete enough to run by hand once both exist:

```bash
uv run --project . python - <<'PY'
import json, pathlib, re
night = pathlib.Path.home() / "satyrn-runs" / "2026-09-18-census3-selfhost-preflight-quiet"
record = pathlib.Path("records/2026-09-18-census3-selfhost-preflight-quiet.json")
# uses satyrn_evals.session_patch.build_cumulative_patch per cell, as
# evidence/2026-09-16-census/classify.py:cells() does, to get each
# retained cell's harvested patch, then greps that patch's
# scripts/preflight_quiet.py hunk for the four patterns above.
PY
```

No model, no network, no GPU step: the read is a source-text grep over
already-harvested patches on disk.

## Where night 3's classifier output lands

`evidence/2026-09-18-census-3/` is also where the night's own classifier
run will write its per-task output (`--out evidence/2026-09-18-census-3`,
per `evidence/2026-09-16-census/classify.py`'s `--out` argument), producing
`<out>/selfhost-preflight-quiet/{cells.json,table.md,classes.md}`
alongside this page. The classifier's `night` key refuses to overwrite
another night's directory (`_overwrite_refusal`), so a second, unrelated
night cannot silently clobber this one's output here.

## Provenance

Written 2026-09-18, before night 3 runs, under the maintainer's 2026-09-18
ruling parking I2 and P1/P3/P4 as disclose-and-instrument rather than fix.
Cross-references
`evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/README.md`,
which carries the disclosure and the re-measured evidence this page
counts against retained cells.
