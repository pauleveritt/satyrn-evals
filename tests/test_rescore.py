"""summarize_output/regrade_attempt: pure from-disk rebuild and re-score."""

import json
import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.manifest import (
    DEFAULT_TASKS_ROOT,
    TaskManifest,
    load_manifest,
    resolve_task,
)
from satyrn_evals.receipt import Receipt
from satyrn_evals.rescore import (
    compute_evidence,
    compute_pathology,
    regrade_attempt,
    summarize_output,
)
from satyrn_evals.summary import ABORTED_NAME, SUMMARY_NAME
from satyrn_evals.verdict import Verdict

TASK = "format_number"


def record(**overrides: object) -> AttemptRecord:
    base: dict[str, object] = dict(
        version=1, outcome=AttemptOutcome.ATTEMPTED, code=AttemptCode.OK,
        message="ok", task=TASK, command=("fake",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt",
        patch_digest="a" * 64, transcript_digest="b" * 64,
        verdict=Verdict.PASS, receipt_path="receipt.json",
        timeout=123.0, workspace_base_sha="c" * 40, attempt_dir="cell-1",
    )
    base.update(overrides)
    return AttemptRecord(**base)  # type: ignore[bad-argument-type]  # pyrefly cannot narrow the computed **dict; construction rules are this helper's subject


def write_cell(
    output: Path, name: str, rec: AttemptRecord, receipt: dict | None = None
) -> None:
    """Write a complete V9 cell: record (attempt_dir == dir name) + artifacts.

    A receipt is written only when the caller passes one; summarize treats
    an attempted record that names a receipt whose file is absent as an
    operational error, so callers of this helper must keep record and
    receipt in agreement.
    """
    cell = output / name
    cell.mkdir(parents=True, exist_ok=True)
    write_attempt_record(cell / "attempt.json", replace(rec, attempt_dir=name))
    (cell / "patch.diff").write_text("diff --git a/x b/x\n")
    (cell / "transcript.txt").write_text("t\n")
    if receipt is not None:
        (cell / "receipt.json").write_text(json.dumps(receipt))


_CLEAN_RECEIPT = {"verdict": "pass", "reason": ""}


def _bundled() -> Path:
    return DEFAULT_TASKS_ROOT


def write_anchor(output: Path, *names: str) -> None:
    """A completed-run anchor: summary.json naming its cells."""
    (output / SUMMARY_NAME).write_text(json.dumps({"cells": list(names)}))


def _two_cell_run(output: Path) -> None:
    """One OK cell + one GRADE_FAILED cell, with an anchor over both."""
    write_cell(output, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    write_cell(output, "format_number-2",
               record(code=AttemptCode.GRADE_FAILED, verdict=None,
                      receipt_path=None))
    write_anchor(output, "format_number-1", "format_number-2")


def test_summarize_rebuilds_counts_from_an_anchored_run(tmp_path: Path) -> None:
    out = tmp_path / "run"
    _two_cell_run(out)
    summary = summarize_output(out)
    assert summary.n == 2 and summary.attempted == 2
    assert summary.code_counts["OK"] == 1
    assert summary.code_counts["GRADE_FAILED"] == 1
    assert summary.task == TASK and summary.timeout == 123.0
    assert (out / SUMMARY_NAME).exists()
    assert json.loads((out / SUMMARY_NAME).read_text())["task"] == TASK


def test_summarize_ignores_cells_not_named_by_the_run(tmp_path: Path) -> None:
    """B2: the anchor, not the directory, is authoritative.

    A stray sibling that even carries its own attempt.json (an old partial
    run, an un-appended crash cell) must not change the rebuilt summary.
    """
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    write_cell(out, "format_number-9", record())  # stray, has attempt.json
    write_anchor(out, "format_number-1")
    summary = summarize_output(out)
    assert summary.cells == ["format_number-1"]
    assert summary.n == 1 and summary.attempted == 1


def test_summarize_refuses_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="not a directory"):
        summarize_output(tmp_path / "missing", tasks_root=_bundled())


def test_summarize_refuses_a_directory_without_an_anchor(tmp_path: Path) -> None:
    """No summary.json and no abort marker: not a run output directory."""
    (tmp_path / "empty").mkdir()
    with pytest.raises(UsageError, match=SUMMARY_NAME):
        summarize_output(tmp_path / "empty", tasks_root=_bundled())


def test_summarize_refuses_an_aborted_batch(tmp_path: Path) -> None:
    """B1/B2: an aborted run has no summary.json -- summarize refuses it."""
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    (out / ABORTED_NAME).write_text(
        json.dumps({"requested": 8, "completed": 1, "error": "OSError: boom"})
    )
    with pytest.raises(SatyrnError, match="aborted"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_an_aborted_batch_with_an_unreadable_marker(
    tmp_path: Path,
) -> None:
    """Even an unparseable aborted.json is refused, never silently rebuilt."""
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    (out / ABORTED_NAME).write_text("{not json")
    with pytest.raises(SatyrnError, match="aborted"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_unparseable_record_and_missing_receipt(
    tmp_path: Path,
) -> None:
    out = tmp_path / "run"
    cell = out / "format_number-1"
    cell.mkdir(parents=True)
    write_anchor(out, "format_number-1")
    (cell / "attempt.json").write_text("{not json")
    with pytest.raises(SatyrnError, match="cannot read"):
        summarize_output(out, tasks_root=_bundled())
    (cell / "attempt.json").unlink()
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    (cell / "receipt.json").unlink()
    with pytest.raises(SatyrnError, match="receipt"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_an_unparseable_receipt(tmp_path: Path) -> None:
    """A receipt that exists but is corrupt is operational, not clean."""
    out = tmp_path / "run"
    cell_dir = out / "format_number-1"
    cell_dir.mkdir(parents=True)
    write_attempt_record(cell_dir / "attempt.json",
                         record(attempt_dir="format_number-1"))
    (cell_dir / "receipt.json").write_text("{not json")
    write_anchor(out, "format_number-1")
    with pytest.raises(SatyrnError, match="receipt"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_mixed_task_identity(tmp_path: Path) -> None:
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    write_cell(out, "other-task-1", record(task="other-task"),
               receipt=_CLEAN_RECEIPT)
    write_anchor(out, "format_number-1", "other-task-1")
    with pytest.raises(SatyrnError, match="mixed"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_a_moved_cell(tmp_path: Path) -> None:
    """A record whose attempt_dir disagrees with its directory is usage (2)."""
    out = tmp_path / "run"
    cell = out / "moved-1"
    cell.mkdir(parents=True)
    write_attempt_record(
        cell / "attempt.json", record(attempt_dir="format_number-1")
    )
    (cell / "receipt.json").write_text(json.dumps(_CLEAN_RECEIPT))
    write_anchor(out, "moved-1")
    with pytest.raises(UsageError, match="moved or renamed"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_a_missing_anchored_cell(tmp_path: Path) -> None:
    """A cell the run's summary names but the directory no longer holds."""
    out = tmp_path / "run"
    out.mkdir(parents=True)
    write_anchor(out, "format_number-1")
    with pytest.raises(SatyrnError, match="missing"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_an_unusable_anchor(tmp_path: Path) -> None:
    """A corrupt or cell-less summary.json is operational, never silent."""
    out = tmp_path / "run"
    out.mkdir(parents=True)
    (out / SUMMARY_NAME).write_text("{not json")
    with pytest.raises(SatyrnError, match="cannot read"):
        summarize_output(out, tasks_root=_bundled())
    (out / SUMMARY_NAME).write_text(json.dumps({"n": 0}))
    with pytest.raises(SatyrnError, match="cells"):
        summarize_output(out, tasks_root=_bundled())
    (out / SUMMARY_NAME).write_text(json.dumps({"cells": []}))
    with pytest.raises(SatyrnError, match="names no cells"):
        summarize_output(out, tasks_root=_bundled())


# --- P4b: regrade_attempt legs (default tier, grade mocked) ---


def _fake_grade(verdict: Verdict):
    """A grade double that mirrors real grade(): writes the receipt file."""

    def fake(task_dir: Path, patch_path: Path, receipt_path: Path) -> Receipt:
        receipt_path.write_text(
            json.dumps({"task": task_dir.name, "verdict": verdict.value})
        )
        return Receipt(
            task=task_dir.name,
            patch_digest="a" * 64,
            verdict=verdict,
            reason="",
            evidence=None,
        )

    return fake


def test_regrade_turns_a_grade_failed_cell_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A GRADE_FAILED cell is the reason regrade exists (success leg)."""
    from satyrn_evals import rescore as rescore_module

    out = tmp_path / "run"
    write_cell(out, "format_number-1",
               record(code=AttemptCode.GRADE_FAILED, verdict=None,
                      receipt_path=None, retained_path="/tmp/retained"))
    monkeypatch.setattr(rescore_module, "grade", _fake_grade(Verdict.PASS))
    rewritten = regrade_attempt(out / "format_number-1", tasks_root=_bundled())
    assert rewritten is not None
    assert rewritten.code is AttemptCode.OK
    assert rewritten.verdict is Verdict.PASS
    assert rewritten.receipt_path == "receipt.json"
    assert rewritten.retained_path == "/tmp/retained"
    loaded = load_attempt_record(out / "format_number-1" / "attempt.json")
    assert loaded.code is AttemptCode.OK and loaded.verdict is Verdict.PASS
    assert loaded.retained_path == "/tmp/retained"
    # the mock wrote the receipt exactly where the record names it
    assert (out / "format_number-1" / "receipt.json").is_file()


def test_regrade_of_a_refusal_cell_is_a_noop(tmp_path: Path) -> None:
    """A refusal code was never graded: nothing to re-score (no-op leg)."""
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(
        code=AttemptCode.NO_PATCH, outcome=AttemptOutcome.REFUSED,
        verdict=None, receipt_path=None, patch_path=None,
        transcript_path=None, patch_digest=None, transcript_digest=None,
    ))
    assert regrade_attempt(out / "format_number-1",
                           tasks_root=_bundled()) is None


def test_regrade_rescores_an_ok_cell_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An OK cell is re-scored: the returned record carries the new verdict."""
    from satyrn_evals import rescore as rescore_module

    out = tmp_path / "run"
    write_cell(out, "format_number-1",
               record(verdict=Verdict.FAIL, message="old"),
               receipt=_CLEAN_RECEIPT)
    monkeypatch.setattr(rescore_module, "grade", _fake_grade(Verdict.PASS))
    rewritten = regrade_attempt(out / "format_number-1",
                                tasks_root=_bundled())
    assert rewritten is not None
    assert rewritten.verdict is Verdict.PASS
    assert rewritten.message == "attempt re-graded"
    loaded = load_attempt_record(out / "format_number-1" / "attempt.json")
    assert loaded.verdict is Verdict.PASS


def test_regrade_refuses_identity_mismatch(tmp_path: Path) -> None:
    """A renamed cell must not be graded (refusal leg)."""
    cell = tmp_path / "other-1"
    cell.mkdir()
    write_attempt_record(
        cell / "attempt.json",
        replace(record(code=AttemptCode.GRADE_FAILED, verdict=None,
                       receipt_path=None), attempt_dir="format_number-1"),
    )
    with pytest.raises(UsageError, match="names"):
        regrade_attempt(cell, tasks_root=_bundled())


def test_regrade_refuses_a_non_cell_directory(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="no attempt record"):
        regrade_attempt(tmp_path / "nope", tasks_root=_bundled())


def test_regrade_refuses_an_unreadable_record(tmp_path: Path) -> None:
    """An attempt.json that exists but is corrupt is operational (3)."""
    cell = tmp_path / "format_number-1"
    cell.mkdir()
    (cell / "attempt.json").write_text("{not json")
    with pytest.raises(SatyrnError, match="cannot read"):
        regrade_attempt(cell, tasks_root=_bundled())


def test_regrade_unavailable_verdict_raises_operational(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UNAVAILABLE after a successful regrade is exit-3 class (spec §6)."""
    from satyrn_evals import rescore as rescore_module

    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    monkeypatch.setattr(rescore_module, "grade",
                        _fake_grade(Verdict.UNAVAILABLE))
    with pytest.raises(SatyrnError, match="unavailable"):
        regrade_attempt(out / "format_number-1", tasks_root=_bundled())
    # the record was still rewritten and consistent before the raise
    loaded = load_attempt_record(out / "format_number-1" / "attempt.json")
    assert loaded.code is AttemptCode.OK
    assert loaded.verdict is Verdict.UNAVAILABLE


# --- V10 P3a Task 2: compute_pathology (the artifact binder) ---

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GOOD_TRANSCRIPT = (
    _REPO_ROOT / "tests" / "data" / "v10" / "good-repair.jsonl"
).read_text(encoding="utf-8")


def _pathology_cell(
    output: Path,
    name: str,
    *,
    task: str = TASK,
    transcript: str | None = None,
    names_transcript: bool = True,
    as_directory: bool = False,
    unreadable: bool = False,
) -> tuple[str, AttemptRecord, None]:
    """One cell dir with an attempt record (and on-disk copy) + transcript.

    ``transcript=None`` leaves the file absent while the record still
    names it (spec §4: missing at summary time); ``names_transcript=False``
    mirrors a TRANSCRIPT_MISSING refusal whose record names no transcript
    at all.
    """
    cell = output / name
    cell.mkdir(parents=True, exist_ok=True)
    (cell / "patch.diff").write_text("diff --git a/x b/x\n", encoding="utf-8")
    if names_transcript:
        rec = record(task=task, attempt_dir=name)
        target = cell / "transcript.txt"
        if as_directory:
            target.mkdir()
        elif unreadable:
            target.write_text("x\n", encoding="utf-8")
            target.chmod(0)
        elif transcript is not None:
            target.write_text(transcript, encoding="utf-8")
    else:
        rec = record(
            task=task,
            attempt_dir=name,
            outcome=AttemptOutcome.REFUSED,
            code=AttemptCode.TRANSCRIPT_MISSING,
            verdict=None,
            transcript_path=None,
            transcript_digest=None,
            receipt_path=None,
        )
    write_attempt_record(cell / "attempt.json", rec)
    return name, rec, None


def _visible_setup(tmp_path: Path) -> tuple[Path, Path, TaskManifest]:
    """Output dir + the bundled format_number task's dir and manifest."""
    task_dir = resolve_task(TASK, tasks_root=_bundled())
    return tmp_path / "run", task_dir, load_manifest(task_dir)


def _hidden_task_dir(tmp_path: Path, name: str = "hidden-task") -> Path:
    """A bundled-style hidden task: base (with skip-worthy entries),
    a grader overlay, and a manifest declaring both."""
    task = tmp_path / name
    (task / "base").mkdir(parents=True)
    (task / "base" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (task / "base" / "pkg").mkdir()
    (task / "base" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (task / "base" / "data.bin").write_bytes(b"\xff\xfe\x00")
    os.symlink("app.py", task / "base" / "link.py")
    (task / "fixtures").mkdir(parents=True)
    (task / "fixtures" / "kg.patch").write_text("", encoding="utf-8")
    (task / "grader" / "overlay" / "tests").mkdir(parents=True)
    (task / "grader" / "overlay" / "tests" / "t_hidden.py").write_text(
        _HIDDEN_OVERLAY, encoding="utf-8"
    )
    (task / "manifest.json").write_text(
        json.dumps(
            {
                "name": name,
                "contract": "do the thing",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["tests/t_hidden.py::test_x"],
                "source_paths": ["src"],
                "fixtures": {"known_good": "fixtures/kg.patch"},
                "grader_overlay": "grader/overlay",
                "oracle_visibility": "hidden",
            }
        ),
        encoding="utf-8",
    )
    return task


_HIDDEN_OVERLAY = (
    "def test_x():\n"
    "\n"
    "    x = 1\n"
    "    y = 2\n"
    "    z = 3\n"
    "    assert x + y == z\n"
)  # 5 non-blank lines: >= GRADER_BLOCK_LINES, so block windows match


def _leaky_transcript(payload: str) -> str:
    """A well-formed (R1-R6) one-turn transcript whose read result echoes
    ``payload`` inside a JSON string -- the only way overlay content can
    appear in a *measured* cell (spec §3.8, decoded scan body)."""
    return "\n".join(
        [
            '{"type": "session", "version": 3, "cwd": "/w"}',
            '{"type": "agent_start"}',
            '{"type": "turn_start"}',
            '{"type": "tool_execution_start", "toolCallId": "r1", "toolName": "read", "args": {"path": "app.py"}}',
            json.dumps(
                {
                    "type": "tool_execution_end", "toolCallId": "r1",
                    "toolName": "read",
                    "result": {"content": [{"type": "text", "text": payload}]},
                }
            ),
            '{"type": "turn_end", "message": {"role": "assistant", "content": []}}',
            '{"type": "agent_end"}',
            '{"type": "agent_settled"}',
        ]
    )


def _hidden_setup(tmp_path: Path) -> tuple[Path, Path, TaskManifest]:
    task_dir = _hidden_task_dir(tmp_path)
    return tmp_path / "run", task_dir, load_manifest(task_dir)


def test_compute_pathology_marks_missing_transcript_absent(
    tmp_path: Path,
) -> None:
    output, task_dir, manifest = _visible_setup(tmp_path)
    cells = [
        _pathology_cell(output, "format_number-1"),
        _pathology_cell(output, "format_number-2"),
    ]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block == {
        "format_number-1": {"measured": False, "reason": "absent"},
        "format_number-2": {"measured": False, "reason": "absent"},
    }


def test_compute_pathology_counts_a_good_transcript(tmp_path: Path) -> None:
    output, task_dir, manifest = _visible_setup(tmp_path)
    cells = [
        _pathology_cell(output, "format_number-1", transcript=_GOOD_TRANSCRIPT)
    ]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    cell = block["format_number-1"]
    assert cell["measured"] is True
    assert cell["tool_calls"] == {"read": 6, "edit": 2}
    assert "overlay_windows" not in cell  # visible task never carries the key


def test_compute_pathology_record_without_transcript_is_absent(
    tmp_path: Path,
) -> None:
    """Refusal-cell records name no transcript: absent, never an error."""
    output, task_dir, manifest = _visible_setup(tmp_path)
    cells = [_pathology_cell(output, "format_number-1", names_transcript=False)]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block["format_number-1"] == {"measured": False, "reason": "absent"}


def test_compute_pathology_non_regular_transcript_is_absent(
    tmp_path: Path,
) -> None:
    output, task_dir, manifest = _visible_setup(tmp_path)
    cells = [_pathology_cell(output, "format_number-1", as_directory=True)]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block["format_number-1"] == {"measured": False, "reason": "absent"}


def test_compute_pathology_unreadable_transcript_is_absent(
    tmp_path: Path,
) -> None:
    output, task_dir, manifest = _visible_setup(tmp_path)
    cells = [_pathology_cell(output, "format_number-1", unreadable=True)]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block["format_number-1"] == {"measured": False, "reason": "absent"}


def test_compute_pathology_garbage_text_is_unparseable_not_absent(
    tmp_path: Path,
) -> None:
    """Readable garbage is the parser's verdict (unparseable), not the
    binder's (absent) — spec §4: only genuinely unreadable files are
    absent."""
    output, task_dir, manifest = _visible_setup(tmp_path)
    cells = [_pathology_cell(output, "format_number-1", transcript="not json\n")]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block["format_number-1"] == {"measured": False, "reason": "unparseable"}


def test_compute_pathology_hidden_measured_cell_gains_overlay_windows(
    tmp_path: Path,
) -> None:
    """The clean sibling of the leak pair: a hidden cell whose decoded
    payload carries no overlay window reports overlay_windows == 0."""
    output, task_dir, manifest = _hidden_setup(tmp_path)
    cells = [
        _pathology_cell(
            output, "hidden-task-1", task="hidden-task",
            transcript=_GOOD_TRANSCRIPT,
        )
    ]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    cell = block["hidden-task-1"]
    assert cell["measured"] is True
    assert cell["overlay_windows"] == 0  # clean transcript: no leak


def test_compute_pathology_hidden_overlay_leak_fires(
    tmp_path: Path,
) -> None:
    """BRIEF rule 8, fire direction: a hidden cell whose *decoded* result
    content carries the overlay's hidden-file window verbatim reports
    overlay_windows == 1 (the raw stream is JSON-escaped, so only the
    decoded scan body can catch the leak -- spec §3.8 amendment)."""
    output, task_dir, manifest = _hidden_setup(tmp_path)
    cells = [
        _pathology_cell(
            output, "hidden-task-1", task="hidden-task",
            transcript=_leaky_transcript(_HIDDEN_OVERLAY),
        )
    ]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block["hidden-task-1"]["overlay_windows"] == 1


def test_compute_pathology_overlay_window_shared_with_base_stays_clean(
    tmp_path: Path,
) -> None:
    """BRIEF rule 8, silence direction: a window also present in the
    model-visible base texts is shown content, not evidence -- the same
    decoded echo reports 0 when the base carries the text (visible
    subtraction, spec §3.8)."""
    output, task_dir, manifest = _hidden_setup(tmp_path)
    # The base now carries the very text the transcript echoes: the model
    # could legitimately have read it there.
    (task_dir / "base" / "public.py").write_text(
        _HIDDEN_OVERLAY, encoding="utf-8"
    )
    cells = [
        _pathology_cell(
            output, "hidden-task-1", task="hidden-task",
            transcript=_leaky_transcript(_HIDDEN_OVERLAY),
        )
    ]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block["hidden-task-1"]["overlay_windows"] == 0


def test_compute_pathology_hidden_without_base_scans_no_visible_text(
    tmp_path: Path,
) -> None:
    """A hidden task whose base vanished post-load: visible subtraction
    is empty and the scan still runs (0 windows on a clean transcript)."""
    output, task_dir, manifest = _hidden_setup(tmp_path)
    shutil.rmtree(task_dir / "base")
    cells = [
        _pathology_cell(
            output, "hidden-task-1", task="hidden-task",
            transcript=_GOOD_TRANSCRIPT,
        )
    ]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block["hidden-task-1"]["overlay_windows"] == 0


def test_compute_pathology_unmeasured_cell_never_carries_count_keys(
    tmp_path: Path,
) -> None:
    """S1: measured:false publishes only a reason — no overlay_windows even
    when the raw transcript text echoes the overlay verbatim (raw overlay
    lines are not a well-formed Pi stream, so the parser calls it
    unparseable and no count key is attached)."""
    output, task_dir, manifest = _hidden_setup(tmp_path)
    cells = [
        _pathology_cell(
            output, "hidden-task-1", task="hidden-task",
            transcript=_HIDDEN_OVERLAY,
        )
    ]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block["hidden-task-1"] == {"measured": False, "reason": "unparseable"}


def test_compute_pathology_unreadable_overlay_is_operational(
    tmp_path: Path,
) -> None:
    """A stored overlay that disappears between manifest load and summary
    time is shared-task-data corruption: it raises, never per-cell
    unmeasured (spec §4)."""
    output, task_dir, manifest = _hidden_setup(tmp_path)
    shutil.rmtree(task_dir / "grader")
    cells = [
        _pathology_cell(
            output, "hidden-task-1", task="hidden-task",
            transcript=_GOOD_TRANSCRIPT,
        )
    ]
    with pytest.raises(SatyrnError):
        compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)


def test_compute_pathology_had_patch_false_counts_the_terminal_turn(
    tmp_path: Path,
) -> None:
    """The binder-level had_patch=False arc (spec §3.6, deferred minor from
    P3a Task 2): a measured transcript whose cell preserved no patch (a
    NO_PATCH refusal that still delivered a transcript) and whose terminal
    turn is text-only reports tool_free_terminal_turns == 1 — the
    floored-model signal — never a hard-wired 0."""
    output, task_dir, manifest = _visible_setup(tmp_path)
    name = "format_number-1"
    cell = output / name
    cell.mkdir(parents=True, exist_ok=True)
    (cell / "transcript.txt").write_text(_GOOD_TRANSCRIPT, encoding="utf-8")
    rec = record(
        task=TASK,
        attempt_dir=name,
        outcome=AttemptOutcome.REFUSED,
        code=AttemptCode.NO_PATCH,
        patch_path=None,
        patch_digest=None,
        verdict=None,
        receipt_path=None,
    )
    write_attempt_record(cell / "attempt.json", rec)
    block = compute_pathology(
        output, [(name, rec, None)], task_dir=task_dir, manifest=manifest
    )
    cell_block = block[name]
    assert cell_block["measured"] is True
    assert cell_block["tool_free_terminal_turns"] == 1


def test_compute_pathology_had_patch_true_keeps_terminal_zero(
    tmp_path: Path,
) -> None:
    """Sibling of the pin above: the same text-only-terminal transcript
    with a preserved patch (the usual OK cell) reports 0 — the count is
    the conjunction, not the terminal text alone."""
    output, task_dir, manifest = _visible_setup(tmp_path)
    cells = [
        _pathology_cell(
            output, "format_number-1", transcript=_GOOD_TRANSCRIPT
        )
    ]
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    cell_block = block["format_number-1"]
    assert cell_block["measured"] is True
    assert cell_block["tool_free_terminal_turns"] == 0


def test_summarize_refuses_an_unreadable_overlay_as_operational(
    tmp_path: Path,
) -> None:
    """An overlay that vanishes between the run and a later summarize is
    shared task data: summarize raises operational (exit 3), never a
    per-cell unmeasured (V10 spec §4). OverlayError alone would exit 2
    (usage); the summary write path must be 3."""
    task_dir = _hidden_task_dir(tmp_path, name="hidden-task")
    # Corrupt the overlay content: the manifest's path-only check passes,
    # but load_overlay's deep validation (UTF-8 text) fails -- the layer
    # spec §4 calls operational (3) on the summarize write path.
    (task_dir / "grader" / "overlay" / "tests" / "t_hidden.py").write_bytes(
        b"\xff\xfe not utf-8"
    )
    out = tmp_path / "run"
    write_cell(
        out, "hidden-task-1",
        record(task="hidden-task", attempt_dir="hidden-task-1"),
        receipt=_CLEAN_RECEIPT,
    )
    write_anchor(out, "hidden-task-1")
    with pytest.raises(SatyrnError, match="overlay") as excinfo:
        summarize_output(out, tasks_root=tmp_path)
    assert excinfo.value.exit_code == 3


# --- V11a Task 5: re-summarizing preserves rung provenance ---


def test_summarize_rebuilds_the_rung_and_digest(tmp_path: Path) -> None:
    out = tmp_path / "run"
    digest = "1" * 64
    write_cell(out, "format_number-1",
               record(rung="R1", contract_digest=digest),
               receipt=_CLEAN_RECEIPT)
    write_cell(out, "format_number-2",
               record(rung="R1", contract_digest=digest),
               receipt=_CLEAN_RECEIPT)
    write_anchor(out, "format_number-1", "format_number-2")
    summary = summarize_output(out)
    assert summary.rung == "R1"
    assert summary.contract_digest == digest


def test_summarize_of_a_rung_run_is_byte_identical_on_re_summarize(
    tmp_path: Path,
) -> None:
    """BRIEF rule 3, executable: the rebuild carries the new fields and
    reproduces the previous artifact byte for byte."""
    out = tmp_path / "run"
    digest = "1" * 64
    write_cell(out, "format_number-1",
               record(rung="R1", contract_digest=digest),
               receipt=_CLEAN_RECEIPT)
    write_anchor(out, "format_number-1")
    summarize_output(out)
    first = (out / SUMMARY_NAME).read_bytes()
    summarize_output(out)
    assert (out / SUMMARY_NAME).read_bytes() == first
    assert b'"rung": "R1"' in first


def test_summarize_of_legacy_cells_keeps_the_unknowns(tmp_path: Path) -> None:
    """Sibling success: a pre-V11a run re-summarizes with both fields null."""
    out = tmp_path / "run"
    _two_cell_run(out)
    summary = summarize_output(out)
    assert summary.rung is None and summary.contract_digest is None


def test_summarize_refuses_a_mixed_rung_batch(tmp_path: Path) -> None:
    out = tmp_path / "run"
    write_cell(out, "format_number-1",
               record(rung="R1", contract_digest="1" * 64),
               receipt=_CLEAN_RECEIPT)
    write_cell(out, "format_number-2",
               record(rung="R3", contract_digest="3" * 64),
               receipt=_CLEAN_RECEIPT)
    write_anchor(out, "format_number-1", "format_number-2")
    with pytest.raises(SatyrnError, match="mixed rungs"):
        summarize_output(out)


def _empty_patch_cell(
    output: Path, name: str, *, patch: str | None
) -> tuple[str, AttemptRecord, None]:
    """A pi-adapter-shaped refusal cell: the record names ``patch.diff``
    and the file exists, because ``attempt_pi.py:230`` writes it
    unconditionally. ``patch`` is that file's content; ``None`` makes it
    unreadable instead (mode 0).
    """
    cell = output / name
    cell.mkdir(parents=True, exist_ok=True)
    target = cell / "patch.diff"
    if patch is None:
        target.write_text("x\n", encoding="utf-8")
        target.chmod(0)
    else:
        target.write_text(patch, encoding="utf-8")
    (cell / "transcript.txt").write_text(_GOOD_TRANSCRIPT, encoding="utf-8")
    rec = record(
        task=TASK,
        attempt_dir=name,
        outcome=AttemptOutcome.REFUSED,
        code=AttemptCode.NO_PATCH,
        verdict=None,
        receipt_path=None,
    )
    write_attempt_record(cell / "attempt.json", rec)
    return name, rec, None


def test_compute_pathology_an_empty_patch_file_counts_the_terminal_turn(
    tmp_path: Path,
) -> None:
    """V11d F2, the defect this pins: every pi-adapter cell names a
    ``patch.diff`` because the adapter always writes one, so
    ``patch_path is not None`` was true even on a NO_PATCH refusal and
    ``tool_free_terminal_turns`` could never fire. ``had_patch`` means a
    non-empty patch. Demonstration cell (from the *voided* first
    mini-probe, retained transcript only):
    ``~/satyrn-smokes/2026-09-05-v11c-miniprobe/plausible-wrong-fix/
    agentclinic-repair-plausible-wrong-fix-20260905-200622-258836`` --
    0-byte ``patch.diff``, published 0, recomputes to 1.
    """
    output, task_dir, manifest = _visible_setup(tmp_path)
    cell = _empty_patch_cell(output, "format_number-1", patch="")
    block = compute_pathology(
        output, [cell], task_dir=task_dir, manifest=manifest
    )["format_number-1"]
    assert block["measured"] is True
    assert block["tool_free_terminal_turns"] == 1


def test_compute_pathology_a_whitespace_only_patch_counts_the_terminal_turn(
    tmp_path: Path,
) -> None:
    """Sibling of the pin above: a patch file holding only whitespace
    applies nothing, so it is not a patch either -- emptiness is decided
    after stripping, not on the byte count."""
    output, task_dir, manifest = _visible_setup(tmp_path)
    cell = _empty_patch_cell(output, "format_number-1", patch="\n \n")
    block = compute_pathology(
        output, [cell], task_dir=task_dir, manifest=manifest
    )["format_number-1"]
    assert block["measured"] is True
    assert block["tool_free_terminal_turns"] == 1


def test_compute_pathology_a_real_patch_file_keeps_terminal_zero(
    tmp_path: Path,
) -> None:
    """The success sibling for the two pins above, in the same shape: the
    record names ``patch.diff`` and the file holds a real diff, so the
    gate still stays silent in the direction it was designed for."""
    output, task_dir, manifest = _visible_setup(tmp_path)
    cell = _empty_patch_cell(
        output, "format_number-1", patch="diff --git a/x b/x\n"
    )
    block = compute_pathology(
        output, [cell], task_dir=task_dir, manifest=manifest
    )["format_number-1"]
    assert block["measured"] is True
    assert block["tool_free_terminal_turns"] == 0


def test_compute_pathology_an_unreadable_patch_stays_silent(
    tmp_path: Path,
) -> None:
    """Confirmed 2026-09-05: a recorded patch that cannot be read is
    absent evidence, and absent evidence does not become a finding. The
    count stays 0 rather than manufacturing a pathology from an I/O
    problem; the rest of the transcript-local counts are unaffected."""
    output, task_dir, manifest = _visible_setup(tmp_path)
    cell = _empty_patch_cell(output, "format_number-1", patch=None)
    block = compute_pathology(
        output, [cell], task_dir=task_dir, manifest=manifest
    )["format_number-1"]
    assert block["measured"] is True
    assert block["tool_free_terminal_turns"] == 0


def test_compute_pathology_a_directory_shaped_patch_stays_silent(
    tmp_path: Path,
) -> None:
    """Shape pin for the same silence rule: a recorded ``patch.diff`` that
    is a directory reads as an OSError, which is absent evidence rather
    than a finding. Sibling of the unreadable-patch pin above; both keep
    the empty-patch fix from firing on an I/O problem."""
    output, task_dir, manifest = _visible_setup(tmp_path)
    name = "format_number-1"
    cell = output / name
    cell.mkdir(parents=True, exist_ok=True)
    (cell / "patch.diff").mkdir()
    (cell / "transcript.txt").write_text(_GOOD_TRANSCRIPT, encoding="utf-8")
    rec = record(
        task=TASK,
        attempt_dir=name,
        outcome=AttemptOutcome.REFUSED,
        code=AttemptCode.NO_PATCH,
        verdict=None,
        receipt_path=None,
    )
    write_attempt_record(cell / "attempt.json", rec)
    block = compute_pathology(
        output, [(name, rec, None)], task_dir=task_dir, manifest=manifest
    )[name]
    assert block["measured"] is True
    assert block["tool_free_terminal_turns"] == 0


# --- V11d slice 4: reclassifying a collected cell offline ---

_OOM_TRANSCRIPT = "\n".join([
    '{"type": "session", "version": 3, "cwd": "/w"}',
    '{"type": "agent_start"}',
    '{"type": "turn_start"}',
    json.dumps({"type": "turn_end", "message": {
        "role": "assistant", "content": [], "model": "m",
        "usage": {"totalTokens": 0}, "stopReason": "error",
        "errorMessage": "[METAL] Command buffer execution failed: "
                        "Insufficient Memory (kIOGPUCommandBufferCallback"
                        "ErrorOutOfMemory).",
    }}),
    '{"type": "agent_end"}',
])


def _refusal_cell(output: Path, name: str, transcript: str) -> Path:
    cell = output / name
    cell.mkdir(parents=True, exist_ok=True)
    (cell / "patch.diff").write_text("", encoding="utf-8")
    (cell / "transcript.txt").write_text(transcript, encoding="utf-8")
    write_attempt_record(cell / "attempt.json", record(
        task=TASK, attempt_dir=name, outcome=AttemptOutcome.REFUSED,
        code=AttemptCode.NO_PATCH, verdict=None, receipt_path=None,
    ))
    return cell


def test_regrade_reclassifies_a_collected_infrastructure_failure(
    tmp_path: Path,
) -> None:
    """The gap the V11d plan missed: regrade no-ops on refusal cells
    (`rescore.py`, "nothing was graded, so nothing re-scores"), so an
    attempt-time-only MODEL_ERROR would strand every cell already
    collected at NO_PATCH -- which is what BRIEF rule 3 exists to
    prevent. Five such cells are on record."""
    cell = _refusal_cell(tmp_path / "run", "cell-1", _OOM_TRANSCRIPT)
    rewritten = regrade_attempt(cell, tasks_root=DEFAULT_TASKS_ROOT)
    assert rewritten is not None
    assert rewritten.code is AttemptCode.MODEL_ERROR
    assert load_attempt_record(cell / "attempt.json").code is AttemptCode.MODEL_ERROR


def test_regrade_leaves_a_genuine_refusal_alone(tmp_path: Path) -> None:
    """The success sibling, and the cell that defeated two earlier
    screens: a 400 about the server's own context limit means the model
    was reached. Genuine pathology; it stays NO_PATCH and stays in the
    denominator."""
    context = _OOM_TRANSCRIPT.replace(
        "[METAL] Command buffer execution failed: Insufficient Memory "
        "(kIOGPUCommandBufferCallbackErrorOutOfMemory).",
        '400: {"message":"Prompt too long: 80036 tokens exceeds max '
        'context window of 80000 tokens"}',
    )
    cell = _refusal_cell(tmp_path / "run", "cell-1", context)
    assert regrade_attempt(cell, tasks_root=DEFAULT_TASKS_ROOT) is None
    assert load_attempt_record(cell / "attempt.json").code is AttemptCode.NO_PATCH


def test_regrade_reclassification_is_idempotent(tmp_path: Path) -> None:
    """Re-scoring is run repeatedly over retained evidence, so a cell
    already reclassified must not be rewritten again."""
    cell = _refusal_cell(tmp_path / "run", "cell-1", _OOM_TRANSCRIPT)
    assert regrade_attempt(cell, tasks_root=DEFAULT_TASKS_ROOT) is not None
    assert regrade_attempt(cell, tasks_root=DEFAULT_TASKS_ROOT) is None


def _partial_leak(payload: str) -> str:
    """A timed-out cell's transcript: the leak is read, nothing closes the turn."""
    return "\n".join(_leaky_transcript(payload).splitlines()[:5]) + "\n"


def test_evidence_scans_a_timed_out_hidden_cell_that_pathology_cannot_measure(tmp_path: Path) -> None:
    output, task_dir, manifest = _hidden_setup(tmp_path)
    name, rec, receipt = _pathology_cell(output, "hidden-task-1", task="hidden-task", transcript=_partial_leak(_HIDDEN_OVERLAY))
    timed_out = replace(
        rec, outcome=AttemptOutcome.REFUSED, code=AttemptCode.COMMAND_TIMEOUT, command_exit=None,
        verdict=None, receipt_path=None, patch_path=None, patch_digest=None,
    )
    cells = [(name, timed_out, receipt)]
    assert compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)[name]["measured"] is False
    block = compute_evidence(output, cells, task_dir=task_dir, manifest=manifest)[name]
    assert block["transcript"] is True and block["overlay_windows"] == 1
    assert block["timeline"] is False


def test_evidence_for_a_clean_hidden_cell_reports_zero_windows(tmp_path: Path) -> None:
    output, task_dir, manifest = _hidden_setup(tmp_path)
    cells = [_pathology_cell(output, "hidden-task-1", task="hidden-task", transcript=_GOOD_TRANSCRIPT)]
    assert compute_evidence(output, cells, task_dir=task_dir, manifest=manifest)["hidden-task-1"]["overlay_windows"] == 0


def test_evidence_says_when_a_cell_has_no_transcript_and_reads_a_timeline_when_present(tmp_path: Path) -> None:
    output, task_dir, manifest = _visible_setup(tmp_path)
    absent = _pathology_cell(output, "format_number-1", transcript=None)
    present = _pathology_cell(output, "format_number-2", transcript=_GOOD_TRANSCRIPT)
    (output / "format_number-2" / "timeline.jsonl").write_text(
        '{"at": 1.0, "event": "start", "toolCallId": "b", "toolName": "bash"}\n', encoding="utf-8"
    )
    blocks = compute_evidence(output, [absent, present], task_dir=task_dir, manifest=manifest)
    assert blocks["format_number-1"] == {"transcript": False}
    assert blocks["format_number-2"]["timeline"] is True
    assert blocks["format_number-2"]["unfinished_commands"] == 1
    assert blocks["format_number-2"]["overlay_windows"] is None


def test_regrade_reverts_a_reclassification_the_rule_no_longer_supports(
    tmp_path: Path,
) -> None:
    """Re-scoring derives the code from the transcript in *both*
    directions (correction 2026-09-06). A one-way promotion would strand
    every cell reclassified under a rule later found wrong -- and the
    rule was already corrected once, when a 503 was moved from model-side
    to infrastructure. The transcript is the authority, not the record."""
    context = _OOM_TRANSCRIPT.replace(
        "[METAL] Command buffer execution failed: Insufficient Memory "
        "(kIOGPUCommandBufferCallbackErrorOutOfMemory).",
        '400: {"message":"Prompt too long"}',
    )
    cell = _refusal_cell(tmp_path / "run", "cell-1", context)
    # a record wrongly reclassified under some earlier rule
    rec = load_attempt_record(cell / "attempt.json")
    write_attempt_record(
        cell / "attempt.json",
        replace(rec, code=AttemptCode.MODEL_ERROR, message="attempt refused: MODEL_ERROR"),
    )
    rewritten = regrade_attempt(cell, tasks_root=DEFAULT_TASKS_ROOT)
    assert rewritten is not None
    assert rewritten.code is AttemptCode.NO_PATCH
    assert load_attempt_record(cell / "attempt.json").code is AttemptCode.NO_PATCH
