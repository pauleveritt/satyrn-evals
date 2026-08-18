# V2 — Capture by revert: design spec

**Phase:** V2 (`ROADMAP.md:20`). **Date:** 2026-08-18. **Status:** approved
design; implementation plan pending.

## Why this phase

V1 proved the grading seam: a bundled task's known-good patch is accepted and
its known-broken one rejected, offline and deterministic. But every task in
V1 is hand-authored, and hand-authored tasks are how the prior project
saturated every suite it built. V2 changes how tasks get made: `capture
--revert SHA` turns a real fixing commit from a contributor's own repository
into a task whose base is the buggy parent tree and whose known-good patch is
the fix diff itself — winnable by construction, in minutes.

This is the first step of the roadmap's capture→attempt→grade→diagnose loop
(`README.md:56`), and the first *diagnostic workload* producer. The
unsolved-problem section of `BRIEF.md` ("a suite with headroom") is not
settled here: V2 proves a captured task is *valid* (un-done at base, and
winnable), not that it *discriminates*. The baseline probe, which owns
discriminating power, lands with the attempt loop in V3/V4. V2 must not
over-build for a consumer that does not exist yet.

Settled and not reopened: the phase list, the diagnosis-before-claims split,
and the two selection rules (`BRIEF.md`; `ROADMAP.md:20`). This spec only
fixes how those rules apply to V2's artifacts.

## Done-when

- `satyrn-evals capture --revert SHA` (with `--repo`, `--name`,
  `--contract`, `--output`) turns a fixing commit in a real repository into
  a task directory whose four deterministic capture checks all pass, in
  minutes, without touching the source repository's working tree, index,
  branch, or `HEAD`.
- The captured task's `fixtures/known-good.patch` grades `pass` through the
  real `grade` command, asserting the fixture by name (the capture analog of
  the evidence floor, `BRIEF.md` rule 2).
- Refusal is the default outcome of most failures and is never silent: each
  refusal path (dirty source, fix touching only tests, empty discriminating
  set, missing oracle environment, git and cleanup failures) writes a
  capture record naming a precise `code`, and each refusal test has a
  sibling success test (`CLAUDE.md` rule 6).
- Default tier green with the spawn tripwire active; `ruff` and `pyrefly`
  clean; integration tier green.

## Decisions from the brainstorm

1. **Verification is capture, not a flag** — capture runs the repository's
   tests twice (at base, and with the fix applied), computes the
   discriminating test set, and refuses to produce a task if any of the four
   deterministic checks fails. No `--verify`; a captured task is by
   definition one whose checks passed.
2. **The source repository is read-only; isolation comes from a detached
   worktree** — the pattern specified in the E3 delivery spec of the sibling
   repository (`satyrn-engine` PR #1,
   `docs/superpowers/specs/2026-08-18-e3-delivery-design.md`): pin
   `PARENT^{commit}`, preflight a clean tree, `git worktree add --detach` in
   a unique temporary parent, strip repository-local routing variables from
   child environments, and enforce a cleanup precedence with `git worktree
   remove --force`. That spec is evidence, not source: the lifecycle is
   re-earned here. Unlike E3, capture never commits and never publishes a
   ref — the worktree is the materialization mechanism, not a publication
   channel.
3. **The oracle is recorded; the environment is whatever capture runs in**
   — the manifest's oracle is `python -m pytest -p satyrn_evals.oracle_hook
   <discriminating test IDs...>`, run with the environment evals provides
   (Q3 option b). A repository whose dependencies are not importable there
   fails the base-oracle check honestly, with a clear reason; environment
   materialization stays deferred where `CLAUDE.md` already puts it. No
   absolute paths, venv snapshots, or dependency manifests are recorded:
   provenance (repo + SHAs) lets a future job re-derive the environment.
4. **A captured task carries no known-broken fixture** — `known_broken`
   becomes optional in the manifest (Q4 option a). A captured task is a
   diagnostic workload; its validity is the four checks, not a fabricated
   broken patch. The two selection rules are settled: a grader fixture (the
   bundled `format_number`) proves the grading machinery discriminates and
   keeps both fixtures; a diagnostic workload must be able to show a
   difference. Forcing capture to synthesize a guaranteed-broken patch would
   either break the schema or fabricate evidence — the harvest index warns
   against clean-looking numbers.
5. **Exit codes stay coarse; the capture record is precise** — `0`
   captured, `2` usage, `3` refused. The reason lives in the capture record's
   `code`, never in the exit code (V1 rule 4's philosophy, reused).

## CLI surface

```
satyrn-evals capture --revert SHA [--repo PATH] [--name NAME] [--contract TEXT] [--output DIR]
satyrn-evals grade --tasks-root DIR TASK PATCH [--receipt PATH]
```

- `--revert SHA` — the fixing commit. The task's base is `PARENT^{commit}`,
  and the known-good patch is the fix diff restricted to non-test source
  paths. Required.
- `--repo PATH` — the source repository; default: the current directory. The
  repository's working tree, index, branch, and `HEAD` are never touched;
  the only source-repository mutation is the transient worktree
  registration, removed on cleanup (E3's isolation guarantee).
- `--name NAME` — the task directory name; default: a slug of the fix
  commit's subject line. Must be a single path component (the `resolve_task`
  rule from V1). An invalid or underivable name (empty subject, unsafe
  slug) is a usage error (exit 2, nothing written); a collision with an
  existing task or record in the output directory is a refusal
  (`TASK_EXISTS`, exit 3).
- `--contract TEXT` — the manifest's one-sentence task statement; default:
  the fix commit's subject line.
- `--output DIR` — where the task directory is written; default `./tasks/`.
- `grade --tasks-root DIR` — captured tasks live outside the wheel; this
  points `grade` at them. The bundled root (`DEFAULT_TASKS_ROOT`) stays the
  default.

Capture is silent over the CLI: artifacts, not stdout. No `--verify` flag
(decision 1).

## Exit codes

| Code | Meaning | Artifact |
|------|---------|----------|
| 0 | Task captured; all four checks passed | task directory + capture record (`outcome: captured`) |
| 2 | Usage error — bad arguments, invalid task name, `--repo` not a git repository or has no commits, `--revert SHA` does not name a commit in the repository, missing `--revert` | none |
| 3 | Refusal — a check failed, a precondition is unmet (dirty source, name collision), or a git/cleanup operation failed | capture record (`outcome: refused`) with a precise `code` |

The capture record's `code` is authoritative; the exit code is coarse by
design. On a usage error nothing is written because no operation was
accepted.

## Data shapes

**Task directory** (`<output>/<name>/`):

```
manifest.json
base/
fixtures/known-good.patch
```

**Capture record** (`<output>/<name>.capture.json`) — written for every
accepted operation (captured or refused), E3-shaped. The path always names
the task: refusals happen only after the name exists, and usage errors write
nothing.

| field | type | populated when |
|-------|------|----------------|
| `version` | integer | always `1` |
| `outcome` | string | always: `captured` or `refused` |
| `code` | string | always; authoritative specific result |
| `message` | string | always; human-readable detail |
| `repo` | string | always; absolute normalized input path |
| `base_sha` | string | preflight resolves `PARENT^{commit}` |
| `fix_sha` | string | preflight resolves `FIX^{commit}` |
| `task_dir` | string or null | the task directory path, when written |
| `oracle` | array or null | the recorded manifest oracle, when checks pass |
| `expected_test_ids` | array or null | the discriminating set, when non-empty |
| `check_outcomes` | object | the four checks: `passed`, `failed`, or `not-run` each |

**Manifest** (`manifest.json`) — the V1 shape (`name`, `contract`, `oracle`,
`expected_test_ids`, `source_paths`, `fixtures`), with two changes:

- `fixtures.known_broken` is **optional**. `known_good` remains required.
  The loader change has sibling tests: a captured task without `known_broken`
  loads; a manifest with a malformed `known_broken` value still rejects.
- Optional `provenance`: `{"repo": ..., "base_sha": ..., "fix_sha": ...}` —
  the one new term in the concept budget; it names what the design needs
  (re-derivation of the environment, diagnosis context, the record a future
  commit miner would read).

**Oracle** — `["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook",
<discriminating test IDs...>]`. The discriminating IDs are baked into the
command so the executed-vs-expected guard holds when `grade` runs it.

**`base/`** — the tracked tree at `PARENT^{commit}`: the pristine worktree
tree copied before any oracle run (so caches and hook artifacts never leak
into the task), without `.git` and without untracked files. The whole tree,
for now: pruning is a deferred optimization, correctness first.

**`fixtures/known-good.patch`** — the fix diff (`git diff PARENT FIX`)
restricted to non-test source paths. Hunks touching test paths are stripped:
tests stay at base. A fix whose changes are *entirely* test paths is refused
(`NO_SOURCE_CHANGE`).

**Test-path rule** (documented, testable, sibling-tested): a path is a test
path when its basename matches `test_*` or `*_test.py`, it is
`conftest.py`, or any path component is `tests`. Everything else is source.
The rule cannot be perfect, and does not need to be: a misclassification
that matters fails a check honestly. Strip a needed source hunk and the
winnable check refuses; keep a test hunk and the executed-vs-expected guard
refuses. The existing machinery is the safety net.

## The four deterministic capture checks

`BRIEF.md`'s phrase, now enumerated. They run in order; the first failure
refuses, and later checks record `not-run`:

1. **Source preflight** — the tracked, deleted, and untracked state is
   clean (E3's exact command: `git --no-optional-locks status --porcelain=v1 -z
   --untracked-files=all --ignore-submodules=none`); `PARENT^{commit}`
   exists (a root-commit fix has no base to revert to and is refused as
   `NO_PARENT`); and the fix diff has at least one non-test source path (an
   all-test-path fix is refused as `NO_SOURCE_CHANGE`). (`--repo` resolving
   to a git repository with at least one commit, and `FIX^{commit}`
   resolving, are usage-boundary checks — see Pin — because they happen
   before a task name exists, so no record can be named.)
2. **Base oracle runs** — a full-suite oracle run (`python -m pytest -p
   satyrn_evals.oracle_hook`, no test-ID restriction — the discriminating
   set is not known yet) produces a hook result with no collection errors
   in the pristine worktree at `PARENT`. Missing dependencies fail here,
   honestly (`ORACLE_ENV`, naming the import failure); this is where Q3's
   environment decision is enforced.
3. **Un-done at base** — the discriminating set (test IDs that fail at base
   and pass with the fix) is non-empty. An empty set is a task at or near
   ceiling — smoke, per `BRIEF.md`'s two selection rules — and is refused
   (`NO_DISCRIMINATING_TESTS`).
4. **Winnable** — with the source-only known-good applied, the recorded
   oracle (the discriminating IDs baked in) passes every discriminating
   test ID; failure is refused as `NOT_WINNABLE`. This verifies the exact
   command grading will run, including that its node IDs are runnable.

## Capture mechanics

The lifecycle, re-earned from the E3 spec. Source-side operations (pin,
preflight, derive) run from the source root and need no worktree;
worktree-side operations (materialize, verify) run in the isolated
worktree:

1. **Pin** — resolve `--repo` with `git rev-parse --show-toplevel`; pin
   `FIX^{commit}` and `PARENT^{commit}`. Derive the task name from the fix
   commit's subject (or accept `--name`). Every later action is based on the
   immutable commits. `--repo` not a git repository (`REPO_NOT_GIT`), a
   repository with no commits (`REPO_UNBORN`), and a `--revert SHA` that
   does not name a commit are **usage errors** (exit 2, no record): they
   happen before a task name exists, so no record can be named, matching
   the exit-table's "no operation was accepted".
2. **Preflight** — check 1: clean tree, `PARENT` exists, fix diff has a
   non-test source path. Check 1 refuses `REPO_DIRTY`, `NO_PARENT`, and
   `NO_SOURCE_CHANGE`; the name-collision `TASK_EXISTS` is a separate
   refusal before checks begin. All of these happen before any worktree
   exists; later git failures are `GIT_FAILED`. (Repo-not-git, unborn, and
   bad-SHA are at the usage boundary — see Pin — not check 1.)
3. **Derive** — `git diff PARENT FIX` read-only from the source root; strip
   test-path hunks; the remainder is `known-good.patch` and `source_paths`
   (the diff computed in check 1, now formatted as artifacts).
4. **Worktree** — `git worktree add --detach PATH PARENT` in a unique
   temporary parent. The only source-repository mutation is the transient
   worktree registration in its gitdir, removed on cleanup; the working
   tree, index, branch, and `HEAD` never change.
5. **Materialize** — copy the pristine worktree tree to the task's `base/`
   before any oracle run.
6. **Verify** — three oracle runs, reusing V1's hook-result machinery (a
   unique reserved-but-unlinked hook path, the run-start timestamp, the
   stale-file rejection — the verdict never comes from stdout or an exit
   code):
   - the **full-suite base run** in the pristine worktree (check 2);
   - apply the known-good, then the **full-suite fixed run** — the
     discriminating set is fail-at-base ∩ pass-with-fix (check 3);
   - the **recorded restricted oracle** — the discriminating IDs baked in —
     which must pass every discriminating ID (check 4, proving the exact
     command grading will run).
7. **Cleanup** — `try`/`finally`, guard set only after registration is
   confirmed and cleared after confirmed removal; `git worktree remove
   --force`. A locked worktree is a visible `CLEANUP_FAILED` naming the
   retained path, with the documented manual recovery (`git worktree unlock
   PATH`, `git worktree remove --force PATH`, `git worktree prune`).
   Abrupt-termination crash recovery is deferred.
8. **Record** — write the capture record and, when captured, the task
   directory.

Environment boundaries on every child process (git and oracle): strip the
variables named by `git rev-parse --local-env-vars` plus `GIT_NAMESPACE`, so
a Git command discovers the isolated worktree rather than the source
repository. Repository config and `core.hooksPath` handling follow E3
(hooks pointed at an engine-owned empty directory) if a captured repository
has hooks; a hook sentinel test is part of the integration tier.

## Test layout

**Default tier** — no model, no network, no subprocess (tripwire):
- discriminating-set computation from two hook results (refusal sibling:
  empty set);
- test-path classification and test-hunk stripping from a diff (siblings:
  each classification, an all-test-path refusal, a mixed diff);
- manifest loading with optional `known_broken` and `provenance` (siblings);
- capture-record construction (captured and refused shapes, nulls);
- name derivation, path-component validation, exit-code mapping.

**Integration tier** (`pytest -m integration`, not run in CI) — real git and
real oracle subprocesses against a small committed stdlib-only fixture
repository with a known fixing commit:
- capture succeeds: four checks pass, known-good derived, `base/` material,
  record written, source working tree/index/HEAD untouched;
- the captured task's `known-good.patch` grades `pass` through the real
  `grade` command with `--tasks-root`, naming the fixture;
- refusal siblings: dirty source, fix touching only tests, no discriminating
  set, missing oracle environment;
- a locked worktree proves `CLEANUP_FAILED`, record precedence, retained-path
  reporting, and explicit test teardown;
- a hook sentinel does not fire during capture;
- the source repository's reflog is unchanged after a successful capture.

## File layout

```
src/satyrn_evals/
  cli.py            capture subcommand, --tasks-root on grade, exit codes
  capture.py        orchestrate: pin, preflight, worktree, materialize,
                    derive, verify, cleanup, record
  capture_record.py capture record shape, write/read
  diff_filter.py    test-path classification, test-hunk stripping
  discriminating.py discriminating-set computation from two hook results
  manifest.py       known_broken optional, provenance
  (unchanged)       grade.py, patch.py, verdict.py, receipt.py, oracle_hook.py
tests/
  test_capture_logic.py      default tier: pure logic above
  integration/test_capture.py real git, real oracle, fixture repository
```

The fixture repository lives in the integration tests (a committed mini-repo
built in a tmp dir), not in the wheel: captured-task machinery is tested
against a synthetic history, not shipped data.

## Concept budget

Defined now: **provenance** (the manifest's repo + base/fix SHAs — the one
new term; it names what re-derivation and diagnosis need),
**capture record** (the durable artifact capture writes, E3-shaped),
**discriminating set** (the test IDs that fail at base and pass with the
fix — the oracle's expected set). The four deterministic capture checks and
the two selection rules are `BRIEF.md` terms, now given concrete form.

## Out of scope (deferred, with the phase that reopens each)

- environment materialization — with the attempt loop (V3/V4); `CLAUDE.md`
  already places it in the integration tier
- the baseline probe and discriminating power — with the attempt loop (V3/V4)
- automated commit mining — backlog, after three manual captures show which
  steps repeat
- pruning the captured `base/` tree — deferred optimization, no consumer yet
- a security sandbox, descendant supervision, retry, repair — outside V2,
  matching E3's scope guard
- bare or unborn repositories, sparse checkouts, submodule mutation,
  Windows — outside V2, matching E3's scope guard
- the claims layer — later, with a consumer
- wall-clock comparisons — never (`BRIEF.md`; summaries use counts)
