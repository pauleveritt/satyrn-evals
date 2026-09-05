"""The strict tally: it refuses a malformed batch rather than shrinking a
denominator.

No model, no network, no subprocess — every fixture is on-disk JSON under
``tmp_path``.

**Why both directions (BRIEF rule 8).** A checker whose normal state is
silence passes every day while broken. So the module is exercised as a
pair for each failure mode: one row mutates exactly one cell of a
known-good 24-cell batch and names the refusal kind it expects, and the
sibling success is `test_the_expected_set_tallies_to_the_expected_counts`
over that same batch, unmutated. Twelve refusal kinds, one success the
whole file leans on.
"""

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.verdict import Verdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from tally import (  # noqa: E402  # type: ignore[missing-import]  # scripts/ added via sys.path above
    Refusal,
    TallyRefused,
    main,
    tally,
)

TASK = "agentclinic-repair-plausible-wrong-fix"
RUNG = "R1"
DIGEST = "a" * 64
MODEL = "omlx/gemma-4-12B-it-MLX-8bit"
BASELINE_CMD = [
    "satyrn-evals-attempt-pi",
    "--model",
    MODEL,
    "--tools",
    "read,bash,edit,write",
]
ENGINE_CMD = ["satyrn-engine", "attempt", "--model", MODEL]
N_PER_ARM = 12


def _counts(keys: list[str], hit: str) -> dict[str, int]:
    return {key: (1 if key == hit else 0) for key in keys}


def _summary(
    *,
    cell: str,
    command: list[str],
    task: str = TASK,
    rung: str | None = RUNG,
    digest: str | None = DIGEST,
    code: str = AttemptCode.OK.value,
    verdict: str = Verdict.PASS.value,
    outcome_flag: str = "clean",
    measured: bool = True,
) -> dict[str, object]:
    """One `run --n 1` summary, in the shape `summary.py` writes plus the
    two fields V11a adds (`rung`, `contract_digest`)."""
    code_counts = _counts([member.value for member in AttemptCode], code)
    return {
        "n": 1,
        "attempted": 1 if code != AttemptCode.NO_PATCH.value else 0,
        "refused": 0 if code != AttemptCode.NO_PATCH.value else 1,
        "code_counts": code_counts,
        "verdict_counts": _counts([member.value for member in Verdict], verdict),
        "timeouts": code_counts[AttemptCode.COMMAND_TIMEOUT.value],
        "task": task,
        "command": command,
        "timeout": 900.0,
        "oracle_visibility": "hidden",
        "cells": [cell],
        "contamination": {
            "graded": 1,
            "flagged": 1 if outcome_flag == "flagged" else 0,
            "clean": 1 if outcome_flag == "clean" else 0,
            "unmeasured": 1 if outcome_flag == "unmeasured" else 0,
        },
        "pathology": {
            cell: (
                {"measured": True, "tool_calls": {"read": 3}}
                if measured
                else {"measured": False, "reason": "unknown_event"}
            )
        },
        "rung": rung,
        "contract_digest": digest,
    }


type Mutate = Callable[[int, str, dict[str, object]], dict[str, object] | None]


@pytest.fixture()
def batch(tmp_path: Path) -> Callable[..., tuple[Path, Path]]:
    """Builds a 24-cell batch on disk; ``mutate`` may alter or drop a cell.

    ``mutate(index, arm, summary)`` returns the summary to write, or None
    to write no ``summary.json`` at all.
    """

    def build(mutate: Mutate | None = None) -> tuple[Path, Path]:
        runs = tmp_path / "runs"
        runs.mkdir()
        cells = []
        for index in range(N_PER_ARM * 2):
            arm = "baseline" if index % 2 == 0 else "engine"
            command = BASELINE_CMD if arm == "baseline" else ENGINE_CMD
            name = f"cell-{index:03d}-{arm}"
            cells.append({"index": index, "arm": arm, "dir": name, "command": command})
            directory = runs / name
            directory.mkdir()
            summary = _summary(cell=f"{TASK}-2026090512{index:04d}", command=command)
            if mutate is not None and (
                (replaced := mutate(index, arm, summary)) is not summary
            ):
                if replaced is None:
                    continue
                summary = replaced
            (directory / "summary.json").write_text(json.dumps(summary))
        schedule = tmp_path / "schedule.json"
        schedule.write_text(
            json.dumps(
                {
                    "version": 1,
                    "seed": 20260905,
                    "task": TASK,
                    "rung": RUNG,
                    "contract_digest": DIGEST,
                    "model": MODEL,
                    "cells": cells,
                }
            )
        )
        return schedule, runs

    return build


def _refuses(build: Callable[..., tuple[Path, Path]], mutate: Mutate) -> list[Refusal]:
    schedule, runs = build(mutate)
    with pytest.raises(TallyRefused) as caught:
        tally(schedule, runs)
    return caught.value.refusals


# --- the success the whole file leans on -----------------------------------


def test_the_expected_set_tallies_to_the_expected_counts(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    schedule, runs = batch()
    result = tally(schedule, runs)
    assert result.cells == 24
    assert result.per_arm["baseline"]["cells"] == 12
    assert result.per_arm["engine"]["cells"] == 12
    assert result.per_arm["baseline"]["verdict_counts"]["pass"] == 12
    assert result.per_arm["engine"]["code_counts"]["OK"] == 12
    assert result.per_arm["baseline"]["timeouts"] == 0
    assert result.per_arm["engine"]["contamination"]["clean"] == 12
    assert result.per_arm["baseline"]["pathology"] == {"measured": 12, "unmeasured": 0}
    assert "duration" not in json.dumps(result.to_wire())  # counts only


def test_a_flagged_cell_stays_in_the_denominator(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    """Contamination is reported beside the denominator, never subtracted
    from it (V7). Sibling refusal rows are below; this row is the reason
    they must not be implemented by dropping cells."""

    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 4:
            return summary
        return _summary(cell="c-4", command=BASELINE_CMD, outcome_flag="flagged")

    schedule, runs = batch(mutate)
    result = tally(schedule, runs)
    assert result.cells == 24
    assert result.per_arm["baseline"]["cells"] == 12
    assert result.per_arm["baseline"]["contamination"]["flagged"] == 1
    assert result.per_arm["baseline"]["contamination"]["clean"] == 11


def test_an_unmeasured_pathology_cell_is_counted_not_dropped(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 6:
            return summary
        return _summary(cell="c-6", command=BASELINE_CMD, measured=False)

    schedule, runs = batch(mutate)
    result = tally(schedule, runs)
    assert result.per_arm["baseline"]["pathology"] == {"measured": 11, "unmeasured": 1}
    assert result.per_arm["baseline"]["cells"] == 12


# --- one refusal row per failure mode --------------------------------------


def test_a_missing_expected_cell_is_refused(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    refusals = _refuses(batch, lambda i, a, s: None if i == 3 else s)
    assert [r.kind for r in refusals] == ["missing"]
    assert refusals[0].cell == "cell-003-engine"


def test_an_aborted_cell_is_refused(
    batch: Callable[..., tuple[Path, Path]], tmp_path: Path
) -> None:
    """V9 writes `aborted.json`, never `summary.json`, for a partial batch."""
    schedule, runs = batch(lambda i, a, s: None if i == 5 else s)
    (runs / "cell-005-engine" / "aborted.json").write_text(
        json.dumps({"requested": 1, "completed": 0, "error": "boom"})
    )
    with pytest.raises(TallyRefused) as caught:
        tally(schedule, runs)
    assert [r.kind for r in caught.value.refusals] == ["aborted"]


def test_a_duplicate_attempt_cell_is_refused(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    """Two run directories naming the same attempt cell would double-count
    one attempt, which inflates a denominator as surely as dropping one
    shrinks it."""

    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 2:
            return summary
        return _summary(cell=f"{TASK}-20260905120000", command=BASELINE_CMD)

    refusals = _refuses(batch, mutate)
    assert [r.kind for r in refusals] == ["duplicate"]


def test_an_unexpected_task_is_refused(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 7:
            return summary
        return _summary(cell="c-7", command=ENGINE_CMD, task="local-pings")

    refusals = _refuses(batch, mutate)
    assert [r.kind for r in refusals] == ["unexpected_task"]
    assert "local-pings" in refusals[0].detail


def test_a_wrong_rung_is_refused(batch: Callable[..., tuple[Path, Path]]) -> None:
    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 8:
            return summary
        return _summary(cell="c-8", command=BASELINE_CMD, rung="R3")

    assert [r.kind for r in _refuses(batch, mutate)] == ["wrong_rung"]


def test_a_summary_with_no_rung_field_is_refused(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    """A pre-V11a summary cannot prove which contract the model saw."""

    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 9:
            return summary
        stripped = _summary(cell="c-9", command=ENGINE_CMD)
        del stripped["rung"]
        return stripped

    assert [r.kind for r in _refuses(batch, mutate)] == ["wrong_rung"]


def test_a_wrong_contract_digest_is_refused(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 10:
            return summary
        return _summary(cell="c-10", command=BASELINE_CMD, digest="b" * 64)

    assert [r.kind for r in _refuses(batch, mutate)] == ["wrong_digest"]


def test_a_wrong_model_is_refused(batch: Callable[..., tuple[Path, Path]]) -> None:
    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 11:
            return summary
        command = ["satyrn-engine", "attempt", "--model", "omlx/other-model"]
        return _summary(cell="c-11", command=command)

    refusals = _refuses(batch, mutate)
    assert [r.kind for r in refusals] == ["wrong_model"]
    assert "omlx/other-model" in refusals[0].detail


def test_a_command_naming_no_model_is_refused(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 12:
            return summary
        return _summary(cell="c-12", command=["satyrn-evals-attempt-pi"])

    # a command truncated to its executable fails both checks, and both are
    # reported: the tally never stops at the first fault in a cell
    assert [r.kind for r in _refuses(batch, mutate)] == ["wrong_model", "wrong_arm"]


def test_a_wrong_arm_is_refused(batch: Callable[..., tuple[Path, Path]]) -> None:
    """The engine command in a directory the schedule assigned to baseline."""

    def mutate(index: int, arm: str, summary: dict[str, object]) -> dict[str, object]:
        if index != 14:
            return summary
        return _summary(cell="c-14", command=ENGINE_CMD)

    refusals = _refuses(batch, mutate)
    assert [r.kind for r in refusals] == ["wrong_arm"]
    assert refusals[0].cell == "cell-014-baseline"


def test_an_unreadable_summary_is_refused(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    schedule, runs = batch(lambda i, a, s: None if i == 15 else s)
    (runs / "cell-015-engine" / "summary.json").write_text("{not json")
    with pytest.raises(TallyRefused) as caught:
        tally(schedule, runs)
    assert [r.kind for r in caught.value.refusals] == ["unreadable"]


def test_a_run_directory_the_schedule_never_named_is_refused(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    """A stray summary under the runs root is a cell nobody scheduled; the
    tally must not silently ignore it."""
    schedule, runs = batch()
    stray = runs / "cell-999-baseline"
    stray.mkdir()
    (stray / "summary.json").write_text(
        json.dumps(_summary(cell="stray", command=BASELINE_CMD))
    )
    with pytest.raises(TallyRefused) as caught:
        tally(schedule, runs)
    assert [r.kind for r in caught.value.refusals] == ["unscheduled"]


def test_every_refusal_is_reported_not_just_the_first(
    batch: Callable[..., tuple[Path, Path]],
) -> None:
    """Refusing on the first fault would hide the rest behind repeated runs."""
    refusals = _refuses(batch, lambda i, a, s: None if i in (1, 2, 3) else s)
    assert [r.kind for r in refusals] == ["missing"] * 3


def test_a_schedule_that_is_not_this_version_is_refused(tmp_path: Path) -> None:
    """Sibling success: every row above reads a version-1 schedule."""
    schedule = tmp_path / "schedule.json"
    schedule.write_text(json.dumps({"version": 2, "cells": []}))
    with pytest.raises(TallyRefused, match="version"):
        tally(schedule, tmp_path)


# --- the executable shell --------------------------------------------------


def test_main_writes_the_tally_and_exits_zero(
    batch: Callable[..., tuple[Path, Path]], tmp_path: Path, capsys
) -> None:
    schedule, runs = batch()
    out = tmp_path / "tally.json"
    assert main([str(schedule), str(runs), "--output", str(out)]) == 0
    written = json.loads(out.read_text())
    assert written["cells"] == 24
    assert written["per_arm"]["engine"]["cells"] == 12
    assert "24" in capsys.readouterr().out


def test_main_refuses_and_writes_no_tally(
    batch: Callable[..., tuple[Path, Path]], tmp_path: Path, capsys
) -> None:
    """Sibling success: the row above. A refused batch produces no counts
    at all — a partial number is what "shrinking a denominator" looks like."""
    schedule, runs = batch(lambda i, a, s: None if i == 3 else s)
    out = tmp_path / "tally.json"
    assert main([str(schedule), str(runs), "--output", str(out)]) == 1
    assert not out.exists()
    assert "missing" in capsys.readouterr().err


def test_main_without_an_output_path_still_prints(
    batch: Callable[..., tuple[Path, Path]], capsys
) -> None:
    schedule, runs = batch()
    assert main([str(schedule), str(runs)]) == 0
    assert '"cells": 24' in capsys.readouterr().out
