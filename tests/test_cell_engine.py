"""The Engine arm's checkout: where it resolves, and the refusals that need no git.

The checks that run ``git`` live in ``tests/integration/test_cell_engine.py``;
these run no subprocess, so the default tier stays clean.
"""

from dataclasses import replace
from pathlib import Path

from satyrn_evals.arms import load_arm
from satyrn_evals.cell_engine import (
    checkout_root,
    default_checkout,
    engine_checkout_problems,
)

ARMS = Path(__file__).resolve().parents[1] / "arms"
ENGINE_ARM = ARMS / "engine-ornith15-9b.json"


def test_checkout_root_prefers_the_arms_own_path() -> None:
    arm = replace(load_arm(ENGINE_ARM), argv=("satyrn-evals-attempt-engine", "--engine-repo", "/engines/a"))
    assert checkout_root(arm, {"SATYRN_ENGINE_REPO": "/engines/b"}) == Path("/engines/a")


def test_checkout_root_falls_back_to_the_variable() -> None:
    arm = load_arm(ENGINE_ARM)
    assert checkout_root(arm, {"SATYRN_ENGINE_REPO": "/engines/b"}) == Path("/engines/b")


def test_checkout_root_defaults_to_the_sibling() -> None:
    arm = load_arm(ENGINE_ARM)
    default = default_checkout({})
    assert checkout_root(arm, {}) == default
    assert default.name == "satyrn-engine"


def test_a_baseline_arm_has_no_checkout_to_check() -> None:
    baseline = load_arm(ARMS / "baseline-ornith15-9b.json")
    assert engine_checkout_problems(baseline, {}) == []


def test_a_missing_engine_checkout_is_a_problem() -> None:
    arm = load_arm(ENGINE_ARM)
    problems = engine_checkout_problems(arm, {"SATYRN_ENGINE_REPO": "/no/such/engine"})
    assert len(problems) == 1
    assert "missing or is not an engine tree" in problems[0]
    assert "just fetch-engine" in problems[0]
