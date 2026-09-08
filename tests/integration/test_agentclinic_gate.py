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
import time
from pathlib import Path

import pytest
from test_agentclinic_manifests import (  # type: ignore[missing-import]  # pytest sibling resolution (tests/ on sys.path)
    QUALIFIED,
)

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.verdict import load_hook_result

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


def _grade(task_dir: Path, patch_path: Path, tmp_path: Path, *, check: bool = True) -> dict:
    receipt_path = tmp_path / "receipt.json"
    subprocess.run(
        [_cli(), "grade", task_dir.name, str(patch_path),
         "--receipt", str(receipt_path), "--tasks-root", str(task_dir.parent)],
        check=check, capture_output=True)
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


def _qualification_record(state: str) -> dict:
    path = _task(state) / "qualification.json"
    return json.loads(path.read_text())


def _run_qualification_suite(
    task_dir: Path,
    tmp_path: Path,
    *,
    argv: list[str],
    patch: Path | None,
    include_hidden_overlay: bool,
) -> dict:
    """Run one declared suite in a fresh task copy and validate fresh hook data.

    The public route uses its manifest argv unchanged. Its plugin enters through
    the environment, as it does for qualification, rather than by changing the
    command the solver is entitled to run.
    """
    import satyrn_evals
    from satyrn_evals.grade import _hook_import_path
    from satyrn_evals.overlay import load_overlay, materialize_overlay

    tmp_path.mkdir(parents=True)
    work = tmp_path / "work"
    shutil.copytree(task_dir / "base", work)
    if patch is not None:
        subprocess.run(
            ["git", "init", "-q"], cwd=work, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "apply", "-"],
            input=patch.read_bytes(),
            cwd=work,
            check=True,
            capture_output=True,
        )
    if include_hidden_overlay:
        materialize_overlay(load_overlay(task_dir, load_manifest(task_dir)), work)
    subprocess.run(["uv", "sync", "--locked"], cwd=work, check=True, capture_output=True)
    hook_path = tmp_path / "hook.json"
    env = dict(os.environ)
    env["SATYRN_ORACLE_RESULT"] = str(hook_path)
    env["PYTEST_PLUGINS"] = "satyrn_evals.oracle_hook"
    env["PATH"] = os.fspath(work / ".venv" / "bin") + os.pathsep + env.get("PATH", "")
    env["PYTHONPATH"] = os.fspath(
        _hook_import_path(work, Path(satyrn_evals.__file__).resolve().parent)
    )
    started = time.time()
    subprocess.run(argv, cwd=work, env=env, capture_output=True)
    hook = load_hook_result(hook_path, started)
    return {
        "executed_test_ids": list(hook.executed_test_ids),
        "outcomes": hook.outcomes,
        "collect_errors": list(hook.collect_errors),
    }


def _nonpassing_ids(data: dict) -> list[str]:
    return sorted(test_id for test_id, outcome in data["outcomes"].items() if outcome != "passed")


@pytest.mark.parametrize("state", QUALIFIED)
def test_r3_qualification_witnesses_match_the_authored_record(
    state: str, tmp_path: Path
) -> None:
    """Each R3 witness row is fresh hook evidence, not command status."""
    task_dir = _task(state)
    manifest = load_manifest(task_dir)
    record = _qualification_record(state)

    assert record["task"] == manifest.name
    assert record["rung"] == "R3"
    assert "public_command" not in record
    assert manifest.public_suite
    assert {behavior["assessment"] for behavior in record["behaviors"]} == {"justified"}
    assert {
        check
        for behavior in record["behaviors"]
        for check in behavior["hidden_checks"]
    } == set(manifest.expected_test_ids)

    assert len(record["witnesses"]) >= 3, state
    for witness in record["witnesses"]:
        patch = task_dir / witness["patch"] if witness["patch"] else None
        public = _run_qualification_suite(
            task_dir,
            tmp_path / witness["id"] / "public",
            argv=list(manifest.public_suite),
            patch=patch,
            include_hidden_overlay=False,
        )
        hidden = _run_qualification_suite(
            task_dir,
            tmp_path / witness["id"] / "hidden",
            argv=[*manifest.oracle, *manifest.expected_test_ids],
            patch=patch,
            include_hidden_overlay=True,
        )

        assert public["collect_errors"] == [], witness["id"]
        assert public["executed_test_ids"], witness["id"]
        assert public["executed_test_ids"] == sorted(witness["public"]["expected_executed_ids"])
        assert "skipped" not in public["outcomes"].values(), witness["id"]
        assert _nonpassing_ids(public) == sorted(witness["public"]["expected_nonpassing_ids"])
        assert hidden["collect_errors"] == [], witness["id"]
        assert hidden["executed_test_ids"], witness["id"]
        assert hidden["executed_test_ids"] == sorted(manifest.expected_test_ids)
        assert "skipped" not in hidden["outcomes"].values(), witness["id"]
        assert _nonpassing_ids(hidden) == sorted(witness["hidden_expected_nonpassing_ids"])


def test_depth_3_r3_record_maps_the_declared_omission_to_its_hidden_check() -> None:
    record = _qualification_record("depth-3")
    behaviors = {behavior["id"]: behavior for behavior in record["behaviors"]}
    incomplete = next(witness for witness in record["witnesses"] if witness["id"] == "partial-no-303")

    assert incomplete["omits_behavior_ids"] == ["see-other-redirect"]
    omitted = behaviors["see-other-redirect"]
    assert incomplete["hidden_expected_nonpassing_ids"] == omitted["hidden_checks"]
    assert incomplete["public"]["expected_nonpassing_ids"] == omitted["public_tests"]


def test_misleading_locus_r3_record_names_the_exact_preservation_checks_it_breaks() -> None:
    """The wrong repair edits the board template instead of the handler.

    It is a discriminating witness only if the record names *which* preservation
    checks it breaks: an overall failure is not evidence, because the seam it
    leaves unrepaired fails anyway. The two named sets must exhaust the
    witness's failing set, and each must be a check the behavior it is filed
    under actually owns.
    """
    record = _qualification_record("misleading-locus")
    behaviors = {behavior["id"]: behavior for behavior in record["behaviors"]}
    wrong = next(w for w in record["witnesses"] if w["id"] == "known-broken")

    assert wrong["omits_behavior_ids"] == ["record-posted-complaint"]
    assert wrong["violates_behavior_ids"] == ["preserve-page-board-and-redirect-behavior"]
    assert wrong["violated_hidden_checks"] == [
        "test_acceptance.py::test_complaints_board_still_renders_seed_complaint_details"
    ]

    violated = set(wrong["violated_hidden_checks"])
    assert violated <= set(behaviors["preserve-page-board-and-redirect-behavior"]["hidden_checks"])
    omitted = set(behaviors["record-posted-complaint"]["hidden_checks"])
    assert violated.isdisjoint(omitted)
    assert sorted(violated | omitted) == sorted(wrong["hidden_expected_nonpassing_ids"])

    # The sibling direction, from the row that ISOLATES the change: `base` and
    # `known-broken` differ by exactly this witness's patch (the template, and
    # nothing else), so a check that is silent at base and fires here tracks
    # the wrong repair rather than the unrepaired seam. `known-good` differs in
    # two ways at once and cannot make that argument on its own; it is asserted
    # here only as the all-clear end of the range. Naming the checks rather
    # than comparing to `[]` is deliberate: an equality against the empty list
    # stays green if `violated_hidden_checks` is renamed to something no
    # witness ever fails.
    base = next(w for w in record["witnesses"] if w["id"] == "base")
    good = next(w for w in record["witnesses"] if w["id"] == "known-good")
    assert violated.isdisjoint(base["hidden_expected_nonpassing_ids"])
    assert violated.isdisjoint(good["hidden_expected_nonpassing_ids"])
    assert good["hidden_expected_nonpassing_ids"] == []


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


@pytest.mark.parametrize("state", STATES)
def test_contamination_pairs_fire_and_stay_silent(state: str, tmp_path: Path) -> None:
    task_dir = _task(state)
    overlay_text = (task_dir / "overlay" / "test_acceptance.py").read_text()
    lines = [ln for ln in overlay_text.splitlines() if ln.strip()][:5]
    # a NEW test file under an allowlisted path (tests/), valid git format:
    # adding lines to an existing file with no context is malformed, so the
    # leak is a new-file patch
    leak = tmp_path / "leak.patch"
    leak.write_text(
        f"--- /dev/null\n+++ b/tests/test_leak.py\n@@ -0,0 +1,{len(lines)} @@\n"
        + "".join(f"+{ln}\n" for ln in lines)
    )
    # eligibility first: the grade RAN and the contamination scan produced an
    # annotation — never a silent oracle or a missing section. The two
    # collection-abort rows exit 3 (unavailable) by design, so this row's
    # grade tolerates it and reads the receipt it still writes.
    firing = _grade(task_dir, leak, tmp_path,
                    check=state not in COLLECTION_ABORT)
    assert "contamination" in firing, state
    # Verdict by state class: the four assertion-state bases collect and fail
    # specific tests (fail). The two collection-abort bases cannot collect
    # (models missing/renamed), so the hook's executed==expected rule yields
    # unavailable (verdict.py compute_verdict) — the leak-only patch does not
    # recreate the model module; that is why their known-broken fixtures add a
    # collecting stub.
    if state in ASSERTION_STATES:
        assert firing["verdict"] == "fail", state
    else:
        assert firing["verdict"] == "unavailable", state
        assert "executed tests mismatch expected" in firing["reason"], state
    check = firing["contamination"]["checks"][0]
    assert check["check"] == "grader_content_in_patch", state
    assert check["outcome"] == "flagged", state  # overlay-only block, not in base

    good = _grade(task_dir, task_dir / "fixtures" / "known-good.patch", tmp_path)
    good_check = good["contamination"]["checks"][0]
    assert good_check["outcome"] == "clean", state  # known-good stays silent
