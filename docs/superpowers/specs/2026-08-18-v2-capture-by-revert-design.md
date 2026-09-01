# V2 — Capture by revert: design spec

**Phase:** V2 (`ROADMAP.md:20`). **Date:** 2026-08-18. **Status:** implemented;
corrected 2026-08-19.

## Correction — 2026-08-19 (normative)

The approved text originally described the source repository as wholly
read-only, armed the cleanup guard only after `git worktree add` reported
success, scoped hook suppression to worktree add/remove, placed hook results
in an independent system temporary location, copied `base/` without an
explicit symlink contract, and derived the selected patch by parsing and
reassembling Git's human-readable diff. It also described cleanup precedence
in terms of the record written to disk without stating that the returned
record and CLI result must change. Review found that each statement left a
real lifecycle or evidence gap. They are corrected, rather than silently
edited away, by the following rules; these rules supersede any conflicting
historical wording or examples in the plan:

1. `--output` authorizes the declared task-directory and capture-record
   writes and is the **only** exception to source immutability. Pre-existing
   source files and the source repository's index, branch, and `HEAD` remain
   unchanged. Output inside the source working tree is therefore an explicit
   artifact write, not evidence that capture mutated pre-existing source.
2. Immediately before the mutating `git worktree add`, registration state is
   conservatively `MAY_EXIST`. It becomes registered or absent only after Git
   state confirms that fact. The temporary parent is never removed until
   registration absence is confirmed; an add that mutates registration and
   then reports failure still enters cleanup.
3. Every Git command owned by capture, including discovery, pin, status,
   metadata, patch generation, apply, add, removal, and cleanup probes, runs
   with `-c core.hooksPath=/dev/null -c core.fsmonitor=false`, ignores replace
   refs and legacy grafts, and uses the documented repository-routing
   environment cleanup. Thus mutable repository-local overlays cannot change
   the pinned commit, its parent, or the captured tree.
4. Before worktree creation, capture validates that its safe temporary parent
   is outside every path reported by `git worktree list --porcelain -z`.
   Worktree materialization and reserved-but-unlinked oracle hook-result files
   live under that validated parent, so evaluator evidence is never nested
   beneath a pre-existing registered worktree and safe-parent deletion has an
   independently verified boundary.
5. A cleanup failure replaces the pending success, refusal, or post-acceptance
   collision everywhere: the persisted record, the `CaptureRecord` returned
   by the public API, and the CLI outcome/exit code all report
   `CLEANUP_FAILED`. The displaced result is retained in the message, and the
   retained path is named. An unexpected catchable exception is re-raised,
   with any cleanup failure attached without replacing the original.
6. Materializing `base/` preserves tracked symbolic links as symbolic links;
   it does not dereference them into copied files. On POSIX, capture overrides
   a repository's `core.symlinks=false` while creating the isolated worktree
   so the Git tree, not local checkout policy, controls the materialization.
7. Source selection comes from Git's NUL-delimited name-status metadata. Both
   old and new paths of a rename or copy are classified by the test-path rule,
   including copies found only by `--find-copies-harder`. Git itself generates
   the patch for the selected paths with external diff drivers and textconv
   disabled. Capture does not parse and reconstruct a human-readable unified
   diff. Grading recognizes ordinary hunks and Git's extended rename, copy,
   binary, mode-only, and empty-file forms, including quoted control and UTF-8
   byte escapes, before applying the source allowlist. Git output and patch
   artifacts are carried without universal newline conversion, so carriage
   returns, CRLF blobs, and filesystem path bytes survive capture and
   re-grading unchanged.
8. An output directory inside the source repository is allowed only when its
   subtree contains no tracked path. Capture then excludes that declared,
   untracked artifact subtree from the clean-tree check, so a second capture
   can coexist with the first without hiding dirty source. The repository root
   and Git administrative directories are never valid output directories.
   Containment checks account for symlink and case-insensitive filesystem
   aliases rather than relying on lexical spelling alone.
9. A pre-existing task directory or capture-record path is a usage error
   (exit 2, no write), not a `TASK_EXISTS` record that would overwrite the
   artifact proving the collision. Task ownership is established before
   rollback is allowed, and records are published atomically and exclusively;
   a race, dangling symlink, or failed publication cannot overwrite, follow,
   or remove another writer's artifact. `TASK_EXISTS` remains readable for
   records produced by the original implementation.
10. After pin/name/output acceptance, predictable Git spawn failures,
    oracle-result setup failures, and task artifact write failures become
    named refusals (`GIT_FAILED`, `ORACLE_ENV`, and `ARTIFACT_FAILED`). Pin
    cannot distinguish an unusable Git executable from an unusable repository
    through its shared Git boundary, so pin failure remains usage/no record.
    Resolving the first parent and reading the fixing commit subject are part
    of pinning and happen before name/output acceptance; a Git invocation
    failure at either step is therefore usage/no record. A successfully
    resolved root commit is distinct: after name/output acceptance it is a
    recorded `NO_PARENT` refusal.
    A failure to create the output directory is also usage because there is no
    writable channel for a record.
11. The isolated worktree overrides `core.sparseCheckout=true`. A caller may
    use a sparse checkout, but the captured `base/` is always the complete
    tracked tree at the pinned parent, including paths omitted from the
    caller's checkout patterns.
12. Exception precedence is based only on an exception raised by the active
    capture operation. An exception already being handled by the caller is
    never treated as capture's primary exception and never receives capture
    cleanup notes.

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
  minutes, without changing pre-existing source files or the source
  repository's index, branch, or `HEAD`; declared writes below `--output`
  are the sole exception.
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
2. **Pre-existing source state is immutable; isolation comes from a detached
   worktree** — the pattern specified in the E3 delivery spec of the sibling
   repository (`satyrn-engine` PR #1,
   `docs/superpowers/specs/2026-08-18-e3-delivery-design.md`): pin
   `PARENT^{commit}`, preflight a clean tree, `git worktree add --detach` in
   a validated safe temporary parent outside all registered worktrees, strip
   repository-local routing variables from child environments, suppress
   hooks and filesystem monitors on every owned Git command, and enforce a
   cleanup precedence with `git worktree remove --force`. That spec is
   evidence, not source: the lifecycle is re-earned here. Unlike E3, capture
   never commits and never publishes a ref — the worktree is the
   materialization mechanism, not a publication channel. Declared artifacts
   below `--output` are the sole source-write exception.
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
  repository's pre-existing files, index, branch, and `HEAD` are never
  changed. The transient worktree registration is removed on cleanup;
  declared artifacts below `--output` are the only permitted working-tree
  writes (E3's isolation guarantee, corrected 2026-08-19).
- `--name NAME` — the task directory name; default: a slug of the fix
  commit's subject line. Must be a single path component (the `resolve_task`
  rule from V1). An invalid or underivable name (empty subject, unsafe
  slug) is a usage error (exit 2, nothing written). A collision with an
  existing task or record is also a usage error and never overwrites it.
- `--contract TEXT` — the manifest's one-sentence task statement; default:
  the fix commit's subject line.
- `--output DIR` — where the task directory and capture record are written;
  default `./tasks/`. These declared artifact writes are permitted even when
  `DIR` is inside the source working tree, provided its subtree contains no
  tracked path. The repository root and Git administrative directories are
  rejected. No pre-existing source path may be modified.
- `grade --tasks-root DIR` — captured tasks live outside the wheel; this
  points `grade` at them. The bundled root (`DEFAULT_TASKS_ROOT`) stays the
  default.

Capture is silent over the CLI: artifacts, not stdout. No `--verify` flag
(decision 1).

## Exit codes

| Code | Meaning | Artifact |
|------|---------|----------|
| 0 | Task captured; all four checks passed | task directory + capture record (`outcome: captured`) |
| 2 | Usage error — bad arguments, invalid/colliding task name, invalid output location, `--repo` not a git repository or has no commits, `--revert SHA` does not name a commit in the repository, missing `--revert` | none |
| 3 | Refusal — a check or accepted git/oracle/artifact/cleanup operation failed | capture record (`outcome: refused`) with a precise `code` |

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
for now, with tracked symbolic links preserved as links rather than
dereferenced. Pruning is a deferred optimization, correctness first.

**`fixtures/known-good.patch`** — a Git-generated diff from `PARENT` to `FIX`
restricted to selected non-test source changes. Selection uses NUL-delimited
Git name-status metadata and classifies both old and new paths for renames and
copies; Git then renders the selected patch. Capture does not split and
reassemble human-readable diff sections. Tests stay at base. A fix whose
changes are *entirely* test paths is refused (`NO_SOURCE_CHANGE`).

**Test-path rule** (documented, testable, sibling-tested): a path is a test
path when its basename matches `test_*` or `*_test.py`, it is
`conftest.py`, or any path component is `tests`. Everything else is source.
The rule cannot be perfect, and does not need to be: a misclassification
that matters fails a check honestly. Exclude a needed source change and the
winnable check refuses; include a test change and the executed-vs-expected
guard refuses. For a rename or copy, both the old and new path are classified
so a change crossing the source/test boundary is not smuggled into the
selected patch. The existing machinery is the safety net.

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
   non-test source change according to Git's NUL-delimited metadata. Check 1
   refuses `REPO_DIRTY`, `NO_PARENT`, and `NO_SOURCE_CHANGE`. A name collision
   is a usage error because preserving the existing artifact
   leaves no safe record path. All of these happen before any worktree exists;
   later git failures are `GIT_FAILED`. (Repo-not-git, unborn, and bad-SHA are
   at the usage boundary — see Pin — not check 1.)
3. **Derive** — read Git's NUL-delimited name-status metadata for `PARENT` to
   `FIX`; classify both old and new paths for rename/copy entries; ask Git to
   generate the diff for the selected source paths with rename/copy detection,
   external drivers, textconv, and color disabled. That Git-produced diff is
   `known-good.patch`; the selected paths are `source_paths`.
4. **Worktree** — obtain a temporary parent, verify it lies outside every
   registered worktree, and reserve the hook-result paths beneath it. Set the
   registration guard to `MAY_EXIST` immediately before `git worktree add
   --detach PATH PARENT`; resolve the guard only by inspecting Git's
   registration state. The transient registration is removed on cleanup.
5. **Materialize** — copy the pristine worktree tree to the task's `base/`
   before any oracle run, preserving tracked symbolic links.
6. **Verify** — three oracle runs, reusing V1's hook-result machinery (a
   unique reserved-but-unlinked hook path under the validated safe temporary
   parent, the run-start timestamp, the stale-file rejection — the verdict
   never comes from stdout or an exit code):
   - the **full-suite base run** in the pristine worktree (check 2);
   - apply the known-good, then the **full-suite fixed run** — the
     discriminating set is fail-at-base ∩ pass-with-fix (check 3);
   - the **recorded restricted oracle** — the discriminating IDs baked in —
     which must pass every discriminating ID (check 4, proving the exact
     command grading will run).
7. **Cleanup** — `try`/`finally`; the guard is already `MAY_EXIST` before the
   mutating add and is cleared only after registration absence is confirmed.
   Use `git worktree remove --force` when registered, and retain the temporary
   parent whenever absence cannot be confirmed. A locked or uncertain
   worktree is a visible `CLEANUP_FAILED` naming the retained path, with the
   documented manual recovery (`git worktree unlock PATH`, `git worktree
   remove --force PATH`, `git worktree prune`). The cleanup result replaces
   the pending persisted record, returned record, and CLI result.
   Abrupt-termination crash recovery is deferred.
8. **Record** — write the capture record and, when captured, the task
   directory.

Environment boundaries on every child process (git and oracle): strip the
variables named by `git rev-parse --local-env-vars` plus `GIT_NAMESPACE`, so
a Git command discovers the isolated worktree rather than the source
repository. Every engine-owned Git invocation also carries `-c
core.hooksPath=/dev/null -c core.fsmonitor=false`; this is unconditional, not
limited to worktree add/remove or repositories known to have hooks. Hook and
filesystem-monitor sentinels are part of the integration tier.

## Test layout

**Default tier** — no model, no network, no subprocess (tripwire):
- discriminating-set computation from two hook results (refusal sibling:
  empty set);
- NUL name-status parsing and test-path selection (siblings: each
  classification, old/new rename and copy paths, an all-test-path refusal,
  and a mixed selection); Git-generated patch correctness stays in the
  integration tier;
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
  reporting, returned-record/CLI precedence, and explicit test teardown;
- add failure after registration proves the `MAY_EXIST` guard retains or
  removes the temporary parent only after registration absence is confirmed;
- hook and filesystem-monitor sentinels do not fire during any owned Git
  command; the safe temporary parent and hook-result paths are outside all
  registered worktrees;
- materialized `base/` preserves a tracked symlink;
- a sparse-configured source still materializes the complete tracked tree;
- rename/copy and unusual-name fixtures prove NUL metadata classification and
  Git-generated selected patches; space, tab, UTF-8, binary, empty deletion,
  and extended rename/copy patches pass the real grader allowlist;
- source-local output proves repeated capture works while tracked output
  subtrees and collision targets cannot hide or overwrite source/artifacts;
- the source repository's reflog is unchanged after a successful capture.

## Correction verification — 2026-08-19

Verified from the corrected tree, not inferred from the plan:

- default tier: 269 passed, 85 integration tests deselected;
- integration tier: 84 passed, 1 capability skip because this APFS host
  rejects a raw non-UTF-8 filename before the test can create it;
- combined source coverage: 1,200 statements and 378 branches, 100% for
  both, after combining default, integration, and covered child processes;
- Ruff, Pyrefly, strict Sphinx, and `git diff --check`: clean.

The reproducible coverage sequence is `coverage erase`, `coverage run -m
pytest`, `coverage run -m pytest -m integration`, `coverage combine`, then
`coverage report`. The two runs intentionally do not use `--append` because
subprocess coverage writes parallel data files that `coverage combine` owns.

## File layout

```
src/satyrn_evals/
  cli.py            capture subcommand, --tasks-root on grade, exit codes
  capture.py        orchestrate: pin, preflight, worktree, materialize,
                    derive, verify, cleanup, record
  capture_record.py capture record shape, write/read
  diff_filter.py    NUL name-status parsing and old/new test-path selection
  discriminating.py discriminating-set computation from two hook results
  manifest.py       known_broken optional, provenance
  patch.py          ordinary/extended Git diff path parsing and allowlist
  grade.py          byte-preserving patch hashing and application
  (unchanged)       verdict.py, receipt.py, oracle_hook.py
tests/
  test_capture_*.py          default tier: pure logic and injected failures
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
- bare or unborn repositories, submodule mutation, Windows — outside V2,
  matching E3's scope guard
- the claims layer — later, with a consumer
- wall-clock comparisons — never (`BRIEF.md`; summaries use counts)
