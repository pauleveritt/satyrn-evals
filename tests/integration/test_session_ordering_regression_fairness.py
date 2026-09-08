"""The fairness gate: an implementation written only from the prompts passes.

Why this exists (2026-09-08). The task's hidden checks demanded two details its
prompts never stated -- the ellipsis had to be `…` (U+2026) counted inside
`width`, and the first sentence had to have its terminal punctuation stripped.
A live Baseline session failed every checkpoint from step 1 on, with a
`summarize` that was an ordinary reading of what it was asked for. The
repository's standard is that ordinary code reasoning is allowed and hidden
requirements are not, so the prompts were corrected to state both.

`fixtures/prompt-faithful.patch` is the guard against that recurring: it was
written strictly from the prompt text, and it must satisfy every hidden check.
If a hidden check is ever tightened without the prompt following, this row goes
red -- which is the only mechanical way to keep a prompt honest about what
success requires.

The sibling below is what stops it being vacuous: `known-broken` must still
fail. A grader that passed everything would satisfy the gate and mean nothing.
"""

from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.session_manifest import load_session_spec
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASK = (
    Path(__file__).resolve().parents[2]
    / "src/satyrn_evals/tasks/session-ordering-regression"
)


def _all_hidden_selectors() -> tuple[str, ...]:
    spec = load_session_spec(TASK)
    return tuple(s for step in spec.steps for s in step.new_feature_selectors)


def _grade(tmp_path: Path, patch: str, name: str, selectors):
    return grade(
        TASK,
        TASK / "fixtures" / patch,
        tmp_path / f"{name}.json",
        overlay=load_overlay(TASK, load_manifest(TASK)),
        selectors=selectors,
        expected=selectors,
    )


def test_an_implementation_written_from_the_prompts_alone_passes(
    tmp_path: Path,
) -> None:
    """No hidden requirement: what the prompts say is enough to succeed."""
    receipt = _grade(
        tmp_path, "prompt-faithful.patch", "faithful", _all_hidden_selectors()
    )
    assert receipt.verdict is Verdict.PASS, receipt.reason


def test_the_prompt_faithful_implementation_preserves_base(tmp_path: Path) -> None:
    spec = load_session_spec(TASK)
    receipt = grade(
        TASK,
        TASK / "fixtures/prompt-faithful.patch",
        tmp_path / "faithful-pres.json",
        selectors=spec.base_preservation_selectors,
        expected=spec.base_preservation_selectors,
    )
    assert receipt.verdict is Verdict.PASS, receipt.reason


def test_the_gate_still_rejects_a_wrong_implementation(tmp_path: Path) -> None:
    """Sibling: the gate discriminates rather than passing everything."""
    receipt = _grade(
        tmp_path, "known-broken.patch", "broken", _all_hidden_selectors()
    )
    assert receipt.verdict is Verdict.FAIL, receipt.reason


def test_the_prompt_states_what_the_hidden_checks_require(tmp_path: Path) -> None:
    """The two details a solver could not otherwise recover, named in the text.

    A weaker check than the rows above -- it reads the prompt rather than
    running anything -- but it fails fast and says why, where a failing
    fairness run only says a selector went red.
    """
    prompt = load_session_spec(TASK).steps[0].prompt
    assert "…" in prompt, "the ellipsis character is not stated"
    assert "exactly width characters" in prompt, "width accounting is not stated"
    assert "drop that punctuation" in prompt, "punctuation handling is not stated"
