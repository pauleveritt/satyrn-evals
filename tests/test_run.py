"""run: repeat the attempt seam n times and write a counts-only summary."""

from pathlib import Path

import pytest

import satyrn_evals.run as run_module
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.verdict import Verdict


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
        return ok_record()

    monkeypatch.setattr(run_module, "attempt", fake_attempt)
    summary = run_module.run(
        task="t", tasks_root=tmp_path, output=tmp_path, command=["fake"], n=2, timeout=1.5
    )
    assert len(calls) == 2
    assert summary.n == 2 and summary.attempted == 2 and summary.refused == 0
    assert (tmp_path / "summary.json").exists()


def test_run_refuses_non_positive_n(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_module, "attempt", lambda **kwargs: ok_record())
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
