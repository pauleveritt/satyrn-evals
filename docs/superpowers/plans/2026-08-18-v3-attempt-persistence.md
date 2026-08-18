# V3 — Attempt persistence: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `satyrn-evals attempt TASK [--tasks-root DIR] [--output DIR] -- COMMAND...`: run an attempt command against a task's base state, preserve its patch and transcript *before* cleanup, grade the delivered patch offline, and write both a receipt and an attempt record — in one invocation, with the command's exit code never trusted.

**Architecture:** The attempt command runs in a disposable workspace (a plain temp copy of the task's `base/` — no git worktree in V3) and reports through reserved env-var paths (`SATYRN_ATTEMPT_PATCH`, `SATYRN_ATTEMPT_TRANSCRIPT`) inside a freshly-created attempt directory, so a silent command leaves no file. Pure decision logic (the refusal decision, attempt-directory naming) lives in `attempt.py` and is tested in the default tier; the attempt record is a small dataclass module mirroring the capture record; orchestration (`attempt()`) runs the command, reads the delivered artifacts, refuses on incomplete preservation, then calls the existing `grade()` on the delivered patch; the CLI splits `argv` at the first `--` itself (argparse `REMAINDER` swallows options after `TASK` — verified) and maps the record's outcome/verdict to a coarse exit code.

**Tech Stack:** Python 3.14, stdlib only in `src/` (argparse, dataclasses, json, subprocess, tempfile, datetime, hashlib), pytest for tests. No third-party dependencies.

**Spec:** `docs/superpowers/specs/2026-08-18-v3-attempt-persistence-design.md` — the plan argues from the spec; executors read both.

## Global Constraints

- Python `>=3.14,<3.15`; no runtime dependencies (`pyproject.toml`).
- Default tests use **no model, no network, no subprocess** — enforced by the audit-hook tripwire in `tests/conftest.py`. Integration tests are marked `integration` and excluded by default; run them with `uv run pytest -m integration`.
- The verdict never comes from stdout or an exit code. Exit codes: `0` attempted and graded (verdict `pass`/`fail`), `2` usage error (unknown task, missing/empty command, command cannot start), `3` refusal or verdict `unavailable`. The attempt record's `outcome`/`code` and the receipt's `verdict` are authoritative; `command_exit` is recorded but never trusted.
- Every refusal test has a sibling success test.
- The seam env vars: `SATYRN_TASK_NAME`, `SATYRN_TASK_CONTRACT` (inputs), `SATYRN_ATTEMPT_PATCH`, `SATYRN_ATTEMPT_TRANSCRIPT` (outputs, reserved-but-never-created).
- Refusal is **preservation** failure (`NO_PATCH`, `PATCH_INVALID`, `TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY` — no receipt); `unavailable` is **grading** failure (apply fail, non-allowlisted path, no hook result — via `grade()`, receipt names the cause). Do not blur this line.
- The delivered patch (the file at `SATYRN_ATTEMPT_PATCH`) is what gets graded, never a diff of the workspace.
- `grade.py`, `receipt.py`, `manifest.py`, `patch.py`, `verdict.py`, `capture.py`, `capture_record.py`, `oracle_hook.py`, and `errors.py` are **unchanged** (attempt reuses `UsageError`/`ManifestError`; refusals return records, not exceptions).
- `ruff` and `pyrefly` must be clean at each commit: `uv run ruff check .` and `uv run pyrefly check`.
- A usage error (command cannot start) must remove the now-empty attempt directory so nothing is written.

---

### Task 1: Attempt record — `attempt_record.py`

The durable artifact `attempt` writes, parallel to the capture record. Pure module, default-tier tested.

**Files:**
- Create: `src/satyrn_evals/attempt_record.py`
- Test: `tests/test_attempt_record.py` (new)

**Interfaces:**
- Consumes: `Verdict` (existing, `src/satyrn_evals/verdict.py`).
- Produces:
  - `class AttemptOutcome(StrEnum)`: `ATTEMPTED = "attempted"`, `REFUSED = "refused"`
  - `@dataclass(frozen=True, slots=True) class AttemptRecord`: `version: int`, `outcome: AttemptOutcome`, `code: str`, `message: str`, `task: str`, `command: tuple[str, ...]`, `command_exit: int`, `patch_path: str | None`, `transcript_path: str | None`, `patch_digest: str | None`, `transcript_digest: str | None`, `verdict: Verdict | None`, `receipt_path: str | None`
  - `write_attempt_record(path: Path, record: AttemptRecord) -> None`
  - `load_attempt_record(path: Path) -> AttemptRecord` (raises `ValueError` on a malformed file)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_attempt_record.py`:

```python
import json

import pytest

from satyrn_evals.attempt_record import (
    AttemptOutcome,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.verdict import Verdict


def _attempted() -> AttemptRecord:
    return AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code="OK",
        message="attempt recorded and graded",
        task="format_number",
        command=("fake_attempt.py", "--good"),
        command_exit=0,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest="a" * 64,
        transcript_digest="b" * 64,
        verdict=Verdict.PASS,
        receipt_path="receipt.json",
    )


def _refused() -> AttemptRecord:
    return AttemptRecord(
        version=1,
        outcome=AttemptOutcome.REFUSED,
        code="NO_PATCH",
        message="attempt refused: NO_PATCH",
        task="format_number",
        command=("fake_attempt.py", "--no-patch"),
        command_exit=0,
        patch_path=None,
        transcript_path="transcript.txt",
        patch_digest=None,
        transcript_digest="b" * 64,
        verdict=None,
        receipt_path=None,
    )


def test_write_attempted_roundtrip(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _attempted())
    data = json.loads(path.read_text())
    assert data["version"] == 1
    assert data["outcome"] == "attempted"
    assert data["code"] == "OK"
    assert data["command"] == ["fake_attempt.py", "--good"]
    assert data["command_exit"] == 0
    assert data["verdict"] == "pass"
    assert load_attempt_record(path) == _attempted()


def test_write_refused_roundtrip(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    assert data["outcome"] == "refused"
    assert data["patch_path"] is None
    assert data["patch_digest"] is None
    assert data["verdict"] is None
    assert data["receipt_path"] is None
    assert load_attempt_record(path) == _refused()


def test_load_rejects_bad_outcome(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    data["outcome"] = "maybe"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outcome"):
        load_attempt_record(path)


def test_load_rejects_bad_verdict(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _attempted())
    data = json.loads(path.read_text())
    data["verdict"] = "maybe"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="verdict"):
        load_attempt_record(path)


def test_load_rejects_missing_required_field(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    del data["code"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="missing a field"):
        load_attempt_record(path)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_attempt_record.py -v`
Expected: collection error — `attempt_record` does not exist.

- [ ] **Step 3: Implement `attempt_record.py`**

Create `src/satyrn_evals/attempt_record.py`:

```python
"""The attempt record: the durable artifact attempt writes, E3-shaped.

Parallel to the capture record: the exit code stays coarse; the record is
precise. It references the receipt by path and repeats the verdict at top
level.
"""

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from satyrn_evals.verdict import Verdict


class AttemptOutcome(StrEnum):
    ATTEMPTED = "attempted"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    version: int
    outcome: AttemptOutcome
    code: str
    message: str
    task: str
    command: tuple[str, ...]
    command_exit: int
    patch_path: str | None
    transcript_path: str | None
    patch_digest: str | None
    transcript_digest: str | None
    verdict: Verdict | None
    receipt_path: str | None


def write_attempt_record(path: Path, record: AttemptRecord) -> None:
    path.write_text(json.dumps(asdict(record), indent=2) + "\n")


def load_attempt_record(path: Path) -> AttemptRecord:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"cannot read attempt record: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("attempt record is not an object")
    try:
        outcome = AttemptOutcome(data["outcome"])
    except (KeyError, ValueError) as e:
        raise ValueError(f"bad outcome: {e}") from e
    try:
        verdict = Verdict(data["verdict"]) if data.get("verdict") is not None else None
    except (KeyError, ValueError) as e:
        raise ValueError(f"bad verdict: {e}") from e
    try:
        return AttemptRecord(
            version=data["version"],
            outcome=outcome,
            code=data["code"],
            message=data["message"],
            task=data["task"],
            command=tuple(data["command"]),
            command_exit=data["command_exit"],
            patch_path=data.get("patch_path"),
            transcript_path=data.get("transcript_path"),
            patch_digest=data.get("patch_digest"),
            transcript_digest=data.get("transcript_digest"),
            verdict=verdict,
            receipt_path=data.get("receipt_path"),
        )
    except (KeyError, TypeError) as e:
        raise ValueError(f"attempt record missing a field: {e}") from e
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_attempt_record.py -v`
Expected: all 5 pass.

- [ ] **Step 5: Verify toolchain, then commit**

```bash
uv run pytest
uv run ruff check .
uv run pyrefly check
git add src/satyrn_evals/attempt_record.py tests/test_attempt_record.py
git commit -m "feat: attempt record shape with write/read"
```

---

### Task 2: Pure decisions — refusal codes and directory naming

`decide_refusal` and `attempt_dir_name` are pure functions in `attempt.py`, default-tier tested (no subprocess). This task also defines the seam env-var constants and a stub-free `attempt.py` skeleton; the orchestration function arrives in Task 3.

**Files:**
- Create: `src/satyrn_evals/attempt.py` (pure parts only; Task 3 adds `attempt()`)
- Test: `tests/test_attempt.py` (new)

**Interfaces:**
- Consumes: `parse_patch_paths` (existing, `src/satyrn_evals/patch.py`), `PatchParseError` (existing, `src/satyrn_evals/errors.py`).
- Produces:
  - Constants: `TASK_NAME_ENV = "SATYRN_TASK_NAME"`, `TASK_CONTRACT_ENV = "SATYRN_TASK_CONTRACT"`, `PATCH_ENV = "SATYRN_ATTEMPT_PATCH"`, `TRANSCRIPT_ENV = "SATYRN_ATTEMPT_TRANSCRIPT"`
  - `decide_refusal(patch_text: str | None, transcript_text: str | None) -> str | None` — an input of `None` means the file was absent; a return of `None` means no refusal (proceed to grade); otherwise one of `"NO_PATCH"`, `"PATCH_INVALID"`, `"TRANSCRIPT_MISSING"`, `"TRANSCRIPT_EMPTY"`.
  - `attempt_dir_name(task: str, when: datetime) -> str` — `<task>-<UTC microsecond timestamp>` (requires a tz-aware `when`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_attempt.py`:

```python
from datetime import datetime, timezone

from satyrn_evals.attempt import attempt_dir_name, decide_refusal

GOOD_PATCH = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)
TRANSCRIPT = "read the task; wrote the fix\n"


def test_valid_artifacts_proceed() -> None:
    assert decide_refusal(GOOD_PATCH, TRANSCRIPT) is None


def test_missing_patch_is_no_patch() -> None:
    assert decide_refusal(None, TRANSCRIPT) == "NO_PATCH"


def test_empty_patch_is_no_patch() -> None:
    assert decide_refusal("", TRANSCRIPT) == "NO_PATCH"


def test_whitespace_patch_is_no_patch() -> None:
    assert decide_refusal("   \n", TRANSCRIPT) == "NO_PATCH"


def test_non_diff_patch_is_patch_invalid() -> None:
    assert decide_refusal("this is not a unified diff\n", TRANSCRIPT) == "PATCH_INVALID"


def test_missing_transcript_is_transcript_missing() -> None:
    assert decide_refusal(GOOD_PATCH, None) == "TRANSCRIPT_MISSING"


def test_empty_transcript_is_transcript_empty() -> None:
    assert decide_refusal(GOOD_PATCH, "") == "TRANSCRIPT_EMPTY"


def test_whitespace_transcript_is_transcript_empty() -> None:
    assert decide_refusal(GOOD_PATCH, "  \n") == "TRANSCRIPT_EMPTY"


def test_patch_checked_before_transcript() -> None:
    # both bad: patch fails first (spec: patch checks run first)
    assert decide_refusal(None, None) == "NO_PATCH"
    assert decide_refusal("not a diff\n", None) == "PATCH_INVALID"


def test_attempt_dir_name_is_deterministic_given_when() -> None:
    when = datetime(2026, 8, 18, 14, 15, 23, 123456, tzinfo=timezone.utc)
    assert attempt_dir_name("format_number", when) == "format_number-20260818-141523-123456"


def test_attempt_dir_name_changes_with_when() -> None:
    a = attempt_dir_name("t", datetime(2026, 8, 18, 14, 15, 23, 1, tzinfo=timezone.utc))
    b = attempt_dir_name("t", datetime(2026, 8, 18, 14, 15, 23, 2, tzinfo=timezone.utc))
    assert a != b
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_attempt.py -v`
Expected: collection error — `attempt` module does not exist.

- [ ] **Step 3: Implement the pure parts of `attempt.py`**

Create `src/satyrn_evals/attempt.py` (only the pure parts; `attempt()` lands in Task 3, and only the imports the pure functions use):

```python
"""Attempt orchestration: run a command through the engine seam, preserve
its patch and transcript, grade the delivered patch offline, and record.

The pure decision logic (refusal codes, directory naming) lives here so the
default test tier can exercise it without spawning anything. The seam is
env-var paths: SATYRN_TASK_NAME/CONTRACT are inputs; SATYRN_ATTEMPT_PATCH/
TRANSCRIPT are where the command writes its delivery.
"""

from datetime import datetime, timezone

from satyrn_evals.errors import PatchParseError
from satyrn_evals.patch import parse_patch_paths

TASK_NAME_ENV = "SATYRN_TASK_NAME"
TASK_CONTRACT_ENV = "SATYRN_TASK_CONTRACT"
PATCH_ENV = "SATYRN_ATTEMPT_PATCH"
TRANSCRIPT_ENV = "SATYRN_ATTEMPT_TRANSCRIPT"

REFUSAL_CODES = ("NO_PATCH", "PATCH_INVALID", "TRANSCRIPT_MISSING", "TRANSCRIPT_EMPTY")


def decide_refusal(patch_text: str | None, transcript_text: str | None) -> str | None:
    """Refusal code when the delivered artifacts are incomplete; None to proceed.

    An input of None means the file was absent. Patch checks run first, then
    transcript checks (spec: "the first failure refuses").
    """
    if not patch_text or not patch_text.strip():
        return "NO_PATCH"
    try:
        parse_patch_paths(patch_text)
    except PatchParseError:
        return "PATCH_INVALID"
    if transcript_text is None:
        return "TRANSCRIPT_MISSING"
    if not transcript_text.strip():
        return "TRANSCRIPT_EMPTY"
    return None


def attempt_dir_name(task: str, when: datetime) -> str:
    """Attempt directory name: <task>-<UTC microsecond timestamp>."""
    stamp = when.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return f"{task}-{stamp}"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_attempt.py -v`
Expected: all 11 pass.

- [ ] **Step 5: Verify toolchain, then commit**

```bash
uv run pytest
uv run ruff check .
uv run pyrefly check
git add src/satyrn_evals/attempt.py tests/test_attempt.py
git commit -m "feat: refusal decision and attempt dir naming"
```

---

### Task 3: Orchestration `attempt()` + fake fixture + integration tests

The full attempt flow. Integration tier only (real subprocess, real oracle). The failing tests are the integration suite; the fixture is the fake command.

**Files:**
- Modify: `src/satyrn_evals/attempt.py` (add `attempt()`)
- Create: `tests/integration/fake_attempt.py` (the fixture command)
- Test: `tests/integration/test_attempt.py` (new, `pytestmark = pytest.mark.integration`)

**Interfaces:**
- Consumes: `AttemptRecord`, `AttemptOutcome`, `write_attempt_record` (Task 1); `decide_refusal`, `attempt_dir_name`, env constants (Task 2); `grade`, `patch_digest`, `load_manifest`, `resolve_task`, `UsageError` (existing).
- Produces:
  - `attempt(*, task: str, tasks_root: Path, output: Path, command: list[str]) -> AttemptRecord` — raises `UsageError` for an empty command or a command that cannot start (and removes the attempt dir on start failure); returns a refused record (no receipt) or an attempted record (receipt written via `grade()`).

- [ ] **Step 1: Write the failing integration tests and the fixture**

Create `tests/integration/fake_attempt.py`:

```python
"""Fake attempt command: honors the env seam for integration tests.

Writes the patch to SATYRN_ATTEMPT_PATCH and the transcript to
SATYRN_ATTEMPT_TRANSCRIPT, then exits. A test double, not a real engine —
it exercises the seam end-to-end without any model or network.

Flags:
  --patch FILE        copy FILE's content to the patch path
  --transcript TEXT   transcript content (default: "fake attempt ran")
  --exit N            process exit code (default: 0)
  --no-patch          write nothing to the patch path
  --bad-patch         write non-diff text to the patch path
  --no-transcript     write nothing to the transcript path
  --empty-transcript  write an empty transcript
"""

import argparse
import os
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--patch")
    p.add_argument("--transcript", default="fake attempt ran")
    p.add_argument("--exit", type=int, default=0)
    p.add_argument("--no-patch", action="store_true")
    p.add_argument("--bad-patch", action="store_true")
    p.add_argument("--no-transcript", action="store_true")
    p.add_argument("--empty-transcript", action="store_true")
    args = p.parse_args()

    patch_path = os.environ.get("SATYRN_ATTEMPT_PATCH")
    if patch_path and not args.no_patch:
        if args.bad_patch:
            Path(patch_path).write_text("this is not a unified diff\n")
        elif args.patch:
            Path(patch_path).write_bytes(Path(args.patch).read_bytes())

    transcript_path = os.environ.get("SATYRN_ATTEMPT_TRANSCRIPT")
    if transcript_path and not args.no_transcript:
        text = "" if args.empty_transcript else args.transcript
        Path(transcript_path).write_text(text)

    sys.exit(args.exit)


if __name__ == "__main__":
    main()
```

Create `tests/integration/test_attempt.py`:

```python
"""End-to-end attempt: a fake command through the seam. Real subprocess, real oracle."""

import json
import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptOutcome, load_attempt_record
from satyrn_evals.errors import UsageError
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.receipt import patch_digest
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

FAKE = Path(__file__).parent / "fake_attempt.py"
KNOWN_GOOD = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"
KNOWN_BROKEN = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-broken.patch"


def _cmd(*args: str) -> list[str]:
    return [sys.executable, str(FAKE), *args]


def _attempt_dir(output: Path) -> Path:
    dirs = [p for p in output.iterdir() if p.is_dir()]
    assert len(dirs) == 1, dirs
    return dirs[0]


def test_known_good_attempt_grades_pass(tmp_path: Path) -> None:
    """Evidence floor: the delivered known-good patch grades pass, fixture named."""
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_GOOD), "--transcript", "wrote the fix"),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.code == "OK"
    assert record.verdict is Verdict.PASS
    attempt_dir = _attempt_dir(output)
    assert (attempt_dir / "patch.diff").read_bytes() == KNOWN_GOOD.read_bytes()
    assert record.patch_digest == patch_digest(KNOWN_GOOD.read_bytes())
    assert record.receipt_path == "receipt.json"
    receipt = json.loads((attempt_dir / "receipt.json").read_text())
    assert receipt["verdict"] == "pass"
    assert receipt["patch_digest"] == record.patch_digest
    assert load_attempt_record(attempt_dir / "attempt.json") == record


def test_known_broken_attempt_grades_fail(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_BROKEN)),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.FAIL


def test_no_patch_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--no-patch"),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "NO_PATCH"
    attempt_dir = _attempt_dir(output)
    assert not (attempt_dir / "patch.diff").exists()
    assert (attempt_dir / "transcript.txt").exists()  # transcript still persisted
    assert not (attempt_dir / "receipt.json").exists()


def test_invalid_patch_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--bad-patch"),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "PATCH_INVALID"


def test_no_transcript_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_GOOD), "--no-transcript"),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "TRANSCRIPT_MISSING"
    attempt_dir = _attempt_dir(output)
    assert (attempt_dir / "patch.diff").exists()  # patch still persisted
    assert not (attempt_dir / "transcript.txt").exists()


def test_empty_transcript_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_GOOD), "--empty-transcript"),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "TRANSCRIPT_EMPTY"


def test_nonzero_exit_still_graded(tmp_path: Path) -> None:
    """Artifact-driven: a nonzero exit with valid artifacts is still attempted + graded."""
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_GOOD), "--exit", "7"),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.PASS
    assert record.command_exit == 7


def test_non_allowlisted_patch_is_unavailable(tmp_path: Path) -> None:
    bad = tmp_path / "touches-tests.patch"
    bad.write_text(
        "diff --git a/test_solution.py b/test_solution.py\n"
        "--- a/test_solution.py\n"
        "+++ b/test_solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " from solution import format_number\n"
        "+# tampered\n"
    )
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(bad)),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.UNAVAILABLE
    receipt = json.loads((_attempt_dir(output) / "receipt.json").read_text())
    assert "non-source" in receipt["reason"]


def test_unappliable_patch_is_unavailable(tmp_path: Path) -> None:
    bad = tmp_path / "no-apply.patch"
    bad.write_text(
        "diff --git a/solution.py b/solution.py\n"
        "--- a/solution.py\n"
        "+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def double(n):\n"
        "-    return n + 999\n"
        "+    return n * 2\n"
    )
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(bad)),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.UNAVAILABLE
    receipt = json.loads((_attempt_dir(output) / "receipt.json").read_text())
    assert "apply" in receipt["reason"]


def test_command_not_found_is_usage_error(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    with pytest.raises(UsageError, match="cannot start"):
        attempt(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=output,
            command=["definitely-not-a-real-command-xyz-123"],
        )
    # usage writes nothing: the attempt directory was removed again
    assert not any(output.iterdir())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -m integration tests/integration/test_attempt.py -v`
Expected: collection error — `from satyrn_evals.attempt import attempt` fails (no `attempt` symbol yet).

- [ ] **Step 3: Implement `attempt()`**

Append to `src/satyrn_evals/attempt.py` (replacing the Task-2 note about unused imports — these imports are now used; add the new imports below the existing ones):

Add to the import block (this is the complete final import set for `attempt.py` — stdlib block, then `satyrn_evals` block, alphabetical):

```python
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from satyrn_evals.attempt_record import AttemptOutcome, AttemptRecord, write_attempt_record
from satyrn_evals.errors import PatchParseError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.receipt import patch_digest
```

(The Task-2 block already has `from datetime import datetime, timezone` and `from satyrn_evals.errors import PatchParseError` / `from satyrn_evals.patch import parse_patch_paths`; merge, don't duplicate.)

Append the function:

```python
def attempt(
    *,
    task: str,
    tasks_root: Path,
    output: Path,
    command: list[str],
) -> AttemptRecord:
    """Run COMMAND against TASK, preserve patch + transcript, grade, and record.

    Usage errors (unknown task, empty command, command cannot start) raise
    UsageError and write nothing — a start failure also removes the
    freshly-created attempt directory. Refusals and successes write an
    attempt record; the CLI maps outcome/verdict to an exit code.
    """
    task_dir = resolve_task(task, tasks_root)
    manifest = load_manifest(task_dir)
    if not command:
        raise UsageError("attempt command is empty")
    output.mkdir(parents=True, exist_ok=True)
    attempt_dir = output / attempt_dir_name(manifest.name, datetime.now(timezone.utc))
    attempt_dir.mkdir()
    patch_path = attempt_dir / "patch.diff"
    transcript_path = attempt_dir / "transcript.txt"

    env = dict(os.environ)
    env[TASK_NAME_ENV] = manifest.name
    env[TASK_CONTRACT_ENV] = manifest.contract
    env[PATCH_ENV] = str(patch_path)
    env[TRANSCRIPT_ENV] = str(transcript_path)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")

    with tempfile.TemporaryDirectory(prefix="satyrn-attempt-") as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(task_dir / "base", work)
        try:
            proc = subprocess.run(command, cwd=work, env=env, capture_output=True)
        except OSError as e:
            shutil.rmtree(attempt_dir, ignore_errors=True)  # usage writes nothing
            raise UsageError(f"attempt command cannot start: {e}") from e
    command_exit = proc.returncode

    patch_bytes = patch_path.read_bytes() if patch_path.exists() else None
    transcript_bytes = transcript_path.read_bytes() if transcript_path.exists() else None
    patch_text = patch_bytes.decode("utf-8", errors="replace") if patch_bytes is not None else None
    transcript_text = (
        transcript_bytes.decode("utf-8", errors="replace") if transcript_bytes is not None else None
    )
    patch_hash = patch_digest(patch_bytes) if patch_bytes is not None else None
    transcript_hash = patch_digest(transcript_bytes) if transcript_bytes is not None else None

    code = decide_refusal(patch_text, transcript_text)
    if code is not None:
        record = AttemptRecord(
            version=1,
            outcome=AttemptOutcome.REFUSED,
            code=code,
            message=f"attempt refused: {code}",
            task=manifest.name,
            command=tuple(command),
            command_exit=command_exit,
            patch_path="patch.diff" if patch_bytes is not None else None,
            transcript_path="transcript.txt" if transcript_bytes is not None else None,
            patch_digest=patch_hash,
            transcript_digest=transcript_hash,
            verdict=None,
            receipt_path=None,
        )
        write_attempt_record(attempt_dir / "attempt.json", record)
        return record

    receipt = grade(task_dir, patch_path, attempt_dir / "receipt.json")
    record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code="OK",
        message="attempt recorded and graded",
        task=manifest.name,
        command=tuple(command),
        command_exit=command_exit,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest=patch_hash,
        transcript_digest=transcript_hash,
        verdict=receipt.verdict,
        receipt_path="receipt.json",
    )
    write_attempt_record(attempt_dir / "attempt.json", record)
    return record
```

> Note: `patch_hash`/`transcript_hash` are computed once up front (before `decide_refusal`), so both the refused and attempted branches use them without re-hashing and without type-narrowing games. The receipt's `patch_digest` and the record's `patch_digest` both hash the persisted `patch.diff` — one source, no drift.

- [ ] **Step 4: Run the integration tests to verify they pass**

Run: `uv run pytest -m integration tests/integration/test_attempt.py -v`
Expected: all 11 pass (known-good, known-broken, four refusals, artifact-driven exit, two unavailables, usage).

- [ ] **Step 5: Verify the default tier is still green and the tripwire holds**

```bash
uv run pytest
uv run ruff check .
uv run pyrefly check
```

Expected: default suite passes (the tripwire proves the integration tests are the only spawners).

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/attempt.py tests/integration/fake_attempt.py tests/integration/test_attempt.py
git commit -m "feat: attempt orchestration preserves patch + transcript and grades offline"
```

---

### Task 4: CLI — attempt subcommand, `--` splitting, exit codes

The CLI splits `argv` at the first `--` itself (argparse `REMAINDER` swallows options after `TASK` — verified empirically), then hands the flags to argparse and the remainder to `attempt()`.

**Files:**
- Modify: `src/satyrn_evals/cli.py`
- Modify: `tests/test_cli.py` (default-tier additions)
- Modify: `tests/integration/test_attempt.py` (add the CLI end-to-end test)

**Interfaces:**
- Consumes: `attempt()` (Task 3), `AttemptOutcome` (Task 1), `UsageError` (existing), `Verdict` (existing).
- Produces:
  - `split_attempt_argv(argv: list[str]) -> tuple[list[str], list[str]]` — `argv` is everything after the `attempt` token; returns `(flags, command)` where `command` is everything after the first `--` (empty when there is no `--`).
  - `main(argv)` handles the `attempt` subcommand: exit `0` attempted+graded, `2` usage, `3` refusal or unavailable.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py` (imports: add `split_attempt_argv` to the existing `from satyrn_evals.cli import main` line):

```python
def test_attempt_split_keeps_flags_and_command() -> None:
    flags, command = split_attempt_argv(["t", "--tasks-root", "R", "--", "cmd", "--flag", "x"])
    assert flags == ["t", "--tasks-root", "R"]
    assert command == ["cmd", "--flag", "x"]


def test_attempt_split_without_dashdash_has_no_command() -> None:
    flags, command = split_attempt_argv(["t", "--tasks-root", "R"])
    assert flags == ["t", "--tasks-root", "R"]
    assert command == []


def test_attempt_missing_command_is_usage() -> None:
    assert main(["attempt", "t"]) == 2


def test_attempt_unknown_task_is_usage(tmp_path) -> None:
    assert (
        main(
            [
                "attempt",
                "--tasks-root",
                str(tmp_path),
                "no_such_task",
                "--",
                "echo",
                "hi",
            ]
        )
        == 2
    )
```

Append to `tests/integration/test_attempt.py` (imports: add `from satyrn_evals.cli import main`):

```python
def test_attempt_cli_success_refusal_and_usage(tmp_path: Path) -> None:
    ok_output = tmp_path / "ok"
    code = main(
        [
            "attempt",
            "--tasks-root", str(DEFAULT_TASKS_ROOT),
            "--output", str(ok_output),
            "format_number",
            "--", sys.executable, str(FAKE), "--patch", str(KNOWN_GOOD),
        ]
    )
    assert code == 0
    record = load_attempt_record(_attempt_dir(ok_output) / "attempt.json")
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.PASS

    refused_output = tmp_path / "refused"
    code = main(
        [
            "attempt",
            "--tasks-root", str(DEFAULT_TASKS_ROOT),
            "--output", str(refused_output),
            "format_number",
            "--", sys.executable, str(FAKE), "--no-patch",
        ]
    )
    assert code == 3
    record = load_attempt_record(_attempt_dir(refused_output) / "attempt.json")
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "NO_PATCH"

    usage_output = tmp_path / "usage"
    code = main(
        [
            "attempt",
            "--tasks-root", str(DEFAULT_TASKS_ROOT),
            "--output", str(usage_output),
            "format_number",
            "--", "definitely-not-a-real-command-xyz-123",
        ]
    )
    assert code == 2
    assert not any(usage_output.iterdir())
```

- [ ] **Step 2: Run the tests to verify they fail**

Default tier: `uv run pytest tests/test_cli.py -v` — expected: import error (`split_attempt_argv` does not exist).
Integration: `uv run pytest -m integration tests/integration/test_attempt.py -v` — expected: `test_attempt_cli_success_refusal_and_usage` fails (no `main` handling of `attempt` yet).

- [ ] **Step 3: Implement the CLI**

Rewrite `src/satyrn_evals/cli.py`:

```python
"""Console entry point: satyrn-evals grade, capture, and attempt."""

import argparse
import sys
from pathlib import Path

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptOutcome
from satyrn_evals.capture import capture
from satyrn_evals.capture_record import CaptureOutcome
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, resolve_task
from satyrn_evals.verdict import Verdict

_EXIT_CODES: dict[Verdict, int] = {Verdict.PASS: 0, Verdict.FAIL: 0, Verdict.UNAVAILABLE: 3}


def split_attempt_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split the attempt subcommand's argv (after the 'attempt' token).

    Returns (flags, command): everything before the first '--' is evals'
    own flags; everything after is the attempt command verbatim. An empty
    command means the caller must treat it as a usage error.
    """
    if "--" in argv:
        i = argv.index("--")
        return argv[:i], argv[i + 1 :]
    return argv, []


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv[:1] == ["attempt"]:
            flags, command = split_attempt_argv(argv[1:])
            if not command:
                raise UsageError(
                    "attempt command is required: attempt TASK [flags] -- COMMAND..."
                )
            args = parser.parse_args(["attempt", *flags])
            record = attempt(
                task=args.task,
                tasks_root=Path(args.tasks_root),
                output=Path(args.output),
                command=command,
            )
            if record.outcome is AttemptOutcome.REFUSED:
                return 3
            return 0 if record.verdict in (Verdict.PASS, Verdict.FAIL) else 3
        args = parser.parse_args(argv)
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

attempt_p = sub.add_parser(
    "attempt", help="run an attempt command, preserve patch + transcript, grade offline"
)
attempt_p.add_argument("task", help="task name")
attempt_p.add_argument(
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
)
attempt_p.add_argument(
    "--output", default="attempts", help="attempt output directory (default: ./attempts)"
)
```

> Note: the `parser`/`sub` definitions move to module bottom (after `main`) so `main` can call `parser.parse_args` — the existing file defines them before `main`; moving them below is required because `main` now branches on `argv[:1]` before the normal parse. The `attempt` subparser declares only `task` + flags (no command positional): the command never reaches argparse.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_cli.py -v
uv run pytest -m integration tests/integration/test_attempt.py -v
```

Expected: default-tier CLI tests pass; integration CLI test passes.

- [ ] **Step 5: Full verification, then commit**

```bash
uv run pytest
uv run pytest -m integration
uv run ruff check .
uv run pyrefly check
git add src/satyrn_evals/cli.py tests/test_cli.py tests/integration/test_attempt.py
git commit -m "feat: attempt subcommand with -- command splitting"
```

---

## After the last task

Verify the evidence floor from the CLI exactly as a contributor would. The attempt command runs with its cwd inside a disposable temp work copy, so **script and patch paths in the command must be absolute** (relative paths resolve against the temp dir and fail):

```bash
ROOT="$(pwd)"
uv run satyrn-evals attempt format_number --output /tmp/attempts \
  -- python "$ROOT/tests/integration/fake_attempt.py" \
  --patch "$ROOT/src/satyrn_evals/tasks/format_number/fixtures/known-good.patch"
echo $?   # 0
ls /tmp/attempts/*/   # patch.diff transcript.txt receipt.json attempt.json
```

(`python` resolves to the venv interpreter because the orchestration prepends `sys.executable`'s directory to `PATH` — the same as `grade` and `capture` do. `docs/usage.md` must state that attempt commands run with cwd inside a temporary work copy, so relative paths in the command resolve there.)

Then update the docs: `docs/usage.md` (the attempt command, its exit table, the attempt record JSON), `docs/architecture.md` (the data flow gains the attempt step; "What is not here yet" drops the attempt line), and `docs/glossary.md` (define **attempt record**; the "attempt command" and "preservation" glossary entries land). Commit as `docs: V3 attempt usage, architecture, glossary`.
