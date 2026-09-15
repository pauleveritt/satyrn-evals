"""Offline qualification's pure judgements and the candidate list."""

import pytest

from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.qualify import (
    CEILING_CANDIDATES,
    FLOOR_CANDIDATES,
    judge_fixture,
    judge_harvest,
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
