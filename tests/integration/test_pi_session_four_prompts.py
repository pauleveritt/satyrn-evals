"""The real-seam proof: the shipped Pi adapter driven through all four prompts.

Pi is replaced by a deterministic scripted RPC fixture (the V4
substitution pattern): the full session protocol runs through the real
executable seam with zero model. Layer (b) — the real-model smoke — is
the manual runbook, not this test.
"""

import json
import sys
from pathlib import Path

import pytest

from satyrn_evals.session import run_session
from satyrn_evals.session_grader import SessionGrader
from satyrn_evals.session_manifest import load_session_spec
from satyrn_evals.session_record import deepest_feature_milestone

pytestmark = pytest.mark.integration

ADAPTER = Path(__file__).resolve().parents[2] / (
    "src/satyrn_evals/adapters/pi_session.py"
)
FAKE_PI = Path(__file__).resolve().parent / "fake_pi_rpc.py"
TASKS_ROOT = Path(__file__).resolve().parents[2] / "src/satyrn_evals/tasks"
TASK = TASKS_ROOT / "session-mechanics"

FEATURE_CODE = {
    "1": (
        "\n\ndef slugify(text: str) -> str:\n"
        "    \"\"\"Lowercase and join words with single dashes.\"\"\"\n"
        "    return \"-\".join(text.strip().lower().split())\n"
    ),
    "2": (
        "\n\ndef truncate(text: str, width: int) -> str:\n"
        "    \"\"\"Cut text to width, ending with an ellipsis when cut.\"\"\"\n"
        "    if len(text) <= width:\n        return text\n"
        "    return text[: width - 1].rstrip() + \"\u2026\"\n"
    ),
    "3": (
        "\n\ndef pluralize(word: str) -> str:\n"
        "    \"\"\"Naive English plural.\"\"\"\n"
        "    return word + (\"es\" if word.endswith((\"s\", \"x\", \"ch\")) else \"s\")\n"
    ),
    "4": "",
}


def _adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    shim = tmp_path / "pi"
    shim.write_text(
        f"#!/bin/sh\nexec {sys.executable} {FAKE_PI} \"$@\"\n"
    )
    shim.chmod(0o755)
    script = tmp_path / "script.json"
    script.write_text(json.dumps(FEATURE_CODE))
    monkeypatch.setenv("PI_FAKE_SCRIPT", str(script))
    monkeypatch.setenv("PI_FAKE_FILE", "src/textkit/__init__.py")
    return [
        sys.executable,
        str(ADAPTER),
        "--provider",
        "fake",
        "--model",
        "fake-model",
        "--pi-bin",
        str(shim),
    ]


def test_four_prompt_session_through_the_shipped_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv = _adapter(tmp_path, monkeypatch)
    record = run_session(
        task="session-mechanics",
        tasks_root=TASKS_ROOT,
        output=tmp_path,
        adapter_command=argv,
        grader=SessionGrader(task_dir=TASK),
    )
    assert record.code.value in ("COMPLETE",)
    assert record.conversation_id.startswith("pi-")
    assert [s.step_id for s in record.steps] == [
        "add-slugify",
        "add-truncate",
        "add-pluralize",
        "review-and-regression",
    ]
    assert all(s.outcome == "settled" for s in record.steps)
    # compaction, non-vacuous: the fixture always emits it on prompts 2 and 3
    assert record.steps[0].context_events == 0
    assert record.steps[1].context_events == 2
    assert record.steps[2].context_events == 2
    # cumulative union graded through the shipped adapter
    assert [s.feature_verdict for s in record.steps] == ["pass", "pass", "pass", "pass"]
    assert record.steps[-1].preservation_verdict == "pass"
    # review edits nothing: its cumulative patch repeats add-pluralize's
    assert record.steps[3].patch_digest == record.steps[2].patch_digest
    # review does not advance the milestone
    assert deepest_feature_milestone(load_session_spec(TASK), record.steps) == 3


def test_scope_violation_through_the_shipped_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refusal path: the scripted Pi writes outside source_paths on prompt 2.

    The violating checkpoints keep their full patches as evidence, hidden
    grading is skipped for them, and the record ends SCOPE_VIOLATION —
    with the clean four-prompt run above as the required sibling.
    """
    argv = _adapter(tmp_path, monkeypatch)
    monkeypatch.setenv("PI_FAKE_OUTSIDE", "1")
    record = run_session(
        task="session-mechanics",
        tasks_root=TASKS_ROOT,
        output=tmp_path,
        adapter_command=argv,
        grader=SessionGrader(task_dir=TASK),
    )
    assert record.code.value == "SCOPE_VIOLATION"
    assert record.steps[0].scope_violations == ()
    assert record.steps[0].feature_verdict == "pass"
    for step in record.steps[1:]:
        assert "outside.txt" in step.scope_violations
        assert step.feature_verdict is None  # hidden grading skipped
    assert record.steps[-1].preservation_verdict == "pass"  # graded as captured


def test_output_limit_terminal_through_the_shipped_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pi declares stopReason "length" on prompt 2: the adapter must map
    the terminal to output-limit, not settle it (review finding 3)."""
    argv = _adapter(tmp_path, monkeypatch)
    monkeypatch.setenv("PI_FAKE_TERMINAL", "length")
    record = run_session(
        task="session-mechanics",
        tasks_root=TASKS_ROOT,
        output=tmp_path,
        adapter_command=argv,
        grader=SessionGrader(task_dir=TASK),
    )
    assert record.code.value == "OUTPUT_LIMIT"
    assert [s.step_id for s in record.steps] == ["add-slugify", "add-truncate"]
    assert record.steps[0].outcome == "settled"
    assert record.steps[1].outcome == "output-limit"
    assert record.steps[1].patch_digest  # captured after the reap


def test_failed_response_is_agent_error_through_the_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed prompt response surfaces agent-error, not success.

    The tree is unedited, so the overlay cannot collect: the record maps
    to GRADE_UNAVAILABLE while the step's adapter outcome stays
    agent-error — plumbing pass, candidate failure separated.
    """
    argv = _adapter(tmp_path, monkeypatch)
    monkeypatch.setenv("PI_FAKE_RESPONSE_FAIL", "1")
    record = run_session(
        task="session-mechanics",
        tasks_root=TASKS_ROOT,
        output=tmp_path,
        adapter_command=argv,
        grader=SessionGrader(task_dir=TASK),
    )
    assert record.code.value == "GRADE_UNAVAILABLE"
    assert record.steps[0].outcome == "agent-error"


def test_retry_failure_terminal_through_the_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """auto_retry_end{success:false} before agent_settled maps agent-error."""
    argv = _adapter(tmp_path, monkeypatch)
    monkeypatch.setenv("PI_FAKE_RETRY_FAIL", "1")
    record = run_session(
        task="session-mechanics",
        tasks_root=TASKS_ROOT,
        output=tmp_path,
        adapter_command=argv,
    )
    assert record.code.value == "ADAPTER_ERROR"
    assert record.steps[1].outcome == "agent-error"


def test_python_test_run_leaves_no_bytecode_in_the_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session runtime policy: a self-verifying model's pytest run must
    not leave __pycache__ in the evolving checkout (the smoke finding).
    The fake really runs pytest; the ran-marker proves it; the captured
    tree shows no bytecode scope violations and no __pycache__ paths."""
    argv = _adapter(tmp_path, monkeypatch)
    pytest_ran = tmp_path / "pytest-ran"
    monkeypatch.setenv("PI_FAKE_PYTEST", "1")
    monkeypatch.setenv("PI_FAKE_PYTEST_RAN", str(pytest_ran))
    record = run_session(
        task="session-mechanics",
        tasks_root=TASKS_ROOT,
        output=tmp_path,
        adapter_command=argv,
        grader=SessionGrader(task_dir=TASK),
    )
    assert record.code.value == "COMPLETE"
    assert pytest_ran.exists() and pytest_ran.read_text().startswith("rc=0")
    for step in record.steps:
        assert not any("__pycache__" in v for v in step.scope_violations)
        assert step.scope_violations == ()
    session_dir = _session_dir(tmp_path)
    patch = (session_dir / record.steps[-1].patch_path).read_text()
    assert "__pycache__" not in patch


def test_out_of_scope_edit_still_violates_with_the_policy_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The policy must not weaken scope detection: a genuine out-of-scope
    edit still produces SCOPE_VIOLATION while bytecode stays suppressed
    (the sibling of the bytecode-clean test above)."""
    argv = _adapter(tmp_path, monkeypatch)
    monkeypatch.setenv("PI_FAKE_PYTEST", "1")
    monkeypatch.setenv("PI_FAKE_OUTSIDE", "1")
    record = run_session(
        task="session-mechanics",
        tasks_root=TASKS_ROOT,
        output=tmp_path,
        adapter_command=argv,
        grader=SessionGrader(task_dir=TASK),
    )
    assert record.code.value == "SCOPE_VIOLATION"
    assert record.steps[0].scope_violations == ()
    for step in record.steps[1:]:
        assert "outside.txt" in step.scope_violations
        assert not any("__pycache__" in v for v in step.scope_violations)


def test_the_pi_child_inherits_the_runtime_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fake stands in as the adapter's pi child; it writes a marker
    only when PYTHONDONTWRITEBYTECODE is missing, so a missing marker
    proves the setting was inherited through the shipped adapter."""
    argv = _adapter(tmp_path, monkeypatch)
    marker = tmp_path / "env-marker"
    monkeypatch.setenv("PI_FAKE_ENV_MARKER", str(marker))
    record = run_session(
        task="session-mechanics",
        tasks_root=TASKS_ROOT,
        output=tmp_path,
        adapter_command=argv,
    )
    assert record.code.value == "COMPLETE"
    assert not marker.exists()  # the child saw the policy; nothing written


def _session_dir(tmp_path: Path) -> Path:
    dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(dirs) == 1
    return dirs[0]
