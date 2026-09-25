"""The timing wrapper derives setup/command/grading/residual from mtimes.

Every refusal below has a success sibling built from the same fixture shape
(`BRIEF.md` rule 6): the *only* difference between a refusing and an
accepting fixture is the one thing under test -- a missing artifact, an
incoherent timestamp, or an ambiguous directory. `AGENTS.md` requires the
default tier to stay model-, network-, and subprocess-free, so every test
here builds its fixture directly on disk with `os.utime` and never spawns
anything; the sole exception, the `run_and_measure` entry point, is marked
`@pytest.mark.integration` and drives only a trivial, model-free
`python -c` command.

The point of the refusal direction is the same "absent is not zero"
discipline as `scripts/token_floor.py`: a REFUSED attempt (no receipt, no
transcript) must report its dependent phases as MISSING with a named reason,
never as `0`, and incoherent input (end before start, an artifact predating
the wrapper, a receipt older than the transcript it grades) must be refused
by name rather than silently reported as a negative span.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from timing import (  # noqa: E402  # type: ignore[missing-import]  # scripts/ added via sys.path above
    ARTIFACT_NAMES,
    TimingError,
    main,
    measure_timing,
    run_and_measure,
)

_TASK = "demo-task"
_STAMP = "20260908-000000-000000"

# A whole-second base far from epoch 0, chosen the same way token_floor's
# fixtures pick concrete numbers: readable in a failure message, and far
# enough from 0 that a sign error would be obvious.
_BASE = 1_700_000_000.0


def _make_cell(
    tmp_path: Path,
    *,
    patch: float | None = None,
    transcript: float | None = None,
    receipt: float | None = None,
    attempt_record: float | None = None,
    extra_dirs: tuple[str, ...] = (),
    no_attempt_dir: bool = False,
) -> Path:
    """A cell directory holding one <task>-<stamp> attempt directory.

    Each of the four keyword args is a mtime (seconds, same unit as the
    fixture's wrapper_start/end below) or ``None`` to leave that artifact
    absent -- absence is the mechanism the REFUSED-attempt tests use.
    """
    cell_dir = tmp_path / "cell-000"
    cell_dir.mkdir()
    if no_attempt_dir:
        return cell_dir
    attempt_dir = cell_dir / f"{_TASK}-{_STAMP}"
    attempt_dir.mkdir()
    for name in extra_dirs:
        (cell_dir / name).mkdir()
    for filename, mtime in (
        ("patch.diff", patch),
        ("transcript.txt", transcript),
        ("receipt.json", receipt),
        ("attempt.json", attempt_record),
    ):
        if mtime is None:
            continue
        path = attempt_dir / filename
        path.write_text(filename, encoding="utf-8")
        os.utime(path, (mtime, mtime))
    return cell_dir


def _births(**by_name: float | None):
    """An injected birth-time reader.

    Unit tests must not depend on filesystem birth-time semantics: on APFS,
    ``os.utime`` to an older timestamp drags ``st_birthtime`` back with it, so
    a fixture cannot set mtime and birth time independently. Injecting the
    reader keeps the default tier hermetic and portable.
    """

    def read(path: Path) -> float | None:
        return by_name.get(path.name)

    return read


# --- successes -------------------------------------------------------------


def test_a_complete_attempt_derives_every_phase_and_a_separate_residual(
    tmp_path: Path,
) -> None:
    cell_dir = _make_cell(
        tmp_path,
        patch=_BASE + 5,
        transcript=_BASE + 10,
        receipt=_BASE + 20,
        attempt_record=_BASE + 21,
    )
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 30,
        birthtime_reader=_births(**{"transcript.txt": _BASE + 5}),
    )

    assert result.schema_version == 1
    assert result.attempt_dir == f"{_TASK}-{_STAMP}"
    assert result.missing == {}
    assert result.phases == {"setup": 5.0, "command": 5.0, "grading": 10.0}
    assert result.residual_seconds == 10.0
    assert result.residual_missing is None
    # total is authoritative and independent of the phase breakdown, but the
    # two are consistent here because every artifact was observed.
    assert result.total_seconds == 30.0
    assert "wall-clock" in result.total_source
    assert result.artifact_mtimes == {
        "patch.diff": _BASE + 5,
        "transcript.txt": _BASE + 10,
        "receipt.json": _BASE + 20,
        "attempt.json": _BASE + 21,
    }
    # every reported figure is named as a filesystem observation
    assert "filesystem observations" in result.boundary_note
    assert "not instrumented spans" in result.boundary_note


def test_the_residual_is_never_folded_into_the_phases_dict(tmp_path: Path) -> None:
    """Guards the double-counting failure mode named in the spec."""
    cell_dir = _make_cell(
        tmp_path,
        patch=_BASE + 5,
        transcript=_BASE + 10,
        receipt=_BASE + 20,
        attempt_record=_BASE + 21,
    )
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 30,
        birthtime_reader=_births(**{"transcript.txt": _BASE + 5}),
    )

    assert "residual" not in result.phases
    assert set(result.phases) <= {"setup", "command", "grading"}
    # the phases plus the residual happen to add back up to total here, but
    # total is computed independently (wrapper_end - wrapper_start), not by
    # summing phases + residual -- summing is a coincidence of this fixture,
    # not how total_seconds is derived.
    summed = sum(result.phases.values()) + result.residual_seconds
    assert summed == pytest.approx(result.total_seconds)


# --- REFUSED attempts: missing, not zero ------------------------------------


def test_a_refused_attempt_with_no_receipt_reports_grading_missing_not_zero(
    tmp_path: Path,
) -> None:
    cell_dir = _make_cell(
        tmp_path,
        patch=_BASE + 5,
        transcript=_BASE + 10,
        receipt=None,
        attempt_record=_BASE + 11,
    )
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 30,
        birthtime_reader=_births(**{"transcript.txt": _BASE + 5}),
    )

    assert result.phases == {"setup": 5.0, "command": 5.0}
    assert "grading" not in result.phases
    assert "receipt.json is absent" in result.missing["grading"]
    assert result.residual_seconds is None
    assert "receipt.json is absent" in result.residual_missing
    # total is still reported: it comes from the wrapper's own clock.
    assert result.total_seconds == 30.0


def test_a_missing_transcript_reports_command_and_grading_missing_not_zero(
    tmp_path: Path,
) -> None:
    cell_dir = _make_cell(
        tmp_path,
        patch=_BASE + 5,
        transcript=None,
        receipt=None,
        attempt_record=_BASE + 6,
    )
    result = measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)

    # Without a transcript there is no observable setup/command boundary, so
    # setup is reported missing rather than guessed from another artifact.
    assert result.phases == {}
    assert "command" not in result.phases and "grading" not in result.phases
    assert "boundary is unknown" in result.missing["setup"]
    assert "transcript.txt is absent" in result.missing["command"]
    assert "transcript.txt is absent" in result.missing["grading"]
    assert result.total_seconds == 30.0


def test_an_attempt_directory_with_no_artifacts_at_all_reports_only_total(
    tmp_path: Path,
) -> None:
    cell_dir = tmp_path / "cell-000"
    cell_dir.mkdir()
    (cell_dir / f"{_TASK}-{_STAMP}").mkdir()  # exists, but writes nothing
    result = measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)

    assert result.phases == {}
    assert set(result.missing) == {"setup", "command", "grading"}
    assert result.residual_seconds is None
    assert result.total_seconds == 30.0


def test_a_cell_with_no_attempt_directory_at_all_still_reports_total(
    tmp_path: Path,
) -> None:
    """The most extreme absence: not even an attempt directory was created."""
    cell_dir = _make_cell(tmp_path, no_attempt_dir=True)
    result = measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)

    assert result.attempt_dir is None
    assert result.phases == {}
    assert set(result.missing) == {"setup", "command", "grading"}
    assert "no attempt directory" in result.missing["setup"]
    assert result.residual_seconds is None
    assert result.total_seconds == 30.0


# --- incoherent input: refuse and name what was observed -------------------


def test_end_before_start_is_refused() -> None:
    with pytest.raises(TimingError, match="incoherent") as caught:
        measure_timing(
            Path("/nonexistent-does-not-matter"),
            wrapper_start=_BASE + 10,
            wrapper_end=_BASE,
        )
    message = str(caught.value)
    assert str(_BASE + 10) in message
    assert str(_BASE) in message


def test_end_after_start_is_accepted(tmp_path: Path) -> None:
    cell_dir = _make_cell(tmp_path, no_attempt_dir=True)
    result = measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 1)
    assert result.total_seconds == 1.0


def test_an_artifact_predating_the_wrapper_start_is_refused(tmp_path: Path) -> None:
    cell_dir = _make_cell(tmp_path, patch=_BASE - 10)
    with pytest.raises(TimingError, match="patch.diff") as caught:
        measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)
    assert "predates wrapper start" in str(caught.value)


def test_an_artifact_at_or_after_wrapper_start_is_accepted(tmp_path: Path) -> None:
    cell_dir = _make_cell(tmp_path, patch=_BASE, transcript=_BASE + 1)
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 30,
        birthtime_reader=_births(**{"transcript.txt": _BASE}),
    )
    assert result.phases["setup"] == 0.0


def test_a_receipt_older_than_its_transcript_is_refused(tmp_path: Path) -> None:
    cell_dir = _make_cell(
        tmp_path, patch=_BASE + 1, transcript=_BASE + 10, receipt=_BASE + 5
    )
    with pytest.raises(TimingError, match="grading cannot have finished") as caught:
        measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)
    message = str(caught.value)
    assert str(_BASE + 5) in message
    assert str(_BASE + 10) in message


def test_a_receipt_at_or_after_its_transcript_is_accepted(tmp_path: Path) -> None:
    cell_dir = _make_cell(
        tmp_path, patch=_BASE + 1, transcript=_BASE + 10, receipt=_BASE + 10
    )
    result = measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)
    assert result.phases["grading"] == 0.0


def test_a_receipt_after_wrapper_end_is_refused(tmp_path: Path) -> None:
    cell_dir = _make_cell(
        tmp_path, patch=_BASE + 1, transcript=_BASE + 5, receipt=_BASE + 40
    )
    with pytest.raises(TimingError, match="negative residual"):
        measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)


def test_a_receipt_at_wrapper_end_is_accepted(tmp_path: Path) -> None:
    cell_dir = _make_cell(
        tmp_path, patch=_BASE + 1, transcript=_BASE + 5, receipt=_BASE + 30
    )
    result = measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)
    assert result.residual_seconds == 0.0


def test_a_missing_cell_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TimingError, match="no such cell directory"):
        measure_timing(
            tmp_path / "never-created", wrapper_start=_BASE, wrapper_end=_BASE + 1
        )


def test_an_existing_cell_directory_is_accepted(tmp_path: Path) -> None:
    cell_dir = _make_cell(tmp_path, no_attempt_dir=True)
    assert cell_dir.is_dir()
    measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 1)  # no raise


def test_more_than_one_attempt_directory_is_an_ambiguous_refusal(
    tmp_path: Path,
) -> None:
    cell_dir = _make_cell(tmp_path, patch=_BASE + 1)
    (cell_dir / f"{_TASK}-20260101-000000-000000").mkdir()
    with pytest.raises(TimingError, match="ambiguous"):
        measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)


def test_a_sibling_engine_contracts_directory_is_not_an_attempt_directory(
    tmp_path: Path,
) -> None:
    """Regression: every real cell holds ``engine-contracts/`` beside the attempt.

    An only-child rule refused on every cell a real run produces. The full
    synthetic suite passed while that was true; running the tool against a
    retained cell is what surfaced it.
    """
    cell_dir = _make_cell(tmp_path, patch=_BASE + 1, transcript=_BASE + 5)
    (cell_dir / "engine-contracts").mkdir()
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 30,
        birthtime_reader=_births(**{"transcript.txt": _BASE + 1}),
    )
    assert result.attempt_dir == f"{_TASK}-{_STAMP}"
    assert result.phases["command"] == pytest.approx(4.0)


def test_exactly_one_subdirectory_is_accepted(tmp_path: Path) -> None:
    cell_dir = _make_cell(tmp_path, patch=_BASE + 1)
    result = measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 30)
    assert result.attempt_dir == f"{_TASK}-{_STAMP}"


def test_a_negative_supplied_authoritative_total_is_refused(tmp_path: Path) -> None:
    cell_dir = _make_cell(tmp_path, no_attempt_dir=True)
    with pytest.raises(TimingError, match="authoritative total is negative"):
        measure_timing(
            cell_dir,
            wrapper_start=_BASE,
            wrapper_end=_BASE + 1,
            total_seconds=-1.0,
        )


def test_a_nonnegative_supplied_authoritative_total_is_accepted(
    tmp_path: Path,
) -> None:
    cell_dir = _make_cell(tmp_path, no_attempt_dir=True)
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 1,
        total_seconds=0.5,
        total_source="monotonic wrapper bounds",
    )
    assert result.total_seconds == 0.5
    assert result.total_source == "monotonic wrapper bounds"


# --- the artifact names this module reads, kept explicit --------------------


def test_the_four_artifact_names_match_the_record() -> None:
    assert ARTIFACT_NAMES == (
        "patch.diff",
        "transcript.txt",
        "receipt.json",
        "attempt.json",
    )


# --- the CLI, both directions -----------------------------------------------


def test_cli_measure_records_a_coherent_timing(tmp_path: Path) -> None:
    cell_dir = _make_cell(
        tmp_path,
        patch=_BASE + 5,
        transcript=_BASE + 10,
        receipt=_BASE + 20,
        attempt_record=_BASE + 21,
    )
    record = tmp_path / "timing.json"
    assert (
        main(
            [
                "measure",
                str(cell_dir),
                "--start",
                str(_BASE),
                "--end",
                str(_BASE + 30),
                "--record",
                str(record),
            ]
        )
        == 0
    )
    stored = json.loads(record.read_text(encoding="utf-8"))
    assert stored["schema_version"] == 1
    # The setup/command split depends on filesystem birth-time support, which
    # the CLI reads for real; grading, residual and total do not.
    assert stored["phases"]["grading"] == 10.0
    assert set(stored["phases"]) <= {"setup", "command", "setup_and_command", "grading"}
    assert stored["residual_seconds"] == 10.0
    assert stored["total_seconds"] == 30.0
    assert "measurement_source" in stored
    assert "boundary_note" in stored


def test_cli_measure_refuses_and_writes_no_record_on_incoherent_input(
    tmp_path: Path,
) -> None:
    cell_dir = _make_cell(tmp_path, no_attempt_dir=True)
    record = tmp_path / "timing.json"
    assert (
        main(
            [
                "measure",
                str(cell_dir),
                "--start",
                str(_BASE + 10),
                "--end",
                str(_BASE),
                "--record",
                str(record),
            ]
        )
        == 1
    )
    assert not record.exists()


def test_cli_measure_reports_a_missing_cell_directory_distinctly(
    tmp_path: Path,
) -> None:
    assert (
        main(
            [
                "measure",
                str(tmp_path / "nope"),
                "--start",
                "0",
                "--end",
                "1",
            ]
        )
        == 2
    )


# --- the run entry point: subprocess-using, integration tier only ----------


@pytest.mark.integration
def test_run_and_measure_times_a_trivial_model_free_command(tmp_path: Path) -> None:
    """Drives ``python -c`` -- never a model, never the engine, never a network call."""
    cell_dir = tmp_path / "cell-000"
    cell_dir.mkdir()
    attempt_dir = cell_dir / f"{_TASK}-{_STAMP}"
    script = textwrap.dedent(
        f"""
        import pathlib
        attempt = pathlib.Path({str(attempt_dir)!r})
        attempt.mkdir(parents=True)
        (attempt / "patch.diff").write_text("diff")
        (attempt / "transcript.txt").write_text("transcript")
        (attempt / "receipt.json").write_text("{{}}")
        (attempt / "attempt.json").write_text("{{}}")
        """
    )
    result = run_and_measure([sys.executable, "-c", script], cell_dir)

    assert result.attempt_dir == f"{_TASK}-{_STAMP}"
    assert result.total_seconds >= 0.0
    assert "monotonic" in result.total_source
    assert result.missing == {}
    assert result.residual_seconds is not None
    assert result.residual_seconds >= 0.0


# --- the setup/command boundary comes from birth time, not earliest mtime ---


def test_the_command_span_starts_at_the_transcript_birth_not_earliest_mtime(
    tmp_path: Path,
) -> None:
    """An mtime is a *last* write, so it cannot mark where the command began.

    Verified against a retained cell: reading the boundary from the earliest
    mtime attributed the whole 46.6 s command to setup and left the command
    itself at 0.0 s.
    """
    cell_dir = _make_cell(
        tmp_path,
        patch=_BASE + 47,
        transcript=_BASE + 47,
        receipt=_BASE + 49,
        attempt_record=_BASE + 49,
    )
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 50,
        birthtime_reader=_births(**{"transcript.txt": _BASE + 0.3}),
    )

    assert result.phases["setup"] == pytest.approx(0.3)
    assert result.phases["command"] == pytest.approx(46.7)
    assert result.phases["grading"] == pytest.approx(2.0)


def test_without_a_birth_time_setup_and_command_are_one_combined_span(
    tmp_path: Path,
) -> None:
    """The honest fallback: report one span rather than invent two."""
    cell_dir = _make_cell(
        tmp_path,
        patch=_BASE + 47,
        transcript=_BASE + 47,
        receipt=_BASE + 49,
        attempt_record=_BASE + 49,
    )
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 50,
        birthtime_reader=_births(),  # reads None for every artifact
    )

    assert "setup" not in result.phases
    assert "command" not in result.phases
    assert result.phases["setup_and_command"] == pytest.approx(47.0)
    assert "unobservable" in result.missing["setup"]
    assert "unobservable" in result.missing["command"]
    assert result.phases["grading"] == pytest.approx(2.0)


def test_a_transcript_born_before_the_wrapper_started_is_refused(
    tmp_path: Path,
) -> None:
    cell_dir = _make_cell(tmp_path, patch=_BASE + 1, transcript=_BASE + 10)
    with pytest.raises(TimingError, match="predates wrapper start"):
        measure_timing(
            cell_dir,
            wrapper_start=_BASE,
            wrapper_end=_BASE + 30,
            birthtime_reader=_births(**{"transcript.txt": _BASE - 5}),
        )


# --- producer ordering: the labels must not overstate what mtimes measure --


def test_the_artifact_states_lifecycle_durations_are_unmeasured_and_names_the_limitation(
    tmp_path: Path,
) -> None:
    """Every result carries the disclosure, regardless of the fixture's shape."""
    cell_dir = _make_cell(tmp_path, no_attempt_dir=True)
    result = measure_timing(cell_dir, wrapper_start=_BASE, wrapper_end=_BASE + 1)

    assert result.lifecycle_durations == "unmeasured by this filesystem-mtime method"
    assert "patch.diff" in result.producer_ordering_limitation
    assert "AFTER" in result.producer_ordering_limitation
    assert set(result.interval_definitions) == {
        "setup",
        "command",
        "setup_and_command",
        "grading",
        "residual",
    }


def test_producer_ordering_patch_after_transcript_does_not_relabel_grading_as_pure(
    tmp_path: Path,
) -> None:
    """Exercises the real engine's producer ordering, per Sol's note.

    The real engine writes ``patch.diff`` AFTER the final ``transcript.txt``
    write (verified 22 ms later on a retained cell), not before it as the
    other fixtures in this file assume for readability. This fixture mirrors
    that real ordering -- patch.diff mtime after transcript.txt mtime -- and
    checks that the resulting artifact still discloses the limitation and
    that the 'grading' interval's own definition disclaims being grading
    alone, rather than silently presenting a clean phase breakdown.
    """
    cell_dir = _make_cell(
        tmp_path,
        transcript=_BASE + 10,
        patch=_BASE + 10.022,  # patch published 22ms AFTER the transcript, as real
        receipt=_BASE + 20,
        attempt_record=_BASE + 21,
    )
    result = measure_timing(
        cell_dir,
        wrapper_start=_BASE,
        wrapper_end=_BASE + 30,
        birthtime_reader=_births(**{"transcript.txt": _BASE + 5}),
    )

    # The interval is still computed as transcript mtime -> receipt mtime --
    # the code does not (and cannot) exclude patch publication from it.
    assert result.phases["grading"] == pytest.approx(10.0)
    # But its definition must not claim to be grading alone.
    grading_definition = result.interval_definitions["grading"]
    assert "not grading alone" in grading_definition
    assert "patch" in grading_definition
    # And the run-level limitation note is present and names the same reason.
    assert "patch.diff is published AFTER" in result.producer_ordering_limitation
    assert result.lifecycle_durations == "unmeasured by this filesystem-mtime method"


def test_a_transcript_born_after_its_own_mtime_is_refused(tmp_path: Path) -> None:
    cell_dir = _make_cell(tmp_path, patch=_BASE + 1, transcript=_BASE + 10)
    with pytest.raises(TimingError, match="cannot have started after"):
        measure_timing(
            cell_dir,
            wrapper_start=_BASE,
            wrapper_end=_BASE + 30,
            birthtime_reader=_births(**{"transcript.txt": _BASE + 20}),
        )
