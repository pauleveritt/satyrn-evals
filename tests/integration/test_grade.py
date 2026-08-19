"""End-to-end grading with a temporary task. Real git, real oracle subprocess."""

import json
import subprocess
from pathlib import Path

import pytest

import satyrn_evals.grade as grade_module
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
    def fail_init(
        *_args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        raise failure

    monkeypatch.setattr(grade_module.subprocess, "run", fail_init)

    with pytest.raises(ApplyError, match="cannot run git"):
        grade_module._run_oracle(
            load_manifest(tmp_task),
            tmp_task,
            GOOD_PATCH,
        )
