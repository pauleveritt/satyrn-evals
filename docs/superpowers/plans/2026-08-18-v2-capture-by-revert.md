# V2 — Capture by revert: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `satyrn-evals capture --revert SHA [--repo PATH] [--name NAME] [--contract TEXT] [--output DIR]`: turn a real fixing commit into a task directory (manifest, base tree, known-good patch) whose four deterministic capture checks all pass — without changing pre-existing source files or the source repository's index, branch, or `HEAD`; declared writes below `--output` are the sole exception.

**Architecture:** Pure logic (NUL-safe Git metadata classification, discriminating-set computation, capture record, name derivation, manifest changes) lives in small single-purpose modules tested in the default tier; orchestration (`capture.py`) pins the commits, preflights a clean source, asks Git to render the selected fix patch, adds a detached worktree beneath a validated safe temporary parent, preserves the base tree, runs the oracle three times (base full-suite, fixed full-suite, recorded restricted) with hook evidence under that parent, cleans up with E3's precedence, and writes the capture record. Every owned Git command disables hooks and fsmonitor; cleanup state is conservative before add and determines the persisted, returned, and CLI result. The oracle hook gains collection-error recording so "the suite never ran" is distinguishable from "the suite is empty". The CLI gains the `capture` subcommand and `--tasks-root` on `grade`.

**Tech Stack:** Python 3.14, stdlib only in `src/` (argparse, dataclasses, json, subprocess, tempfile, re), pytest for tests, git for worktree/diff operations. No third-party dependencies.

**Spec:** `docs/superpowers/specs/2026-08-18-v2-capture-by-revert-design.md` — the plan argues from the spec; executors read both.

## Correction — 2026-08-19 (normative)

Review after implementation found twelve places where the original plan's
lifecycle and artifact examples were weaker than the approved guarantee. The
historical task steps and code excerpts remain below as the record of what was
planned; they must not be re-applied where they conflict with this correction.
An implementation or review of V2 uses these corrected rules:

1. `--output` is the declared artifact-write surface and the only exception
   to source immutability. Capture does not change any pre-existing source
   file or the source repository's index, branch, or `HEAD`.
2. The worktree-registration guard becomes `MAY_EXIST` immediately before
   the mutating `git worktree add`, not after a successful return. Cleanup
   resolves actual registration state, and the temporary parent is not
   deleted until absence is confirmed. This covers an add that registers the
   worktree and then reports failure.
3. Every Git invocation owned by capture uses both `-c
   core.hooksPath=/dev/null` and `-c core.fsmonitor=false`, ignores replace
   refs and legacy grafts, and strips repository-local routing variables.
   This includes discovery, pin, preflight, metadata, patch generation,
   apply, add/remove, and cleanup probes; the original `_git`/`_git_worktree`
   split is superseded.
4. The temporary parent is validated to be outside every registered worktree
   reported by Git. Worktree materialization and each unique,
   reserved-but-unlinked hook-result path live under that safe parent.
5. Cleanup failure replaces a pending success, refusal, or post-acceptance
   collision in all observable channels: the record on disk, the
   `CaptureRecord` returned by `capture()`, and the CLI outcome (exit 3)
   report `CLEANUP_FAILED`, with the displaced result and retained path in the
   message. Unexpected catchable exceptions retain their identity and receive
   cleanup notes. Merely rewriting the file from `finally` while returning the
   previously evaluated object is incorrect.
6. The pristine tree copy used for `base/` preserves tracked symbolic links
   (`copytree(..., symlinks=True)` or an equivalent Git-faithful copy), and
   the isolated POSIX checkout overrides `core.symlinks=false`.
7. Derivation first reads Git's NUL-delimited name-status metadata, including
   both old and new paths for renames/copies, and applies the test-path rule to
   both. Git itself then generates the patch for the selected paths with
   copy detection; the human-readable unified diff is not parsed and
   reassembled by capture. External diff drivers, textconv, and color are
   disabled. The grader recognizes Git's ordinary and extended patch forms
   and decodes quoted control/UTF-8 byte escapes before enforcing the source
   allowlist. Git output and patch artifacts preserve carriage returns, CRLF
   content, and filesystem path bytes without universal-newline conversion.
8. Source-local output is valid only in a subtree with no tracked paths; that
   declared artifact subtree is excluded from status, while the repository
   root, Git administrative directories, and tracked subtrees are rejected.
   This permits repeated captures without hiding dirty source. Containment is
   filesystem-aware, including symlink and case-insensitive aliases.
9. A task-directory or record collision is a usage error with no write. It
   cannot safely be a named refusal because writing that refusal would replace
   the evidence of the collision. Task rollback is ownership-gated and record
   publication is atomic, exclusive, and no-follow, including races and
   dangling symlinks. Historical `TASK_EXISTS` records still load.
10. After pin/name/output acceptance, Git spawn, oracle-result setup, and
    task-artifact write failures are mapped to `GIT_FAILED`, `ORACLE_ENV`, and
    `ARTIFACT_FAILED`. Pin failure and failure to create the record's output
    directory remain usage errors because no safe record channel exists.
    Resolving the first parent and reading the fixing commit subject are part
    of pinning and happen before name/output acceptance, so a Git invocation
    failure at either step is usage/no record. A successfully resolved root
    commit remains a recorded `NO_PARENT` refusal after acceptance.
11. Worktree creation overrides `core.sparseCheckout=true`; `base/` is the
    complete tracked tree at the pinned parent even when the caller uses a
    sparse checkout.
12. Cleanup precedence tracks only exceptions raised by capture itself. It
    does not inherit an exception already being handled by the caller or add
    cleanup notes to that unrelated exception.

Why this is a correction rather than a feature expansion: these rules close
gaps in guarantees the original plan already claimed—source-state isolation,
safe cleanup, hook suppression, faithful base materialization, and a durable,
authoritative result. The collision classification and `ARTIFACT_FAILED` code
make previously unsafe or unnamed failures explicit; the command syntax and
record fields are unchanged.

## Global Constraints

- Python `>=3.14,<3.15`; no runtime dependencies (`pyproject.toml`).
- Default tests use **no model, no network, no subprocess** — enforced by the audit-hook tripwire (V1 Task 1). Integration tests are marked `integration` and excluded by default; run them with `uv run pytest -m integration tests/integration/`.
- The verdict never comes from stdout or an exit code. Exit codes: `0` captured, `2` usage error, `3` refusal. The capture record's `code` is authoritative.
- Every refusal test has a sibling success test.
- Pre-existing source files and the source repository's index, branch, and
  `HEAD` are never changed. Declared artifacts below `--output` are the sole
  write exception; transient worktree registration is removed on cleanup.
- Before the mutating worktree add, registration is `MAY_EXIST`; the safe
  temporary parent is retained until registration absence is confirmed.
- Every owned Git command disables hooks and filesystem monitors with `-c
  core.hooksPath=/dev/null -c core.fsmonitor=false`.
- The temporary parent and hook-result paths are outside all registered
  worktrees; `base/` preserves symlinks; selected patches are rendered by Git
  from NUL-delimited old/new path metadata.
- `CLEANUP_FAILED` replaces the pending persisted record, returned record,
  and CLI result. It never leaves callers holding the displaced success or
  refusal.
- No subprocess spawn may happen during a default-tier test; weakening the tripwire fails the build.
- `ruff` and `pyrefly` run over `src/` and `tests/`; pyrefly must be verified from the main checkout at merge time (the `.worktrees/` gitignore pattern shadows `tests/` inside a worktree).
- Combined default and integration coverage over `satyrn_evals` must remain
  at 100% statements and branches; subprocess coverage is enabled for the
  real CLI and oracle evidence.
- **Repo-not-git, unborn, bad-SHA, invalid output, and artifact collisions are
  usage errors** (exit 2, no record). The last case cannot write a refusal
  without overwriting the artifact that caused it. Accepted-operation
  refusals (`REPO_DIRTY`, `NO_PARENT`, `NO_SOURCE_CHANGE`, `ORACLE_ENV`,
  `NO_DISCRIMINATING_TESTS`, `NOT_WINNABLE`, `GIT_FAILED`,
  `ARTIFACT_FAILED`, `CLEANUP_FAILED`) are exit 3 with a named record;
  historical `TASK_EXISTS` records remain readable.
- **Codes `NOT_WINNABLE` (check 4) and `ORACLE_ENV` (check 2)** are named in the spec's checks; the plan implements them verbatim.

---

### Task 1: Manifest — optional known_broken and provenance

**Files:**
- Modify: `src/satyrn_evals/manifest.py`
- Modify: `tests/test_manifest.py`

**Interfaces:**
- Consumes: `ManifestError` (existing), V1's manifest shape.
- Produces: `TaskManifest` gains `provenance: dict[str, str] | None` (default `None`); `load_manifest(task_dir)` accepts a manifest without `fixtures.known_broken` and with an optional `provenance` object (`repo`, `base_sha`, `fix_sha` — all non-empty strings); new helper `is_valid_task_name(name: str) -> bool` (the V1 `resolve_task` rule extracted); `resolve_task` refactored to use it with unchanged behavior.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_manifest.py`:

```python
def test_load_manifest_without_known_broken(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    del data["fixtures"]["known_broken"]
    (task_dir / "manifest.json").write_text(json.dumps(data))
    m = load_manifest(task_dir)
    assert "known_broken" not in m.fixtures
    assert m.provenance is None


def test_load_manifest_with_provenance(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["provenance"] = {"repo": "/src/app", "base_sha": "b" * 40, "fix_sha": "f" * 40}
    (task_dir / "manifest.json").write_text(json.dumps(data))
    m = load_manifest(task_dir)
    assert m.provenance == {"repo": "/src/app", "base_sha": "b" * 40, "fix_sha": "f" * 40}


def test_load_manifest_with_malformed_known_broken_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["fixtures"]["known_broken"] = ""
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="known_broken"):
        load_manifest(task_dir)


def test_load_manifest_with_malformed_provenance_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["provenance"] = {"repo": "/src/app"}
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="provenance"):
        load_manifest(task_dir)


def test_load_manifest_with_non_object_provenance_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["provenance"] = ["not", "an", "object"]
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="provenance"):
        load_manifest(task_dir)


def test_is_valid_task_name() -> None:
    assert is_valid_task_name("format_number")
    assert is_valid_task_name("a-b_c.1")


@pytest.mark.parametrize("name", ["", "../etc", "a/b", "a\\b", ".", ".."])
def test_is_valid_task_name_rejects(name: str) -> None:
    assert not is_valid_task_name(name)


def test_resolve_task_uses_same_rule(tmp_path) -> None:
    with pytest.raises(ManifestError, match="invalid task name"):
        resolve_task("../etc", tasks_root=tmp_path)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: FAIL — `is_valid_task_name` undefined (ImportError); provenance tests fail (field not present / no validation).

- [ ] **Step 3: Implement**

Edit `src/satyrn_evals/manifest.py`:

```python
@dataclass(frozen=True)
class TaskManifest:
    name: str
    contract: str
    oracle: tuple[str, ...]
    expected_test_ids: tuple[str, ...]
    source_paths: tuple[str, ...]
    fixtures: dict[str, str]
    provenance: dict[str, str] | None = None


def is_valid_task_name(name: str) -> bool:
    return Path(name).name == name and "/" not in name and "\\" not in name and name not in ("", ".", "..")
```

In `load_manifest`, replace the fixtures validation loop:

```python
    for key in ("known_good",):
        if not isinstance(fixtures.get(key), str) or not fixtures[key]:
            raise ManifestError(f"fixtures.{key} must be a non-empty path string")
    if "known_broken" in fixtures:
        broken = fixtures["known_broken"]
        if not isinstance(broken, str) or not broken:
            raise ManifestError("fixtures.known_broken must be a non-empty path string")
    provenance = data.get("provenance")
    if provenance is not None:
        if not isinstance(provenance, dict):
            raise ManifestError("provenance must be an object")
        if set(provenance) != {"repo", "base_sha", "fix_sha"}:
            raise ManifestError("provenance must have exactly repo, base_sha, fix_sha")
        if not all(
            isinstance(provenance[k], str) and provenance[k] for k in ("repo", "base_sha", "fix_sha")
        ):
            raise ManifestError("provenance fields must be non-empty strings")
```

Also in `load_manifest`, replace the `for key in ("known_good", "known_broken"):` fixture-file-existence loop with:

```python
    for key in ("known_good", "known_broken"):
        if key not in fixtures:
            continue
        if not (task_dir / fixtures[key]).is_file():
            raise ManifestError(f"fixture file missing: {fixtures[key]}")
```

And update the `return TaskManifest(...)` to pass `provenance=provenance`.

Refactor `resolve_task`:

```python
def resolve_task(name: str, tasks_root: Path = DEFAULT_TASKS_ROOT) -> Path:
    if not is_valid_task_name(name):
        raise ManifestError(f"invalid task name: {name}")
    task_dir = tasks_root / name
    if not task_dir.is_dir():
        raise ManifestError(f"unknown task: {name}")
    return task_dir
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_manifest.py -v`
Expected: all PASS. Then `uv run ruff check src/satyrn_evals/manifest.py tests/test_manifest.py` and `uv run pyrefly check` — clean.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/manifest.py tests/test_manifest.py
git commit -m "feat: manifest optional known_broken and provenance; extract name rule"
```

---

### Task 2: Oracle hook records collection errors

**Files:**
- Modify: `src/satyrn_evals/oracle_hook.py`
- Modify: `src/satyrn_evals/verdict.py`
- Modify: `tests/test_oracle_hook.py`
- Modify: `tests/test_verdict.py`

**Interfaces:**
- Consumes: `Outcome`, `HookResultData` from `verdict.py`; pytest hook functions.
- Produces: `oracle_hook._collect_errors: list[str]`; `pytest_collectreport(report)` accumulating `str(report.longrepr)` on failed collection; the hook JSON gains `collect_errors` (always a list, empty when none). `HookResult` gains `collect_errors: tuple[str, ...] = ()`; `load_hook_result` reads the field, defaulting to `()` when absent (V1 files still load); `HookResultData` gains `collect_errors: NotRequired[list[str]]`. V1's `compute_verdict` behavior is unchanged.

**Why:** without this, a missing dependency writes a valid-looking *empty* hook result and check 3 would misreport the task as ceiling-tied (`NO_DISCRIMINATING_TESTS`) when the truth is the suite never ran. The harvest index's "the number looked clean and was fabricated" trap.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_oracle_hook.py` — extend the fake report with `longrepr`:

```python
class FakeReport:
    def __init__(
        self, nodeid: str, when: str = "call", passed=False, failed=False, skipped=False,
        longrepr: str = "",
    ) -> None:
        self.nodeid = nodeid
        self.when = when
        self.passed = passed
        self.failed = failed
        self.skipped = skipped
        self.longrepr = longrepr
```

(Replace the existing `FakeReport` class and its construction helper `_report`; keep existing call sites working by giving `when` and the new `longrepr` defaults.)

Update the existing autouse `_clear_reports` fixture to clear the new module state too, or `test_hook_collect_errors_empty_by_default` will see stale errors from the previous test:

```python
@pytest.fixture(autouse=True)
def _clear_reports() -> None:
    oracle_hook._reports.clear()
    oracle_hook._collect_errors.clear()
    yield
    oracle_hook._reports.clear()
    oracle_hook._collect_errors.clear()
```

Add tests:

```python
def test_hook_records_collection_error(tmp_path, monkeypatch) -> None:
    result_path = tmp_path / "hook.json"
    monkeypatch.setenv(oracle_hook.RESULT_ENV, str(result_path))
    oracle_hook.pytest_collectreport(
        FakeReport("broken_import_test.py", failed=True, longrepr="ModuleNotFoundError: nope")
    )
    oracle_hook.pytest_sessionfinish(None, 2)
    data = json.loads(result_path.read_text())
    assert data["collect_errors"] == ["ModuleNotFoundError: nope"]
    assert data["executed_test_ids"] == []


def test_hook_collect_errors_empty_by_default(tmp_path, monkeypatch) -> None:
    result_path = tmp_path / "hook.json"
    monkeypatch.setenv(oracle_hook.RESULT_ENV, str(result_path))
    oracle_hook.pytest_runtest_logreport(_report("a::t1", passed=True))
    oracle_hook.pytest_sessionfinish(None, 0)
    data = json.loads(result_path.read_text())
    assert data["collect_errors"] == []
```

Append to `tests/test_verdict.py`:

```python
def test_load_hook_result_with_collect_errors(tmp_path) -> None:
    path = tmp_path / "hook.json"
    data = _hook_data([], {})
    data["collect_errors"] = ["ModuleNotFoundError: nope"]
    path.write_text(json.dumps(data))
    hook = load_hook_result(path, time.time() - 100)
    assert hook.collect_errors == ("ModuleNotFoundError: nope",)


def test_load_hook_result_absent_collect_errors_defaults_empty(tmp_path) -> None:
    path = tmp_path / "hook.json"
    path.write_text(json.dumps(_hook_data(["a"], {"a": "passed"})))
    hook = load_hook_result(path, time.time() - 100)
    assert hook.collect_errors == ()


def test_load_hook_result_non_list_collect_errors_rejected(tmp_path) -> None:
    path = tmp_path / "hook.json"
    data = _hook_data(["a"], {"a": "passed"})
    data["collect_errors"] = "nope"
    path.write_text(json.dumps(data))
    with pytest.raises(HookError, match="collect_errors"):
        load_hook_result(path, time.time() - 100)
```

Note: `_hook_data([], {})` must produce an empty executed set with all-zero counts — verify the existing helper produces `{"executed_test_ids": [], "outcomes": {}, "counts": {"passed": 0, "failed": 0, "error": 0, "skipped": 0}}` (it does: it sums over `outcomes.values()`).

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_oracle_hook.py tests/test_verdict.py -v`
Expected: FAIL — `collect_errors` missing from hook JSON, `HookResult` has no such field.

- [ ] **Step 3: Implement**

Edit `src/satyrn_evals/oracle_hook.py`:

```python
_reports: dict[str, Outcome] = {}
_collect_errors: list[str] = []


def pytest_collectreport(report) -> None:
    if report.failed:
        _collect_errors.append(str(report.longrepr))
```

In `pytest_sessionfinish`, extend the data dict:

```python
    data: HookResultData = {
        "executed_test_ids": sorted(_reports),
        "outcomes": dict(_reports),
        "counts": counts,
        "collect_errors": list(_collect_errors),
    }
```

Edit `src/satyrn_evals/verdict.py`:

```python
from typing import Literal, NotRequired, TypedDict


class HookResultData(TypedDict):
    executed_test_ids: list[str]
    outcomes: dict[str, Outcome]
    counts: dict[str, int]
    collect_errors: NotRequired[list[str]]
```

```python
@dataclass(frozen=True, slots=True)
class HookResult:
    executed_test_ids: tuple[str, ...]
    outcomes: dict[str, Outcome]
    counts: dict[str, int]
    collect_errors: tuple[str, ...] = ()
```

In `load_hook_result`, after the counts validation and before the `return`:

```python
    raw_errors = data.get("collect_errors", [])
    if not isinstance(raw_errors, list) or not all(isinstance(e, str) for e in raw_errors):
        raise HookError("collect_errors must be a list of strings")
    return HookResult(
        executed_test_ids=tuple(sorted(executed)),
        outcomes=dict(outcomes),
        counts=dict(counts),
        collect_errors=tuple(raw_errors),
    )
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_oracle_hook.py tests/test_verdict.py -v`
Expected: all PASS (including V1's existing hook and verdict tests). Then `uv run ruff check src/satyrn_evals/oracle_hook.py src/satyrn_evals/verdict.py tests/test_oracle_hook.py tests/test_verdict.py` and `uv run pyrefly check` — clean.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/oracle_hook.py src/satyrn_evals/verdict.py tests/test_oracle_hook.py tests/test_verdict.py
git commit -m "feat: oracle hook records collection errors; verdict reads them"
```

---

### Task 3: Test-path classification and hunk stripping

**Files:**
- Create: `src/satyrn_evals/diff_filter.py`
- Create: `tests/test_diff_filter.py`

**Interfaces:**
- Consumes: `PatchParseError` from `errors.py`.
- Produces: `FileSection(path: str, text: str)` dataclass; `split_file_sections(patch_text: str) -> tuple[FileSection, ...]` (raises `PatchParseError` on no sections or a malformed header); `is_test_path(path: str) -> bool` (the spec's rule: basename `test_*`, `*_test.py`, `conftest.py`, or any path component `tests`); `strip_test_hunks(patch_text: str) -> tuple[str, tuple[str, ...]]` returning (source-only patch text, source paths in order) — `("", ())` when every file is a test path.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_diff_filter.py`:

```python
import pytest

from satyrn_evals.diff_filter import (
    FileSection,
    is_test_path,
    split_file_sections,
    strip_test_hunks,
)
from satyrn_evals.errors import PatchParseError


def _patch(*sections: str) -> str:
    return "\n".join(sections) + "\n"


SOLUTION = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)
TEST_FILE = (
    "diff --git a/test_solution.py b/test_solution.py\n"
    "--- a/test_solution.py\n"
    "+++ b/test_solution.py\n"
    "@@ -1,2 +1,3 @@\n"
    " from solution import double\n"
    "+# regression test comment\n"
)
TESTS_DIR = (
    "diff --git a/tests/test_util.py b/tests/test_util.py\n"
    "--- a/tests/test_util.py\n"
    "+++ b/tests/test_util.py\n"
    "@@ -1 +1 @@\n"
    "-x\n"
    "+y\n"
)


def test_split_sections_single_file() -> None:
    sections = split_file_sections(SOLUTION)
    assert len(sections) == 1
    assert sections[0].path == "solution.py"
    assert sections[0].text.startswith("diff --git a/solution.py")


def test_split_sections_multiple_files() -> None:
    sections = split_file_sections(_patch(SOLUTION, TEST_FILE))
    assert [s.path for s in sections] == ["solution.py", "test_solution.py"]


def test_split_rejects_no_sections() -> None:
    with pytest.raises(PatchParseError, match="no file sections"):
        split_file_sections("@@ -1 +1 @@\n nothing\n")


def test_split_rejects_malformed_header() -> None:
    with pytest.raises(PatchParseError, match="malformed diff header"):
        split_file_sections("diff --git a/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-x\n+y\n")


@pytest.mark.parametrize(
    "path",
    ["test_solution.py", "tests/test_util.py", "a/tests/test_util.py", "conftest.py",
     "my_test.py", "test_thing.py"],
    ids=["test-prefix", "tests-dir", "nested-tests-dir", "conftest", "suffix", "prefix"],
)
def test_is_test_path_true(path: str) -> None:
    assert is_test_path(path)


@pytest.mark.parametrize(
    "path",
    ["solution.py", "src/app.py", "mytests.py", "setup.py", "tests_helpers.py"],
    ids=["solution", "src", "not-suffix", "setup", "prefix-not-test"],
)
def test_is_test_path_false(path: str) -> None:
    assert not is_test_path(path)


def test_strip_keeps_only_source_sections() -> None:
    text, paths = strip_test_hunks(_patch(SOLUTION, TEST_FILE, TESTS_DIR))
    assert paths == ("solution.py",)
    assert "test_solution.py" not in text
    assert "tests/test_util.py" not in text
    assert "solution.py" in text


def test_strip_all_test_paths_returns_empty() -> None:
    text, paths = strip_test_hunks(_patch(TEST_FILE, TESTS_DIR))
    assert text == ""
    assert paths == ()


def test_strip_preserves_source_ordering() -> None:
    text, paths = strip_test_hunks(_patch(TEST_FILE, SOLUTION, TESTS_DIR))
    assert paths == ("solution.py",)


def test_strip_handles_deleted_source_file() -> None:
    deleted = (
        "diff --git a/old.py b/old.py\n"
        "deleted file mode 100644\n"
        "--- a/old.py\n"
        "+++ /dev/null\n"
        "@@ -1 +0,0 @@\n"
        "-gone\n"
    )
    text, paths = strip_test_hunks(deleted)
    assert paths == ("old.py",)
    assert "old.py" in text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_diff_filter.py -v`
Expected: all FAIL with `ModuleNotFoundError: satyrn_evals.diff_filter`.

- [ ] **Step 3: Implement**

Create `src/satyrn_evals/diff_filter.py`:

```python
"""Unified-diff file-section splitting and the test-path rule.

Capture needs to strip hunks that touch test files from a fix diff: tests
stay at base, so the known-good patch may only touch source paths. This
module splits a unified diff into per-file sections, classifies each path
by the spec's test-path rule, and filters.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.errors import PatchParseError

_HEADER_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")


@dataclass(frozen=True, slots=True)
class FileSection:
    path: str
    text: str


def split_file_sections(patch_text: str) -> tuple[FileSection, ...]:
    """Split a unified diff into per-file sections, in order."""
    lines = patch_text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("diff --git ")]
    if not starts:
        raise PatchParseError("patch has no file sections")
    sections: list[FileSection] = []
    for j, start in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(lines)
        header = _HEADER_RE.match(lines[start])
        if not header:
            raise PatchParseError(f"malformed diff header: {lines[start]}")
        a_side, b_side = header.group(1), header.group(2)
        path = b_side if b_side != "/dev/null" else a_side
        if not path:
            raise PatchParseError(f"diff header names no file: {lines[start]}")
        sections.append(FileSection(path=path, text="\n".join(lines[start:end]) + "\n"))
    return tuple(sections)


def is_test_path(path: str) -> bool:
    """The spec's test-path rule: test_*, *_test.py, conftest.py, tests/ component."""
    parts = Path(path).parts
    if "tests" in parts:
        return True
    base = parts[-1]
    return base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py"


def strip_test_hunks(patch_text: str) -> tuple[str, tuple[str, ...]]:
    """Return (source-only patch text, source paths in order).

    Test-path sections are dropped. Every section a test path yields
    ("", ()), which the caller maps to the NO_SOURCE_CHANGE refusal.
    """
    sections = split_file_sections(patch_text)
    kept = [s for s in sections if not is_test_path(s.path)]
    return ("".join(s.text for s in kept), tuple(s.path for s in kept))
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_diff_filter.py -v`
Expected: all PASS. Then `uv run ruff check src/satyrn_evals/diff_filter.py tests/test_diff_filter.py` and `uv run pyrefly check` — clean.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/diff_filter.py tests/test_diff_filter.py
git commit -m "feat: diff file-section splitting and test-path rule"
```

---

### Task 4: Discriminating-set computation

**Files:**
- Create: `src/satyrn_evals/discriminating.py`
- Create: `tests/test_discriminating.py`

**Interfaces:**
- Consumes: `HookResult` from `verdict.py` (Task 2).
- Produces: `failing_ids(hook: HookResult) -> frozenset[str]` (outcomes `failed` or `error`); `discriminating_set(base: HookResult, fixed: HookResult) -> tuple[str, ...]` (sorted fail-at-base ∩ pass-with-fix); `recorded_oracle(ids: tuple[str, ...]) -> tuple[str, ...]` (`("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook", *ids)`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_discriminating.py`:

```python
import pytest

from satyrn_evals.discriminating import (
    discriminating_set,
    failing_ids,
    recorded_oracle,
)
from satyrn_evals.verdict import HookResult, Outcome


def _hook(outcomes: dict[str, Outcome]) -> HookResult:
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for outcome in outcomes.values():
        counts[outcome] += 1
    return HookResult(executed_test_ids=tuple(sorted(outcomes)), outcomes=dict(outcomes), counts=counts)


def test_failing_ids() -> None:
    hook = _hook({"a": "failed", "b": "error", "c": "passed", "d": "skipped"})
    assert failing_ids(hook) == frozenset({"a", "b"})


def test_discriminating_set() -> None:
    base = _hook({"a": "failed", "b": "failed", "c": "passed"})
    fixed = _hook({"a": "passed", "b": "failed", "c": "passed"})
    assert discriminating_set(base, fixed) == ("a",)


def test_discriminating_set_sorted() -> None:
    base = _hook({"z": "failed", "a": "failed"})
    fixed = _hook({"z": "passed", "a": "passed"})
    assert discriminating_set(base, fixed) == ("a", "z")


def test_discriminating_set_empty_is_refusal_case() -> None:
    base = _hook({"a": "failed"})
    fixed = _hook({"a": "failed"})  # fix did not move it
    assert discriminating_set(base, fixed) == ()


def test_discriminating_set_ignores_extra_fixed_tests() -> None:
    base = _hook({"a": "failed"})
    fixed = _hook({"a": "passed", "b": "passed"})  # b added by the fix, not at base
    assert discriminating_set(base, fixed) == ("a",)


def test_recorded_oracle() -> None:
    assert recorded_oracle(("a", "b")) == (
        "python",
        "-m",
        "pytest",
        "-p",
        "satyrn_evals.oracle_hook",
        "a",
        "b",
    )


def test_recorded_oracle_empty() -> None:
    assert recorded_oracle(()) == ("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_discriminating.py -v`
Expected: all FAIL with `ModuleNotFoundError: satyrn_evals.discriminating`.

- [ ] **Step 3: Implement**

Create `src/satyrn_evals/discriminating.py`:

```python
"""The discriminating set: test IDs that fail at base and pass with the fix.

A captured task's validity (BRIEF's "un-done at base, and winnable") is
proven by this set being non-empty and the recorded oracle passing it.
"""

from satyrn_evals.verdict import HookResult

FULL_SUITE_ORACLE: tuple[str, ...] = (
    "python",
    "-m",
    "pytest",
    "-p",
    "satyrn_evals.oracle_hook",
)


def failing_ids(hook: HookResult) -> frozenset[str]:
    return frozenset(i for i, o in hook.outcomes.items() if o in ("failed", "error"))


def discriminating_set(base: HookResult, fixed: HookResult) -> tuple[str, ...]:
    """Sorted IDs that fail at base and pass with the fix. Empty => refuse."""
    failing = failing_ids(base)
    passing = frozenset(i for i, o in fixed.outcomes.items() if o == "passed")
    return tuple(sorted(failing & passing))


def recorded_oracle(ids: tuple[str, ...]) -> tuple[str, ...]:
    """The manifest oracle: full-suite command with the discriminating IDs baked in."""
    return (*FULL_SUITE_ORACLE, *ids)
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_discriminating.py -v`
Expected: all PASS. Then `uv run ruff check src/satyrn_evals/discriminating.py tests/test_discriminating.py` and `uv run pyrefly check` — clean.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/discriminating.py tests/test_discriminating.py
git commit -m "feat: discriminating-set computation and recorded oracle"
```

---

### Task 5: Capture record

**Files:**
- Create: `src/satyrn_evals/capture_record.py`
- Create: `tests/test_capture_record.py`

**Interfaces:**
- Consumes: nothing new (stdlib only).
- Produces: `CaptureOutcome(StrEnum)` with `CAPTURED = "captured"`, `REFUSED = "refused"`; `CHECK_NAMES = ("source_preflight", "base_oracle", "un_done_at_base", "winnable")`; `CaptureRecord(version: int, outcome: CaptureOutcome, code: str, message: str, repo: str, base_sha: str | None, fix_sha: str | None, task_dir: str | None, oracle: tuple[str, ...] | None, expected_test_ids: tuple[str, ...] | None, check_outcomes: dict[str, str])` frozen slots dataclass; `write_capture_record(path: Path, record: CaptureRecord) -> None`; `load_capture_record(path: Path) -> CaptureRecord` (validates); `merge_cleanup_failure(pending: CaptureRecord, cleanup_message: str) -> CaptureRecord` — returns a copy with `code="CLEANUP_FAILED"`, `outcome` unchanged, `message=f"{cleanup_message}; displaced {pending.code}: {pending.message}"` (E3's precedence: cleanup failure replaces any pending result).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_capture_record.py`:

```python
import json

import pytest

from satyrn_evals.capture_record import (
    CHECK_NAMES,
    CaptureOutcome,
    CaptureRecord,
    load_capture_record,
    merge_cleanup_failure,
    write_capture_record,
)


def _captured() -> CaptureRecord:
    return CaptureRecord(
        version=1,
        outcome=CaptureOutcome.CAPTURED,
        code="OK",
        message="task captured",
        repo="/src/app",
        base_sha="b" * 40,
        fix_sha="f" * 40,
        task_dir="/tasks/app",
        oracle=("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook", "a"),
        expected_test_ids=("a",),
        check_outcomes={name: "passed" for name in CHECK_NAMES},
    )


def _refused() -> CaptureRecord:
    return CaptureRecord(
        version=1,
        outcome=CaptureOutcome.REFUSED,
        code="REPO_DIRTY",
        message="source tree dirty",
        repo="/src/app",
        base_sha=None,
        fix_sha=None,
        task_dir=None,
        oracle=None,
        expected_test_ids=None,
        check_outcomes={name: "not-run" for name in CHECK_NAMES},
    )


def test_write_captured_roundtrip(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _captured())
    data = json.loads(path.read_text())
    assert data["version"] == 1
    assert data["outcome"] == "captured"
    assert data["code"] == "OK"
    assert data["oracle"] == ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook", "a"]
    assert data["check_outcomes"]["winnable"] == "passed"
    assert load_capture_record(path) == _captured()


def test_write_refused_roundtrip(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    assert data["outcome"] == "refused"
    assert data["base_sha"] is None
    assert load_capture_record(path) == _refused()


def test_load_rejects_bad_outcome(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["outcome"] = "maybe"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outcome"):
        load_capture_record(path)


def test_load_rejects_bad_check_outcomes(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["check_outcomes"] = {"source_preflight": "passed"}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="check_outcomes"):
        load_capture_record(path)


def test_load_rejects_missing_required_field(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    del data["code"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="missing a field"):
        load_capture_record(path)


def test_merge_cleanup_failure_precedence() -> None:
    pending = _refused()
    merged = merge_cleanup_failure(pending, "cannot remove locked worktree /tmp/wt")
    assert merged.code == "CLEANUP_FAILED"
    assert merged.outcome is CaptureOutcome.REFUSED
    assert "displaced REPO_DIRTY" in merged.message
    assert "source tree dirty" in merged.message
    assert merged.task_dir is None


def test_merge_cleanup_failure_demotes_captured_to_refused() -> None:
    captured = _captured()
    merged = merge_cleanup_failure(captured, "cannot remove locked worktree /tmp/wt")
    assert merged.outcome is CaptureOutcome.REFUSED
    assert merged.code == "CLEANUP_FAILED"
    assert "displaced OK" in merged.message
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_capture_record.py -v`
Expected: all FAIL with `ModuleNotFoundError: satyrn_evals.capture_record`.

- [ ] **Step 3: Implement**

Create `src/satyrn_evals/capture_record.py`:

```python
"""The capture record: the durable artifact capture writes, E3-shaped.

Like V1's receipt, the record is the authoritative result; the CLI's exit
code is coarse by design. `merge_cleanup_failure` implements E3's
precedence: a cleanup failure replaces any pending result.
"""

import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path

CHECK_NAMES = ("source_preflight", "base_oracle", "un_done_at_base", "winnable")
_VALID_CHECK_STATES = ("passed", "failed", "not-run")


class CaptureOutcome(StrEnum):
    CAPTURED = "captured"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class CaptureRecord:
    version: int
    outcome: CaptureOutcome
    code: str
    message: str
    repo: str
    base_sha: str | None
    fix_sha: str | None
    task_dir: str | None
    oracle: tuple[str, ...] | None
    expected_test_ids: tuple[str, ...] | None
    check_outcomes: dict[str, str]


def write_capture_record(path: Path, record: CaptureRecord) -> None:
    path.write_text(json.dumps(asdict(record), indent=2) + "\n")


def load_capture_record(path: Path) -> CaptureRecord:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"cannot read capture record: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("capture record is not an object")
    try:
        outcome = CaptureOutcome(data["outcome"])
    except (KeyError, ValueError) as e:
        raise ValueError(f"bad outcome: {e}") from e
    check_outcomes = data.get("check_outcomes")
    if not isinstance(check_outcomes, dict):
        raise ValueError("check_outcomes must be an object")
    if set(check_outcomes) != set(CHECK_NAMES) or not all(
        v in _VALID_CHECK_STATES for v in check_outcomes.values()
    ):
        raise ValueError("check_outcomes must name all four checks as passed/failed/not-run")
    try:
        return CaptureRecord(
            version=data["version"],
            outcome=outcome,
            code=data["code"],
            message=data["message"],
            repo=data["repo"],
            base_sha=data.get("base_sha"),
            fix_sha=data.get("fix_sha"),
            task_dir=data.get("task_dir"),
            oracle=tuple(data["oracle"]) if data.get("oracle") is not None else None,
            expected_test_ids=tuple(data["expected_test_ids"])
            if data.get("expected_test_ids") is not None
            else None,
            check_outcomes=dict(check_outcomes),
        )
    except (KeyError, TypeError) as e:
        raise ValueError(f"capture record missing a field: {e}") from e


def merge_cleanup_failure(pending: CaptureRecord, cleanup_message: str) -> CaptureRecord:
    """CLEANUP_FAILED replaces any pending result (E3 precedence).

    The outcome becomes REFUSED even when the pending record was captured:
    a retained worktree means the operation did not fully complete.
    """
    return replace(
        pending,
        outcome=CaptureOutcome.REFUSED,
        code="CLEANUP_FAILED",
        message=f"{cleanup_message}; displaced {pending.code}: {pending.message}",
    )
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_capture_record.py -v`
Expected: all PASS. Then `uv run ruff check src/satyrn_evals/capture_record.py tests/test_capture_record.py` and `uv run pyrefly check` — clean.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/capture_record.py tests/test_capture_record.py
git commit -m "feat: E3-shaped capture record with cleanup-failure precedence"
```

---

### Task 6: Name derivation from the fix subject

**Files:**
- Create: `src/satyrn_evals/capture.py` (the `slugify_subject` function only in this task; orchestration lands in Task 7)
- Create: `tests/test_capture_logic.py`

**Interfaces:**
- Consumes: `is_valid_task_name` from `manifest.py` (Task 1).
- Produces: `slugify_subject(subject: str) -> str | None` — lowercase, runs of non-`[a-z0-9]` become `-`, stripped of leading/trailing `-`; `None` when the result is empty.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_capture_logic.py`:

```python
import pytest

from satyrn_evals.capture import slugify_subject
from satyrn_evals.manifest import is_valid_task_name


def test_slugify_subject() -> None:
    assert slugify_subject("Fix off-by-one in index computation") == "fix-off-by-one-in-index-computation"


def test_slugify_subject_handles_punctuation() -> None:
    assert slugify_subject("  Fix: double(n) returns n  ") == "fix-double-n-returns-n"


def test_slugify_subject_lowercases() -> None:
    assert slugify_subject("Add SortedSet") == "add-sortedset"


def test_slugify_subject_empty_is_none() -> None:
    assert slugify_subject("") is None
    assert slugify_subject("!!!") is None


def test_slugify_subject_result_is_valid_task_name() -> None:
    slug = slugify_subject("Fix the broken thing: part 2!")
    assert slug is not None
    assert is_valid_task_name(slug)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_capture_logic.py -v`
Expected: FAIL with `ModuleNotFoundError: satyrn_evals.capture`.

- [ ] **Step 3: Implement**

Create `src/satyrn_evals/capture.py`:

```python
"""Capture orchestration: turn a fixing commit into a valid task.

Task 6 defines `slugify_subject`; the full lifecycle lands with capture().
"""

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_subject(subject: str) -> str | None:
    """Task-name slug from a commit subject; None when underivable."""
    slug = _SLUG_RE.sub("-", subject.strip().lower()).strip("-")
    return slug or None
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_capture_logic.py -v`
Expected: all PASS. Then `uv run ruff check src/satyrn_evals/capture.py tests/test_capture_logic.py` and `uv run pyrefly check` — clean.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/capture.py tests/test_capture_logic.py
git commit -m "feat: task-name slug derivation from commit subject"
```

---

### Task 7: Capture orchestration, proven end-to-end

> **2026-08-19 correction:** The interfaces, tests, and implementation excerpt
> in this historical task predate the normative correction above. In
> particular, do not copy its post-success boolean registration guard,
> system-global hook-result temporary file, partial Git configuration,
> symlink-dereferencing `copytree`, Python-reassembled diff, or `finally`
> return behavior. The twelve corrected rules govern the implementation while
> preserving this excerpt as evidence of what was corrected.

**Files:**
- Modify: `src/satyrn_evals/capture.py` (add the lifecycle; keep `slugify_subject`)
- Create: `tests/integration/test_capture.py`
- Modify: `src/satyrn_evals/errors.py` (capture error classes)

**Interfaces:**
- Consumes: `is_valid_task_name`, `TaskManifest`, `load_manifest` (Task 1); `HookResult`, `load_hook_result`, `HookResultData` (Task 2); `split_file_sections`, `is_test_path`, `strip_test_hunks` (Task 3); `failing_ids`, `discriminating_set`, `recorded_oracle`, `FULL_SUITE_ORACLE` (Task 4); `CaptureRecord`, `CaptureOutcome`, `CHECK_NAMES`, `write_capture_record`, `merge_cleanup_failure` (Task 5); `slugify_subject` (Task 6); `RESULT_ENV` from `oracle_hook`.
- Produces: `capture(*, repo: Path, fix_sha: str, name: str | None, contract: str | None, output: Path) -> CaptureRecord` — writes the capture record always (accepted operation); writes the task directory on success; raises `CaptureUsageError` (exit 2, nothing written) for `REPO_NOT_GIT`, `REPO_UNBORN`, SHA-not-a-commit, invalid/underivable name. Errors added to `errors.py`:

```python
class CaptureUsageError(UsageError):
    pass


class CaptureRefused(SatyrnError):
    code: str = "GIT_FAILED"


class RepoDirty(CaptureRefused):
    code = "REPO_DIRTY"


class NoParent(CaptureRefused):
    code = "NO_PARENT"


class NoSourceChange(CaptureRefused):
    code = "NO_SOURCE_CHANGE"


class TaskExists(CaptureRefused):
    code = "TASK_EXISTS"


class OracleEnv(CaptureRefused):
    code = "ORACLE_ENV"


class NoDiscriminatingTests(CaptureRefused):
    code = "NO_DISCRIMINATING_TESTS"


class NotWinnable(CaptureRefused):
    code = "NOT_WINNABLE"


class GitFailed(CaptureRefused):
    code = "GIT_FAILED"


class CleanupFailed(CaptureRefused):
    code = "CLEANUP_FAILED"
```

- [ ] **Step 1: Write the failing integration tests**

Create `tests/integration/test_capture.py`. The fixture repository is a committed mini-repo built in a tmp dir: base has a buggy `double` with two failing tests; the fix commit corrects `double` *and* touches a test file (proving test-hunk stripping).

```python
"""End-to-end capture with a committed fixture repo. Real git, real oracle."""

import json
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.capture import capture
from satyrn_evals.capture_record import CaptureOutcome, load_capture_record
from satyrn_evals.errors import CaptureUsageError
from satyrn_evals.grade import grade
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

BASE_SOLUTION = "def double(n):\n    return n\n"
BASE_TESTS = (
    "from solution import double\n\n\n"
    "def test_double_positive():\n"
    "    assert double(3) == 6\n\n\n"
    "def test_double_five():\n"
    "    assert double(5) == 10\n"
)
FIXED_SOLUTION = "def double(n):\n    return n * 2\n"
# The fix also touches a test file: those hunks must be stripped from known-good.
FIXED_TESTS = BASE_TESTS + "\n\ndef test_double_negative():\n    assert double(-3) == -6\n"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True
    )


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    proc = _git(repo, "commit", "-q", "-m", message)
    assert proc.returncode == 0, proc.stderr


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> tuple[Path, str]:
    """A committed repo: base (buggy) then fix commit touching source + tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "solution.py").write_text(BASE_SOLUTION)
    (repo / "test_solution.py").write_text(BASE_TESTS)
    _commit(repo, "base: buggy double with failing tests")
    (repo / "solution.py").write_text(FIXED_SOLUTION)
    (repo / "test_solution.py").write_text(FIXED_TESTS)
    _commit(repo, "fix: double returns twice n")
    fix_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert _git(repo, "status", "--porcelain").stdout == ""
    return repo, fix_sha


def test_capture_succeeds_and_source_is_untouched(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    reflog_before = _git(repo, "reflog").stdout
    head_before = _git(repo, "rev-parse", "HEAD").stdout.strip()
    record = capture(repo=repo, fix_sha=fix_sha, name="double_task", contract=None, output=output)
    assert record.outcome is CaptureOutcome.CAPTURED
    assert record.code == "OK"
    assert record.expected_test_ids == (
        "test_solution.py::test_double_five",
        "test_solution.py::test_double_positive",
    )
    # source untouched: HEAD, reflog, clean status
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == head_before
    assert _git(repo, "reflog").stdout == reflog_before
    assert _git(repo, "status", "--porcelain").stdout == ""
    # no worktree registration remains
    assert "double_task" not in _git(repo, "worktree", "list").stdout
    # task artifacts
    task_dir = output / "double_task"
    manifest = json.loads((task_dir / "manifest.json").read_text())
    assert manifest["name"] == "double_task"
    assert manifest["provenance"] == {
        "repo": str(repo.resolve()),
        "base_sha": _git(repo, "rev-parse", f"{fix_sha}^").stdout.strip(),
        "fix_sha": fix_sha,
    }
    assert "known_broken" not in manifest["fixtures"]
    # known-good touches only source
    known_good = (task_dir / "fixtures" / "known-good.patch").read_text()
    assert "test_solution.py" not in known_good
    assert "solution.py" in known_good
    # base is the parent tree
    base_solution = (task_dir / "base" / "solution.py").read_text()
    assert base_solution == BASE_SOLUTION
    assert not (task_dir / "base" / ".git").exists()
    # record on disk
    loaded = load_capture_record(output / "double_task.capture.json")
    assert loaded == record


def test_captured_task_grades_pass_through_real_grade(fixture_repo, tmp_path) -> None:
    """The evidence floor for capture: known-good grades pass, fixture named."""
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    record = capture(repo=repo, fix_sha=fix_sha, name="double_task", contract=None, output=output)
    assert record.outcome is CaptureOutcome.CAPTURED
    task_dir = output / "double_task"
    receipt = tmp_path / "r.json"
    result = grade(task_dir, task_dir / "fixtures" / "known-good.patch", receipt)
    assert result.verdict is Verdict.PASS
    data = json.loads(receipt.read_text())
    assert data["verdict"] == "pass"
    assert data["evidence"]["counts"]["passed"] == 2


def test_dirty_source_is_refused(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    (repo / "solution.py").write_text(BASE_SOLUTION + "# dirty\n")
    output = tmp_path / "tasks"
    record = capture(repo=repo, fix_sha=fix_sha, name="double_task", contract=None, output=output)
    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "REPO_DIRTY"
    assert not (output / "double_task").exists()
    assert (output / "double_task.capture.json").exists()


def test_fix_touching_only_tests_is_refused(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "solution.py").write_text(BASE_SOLUTION)
    (repo / "test_solution.py").write_text(BASE_TESTS)
    _commit(repo, "base")
    (repo / "test_solution.py").write_text(BASE_TESTS + "# comment\n")
    _commit(repo, "fix: only tests changed")
    fix_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    record = capture(repo=repo, fix_sha=fix_sha, name="t", contract=None, output=tmp_path / "tasks")
    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "NO_SOURCE_CHANGE"


def test_fix_with_no_discriminating_tests_is_refused(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "solution.py").write_text(BASE_SOLUTION)
    (repo / "test_solution.py").write_text(BASE_TESTS)
    _commit(repo, "base")
    # fix changes source but not behavior: tests still fail at base and after
    (repo / "solution.py").write_text(BASE_SOLUTION + "# comment\n")
    _commit(repo, "fix: cosmetic source change")
    fix_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    record = capture(repo=repo, fix_sha=fix_sha, name="t", contract=None, output=tmp_path / "tasks")
    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "NO_DISCRIMINATING_TESTS"


def test_missing_oracle_environment_is_refused(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "solution.py").write_text(BASE_SOLUTION)
    (repo / "test_solution.py").write_text(
        "import does_not_exist_xyz\n\n\ndef test_nope():\n    assert True\n"
    )
    _commit(repo, "base")
    (repo / "solution.py").write_text(FIXED_SOLUTION)
    _commit(repo, "fix: fixes double")
    fix_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    record = capture(repo=repo, fix_sha=fix_sha, name="t", contract=None, output=tmp_path / "tasks")
    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "ORACLE_ENV"
    assert "does_not_exist_xyz" in record.message


def test_shorthand_sha_ok_and_bad_sha_is_usage(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    short = fix_sha[:8]
    record = capture(repo=repo, fix_sha=short, name="t", contract=None, output=tmp_path / "tasks")
    assert record.outcome is CaptureOutcome.CAPTURED
    with pytest.raises(CaptureUsageError):
        capture(repo=repo, fix_sha="deadbeef", name="t", contract=None, output=tmp_path / "tasks")


def test_locked_worktree_proves_cleanup_failed(fixture_repo, tmp_path) -> None:
    """A genuinely locked worktree makes git worktree remove fail; the record
    names the retained path and CLEANUP_FAILED; teardown unlocks and removes."""
    from satyrn_evals.capture import _cleanup_worktree
    from satyrn_evals.errors import CleanupFailed

    repo, _fix_sha = fixture_repo
    wt = tmp_path / "wt"
    empty_hooks = tmp_path / "empty-hooks"
    empty_hooks.mkdir()
    _git(repo, "worktree", "add", "--detach", str(wt), "HEAD")
    _git(repo, "worktree", "lock", str(wt))
    try:
        with pytest.raises(CleanupFailed, match="retained"):
            _cleanup_worktree(repo, wt, empty_hooks)
    finally:
        _git(repo, "worktree", "unlock", str(wt))
        _git(repo, "worktree", "remove", "--force", str(wt))


def test_hook_sentinel_does_not_fire(fixture_repo, tmp_path) -> None:
    """A post-checkout hook in the source repo must not fire during capture."""
    repo, fix_sha = fixture_repo
    sentinel = tmp_path / "hook-fired.txt"
    hook = repo / ".git" / "hooks" / "post-checkout"
    hook.write_text(f"#!/bin/sh\ntouch {sentinel}\n")
    hook.chmod(0o755)
    record = capture(repo=repo, fix_sha=fix_sha, name="t", contract=None, output=tmp_path / "tasks")
    assert record.outcome is CaptureOutcome.CAPTURED
    assert not sentinel.exists()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest -m integration tests/integration/test_capture.py -v`
Expected: FAIL with `ModuleNotFoundError: satyrn_evals.capture` (or attribute errors on `_cleanup_worktree`).

- [ ] **Step 3: Implement the capture lifecycle**

Extend `src/satyrn_evals/capture.py` (keep `slugify_subject`):

```python
"""Capture orchestration: turn a fixing commit into a valid task.

The lifecycle, re-earned from the satyrn-engine E3 delivery spec: pin the
commits, preflight a clean source, derive the fix diff, add a detached
worktree at the parent, materialize the base, run the oracle three times,
clean up with E3's precedence, and write the capture record. The source
repository's working tree, index, branch, and HEAD are never touched.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from satyrn_evals import oracle_hook
from satyrn_evals.capture_record import (
    CHECK_NAMES,
    CaptureOutcome,
    CaptureRecord,
    merge_cleanup_failure,
    write_capture_record,
)
from satyrn_evals.diff_filter import strip_test_hunks
from satyrn_evals.discriminating import FULL_SUITE_ORACLE, discriminating_set, recorded_oracle
from satyrn_evals.errors import (
    CaptureRefused,
    CaptureUsageError,
    CleanupFailed,
    GitFailed,
    HookError,
    NoDiscriminatingTests,
    NoParent,
    NoSourceChange,
    NotWinnable,
    OracleEnv,
    RepoDirty,
    TaskExists,
)
from satyrn_evals.manifest import is_valid_task_name
from satyrn_evals.verdict import HookResult, load_hook_result

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_subject(subject: str) -> str | None:
    """Task-name slug from a commit subject; None when underivable."""
    slug = _SLUG_RE.sub("-", subject.strip().lower()).strip("-")
    return slug or None


def _local_env_vars() -> set[str]:
    proc = subprocess.run(["git", "rev-parse", "--local-env-vars"], capture_output=True, text=True)
    names = set(proc.stdout.split()) if proc.returncode == 0 else set()
    names.add("GIT_NAMESPACE")
    return names


def _clean_env() -> dict[str, str]:
    """Child environment with repository-local routing variables stripped."""
    env = dict(os.environ)
    for name in _local_env_vars():
        env.pop(name, None)
    return env


def _git(root: Path, args: list[str], *, input_text: str | None = None) -> str:
    """Run git from the source root with stripped env; raise GitFailed."""
    env = _clean_env()
    proc = subprocess.run(
        ["git", *args], cwd=root, env=env, capture_output=True, text=True, input=input_text
    )
    if proc.returncode != 0:
        raise GitFailed(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _git_worktree(root: Path, args: list[str], empty_hooks: Path) -> str:
    """Git for worktree add/remove: hooksPath pointed at an engine-owned empty dir."""
    env = _clean_env()
    proc = subprocess.run(
        ["git", "-c", f"core.hooksPath={empty_hooks}", *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitFailed(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _run_oracle(worktree: Path, cmd: tuple[str, ...]) -> HookResult:
    """Run an oracle in the worktree; V1's hook-result machinery.

    A unique reserved-but-unlinked hook path, the run-start timestamp, and
    the stale-file rejection — the verdict never comes from stdout or an
    exit code. Raises OracleEnv when no hook result exists.
    """
    fd, hook_path = tempfile.mkstemp(prefix="satyrn-hook-", suffix=".json")
    os.close(fd)
    os.unlink(hook_path)
    env = _clean_env()
    env[oracle_hook.RESULT_ENV] = hook_path
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    run_started = time.time()
    try:
        subprocess.run(list(cmd), cwd=worktree, env=env, capture_output=True)
    except OSError as e:
        raise OracleEnv(f"oracle failed to start: {e}") from e
    try:
        return load_hook_result(Path(hook_path), run_started)
    except HookError as e:
        raise OracleEnv(str(e)) from e
    finally:
        Path(hook_path).unlink(missing_ok=True)


def _cleanup_worktree(root: Path, worktree: Path, empty_hooks: Path) -> None:
    """git worktree remove --force; raises CleanupFailed naming the path."""
    try:
        _git_worktree(root, ["worktree", "remove", "--force", str(worktree)], empty_hooks)
    except GitFailed as e:
        raise CleanupFailed(
            f"worktree cleanup failed; retained at {worktree}: {e}"
        ) from e


def capture(
    *,
    repo: Path,
    fix_sha: str,
    name: str | None,
    contract: str | None,
    output: Path,
) -> CaptureRecord:
    """Capture a fixing commit as a task; write the record; return it.

    Usage errors (REPO_NOT_GIT, REPO_UNBORN, SHA not a commit, invalid or
    underivable name) raise CaptureUsageError and write nothing. Refusals
    and success write a capture record; the CLI maps outcome to exit code.
    """
    repo_abs = str(Path(repo).resolve())
    output = Path(output)
    checks: dict[str, str] = {n: "not-run" for n in CHECK_NAMES}
    result: CaptureRecord | None = None
    tmp_root: Path | None = None
    worktree: Path | None = None
    worktree_registered = False
    base_sha = ""
    resolved_fix = ""

    def refused(code: str, message: str) -> CaptureRecord:
        nonlocal result
        record = CaptureRecord(
            version=1,
            outcome=CaptureOutcome.REFUSED,
            code=code,
            message=message,
            repo=repo_abs,
            base_sha=base_sha or None,
            fix_sha=resolved_fix or None,
            task_dir=None,
            oracle=None,
            expected_test_ids=None,
            check_outcomes=dict(checks),
        )
        write_capture_record(output / f"{name}.capture.json", record)
        result = record
        return record

    # Pin (usage errors here write nothing: no task name exists yet)
    try:
        root = Path(_git(repo, ["rev-parse", "--show-toplevel"]).strip())
    except GitFailed:
        raise CaptureUsageError(f"not a git repository: {repo_abs}")
    try:
        _git(root, ["rev-parse", "--verify", "--quiet", "HEAD^{commit}"])
    except GitFailed:
        raise CaptureUsageError(f"repository has no commits: {repo_abs}")
    try:
        resolved_fix = _git(
            root, ["rev-parse", "--verify", "--quiet", f"{fix_sha}^{{commit}}"]
        ).strip()
    except GitFailed:
        raise CaptureUsageError(f"not a commit in the repository: {fix_sha}")
    try:
        base_sha = _git(
            root, ["rev-parse", "--verify", "--quiet", f"{resolved_fix}^"]
        ).strip()
    except GitFailed:
        # NO_PARENT is a refusal, not usage: the fix resolved, so a name
        # exists and the record is named (spec check 1).
        pass
    subject = _git(root, ["log", "-1", "--format=%s", resolved_fix]).strip()
    if name is None:
        slug = slugify_subject(subject)
        if slug is None or not is_valid_task_name(slug):
            raise CaptureUsageError(f"cannot derive a task name from subject: {subject!r}")
        name = slug
    elif not is_valid_task_name(name):
        raise CaptureUsageError(f"invalid task name: {name}")
    if contract is None:
        contract = subject
    output.mkdir(parents=True, exist_ok=True)
    task_dir = output / name

    try:
        # TASK_EXISTS is a refusal before checks begin (name exists now)
        if task_dir.exists() or (output / f"{name}.capture.json").exists():
            return refused("TASK_EXISTS", f"task already exists: {name}")
        # Preflight (check 1)
        checks["source_preflight"] = "passed"
        try:
            status = _git(
                root,
                [
                    "--no-optional-locks", "status", "--porcelain=v1", "-z",
                    "--untracked-files=all", "--ignore-submodules=none",
                ],
            )
            if status:
                raise RepoDirty("source repository is dirty")
            if not base_sha:
                raise NoParent(f"fix has no parent (root commit): {resolved_fix}")
            fix_diff = _git(root, ["diff", f"{base_sha}..{resolved_fix}"])
            source_text, source_paths = strip_test_hunks(fix_diff)
            if not source_paths:
                raise NoSourceChange("fix touches only test paths")
        except CaptureRefused as e:
            checks["source_preflight"] = "failed"
            raise
        except GitFailed as e:
            checks["source_preflight"] = "failed"
            raise GitFailed(str(e)) from e

        # Derive
        known_good_text = source_text

        # Worktree + materialize + verify
        tmp_root = Path(tempfile.mkdtemp(prefix="satyrn-capture-"))
        empty_hooks = tmp_root / "empty-hooks"
        empty_hooks.mkdir()
        worktree = tmp_root / "worktree"
        _git_worktree(
            root, ["worktree", "add", "--detach", str(worktree), base_sha], empty_hooks
        )
        worktree_registered = True
        base_staging = tmp_root / "base"
        shutil.copytree(worktree, base_staging, ignore=shutil.ignore_patterns(".git"))
        # check 2: full-suite base run
        base_hook = _run_oracle(worktree, FULL_SUITE_ORACLE)
        if base_hook.collect_errors:
            checks["base_oracle"] = "failed"
            raise OracleEnv(f"base oracle did not run: {base_hook.collect_errors[0]}")
        checks["base_oracle"] = "passed"
        # apply known-good in the worktree
        _git(worktree, ["apply", "-"], input_text=known_good_text)
        # check 3: full-suite fixed run, discriminating set
        fixed_hook = _run_oracle(worktree, FULL_SUITE_ORACLE)
        if fixed_hook.collect_errors:
            checks["un_done_at_base"] = "failed"
            raise NotWinnable(f"fixed oracle did not run: {fixed_hook.collect_errors[0]}")
        ids = discriminating_set(base_hook, fixed_hook)
        if not ids:
            checks["un_done_at_base"] = "failed"
            raise NoDiscriminatingTests(
                "no tests fail at base and pass with the fix (task at or near ceiling)"
            )
        checks["un_done_at_base"] = "passed"
        # check 4: recorded restricted oracle passes every discriminating ID
        oracle_cmd = recorded_oracle(ids)
        restricted_hook = _run_oracle(worktree, oracle_cmd)
        if restricted_hook.collect_errors:
            checks["winnable"] = "failed"
            raise NotWinnable(
                f"recorded oracle did not run: {restricted_hook.collect_errors[0]}"
            )
        failing = set(
            i for i, o in restricted_hook.outcomes.items() if o in ("failed", "error", "skipped")
        ) | (set(ids) - set(restricted_hook.executed_test_ids))
        if failing:
            checks["winnable"] = "failed"
            raise NotWinnable(f"recorded oracle did not pass: failing {sorted(failing)}")
        checks["winnable"] = "passed"
        # write task dir
        task_dir.mkdir(parents=True)
        (task_dir / "fixtures").mkdir()
        shutil.move(str(base_staging), str(task_dir / "base"))
        (task_dir / "fixtures" / "known-good.patch").write_text(known_good_text)
        manifest = {
            "name": name,
            "contract": contract,
            "oracle": list(oracle_cmd),
            "expected_test_ids": list(ids),
            "source_paths": list(source_paths),
            "fixtures": {"known_good": "fixtures/known-good.patch"},
            "provenance": {
                "repo": str(Path(repo).resolve()),
                "base_sha": base_sha,
                "fix_sha": resolved_fix,
            },
        }
        (task_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        record = CaptureRecord(
            version=1,
            outcome=CaptureOutcome.CAPTURED,
            code="OK",
            message="task captured",
            repo=repo_abs,
            base_sha=base_sha,
            fix_sha=resolved_fix,
            task_dir=str(task_dir),
            oracle=oracle_cmd,
            expected_test_ids=ids,
            check_outcomes=dict(checks),
        )
        write_capture_record(output / f"{name}.capture.json", record)
        result = record
        return record
    except CaptureRefused as e:
        return refused(e.code, str(e))
    except GitFailed as e:
        return refused("GIT_FAILED", str(e))
    finally:
        if worktree is not None and worktree_registered and tmp_root is not None:
            try:
                _cleanup_worktree(root, worktree, tmp_root / "empty-hooks")
                worktree_registered = False
            except CleanupFailed as ce:
                # cleanup failure replaces any pending result (E3 precedence);
                # the guard STAYS True so the retained worktree and its temp
                # root survive for the manual recovery in the record message
                if result is not None:
                    write_capture_record(
                        output / f"{name}.capture.json",
                        merge_cleanup_failure(result, str(ce)),
                    )
                else:
                    refused("CLEANUP_FAILED", str(ce))
        if tmp_root is not None and not worktree_registered:
            shutil.rmtree(tmp_root, ignore_errors=True)
```

**Note on the `finally` block:** when cleanup fails, the worktree path is
retained *and the temp root is kept* — the record's message names the
retained path for the documented manual recovery (`git worktree unlock
PATH`, `git worktree remove --force PATH`, `git worktree prune`). A
cleanup failure replaces any pending result — even a captured one — via
`merge_cleanup_failure` (E3's precedence), because a retained worktree
means the operation did not fully complete.

**Correction (2026-08-19):** the excerpt above does not fully implement that
precedence: Python evaluates its pending `return` before `finally`, so rewriting
the file alone can still return the displaced object and produce the wrong CLI
exit. The corrected control flow defers return until cleanup has produced the
final record. Its registration state is `MAY_EXIST` before `worktree add`, and
the temporary parent survives until Git confirms registration is absent.

**Note on `_run_oracle`:** `load_hook_result` raises `HookError` (missing,
stale, unparseable) — the oracle-runner above surfaces it as `OracleEnv`
so check 2 (and the fixed/restricted runs) refuse with a named code
instead of an unhandled exception.

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest -m integration tests/integration/test_capture.py -v`
Expected: all PASS (capture succeeds; source untouched; known-good grades `pass`; dirty/all-test/no-discriminating/missing-env refusals with their codes; shorthand SHA works and bad SHA is usage; locked worktree proves `CLEANUP_FAILED` via `_cleanup_worktree`; hook sentinel does not fire).

- [ ] **Step 5: Full verification and commit**

Run:
```bash
uv run pytest
uv run pytest -m integration tests/integration/
uv run ruff check .
```
Expected: default tier green (tripwire active), integration tier green, ruff clean. Pyrefly from the main checkout (recorded worktree caveat in Global Constraints).

```bash
git add src/satyrn_evals/capture.py src/satyrn_evals/errors.py tests/integration/test_capture.py
git commit -m "feat: capture orchestration with detached worktree and four checks"
```

---

### Task 8: CLI — capture subcommand and grade --tasks-root

**Files:**
- Modify: `src/satyrn_evals/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/integration/test_capture.py` (one CLI-level test appended)

**Interfaces:**
- Consumes: `capture` (Task 7), `resolve_task`, `DEFAULT_TASKS_ROOT` (Task 1), `SatyrnError`, `CaptureUsageError` (Task 7), `Verdict`, `grade` (V1).
- Produces: `main(argv: list[str] | None = None) -> int` with the `capture` subcommand and `--tasks-root` on `grade`; console script unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py`:

```python
def test_capture_requires_revert() -> None:
    with pytest.raises(SystemExit):
        main(["capture"])


def test_grade_tasks_root_unknown_task_is_usage(tmp_path) -> None:
    assert main(["grade", "--tasks-root", str(tmp_path), "no_such_task", "x.patch"]) == 2
```

Append to `tests/integration/test_capture.py`:

```python
def test_capture_cli_success_and_refusal(fixture_repo, tmp_path) -> None:
    from satyrn_evals.cli import main

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    code = main(
        [
            "capture", "--revert", fix_sha, "--repo", str(repo),
            "--name", "cli_task", "--output", str(output),
        ]
    )
    assert code == 0
    record = load_capture_record(output / "cli_task.capture.json")
    assert record.outcome is CaptureOutcome.CAPTURED
    # refusal path: dirty source with a DISTINCT name (TASK_EXISTS is
    # checked before the dirty check, per the spec's refusal ordering)
    (repo / "solution.py").write_text(BASE_SOLUTION + "# dirty\n")
    code = main(
        [
            "capture", "--revert", fix_sha, "--repo", str(repo),
            "--name", "cli_task_dirty", "--output", str(output),
        ]
    )
    assert code == 3
    record = load_capture_record(output / "cli_task_dirty.capture.json")
    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "REPO_DIRTY"
    # usage path: SHA names nothing — exit 2, nothing written
    before = sorted(p.name for p in output.iterdir())
    code = main(
        ["capture", "--revert", "deadbeef", "--repo", str(repo), "--name", "cli_task", "--output", str(output)]
    )
    assert code == 2
    assert sorted(p.name for p in output.iterdir()) == before
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_cli.py -v` — the new tests FAIL (no `capture` subcommand, no `--tasks-root`).
Run: `uv run pytest -m integration tests/integration/test_capture.py -k cli -v` — FAIL.

- [ ] **Step 3: Implement**

Edit `src/satyrn_evals/cli.py`:

```python
"""Console entry point: satyrn-evals grade and capture."""

import argparse
import sys
from pathlib import Path

from satyrn_evals.capture import capture
from satyrn_evals.capture_record import CaptureOutcome
from satyrn_evals.errors import SatyrnError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, resolve_task
from satyrn_evals.verdict import Verdict

_EXIT_CODES: dict[Verdict, int] = {Verdict.PASS: 0, Verdict.FAIL: 0, Verdict.UNAVAILABLE: 3}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="satyrn-evals",
        description="Offline grading and task capture for development tasks.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    grade_p = sub.add_parser("grade", help="apply PATCH to TASK and record the verdict")
    grade_p.add_argument("task", help="bundled task name")
    grade_p.add_argument("patch", help="unified diff file")
    grade_p.add_argument(
        "--receipt", default="receipt.json", help="receipt path (default: receipt.json)"
    )
    grade_p.add_argument(
        "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
    )

    capture_p = sub.add_parser(
        "capture", help="turn a fixing commit into a task (winnable by construction)"
    )
    capture_p.add_argument("--revert", required=True, help="the fixing commit SHA")
    capture_p.add_argument("--repo", default=".", help="source repository (default: cwd)")
    capture_p.add_argument("--name", help="task name (default: slug of the fix subject)")
    capture_p.add_argument("--contract", help="task contract (default: fix subject)")
    capture_p.add_argument("--output", default="tasks", help="output directory (default: ./tasks)")

    args: argparse.Namespace = parser.parse_args(argv)
    try:
        if args.command == "grade":
            task_dir = resolve_task(args.task, tasks_root=Path(args.tasks_root))
            receipt = grade(task_dir, Path(args.patch), Path(args.receipt))
            return _EXIT_CODES[receipt.verdict]
        record = capture(
            repo=Path(args.repo),
            fix_sha=args.revert,
            name=args.name,
            contract=args.contract,
            output=Path(args.output),
        )
        return 0 if record.outcome is CaptureOutcome.CAPTURED else 3
    except SatyrnError as e:
        print(f"satyrn-evals: {e}", file=sys.stderr)
        return e.exit_code
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_cli.py -v` — all PASS.
Run: `uv run pytest -m integration tests/integration/test_capture.py -v` — all PASS.
Run: `uv sync && uv run satyrn-evals --help && uv run satyrn-evals capture --help && uv run satyrn-evals grade --help` — each prints usage, exit 0.
Then `uv run ruff check .` — clean.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/cli.py tests/test_cli.py tests/integration/test_capture.py
git commit -m "feat: capture subcommand and grade --tasks-root"
```

---

### Task 9: Docs, glossary, roadmap

**Files:**
- Modify: `docs/usage.md` (capture command, exit codes, the capture record; `grade --tasks-root`)
- Modify: `docs/architecture.md` (capture data flow, the four checks, modules table)
- Modify: `docs/glossary.md` (provenance, capture record, discriminating set)
- Modify: `README.md` (usage snippet, status: V2 complete)
- Modify: `ROADMAP.md` (V2 complete; move to Prior work; check the concept budget)
- Modify: `docs/superpowers/index.md` (V2 cycle's spec and plan are picked up by the glob toctrees — verify no edit needed)

**Interfaces:**
- Consumes: everything above.
- Produces: the docs that match the shipped CLI; the roadmap records V2 as complete with its spec and plan linked.

- [ ] **Step 1: Update usage and architecture**

In `docs/usage.md`, add a `capture` section after the `grade` section:

```markdown
## capture

Turn a real fixing commit in a repository into a {term}`task` — manifest,
base state, and a known-good {term}`patch` — winnable by construction, in
minutes. The task's base is the fix's parent tree; the known-good patch is
the fix diff restricted to non-test source paths; the {term}`oracle`
runs only the tests that fail at base and pass with the fix.

```console
satyrn-evals capture --revert SHA [--repo PATH] [--name NAME] [--contract TEXT] [--output DIR]
```

- `--revert SHA` — the fixing commit. Required.
- `--repo PATH` — the source repository; default: the current directory. Its
  working tree, index, branch, and `HEAD` are never touched.
- `--name NAME` — the task directory name; default: a slug of the fix
  commit's subject line.
- `--contract TEXT` — the task statement; default: the fix subject line.
- `--output DIR` — where the task directory is written; default `./tasks/`.

Four deterministic checks run during capture; a failed check refuses with
a precise `code` in the {term}`capture record`. Exit codes: `0` captured,
`2` usage error, `3` refusal.
```

Update the `grade` section to mention `--tasks-root`, and add a capture-record
example. In `docs/architecture.md`, add the capture data flow (source repo →
pin → preflight → derive → worktree → materialize → verify → cleanup →
record), the four checks, and the new modules to the modules table.

- [ ] **Step 2: Update the glossary**

Add to `docs/glossary.md` (concept budget check: each term earned its place):

```{glossary}
capture record
  The durable artifact {term}`capture` writes: version, outcome
  (`captured`/`refused`), a precise `code`, message, repo and SHAs, task
  directory, the recorded {term}`oracle`, the {term}`discriminating set`,
  and the four checks' outcomes. E3-shaped; the exit code is coarse by
  design.

discriminating set
  The test IDs that fail at base and pass with the fix — the captured
  task's {term}`oracle` runs exactly these, and they are its expected test
  IDs. Non-empty proves the task is un-done at base; the four checks prove
  it is winnable.

provenance
  The manifest's `repo`, `base_sha`, and `fix_sha` — where a captured
  {term}`task` came from. Names what re-derivation of the environment and
  future diagnosis need.
```

(Insert the `capture` and `capture record` cross-references in the existing
entries' wording where natural.)

- [ ] **Step 3: Update README and roadmap**

In `README.md`, update the usage snippet to show `capture` and move V2 into
the Status section:

```markdown
- [_V2_](https://github.com/pauleveritt/satyrn-evals/tree/v2) — capture by
  revert. `satyrn-evals capture --revert SHA` turns a fixing commit into a
  task winnable by construction, in minutes, without touching the source
  repository's working tree.
  ([_spec_](https://github.com/pauleveritt/satyrn-evals/blob/main/docs/superpowers/specs/2026-08-18-v2-capture-by-revert-design.md),
  [_plan_](https://github.com/pauleveritt/satyrn-evals/blob/main/docs/superpowers/plans/2026-08-18-v2-capture-by-revert.md))
```

In `ROADMAP.md`, move V2 from `## Now` to `## Prior work`, updating the
concept budget note: provenance, capture record, and discriminating set
are now defined in the glossary.

- [ ] **Step 4: Verify the docs build and commit**

Run:
```bash
uv run --group docs sphinx-build -W -b html docs docs/_build/html
```
Expected: clean build with no warnings-as-errors. Then:

```bash
git add docs/usage.md docs/architecture.md docs/glossary.md README.md ROADMAP.md
git commit -m "docs: V2 capture usage, architecture, glossary, roadmap"
```

---

## Done-when (V2)

- `uv run pytest` — green, no subprocess spawned (tripwire active), integration excluded.
- `uv run pytest -m integration tests/integration/` — green; capture of the
  fixture repo's fix succeeds (four checks pass, source untouched) and the
  captured task's `known-good.patch` grades `pass` through the real `grade`
  command, each asserted by naming the fixture.
- `uv run coverage erase`; run default and integration tests separately under
  `coverage run`; then `uv run coverage combine` and `uv run coverage report`
  — 100% statement and branch coverage. Do not use `--append`: subprocess
  coverage writes parallel data files for `coverage combine`.
- `uv run ruff check .` and `uv run pyrefly check` (from the main checkout)
  — clean.
- `uv run --group docs sphinx-build -W -b html docs docs/_build/html` — clean.
- `uv run satyrn-evals capture --revert <sha> --repo <fixture-repo> --output /tmp/tasks; echo $?` — exit 0; `/tmp/tasks/<name>.capture.json` reads `outcome: captured`.

## Revisions

- **2026-08-19 — Capture isolation and evidence correction (normative).** The
  original plan overstated source read-only behavior without naming
  `--output` as the sole declared write, armed cleanup only after worktree-add
  success, disabled hooks only for add/remove and did not disable fsmonitor,
  placed hook results outside an independently validated safe parent,
  rewrote only the on-disk record on cleanup failure, dereferenced symlinks in
  `base/`, and parsed/reassembled human-readable diffs using only one path per
  change. The Correction section above records the replacements: output-only
  writes; a pre-add `MAY_EXIST` guard and confirmed-absence deletion gate;
  `/dev/null` hooks, disabled fsmonitor, and raw-object ancestry for every
  owned Git command; a temporary parent outside every registered worktree
  holding worktree and hook evidence; cleanup precedence for
  persisted/API/CLI results; Git-faithful symlink materialization; NUL old/new
  metadata plus byte-preserving Git-generated patches; filesystem-aware,
  repeatable source-local output; ownership-gated task rollback and atomic
  exclusive record publication; and named operational write failures.
  Worktree creation also disables sparse checkout so `base/` is complete,
  and exception precedence uses capture-local state rather than the caller's
  active exception context.
  Recorded rather than editing the historical task excerpt away.

- **2026-08-18 — Task 7 fixture defect (recorded).** The plan's fixture
  `test_double_zero` asserted `double(0) == 0`, which the buggy `return n`
  satisfies at base — a degenerate test that passes before the fix. The
  discriminating set therefore contained only `test_double_positive`, and
  the evidence-floor grade passed 1 of 2. Fixed by renaming to
  `test_double_five` (`double(5) == 10`), which fails at base and passes
  with the fix. Recorded rather than edited away.

- **2026-08-18 — Task 6 test typing defect (recorded).** The plan's
  `test_slugify_subject_result_is_valid_task_name` passed
  `slugify_subject(...)` (typed `str | None`) directly to
  `is_valid_task_name(name: str)` — pyrefly rejected it on the merged
  tree (the worktree's gitignore shadow had masked `tests/`). Fixed by
  asserting the slug is not `None` first. Recorded rather than edited
  away; merge verification on main is what surfaced it.
