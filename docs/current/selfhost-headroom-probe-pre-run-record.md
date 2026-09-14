# Pre-run record — self-hosted headroom probe, Baseline only, `n = 12`

**Written 2026-09-14, before any inference.** Every value below is frozen at
the moment of writing. Authorized by
`docs/current/selfhost-headroom-probe-brief.md` (Fable, 2026-09-14). This
record fixes that brief's concrete values; it adds no question, no cell and
no arm.

**Fix-round update, read first.** An earlier draft of this record reported
`selfhost-run-record-gate` as unqualifiable and two of the R1 prompts as
under-specified relative to their hidden suites. Both are fixed below: (1)
`selfhost-run-record-gate`'s `manifest.json` `oracle` now reads
`env PYTHONPATH=src python -m pytest -p satyrn_evals.oracle_hook`, which
makes it gradeable in both directions (see "Task qualification"); (2)
`selfhost-docs-linter` and `selfhost-run-record-gate`'s `contracts.R1` were
amended to disclose the exact literal message formats and skip-list
semantics their hidden suites assert on — text the model otherwise had no
way to derive — following the `agentclinic-repair-depth-3` precedent of
disclosing assertion text at `R1` (see "The three prompts" below for the
full per-id answerability check). The controller reviewed both fixes and
confirmed `n = 12` stands across all three tasks. `selfhost-guard-prefixes`
was not touched in the fix round — its hidden suite asserts only
`decide(...) is None` / `is not None`, already answerable from its original
prompt.

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
| `selfhost-run-record-gate` | resolves | `pass` (20/20) | `fail` (18 of 20 fail against a `None`-returning/no-op stub; 2 pass trivially — `test_run_record_error_is_a_usage_error` and `test_batch_allows_twelve_and_twelve_hours`, both satisfiable by a no-op; zero collection errors) | **yes** |

**`selfhost-run-record-gate` initially did not qualify; fixed by changing
`manifest.json`'s `oracle`.** `src/satyrn_evals/grade.py`'s
`_hook_import_path()` builds a PYTHONPATH shim containing exactly one
package, `satyrn_evals`, symlinked to `Path(satyrn_evals.__file__).resolve().parent`
— the **outer, currently-running** package (this worktree's real
`src/satyrn_evals`), not the materialized grading workspace's own copy. By
default that shim sits ahead of the fresh `uv sync --locked` environment's
site-packages on `PYTHONPATH`, so any hidden test that does
`import satyrn_evals.<anything>` binds to the outer package regardless of
what the candidate patch adds inside the workspace. This task's HIDDEN
content (`tests/test_run_record.py` at `b253c99`, fixed verbatim by the
brief) imports `from satyrn_evals.run_record import RunRecord,
RunRecordError, gate, load_run_record` and `from satyrn_evals.cli import
main` — both inside the shadowed namespace — so collection originally
failed with `ModuleNotFoundError: No module named 'satyrn_evals.run_record'`
regardless of the patch. **Fix:** `manifest.json`'s `oracle` is now
`["env", "PYTHONPATH=src", "python", "-m", "pytest", "-p",
"satyrn_evals.oracle_hook"]`. `env NAME=VALUE cmd` *replaces* (not
prepends) the named variable in `cmd`'s environment while passing the rest
through unchanged; with the oracle's cwd at the materialized workspace
root, `PYTHONPATH=src` resolves to that workspace's own `src/`, so
`satyrn_evals` (oracle plugin included) now binds to the workspace's own
package — the one the candidate patch actually modifies. This drops
`_hook_import_path`'s dependency-isolation intent for this one task only,
which is harmless here because the workspace's locked environment is
`satyrn-evals`'s own project (there is no third-party dependency to
isolate from). No other task's `oracle` field changed. `grade.py` itself
was **not** modified — only this one task's manifest — per "no instrument
change larger than reading the evidence."

**Why this does not reopen the forgery vector the brief's hazard section
warns about.** Replacing PYTHONPATH means `satyrn_evals.oracle_hook` now
resolves to the *workspace's own* copy for this task, which in isolation
would let a model edit `oracle_hook.py` inside its own patch to forge a
result. It cannot, because `src/satyrn_evals/oracle_hook.py` is not in this
task's `source_paths`, and `check_allowlist` (`patch.py:181-184`) runs
**before** the oracle is ever invoked: any patch touching a path outside
`source_paths` is rejected with `PatchRejected: patch touches non-source
path: <path>`, verdict `unavailable`, before `_run_oracle` executes.
Verified directly: a synthetic one-line patch to `oracle_hook.py`, graded
against `selfhost-run-record-gate`, returns exactly that — `unavailable`,
`"patch touches non-source path: src/satyrn_evals/oracle_hook.py"` — the
oracle process is never started. See "Trust-boundary limit" below for the
corrected general statement (this replaces the earlier draft's incorrect
claim that the shim *always* protects the outer package regardless of
`source_paths`).

**Consequence for this run.** All three tasks now qualify in both
directions; the controller confirmed `n = 12` stands across the fixed
twelve-cell schedule below. See "The three prompts" for the accompanying
fix to two of the three `contracts.R1` (message-format disclosure), made
in the same round and required for the same reason — a behaviourally
correct answer must actually be able to reach `pass`.

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
| `selfhost-guard-prefixes` | `00e0b6a3a0ce8b043b1f4f648a92d35d334a78f10b697da5d2bf10aaff21857f` (unchanged) |
| `selfhost-run-record-gate` | `d1ea88fd8d8fecb72d97da3fd47537c8594979526d13362886ada645e6dc8b50` (amended, see below) |
| `selfhost-docs-linter` | `c8b4cdfa0d2ff9e38d314bd66d34f266266ee0dfb03ea96616ff8cad89993286` (amended, see below) |

Digest is `sha256` of the exact prompt string stored in each task's
`manifest.json` `contract` / `contracts.R1` field (identical strings), no
trailing newline.

**Amendment (fix round): message-format disclosure.** A review found that
7 of `selfhost-docs-linter`'s 15 hidden ids and several of
`selfhost-run-record-gate`'s 20 assert exact literal strings — e.g.
`"ROADMAP.md: 151 lines > 150"`, `"docs/current: directory not permitted
under docs/"`, `"mode must be attended or batch"`, `"n has the wrong
type"` — that appear nowhere in the original prompt or in the visible
`base/`. Since `compute_verdict` fails the whole cell if any expected id
fails, a behaviourally perfect implementation of the *stated* rules would
still fail those specific ids on message wording alone, manufacturing
"headroom" before any inference ran. The two-directional qualification
could not catch this, because `known-good.patch` **is** the original
author's code and necessarily reproduces its own strings.

Both `contracts.R1` were amended to disclose the exact message formats,
the exception types, and (for the linter) the skip-list's existence and
root-relative semantics — never the implementation (no regex, no
traversal logic, no function bodies). This is not new information beyond
what `R1` already means in this fleet: `agentclinic-repair-depth-3`'s own
`contracts.R1` (`src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json`)
already discloses assertion text and failing test names ("the third fails
`assert None is not None`, and the fourth fails `assert 307 == 303`").
Disclosing exactly the strings and exception shapes a hidden suite checks,
without disclosing how to produce them, is the established `R1` contract
for this fleet, not a deviation from it — recorded here as a disclosed
correction rather than a silent one.

**Per-id answerability, re-checked after the amendment.** All 15
`selfhost-docs-linter` ids and all 20 `selfhost-run-record-gate` ids were
walked individually against the amended prompt:

- `selfhost-docs-linter`: the 8 boundary/behavior ids (clean tree; fence
  present and under cap; roadmap/result/spec at exactly the cap;
  twelve/thirteen results; `.gitkeep` excluded) were already answerable
  from the original Rules paragraph. The 7 exact-message ids (roadmap
  over cap; result over cap; missing fence; too many results; unlisted
  directory; trailing whitespace + blank EOF, both the message and their
  relative order within one file) are answerable from the new Message
  formats paragraph, which gives every format verbatim and states the
  within-file ordering (whitespace lines before the blank-EOF entry).
  `test_the_skip_list_is_relative_to_root_not_absolute` is answerable
  without a model ever writing a directory-name skip list at all — the
  test only requires that the tree walk uses each file's path relative to
  the root, never the absolute filesystem path, which the new paragraph
  states directly; a straightforward `Path`-relative implementation
  satisfies it whether or not it bothers to skip any named directories.
- `selfhost-run-record-gate`: 11 of the 20 ids need only a substring
  match on a field or mode name already named in the Interfaces/Gate
  rules/schema prose (`decision_rule`, `attended`, `batch`,
  `task_tree_sha256`, `previous_result`, `condition`, and the path in a
  parse-failure message) — already answerable pre-amendment. 4 ids need
  one of the two now-disclosed exact phrases (`not a JSON object`,
  `<field> has the wrong type`, `mode must be attended or batch`,
  `<field> is empty`). `test_run_record_error_is_a_usage_error` follows
  directly from the Interfaces block's "a `UsageError` subclass from
  `errors.py`". `test_launch_without_check_is_a_usage_error` (expects
  exit code 2) and `test_launch_check_accepts_a_good_record` follow from
  the Step 3/4 prose plus the visible `base/src/satyrn_evals/errors.py`,
  whose own docstring and `UsageError.exit_code = 2` are readable by the
  model without any prompt change (Step 3 already tells it to `grep` that
  file). No id was found unanswerable after the amendment.

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

Recomputed after the fix round (the two amended manifests change their
task's digest; `selfhost-guard-prefixes` is untouched):

| Task | Task tree sha256 |
|---|---|
| `selfhost-guard-prefixes` | `a84f6597407c49e805df1d28fa61ad3e0258f142d6391916bc1da721de4de700` (unchanged) |
| `selfhost-run-record-gate` | `f82d90d1e9cd7ee462223a8287dd58e6fb33efdd734eb393a3a2252f9289aaeb` |
| `selfhost-docs-linter` | `b4e966a2e5496ac3c41dc2d07307230cec209ccf83b267bdd96ab12fd49d0c31` |

## Evals revision

| Field | Value |
|---|---|
| Base | `main` at `7c7b188` (the fat tree with both prior probes merged) |
| Worktree | `.claude/worktrees/selfhost-headroom-probe`, branch `worktree-selfhost-headroom-probe` |
| Evals revision for the run | **this record's own commit on this branch** — the fix-round commit that amends `selfhost-run-record-gate`'s and `selfhost-docs-linter`'s manifests, this record, and the launcher; the launcher runs from whatever this branch's tip is when the controller starts it, and that must be this commit or later, not the earlier `b012ab5c1be2dcf8fc182b6d032bb2e4ba712877` ("Build and qualify the three self-hosted headroom-probe tasks"), which predates the qualification fixes |
| pi version | `0.85.1` |

## Exact per-cell commands

**`selfhost-guard-prefixes` (G) — `<cell-dir>` per cell:**

    uv run satyrn-evals run selfhost-guard-prefixes --n 1 --rung R1 \
      --output <cell-dir> --timeout 1200 --attempt-timeout 1500 -- \
      satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

**`selfhost-run-record-gate` (R) — `<cell-dir>` per cell:**

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

**Corrected in the fix round.** The brief's hazard sentence — "A model that
edits [`oracle_hook.py`] could forge a result; `source_paths` excludes it,
so an edit there is a scope violation, **counted not prevented**" — is
wrong in the safe direction. What actually happens, verified directly
(`patch.py:181–184`, `check_allowlist`/`within_source`): `grade()` parses
every path the candidate's patch touches and rejects the whole grade,
verdict `unavailable`, reason `"patch touches non-source path: <path>"`,
**before** `_run_oracle` is ever invoked, for any path outside the task's
`source_paths` — and `src/satyrn_evals/oracle_hook.py` is in no task's
`source_paths`. A synthetic one-line patch to `oracle_hook.py`, graded
against `selfhost-run-record-gate` (the task most exposed, see below),
confirms this: `unavailable`, `"patch touches non-source path:
src/satyrn_evals/oracle_hook.py"`, oracle never started. So an edit there
is **prevented**, not merely counted.

The workspace is still the harness's own package, and the two oracle
`PYTHONPATH` configurations across the three tasks differ in what they
expose, for the record: `selfhost-guard-prefixes` and
`selfhost-docs-linter` use the default shim
(`_hook_import_path`), which binds `satyrn_evals` (and so
`satyrn_evals.oracle_hook`) to the **outer**, real package regardless of
the workspace copy — irrelevant here since their candidate targets
(`tools/hooks/guard.py`, `tools/lint_docs.py`) live outside the
`satyrn_evals` package entirely. `selfhost-run-record-gate` instead runs
its oracle with `PYTHONPATH=src` (replacing the default shim; see "Task
qualification"), so `satyrn_evals.oracle_hook` there binds to the
**workspace's own** copy — the configuration the brief's hazard sentence
was written about — and the allowlist proof above is what makes that safe,
not the shim direction.

The residual, fleet-wide limit — identical to AgentClinic's `models.py` in
`agentclinic-repair-depth-3` — is narrower than "the oracle plugin can be
edited": it is that **candidate code the hidden suite imports and executes
inside the oracle process is, definitionally, in `source_paths`** (here,
`src/satyrn_evals/cli.py` for `selfhost-run-record-gate`, or `tools/hooks/
guard.py` / `tools/lint_docs.py` for the other two), so the oracle process
does run code the model wrote. That is not a defect; it is what "the model's
fix is graded" means for any task, self-hosted or not — the same trust
placed in AgentClinic's `models.py` inside its own oracle process. The
self-hosted shape does not widen this beyond the ordinary case; it only
makes it visible, because here the imported module happens to sit inside
`satyrn_evals` too.

## Contamination check

**Corrected in the fix round.** `grade()`'s auto-overlay path (the one
every call above used) runs only `contamination.scan_patch`, which
produces the `grader_content_in_patch` check; `grader_name_in_payload` is
produced by a different function, `scan_texts`, which is not called from
`grade.py` at all — it scans tool-call payload text during a live `run`/
attempt, not during grading. The earlier draft of this record wrongly
described both checks as running during `grade`. Corrected result: for all
three tasks, both fixtures, `grader_content_in_patch` is `clean` — no
overlay content or overlay path appears in `known-good.patch` or
`known-broken.patch` for any task, confirmed in every receipt's
`contamination.checks` entry (verdict `pass`/`fail` in all six cases, not
`unavailable`, now that `selfhost-run-record-gate` also grades).
`grader_name_in_payload` is not applicable to this record's checks and is
not claimed here; it will run, if at all, during the twelve live cells
themselves, against each cell's tool-call payloads, not against the
fixtures graded here.

## Review

Sonnet implements; Opus reviews this pre-run record before cell 1 and the
result before it is called accepted, per the brief. The review checks:
fixtures proven in both directions for all three tasks (fixed this round —
see "Task qualification" and "The three prompts" for what changed and why);
the plan is absent from every `base/`; the rule applied as written; every
count carries its recompute; diagnostics labelled; no sentence compares
Ornith with another model or one arm with another. **No Fable review
unless the maintainer asks.**

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

It is not run as part of preparing this record. All twelve cells are live:
the controller confirmed `n = 12` stands, since all three tasks now
qualify in both directions (fix round). The launcher also gained, this
round, a guard against a truncated per-cell command argv (INFRASTRUCTURE
STOP rather than silently "succeeding" at running nothing) and a
`launcher COMPLETE, all cells NOT-RUN` variant of its final log line for
the case where the wall-clock stop is already past before the first cell
can start.

## Retention

Every cell keeps its `attempt.json`, patch(es), receipts and transcript
under its own cell directory (`<output-root>/cell-NN-XY/`). Nothing is
discarded, including cells that stop early. The output root itself keeps the
launcher's own copy (`launch.sh`), the batch `schedule.json`, the launcher
log (`run.log`, with per-cell start/end timestamps and elapsed seconds), and
— one level up, beside each cell directory rather than inside it — that
cell's captured stdout, `<output-root>/cell-NN-XY.stdout.log`.

## Disclosed debt (recorded, not fixed)

Per "no instrument change larger than reading the evidence" and "no design
rewrite" — named here so the reviewer and result document can weigh them,
none acted on:

- **`just gates` (and its `just docs` step) is red on this branch**,
  independent of anything built for this probe: `docs/current/selfhost-headroom-probe-brief.md:11`
  has a dangling MyST cross-reference to `ornith-9b-ceiling-probe-result.md`,
  a file that does not exist in this worktree (introduced with the brief
  itself at `f3b6fc6`, before this probe's work started). Confirmed with a
  clean `docs/_build`: `sphinx-build -W` treats the warning as an error,
  `just docs` exits 1, `just gates` fails at that step. The brief is not
  edited to fix this (out of scope; it is the frozen authorization
  document), and the default pytest tier — the tier this record's green
  runs are measured against — does not include `just gates`.
- **`selfhost-guard-prefixes`'s `base/` omits `tests/test_hook_guard.py`
  entirely** (it is the task's own hidden file, excluded per the brief's
  rule), so 75 of its 83 expected hidden ids are regression tests for
  guard behavior that predates this task and are invisible to the model —
  the workspace ships no public test that exercises `tools/hooks/guard.py`
  at all. A model has no public signal that its edit preserved (or broke)
  any of those 75; only the 8 new wrapper-prefix cases are described in
  the prompt.
- **`base/docs/superpowers/` is an empty directory in all three task
  trees** — `plans/` and `specs/` are excluded per the brief, and nothing
  else lives directly under `superpowers/` at these commits, so the
  directory itself is present and empty. Harmless, noted for completeness.
- **Plausible, reasonable model behaviors resolve to `unavailable` (a
  scope violation caught by `check_allowlist`) rather than to a graded
  `fail`**, for all three tasks: creating `src/satyrn_evals/run_record/__init__.py`
  instead of `src/satyrn_evals/run_record.py` (a package instead of a
  module — same import surface, different path, outside `source_paths`);
  touching `pyproject.toml` or `uv.lock` (e.g. to add a dependency); or
  placing a new test file outside `tests/`. These are in-rule as
  non-`pass` outcomes per the decision rule (`receipt.json verdict` is not
  `pass`), but they are a materially different failure mode from a
  behaviorally wrong implementation, and the result document's per-cell
  table must keep them separable (e.g. by `reason` text), not collapsed
  into an undifferentiated "fail" count.

## Budget grant

**Granted 2026-09-14 by the maintainer, in session** ("Granted, exclusive
GPU, dispatch it to an Opus controller"): `n = 12` cells under the frozen
conditions above, on **exclusive GPU** for the duration of the run,
wall-clock stop 3 h. Cell 1 may start once the three tasks are qualified in
both directions and this record is committed and reviewed — **all three
now are** (fix round: `selfhost-run-record-gate`'s `oracle` field and two
`contracts.R1` were amended; see "Task qualification" and "The three
prompts"). The controller confirmed `n = 12` stands across all three
tasks.
