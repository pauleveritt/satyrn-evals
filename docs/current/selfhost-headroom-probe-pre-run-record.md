# Pre-run record — self-hosted headroom probe, Baseline only, `n = 12`

**Written 2026-09-14, before any inference.** Every value below is frozen at
the moment of writing. Authorized by
`docs/current/selfhost-headroom-probe-brief.md` (Fable, 2026-09-14). This
record fixes that brief's concrete values; it adds no question, no cell and
no arm.

**Blocking finding, read first.** `selfhost-run-record-gate` does **not**
qualify (see "Task qualification" below): both `known-good.patch` and
`known-broken.patch` grade `unavailable` ("executed 0"), for a harness reason
unrelated to either fixture's correctness. Cells R1–R4 in the schedule below
are therefore **not interpretable** under the current toolchain. This record
is written anyway, per the brief's sequence, so the controller and reviewer
have the full picture before deciding whether to run G/D cells only, hold
the whole batch, or pursue a fix to the harness (out of this probe's scope).

## The question, and the decision rule (verbatim from the brief)

**Question.** For each of the three tasks, how many of four Baseline cells
on Ornith 1.5 9B fail?

**A cell fails** when `receipt.json` `verdict` is not `pass` **or**
`attempt.json` `code` is not `OK`, read from the retained attempt directory.
A `MODEL_ERROR` (5xx, out of memory) is infrastructure: the cell is
**unscored**, diagnosed, recorded, and not re-run; denominators count scored
cells only.

**Decision rule.** A task has **headroom** if **2 or more of its 4 scored
cells fail**. Report per task. Then:

- If one or more tasks has headroom, the self-hosted generator enters the
  release-one design as a workload source alongside `depth-3` at `R1`, and
  the task(s) with headroom are named as candidates. Nothing is designed
  toward them here.
- If none has headroom, say so plainly: the self-hosted shape at this size
  is inside Ornith's reach, and the design keeps `depth-3` at `R1` as its one
  ceiling. Name, without running, what a harder self-hosted task would be
  (Task 9's review script with its three reviewer-found defects; the Task 10
  guard from scratch with its 70-case suite).

**Also record, per cell, as measures.** Wall clock (launcher `run.log`);
turns (`turn_start`); tool calls (`tool_execution_start`, one per call);
input and output tokens (`scripts/usage_totals.py <transcript>`); public-suite
runs before the last mutation; and the outcome code. These are the budget
columns every later comparison needs.

**Diagnostics, kept apart from the measures.** Two shapes the ceiling probe
saw, counted here but not in the rule: (a) **oracle hunting** — any `bash`
command whose text searches outside the workspace root (`find /`, `locate`,
`grep -r` with an absolute path above the workspace, `ls` of a parent
directory); (b) same-file mutation churn (`edit`+`write` per target path) and
failed tool results. Carry the recompute script. State that these did not
enter the rule.

**Not asked.** Comparison with any other model or arm; any Engine arm; any
Fisher test or interval; why Ornith fails where it fails. Twelve cells
support per-task presence/absence of headroom and nothing finer.

## Frozen conditions (verbatim from the brief)

| Field | Value |
|---|---|
| Model | `omlx/Ornith-1.5-9B-MLX-8bit` at `127.0.0.1:8001` — verify with a live completion, never `/v1/models`; if any transcript's `message.model` differs, **stop and report, do not substitute** |
| Inference | the model's own settings from `arms/baseline-ornith15-9b.json`; record, do not normalise |
| Arm | Baseline only, `satyrn-evals-attempt-pi`, tools `read,bash,edit,write`, pi `0.85.1` |
| Repeat limit | **off**, as in both prior Ornith probes |
| Launch | `satyrn-evals run <task> --n 1 --rung R1 --output <cell> --timeout 1200 --attempt-timeout 1500 -- satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit --tools read,bash,edit,write` — the command budget is 1200 s, not the ceiling probe's 900 s, because the workspace's own public suite takes about 30 s per run on this machine and a real task runs it several times; the result states this budget beside every count |
| Order | G1 R1 D1 G2 R2 D2 G3 R3 D3 G4 R4 D4 (guard, run-record, docs-linter), serial |
| Output root | `~/satyrn-smokes/2026-09-14-selfhost-headroom-probe/` (must not exist) |
| Wall-clock stop | 3 h from the first cell; unreached cells reported as not-run |

**Inference settings, verbatim from `arms/baseline-ornith15-9b.json`** (not
normalised): context window 262,144; max tokens 32,000; temperature 0.6;
top_p 0.95; top_k 20; min_p 0.0; presence_penalty 0.0; repetition_penalty
1.0; compaction enabled, 16,384 reserve; `declares_reasoning: true`.
`pins.pi` = `0.85.1`.

## Task qualification, before any cell

Qualified with `satyrn-evals grade <task> <patch> --receipt <path>` against
both fixtures, and `resolve_task` for each name.

| Task | `resolve_task` | known-good verdict | known-broken verdict | Qualifies? |
|---|---|---|---|---|
| `selfhost-guard-prefixes` | resolves | `pass` (83/83 expected ids executed and passed) | `fail` (8 of 83 fail — the 8 new wrapper-prefix cases; the other 75 pass, including all lookalike-allow cases) | **yes** |
| `selfhost-docs-linter` | resolves | `pass` (15/15) | `fail` (all 15 fail on assertion/type errors against a `None`-returning stub; zero collection errors) | **yes** |
| `selfhost-run-record-gate` | resolves | `unavailable`, `executed tests mismatch expected ... executed 0` | `unavailable`, same reason, same message | **no — see below** |

**Why `selfhost-run-record-gate` does not qualify.** `src/satyrn_evals/grade.py`'s
`_hook_import_path()` builds a PYTHONPATH shim containing exactly one
package, `satyrn_evals`, symlinked to `Path(satyrn_evals.__file__).resolve().parent`
— i.e. the **outer, currently-running** package (this worktree's real
`src/satyrn_evals`), not the materialized grading workspace's own copy. That
shim sits ahead of the fresh `uv sync --locked` environment's site-packages
on `PYTHONPATH`, so any hidden test that does `import satyrn_evals.<anything>`
binds to the outer package regardless of what the candidate patch adds inside
the workspace. This task's HIDDEN content (`tests/test_run_record.py` at
`b253c99`, fixed verbatim by the brief) imports
`from satyrn_evals.run_record import RunRecord, RunRecordError, gate, load_run_record`
and `from satyrn_evals.cli import main` — both inside the shadowed namespace.
The outer package has no `run_record` module (it is not implemented in this
repository outside the task fixtures), so collection fails with
`ModuleNotFoundError: No module named 'satyrn_evals.run_record'` regardless
of the patch. Reproduced three ways: (1) `satyrn-evals grade` against both
fixtures, twice each, identical `unavailable`/`executed 0` result; (2) a
manual reproduction outside the CLI (materialize `base/`, apply
`known-good.patch`, overlay the hidden test, `uv sync --locked`, run
`python -m pytest -p satyrn_evals.oracle_hook test_run_record.py -q` with the
exact env the grader builds) — same `ModuleNotFoundError`; (3) inspection of
`_hook_import_path`'s docstring, which states the intent ("Nothing else is
on PYTHONPATH, so a dependency-bearing oracle resolves every task dependency
from its own locked environment instead of from evals' install location") —
an intent that only holds when the task's own dependency does **not** share
a top-level package name with the harness. This is a structural property of
the current oracle isolation design, triggered specifically because this
task's fix target *is* the harness's own package — the exact hazard the
brief names ("The workspace is the harness's own package") in a form the
brief's own hazard writeup did not anticipate (it anticipated the model
forging a result by editing `oracle_hook`, not the harness's own anti-forgery
shim making the task ungradeable). Per "no instrument change larger than
reading the evidence; record debt instead," `grade.py` is not touched here.
The task directory, base, overlay and fixtures are still built and committed
in full, because the brief's exclusion-list and prompt-derivation work is
independent of this defect and may be reusable if the isolation mechanism is
later adjusted (Phase 2 concern, not this probe's).

**Consequence for this run.** Only `selfhost-guard-prefixes` and
`selfhost-docs-linter` produce interpretable cells. The schedule below still
lists all twelve cells in the brief's fixed order, because dropping or
reordering cells is a decision for the controller/maintainer, not something
this record makes unilaterally; but R1–R4 should not be launched, or if
launched, their `unavailable` outcomes must not be read as evidence about
Ornith's headroom on that task shape — they are evidence about the harness
only.

## The three prompts (rung `R1`), their digests, and the exclusion list

Each prompt is: the task title, the **Files** list, the **Interfaces →
Produces** block verbatim, and the prose of each step (plus, for the two
plan-derived tasks, the intervening rules/schema prose that a step
references) with every fenced code block removed. Where the original prose
named the hidden test file by its literal path, that mention was paraphrased
to "its test module" — required by `manifest.py`'s
`_assert_contract_names_no_overlay` check, which refuses a hidden task whose
contract names a grader-only path; both plan-derived prompts originally named
their hidden file and were rewritten before being accepted. No prompt
contains a fenced code block.

**Exclusion list applied to every `base/`:** `docs/superpowers/plans/**`,
`docs/superpowers/specs/**`, `.claude/**`, `.github/**`, `PROVENANCE.md`, and
the task's own HIDDEN test file. Verified by `find`/`grep` after each `base/`
was built: no `.claude`, `.github`, `PROVENANCE.md`, `docs/superpowers/plans`
or `docs/superpowers/specs` directory exists under any `base/`; no `base/`
contains its own hidden test file by name; `grep -rl` for the hidden test
function names and for the fix-wave/plan prose text returns nothing under
any `base/`.

| Task | Prompt sha256 |
|---|---|
| `selfhost-guard-prefixes` | `00e0b6a3a0ce8b043b1f4f648a92d35d334a78f10b697da5d2bf10aaff21857f` |
| `selfhost-run-record-gate` | `eaf723aab37affb654c349a23b5983a0b0df4407cc8c2427917efdf3bddadef8` |
| `selfhost-docs-linter` | `c7fa294ca5e9ffee7d2a1466e296aea03e82cc9a1ebef63d8affd29f2cc5a0a9` |

Digest is `sha256` of the exact prompt string stored in each task's
`manifest.json` `contract` / `contracts.R1` field (identical strings), no
trailing newline.

## Task-tree digests

The digest is the same walk the ceiling and pathology probes' result
documents use:

    uv run python -c "
    import hashlib, sys
    from pathlib import Path
    d = Path('src/satyrn_evals/tasks') / sys.argv[1]
    h = hashlib.sha256()
    for p in sorted(d.rglob('*')):
        if p.is_file():
            h.update(p.relative_to(d).as_posix().encode()); h.update(p.read_bytes())
    print(h.hexdigest())
    " <task>

The Baseline `run` command carries **no** `--task-tree-sha256` flag, so for
this run the digest is a **recorded identity, not a command-enforced gate**.

| Task | Task tree sha256 |
|---|---|
| `selfhost-guard-prefixes` | `a84f6597407c49e805df1d28fa61ad3e0258f142d6391916bc1da721de4de700` |
| `selfhost-run-record-gate` | `5900b4993e79a38c2e2a9d217ab4a0cbc9b6b8a3ded4cd02029a51b13fcd6640` |
| `selfhost-docs-linter` | `19d31af1b3bca2f923e9332140acdd334525e355f15a861e191bfd7b4ec4a013` |

## Evals revision

| Field | Value |
|---|---|
| Base | `main` at `7c7b188` (the fat tree with both prior probes merged) |
| Worktree | `.claude/worktrees/selfhost-headroom-probe`, branch `worktree-selfhost-headroom-probe` |
| Evals revision for the run | `b012ab5c1be2dcf8fc182b6d032bb2e4ba712877` ("Build and qualify the three self-hosted headroom-probe tasks"), this record's own commit is on top of it |
| pi version | `0.85.1` |

## Exact per-cell commands

**`selfhost-guard-prefixes` (G) — `<cell-dir>` per cell:**

    uv run satyrn-evals run selfhost-guard-prefixes --n 1 --rung R1 \
      --output <cell-dir> --timeout 1200 --attempt-timeout 1500 -- \
      satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

**`selfhost-run-record-gate` (R) — `<cell-dir>` per cell — see blocking
finding above; not interpretable under the current toolchain:**

    uv run satyrn-evals run selfhost-run-record-gate --n 1 --rung R1 \
      --output <cell-dir> --timeout 1200 --attempt-timeout 1500 -- \
      satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

**`selfhost-docs-linter` (D) — `<cell-dir>` per cell:**

    uv run satyrn-evals run selfhost-docs-linter --n 1 --rung R1 \
      --output <cell-dir> --timeout 1200 --attempt-timeout 1500 -- \
      satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

All three run under `uv run` with the current working directory set to this
worktree. No command passes `--max-repeated-calls`: the repeat limit is off,
by the frozen condition above.

## The cells, in execution order

| Cell | Task | Rung |
|---|---|---|
| `cell-01-G1` | `selfhost-guard-prefixes` | R1 |
| `cell-02-R1` | `selfhost-run-record-gate` | R1 |
| `cell-03-D1` | `selfhost-docs-linter` | R1 |
| `cell-04-G2` | `selfhost-guard-prefixes` | R1 |
| `cell-05-R2` | `selfhost-run-record-gate` | R1 |
| `cell-06-D2` | `selfhost-docs-linter` | R1 |
| `cell-07-G3` | `selfhost-guard-prefixes` | R1 |
| `cell-08-R3` | `selfhost-run-record-gate` | R1 |
| `cell-09-D3` | `selfhost-docs-linter` | R1 |
| `cell-10-G4` | `selfhost-guard-prefixes` | R1 |
| `cell-11-R4` | `selfhost-run-record-gate` | R1 |
| `cell-12-D4` | `selfhost-docs-linter` | R1 |

Sequential, non-overlapping, one at a time, each into its own directory under
the output root. The launcher writes `schedule.json` before the first cell
and a per-cell log with start/end timestamps and elapsed seconds. No cell is
added, dropped or reordered after this record is committed. `n = 12` is
frozen: no extension, re-run or replacement for any result.

## Measures and their recompute commands

Same recompute commands as the ceiling probe's record: wall clock from
`run.log`; turns from `turn_start` events; tool calls from
`tool_execution_start` events; tokens from `uv run python scripts/usage_totals.py <transcript>`.

## Diagnostics (kept apart from the measures)

Per cell: (a) oracle hunting — any `bash` command whose text searches
outside the workspace root; (b) same-file mutation churn (`edit`+`write`
per target path) and failed tool results. Same recompute walk as the
ceiling probe's record (`tool_execution_start`/`tool_execution_end`
events). These counts do not enter the decision rule.

## Model identity, verified before writing this

A live one-word completion was sent to
`127.0.0.1:8001/v1/chat/completions` with request
`"model": "Ornith-1.5-9B-MLX-8bit"`. It returned:

    {"id":"chatcmpl-8c0c952f","model":"Ornith-1.5-9B-MLX-8bit",
     "choices":[{"message":{"role":"assistant",
       "content":"The user asked me to reply with OK"},"finish_reason":"length"}], ...}

The response's own `model` field is `Ornith-1.5-9B-MLX-8bit`. **The model is
loadable.** Identity is re-read from each cell's own transcript
(`message.model`) before any cell is counted; a wrong observed
`message.model` is an infrastructure stop, per the brief's frozen
conditions — no substitution.

## Preflight performed before this record

| Check | Result |
|---|---|
| Working tree clean, probe worktree | `git status --porcelain` empty at `b012ab5` on `worktree-selfhost-headroom-probe` |
| All three task-tree digests recomputed | match the values above |
| `satyrn-evals-attempt-pi` resolves | yes — console script at this worktree's `.venv/bin/satyrn-evals-attempt-pi`; invoking with an unknown flag raises `AdapterError` from `attempt_pi.py` (no import/entry-point failure) |
| One live completion from the model | returned text, observed `model` = `Ornith-1.5-9B-MLX-8bit` (above) |
| No measurement-shaped Pi process | `ps aux \| grep -i "satyrn-evals-attempt-pi\|satyrn-evals-session-pi\|satyrn-evals run\|satyrn-evals session"` (minus the grep itself) returned empty |
| Output root absent | `~/satyrn-smokes/2026-09-14-selfhost-headroom-probe/` does not exist |
| `pi` version | `0.85.1` (per `arms/baseline-ornith15-9b.json` `pins.pi`) |
| Arm inference settings recorded verbatim | from `arms/baseline-ornith15-9b.json`, reproduced in Frozen conditions above |
| Offline public-suite timing | scratch materialization (`rsync` of the worktree, `.git` excluded, into a fresh directory), `uv sync --frozen` from local cache, then `UV_OFFLINE=1` plus an unroutable proxy (`http(s)_proxy=http://127.0.0.1:1`) to force any network attempt to fail fast, then `uv run --offline python -m pytest -q`: **2019 passed, 420 deselected in 29.74s**, no network error (the deps resolved entirely from the local `uv` cache) |
| Default tier, this worktree | `uv run pytest -q` → **2019 passed, 420 deselected in 29.62s** (includes the new `tests/test_writable_paths_declaration.py` rows for the three tasks; see the qualification commit) |

## Trust-boundary limit

The workspace is the harness's own package. For `selfhost-guard-prefixes`
and `selfhost-docs-linter`, the oracle's `PYTHONPATH` shim
(`_hook_import_path`) only ever needs to expose `satyrn_evals.oracle_hook`
itself; the candidate's target files (`tools/hooks/guard.py`,
`tools/lint_docs.py`) live outside the `satyrn_evals` package, so the shim
does not shadow them, and a model that edited `oracle_hook.py` inside its own
workspace copy could still not forge a result, because the shim always binds
`satyrn_evals` (and therefore `satyrn_evals.oracle_hook`) to the **outer**,
real package, never the workspace's copy — the opposite exposure from what
the brief's hazard section anticipated, and the safer direction. `source_paths`
excludes `src/satyrn_evals/oracle_hook.py` from every task's allowlist
regardless, so an edit there is also a counted scope violation, belt and
braces. For `selfhost-run-record-gate` the same shim is why the task cannot
be graded at all (see "Task qualification" above) — the one task among the
three whose fix target sits inside the shadowed namespace.

## Contamination check

`grader_content_in_patch` / `grader_name_in_payload` ran as part of every
`satyrn-evals grade` call above (the auto-overlay path in `grade.py` always
runs `contamination.scan_patch` for a hidden-oracle task). Result for all
three tasks, both fixtures: no contamination finding — `known-good.patch`
and `known-broken.patch` for `selfhost-guard-prefixes` and
`selfhost-docs-linter` do not name or embed overlay content; the same is
true of `selfhost-run-record-gate`'s fixtures, confirmed by the same scan
running (and finding nothing) inside the `unavailable`-verdict receipts.

## Review

Sonnet implements; Opus reviews this pre-run record before cell 1 and the
result before it is called accepted, per the brief. The review checks:
fixtures proven in both directions (two of three; `selfhost-run-record-gate`
is not, with evidence above); the plan is absent from every `base/`; the
rule applied as written; every count carries its recompute; diagnostics
labelled; no sentence compares Ornith with another model or one arm with
another. **No Fable review unless the maintainer asks.**

## Loop rules (verbatim from the brief)

- Only an **established infrastructure failure** stops launches. A fail, a
  timeout, a refusal, a collection error or a scope violation is the
  observation; it is kept and counted, never replaced.
- `n = 12` is frozen. No extension, re-run or replacement for any result.
- No other inference on this machine while the launcher runs.

## Launcher

Committed at `tools/launch-selfhost-headroom-probe.sh` on this branch
(executable, version controlled, adapted from the retained ceiling-probe
`launch.sh` with the three tasks substituted). The controller runs it, from
this worktree:

    cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals/.claude/worktrees/selfhost-headroom-probe
    nohup tools/launch-selfhost-headroom-probe.sh \
      > ~/satyrn-smokes/2026-09-14-selfhost-headroom-probe.launcher.log 2>&1 &

It is not run as part of preparing this record. Given the blocking finding
above, the controller should decide whether to run all twelve cells, run
only the eight `G`/`D` cells, or hold the run until
`selfhost-run-record-gate`'s qualification defect is resolved, before
starting it.

## Retention

Every cell keeps its `attempt.json`, patch(es), receipts and transcript
under its own cell directory (`<output-root>/cell-NN-XY/`). Nothing is
discarded, including cells that stop early. The output root itself keeps the
launcher's own copy (`launch.sh`), the batch `schedule.json`, the launcher
log (`run.log`, with per-cell start/end timestamps and elapsed seconds), and
— one level up, beside each cell directory rather than inside it — that
cell's captured stdout, `<output-root>/cell-NN-XY.stdout.log`.

## Budget grant

**Granted 2026-09-14 by the maintainer, in session** ("Granted, exclusive
GPU, dispatch it to an Opus controller"): `n = 12` cells under the frozen
conditions above, on **exclusive GPU** for the duration of the run,
wall-clock stop 3 h. Cell 1 may start once the three tasks are qualified in
both directions and this record is committed and reviewed — **two of three
are; the third is documented above as not qualifiable, and the controller's
decision on how to proceed is requested, not assumed.**
