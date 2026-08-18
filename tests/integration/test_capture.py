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
