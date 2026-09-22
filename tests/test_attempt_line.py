"""`attempt()` wires the record's declared line through to the workspace
boundary and back into the durable record, for both arms.

Default tier: the workspace boundary is faked exactly as `test_attempt.py`
fakes it (`prepare_workspace`/`run_prepared_command`/`release_workspace`),
so no process or git runs; only the wiring is under test here.
"""

import json
from pathlib import Path
from typing import Any

import pytest

import satyrn_evals.attempt as attempt_module
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.budget import LineBudget, LineCrossing
from satyrn_evals.receipt import Receipt
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import LINE_PATCH_NAME, WorkspaceCode, WorkspaceResult


def _grade_pass(*_args: object, **_kwargs: object) -> Receipt:
    return Receipt(task="t", patch_digest="a" * 64, verdict=Verdict.PASS, reason="", evidence=None)


GOOD_PATCH = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)


class _FakeLease:
    def __init__(self, prepared: dict[str, Any]) -> None:
        self.prepared = prepared
        self.parent = Path("/tmp/fake-prepared-workspace")
        self.base_sha = "b" * 40
        self._environment = dict(prepared.get("environment", {}))


def _install(monkeypatch: pytest.MonkeyPatch, run: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def prepare(**kwargs: Any) -> _FakeLease:
        return _FakeLease(kwargs)

    def run_prepared(lease: _FakeLease, **kwargs: Any) -> WorkspaceResult:
        calls.append(kwargs)
        return run(lease, **kwargs)

    def release_prepared(lease: _FakeLease, **kwargs: Any) -> str | None:
        return None

    monkeypatch.setattr(attempt_module, "prepare_workspace", prepare)
    monkeypatch.setattr(attempt_module, "run_prepared_command", run_prepared)
    monkeypatch.setattr(attempt_module, "release_workspace", release_prepared)
    return calls


def _task(tasks_root: Path) -> Path:
    task_dir = tasks_root / "t"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "base" / "solution.py").write_text("def double(n): return n\n")
    (task_dir / "fixtures").mkdir()
    (task_dir / "fixtures" / "known-good.patch").write_text(GOOD_PATCH)
    (task_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "t", "contract": "Fix it.", "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["test_solution.py::test_one"], "source_paths": ["solution.py"],
                "fixtures": {"known_good": "fixtures/known-good.patch"},
            }
        )
    )
    return task_dir


def test_attempt_without_a_line_budget_passes_none_and_records_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(lease: _FakeLease, **kwargs: Any) -> WorkspaceResult:
        Path(lease._environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(lease._environment[attempt_module.TRANSCRIPT_ENV]).write_text("did it\n")
        return WorkspaceResult(WorkspaceCode.OK, "attempt command completed", 0, "b" * 40)

    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    calls = _install(monkeypatch, run)
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts", command=["fake-agent"], timeout=10.0,
    )
    assert calls[0]["line_budget"] is None
    assert calls[0]["engine_arm"] is False
    assert record.line_crossed is None
    assert record.line_patch_path is None
    assert record.line_harvest_error is None


def test_attempt_passes_the_line_budget_and_a_line_patch_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    line = LineBudget(output_tokens=16000, turns=24)

    def run(lease: _FakeLease, **kwargs: Any) -> WorkspaceResult:
        Path(lease._environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(lease._environment[attempt_module.TRANSCRIPT_ENV]).write_text("did it\n")
        return WorkspaceResult(WorkspaceCode.OK, "attempt command completed", 0, "b" * 40)

    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    calls = _install(monkeypatch, run)
    attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts", command=["fake-agent"], timeout=10.0,
        line_budget=line,
    )
    assert calls[0]["line_budget"] is line
    assert calls[0]["line_patch"].name == LINE_PATCH_NAME


def test_attempt_records_a_harvested_line_crossing_from_the_workspace_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=10, at="2026-09-19T00:00:00+00:00")

    def run(lease: _FakeLease, **kwargs: Any) -> WorkspaceResult:
        Path(lease._environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(lease._environment[attempt_module.TRANSCRIPT_ENV]).write_text("did it\n")
        kwargs["line_patch"].write_text("diff --git a/x b/x\n")
        return WorkspaceResult(
            WorkspaceCode.OK, "attempt command completed", 0, "b" * 40,
            line_crossed=crossing, line_patch_written=True,
        )

    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    _install(monkeypatch, run)
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts", command=["fake-agent"], timeout=10.0,
        line_budget=LineBudget(16000, 24),
    )
    assert record.line_crossed == crossing
    assert record.line_patch_path == LINE_PATCH_NAME
    assert record.line_harvest_error is None


def test_attempt_records_a_line_crossing_even_on_a_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cell can cross the line and still end refused (e.g. NO_PATCH)."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    crossing = LineCrossing(by="turns", output_tokens=10, turn=25, at="2026-09-19T00:00:00+00:00")

    def run(lease: _FakeLease, **kwargs: Any) -> WorkspaceResult:
        # No patch/transcript written -- this cell refuses NO_PATCH.
        return WorkspaceResult(
            WorkspaceCode.OK, "attempt command completed", 0, "b" * 40, line_crossed=crossing,
        )

    _install(monkeypatch, run)
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts", command=["fake-agent"], timeout=10.0,
        line_budget=LineBudget(16000, 24),
    )
    assert record.code is AttemptCode.NO_PATCH
    assert record.line_crossed == crossing
    assert record.line_patch_path is None


def test_attempt_never_carries_both_a_line_patch_path_and_a_line_harvest_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N2: `_harvest_patch` can return `(False, error)` with `line.diff`
    already present on disk (a write that creates the file and then fails,
    or any other race) -- `line_patch_path` must never be set alongside
    `line_harvest_error`, or `AttemptRecord` refuses the combination and the
    whole cell crashes instead of writing attempt.json."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=10, at="2026-09-19T00:00:00+00:00")

    def run(lease: _FakeLease, **kwargs: Any) -> WorkspaceResult:
        Path(lease._environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(lease._environment[attempt_module.TRANSCRIPT_ENV]).write_text("did it\n")
        # A partial/stale line.diff is present on disk despite the harvest
        # itself having failed -- the exact shape `_harvest_patch` returns
        # when a write raises after creating the file.
        kwargs["line_patch"].write_text("diff --git a/x b/x\n")
        return WorkspaceResult(
            WorkspaceCode.OK, "attempt command completed", 0, "b" * 40,
            line_crossed=crossing, line_patch_written=False,
            line_harvest_error="OSError: No space left on device",
        )

    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    _install(monkeypatch, run)
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts", command=["fake-agent"], timeout=10.0,
        line_budget=LineBudget(16000, 24),
    )
    assert record.line_crossed == crossing
    assert record.line_patch_path is None
    assert record.line_harvest_error == "OSError: No space left on device"


def test_attempt_marks_the_engine_wrapper_command_as_the_engine_arm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    engine_repo = tmp_path / "engine"

    def run(lease: _FakeLease, **kwargs: Any) -> WorkspaceResult:
        Path(lease._environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(lease._environment[attempt_module.TRANSCRIPT_ENV]).write_text("did it\n")
        return WorkspaceResult(WorkspaceCode.OK, "attempt command completed", 0, "b" * 40)

    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    calls = _install(monkeypatch, run)
    attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts",
        command=["uv", "run", "--project", str(engine_repo), "satyrn-engine"], timeout=10.0,
        line_budget=LineBudget(16000, 24),
    )
    assert calls[0]["engine_arm"] is True
