# V4 — Real engine attempt: implementation plan

**Goal:** Replace V3's copied attempt directory with an eval-owned synthetic
Git repository and detached worktree, then run one real E5
`satyrn-engine attempt` through the existing artifact seam and grade its
persisted patch offline.

## Correction — 2026-08-23 post-implementation review

The implementation follows the accepted design with the correction recorded
in the spec. In particular:

- `WorkspaceCode` also contains `COMMAND_UNAVAILABLE` for start failure;
- `WorkspaceResult` is the single typed return boundary; the conditional
  `WorkspaceRun` and `CommandRunner` listed below were unnecessary;
- empty bases are valid, while ignored persisted files are force-added;
- temporary-root discovery includes enclosing repositories, all their linked
  worktrees, and Git admin/common directories;
- process/spool/temp ownership and cleanup precedence are tested across
  `OSError` and catchable `BaseException` paths;
- authoritative attempt records use exact field and dependent-artifact
  invariants; and
- the real Engine integration uses real `uv` project and console-script
  resolution with only Pi replaced by a fixture.

The historical task text below remains as planned; this correction is the
authoritative final shape.

**Spec:**
`docs/superpowers/specs/2026-08-23-v4-real-engine-attempt-design.md`.

**Architecture:** `workspace.py` owns only repository reconstruction,
worktree registration, clean child environment, process lifecycle, and
cleanup evidence. `attempt.py` owns task/attempt artifacts, invokes the
workspace once, applies V3's artifact-driven refusal rules, grades, and writes
the attempt record. `manifest.py` exposes an optional opaque Engine contract
path but never parses it. No Engine module is imported.

**Stack:**

```text
v2-capture-documentation
  -> v4-real-attempt-design       spec + this plan
  -> v4-attempt-workspace         synthetic repo/worktree + fake command
  -> v4-engine-integration        opaque contract + real E5 integration
  -> v4-real-attempt-docs         public docs + final evidence
```

Each branch is independently testable and becomes one stacked PR. The final
PR closes Issue #5; earlier PRs link it without claiming completion.

## Global constraints

- Python `>=3.14,<3.15`; stdlib-only runtime remains unchanged.
- Default tests spawn no process and run with the existing tripwire.
- Real Git/process/Engine tests are `integration` tests.
- Preserve V3's artifact-driven semantics: command exit is diagnostic, never
  a verdict.
- Do not import `satyrn_engine`; the executable is the only integration seam.
- Use `StrEnum`, frozen/slotted dataclasses, typed mappings, and Protocols at
  external seams. Do not add a generic result framework.
- Every refusal/timeout/cleanup test has a sibling success test.
- No implementation commit is accepted until the exact phase's tests, Ruff,
  and Pyrefly pass. The completed stack additionally requires strict Sphinx,
  `git diff --check`, all integration tests, and 100% statement/branch
  coverage.

## Phase 1 — Design and plan

**Files**

- Add this plan.
- Add `docs/superpowers/specs/2026-08-23-v4-real-engine-attempt-design.md`.

**Checks**

- Verify Issue #5's two questions are answered: reconstruct from `base/`, and
  evals owns isolation when invoking E5 directly.
- Verify the spec names the newer hooks/fsmonitor boundary rather than the
  issue's older empty-hooks-directory wording.
- Verify ownership of task, Engine contract, worktree, artifacts, and grading
  is explicit.
- Run strict Sphinx and `git diff --check`.

**Commit:** `docs: define V4 real engine attempt`

## Phase 2 — Synthetic repository and detached workspace

### Task 2.1 — Typed workspace model

**Files**

- Add `src/satyrn_evals/workspace.py`.
- Add `tests/test_workspace.py`.

**Interfaces**

- `WorkspaceCode(StrEnum)`: `OK`, `WORKSPACE_FAILED`, `COMMAND_TIMEOUT`,
  `CLEANUP_FAILED`.
- `Registration(Enum)`: `ABSENT`, `MAY_EXIST`, `PRESENT`.
- `TreeKind(StrEnum)`: `REGULAR`, `EXECUTABLE`, `SYMLINK`.
- `TreeEntry` frozen/slotted dataclass: path, kind, digest-or-target.
- `WorkspaceResult` frozen/slotted dataclass: code, message, command exit,
  synthetic base SHA, retained path.
- `WorkspaceRun` frozen/slotted dataclass: result plus captured process output
  metadata required by `attempt.py`.
- `CommandRunner(Protocol)` only where a unit-test seam is needed; production
  Git behavior remains integration-tested against real Git.

Write pure tests first for enum completeness, state transitions, tree
snapshot equality, and cleanup precedence. Keep mappings explicit so a new
code cannot silently inherit an outcome or exit status.

### Task 2.2 — Safe Git and environment boundary

Implement:

- a bytes-preserving Git runner with the corrected safety config;
- local-routing-variable discovery and child-environment stripping;
- safe temporary-parent allocation from explicit roots;
- filesystem-identity containment checks for existing aliases;
- deterministic synthetic commit identity with signing/date interference
  disabled.

Default tests exercise pure environment transformation using supplied names.
Integration tests prove repository-local routing variables, hooks,
reference-transaction hooks, and fsmonitor cannot affect owned Git or the
child, while a normal clean/smudge filter still behaves normally.

### Task 2.3 — Reconstruct and verify the base

Implement:

1. snapshot `task/base` without following symlinks;
2. copy the base into `seed/` preserving links/modes, initialize it, run
   `git add --force --all`, and create the deterministic base commit;
3. set registration to `MAY_EXIST`, add `worktree/` detached at that commit,
   and require confirmed `PRESENT`;
4. verify detached `HEAD`, clean status, and snapshot equality before running
   the command.

Real Git tests cover ordinary files, executable files, relative symlinks,
empty-base/setup refusal, filters, sparse-checkout configuration, hostile
`TMPDIR`, and interruption immediately after a real add.

### Task 2.4 — Run once, timeout, and cleanup

Replace `subprocess.run` in `attempt.py` with the workspace runner:

- disconnected stdin;
- new POSIX session/process group;
- configurable finite positive timeout, default 30 seconds;
- TERM, bounded grace, KILL, direct-child reap, and final group probe;
- cleanup only after safe process disposition;
- remove linked worktree, re-check registration, then remove parent;
- retain parent and return `CLEANUP_FAILED` when absence cannot be confirmed;
- preserve exact unexpected exception identity and attach secondary cleanup
  failures as notes.

Add `--timeout` to the attempt CLI without changing the literal `--` command
boundary. Update `AttemptRecord.command_exit` to `int | None` and introduce a
dedicated typed `AttemptCode`. Loader tests cover old V3 records and the new
nullable operational records.

Integration tests cover normal fake command, nonzero command, timeout with a
TERM-ignoring descendant, locked worktree cleanup, post-add reported failure,
and caller/task/output cleanliness. Default failure tests mock only the
otherwise destructive or non-portable failure branches.

**Phase checks**

```text
uv run pytest -q
uv run pytest -m integration tests/integration/test_attempt.py -q
uv run ruff check .
uv run pyrefly check
git diff --check <phase-base>...HEAD
```

**Commit:** `feat: isolate attempts in detached worktrees`

## Phase 3 — Opaque contract and real E5 command

### Task 3.1 — Manifest contract reference

**Files**

- Modify `src/satyrn_evals/manifest.py`.
- Modify `tests/test_manifest.py`.
- Add `src/satyrn_evals/tasks/format_number/engine-contract.yaml`.
- Modify the bundled manifest.

Add `engine_contract: str | None` to `TaskManifest`. Validate only the path:
safe relative POSIX syntax, existing regular file, no symlink component, and
containment below the task directory. Do not read or parse its contents.
Keep the field optional so V2-captured V3 tasks remain usable.

### Task 3.2 — Append the contract at the executable seam

In `attempt.py`, append the absolute contract path exactly once when the
manifest declares it. Preserve every caller-supplied command token verbatim.
The record stores the effective argv so the actual Engine invocation is
diagnosable.

Update the fake command to accept and record the final positional contract.
Add siblings for an Engine-capable task, a legacy task without a contract,
unsafe contract paths, and a command prefix already containing literal `--`.

### Task 3.3 — Real E5 vertical slice

Add a marked integration test that:

1. points `SATYRN_ENGINE_REPO` at an E5 source checkout;
2. installs a deterministic fake `pi` executable in a private `PATH`;
3. invokes evals with the real command prefix
   `uv run --project ENGINE satyrn-engine attempt --model=fixture/model --`;
4. proves the Engine sees a clean detached Git worktree and uses its E4
   mutation tool;
5. preserves the exact Engine patch/transcript outside the worktree;
6. grades the named bundled known-good result `pass`;
7. proves no synthetic repository, linked-worktree registration, child, or
   source-task mutation remains.

Add a real Engine failure sibling that writes a transcript but no patch;
assert `NO_PATCH`, the Engine exit code, transcript digest/path, and no grade
receipt. The test skips with a precise reason when the source Engine checkout,
Node, Pi fixture prerequisites, or POSIX process behavior are unavailable;
the committed verification record names the exact checkout SHA used.

**Phase checks:** the Phase 2 commands plus the focused real E5 integration.

**Commit:** `feat: run real engine attempts`

## Phase 4 — Evidence, coverage, and public docs

### Task 4.1 — Close the failure matrix and coverage

- Run default and integration tiers together with branch coverage.
- Add only missing behavioral tests; no pragma exclusions for reachable
  branches.
- Prove every workspace/attempt production module at 100% statements and
  branches, then the repository total at 100%.
- Run process/group and locked-cleanup tests repeatedly to expose races.

### Task 4.2 — Synchronize public documentation

Update:

- `README.md` — real Engine example and source-checkout prerequisite;
- `ROADMAP.md` — V4 complete, V5 current only after its prerequisite is met;
- `docs/architecture.md` — reconstructed repo, detached worktree, ownership;
- `docs/usage.md` — command, timeout, opaque contract, recovery procedure;
- `docs/glossary.md` — synthetic base and Engine-capable task only if those
  terms remain necessary after editing;
- `docs/index.md` — current command count and phase status;
- `docs/sdd.md` — exact commands, counts, platform skip, Engine SHA, and named
  evidence.

Do not claim Windows support, a security sandbox, model quality, or task-suite
headroom.

### Task 4.3 — Final gates

Run on one stable tree:

```text
uv run pytest -q
uv run pytest -m integration -q
uv run pytest -m '' --cov=satyrn_evals --cov-branch --cov-report=term-missing -q
uv run ruff check .
uv run pyrefly check
uv run sphinx-build -W -b html docs docs/_build/html
git diff --check <stack-base>...HEAD
git status --short
```

Record the exact results in `docs/sdd.md`; do not pre-write expected counts.

**Commit:** `docs: document V4 real engine attempts`

## Stack publication

After every phase is green locally, push the four branches and create stacked
PRs with exact bases from the Stack section. Use concise titles matching the
existing repository style. The final PR body is exactly:

```text
fixes: #5
```

Earlier PR bodies link Issue #5 without a closing keyword. Before requesting
review, verify remote head OIDs, ancestry, PR bases, mergeability, review
threads, and checks for the whole stack.
