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
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.errors import UsageError
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.verdict import Verdict

HIDDEN_TASK_NAME = "agentclinic-repair-misleading-locus"
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
    rung: str | None = None,
    contract_digest: str = "d" * 64,
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
        rung=rung,
        contract_digest=contract_digest,
        workspace_base_sha="c" * 40,
        attempt_dir=cell_name,
    )


def _fake_attempt(
    receipt_text: str = '{"verdict": "pass"}',
    transcript: str | None = None,
):
    """A non-spawning attempt double bound to one directory identity.

    Mirrors attempt()'s contract end to end on disk: run() hands the double
    task/output/command/timeout as keyword arguments (exactly as it calls
    attempt()), so the double creates the <task>-<stamp> directory holding
    receipt.json AND attempt.json, and returns a record whose attempt_dir
    names it. When ``transcript`` is given, the double also writes
    transcript.txt at the seam path the real command writes through, so
    the cell measures under the V10 pathology binder.
    """

    def fake(
        *,
        task: str,
        tasks_root: Path,
        output: Path,
        command: list[str],
        timeout: float,
        rung: str | None = None,
        max_repeated_calls: int | None = None,
    ) -> AttemptRecord:
        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name(task, datetime.now(UTC))
        cell_dir = output / name
        cell_dir.mkdir()
        (cell_dir / "receipt.json").write_text(receipt_text, encoding="utf-8")
        if transcript is not None:
            (cell_dir / "transcript.txt").write_text(transcript, encoding="utf-8")
        record = ok_record(
            name, task=task, command=tuple(command), timeout=timeout, rung=rung
        )
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
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path,
        command=["fake"],
        n=2,
        timeout=1.5,
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
        p.name
        for p in (tmp_path / "out").iterdir()
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
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=["fake"],
        n=2,
    )
    assert len(summary.cells) == 2
    assert all(name.startswith("format_number-") for name in summary.cells)
    assert "stray-sibling" not in summary.cells
    assert "other-task-1" not in summary.cells
    assert (output / "summary.json").exists()


def test_run_on_hidden_task_tallies_contamination(tmp_path: Path, monkeypatch) -> None:
    """Default-tier sibling: run() against a hidden manifest still tallies.

    The hidden task's manifest marks the oracle hidden, so run() must produce
    the contamination section even when the seam is faked in-process (the
    non-spawning double writes graded, contamination-bearing receipts). The
    spawning end-to-end twin lives in tests/integration/test_run.py.
    """
    monkeypatch.setattr(
        run_module, "attempt", _fake_attempt(receipt_text=_CLEAN_RECEIPT)
    )
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
        "graded": 2,
        "flagged": 0,
        "clean": 2,
        "unmeasured": 0,
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
    with pytest.raises(RuntimeError, match="does not name its attempt directory"):
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
        run(
            task="format_number",
            tasks_root=tmp_path,
            output=tmp_path,
            command=["whatever"],
            n=0,
            timeout=5.0,
        )


def test_run_rejects_an_empty_command_directly(tmp_path: Path) -> None:
    from satyrn_evals.errors import UsageError
    from satyrn_evals.run import run

    with pytest.raises(UsageError, match="run command is required"):
        run(
            task="format_number",
            tasks_root=tmp_path,
            output=tmp_path,
            command=[],
            n=1,
            timeout=5.0,
        )


def test_run_summary_names_the_arm(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    summary = run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out",
        command=["fake"],
        n=1,
        timeout=123.0,
    )
    assert summary.task == "format_number"
    assert summary.command == ["fake"]
    assert summary.timeout == 123.0


def test_run_rejects_invalid_attempt_timeout_without_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="finite number greater than zero"):
        run_module.run(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=tmp_path / "out",
            command=["fake"],
            n=1,
            attempt_timeout=0,
        )
    assert not (tmp_path / "out").exists()


def test_run_passes_bounded_timeout_to_each_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    seen: list[float] = []
    fake = _fake_attempt()

    def bounded(**kwargs):
        seen.append(kwargs["attempt_timeout"])
        kwargs.pop("attempt_timeout")
        return fake(**kwargs)

    monkeypatch.setattr(run_module, "attempt", bounded)
    run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out",
        command=["fake"],
        n=2,
        attempt_timeout=12.0,
    )
    assert seen == [12.0, 12.0]


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
            message=("attempt preserved and admitted; grading did not complete: boom"),
        )
        write_attempt_record(cell / "attempt.json", record)
        return record

    monkeypatch.setattr(run_module, "attempt", fake)
    summary = run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out",
        command=["fake"],
        n=2,
        timeout=123.0,
    )
    assert summary.n == 2 and summary.attempted == 2
    assert summary.code_counts["GRADE_FAILED"] == 1
    assert summary.code_counts["OK"] == 1
    assert len(summary.cells) == 2
    assert (tmp_path / "out" / "summary.json").exists()


def test_run_writes_an_aborted_marker_and_reraises(tmp_path: Path, monkeypatch) -> None:
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
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=output,
            command=["fake"],
            n=3,
            timeout=123.0,
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
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=output,
            command=["fake"],
            n=4,
            timeout=123.0,
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
            task=HIDDEN_TASK_NAME,
            tasks_root=DEFAULT_TASKS_ROOT,
            output=output,
            command=["fake"],
            n=3,
            timeout=123.0,
        )
    marker = json.loads((output / "aborted.json").read_text())
    assert marker["oracle_visibility"] == "hidden"
    assert marker["contamination"] == {
        "graded": 1,
        "flagged": 0,
        "clean": 1,
        "unmeasured": 0,
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
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=["fake"],
        n=1,
        timeout=123.0,
    )
    assert summary.n == 1
    assert not (output / "aborted.json").exists()
    assert (output / "summary.json").exists()


# A well-formed Pi v3 transcript whose pathology counts are
# {tool_calls: {read: 2, edit: 2}} (the P1 test-module shape): two reads in
# turn one, an identical edit twice across turns two/three, a text-only
# final turn, and the agent terminal. Mirror of tests/test_pathology.py's
# GOOD.
GOOD_TRANSCRIPT = "\n".join(
    [
        '{"type": "session", "version": 3, "cwd": "/w"}',
        '{"type": "agent_start"}',
        '{"type": "turn_start"}',
        '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", "args": {"path": "app.py"}}',
        '{"type": "tool_execution_end", "toolCallId": "1", "toolName": "read", "result": {}}',
        '{"type": "tool_execution_start", "toolCallId": "2", "toolName": "read", "args": {"path": "tests/test_app.py"}}',
        '{"type": "tool_execution_end", "toolCallId": "2", "toolName": "read", "result": {}}',
        '{"type": "turn_end", "message": {"role": "assistant", "content": []}}',
        '{"type": "turn_start"}',
        '{"type": "tool_execution_start", "toolCallId": "3", "toolName": "edit", "args": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}}',
        '{"type": "tool_execution_end", "toolCallId": "3", "toolName": "edit", "result": {}}',
        '{"type": "turn_end", "message": {"role": "assistant", "content": []}}',
        '{"type": "turn_start"}',
        '{"type": "tool_execution_start", "toolCallId": "4", "toolName": "edit", "args": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}}',
        '{"type": "tool_execution_end", "toolCallId": "4", "toolName": "edit", "result": {}}',
        '{"type": "turn_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}}',
        '{"type": "agent_end"}',
        '{"type": "agent_settled"}',
    ]
)


def test_run_summary_carries_real_pathology_for_completed_cells(
    tmp_path: Path, monkeypatch
) -> None:
    """run's own summary carries the binder's measured blocks (V10 §4)."""
    output = tmp_path / "runs"
    fake = _fake_attempt(transcript=GOOD_TRANSCRIPT)
    monkeypatch.setattr(run_module, "attempt", fake)
    run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=["fake"],
        n=2,
        timeout=1.5,
    )
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert set(summary["pathology"]) == set(summary["cells"])
    assert all(block["measured"] is True for block in summary["pathology"].values())
    assert summary["pathology"][summary["cells"][0]]["tool_calls"] == {
        "read": 2,
        "edit": 2,
    }


def test_run_summary_marks_fake_cells_without_transcripts_absent(
    tmp_path: Path, monkeypatch
) -> None:
    """Success sibling: a cell whose record names no transcript on disk is
    `absent`, never a fabricated zero — asserted, not hidden."""
    output = tmp_path / "runs"
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=["fake"],
        n=1,
        timeout=1.5,
    )
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    cell = summary["cells"][0]
    assert summary["pathology"][cell] == {
        "measured": False,
        "reason": "absent",
    }


def test_abort_marker_never_masks_the_primary_exception(
    tmp_path: Path, monkeypatch
) -> None:
    """The primary abort exception surfaces; the marker records it."""
    output = tmp_path / "runs"

    def failing_fake(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(run_module, "attempt", failing_fake)
    with pytest.raises(RuntimeError, match="boom"):
        run_module.run(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=output,
            command=["fake"],
            n=2,
            timeout=1.5,
        )
    marker = json.loads((output / "aborted.json").read_text(encoding="utf-8"))
    assert "boom" in marker["error"]
    assert not (output / "summary.json").exists()


def test_abort_binder_failure_never_masks_the_primary_exception(
    tmp_path: Path, monkeypatch
) -> None:
    """A binder failure on the abort path is folded into the marker's error;
    the marker omits the block and the primary exception still surfaces."""
    output = tmp_path / "runs"
    calls = {"n": 0}
    base = _fake_attempt(transcript=GOOD_TRANSCRIPT)

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return base(**kwargs)

    def broken_binder(
        output,
        cells,
        *,
        task_dir,
        manifest,
        overlay=None,
        visible_texts=None,
    ):
        raise RuntimeError("binder broke")

    monkeypatch.setattr(run_module, "attempt", flaky)
    monkeypatch.setattr(run_module, "compute_pathology", broken_binder)
    with pytest.raises(RuntimeError, match="boom"):
        run_module.run(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=output,
            command=["fake"],
            n=2,
            timeout=1.5,
        )
    marker = json.loads((output / "aborted.json").read_text(encoding="utf-8"))
    assert "boom" in marker["error"]
    assert "pathology unavailable: RuntimeError: binder broke" in marker["error"]
    assert "pathology" not in marker  # the block is omitted, never fabricated
    assert not (output / "summary.json").exists()


def test_abort_marker_carries_pathology_when_binder_succeeds(
    tmp_path: Path, monkeypatch
) -> None:
    """Success sibling: an abort with a working binder writes the marker
    WITH the completed cells' measured blocks."""
    output = tmp_path / "runs"
    calls = {"n": 0}
    base = _fake_attempt(transcript=GOOD_TRANSCRIPT)

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("boom")
        return base(**kwargs)

    monkeypatch.setattr(run_module, "attempt", flaky)
    with pytest.raises(OSError, match="boom"):
        run_module.run(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=output,
            command=["fake"],
            n=2,
            timeout=1.5,
        )
    marker = json.loads((output / "aborted.json").read_text(encoding="utf-8"))
    assert marker["completed"] == 1
    cells = marker["cells"]
    assert set(marker["pathology"]) == set(cells)
    assert marker["pathology"][cells[0]]["measured"] is True
    assert not (output / "summary.json").exists()


def _hidden_run_task(tmp_path: Path) -> tuple[Path, Path]:
    """A bundled-style hidden task under ``tmp_path`` (name ``hidden-task``).

    Returns ``(task_dir, overlay_file)`` so a test can corrupt or repair
    the overlay after construction (V10 close-out recovery tests)."""
    task_dir = tmp_path / "hidden-task"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "base" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (task_dir / "fixtures").mkdir(parents=True)
    (task_dir / "fixtures" / "kg.patch").write_text("", encoding="utf-8")
    (task_dir / "grader" / "overlay").mkdir(parents=True)
    overlay_file = task_dir / "grader" / "overlay" / "t_hidden.py"
    overlay_file.write_text("def test_x():\n    assert True\n", encoding="utf-8")
    (task_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "hidden-task",
                "contract": "do the thing",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["t_hidden.py::test_x"],
                "source_paths": ["src"],
                "fixtures": {"known_good": "fixtures/kg.patch"},
                "grader_overlay": "grader/overlay",
                "oracle_visibility": "hidden",
            }
        ),
        encoding="utf-8",
    )
    return task_dir, overlay_file


def test_run_refuses_a_broken_overlay_before_any_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    """A broken overlay refuses run BEFORE its first attempt (V10 spec §4,
    close-out correction 2026-09-05): nothing is preserved, no
    summary/aborted marker is written, and the attempt seam is never
    invoked -- repair + rerun costs no model time."""
    from satyrn_evals.errors import SatyrnError

    _task_dir, overlay_file = _hidden_run_task(tmp_path)
    # Corrupt the overlay content: load_manifest's path-only check passes;
    # load_overlay's deep UTF-8 validation fails on run's pre-loop load.
    overlay_file.write_bytes(b"\xff\xfe not utf-8")
    calls = {"n": 0}
    base = _fake_attempt(transcript=GOOD_TRANSCRIPT)

    def counting_fake(**kwargs):
        calls["n"] += 1
        return base(**kwargs)

    monkeypatch.setattr(run_module, "attempt", counting_fake)
    output = tmp_path / "out"
    with pytest.raises(SatyrnError, match="overlay") as excinfo:
        run_module.run(
            task="hidden-task",
            tasks_root=tmp_path,
            output=output,
            command=["fake"],
            n=2,
            timeout=1.5,
        )
    assert excinfo.value.exit_code == 3
    assert calls["n"] == 0  # refused before the first attempt
    assert not (output / "summary.json").exists()
    assert not (output / "aborted.json").exists()
    assert not output.exists() or not any(output.iterdir())  # no cells


def test_run_then_summarize_recovers_after_overlay_repair(
    tmp_path: Path, monkeypatch
) -> None:
    """The recovery requirement (V10 spec §4/§9.7, close-out correction):
    after run() succeeds, a later overlay break makes summarize fail
    operationally (the run is already anchored), and repairing the overlay
    lets summarize_output recover from the preserved anchor reproducing the
    run's own bytes -- with ZERO additional attempt invocations (no model
    re-run)."""
    from satyrn_evals.errors import SatyrnError
    from satyrn_evals.rescore import summarize_output

    _task_dir, overlay_file = _hidden_run_task(tmp_path)
    overlay_text = "def test_x():\n    assert True\n"
    calls = {"n": 0}
    base = _fake_attempt(transcript=GOOD_TRANSCRIPT, receipt_text=_CLEAN_RECEIPT)

    def counting_fake(**kwargs):
        calls["n"] += 1
        return base(**kwargs)

    monkeypatch.setattr(run_module, "attempt", counting_fake)
    output = tmp_path / "out"
    run_module.run(
        task="hidden-task",
        tasks_root=tmp_path,
        output=output,
        command=["fake"],
        n=1,
        timeout=1.5,
    )
    own = (output / "summary.json").read_bytes()
    assert "pathology" in json.loads(own.decode())
    # Break the overlay after the run: summarize fails operationally...
    overlay_file.write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(SatyrnError, match="overlay"):
        summarize_output(output, tasks_root=tmp_path)
    # ...and repair recovers from the anchor with no new attempts.
    overlay_file.write_text(overlay_text, encoding="utf-8")
    summarize_output(output, tasks_root=tmp_path)
    assert (output / "summary.json").read_bytes() == own
    assert calls["n"] == 1  # only run's single attempt; summarize never invokes


def test_run_then_summarize_is_byte_identical_with_pathology(
    tmp_path: Path, monkeypatch
) -> None:
    """The V9 invariant extended to pathology: summarize's rebuild over
    the run's own cells reproduces run's summary.json byte for byte,
    including the pathology block computed from the preserved
    transcripts (V10 spec §4)."""
    from satyrn_evals.rescore import summarize_output

    output = tmp_path / "runs"
    monkeypatch.setattr(
        run_module, "attempt", _fake_attempt(transcript=GOOD_TRANSCRIPT)
    )
    run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=["fake"],
        n=2,
        timeout=1.5,
    )
    own = (output / "summary.json").read_bytes()
    summarize_output(output, tasks_root=DEFAULT_TASKS_ROOT)
    assert (output / "summary.json").read_bytes() == own


def test_summarize_enriches_a_pre_v10_summary(tmp_path: Path, monkeypatch) -> None:
    """A pre-V10 summary (no pathology key) re-summarized under V10 gains
    the block and is restored to the run's own bytes (V10 spec §4,
    retroactive application)."""
    from satyrn_evals.rescore import summarize_output

    output = tmp_path / "runs"
    monkeypatch.setattr(
        run_module, "attempt", _fake_attempt(transcript=GOOD_TRANSCRIPT)
    )
    run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=["fake"],
        n=2,
        timeout=1.5,
    )
    path = output / "summary.json"
    own = path.read_bytes()
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["pathology"]  # simulate a pre-V10 summary
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    summarize_output(output, tasks_root=DEFAULT_TASKS_ROOT)
    rebuilt = json.loads(path.read_text(encoding="utf-8"))
    assert set(rebuilt["pathology"]) == set(rebuilt["cells"])
    assert all(b["measured"] is True for b in rebuilt["pathology"].values())
    assert path.read_bytes() == own


# --- V11a Task 4: run passes --rung through to every attempt ---


def _task_with_contracts(tmp_path: Path, contracts: dict[str, str]) -> Path:
    """A minimal visible task root whose manifest declares a rung map."""
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "rungs"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "fixtures").mkdir()
    (task_dir / "fixtures" / "known-good.patch").write_text("ok")
    (task_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "rungs",
                "contract": "Fix it.",
                "contracts": contracts,
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["test_solution.py::test_one"],
                "source_paths": ["solution.py"],
                "fixtures": {"known_good": "fixtures/known-good.patch"},
            }
        )
    )
    return tasks_root


def test_run_passes_the_rung_to_every_attempt(tmp_path: Path, monkeypatch) -> None:
    tasks_root = _task_with_contracts(tmp_path, {"R1": "bare", "R3": "Fix it."})
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    output = tmp_path / "out"
    summary = run_module.run(
        task="rungs",
        tasks_root=tasks_root,
        output=output,
        command=["fake"],
        n=2,
        rung="R1",
    )
    assert len(summary.cells) == 2
    rungs = [
        load_attempt_record(output / name / "attempt.json").rung
        for name in summary.cells
    ]
    assert rungs == ["R1", "R1"]


def test_run_without_a_rung_records_the_default_contract(
    tmp_path: Path, monkeypatch
) -> None:
    """Sibling success: the default path is unchanged by --rung existing."""
    tasks_root = _task_with_contracts(tmp_path, {"R1": "bare", "R3": "Fix it."})
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    output = tmp_path / "out"
    summary = run_module.run(
        task="rungs",
        tasks_root=tasks_root,
        output=output,
        command=["fake"],
        n=2,
    )
    assert all(
        load_attempt_record(output / name / "attempt.json").rung is None
        for name in summary.cells
    )


def test_run_refuses_an_unknown_rung_before_the_first_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    """The refusal costs no cells: nothing is preserved and nothing is run."""
    tasks_root = _task_with_contracts(tmp_path, {"R1": "bare", "R3": "Fix it."})
    calls: list[object] = []

    def never(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(run_module, "attempt", never)
    output = tmp_path / "out"
    with pytest.raises(UsageError, match="R1, R3"):
        run_module.run(
            task="rungs",
            tasks_root=tasks_root,
            output=output,
            command=["fake"],
            n=2,
            rung="R9",
        )
    assert calls == []
    assert not output.exists()


def test_run_refuses_a_rung_on_a_task_with_no_contracts(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    with pytest.raises(UsageError, match="declares no contracts"):
        run_module.run(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=tmp_path / "out",
            command=["fake"],
            n=1,
            rung="R1",
        )
