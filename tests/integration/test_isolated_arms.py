"""Both arms under two-uid isolation, against a fake model, with the budget tripwire.

Roadmap row 2b: "the eval runs both arms against a fake under isolation
with the budget tripwire". The real harness, the real adapters, real sudo
and git; ``pi`` is `fake_pi_build.py` run as the cell user from a scratch
directory under the cells root. The Engine rows also need an engine
checkout (``SATYRN_V4_ENGINE_REPO``, as the Phase 2a rows do), exported for
the cell with `cell_engine.export_engine`. No model runs.
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from integration.cell_support import cell_process_alive
from integration.test_attempt import (
    _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
)
from satyrn_evals.arms import load_arm
from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_engine import RECEIPT_NAME
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.budget import AttemptBudget, LineBudget
from satyrn_evals.cell import (
    CELL_PATH_PREFIX_ENV,
    CELLS_ROOT,
    Isolation,
    share_with_cell,
)
from satyrn_evals.cell_engine import (
    EXPORT_PATHS,
    MARKER,
    export_engine,
    export_leaks,
    verify_export,
)
from satyrn_evals.hygiene import overlay_digests
from satyrn_evals.launch import SLOTS_DIR
from satyrn_evals.line_grade import grade_night, render_summary
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.run_record import RunRecord
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"
CAMPAIGN = AttemptBudget(output_tokens=32_000, turns=48)


def _cell_pi(scratch: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> Path:
    """Put a cell-readable fake ``pi`` first on the cell's PATH; return its pidfile path."""
    bin_dir = scratch / "bin"
    bin_dir.mkdir()
    shutil.copyfile(FAKE_PI, bin_dir / "fake_pi_build.py")
    pidfile = scratch / "pi.pid"
    shim = bin_dir / "pi"
    shim.write_text(
        f"#!/bin/sh\nSATYRN_FAKE_PI_MODE={mode} SATYRN_FAKE_PI_PIDFILE={pidfile} "
        f'exec python3 {bin_dir / "fake_pi_build.py"} "$@"\n'
    )
    shim.chmod(0o755)
    share_with_cell(scratch)
    monkeypatch.setenv(CELL_PATH_PREFIX_ENV, os.fspath(bin_dir))
    return pidfile


def _gone(pidfile: Path) -> None:
    pid = int(pidfile.read_text())
    stop = time.monotonic() + 15
    while time.monotonic() < stop:
        if not cell_process_alive(pid):
            return
        time.sleep(0.1)
    pytest.fail(f"fake pi {pid} outlived its cell")


def _baseline() -> list[str]:
    return [sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"]


def _no_cells_left(before: set[str]) -> None:
    assert {p.name for p in CELLS_ROOT.iterdir() if p.name.startswith("satyrn-attempt-")} <= before


def test_an_isolated_baseline_cell_commits_as_the_cell_user_and_is_harvested_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "commit")
    before = {p.name for p in CELLS_ROOT.iterdir()}
    output = tmp_path / "attempts"
    record = attempt(
        task="calc-build", tasks_root=TASKS, output=output, command=_baseline(), timeout=120,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED,
    )
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    cell = output / record.attempt_dir
    assert sorted(parse_patch_paths((cell / "patch.diff").read_text())) == ["calc/core.py", "calc/format.py", "calc/helpers.py"]
    assert json.loads((cell / "transcript.txt").read_text().splitlines()[0])["cwd"].startswith(os.fspath(CELLS_ROOT.resolve()))
    _no_cells_left(before)


def test_an_isolated_baseline_cell_over_budget_is_stopped_and_leaves_no_model_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    pidfile = _cell_pi(cell_scratch, monkeypatch, "spend")
    before = {p.name for p in CELLS_ROOT.iterdir()}
    record = attempt(
        task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts", command=_baseline(), timeout=120,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED,
    )
    assert record.code is AttemptCode.BUDGET_EXCEEDED, record.message
    assert (record.command_exit, record.retained_path) == (None, None)
    _gone(pidfile)
    _no_cells_left(before)


def _engine_arm(scratch: Path) -> list[str]:
    export = export_engine(_engine_repo(), "HEAD", root=scratch)
    uv = shutil.which("uv")
    assert uv is not None
    return [sys.executable, "-m", "satyrn_evals.attempt_engine", "--model", "omlx/fixture",
            "--engine-repo", os.fspath(export), "--uv-bin", "uv"]


def test_an_isolated_engine_cell_delivers_a_candidate_that_is_harvested_and_graded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "write")
    command = _engine_arm(cell_scratch)
    output = tmp_path / "attempts"
    record = attempt(
        task="calc-build", tasks_root=TASKS, output=output, command=command, timeout=300,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED,
    )
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    receipt = json.loads((output / record.attempt_dir / RECEIPT_NAME).read_text())
    assert (receipt["code"], receipt["validation"]) == ("OK", "passed")


def test_an_isolated_engine_cell_stopped_by_the_harness_leaves_no_model_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    pidfile = _cell_pi(cell_scratch, monkeypatch, "trickle")
    command = _engine_arm(cell_scratch)
    output = tmp_path / "attempts"
    before = {p.name for p in CELLS_ROOT.iterdir()}
    record = attempt(
        task="calc-build", tasks_root=TASKS, output=output, command=command, timeout=300,
        budget=AttemptBudget(output_tokens=16_000, turns=48), isolation=Isolation.ISOLATED,
    )
    assert record.code is AttemptCode.BUDGET_EXCEEDED, record.message
    assert (record.command_exit, record.retained_path) == (None, None)
    _gone(pidfile)
    assert record.attempt_dir is not None
    assert not (output / record.attempt_dir / RECEIPT_NAME).exists()
    _no_cells_left(before)


def test_an_isolated_engine_cells_line_crossing_is_harvested_from_its_own_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    """C1 (Opus review of a113f0b..3ecf068): the Engine's own internal
    deliver worktree is created by ``git worktree add`` run as the cell user
    (satyrn-engine's own subprocess, under isolation) -- its Git admin data
    is cell-owned, so a maintainer-run harvest against it must scope
    ``safe.directory`` to that one resolved path or git refuses it as
    "dubious ownership" (exit 128). A crossed line, harvested while the
    Engine's `deliver` is still running in its own private worktree, must
    read that worktree's real content -- not error, and not silently read
    the (not-yet-populated) Evals worktree instead."""
    _cell_pi(cell_scratch, monkeypatch, "line-cross")
    command = _engine_arm(cell_scratch)
    output = tmp_path / "attempts"
    from satyrn_evals.budget import LineBudget

    record = attempt(
        task="calc-build", tasks_root=TASKS, output=output, command=command, timeout=300,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED,
        line_budget=LineBudget(output_tokens=2_000, turns=40),
    )
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    cell = output / record.attempt_dir
    assert record.line_crossed is not None
    assert record.line_harvest_error is None, record.line_harvest_error
    line_patch = cell / "line.diff"
    assert line_patch.exists()
    assert sorted(parse_patch_paths(line_patch.read_text())) == [
        "calc/core.py", "calc/format.py", "calc/helpers.py",
    ]


def test_the_declared_line_is_harvested_and_graded_by_the_real_grader_on_both_arms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    """Permanent end-to-end row for the declared-line feature (release two):
    both arms (Baseline and the Engine arm from the pinned export), under
    ``Isolation.ISOLATED`` with the real cell user (as every other isolated-
    arm test in this file), a declared line the fake model crosses
    (``fake_pi_build.py``'s ``line-cross`` mode, added in 0302e0b), then
    ``line_grade.grade_night`` with the REAL grader on the bundled calc-build
    task -- no faked grader seam.

    Driven through ``attempt()`` directly, not the launcher (``launch
    RECORD``): the launcher's own default-tier fixtures build a frozen,
    git-tracked record and arm files with a live model-server preflight,
    every seam faked (``test_launch_record.py``'s ``_facts``/``_record``) --
    reusing them for a REAL two-cell isolated run would mean fighting the
    frozen/drift/model-server gates for no benefit, since ``attempt()`` is
    the one function both the launcher's own ``spawn()`` and this test call
    into. The remaining link -- the launcher puts a record's declared line
    onto every spawned slot spec -- is covered separately by N6's
    ``test_a_declared_line_reaches_every_spawned_slot_spec``
    (``tests/test_launch_record.py``). What this test adds beyond both of
    those and the existing per-arm line-harvest tests above: one assembled
    night with real cells from BOTH arms, graded together by the real
    offline grader, proving the whole harvest -> grade-line chain produces
    a passing per-(task, arm) row with nothing excluded.
    """
    _cell_pi(cell_scratch, monkeypatch, "line-cross")
    line = LineBudget(output_tokens=2_000, turns=40)
    night = tmp_path / "night"

    baseline_record = attempt(
        task="calc-build", tasks_root=TASKS, output=night / "baseline", command=_baseline(), timeout=120,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED, line_budget=line,
    )
    assert baseline_record.line_crossed is not None
    assert baseline_record.line_harvest_error is None, baseline_record.message

    engine_command = _engine_arm(cell_scratch)
    engine_record = attempt(
        task="calc-build", tasks_root=TASKS, output=night / "engine", command=engine_command, timeout=300,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED, line_budget=line,
    )
    assert engine_record.line_crossed is not None
    assert engine_record.line_harvest_error is None, engine_record.message

    records = {"baseline": baseline_record, "engine": engine_record}
    for arm, record in records.items():
        assert record.attempt_dir is not None
        line_patch = night / arm / record.attempt_dir / "line.diff"
        assert line_patch.exists() and line_patch.read_text().strip(), arm

    # Assemble the night's slots the way the launcher's own spawn()/write_ledger
    # would (launch.read_slots is what grade_night reuses to enumerate them).
    (night / SLOTS_DIR).mkdir(parents=True)
    for index, (arm, record) in enumerate(records.items()):
        (night / SLOTS_DIR / f"{index:02d}.json").write_text(
            json.dumps({"slot": index, "arm": arm, "attempt_dir": record.attempt_dir, "code": record.code.value})
        )

    run_record = RunRecord(
        version=1, task="calc-build", task_tree_sha256="0" * 64, arm="baseline+engine", model="omlx/fixture",
        condition="cold", n=1, mode="batch", max_minutes=60, stop_rule="infrastructure only",
        decision_rule="fisher", previous_result=None,
        token_budget=CAMPAIGN.output_tokens, turn_budget=CAMPAIGN.turns,
        isolation="isolated", purpose="development",
        line_token_budget=line.output_tokens, line_turn_budget=line.turns,
    )
    report = grade_night(night, run_record, tmp_path / "grades", tasks_root=TASKS)
    by_arm = {row.arm: row for row in report.rows}
    assert set(by_arm) == {"baseline", "engine"}
    for arm, row in by_arm.items():
        assert row.line_crossed is not None, arm
        assert row.line_harvest_error is None, (arm, row.line_harvest_error)
        assert row.line_verdict == "pass", (arm, row.line_verdict)

    summary = render_summary(report)
    assert "| calc-build | baseline | 1/1 | 0 |" in summary
    assert "| calc-build | engine | 1/1 | 0 |" in summary


def test_the_engine_export_is_made_once_and_runs_as_the_cell_user(cell_scratch: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from integration.cell_support import run_as_cell
    from satyrn_evals.cell import cell_environment
    from satyrn_evals.cli import main

    first = export_engine(_engine_repo(), "HEAD", root=cell_scratch)
    assert export_engine(_engine_repo(), "HEAD", root=cell_scratch) == first
    assert sorted(path.name for path in first.iterdir()) == sorted([*EXPORT_PATHS, ".venv", MARKER])
    environment = cell_environment(parent=cell_scratch)
    environment.pop("UV_PROJECT_ENVIRONMENT")  # as `attempt_engine.as_cell` does
    ran = run_as_cell(
        ["uv", "run", "--no-sync", "--project", os.fspath(first), "satyrn-engine", "--help"],
        cwd=first, environment=environment,
    )
    assert ran.returncode == 0 and "derive" in ran.stdout, ran.stderr
    probe = first / "probe"
    touched = run_as_cell(["/usr/bin/touch", os.fspath(probe)], cwd=first, environment=environment)
    assert touched.returncode != 0 and not probe.exists(), touched.stderr
    assert main(["cell-engine", "--engine-repo", os.fspath(_engine_repo()), "--commit", "not-a-commit"]) == 2


ENGINE_ARM = Path(__file__).resolve().parents[2] / "arms" / "engine-ornith15-9b.json"


def test_the_export_of_the_arms_pinned_commit_holds_no_grader_material(cell_scratch: Path) -> None:
    """341d4c4's whole tree holds ``tests/test_doc_caps.py``, the name of selfhost-docs-linter's hidden suite;
    its export holds only ``EXPORT_PATHS`` and the environment, and verifies."""
    commit = load_arm(ENGINE_ARM).pins.engine_commit
    assert commit is not None
    export = export_engine(_engine_repo(), commit, root=cell_scratch)
    assert export.name == f"engine-{commit}"
    assert not (export / "tests").exists() and not (export / "docs").exists()
    assert export_leaks(export, overlay_digests()) == []
    assert verify_export(export) == commit
