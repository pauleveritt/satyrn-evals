"""V8 qualification gate: the three rows, parametrized over all six tasks.

Base rows grade the raw broken tree the way ``grade()`` grades — the copy's
OWN locked environment is materialized (``uv sync --locked``, never
independently resolved ``--with`` pins), the oracle runs with the hook, and
the verdict-shaped evidence is read from the hook's JSON record, never from
pytest stdout or an exit code. Fixture rows (known-good, known-broken) grade
through the real CLI, exercising materialized-env grading (P3) and
contamination subtraction (P4) end to end. Integration tier: uv + network on
first sync; the planted no-subprocess tripwire forbids this outside
integration.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

pytestmark = pytest.mark.integration

STATES = ["depth-2", "depth-3", "framing-2", "framing-2-edit",
          "misleading-locus", "plausible-wrong-fix"]
ASSERTION_STATES = ["misleading-locus", "plausible-wrong-fix", "depth-2", "depth-3"]
COLLECTION_ABORT = ["framing-2", "framing-2-edit"]

# spec §2, re-derived on the vendored bases in slice 1 (spec §14 command).
EXPECTED_BASE_FAILURES = {
    "misleading-locus": ["test_posted_complaint_appears_on_complaints_board"],
    "plausible-wrong-fix": ["test_post_complaint_redirects_to_complaints_board"],
    "depth-2": [
        "test_home_html_element_declares_english_language",
        "test_complaints_board_preserves_the_shared_layout",
        "test_post_complaint_redirects_to_complaints_board",
    ],
    "depth-3": [
        "test_home_html_element_declares_english_language",
        "test_complaints_board_preserves_the_shared_layout",
        "test_complaint_model_contract_is_preserved",
        "test_post_complaint_redirects_to_complaints_board",
    ],
}


def _task(state: str) -> Path:
    return DEFAULT_TASKS_ROOT / f"agentclinic-repair-{state}"


def _cli() -> str:
    """The installed console script, resolved beside the running interpreter.

    ``sys.executable`` under ``uv run pytest`` is the project venv's python,
    whose bin holds the ``satyrn-evals`` entry point; resolving the symlink
    would follow to uv's managed base python, which lacks it.
    """
    return os.fspath(Path(sys.executable).parent / "satyrn-evals")


def _grade(task_dir: Path, patch_path: Path, tmp_path: Path) -> dict:
    receipt_path = tmp_path / "receipt.json"
    subprocess.run(
        [_cli(), "grade", task_dir.name, str(patch_path),
         "--receipt", str(receipt_path), "--tasks-root", str(task_dir.parent)],
        check=True, capture_output=True)
    return json.loads(receipt_path.read_text())


def _run_base_with_hook(state: str, tmp_path: Path) -> dict:
    """Raw broken tree + overlay, graded the way grade() grades: the copy's
    OWN locked environment is materialized (uv sync --locked — never
    independently resolved --with pins), the oracle runs with the hook, and
    the verdict-shaped evidence is read from the hook's record file, never
    from pytest stdout or an exit code."""
    import satyrn_evals
    task_dir = _task(state)
    d = tmp_path / state
    shutil.copytree(task_dir / "base", d)
    shutil.copy(task_dir / "overlay" / "test_acceptance.py", d / "test_acceptance.py")
    subprocess.run(["uv", "sync", "--locked"], cwd=d, check=True, capture_output=True)
    hook = tmp_path / f"hook-{state}.json"
    env = dict(os.environ)
    env["SATYRN_ORACLE_RESULT"] = str(hook)
    env["PYTHONPATH"] = os.fspath(Path(satyrn_evals.__file__).resolve().parent.parent)
    env["PATH"] = os.fspath(d / ".venv" / "bin") + os.pathsep + env.get("PATH", "")
    subprocess.run(
        [os.fspath(d / ".venv" / "bin" / "python"), "-m", "pytest", "-p",
         "satyrn_evals.oracle_hook", "-q", "test_acceptance.py"],
        cwd=d, env=env, capture_output=True)
    return json.loads(hook.read_text())


@pytest.mark.parametrize("state", ASSERTION_STATES)
def test_base_row_reproduces_recorded_failing_set(state: str, tmp_path: Path) -> None:
    data = _run_base_with_hook(state, tmp_path)
    outcomes = data["outcomes"]
    assert len(outcomes) == 13, (state, len(outcomes))
    # every expected id is present; the recorded failing set is exactly the
    # non-passed ones (the hook record, not stdout, is the verdict)
    non_passed = {tid for tid, out in outcomes.items() if out != "passed"}
    expected = {f"test_acceptance.py::{t}" for t in EXPECTED_BASE_FAILURES[state]}
    assert non_passed == expected, (state, non_passed)


@pytest.mark.parametrize("state", COLLECTION_ABORT)
def test_base_row_is_collection_abort_not_unavailable(state: str, tmp_path: Path) -> None:
    data = _run_base_with_hook(state, tmp_path)
    assert data["collect_errors"], state  # hook records the abort as evidence


@pytest.mark.parametrize("state", STATES)
def test_known_good_passes_13_of_13(state: str, tmp_path: Path) -> None:
    task_dir = _task(state)
    receipt = _grade(task_dir, task_dir / "fixtures" / "known-good.patch", tmp_path)
    assert receipt["verdict"] == "pass", state
    assert receipt["evidence"]["counts"]["passed"] == 13, state
    assert receipt["evidence"]["counts"]["failed"] == 0, state


@pytest.mark.parametrize("state", STATES)
def test_known_broken_fails(state: str, tmp_path: Path) -> None:
    task_dir = _task(state)
    receipt = _grade(task_dir, task_dir / "fixtures" / "known-broken.patch", tmp_path)
    assert receipt["verdict"] == "fail", state
    failing = [tid for tid, out in receipt["evidence"]["outcomes"].items()
               if out != "passed"]
    assert failing, state  # the receipt names the failing ids
