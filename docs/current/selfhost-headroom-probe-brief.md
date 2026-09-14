# Brief: does bare Pi on Ornith 1.5 9B have headroom on this repository's own work?

**Written 2026-09-14 by Fable, for a fresh agent. Self-contained.** It
authorizes building three tasks from `release-one`'s own history, one pre-run
record, one bounded Baseline-only live probe of at most twelve cells, and a
result document. Nothing else. The maintainer's budget grant is recorded at the
end of this file; **do not run a cell until it is present.**

## Why this probe exists

Release one targets Ornith 1.5 9B. The [ceiling probe](ornith-9b-ceiling-probe-result.md)
found one budget ceiling on the AgentClinic fleet (`depth-3` at `R1`: 3 of 4
cells timed out at 900 s) and none on `depth-2` or the four-phase build. The
AgentClinic fleet is a toy; the audience is Python developers working in real
repositories with real test suites. The maintainer's proposal, 2026-09-14: mint
tasks from work this project actually did. Phase 0 of the restart left twelve
reviewed tasks, each with a base commit, a known-good commit, and the tests the
plan specified. Three of the codeable ones become tasks here.

**The question is only whether headroom exists on this task shape.** If bare
Pi clears all three, the design keeps `depth-3` at `R1` as its single ceiling
and names the self-hosted generator as Phase 2 work. If it fails on some, the
design's workload section is written on that.

**Informed selection, disclosed.** The three tasks were chosen by size and
shape (small single-file regex; medium module plus CLI wiring; cross-file
rewrite), before any Ornith cell ran on any of them. No count from any earlier
run pools with this probe's denominator.

## The three tasks

All three are cut from the `release-one` branch of this repository. `BASE` is
the tree the model receives; `GOOD` is the commit whose non-test changes are
the known-good witness; `HIDDEN` is the test material withheld from the
workspace and run by the oracle. Task directories are
`src/satyrn_evals/tasks/selfhost-<name>/`, built in the probe worktree.

| Name | BASE | GOOD | HIDDEN (oracle) | Size |
|---|---|---|---|---|
| `selfhost-guard-prefixes` | `3e996a1` | `4a54743`, **only** its `tools/hooks/guard.py` hunk | the two parametrized test functions appended to `tests/test_hook_guard.py` in `4a54743` (`test_pi_print_behind_a_wrapper_prefix_is_blocked`, `test_pi_lookalikes_behind_wrapper_shaped_text_are_still_allowed`; 13 cases), as an overlay file replacing the workspace copy | one regex in a 94-line file |
| `selfhost-run-record-gate` | `cc9ab53` | `9131ec5` + `b253c99`, files `src/satyrn_evals/run_record.py` and `src/satyrn_evals/cli.py` | `tests/test_run_record.py` at `b253c99` (`9131ec5` touched no other test file, so the `launch --check` CLI is exercised only through the prose) | new 82-line module + 24-line CLI wiring |
| `selfhost-docs-linter` | `73ec172` | `a7209a3` + `cc9ab53`, file `tools/lint_docs.py` | `tests/test_doc_caps.py` at `cc9ab53` | rewrite of an existing 80-line tool, cross-file behaviour over `docs/` |

**Building a task directory.** For each: `base/` is `git archive BASE` of the
release-one branch, **minus** `docs/superpowers/plans/**` (the plan holds the
complete answer), `docs/superpowers/specs/**`, `.claude/**`, `.github/**`,
`PROVENANCE.md`, and the HIDDEN test file(s). `overlay/` holds the HIDDEN
file(s) at their workspace-relative paths. `fixtures/known-good.patch` is the
GOOD diff restricted to the named non-test files; `fixtures/known-broken.patch`
creates the target module or function as a stub that imports cleanly and
returns `None` (so the hidden suite fails on behaviour, not on collection).
`manifest.json` follows `agentclinic-repair-depth-3/manifest.json`'s shape:
`source_paths` = the files GOOD touches plus `tests`; `oracle` runs pytest with
`-p satyrn_evals.oracle_hook` over the overlay file(s) only; `public_suite` =
`["uv","run","pytest","-q"]`; `expected_test_ids` = every test in HIDDEN.
**Before any cell**, prove each task in both directions with `satyrn-evals grade`
against the two fixtures, exactly as the AgentClinic tasks were qualified; a
task that does not reject its known-broken patch is not run.

**The prompt (rung `R1`, by analogy).** The task's text from the Phase 0 plan
(`git show release-one:docs/superpowers/plans/2026-09-13-phase-0-restart.md`,
Tasks 7, 8; and for the guard task, item B of the fix-wave brief reproduced
below), reduced to: the task title, the **Files** list, the **Interfaces →
Produces** block verbatim, and the prose of each step with **every fenced code
block removed**. The model is told the names and signatures the hidden tests
import, not the code. Record each prompt's digest in the pre-run record.

Fix-wave item B, verbatim, for `selfhost-guard-prefixes`:

> `_PI_LEAD = ^[\s(]*pi\b` lets `uv run pi -p hi`, `env K=1 pi -p hi`,
> `time pi -p hi`, `timeout 60 pi -p hi`, `sudo pi -p hi`, `nohup pi -p hi`,
> `$(pi -p hi)` and `` `pi -p hi` `` through. `uv run` is this repository's
> habitual prefix. Widen the lead to accept an optional run of known wrapper
> tokens before `pi`: `uv run`, `env` (with optional `K=V` assignments),
> `time`, `timeout <arg>`, `sudo`, `nohup`, and an opening `$(` or backtick.
> Keep `ls pi -p`, `grep -rn pi docs`, `echo pi`, `pip install -p x`,
> `pipx -p` allowed. Do not touch the write-protection rules.

## Question and decision rule (frozen here, before any inference)

**Question.** For each of the three tasks, how many of four Baseline cells on
Ornith 1.5 9B fail?

**A cell fails** when `receipt.json` `verdict` is not `pass` **or**
`attempt.json` `code` is not `OK`, read from the retained attempt directory.
A `MODEL_ERROR` (5xx, out of memory) is infrastructure: the cell is **unscored**,
diagnosed, recorded, and not re-run; denominators count scored cells only.

**Decision rule.** A task has **headroom** if **2 or more of its 4 scored cells
fail**. Report per task. Then:

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
Fisher test or interval; why Ornith fails where it fails. Twelve cells support
per-task presence/absence of headroom and nothing finer.

## Frozen conditions

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

## Hazards specific to this task shape, disclosed

- **The workspace is the harness's own package.** The oracle plugin
  `satyrn_evals.oracle_hook` resolves to the *workspace's* copy at BASE. A
  model that edits it could forge a result; `source_paths` excludes it, so an
  edit there is a scope violation, counted not prevented. State this as a
  trust-boundary limit in the record and the result.
- **Offline provisioning.** `uv run` in the materialized workspace must
  resolve from the local cache; preflight runs the public suite once in a
  scratch materialization with the network disabled and records the time.
- **The plan is the answer key.** The exclusion list above removes it; the
  contamination check (`grader_content_in_patch`, `grader_name_in_payload`)
  runs as for every task, and the pre-run record lists what was excluded.
- **Hidden tests that import by name.** The Interfaces block names the
  symbols; a model that chooses a different name fails on collection, which
  is a legitimate failure of the writing-down, and is reported as such.

## Operate here

Main checkout `/Users/pauleveritt/projects/pauleveritt/satyrn-evals` is now
on `release-one`, whose gates block direct `satyrn-evals run` and result writes
outside a launcher that Phase 2 has not built. **This probe therefore runs on
the tagged tree.** The worktree already exists:
`.claude/worktrees/selfhost-headroom-probe`, branch
`worktree-selfhost-headroom-probe`, cut from **`main` at `7c7b188`** (the fat
tree with the task tooling and both prior probes merged); this brief is its
first commit. Work only there. Build the three task directories under its
`src/satyrn_evals/tasks/` and commit them; commit the pre-run record and
the result under `docs/current/` there. Reuse the ceiling probe's launcher
(`~/satyrn-smokes/2026-09-14-ornith9b-ceiling-probe/launch.sh`) with the
cells substituted. **Do not touch** the main checkout, `.claude/worktrees/ornith-*`,
any other worktree, or `satyrn-engine`. **No merge.**

## Sequence

1. **Build and qualify** the three tasks (above). Commit.
2. **Preflight.** Clean tree; task-tree digests (the ceiling probe's walk);
   `satyrn-evals-attempt-pi` resolves; one live completion; no
   measurement-shaped Pi process; output root absent; the offline public-suite
   timing.
3. **Pre-run record**, `docs/current/selfhost-headroom-probe-pre-run-record.md`,
   in the shape of `ornith-9b-ceiling-probe-pre-run-record.md`: question, rule,
   conditions, digests, the three prompts' digests and the exclusion list, the
   exact commands, the evals revision, retention. Toctree entry. Commit.
   **Stop until the grant is present.**
4. **Run** the twelve cells serially: `schedule.json` first, per-cell timestamps,
   loadability by live completion, wall-clock stop, no overwrite.
5. **Read** the measures from retained artifacts. Events, never `grep -c`.
6. **Result**, `docs/current/selfhost-headroom-probe-result.md`: 12-row table
   (cell, task, code, verdict, seconds, turns, tool calls, tokens in/out,
   suite runs before last mutation), per-task fail counts of 4, the rule
   applied verbatim, the diagnostics table, missingness, "what this does not
   establish", digests re-verified. Toctree entry. Commit. Report under 200
   words: the three counts, which tasks have headroom, anything that stopped
   the run.

## Loop rules

- Only an **established infrastructure failure** stops launches. A fail, a
  timeout, a refusal, a collection error or a scope violation is the
  observation; it is kept and counted, never replaced.
- `n = 12` is frozen. No extension, re-run or replacement for any result.
- No other inference on this machine while the launcher runs.

## Review

Sonnet implements; Opus reviews the task qualification and the pre-run record
before cell 1, and the result before it is called accepted, re-deriving the
per-task counts and two cells' budget figures from the artifacts first. **No
Fable review unless the maintainer asks.** Opus checks: fixtures proven in
both directions; the plan is absent from every `base/`; the rule applied as
written; every count carries its recompute; diagnostics labelled; no sentence
compares Ornith with another model or one arm with another.

## Hard stops

- No Engine arm, no engine change, no design rewrite, no new task beyond the
  three named.
- No pooling with either Ornith probe or any gemma run.
- No instrument change larger than reading the evidence; record debt instead.
- The run ends with the result document.

## Budget grant

*Not yet granted. The maintainer records the grant here, in session, before
cell 1.*
