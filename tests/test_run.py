"""run: repeat the attempt seam n times and write a counts-only summary.

The default-tier tests monkeypatch ``attempt`` with a double that creates
the attempt directory, writes a receipt.json, and returns a record whose
``attempt_dir`` names that directory — run reads the cell identity from
the record, never from a directory listing. The end-to-end fake-seam
variant lives in tests/integration/test_run.py.
"""

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

import satyrn_evals.run as run_module
from satyrn_evals.attempt import attempt_dir_name
from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    write_attempt_record,
)
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.verdict import Verdict

HIDDEN_TASK_NAME = "session-mechanics"
# A grade-produced hidden receipt: the patch scanned clean against the overlay.
_CLEAN_RECEIPT = (
    '{"verdict": "pass", "contamination": {"visibility": "hidden", '
    '"checks": [{"check": "grader_content_in_patch", "outcome": "clean", '
    '"evidence": []}]}}'
)


def ok_record(
    cell_name: str,
    *,
    task: str = "format_number",
    command: tuple[str, ...] = ("fake",),
    timeout: float = 123.0,
) -> AttemptRecord:
    return AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.OK,
        message="ok",
        task=task,
        command=command,
        command_exit=0,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest="a" * 64,
        transcript_digest="b" * 64,
        verdict=Verdict.PASS,
        receipt_path="receipt.json",
        timeout=timeout,
        workspace_base_sha="c" * 40,
        attempt_dir=cell_name,
    )


def _fake_attempt(receipt_text: str = '{"verdict": "pass"}'):
    """A non-spawning attempt double bound to one directory identity.

    Mirrors attempt()'s contract end to end on disk: run() hands the double
    task/output/command/timeout as keyword arguments (exactly as it calls
    attempt()), so the double creates the <task>-<stamp> directory holding
    receipt.json AND attempt.json, and returns a record whose attempt_dir
    names it.
    """

    def fake(
        *, task: str, tasks_root: Path, output: Path, command: list[str],
        timeout: float,
    ) -> AttemptRecord:
        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name(task, datetime.now(UTC))
        cell_dir = output / name
        cell_dir.mkdir()
        (cell_dir / "receipt.json").write_text(receipt_text, encoding="utf-8")
        record = ok_record(name, task=task, command=tuple(command),
                           timeout=timeout)
        write_attempt_record(cell_dir / "attempt.json", record)
        return record

    return fake


def test_run_calls_attempt_n_times_and_writes_summary(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[str] = []
    fake = _fake_attempt()

    def recording_fake(**kwargs):
        calls.append(kwargs["task"])
        return fake(**kwargs)

    monkeypatch.setattr(run_module, "attempt", recording_fake)
    summary = run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=tmp_path,
        command=["fake"], n=2, timeout=1.5,
    )
    assert len(calls) == 2
    assert summary.n == 2 and summary.attempted == 2 and summary.refused == 0
    assert len(summary.cells) == 2
    assert (tmp_path / "summary.json").exists()


def test_run_names_cells_from_recorded_attempt_dirs(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    summary = run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out",
        command=["fake"],
        n=3,
    )
    assert len(summary.cells) == 3
    assert all(name.startswith("format_number-") for name in summary.cells)
    # cell names are the record's own identities and match the on-disk dirs
    assert sorted(summary.cells) == sorted(
        p.name for p in (tmp_path / "out").iterdir()
        if p.name.startswith("format_number-")
    )
    assert summary.oracle_visibility == "visible"
    assert summary.contamination is None


def test_run_tolerates_sibling_entries_in_the_output_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """A pre-existing or concurrent sibling entry never corrupts the cells.

    Cell provenance comes from the attempt record's attempt_dir, not from a
    before/after listing of the shared output directory.
    """
    output = tmp_path / "out"
    output.mkdir()
    (output / "stray-sibling").mkdir()
    (output / "other-task-1").mkdir()
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    summary = run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=output,
        command=["fake"], n=2,
    )
    assert len(summary.cells) == 2
    assert all(name.startswith("format_number-") for name in summary.cells)
    assert "stray-sibling" not in summary.cells
    assert "other-task-1" not in summary.cells
    assert (output / "summary.json").exists()


def test_run_on_hidden_task_tallies_contamination(
    tmp_path: Path, monkeypatch
) -> None:
    """Default-tier sibling: run() against a hidden manifest still tallies.

    The hidden task's manifest marks the oracle hidden, so run() must produce
    the contamination section even when the seam is faked in-process (the
    non-spawning double writes graded, contamination-bearing receipts). The
    spawning end-to-end twin lives in tests/integration/test_run.py.
    """
    monkeypatch.setattr(run_module, "attempt", _fake_attempt(
        receipt_text=_CLEAN_RECEIPT
    ))
    summary = run_module.run(
        task=HIDDEN_TASK_NAME,
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out",
        command=["fake"],
        n=2,
    )
    assert summary.oracle_visibility == "hidden"
    assert summary.contamination is not None
    assert summary.contamination == {
        "graded": 2, "flagged": 0, "clean": 2, "unmeasured": 0
    }
    assert summary.contamination["graded"] == (
        summary.contamination["flagged"]
        + summary.contamination["clean"]
        + summary.contamination["unmeasured"]
    )
    assert len(summary.cells) == 2


def test_run_refuses_when_attempt_names_no_directory(
    tmp_path: Path, monkeypatch
) -> None:
    """A record without its own identity is a seam contract breach: never guess."""

    def silent_attempt(**_kwargs: object) -> AttemptRecord:
        return replace(ok_record("x"), attempt_dir=None)

    monkeypatch.setattr(run_module, "attempt", silent_attempt)
    with pytest.raises(
        RuntimeError, match="does not name its attempt directory"
    ):
        run_module.run(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=tmp_path / "out",
            command=["fake"],
            n=1,
        )


def test_run_rejects_a_nonpositive_n_directly(tmp_path: Path) -> None:
    from satyrn_evals.errors import UsageError
    from satyrn_evals.run import run

    with pytest.raises(UsageError, match="positive --n"):
        run(task="format_number", tasks_root=tmp_path, output=tmp_path,
            command=["whatever"], n=0, timeout=5.0)


def test_run_rejects_an_empty_command_directly(tmp_path: Path) -> None:
    from satyrn_evals.errors import UsageError
    from satyrn_evals.run import run

    with pytest.raises(UsageError, match="run command is required"):
        run(task="format_number", tasks_root=tmp_path, output=tmp_path,
            command=[], n=1, timeout=5.0)


def test_run_summary_names_the_arm(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    summary = run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out", command=["fake"], n=1, timeout=123.0,
    )
    assert summary.task == "format_number"
    assert summary.command == ["fake"]
    assert summary.timeout == 123.0


def test_run_counts_a_grade_failed_cell_and_continues(
    tmp_path: Path, monkeypatch
) -> None:
    """A grading failure in one cell must not discard the batch."""
    from satyrn_evals.attempt_record import AttemptCode

    calls = {"n": 0}

    def fake(**kwargs):
        calls["n"] += 1
        output = kwargs["output"]
        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name("format_number", datetime.now(UTC))
        cell = output / name
        cell.mkdir()
        if calls["n"] == 1:  # cell 1 graded OK, receipt on disk
            (cell / "receipt.json").write_text('{"verdict": "pass"}')
            record = ok_record(name)
            write_attempt_record(cell / "attempt.json", record)
            return record
        # cell 2: grading failed -- GRADE_FAILED record, no receipt
        record = replace(
            ok_record(name),
            code=AttemptCode.GRADE_FAILED,
            verdict=None,
            receipt_path=None,
            message=("attempt preserved and admitted; "
                     "grading did not complete: boom"),
        )
        write_attempt_record(cell / "attempt.json", record)
        return record

    monkeypatch.setattr(run_module, "attempt", fake)
    summary = run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out", command=["fake"], n=2, timeout=123.0,
    )
    assert summary.n == 2 and summary.attempted == 2
    assert summary.code_counts["GRADE_FAILED"] == 1
    assert summary.code_counts["OK"] == 1
    assert len(summary.cells) == 2
    assert (tmp_path / "out" / "summary.json").exists()


def test_run_writes_an_aborted_marker_and_reraises(
    tmp_path: Path, monkeypatch
) -> None:
    """B1: an internal bug aborts WITHOUT writing summary.json.

    The partial batch is recorded in aborted.json (requested/completed/
    error + tallies over the completed cells) so it can never be mistaken
    for a completed short run.
    """
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("boom")
        output = kwargs["output"]
        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name("format_number", datetime.now(UTC))
        cell = output / name
        cell.mkdir()
        (cell / "receipt.json").write_text('{"verdict": "pass"}')
        record = ok_record(name)
        write_attempt_record(cell / "attempt.json", record)
        return record

    monkeypatch.setattr(run_module, "attempt", flaky)
    output = tmp_path / "out"
    with pytest.raises(OSError, match="boom"):
        run_module.run(
            task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
            output=output, command=["fake"], n=3, timeout=123.0,
        )
    # no summary.json: an aborted batch is never presented as complete
    assert not (output / "summary.json").exists()
    marker = json.loads((output / "aborted.json").read_text())
    assert marker["requested"] == 3
    assert marker["completed"] == 1
    assert "OSError" in marker["error"]
    assert marker["attempted"] == 1
    assert marker["code_counts"]["OK"] == 1
    assert len(marker["cells"]) == 1


def test_run_aborts_before_any_cell_writes_a_zero_completed_marker(
    tmp_path: Path, monkeypatch
) -> None:
    """An abort before any cell completes still writes the marker."""
    def raises_first(**_kwargs):
        raise RuntimeError("boom before start")

    monkeypatch.setattr(run_module, "attempt", raises_first)
    output = tmp_path / "out"
    with pytest.raises(RuntimeError, match="boom"):
        run_module.run(
            task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
            output=output, command=["fake"], n=4, timeout=123.0,
        )
    assert not (output / "summary.json").exists()
    marker = json.loads((output / "aborted.json").read_text())
    assert marker["requested"] == 4
    assert marker["completed"] == 0
    assert "RuntimeError" in marker["error"]
    assert "attempted" not in marker


def test_run_abort_on_a_hidden_task_keeps_the_contamination_tally(
    tmp_path: Path, monkeypatch
) -> None:
    """The aborted marker carries the hidden task's contamination section."""
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("boom")
        output = kwargs["output"]
        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name(HIDDEN_TASK_NAME, datetime.now(UTC))
        cell = output / name
        cell.mkdir()
        (cell / "receipt.json").write_text(_CLEAN_RECEIPT, encoding="utf-8")
        record = ok_record(name, task=HIDDEN_TASK_NAME)
        write_attempt_record(cell / "attempt.json", record)
        return record

    monkeypatch.setattr(run_module, "attempt", flaky)
    output = tmp_path / "out"
    with pytest.raises(OSError, match="boom"):
        run_module.run(
            task=HIDDEN_TASK_NAME, tasks_root=DEFAULT_TASKS_ROOT,
            output=output, command=["fake"], n=3, timeout=123.0,
        )
    marker = json.loads((output / "aborted.json").read_text())
    assert marker["oracle_visibility"] == "hidden"
    assert marker["contamination"] == {
        "graded": 1, "flagged": 0, "clean": 1, "unmeasured": 0
    }


def test_run_completion_replaces_a_stale_aborted_marker(
    tmp_path: Path, monkeypatch
) -> None:
    """A completed run in a dir with an earlier abort marker clears it."""
    output = tmp_path / "out"
    output.mkdir()
    (output / "aborted.json").write_text('{"requested": 8, "completed": 2}')
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    summary = run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
        output=output, command=["fake"], n=1, timeout=123.0,
    )
    assert summary.n == 1
    assert not (output / "aborted.json").exists()
    assert (output / "summary.json").exists()
