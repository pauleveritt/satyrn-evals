"""End-to-end capture with a committed fixture repo. Real git, real oracle."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.capture import capture
from satyrn_evals.capture_record import CaptureOutcome, load_capture_record
from satyrn_evals.errors import CaptureUsageError
from satyrn_evals.grade import grade
from satyrn_evals.verdict import HookResult, Outcome, Verdict

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
FIXED_TESTS = (
    BASE_TESTS + "\n\ndef test_double_negative():\n    assert double(-3) == -6\n"
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def _worktree_add_path(args: list[str]) -> Path | None:
    if "worktree" not in args:
        return None
    command = args.index("worktree")
    if args[command : command + 3] != ["worktree", "add", "--detach"]:
        return None
    return Path(args[command + 3])


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    proc = _git(repo, "commit", "-q", "-m", message)
    assert proc.returncode == 0, proc.stderr


def _init_repo(repo: Path) -> None:
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")


def _write_buggy_fixture(repo: Path) -> None:
    (repo / "solution.py").write_text(BASE_SOLUTION)
    (repo / "test_solution.py").write_text(BASE_TESTS)


def _fix_fixture(repo: Path) -> None:
    (repo / "solution.py").write_text(FIXED_SOLUTION)
    (repo / "test_solution.py").write_text(FIXED_TESTS)


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> tuple[Path, str]:
    """A committed repo: base (buggy) then fix commit touching source + tests."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_buggy_fixture(repo)
    _commit(repo, "base: buggy double with failing tests")
    _fix_fixture(repo)
    _commit(repo, "fix: double returns twice n")
    fix_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert _git(repo, "status", "--porcelain").stdout == ""
    return repo, fix_sha


def test_capture_succeeds_and_source_is_untouched(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    reflog_before = _git(repo, "reflog").stdout
    head_before = _git(repo, "rev-parse", "HEAD").stdout.strip()
    record = capture(
        repo=repo, fix_sha=fix_sha, name="double_task", contract=None, output=output
    )
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


@pytest.mark.parametrize("repo_name", ["repo ", "repo\n"], ids=["space", "newline"])
def test_repository_path_trailing_whitespace_is_preserved(
    tmp_path, repo_name: str
) -> None:
    repo = tmp_path / repo_name
    _init_repo(repo)
    _write_buggy_fixture(repo)
    _commit(repo, "base")
    _fix_fixture(repo)
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name=f"path-{len(repo_name)}",
        contract=None,
        output=output,
    )
    task = output / f"path-{len(repo_name)}"

    assert record.outcome is CaptureOutcome.CAPTURED
    assert record.repo == str(repo.resolve())
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / f"path-{len(repo_name)}.receipt.json",
    ).verdict is Verdict.PASS


def test_replace_ref_cannot_change_captured_commit_or_provenance(
    fixture_repo, tmp_path
) -> None:
    repo, fix_sha = fixture_repo
    base_sha = _git(repo, "rev-parse", f"{fix_sha}^").stdout.strip()
    (repo / "solution.py").write_text("def double(n):\n    return n + n\n")
    _git(repo, "add", "solution.py")
    tree = _git(repo, "write-tree").stdout.strip()
    replacement = subprocess.run(
        ["git", "commit-tree", tree, "-p", base_sha],
        cwd=repo,
        input="replacement\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    _git(repo, "replace", fix_sha, replacement)
    grafts = repo / ".git" / "info" / "grafts"
    grafts.write_text(f"{fix_sha} {replacement}\n")
    reset = subprocess.run(
        ["git", "--no-replace-objects", "reset", "--hard", fix_sha],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert reset.returncode == 0, reset.stderr

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="raw-object",
        contract=None,
        output=output,
    )
    task = output / "raw-object"
    patch = (task / "fixtures" / "known-good.patch").read_text()

    assert record.outcome is CaptureOutcome.CAPTURED
    assert record.fix_sha == fix_sha
    assert "return n * 2" in patch
    assert "return n + n" not in patch
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / "raw-object.receipt.json",
    ).verdict is Verdict.PASS


def test_captured_task_grades_pass_through_real_grade(fixture_repo, tmp_path) -> None:
    """The evidence floor for capture: known-good grades pass, fixture named."""
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    record = capture(
        repo=repo, fix_sha=fix_sha, name="double_task", contract=None, output=output
    )
    assert record.outcome is CaptureOutcome.CAPTURED
    task_dir = output / "double_task"
    receipt = tmp_path / "r.json"
    result = grade(task_dir, task_dir / "fixtures" / "known-good.patch", receipt)
    assert result.verdict is Verdict.PASS
    data = json.loads(receipt.read_text())
    assert data["verdict"] == "pass"
    assert data["evidence"]["counts"]["passed"] == 2


def test_declared_output_inside_source_is_the_only_source_change(
    fixture_repo,
) -> None:
    repo, fix_sha = fixture_repo
    output = repo / "tasks"

    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="inside",
        contract=None,
        output=output,
    )

    assert record.outcome is CaptureOutcome.CAPTURED
    assert _git(repo, "status", "--porcelain").stdout == "?? tasks/\n"
    assert sorted(path.name for path in output.iterdir()) == [
        "inside",
        "inside.capture.json",
    ]

    second = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="inside-again",
        contract=None,
        output=output,
    )
    assert second.outcome is CaptureOutcome.CAPTURED
    assert _git(repo, "status", "--porcelain").stdout == "?? tasks/\n"


def test_output_inside_tracked_source_is_usage_and_cannot_hide_dirty_state(
    fixture_repo,
) -> None:
    repo, fix_sha = fixture_repo
    tracked_output = repo / "src"
    tracked_output.mkdir()
    tracked = tracked_output / "config.py"
    tracked.write_text("VALUE = 1\n")
    _commit(repo, "add tracked output path")
    tracked.write_text("VALUE = 2\n")

    with pytest.raises(CaptureUsageError, match="must not contain tracked paths"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="hidden-dirty",
            contract=None,
            output=tracked_output,
        )

    assert _git(repo, "status", "--porcelain").stdout == " M src/config.py\n"
    assert not (tracked_output / "hidden-dirty").exists()
    assert not (tracked_output / "hidden-dirty.capture.json").exists()


def test_source_root_cannot_be_the_output(fixture_repo) -> None:
    repo, fix_sha = fixture_repo
    with pytest.raises(CaptureUsageError, match="must not be the source"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="root-output",
            contract=None,
            output=repo,
        )


def test_git_metadata_cannot_be_the_output(fixture_repo) -> None:
    repo, fix_sha = fixture_repo
    output = repo / ".git" / "satyrn-tasks"
    before = _git(repo, "status", "--porcelain").stdout

    with pytest.raises(CaptureUsageError, match="inside Git metadata"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="git-output",
            contract=None,
            output=output,
        )

    assert not output.exists()
    assert _git(repo, "status", "--porcelain").stdout == before


def test_git_metadata_casing_alias_cannot_be_the_output(fixture_repo) -> None:
    repo, fix_sha = fixture_repo
    alias = repo / ".GIT"
    if not alias.exists():
        pytest.skip("filesystem is case-sensitive")
    output = alias / "satyrn-tasks"

    with pytest.raises(CaptureUsageError, match="inside Git metadata"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="git-alias-output",
            contract=None,
            output=output,
        )

    assert not output.exists()


def test_capture_preserves_symlink_without_copying_external_content(tmp_path) -> None:
    repo = tmp_path / "repo"
    external = tmp_path / "outside-secret.txt"
    external.write_text("must not be copied\n")
    _init_repo(repo)
    _write_buggy_fixture(repo)
    (repo / "alias.py").symlink_to("solution.py")
    (repo / "external-link.txt").symlink_to(external)
    _commit(repo, "base")
    _fix_fixture(repo)
    _commit(repo, "fix")
    _git(repo, "config", "core.symlinks", "false")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="links",
        contract=None,
        output=output,
    )
    base = output / "links" / "base"

    assert record.outcome is CaptureOutcome.CAPTURED
    assert (base / "alias.py").is_symlink()
    assert os.readlink(base / "alias.py") == "solution.py"
    assert (base / "external-link.txt").is_symlink()
    assert os.readlink(base / "external-link.txt") == str(external)
    receipt = grade(
        output / "links",
        output / "links" / "fixtures" / "known-good.patch",
        tmp_path / "links-receipt.json",
    )
    assert receipt.verdict is Verdict.PASS


def test_capture_materializes_the_complete_tree_from_a_sparse_repository(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_buggy_fixture(repo)
    (repo / "extra.txt").write_text("tracked outside the sparse patterns\n")
    _commit(repo, "base")
    _fix_fixture(repo)
    _commit(repo, "fix")
    (repo / ".git" / "info" / "sparse-checkout").write_text(
        "/solution.py\n/test_solution.py\n"
    )
    _git(repo, "config", "core.sparseCheckout", "true")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="sparse-source",
        contract=None,
        output=output,
    )

    assert record.outcome is CaptureOutcome.CAPTURED
    assert (output / "sparse-source" / "base" / "extra.txt").read_text() == (
        "tracked outside the sparse patterns\n"
    )


def test_quoted_tab_path_is_captured_and_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    unusual = "src/na\tme.py"
    _init_repo(repo)
    _write_buggy_fixture(repo)
    (repo / "src").mkdir()
    (repo / unusual).write_text("-- option\n")
    _commit(repo, "base")
    _fix_fixture(repo)
    (repo / unusual).write_text("fixed\n")
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="quoted",
        contract=None,
        output=output,
    )

    assert record.outcome is CaptureOutcome.CAPTURED
    manifest = json.loads((output / "quoted" / "manifest.json").read_text())
    assert unusual in manifest["source_paths"]
    receipt = grade(
        output / "quoted",
        output / "quoted" / "fixtures" / "known-good.patch",
        tmp_path / "quoted-receipt.json",
    )
    assert receipt.verdict is Verdict.PASS


def test_carriage_return_path_is_captured_and_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    unusual = "src/a\rb.py"
    _init_repo(repo)
    _write_buggy_fixture(repo)
    (repo / "src").mkdir()
    (repo / unusual).write_text("VALUE = 1\n")
    _commit(repo, "base")
    _fix_fixture(repo)
    (repo / unusual).write_text("VALUE = 2\n")
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="carriage-return",
        contract=None,
        output=output,
    )
    task = output / "carriage-return"

    assert record.outcome is CaptureOutcome.CAPTURED
    assert unusual in json.loads((task / "manifest.json").read_text())["source_paths"]
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / "carriage-return-receipt.json",
    ).verdict is Verdict.PASS


def test_crlf_blob_patch_is_preserved_and_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".gitattributes").write_text("data.txt -text\n")
    (repo / "data.txt").write_bytes(b"VALUE=1\r\n")
    (repo / "test_data.py").write_text(
        "from pathlib import Path\n\n\n"
        "def test_data():\n"
        "    assert Path('data.txt').read_bytes() == b'VALUE=2\\r\\n'\n"
    )
    _commit(repo, "base")
    (repo / "data.txt").write_bytes(b"VALUE=2\r\n")
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="crlf",
        contract=None,
        output=output,
    )
    task = output / "crlf"
    patch = (task / "fixtures" / "known-good.patch").read_bytes()

    assert record.outcome is CaptureOutcome.CAPTURED
    assert b"-VALUE=1\r\n" in patch
    assert b"+VALUE=2\r\n" in patch
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / "crlf-receipt.json",
    ).verdict is Verdict.PASS


@pytest.mark.skipif(os.name == "nt", reason="POSIX byte filename semantics")
def test_non_utf8_path_is_captured_and_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    unusual = os.fsdecode(b"src/non-utf8-\xff.py")
    _init_repo(repo)
    _write_buggy_fixture(repo)
    (repo / "src").mkdir()
    try:
        (repo / unusual).write_bytes(b"VALUE = 1\n")
    except OSError as e:
        pytest.skip(f"filesystem rejects non-UTF-8 filenames: {e}")
    _commit(repo, "base")
    _fix_fixture(repo)
    (repo / unusual).write_bytes(b"VALUE = 2\n")
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="non-utf8",
        contract=None,
        output=output,
    )
    task = output / "non-utf8"

    assert record.outcome is CaptureOutcome.CAPTURED
    assert unusual in json.loads((task / "manifest.json").read_text())["source_paths"]
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / "non-utf8-receipt.json",
    ).verdict is Verdict.PASS


def test_mode_only_change_is_captured_and_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    script = repo / "script.sh"
    script.write_text("#!/bin/sh\nexit 0\n")
    script.chmod(0o644)
    (repo / "test_mode.py").write_text(
        "from pathlib import Path\n\n\n"
        "def test_executable():\n"
        "    assert Path('script.sh').stat().st_mode & 0o111\n"
    )
    _commit(repo, "base")
    script.chmod(0o755)
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="mode-only",
        contract=None,
        output=output,
    )
    task = output / "mode-only"

    assert record.outcome is CaptureOutcome.CAPTURED
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / "mode-only-receipt.json",
    ).verdict is Verdict.PASS


def test_space_path_is_captured_and_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    unusual = "src/space name.py"
    _init_repo(repo)
    _write_buggy_fixture(repo)
    (repo / "src").mkdir()
    (repo / unusual).write_text("VALUE = 1\n")
    _commit(repo, "base")
    _fix_fixture(repo)
    (repo / unusual).write_text("VALUE = 2\n")
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="space",
        contract=None,
        output=output,
    )
    task = output / "space"

    assert record.outcome is CaptureOutcome.CAPTURED
    assert unusual in json.loads((task / "manifest.json").read_text())["source_paths"]
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / "space-receipt.json",
    ).verdict is Verdict.PASS


def test_source_copy_uses_both_paths_and_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "source.py").write_text("VALUE = 1\n")
    (repo / "test_copy.py").write_text(
        "from pathlib import Path\n\n\n"
        "def test_copy_exists():\n"
        "    assert Path('copied.py').exists()\n"
    )
    _commit(repo, "base")
    shutil.copyfile(repo / "source.py", repo / "copied.py")
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="copy",
        contract=None,
        output=output,
    )
    task = output / "copy"
    manifest = json.loads((task / "manifest.json").read_text())

    assert record.outcome is CaptureOutcome.CAPTURED
    assert manifest["source_paths"] == ["source.py", "copied.py"]
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / "copy-receipt.json",
    ).verdict is Verdict.PASS


@pytest.mark.parametrize("change", ["binary", "empty-delete"])
def test_header_only_change_is_captured_and_grades(tmp_path, change: str) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    if change == "binary":
        path = repo / "data.bin"
        path.write_bytes(b"\x00before\n")
        expected = b"\x00after\n"
        test_body = "assert Path('data.bin').read_bytes() == b'\\x00after\\n'"
    else:
        path = repo / "empty.py"
        path.write_bytes(b"")
        expected = None
        test_body = "assert not Path('empty.py').exists()"
    (repo / "test_change.py").write_text(
        "from pathlib import Path\n\n\n"
        f"def test_change():\n    {test_body}\n"
    )
    _commit(repo, "base")
    if expected is None:
        path.unlink()
    else:
        path.write_bytes(expected)
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name=change,
        contract=None,
        output=output,
    )
    task = output / change

    assert record.outcome is CaptureOutcome.CAPTURED
    assert grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / f"{change}-receipt.json",
    ).verdict is Verdict.PASS


def test_test_to_source_rename_is_excluded_and_known_good_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_buggy_fixture(repo)
    (repo / "test_helper.py").write_text("VALUE = 1\n")
    _commit(repo, "base")
    _fix_fixture(repo)
    moved = _git(repo, "mv", "test_helper.py", "helper.py")
    assert moved.returncode == 0, moved.stderr
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="rename",
        contract=None,
        output=output,
    )
    known_good = output / "rename" / "fixtures" / "known-good.patch"

    assert record.outcome is CaptureOutcome.CAPTURED
    assert "helper.py" not in known_good.read_text()
    receipt = grade(
        output / "rename",
        known_good,
        tmp_path / "rename-receipt.json",
    )
    assert receipt.verdict is Verdict.PASS


def test_source_rename_keeps_both_allowlist_paths_and_grades(tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_buggy_fixture(repo)
    (repo / "a").mkdir()
    (repo / "a" / "old_helper.py").write_text("VALUE = 1\n")
    _commit(repo, "base")
    _fix_fixture(repo)
    moved = _git(repo, "mv", "a/old_helper.py", "a/new_helper.py")
    assert moved.returncode == 0, moved.stderr
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="source-rename",
        contract=None,
        output=output,
    )
    task = output / "source-rename"
    manifest = json.loads((task / "manifest.json").read_text())

    assert record.outcome is CaptureOutcome.CAPTURED
    assert "a/old_helper.py" in manifest["source_paths"]
    assert "a/new_helper.py" in manifest["source_paths"]
    receipt = grade(
        task,
        task / "fixtures" / "known-good.patch",
        tmp_path / "source-rename-receipt.json",
    )
    assert receipt.verdict is Verdict.PASS


def test_dirty_source_is_refused(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    (repo / "solution.py").write_text(BASE_SOLUTION + "# dirty\n")
    output = tmp_path / "tasks"
    record = capture(
        repo=repo, fix_sha=fix_sha, name="double_task", contract=None, output=output
    )
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
    record = capture(
        repo=repo, fix_sha=fix_sha, name="t", contract=None, output=tmp_path / "tasks"
    )
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
    record = capture(
        repo=repo, fix_sha=fix_sha, name="t", contract=None, output=tmp_path / "tasks"
    )
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
    record = capture(
        repo=repo, fix_sha=fix_sha, name="t", contract=None, output=tmp_path / "tasks"
    )
    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "ORACLE_ENV"
    assert "does_not_exist_xyz" in record.message


def test_shorthand_sha_ok_and_bad_sha_is_usage(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    short = fix_sha[:8]
    record = capture(
        repo=repo, fix_sha=short, name="t", contract=None, output=tmp_path / "tasks"
    )
    assert record.outcome is CaptureOutcome.CAPTURED
    with pytest.raises(CaptureUsageError):
        capture(
            repo=repo,
            fix_sha="deadbeef",
            name="t",
            contract=None,
            output=tmp_path / "tasks",
        )


def test_default_name_and_explicit_contract_are_preserved(
    fixture_repo, tmp_path
) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name=None,
        contract="Return twice the input.",
        output=output,
    )
    task = output / "fix-double-returns-twice-n"
    manifest = json.loads((task / "manifest.json").read_text())

    assert record.outcome is CaptureOutcome.CAPTURED
    assert manifest["contract"] == "Return twice the input."


def test_invalid_explicit_name_is_usage_without_output(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"

    with pytest.raises(CaptureUsageError, match="invalid task name"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="../escape",
            contract=None,
            output=output,
        )
    assert not output.exists()


def test_root_commit_is_a_named_refusal(tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_buggy_fixture(repo)
    _commit(repo, "root fix")
    output = tmp_path / "tasks"

    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="root",
        contract=None,
        output=output,
    )

    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "NO_PARENT"
    assert load_capture_record(output / "root.capture.json") == record


def test_existing_task_is_usage_and_is_not_modified(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    task = output / "existing"
    task.mkdir(parents=True)
    marker = task / "keep.txt"
    marker.write_text("keep\n")

    with pytest.raises(CaptureUsageError, match="task already exists"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="existing",
            contract=None,
            output=output,
        )

    assert marker.read_text() == "keep\n"
    assert not (output / "existing.capture.json").exists()


def test_existing_record_is_usage_and_is_not_modified(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    output.mkdir()
    record_path = output / "existing.capture.json"
    record_path.write_text("do not overwrite\n")

    with pytest.raises(CaptureUsageError, match="task already exists"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="existing",
            contract=None,
            output=output,
        )

    assert record_path.read_text() == "do not overwrite\n"


def test_dangling_record_symlink_is_not_followed(fixture_repo, tmp_path) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    output.mkdir()
    escaped = tmp_path / "escaped.json"
    record_path = output / "dangling.capture.json"
    record_path.symlink_to(escaped)

    with pytest.raises(CaptureUsageError, match="task already exists"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="dangling",
            contract=None,
            output=output,
        )

    assert record_path.is_symlink()
    assert not escaped.exists()


def test_task_publication_race_does_not_remove_foreign_directory(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    task = output / "raced"
    foreign = task / "foreign.txt"
    real_mkdir = Path.mkdir
    raced = False

    def race_mkdir(path: Path, *args, **kwargs) -> None:
        nonlocal raced
        if path == task and not raced:
            raced = True
            real_mkdir(path, parents=True)
            foreign.write_text("belongs to another capture\n")
            raise FileExistsError("another capture won")
        real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", race_mkdir)
    with pytest.raises(CaptureUsageError, match="task already exists"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="raced",
            contract=None,
            output=output,
        )

    assert raced
    assert foreign.read_text() == "belongs to another capture\n"
    assert not (output / "raced.capture.json").exists()


def test_cleanup_failure_displaces_task_publication_race(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    task = output / "raced-cleanup"
    foreign = task / "foreign.txt"
    retained: Path | None = None
    real_git = capture_module._git
    real_mkdir = Path.mkdir

    def lock_after_add(
        root: Path, args: list[str], *, input_text: str | None = None
    ) -> str:
        nonlocal retained
        value = real_git(root, args, input_text=input_text)
        if (worktree := _worktree_add_path(args)) is not None:
            retained = worktree
            real_git(root, ["worktree", "lock", str(retained)])
        return value

    def race_mkdir(path: Path, *args, **kwargs) -> None:
        if path == task and not task.exists():
            real_mkdir(path, parents=True)
            foreign.write_text("belongs to another capture\n")
            raise FileExistsError("another capture won")
        real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(capture_module, "_git", lock_after_add)
    monkeypatch.setattr(Path, "mkdir", race_mkdir)
    try:
        record = capture(
            repo=repo,
            fix_sha=fix_sha,
            name="raced-cleanup",
            contract=None,
            output=output,
        )

        assert record.code == "CLEANUP_FAILED"
        assert "displaced usage error" in record.message
        assert retained is not None and str(retained) in record.message
        assert foreign.read_text() == "belongs to another capture\n"
        assert load_capture_record(output / "raced-cleanup.capture.json") == record
    finally:
        if retained is not None:
            _git(repo, "worktree", "unlock", str(retained))
            _git(repo, "worktree", "remove", "--force", str(retained))
            shutil.rmtree(retained.parent)


def test_record_publication_race_preserves_winner_and_removes_owned_task(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    record_path = output / "record-race.capture.json"
    real_write = capture_module.write_capture_record

    def race_record(path: Path, record) -> None:
        path.write_text("winner\n")
        real_write(path, record)

    monkeypatch.setattr(capture_module, "write_capture_record", race_record)
    with pytest.raises(CaptureUsageError, match="task already exists"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="record-race",
            contract=None,
            output=output,
        )

    assert record_path.read_text() == "winner\n"
    assert not (output / "record-race").exists()


def test_record_transport_failure_removes_completed_task(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module
    from satyrn_evals.errors import ArtifactFailed

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"

    def fail_record(*_args, **_kwargs) -> None:
        raise OSError("record device failed")

    monkeypatch.setattr(capture_module, "write_capture_record", fail_record)
    with pytest.raises(ArtifactFailed, match="cannot publish capture record"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="record-failure",
            contract=None,
            output=output,
        )

    assert not (output / "record-failure").exists()
    assert not (output / "record-failure.capture.json").exists()


def test_record_failure_does_not_hide_worktree_cleanup_failure(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module
    from satyrn_evals.errors import CleanupFailed

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    real_cleanup = capture_module._cleanup_worktree

    def cleanup_then_report(root: Path, state) -> None:
        real_cleanup(root, state)
        raise CleanupFailed("worktree retained at /important/recovery/path")

    def fail_record(*_args, **_kwargs) -> None:
        raise OSError("record disk full")

    monkeypatch.setattr(capture_module, "_cleanup_worktree", cleanup_then_report)
    monkeypatch.setattr(capture_module, "write_capture_record", fail_record)
    with pytest.raises(CleanupFailed, match="/important/recovery/path") as error:
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="cleanup-and-record",
            contract=None,
            output=output,
        )

    assert "record publication also failed" in str(error.value)
    assert (output / "cleanup-and-record").exists()


def test_record_collision_rollback_failure_retains_task_and_is_cleanup_failed(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module
    from satyrn_evals.errors import CleanupFailed

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    task = output / "record-cleanup-race"
    record_path = output / "record-cleanup-race.capture.json"
    real_write = capture_module.write_capture_record
    real_rmtree = capture_module.shutil.rmtree

    def race_record(path: Path, record) -> None:
        path.write_text("winner\n")
        real_write(path, record)

    def fail_task_cleanup(path: Path) -> None:
        if Path(path) == task:
            raise OSError("task directory busy")
        real_rmtree(path)

    monkeypatch.setattr(capture_module, "write_capture_record", race_record)
    monkeypatch.setattr(capture_module.shutil, "rmtree", fail_task_cleanup)
    with pytest.raises(CleanupFailed, match="task retained"):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="record-cleanup-race",
            contract=None,
            output=output,
        )

    assert record_path.read_text() == "winner\n"
    assert task.exists()
    real_rmtree(task)


def test_locked_worktree_replaces_success_record_and_cli_exit(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    """A real locked capture worktree proves cleanup-result precedence."""
    import satyrn_evals.capture as capture_module
    from satyrn_evals.cli import main

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    retained: Path | None = None
    returned = []
    real_git = capture_module._git
    real_capture = capture_module.capture

    def lock_after_add(
        root: Path, args: list[str], *, input_text: str | None = None
    ) -> str:
        nonlocal retained
        value = real_git(root, args, input_text=input_text)
        if (worktree := _worktree_add_path(args)) is not None:
            retained = worktree
            real_git(root, ["worktree", "lock", str(retained)])
        return value

    monkeypatch.setattr(capture_module, "_git", lock_after_add)

    def record_result(**kwargs):
        result = real_capture(**kwargs)
        returned.append(result)
        return result

    monkeypatch.setattr("satyrn_evals.cli.capture", record_result)
    try:
        exit_code = main(
            [
                "capture",
                "--revert",
                fix_sha,
                "--repo",
                str(repo),
                "--name",
                "locked",
                "--output",
                str(output),
            ]
        )
        record = load_capture_record(output / "locked.capture.json")
        assert exit_code == 3
        assert returned == [record]
        assert record.outcome is CaptureOutcome.REFUSED
        assert record.code == "CLEANUP_FAILED"
        assert record.task_dir == str(output / "locked")
        assert retained is not None
        assert str(retained) in record.message
        assert retained.exists()
    finally:
        if retained is not None:
            _git(repo, "worktree", "unlock", str(retained))
            _git(repo, "worktree", "remove", "--force", str(retained))
            retained.parent.rmdir()


def test_artifact_write_failure_is_a_named_refusal(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    real_write_bytes = Path.write_bytes

    def fail_patch_write(path: Path, data: bytes, *args, **kwargs) -> int:
        if path.name == "known-good.patch":
            raise OSError("output device failed")
        return real_write_bytes(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_bytes", fail_patch_write)
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="artifact-failure",
        contract=None,
        output=output,
    )

    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "ARTIFACT_FAILED"
    assert not (output / "artifact-failure").exists()
    assert load_capture_record(output / "artifact-failure.capture.json") == record


def test_partial_artifact_cleanup_failure_has_cleanup_precedence(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    task = output / "artifact-cleanup"
    real_write_bytes = Path.write_bytes
    real_rmtree = capture_module.shutil.rmtree

    def fail_patch_write(path: Path, data: bytes, *args, **kwargs) -> int:
        if path.name == "known-good.patch":
            raise OSError("output device failed")
        return real_write_bytes(path, data, *args, **kwargs)

    def fail_task_cleanup(path: Path) -> None:
        if Path(path) == task:
            raise OSError("task directory busy")
        real_rmtree(path)

    monkeypatch.setattr(Path, "write_bytes", fail_patch_write)
    monkeypatch.setattr(capture_module.shutil, "rmtree", fail_task_cleanup)
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="artifact-cleanup",
        contract=None,
        output=output,
    )

    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "CLEANUP_FAILED"
    assert record.task_dir == str(task)
    assert "task directory busy" in record.message
    assert load_capture_record(output / "artifact-cleanup.capture.json") == record
    real_rmtree(task)


def test_base_materialization_failure_is_a_named_refusal(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    real_copytree = capture_module.shutil.copytree

    def fail_base_copy(src: Path, dst: Path, *args, **kwargs):
        if Path(dst).name == "base" and "satyrn-capture" in str(dst):
            raise OSError("cannot copy base")
        return real_copytree(src, dst, *args, **kwargs)

    monkeypatch.setattr(capture_module.shutil, "copytree", fail_base_copy)
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="base-copy",
        contract=None,
        output=output,
    )

    assert record.code == "ARTIFACT_FAILED"
    assert "cannot materialize" in record.message
    assert load_capture_record(output / "base-copy.capture.json") == record


def test_artifact_interrupt_preserves_exception_and_rolls_back_task(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    interrupted = KeyboardInterrupt("stop artifact publication")
    real_write_bytes = Path.write_bytes

    def interrupt_patch(path: Path, data: bytes, *args, **kwargs) -> int:
        if path.name == "known-good.patch":
            raise interrupted
        return real_write_bytes(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_bytes", interrupt_patch)
    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="artifact-interrupt",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert not (output / "artifact-interrupt").exists()
    assert not (output / "artifact-interrupt.capture.json").exists()


def test_record_interrupt_preserves_exception_and_rolls_back_task(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    interrupted = KeyboardInterrupt("stop record publication")

    def interrupt_record(*_args, **_kwargs) -> None:
        raise interrupted

    monkeypatch.setattr(capture_module, "write_capture_record", interrupt_record)
    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="record-interrupt",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert not (output / "record-interrupt").exists()
    assert not (output / "record-interrupt.capture.json").exists()


def test_hook_sentinel_does_not_fire(fixture_repo, tmp_path, monkeypatch) -> None:
    """Hooks, fsmonitor, and external diff must not fire during capture."""
    repo, fix_sha = fixture_repo
    sentinel = tmp_path / "hook-fired.txt"
    for name in ("post-checkout", "reference-transaction"):
        hook = repo / ".git" / "hooks" / name
        hook.write_text(f"#!/bin/sh\ntouch {sentinel}\n")
        hook.chmod(0o755)
    monitor = tmp_path / "fsmonitor"
    monitor.write_text(f"#!/bin/sh\ntouch {sentinel}\n")
    monitor.chmod(0o755)
    _git(repo, "config", "core.fsmonitor", str(monitor))
    external_diff = tmp_path / "external-diff"
    external_diff.write_text(f"#!/bin/sh\ntouch {sentinel}\nexit 1\n")
    external_diff.chmod(0o755)
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", str(external_diff))
    record = capture(
        repo=repo, fix_sha=fix_sha, name="t", contract=None, output=tmp_path / "tasks"
    )
    assert record.outcome is CaptureOutcome.CAPTURED
    assert not sentinel.exists()


def test_checkout_filters_remain_active(tmp_path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _git(repo, "config", "filter.satyrn.clean", "sed s/SMUDGED/STORED/")
    _git(repo, "config", "filter.satyrn.smudge", "sed s/STORED/SMUDGED/")
    _write_buggy_fixture(repo)
    (repo / ".gitattributes").write_text("filtered.txt filter=satyrn\n")
    (repo / "filtered.txt").write_text("STORED\n")
    _commit(repo, "base")
    _fix_fixture(repo)
    _commit(repo, "fix")

    output = tmp_path / "tasks"
    record = capture(
        repo=repo,
        fix_sha="HEAD",
        name="filtered",
        contract=None,
        output=output,
    )

    assert record.outcome is CaptureOutcome.CAPTURED
    assert (output / "filtered" / "base" / "filtered.txt").read_text() == "SMUDGED\n"


def test_interrupt_after_real_add_removes_registration(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    before = _git(repo, "worktree", "list", "--porcelain").stdout
    parents: list[Path] = []
    real_allocate = capture_module._safe_temp_parent
    real_registered = capture_module._worktree_registered
    interrupted = False

    def record_parent(root: Path) -> Path:
        parent = real_allocate(root)
        parents.append(parent)
        return parent

    def interrupt_once(root: Path, worktree: Path) -> bool | None:
        nonlocal interrupted
        value = real_registered(root, worktree)
        if value is True and not interrupted:
            interrupted = True
            raise KeyboardInterrupt
        return value

    monkeypatch.setattr(capture_module, "_safe_temp_parent", record_parent)
    monkeypatch.setattr(capture_module, "_worktree_registered", interrupt_once)

    with pytest.raises(KeyboardInterrupt):
        capture(
            repo=repo,
            fix_sha=fix_sha,
            name="interrupted",
            contract=None,
            output=tmp_path / "tasks",
        )

    assert interrupted
    assert _git(repo, "worktree", "list", "--porcelain").stdout == before
    assert _git(repo, "status", "--porcelain").stdout == ""
    assert len(parents) == 1
    assert not parents[0].exists()


def test_add_that_registers_then_reports_failure_is_cleaned_up(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    before = _git(repo, "worktree", "list", "--porcelain").stdout
    real_git = capture_module._git

    def fail_after_add(
        root: Path, args: list[str], *, input_text: str | None = None
    ) -> str:
        value = real_git(root, args, input_text=input_text)
        if _worktree_add_path(args) is not None:
            raise capture_module.GitFailed("add reported failure after registration")
        return value

    monkeypatch.setattr(capture_module, "_git", fail_after_add)
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="add-failure",
        contract=None,
        output=tmp_path / "tasks",
    )

    assert record.code == "GIT_FAILED"
    assert _git(repo, "worktree", "list", "--porcelain").stdout == before


def test_hostile_tmpdir_never_receives_engine_temporary_files(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import tempfile

    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    observed: list[Path] = []
    allocation_roots: list[Path] = []
    real_oracle = capture_module._run_oracle
    real_mkdtemp = tempfile.mkdtemp

    def observe_oracle(
        worktree: Path, command: tuple[str, ...], temp_parent: Path
    ) -> HookResult:
        observed.extend((worktree, temp_parent))
        return real_oracle(worktree, command, temp_parent)

    def observe_mkdtemp(
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | os.PathLike[str] | None = None,
    ) -> str:
        assert dir is not None
        allocation_roots.append(Path(dir).resolve())
        return real_mkdtemp(suffix=suffix, prefix=prefix, dir=dir)

    monkeypatch.setenv("TMPDIR", str(repo))
    monkeypatch.setattr(tempfile, "tempdir", None)
    monkeypatch.setattr(capture_module, "_run_oracle", observe_oracle)
    monkeypatch.setattr(capture_module.tempfile, "mkdtemp", observe_mkdtemp)
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="hostile-tmp",
        contract=None,
        output=tmp_path / "tasks",
    )

    assert record.outcome is CaptureOutcome.CAPTURED
    assert observed
    assert all(not path.resolve().is_relative_to(repo.resolve()) for path in observed)
    assert allocation_roots
    assert all(not path.is_relative_to(repo.resolve()) for path in allocation_roots)
    assert _git(repo, "status", "--porcelain").stdout == ""


def _hook(
    outcomes: dict[str, Outcome], *, collect_errors: tuple[str, ...] = ()
) -> HookResult:
    counts = {name: 0 for name in ("passed", "failed", "error", "skipped")}
    for outcome in outcomes.values():
        counts[outcome] += 1
    return HookResult(
        executed_test_ids=tuple(outcomes),
        outcomes=outcomes,
        counts=counts,
        collect_errors=collect_errors,
    )


@pytest.mark.parametrize(
    ("last_hook", "message"),
    [
        (_hook({}, collect_errors=("fixed collection failed",)), "fixed oracle"),
        (
            _hook({}, collect_errors=("restricted collection failed",)),
            "recorded oracle",
        ),
        (_hook({"test_solution.py::test_double_positive": "failed"}), "failing"),
    ],
    ids=["fixed-collection", "restricted-collection", "restricted-failure"],
)
def test_later_oracle_failures_are_named_refusals(
    fixture_repo, tmp_path, monkeypatch, last_hook: HookResult, message: str
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    test_id = "test_solution.py::test_double_positive"
    base = _hook({test_id: "failed"})
    fixed = _hook({test_id: "passed"})
    results = (
        iter((base, last_hook))
        if message == "fixed oracle"
        else iter((base, fixed, last_hook))
    )

    def fake_oracle(
        _worktree: Path, _command: tuple[str, ...], _temp_parent: Path
    ) -> HookResult:
        return next(results)

    monkeypatch.setattr(capture_module, "_run_oracle", fake_oracle)
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name=f"oracle-{message.replace(' ', '-')}",
        contract=None,
        output=tmp_path / "tasks",
    )

    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "NOT_WINNABLE"
    assert message in record.message


def test_unconfirmed_registration_refuses_without_running_oracle(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    real_registered = capture_module._worktree_registered
    first = True
    oracle_called = False

    def uncertain_once(root: Path, worktree: Path) -> bool | None:
        nonlocal first
        if first:
            first = False
            return None
        return real_registered(root, worktree)

    def forbidden_oracle(
        _worktree: Path, _command: tuple[str, ...], _temp_parent: Path
    ) -> HookResult:
        nonlocal oracle_called
        oracle_called = True
        raise AssertionError("oracle must not run")

    monkeypatch.setattr(capture_module, "_worktree_registered", uncertain_once)
    monkeypatch.setattr(capture_module, "_run_oracle", forbidden_oracle)
    before = _git(repo, "worktree", "list", "--porcelain").stdout
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="uncertain",
        contract=None,
        output=tmp_path / "tasks",
    )

    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "GIT_FAILED"
    assert not oracle_called
    assert _git(repo, "worktree", "list", "--porcelain").stdout == before


def test_parent_removal_failure_replaces_success(
    fixture_repo, tmp_path, monkeypatch
) -> None:
    import shutil

    import satyrn_evals.capture as capture_module

    repo, fix_sha = fixture_repo
    real_rmtree = capture_module.shutil.rmtree
    parent: Path | None = None
    failed = False
    real_allocate = capture_module._safe_temp_parent

    def record_parent(root: Path) -> Path:
        nonlocal parent
        parent = real_allocate(root)
        return parent

    def fail_once(path: Path) -> None:
        nonlocal failed
        if not failed and parent is not None and Path(path) == parent:
            failed = True
            raise OSError("directory busy")
        real_rmtree(path)

    monkeypatch.setattr(capture_module, "_safe_temp_parent", record_parent)
    monkeypatch.setattr(capture_module.shutil, "rmtree", fail_once)
    record = capture(
        repo=repo,
        fix_sha=fix_sha,
        name="parent-cleanup",
        contract=None,
        output=tmp_path / "tasks",
    )

    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "CLEANUP_FAILED"
    assert "directory busy" in record.message
    assert parent is not None and parent.exists()
    shutil.rmtree(parent)


def test_capture_cli_success_and_refusal(fixture_repo, tmp_path) -> None:
    from satyrn_evals.cli import main

    repo, fix_sha = fixture_repo
    output = tmp_path / "tasks"
    code = main(
        [
            "capture",
            "--revert",
            fix_sha,
            "--repo",
            str(repo),
            "--name",
            "cli_task",
            "--output",
            str(output),
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
            "capture",
            "--revert",
            fix_sha,
            "--repo",
            str(repo),
            "--name",
            "cli_task_dirty",
            "--output",
            str(output),
        ]
    )
    assert code == 3
    record = load_capture_record(output / "cli_task_dirty.capture.json")
    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code == "REPO_DIRTY"
    # usage path: SHA names nothing — exit 2, nothing written
    before = sorted(p.name for p in output.iterdir())
    code = main(
        [
            "capture",
            "--revert",
            "deadbeef",
            "--repo",
            str(repo),
            "--name",
            "cli_task",
            "--output",
            str(output),
        ]
    )
    assert code == 2
    assert sorted(p.name for p in output.iterdir()) == before
