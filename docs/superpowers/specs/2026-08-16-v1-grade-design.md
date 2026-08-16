# V1 — It installs and grades: design spec

**Phase:** V1 (`ROADMAP.md:38`). **Date:** 2026-08-16. **Status:** approved
design; implementation plan pending.

## Why this phase

V1 is the first product phase: `satyrn-evals grade TASK PATCH` applies a
patch to a bundled task's base state, runs the task's oracle, and records a
verdict — offline and deterministic. It proves the grading seam the rest of
the roadmap (capture, attempt, the diagnostic loop) builds on.

Settled and not reopened here: the phase list, the diagnosis-before-claims
split, and the two selection rules as concepts (`BRIEF.md`; cited in
`docs/superpowers/research/2026-08-16-harvest-index.md`). This spec only
fixes how those rules apply to V1's artifacts.

## Done-when

The evidence floor (`BRIEF.md` rule 2): the grader has accepted the bundled
task's **known-good** patch and rejected its **known-broken** one, each
asserted in the integration tier by naming the fixture. The default tier is
green with the spawn tripwire active; `ruff` and `pyrefly` are clean.

## Decisions from the brainstorm

1. **Baseline probe is a selection constraint, not a V1 deliverable.** The
   probe (baseline attempt command at n=4–6, recorded once as a task
   property) requires the attempt loop, which lands in V3/V4. V1 therefore
   picks its bundled task under the grader-fixture rule (offline,
   deterministic, no network, no third-party dependencies) and under the
   constraint that the task not be degenerate — so a baseline *could* move
   when the probe lands. No probe is recorded in V1.
2. **The verdict comes from a custom pytest hook file, not stdout, not an
   exit code** (`BRIEF.md` rule 4; predecessor graders were defeated by
   `addopts = --collect-only` and import-time `os._exit(0)`).
3. **The spawn tripwire is a CPython audit hook** (`sys.addaudithook`
   raising on `subprocess.Popen`, `os.exec*`, `os.system`, `posix_spawn`),
   not monkeypatching — it covers every spawn path and cannot be bypassed by
   a held reference. The integration tier opts out via its marker.

## CLI surface

```
satyrn-evals grade TASK PATCH [--receipt PATH]
```

- `TASK` — name of a bundled task shipping in the package
  (`src/satyrn_evals/tasks/<name>/`).
- `PATCH` — path to a unified-diff file.
- `--receipt PATH` — where the verdict receipt is written; default
  `receipt.json` in the current directory.
- `satyrn-evals --help`, `satyrn-evals grade --help` — argparse, stdlib
  only (a CLI framework earns its place only after several commands share a
  shape). Console script `satyrn-evals = satyrn_evals.cli:main` in
  `pyproject.toml`.

## Exit codes

| Code | Meaning | Receipt |
|------|---------|---------|
| 0 | Grading completed | Written; verdict `pass` or `fail` |
| 2 | Usage error (unknown task, unreadable patch, bad args) | None |
| 3 | Operational failure (patch won't apply, oracle can't run, evidence unusable) | Written; verdict `unavailable` and a reason |

The verdict never comes from an exit code (`BRIEF.md` rule 4). No error
path emits a verdict — the harvest rule: a suspiciously clean result is an
instrument fault until checked; record `unavailable` with a distinct exit
code instead.

## Data shapes

**Task manifest** (`tasks/<name>/manifest.json`):
- `name`
- `contract` — one-sentence task statement
- `oracle` — command list run in the materialized workspace after patch
  application (V1's bundled task uses pytest)
- `expected_test_ids` — test IDs the oracle must execute
- `source_paths` — allowlist the patch may touch; tests and manifest stay
  at base (harvest: extra or changed tests broke an executed-vs-expected
  count and a false 0/4)
- `fixtures` — `known_good` and `known_broken` patch paths (the evidence
  floor, asserted by name)

**Patch** — unified diff, must apply cleanly to base state and touch only
`source_paths`.

**Hook result JSON** — written by the oracle hook (below) to a unique
per-run path passed in an environment variable:
- `executed_test_ids`
- `outcomes` — per test ID: `passed` | `failed` | `error` | `skipped`
- `counts` — total and per outcome

**Receipt JSON** — written by `grade`:
- `task`, `patch_digest` (sha256 of the patch file)
- `verdict` — `pass` | `fail` | `unavailable`
- `reason` — evidence summary; for `unavailable`, the cause
- `evidence` — the hook result JSON verbatim

## Verdict mechanism

`grade` copies the task's base state to a temp directory (pure
`shutil.copytree`), applies the patch with `git apply` (real subprocess —
integration tier), then runs the oracle with the hook plugin loaded with
`-p` from installed code, *outside* the workspace the patch could touch.
The plugin's `pytest_sessionfinish` writes the hook result JSON to the path
from the environment variable — a path the patch cannot predict, so it
cannot forge the file. The harness records the run start time and rejects a
stale file (harvest: "the runner watched a hardcoded file").

Verdict from the hook JSON alone:
- file missing, empty, stale, or unparseable → `unavailable`
- executed set ≠ expected set → `unavailable` (the executed-vs-expected
  guard)
- any `skipped` → `unavailable` (the suite did not fully run)
- any `failed` or `error` → `fail`
- all `passed` and nothing else → `pass`

## Bundled task

A small pure-Python task, chosen at plan time under the selection
constraints above: a buggy function with base tests that fail at base; the
known-good patch fixes it; the known-broken patch does not. No network, no
third-party dependencies in the oracle.

## Test layout

**Default tier** — no model, no network, no subprocess (enforced by the
tripwire):
- manifest loading — valid parses, malformed rejected (sibling tests)
- patch parsing and allowlist check — valid diff accepted, garbage and
  test-touching diffs rejected (siblings)
- verdict computation — every branch above with its sibling
- receipt round-trip
- tripwire — audit hook installed in `tests/conftest.py`; planted test
  attempts a spawn and asserts it raises. Weakening or removing the hook
  fails the build (`CLAUDE.md:28`).

**Integration tier** (`pytest -m integration`, not run in CI):
- real `git apply`, real oracle subprocess
- known-good patch → verdict `pass`, receipt written (fixture named)
- known-broken patch → verdict `fail`, receipt written (fixture named)
- exit codes: 0 with pass/fail receipt, 3 with `unavailable` receipt, 2 on
  usage errors

## File layout

```
src/satyrn_evals/
  cli.py          argparse, grade command, exit codes
  manifest.py     load/validate manifest
  patch.py        parse unified diff, allowlist check
  grade.py        orchestrate: materialize, apply, run oracle, receipt
  verdict.py      verdict from hook JSON + expected IDs
  receipt.py      write/read receipt
  oracle_hook.py  pytest plugin; sessionfinish writes hook JSON
  tasks/<name>/   manifest.json, base/, known-good.patch, known-broken.patch
tests/
  conftest.py     audit hook + integration opt-out
  test_manifest.py test_patch.py test_verdict.py test_receipt.py
  test_tripwire.py
  integration/test_grade.py
```

## Concept budget

Defined now: **task** (bundled manifest + base state + fixtures), **oracle**
(the manifest's command whose hook result is the only verdict evidence),
**verdict** (pass/fail/unavailable in a receipt). Defined by later phases:
**preservation**, **attempt command**, **baseline probe** (a recorded
property, not a V1 artifact).

## Out of scope (deferred, with the phase that reopens each)

- capture by revert — V2
- attempt command, patch/transcript persistence — V3
- baseline probe recording — with the attempt loop, V3/V4
- the claims layer — later, with a consumer
- wall-clock comparisons — never (`BRIEF.md`; summaries use counts)
