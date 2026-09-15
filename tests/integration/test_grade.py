"""End-to-end grading with a temporary task. Real git, real oracle subprocess."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import satyrn_evals.grade as grade_module
from satyrn_evals.attempt_record import DeadlinePhase
from satyrn_evals.deadline import AttemptDeadline, AttemptDeadlineExceeded
from satyrn_evals.errors import ApplyError, PatchReadError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

BASE_SOLUTION = "def double(n):\n    return n\n"
BASE_TESTS = (
    "from solution import double\n\n\n"
    "def test_double_positive():\n"
    "    assert double(3) == 6\n\n\n"
    "def test_double_zero():\n"
    "    assert double(0) == 0\n"
)
GOOD_PATCH = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)
BROKEN_PATCH = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n + 1\n"
)
MANIFEST = {
    "name": "tmp_double",
    "contract": "Fix double(n) to return twice n.",
    "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"],
    "expected_test_ids": [
        "test_solution.py::test_double_positive",
        "test_solution.py::test_double_zero",
    ],
    "source_paths": ["solution.py"],
    "fixtures": {
        "known_good": "fixtures/known-good.patch",
        "known_broken": "fixtures/known-broken.patch",
    },
}


@pytest.fixture()
def tmp_task(tmp_path: Path) -> Path:
    task_dir = tmp_path / "tmp_double"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "fixtures").mkdir()
    (task_dir / "base" / "solution.py").write_text(BASE_SOLUTION)
    (task_dir / "base" / "test_solution.py").write_text(BASE_TESTS)
    (task_dir / "fixtures" / "known-good.patch").write_text(GOOD_PATCH)
    (task_dir / "fixtures" / "known-broken.patch").write_text(BROKEN_PATCH)
    (task_dir / "manifest.json").write_text(json.dumps(MANIFEST))
    return task_dir


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_checked_process_failure_does_not_displace_simultaneous_deadline() -> None:
    """The whole deadline controls a checked process result observed with it."""
    calls = iter((0.0, 0.0, 0.0, 1.0))
    deadline = AttemptDeadline(1.0, clock=lambda: next(calls))

    with pytest.raises(AttemptDeadlineExceeded) as raised:
        grade_module._run_grading_subprocess(
            [sys.executable, "-c", "raise SystemExit(7)"],
            check=True,
            capture_output=True,
            deadline=deadline,
        )

    assert raised.value.phase is DeadlinePhase.GRADING


def test_expiry_after_hook_load_retains_grading_scratch(
    tmp_task: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hook evidence survives expiry between loading and scratch cleanup."""
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    original_load = grade_module.load_hook_result

    def load_then_expire(path: Path, run_started: float):
        result = original_load(path, run_started)
        clock.now = 1.0
        return result

    monkeypatch.setattr(grade_module, "load_hook_result", load_then_expire)
    receipt_path = tmp_path / "receipt.json"

    with pytest.raises(AttemptDeadlineExceeded) as raised:
        grade(
            tmp_task,
            tmp_task / "fixtures" / "known-good.patch",
            receipt_path,
            deadline=deadline,
        )

    assert raised.value.phase is DeadlinePhase.GRADING
    assert not receipt_path.exists()
    scratch = list(tmp_path.glob("satyrn-grade-*"))
    assert len(scratch) == 1
    assert list(scratch[0].glob("satyrn-hook-*.json"))


def test_known_good_patch_is_accepted(tmp_task: Path, tmp_path: Path) -> None:
    receipt_path = tmp_path / "r.json"
    receipt = grade(tmp_task, tmp_task / "fixtures" / "known-good.patch", receipt_path)
    assert receipt.verdict is Verdict.PASS
    data = json.loads(receipt_path.read_text())
    assert data["task"] == "tmp_double"
    assert data["verdict"] == "pass"
    assert data["patch_digest"]
    assert data["evidence"]["counts"]["passed"] == 2


def test_known_broken_patch_is_rejected(tmp_task: Path, tmp_path: Path) -> None:
    receipt_path = tmp_path / "r.json"
    receipt = grade(tmp_task, tmp_task / "fixtures" / "known-broken.patch", receipt_path)
    assert receipt.verdict is Verdict.FAIL
    data = json.loads(receipt_path.read_text())
    assert data["verdict"] == "fail"
    assert data["evidence"]["counts"]["failed"] == 2


def test_unappliable_patch_records_unavailable(tmp_task: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.patch"
    bad.write_text(
        "diff --git a/solution.py b/solution.py\n"
        "--- a/solution.py\n"
        "+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def double(n):\n"
        "-    return n + 999\n"
        "+    return n * 2\n"
    )
    receipt_path = tmp_path / "r.json"
    receipt = grade(tmp_task, bad, receipt_path)
    assert receipt.verdict is Verdict.UNAVAILABLE
    data = json.loads(receipt_path.read_text())
    assert data["verdict"] == "unavailable"
    assert "apply" in data["reason"]


def test_oracle_without_hook_records_unavailable(tmp_task: Path, tmp_path: Path) -> None:
    manifest_path = tmp_task / "manifest.json"
    data = json.loads(manifest_path.read_text())
    data["oracle"] = ["python", "-c", "pass"]
    manifest_path.write_text(json.dumps(data))
    receipt_path = tmp_path / "r.json"
    receipt = grade(tmp_task, tmp_task / "fixtures" / "known-good.patch", receipt_path)
    assert receipt.verdict is Verdict.UNAVAILABLE
    data = json.loads(receipt_path.read_text())
    assert data["verdict"] == "unavailable"
    assert "missing" in data["reason"]


def test_oracle_command_not_found_records_unavailable(tmp_task: Path, tmp_path: Path) -> None:
    manifest_path = tmp_task / "manifest.json"
    data = json.loads(manifest_path.read_text())
    data["oracle"] = ["definitely-not-a-real-command-xyz-123"]
    manifest_path.write_text(json.dumps(data))
    receipt_path = tmp_path / "r.json"
    receipt = grade(tmp_task, tmp_task / "fixtures" / "known-good.patch", receipt_path)
    assert receipt.verdict is Verdict.UNAVAILABLE
    data = json.loads(receipt_path.read_text())
    assert data["verdict"] == "unavailable"
    assert "oracle failed to start" in data["reason"]


def test_patch_touching_tests_records_unavailable(tmp_task: Path, tmp_path: Path) -> None:
    bad = tmp_path / "touches-tests.patch"
    bad.write_text(
        "diff --git a/test_solution.py b/test_solution.py\n"
        "--- a/test_solution.py\n"
        "+++ b/test_solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " from solution import double\n"
        "+# tampered\n"
    )
    receipt_path = tmp_path / "r.json"
    receipt = grade(tmp_task, bad, receipt_path)
    assert receipt.verdict is Verdict.UNAVAILABLE
    data = json.loads(receipt_path.read_text())
    assert data["verdict"] == "unavailable"
    assert "non-source" in data["reason"]


PROVENANCE_SECTION = (
    "diff --git a/PROVENANCE.md b/PROVENANCE.md\n"
    "new file mode 100644\n"
    "--- /dev/null\n"
    "+++ b/PROVENANCE.md\n"
    "@@ -0,0 +1 @@\n"
    "+| solution.py | created |\n"
)


def _ignore_provenance(task_dir: Path) -> None:
    manifest_path = task_dir / "manifest.json"
    data = json.loads(manifest_path.read_text())
    data["ignored_paths"] = ["PROVENANCE.md"]
    manifest_path.write_text(json.dumps(data))


def test_an_ignored_path_is_dropped_and_listed_and_the_rest_grades(tmp_task: Path, tmp_path: Path) -> None:
    _ignore_provenance(tmp_task)
    patch = tmp_path / "with-provenance.patch"
    patch.write_text(PROVENANCE_SECTION + GOOD_PATCH)
    receipt_path = tmp_path / "r.json"
    receipt = grade(tmp_task, patch, receipt_path)
    assert receipt.verdict is Verdict.PASS
    assert json.loads(receipt_path.read_text())["ignored_paths"] == ["PROVENANCE.md"]


def test_a_patch_of_only_ignored_paths_grades_the_base(tmp_task: Path, tmp_path: Path) -> None:
    _ignore_provenance(tmp_task)
    patch = tmp_path / "only-provenance.patch"
    patch.write_text(PROVENANCE_SECTION)
    receipt = grade(tmp_task, patch, tmp_path / "r.json")
    assert (receipt.verdict, receipt.ignored_paths) == (Verdict.FAIL, ("PROVENANCE.md",))


def test_an_undeclared_provenance_file_still_makes_the_verdict_unavailable(tmp_task: Path, tmp_path: Path) -> None:
    patch = tmp_path / "with-provenance.patch"
    patch.write_text(PROVENANCE_SECTION + GOOD_PATCH)
    receipt = grade(tmp_task, patch, tmp_path / "r.json")
    assert (receipt.verdict, receipt.reason) == (Verdict.UNAVAILABLE, "patch touches non-source path: PROVENANCE.md")


def test_unreadable_patch_is_a_usage_error(tmp_task: Path, tmp_path: Path) -> None:
    with pytest.raises(PatchReadError, match="cannot read patch"):
        grade(tmp_task, tmp_path / "missing.patch", tmp_path / "r.json")


def test_executed_id_mismatch_records_reason(tmp_task: Path, tmp_path: Path) -> None:
    manifest_path = tmp_task / "manifest.json"
    data = json.loads(manifest_path.read_text())
    data["expected_test_ids"].append("test_solution.py::test_missing")
    manifest_path.write_text(json.dumps(data))

    receipt = grade(
        tmp_task,
        tmp_task / "fixtures" / "known-good.patch",
        tmp_path / "r.json",
    )

    assert receipt.verdict is Verdict.UNAVAILABLE
    assert "test_missing" in receipt.reason


@pytest.mark.parametrize(
    "failure",
    [OSError("git missing"), subprocess.CalledProcessError(1, ["git", "init"])],
    ids=["spawn", "nonzero"],
)
def test_git_init_failure_is_an_apply_error(
    tmp_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: OSError | subprocess.CalledProcessError,
) -> None:
    def fail_init(argv: list[str], **_kwargs: object) -> object:
        if "--local-env-vars" in argv:
            # the T8 routing probe is a real git subprocess now: let it
            # succeed so the failure lands on grading's git init, which is
            # what this test exercises
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        raise failure

    monkeypatch.setattr(grade_module.subprocess, "run", fail_init)

    with pytest.raises(ApplyError, match="cannot run git"):
        grade_module._run_oracle(
            load_manifest(tmp_task),
            tmp_task,
            GOOD_PATCH,
        )


def test_git_apply_error_preserves_filesystem_bytes(
    tmp_task: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # the real sequence is now: routing probe -> git init -> git apply
    calls = iter(
        (
            subprocess.CompletedProcess(["git", "rev-parse"], 0, b"", b""),
            subprocess.CompletedProcess(["git", "init", "-q"], 0, b"", b""),
            subprocess.CompletedProcess(["git", "apply", "-"], 1, b"", b"bad \xff"),
        )
    )
    monkeypatch.setattr(grade_module.subprocess, "run", lambda *_a, **_kw: next(calls))

    with pytest.raises(ApplyError) as raised:
        grade_module._run_oracle(load_manifest(tmp_task), tmp_task, GOOD_PATCH)

    assert b"bad \xff" in os.fsencode(str(raised.value))


def test_git_env_probe_failure_is_an_unavailable_cell(
    tmp_task: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B3: a failing routing probe is one UNAVAILABLE cell, never an abort.

    The probe failure must surface through grade()'s UNAVAILABLE path (the
    receipt names the cause), so a git-absent environment costs one cell
    instead of aborting the whole batch.
    """

    def fail_probe(argv: list[str], **_kwargs: object) -> object:
        if "--local-env-vars" in argv:
            raise OSError("git missing")
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(grade_module.subprocess, "run", fail_probe)
    receipt = grade(
        tmp_task,
        tmp_task / "fixtures" / "known-good.patch",
        tmp_path / "r.json",
    )
    assert receipt.verdict is Verdict.UNAVAILABLE
    assert "cannot inspect Git environment variables" in receipt.reason


# --- V7 P3 Task 1: hidden-task receipts carry contamination findings ---
# grade() spawns git + the oracle (subprocess), so these live in the
# integration tier alongside the rest of the end-to-end grade tests. The
# receipt round-trip tests stay pure (default tier) in tests/test_receipt.py.

def test_hidden_task_receipt_annotated(tmp_hidden_task: Path, clean_patch: Path) -> None:
    grade(tmp_hidden_task, clean_patch, tmp_hidden_task / "receipt.json")
    data = json.loads((tmp_hidden_task / "receipt.json").read_text())
    assert data["contamination"]["visibility"] == "hidden"
    checks = {c["check"]: c["outcome"] for c in data["contamination"]["checks"]}
    assert checks == {"grader_content_in_patch": "clean"}


def test_visible_task_receipt_unannotated(
    tmp_visible_task: Path, clean_patch: Path
) -> None:
    grade(tmp_visible_task, clean_patch, tmp_visible_task / "receipt.json")
    data = json.loads((tmp_visible_task / "receipt.json").read_text())
    assert "contamination" not in data


def test_contaminated_patch_flags_but_verdict_unchanged(
    tmp_hidden_task: Path, contaminated_patch: Path
) -> None:
    receipt = grade(
        tmp_hidden_task, contaminated_patch, tmp_hidden_task / "receipt.json"
    )
    data = json.loads((tmp_hidden_task / "receipt.json").read_text())
    checks = {c["check"]: c["outcome"] for c in data["contamination"]["checks"]}
    assert checks["grader_content_in_patch"] == "flagged"
    # detection never reclassifies: the verdict is whatever the oracle said
    assert receipt.verdict in (Verdict.PASS, Verdict.FAIL, Verdict.UNAVAILABLE)
