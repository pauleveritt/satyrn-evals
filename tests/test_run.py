"""run: repeat the attempt seam n times and write a counts-only summary.

The default-tier tests monkeypatch ``attempt`` with a double that creates
the attempt directory and writes a receipt.json, so run's directory-delta
cell naming is exercised without spawning a subprocess. The end-to-end
fake-seam variant lives in tests/integration/test_run.py.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

import satyrn_evals.run as run_module
from satyrn_evals.attempt import attempt_dir_name
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.verdict import Verdict

HIDDEN_TASK_NAME = "session-mechanics"
# A grade-produced hidden receipt: the patch scanned clean against the overlay.
_CLEAN_RECEIPT = (
    '{"verdict": "pass", "contamination": {"visibility": "hidden", '
    '"checks": [{"check": "grader_content_in_patch", "outcome": "clean", '
    '"evidence": []}]}}'
)


def ok_record() -> AttemptRecord:
    return AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.OK,
        message="ok",
        task="t",
        command=("fake",),
        command_exit=0,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest="a" * 64,
        transcript_digest="b" * 64,
        verdict=Verdict.PASS,
        receipt_path="receipt.json",
        workspace_base_sha="c" * 40,
    )


def _fake_attempt_factory(records: list[AttemptRecord]) -> object:
    """A non-spawning attempt double that creates the attempt directory.

    Mirrors attempt()'s directory contract (one new <task>-<stamp> dir per
    call holding receipt.json) so run's directory-delta cell naming works.
    """

    def fake_attempt(
        *,
        task: str,
        tasks_root: Path,
        output: Path,
        command: list[str],
        timeout: float,
    ) -> AttemptRecord:
        output.mkdir(parents=True, exist_ok=True)
        cell_dir = output / attempt_dir_name(task, datetime.now(UTC))
        cell_dir.mkdir()
        (cell_dir / "receipt.json").write_text(
            '{"verdict": "pass"}', encoding="utf-8"
        )
        record = records.pop(0) if records else ok_record()
        records.append(record)
        return record

    return fake_attempt


def test_run_calls_attempt_n_times_and_writes_summary(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[str] = []

    def fake_attempt(
        *,
        task: str,
        tasks_root: Path,
        output: Path,
        command: list[str],
        timeout: float,
    ) -> AttemptRecord:
        calls.append(task)
        output.mkdir(parents=True, exist_ok=True)
        cell_dir = output / attempt_dir_name(task, datetime.now(UTC))
        cell_dir.mkdir()
        (cell_dir / "receipt.json").write_text(
            '{"verdict": "pass"}', encoding="utf-8"
        )
        return ok_record()

    monkeypatch.setattr(run_module, "attempt", fake_attempt)
    summary = run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=tmp_path,
        command=["fake"], n=2, timeout=1.5,
    )
    assert len(calls) == 2
    assert summary.n == 2 and summary.attempted == 2 and summary.refused == 0
    assert len(summary.cells) == 2
    assert (tmp_path / "summary.json").exists()


def test_run_summary_names_created_attempt_dirs(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(run_module, "attempt", _fake_attempt_factory([]))
    output = tmp_path / "out"
    summary = run_module.run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=["fake"],
        n=3,
    )
    assert len(summary.cells) == 3
    assert all(name.startswith("format_number-") for name in summary.cells)
    # directory-delta names are unique and match real on-disk dirs
    assert sorted(summary.cells) == sorted(
        p.name for p in output.iterdir() if p.name.startswith("format_number-")
    )
    assert summary.oracle_visibility == "visible"
    assert summary.contamination is None


def test_run_on_hidden_task_tallies_contamination(
    tmp_path: Path, monkeypatch
) -> None:
    """Default-tier sibling: run() against a hidden manifest still tallies.

    The hidden task's manifest marks the oracle hidden, so run() must produce
    the contamination section even when the seam is faked in-process (the
    non-spawning double writes graded, contamination-bearing receipts). The
    spawning end-to-end twin lives in tests/integration/test_run.py.
    """

    def fake_attempt(
        *,
        task: str,
        tasks_root: Path,
        output: Path,
        command: list[str],
        timeout: float,
    ) -> AttemptRecord:
        output.mkdir(parents=True, exist_ok=True)
        cell_dir = output / attempt_dir_name(task, datetime.now(UTC))
        cell_dir.mkdir()
        (cell_dir / "receipt.json").write_text(_CLEAN_RECEIPT, encoding="utf-8")
        return ok_record()

    monkeypatch.setattr(run_module, "attempt", fake_attempt)
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


def test_run_refuses_when_attempt_creates_no_directory(
    tmp_path: Path, monkeypatch
) -> None:
    """A delta of zero (or more than one) is a seam contract breach: never guess."""

    def silent_attempt(**_kwargs: object) -> AttemptRecord:
        return ok_record()  # creates no directory

    monkeypatch.setattr(run_module, "attempt", silent_attempt)
    with pytest.raises(RuntimeError, match="attempt created no attempt directory"):
        run_module.run(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=tmp_path / "out",
            command=["fake"],
            n=1,
        )


def test_run_refuses_non_positive_n(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_module, "attempt", _fake_attempt_factory([]))
    try:
        run_module.run(
            task="t", tasks_root=tmp_path, output=tmp_path, command=["fake"], n=0
        )
    except run_module.UsageError:
        pass
    else:
        raise AssertionError("run accepted n=0")


def test_run_rejects_a_nonpositive_n_directly(tmp_path: Path) -> None:
    import pytest

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
