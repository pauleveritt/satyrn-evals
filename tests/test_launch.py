"""The launcher's cell loop against fake cell processes and a fake clock: nothing spawns."""

import json
import signal
from pathlib import Path

import pytest

from satyrn_evals.errors import UsageError
from satyrn_evals.launch import (
    LEDGER_NAME,
    SLOTS_DIR,
    Slot,
    Status,
    check_night,
    infrastructure_reason,
    launch_cells,
    plan_slots,
    read_slots,
    slot_path,
    write_ledger,
)
from satyrn_evals.run import SignalAbort


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeCell:
    """A cell that finishes after ``polls`` polls, writing its slot record unless ``code`` is None."""

    def __init__(self, night: Path, slot: Slot, *, code: str | None, polls: int, phase: str | None = None) -> None:
        self.night, self.slot, self.code, self.polls, self.phase = night, slot, code, polls, phase
        self.exit: int | None = None
        self.signals: list[str] = []

    def _write(self) -> None:
        if self.code is None:
            return
        slot_path(self.night, self.slot).write_text(json.dumps({
            "slot": self.slot.index, "arm": self.slot.arm, "attempt_dir": f"t-{self.slot.index}",
            "code": self.code, "verdict": "pass" if self.code == "OK" else None, "message": f"attempt {self.code}",
            "deadline_phase": self.phase,
        }))

    def poll(self) -> int | None:
        if self.exit is None:
            self.polls -= 1
            if self.polls <= 0:
                self._write()
                self.exit = 0 if self.code is not None else 1
        return self.exit

    def terminate(self) -> None:
        self.signals.append("TERM")
        self.exit = 143

    def kill(self) -> None:
        self.signals.append("KILL")
        self.exit = -9


class Spawner:
    def __init__(self, night: Path, clock: Clock, codes: dict[int, str | None] | None = None, polls: int = 3) -> None:
        self.night, self.clock, self.codes, self.polls = night, clock, codes or {}, polls
        self.started: list[tuple[float, Slot]] = []
        self.cells: dict[int, FakeCell] = {}
        self.max_running = 0

    def __call__(self, slot: Slot) -> FakeCell:
        self.started.append((self.clock.now, slot))
        cell = FakeCell(self.night, slot, code=self.codes.get(slot.index, "OK"), polls=self.polls)
        self.cells[slot.index] = cell
        running = sum(1 for c in self.cells.values() if c.exit is None)
        self.max_running = max(self.max_running, running)
        return cell


def _launch(night: Path, spawner: Spawner, clock: Clock, **over: object):
    kwargs: dict[str, object] = dict(
        night=night, arms=("baseline", "engine"), n=2, k=2, max_seconds=3600, cell_seconds=100,
        spawn=spawner, drift=lambda: None, clock=clock, sleep=clock.sleep, poll_interval=1.0, grace=5.0,
    )
    return launch_cells(**{**kwargs, **over})


def test_slots_alternate_the_arms_in_record_order() -> None:
    assert [(s.index, s.arm) for s in plan_slots(("baseline", "engine"), 2)] == [
        (0, "baseline"), (1, "engine"), (2, "baseline"), (3, "engine"),
    ]
    assert [s.arm for s in plan_slots(("baseline",), 3)] == ["baseline"] * 3


def test_a_record_completes_k_at_a_time_in_slot_order(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock)
    outcome = _launch(tmp_path, spawner, clock)
    assert (outcome.status, outcome.reason) == (Status.COMPLETE, None)
    assert [slot.index for _, slot in spawner.started] == [0, 1, 2, 3]
    assert spawner.max_running == 2
    assert sorted(read_slots(tmp_path)) == [0, 1, 2, 3]
    assert [r["slot"] for r in outcome.finished] == [0, 1, 2, 3]


def test_k_one_runs_one_cell_at_a_time(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock)
    assert _launch(tmp_path, spawner, clock, k=1).status is Status.COMPLETE
    assert spawner.max_running == 1


@pytest.mark.parametrize("code", ["NO_PATCH", "COMMAND_TIMEOUT", "BUDGET_EXCEEDED", "REPEAT_LIMIT", "OK"])
def test_a_model_outcome_never_stops_the_night(tmp_path: Path, code: str) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, codes={0: code, 1: code})
    assert _launch(tmp_path, spawner, clock).status is Status.COMPLETE
    assert len(spawner.started) == 4


@pytest.mark.parametrize("code", ["MODEL_ERROR", "WORKSPACE_FAILED", "CLEANUP_FAILED", "GRADE_FAILED", "TRANSCRIPT_EMPTY"])
def test_an_infrastructure_outcome_stops_the_night_and_lets_running_cells_finish(tmp_path: Path, code: str) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, codes={0: code})
    outcome = _launch(tmp_path, spawner, clock)
    assert outcome.status is Status.INFRASTRUCTURE
    assert outcome.reason == f"slot 00 (baseline): {code}: attempt {code}"
    assert [slot.index for _, slot in spawner.started] == [0, 1]
    assert sorted(read_slots(tmp_path)) == [0, 1]  # slot 1 was running and finished


def test_a_deadline_outside_the_command_is_infrastructure_and_inside_it_is_not() -> None:
    base = {"slot": 3, "arm": "engine", "code": "DEADLINE_EXCEEDED", "message": "m"}
    assert infrastructure_reason({**base, "deadline_phase": "command"}) is None
    assert infrastructure_reason({**base, "deadline_phase": "grading"}) == "slot 03 (engine): DEADLINE_EXCEEDED in grading: m"


def test_a_cell_process_that_exits_without_a_record_stops_the_night(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, codes={1: None})
    outcome = _launch(tmp_path, spawner, clock)
    assert outcome.status is Status.INFRASTRUCTURE
    assert outcome.reason == (
        "slot 01 (engine): the cell process exited 1 without an attempt record; "
        f"see {tmp_path / SLOTS_DIR / '01.log'}"
    )


def test_drift_before_a_cell_stops_the_night(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock)
    answers = iter([None, None, "task_tree_sha256 drifted"])
    outcome = _launch(tmp_path, spawner, clock, drift=lambda: next(answers, None))
    assert (outcome.status, outcome.reason) == (Status.INFRASTRUCTURE, "preflight drift: task_tree_sha256 drifted")
    assert len(spawner.started) == 2


def test_the_wall_clock_stops_new_cells_and_a_second_launch_resumes_without_rerunning(tmp_path: Path) -> None:
    clock = Clock()
    first = Spawner(tmp_path, clock, polls=70)
    outcome = _launch(tmp_path, first, clock, k=1, max_seconds=160, cell_seconds=100)
    assert outcome.status is Status.CAPPED and "3 slot(s) wait" in (outcome.reason or "")
    assert [slot.index for _, slot in first.started] == [0]
    before = slot_path(tmp_path, Slot(0, "baseline")).read_text()
    clock2 = Clock()
    second = Spawner(tmp_path, clock2)
    assert _launch(tmp_path, second, clock2, k=1).status is Status.COMPLETE
    assert [slot.index for _, slot in second.started] == [1, 2, 3]
    assert slot_path(tmp_path, Slot(0, "baseline")).read_text() == before


def test_a_finished_infrastructure_slot_is_replaced_on_the_next_launch(tmp_path: Path) -> None:
    clock = Clock()
    assert _launch(tmp_path, Spawner(tmp_path, clock, codes={0: "MODEL_ERROR"}), clock, k=1).status is Status.INFRASTRUCTURE
    clock2 = Clock()
    second = Spawner(tmp_path, clock2)
    outcome = _launch(tmp_path, second, clock2, k=1)
    assert outcome.status is Status.COMPLETE
    assert [slot.index for _, slot in second.started] == [0, 1, 2, 3]
    assert [r["code"] for r in outcome.replaced] == ["MODEL_ERROR"]
    assert outcome.replaced[0]["replaced_because"].startswith("slot 00 (baseline): MODEL_ERROR")
    assert (tmp_path / SLOTS_DIR / "00.replaced-1.json").is_file()
    assert read_slots(tmp_path)[0]["code"] == "OK"


@pytest.mark.parametrize("error", [SignalAbort(signal.SIGTERM), KeyboardInterrupt()])
def test_a_signal_stops_every_running_cell_and_reports_interrupted(tmp_path: Path, error: BaseException) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, polls=1000)
    calls = {"n": 0}

    def sleep(seconds: float) -> None:
        calls["n"] += 1
        if calls["n"] == 3:
            raise error
        clock.sleep(seconds)

    outcome = _launch(tmp_path, spawner, clock, sleep=sleep)
    assert outcome.status is Status.INTERRUPTED and type(error).__name__ in (outcome.reason or "")
    assert [cell.signals for cell in spawner.cells.values()] == [["TERM"], ["TERM"]]
    assert read_slots(tmp_path) == {}


def test_a_cell_that_ignores_sigterm_is_killed_after_the_grace(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, polls=1000)

    class Stubborn(FakeCell):
        def terminate(self) -> None:
            self.signals.append("TERM")

    def spawn(slot: Slot) -> FakeCell:
        cell = Stubborn(tmp_path, slot, code="OK", polls=1000)
        spawner.cells[slot.index] = cell
        return cell

    raised = []

    def sleep(seconds: float) -> None:
        if clock.now >= 2 and not raised:
            raised.append(True)
            raise KeyboardInterrupt
        clock.sleep(seconds)

    outcome = launch_cells(
        night=tmp_path, arms=("baseline",), n=1, k=1, max_seconds=3600, cell_seconds=10, spawn=spawn,
        drift=lambda: None, clock=clock, sleep=sleep, poll_interval=1.0, grace=0.3,
    )
    assert outcome.status is Status.INTERRUPTED
    assert spawner.cells[0].signals == ["TERM", "KILL"]


def test_a_second_signal_during_the_stop_grace_does_not_escape(tmp_path: Path) -> None:
    """A repeat Ctrl-C/SIGTERM while waiting out the grace must not escape ``launch_cells``:
    cells run in their own sessions, so an escape here would orphan a stubborn cell holding
    the GPU with no ledger ever written. The loop keeps waiting out the grace, then kills."""
    clock = Clock()
    spawner = Spawner(tmp_path, clock, polls=1000)

    class Stubborn(FakeCell):
        def terminate(self) -> None:
            self.signals.append("TERM")

    def spawn(slot: Slot) -> FakeCell:
        cell = Stubborn(tmp_path, slot, code="OK", polls=1000)
        spawner.cells[slot.index] = cell
        return cell

    calls = {"n": 0}

    def sleep(seconds: float) -> None:
        calls["n"] += 1
        if calls["n"] == 3:
            raise KeyboardInterrupt
        if calls["n"] == 5:
            raise SignalAbort(signal.SIGTERM)
        clock.sleep(seconds)

    outcome = launch_cells(
        night=tmp_path, arms=("baseline",), n=1, k=1, max_seconds=3600, cell_seconds=10, spawn=spawn,
        drift=lambda: None, clock=clock, sleep=sleep, poll_interval=1.0, grace=0.3,
    )
    assert outcome.status is Status.INTERRUPTED
    assert spawner.cells[0].signals == ["TERM", "KILL"]


def test_the_ledger_keeps_every_sitting_and_refuses_another_record(tmp_path: Path) -> None:
    identity = {"record": "records/a.json", "record_sha256": "1" * 64}
    clock = Clock()
    capped = _launch(tmp_path, Spawner(tmp_path, clock, polls=70), clock, k=1, max_seconds=160)
    write_ledger(tmp_path, identity=identity, sitting={"started": "s1", "k": 1}, outcome=capped)
    clock2 = Clock()
    done = _launch(tmp_path, Spawner(tmp_path, clock2), clock2, k=1)
    check_night(tmp_path, identity)
    write_ledger(tmp_path, identity=identity, sitting={"started": "s2", "k": 1}, outcome=done)
    ledger = json.loads((tmp_path / LEDGER_NAME).read_text())
    assert [s["status"] for s in ledger["sittings"]] == ["capped", "complete"]
    assert ledger["status"] == "complete" and [s["slot"] for s in ledger["slots"]] == [0, 1, 2, 3]
    with pytest.raises(UsageError, match="belongs to another record"):
        check_night(tmp_path, {**identity, "record_sha256": "2" * 64})


def test_the_ledger_refuses_a_resume_when_the_arm_digest_changed(tmp_path: Path) -> None:
    """The 2026-09-18 harness finding: the launcher resumed a completed night and
    reported complete while the arm had been re-pinned underneath it. The arm file's
    bytes are part of the night's identity, so a changed arm refuses the resume."""
    identity = {"record_sha256": "1" * 64, "arm_sha256": {"engine": "a" * 64}}
    clock = Clock()
    done = _launch(tmp_path, Spawner(tmp_path, clock), clock, k=2)
    write_ledger(tmp_path, identity=identity, sitting={"started": "s1", "k": 2}, outcome=done)
    check_night(tmp_path, identity)
    with pytest.raises(UsageError, match="arm_sha256"):
        check_night(tmp_path, {**identity, "arm_sha256": {"engine": "b" * 64}})


def test_a_resume_that_runs_no_cell_appends_no_sitting(tmp_path: Path) -> None:
    """A re-run whose slots are all finished runs zero cells; it must not append a
    sitting, or a no-op resume reads as a new launch and can hide a mixed-arm one."""
    identity = {"record_sha256": "1" * 64, "arm_sha256": {"engine": "a" * 64}}
    clock = Clock()
    done = _launch(tmp_path, Spawner(tmp_path, clock), clock, k=2)
    write_ledger(tmp_path, identity=identity, sitting={"started": "s1", "k": 2}, outcome=done)
    noop = _launch(tmp_path, Spawner(tmp_path, clock), clock, k=2)
    assert noop.finished == [] and noop.replaced == []
    write_ledger(tmp_path, identity=identity, sitting={"started": "s2", "k": 2}, outcome=noop)
    ledger = json.loads((tmp_path / LEDGER_NAME).read_text())
    assert [s["started"] for s in ledger["sittings"]] == ["s1"]
