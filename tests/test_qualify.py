"""Offline qualification's pure judgements and the candidate list."""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.qualify import (
    CEILING_CANDIDATES,
    FLOOR_CANDIDATES,
    SELF_HOSTED_CONVENTION_FILES,
    convention_files_patch,
    judge_fixture,
    judge_harvest,
    judge_prompt,
    prompt_paths,
)
from satyrn_evals.qualify_fake_pi import committed_paths
from satyrn_evals.receipt import Receipt
from satyrn_evals.verdict import Verdict

IDS = ("t.py::a", "t.py::b")
GOOD_PATCH = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n"


def _receipt(verdict: Verdict, *, executed: tuple[str, ...] = IDS, errors: int = 0, evidence: bool = True) -> Receipt:
    data = {"executed_test_ids": list(executed), "outcomes": {}, "counts": {"passed": 0, "failed": 0, "error": errors, "skipped": 0}}
    return Receipt("t", "d" * 64, verdict, "", data if evidence else None)  # type: ignore[arg-type]


def test_known_good_qualifies_when_it_passes_every_expected_test_without_errors() -> None:
    assert judge_fixture("known-good", _receipt(Verdict.PASS), expect=Verdict.PASS, expected_ids=IDS).passed


@pytest.mark.parametrize(
    "receipt",
    [_receipt(Verdict.PASS, errors=1), _receipt(Verdict.PASS, executed=IDS[:1]), _receipt(Verdict.FAIL), _receipt(Verdict.UNAVAILABLE, evidence=False)],
)
def test_known_good_does_not_qualify_otherwise(receipt: Receipt) -> None:
    assert not judge_fixture("known-good", receipt, expect=Verdict.PASS, expected_ids=IDS).passed


def test_known_broken_qualifies_when_it_fails_on_behaviour() -> None:
    assert judge_fixture("known-broken", _receipt(Verdict.FAIL), expect=Verdict.FAIL, expected_ids=IDS).passed


@pytest.mark.parametrize("receipt", [_receipt(Verdict.FAIL, errors=2), _receipt(Verdict.PASS)])
def test_known_broken_does_not_qualify_when_it_errors_or_passes(receipt: Receipt) -> None:
    assert not judge_fixture("known-broken", receipt, expect=Verdict.FAIL, expected_ids=IDS).passed


def test_a_whole_graded_harvest_qualifies() -> None:
    assert judge_harvest(AttemptCode.OK, Verdict.PASS, GOOD_PATCH, GOOD_PATCH).passed


@pytest.mark.parametrize(
    ("code", "verdict", "patch"),
    [(AttemptCode.NO_PATCH, None, None), (AttemptCode.OK, Verdict.FAIL, GOOD_PATCH), (AttemptCode.OK, Verdict.PASS, GOOD_PATCH.replace("x.py", "y.py"))],
)
def test_a_partial_or_failing_harvest_does_not_qualify(code: AttemptCode, verdict: Verdict | None, patch: str | None) -> None:
    assert not judge_harvest(code, verdict, patch, GOOD_PATCH).passed


def test_the_fake_commits_half_of_several_files_and_a_lone_file_only_when_it_existed() -> None:
    assert committed_paths(["c", "a", "b"], set()) == ["a"]
    assert committed_paths(["b", "a"], set()) == ["a"]
    assert committed_paths(["a"], {"a"}) == ["a"]
    assert committed_paths(["a"], set()) == []


@pytest.mark.parametrize(("name", "rung"), [*CEILING_CANDIDATES.items(), *FLOOR_CANDIDATES.items()])
def test_every_candidate_is_bundled_hidden_and_carries_its_rung(name: str, rung: str) -> None:
    manifest = load_manifest(DEFAULT_TASKS_ROOT / name)
    assert manifest.oracle_visibility == "hidden"
    assert rung in manifest.contracts


def test_a_harvest_with_the_convention_files_qualifies_only_when_grading_dropped_them() -> None:
    patch = convention_files_patch(("PROVENANCE.md",)) + GOOD_PATCH
    assert parse_patch_paths(patch) == ("PROVENANCE.md", "x.py")
    assert judge_harvest(AttemptCode.OK, Verdict.PASS, patch, GOOD_PATCH, extra=("PROVENANCE.md",), dropped=("PROVENANCE.md",)).passed
    assert not judge_harvest(AttemptCode.OK, Verdict.PASS, patch, GOOD_PATCH, extra=("PROVENANCE.md",)).passed
    assert not judge_harvest(AttemptCode.OK, Verdict.UNAVAILABLE, patch, GOOD_PATCH, extra=("PROVENANCE.md",), dropped=()).passed


PROMPT = """Task 9: The review script

Files:
- Create: `tools/review.py`, `tests/`
- Modify: `src/cli.py` (add `launch --check RECORD`)

Step 2: Run `uv run pytest tests/ tests/test_cli.py -q > /tmp/log 2>&1` → FAIL
"""


def _base(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    (base / "tests").mkdir(parents=True)
    (base / "tests" / "test_cli.py").write_text("")
    (base / "src").mkdir()
    (base / "src" / "cli.py").write_text("")
    return base


def test_prompt_paths_are_the_files_lines_and_the_pytest_arguments() -> None:
    assert prompt_paths(PROMPT) == ["tools/review.py", "tests/", "src/cli.py", "tests/", "tests/test_cli.py"]


def test_a_prompt_whose_paths_all_resolve_qualifies(tmp_path: Path) -> None:
    check = judge_prompt({"R1-plan": PROMPT}, ("tools/review.py", "src/cli.py", "tests"), _base(tmp_path))
    assert check.passed, check.detail


@pytest.mark.parametrize(
    ("prompt", "detail"),
    [
        (PROMPT.replace("`tests/`", "`its test module`"), "retired stand-in"),
        (PROMPT.replace("`tests/`", "`tests/test_review.py`"), "tests/test_review.py"),
        (PROMPT.replace("pytest tests/ ", "pytest its/ "), "its/"),
        (PROMPT.replace("`tools/review.py`", "`tools/other.py`"), "tools/other.py"),
    ],
)
def test_a_prompt_with_the_stand_in_or_an_unresolved_path_does_not_qualify(tmp_path: Path, prompt: str, detail: str) -> None:
    check = judge_prompt({"R1-plan": prompt}, ("tools/review.py", "src/cli.py", "tests"), _base(tmp_path))
    assert not check.passed and detail in check.detail


def test_a_task_without_an_r1_plan_rung_has_no_prompt_to_judge(tmp_path: Path) -> None:
    assert judge_prompt({"R1": "its test module"}, ("x.py",), tmp_path).passed


@pytest.mark.parametrize("name", [*CEILING_CANDIDATES, *FLOOR_CANDIDATES])
def test_every_candidate_prompt_qualifies(name: str) -> None:
    manifest = load_manifest(DEFAULT_TASKS_ROOT / name)
    check = judge_prompt(manifest.contracts, manifest.source_paths, DEFAULT_TASKS_ROOT / name / "base")
    assert check.passed, check.detail


@pytest.mark.parametrize("name", [*CEILING_CANDIDATES, *FLOOR_CANDIDATES])
def test_every_generated_candidate_ignores_the_convention_files_and_no_other_task_ignores_any(name: str) -> None:
    generated = "generator" in json.loads((DEFAULT_TASKS_ROOT / name / "manifest.json").read_text())
    assert load_manifest(DEFAULT_TASKS_ROOT / name).ignored_paths == (SELF_HOSTED_CONVENTION_FILES if generated else ())
