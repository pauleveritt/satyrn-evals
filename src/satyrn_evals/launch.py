"""The launcher's cell loop: a record's cells, k at a time, arms alternating, one ledger per night.

``satyrn-evals launch RECORD`` is the only path to a model (spec, "Process").
The gates are the CLI's; this module is what happens after them:

- **Slots.** A record asks n cells per arm. Slot i runs arm
  ``arms[i % len(arms)]``: strict alternation in start order, so a night
  stopped at any point leaves each arm's started cells at most one apart.
  Concurrency is rolling: a free place is filled as soon as any cell exits,
  so which arms are running together at any instant is not fixed by k
  (Ruling 4).
- **k at a time.** A slot starts when fewer than k run, no stop is pending,
  the drift probe is silent, and the cell's whole deadline still fits the
  record's wall clock. Otherwise nothing new starts and the running cells
  finish.
- **Each cell is its own process** (``launch_cell``), writing
  ``slots/NN.json`` when its attempt returns a record. A slot with that file
  is finished and never runs again (resume).
- **Stops.** An infrastructure outcome (``INFRASTRUCTURE_CODES``; a deadline
  outside the command phase; a cell process that exits without a record) or
  a drift stops the loop and is recorded; a model outcome never does. A
  finished infrastructure slot is replaced on the next launch: its record
  moves to ``slots/NN.replaced-M.json`` and the ledger lists it (spec,
  "Denominators": only an established infrastructure failure replaces a cell).
- **Signals.** SIGTERM and SIGHUP raise ``SignalAbort`` (``run._abort_on_signals``)
  and SIGINT raises ``KeyboardInterrupt``: every running cell is sent SIGTERM,
  given ``grace`` seconds to tear its model down, then killed; the outcome says
  ``interrupted`` and the caller writes the ledger and exits (an interrupted
  slot has no record and runs again on the next launch). Cells run in their
  own sessions, so a second signal during that grace must not escape and
  orphan them holding the GPU: the stopping phase runs under its own signal
  guard and swallows a repeated ``SignalAbort``/``KeyboardInterrupt``,
  simply continuing to wait out the grace before killing whatever still runs.

Nothing here spawns: the caller passes ``spawn`` and ``drift``. The default
tier drives the loop with fakes; ``launch_cell.popen_cell`` is the real spawn.
"""

import contextlib
import json
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.errors import UsageError
from satyrn_evals.run import _abort_on_signals

LEDGER_NAME = "launch.json"
SLOTS_DIR = "slots"
#: Outcomes that measured nothing about the model: they stop the night (Ruling 5).
INFRASTRUCTURE_CODES = frozenset({
    AttemptCode.WORKSPACE_FAILED, AttemptCode.CLEANUP_FAILED, AttemptCode.GRADE_FAILED,
    AttemptCode.TRANSCRIPT_MISSING, AttemptCode.TRANSCRIPT_EMPTY, AttemptCode.MODEL_ERROR,
    AttemptCode.PATCH_INVALID,
})
_SLOT_FILE = re.compile(r"^(\d{2})\.json$")


class Status(StrEnum):
    COMPLETE = "complete"
    CAPPED = "capped"
    INFRASTRUCTURE = "infrastructure"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class Slot:
    index: int
    arm: str

    @property
    def name(self) -> str:
        return f"{self.index:02d}"


class CellProcess(Protocol):
    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...


type Spawn = Callable[[Slot], CellProcess]
type Drift = Callable[[], str | None]


@dataclass(slots=True)
class LaunchOutcome:
    status: Status
    reason: str | None
    finished: list[dict] = field(default_factory=list)
    replaced: list[dict] = field(default_factory=list)


def plan_slots(arms: Sequence[str], n: int) -> list[Slot]:
    """n slots per arm, alternating in the record's order."""
    return [Slot(index, arms[index % len(arms)]) for index in range(n * len(arms))]


def slot_path(night: Path, slot: Slot) -> Path:
    return night / SLOTS_DIR / f"{slot.name}.json"


def infrastructure_reason(result: dict) -> str | None:
    """Why a finished slot measured nothing, or ``None`` for a model outcome."""
    code = AttemptCode(result["code"])
    where = f"slot {result['slot']:02d} ({result['arm']})"
    if code in INFRASTRUCTURE_CODES:
        return f"{where}: {code}: {result['message']}"
    if code is AttemptCode.DEADLINE_EXCEEDED and result.get("deadline_phase") != "command":
        return f"{where}: {code} in {result.get('deadline_phase')}: {result['message']}"
    return None


def read_slots(night: Path) -> dict[int, dict]:
    """Every finished slot's result, by index (replaced results are not finished)."""
    directory = night / SLOTS_DIR
    if not directory.is_dir():
        return {}
    found: dict[int, dict] = {}
    for path in sorted(directory.iterdir()):
        if match := _SLOT_FILE.match(path.name):
            found[int(match.group(1))] = json.loads(path.read_text(encoding="utf-8"))
    return found


def _replace_infrastructure_slots(night: Path, finished: dict[int, dict]) -> list[dict]:
    """Move each finished infrastructure slot aside so the slot runs again; return what moved."""
    replaced: list[dict] = []
    for index, result in sorted(finished.items()):
        if (reason := infrastructure_reason(result)) is None:
            continue
        source = night / SLOTS_DIR / f"{index:02d}.json"
        count = len(list(source.parent.glob(f"{index:02d}.replaced-*.json")))
        source.rename(source.with_name(f"{index:02d}.replaced-{count + 1}.json"))
        replaced.append({**result, "replaced_because": reason})
        del finished[index]
    return replaced


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def write_ledger(night: Path, *, identity: dict, sitting: dict, outcome: LaunchOutcome) -> None:
    """Append this sitting to ``launch.json`` and restate the slots every sitting has finished."""
    path = night / LEDGER_NAME
    ledger = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {**identity, "sittings": [], "replaced": []}
    ledger["sittings"].append({**sitting, "ended": _now(), "status": outcome.status, "reason": outcome.reason})
    ledger["replaced"].extend(outcome.replaced)
    ledger["status"], ledger["reason"] = outcome.status, outcome.reason
    finished = read_slots(night)
    ledger["slots"] = [finished[index] for index in sorted(finished)]
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def check_night(night: Path, identity: dict) -> None:
    """Refuse a night directory that belongs to a different record (same stem, other bytes)."""
    path = night / LEDGER_NAME
    if not path.is_file():
        return
    ledger = json.loads(path.read_text(encoding="utf-8"))
    for key, value in identity.items():
        if ledger.get(key) != value:
            raise UsageError(f"{night} belongs to another record: its {key} is {ledger.get(key)!r}, not {value!r}")


def launch_cells(
    *,
    night: Path,
    arms: Sequence[str],
    n: int,
    k: int,
    max_seconds: float,
    cell_seconds: float,
    spawn: Spawn,
    drift: Drift,
    grace: float = 60.0,
    poll_interval: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> LaunchOutcome:
    """Run every unfinished slot; see the module docstring for the rules."""
    (night / SLOTS_DIR).mkdir(parents=True, exist_ok=True)
    finished = read_slots(night)
    outcome = LaunchOutcome(Status.COMPLETE, None, replaced=_replace_infrastructure_slots(night, finished))
    pending = [slot for slot in plan_slots(arms, n) if slot.index not in finished]
    running: dict[int, tuple[Slot, CellProcess]] = {}
    start = clock()
    capped = False
    try:
        with _abort_on_signals():
            while pending or running:
                for index, (slot, process) in list(running.items()):
                    if (exit_code := process.poll()) is None:
                        continue
                    del running[index]
                    reason = _finish(night, slot, exit_code, outcome)
                    if reason is not None and outcome.status is Status.COMPLETE:
                        outcome.status, outcome.reason = Status.INFRASTRUCTURE, reason
                stopping = outcome.status is not Status.COMPLETE or capped
                while not stopping and pending and len(running) < k:
                    if clock() - start + cell_seconds > max_seconds:
                        capped = stopping = True
                    elif (problem := drift()) is not None:
                        outcome.status, outcome.reason = Status.INFRASTRUCTURE, f"preflight drift: {problem}"
                        stopping = True
                    else:
                        slot = pending.pop(0)
                        running[slot.index] = (slot, spawn(slot))
                if not running and (stopping or not pending):
                    break
                sleep(poll_interval)
    except BaseException as exc:  # SignalAbort, KeyboardInterrupt, or a spawn that raised
        _stop_running(running, grace=grace, clock=clock, sleep=sleep, poll_interval=poll_interval)
        for slot, _ in running.values():
            if slot_path(night, slot).is_file():
                outcome.finished.append(json.loads(slot_path(night, slot).read_text(encoding="utf-8")))
        outcome.status, outcome.reason = Status.INTERRUPTED, f"{type(exc).__name__}: {exc}"
        return outcome
    if outcome.status is Status.COMPLETE and pending:
        outcome.status = Status.CAPPED
        outcome.reason = (
            f"the record's wall clock leaves no room for another {cell_seconds:g} s cell; "
            f"{len(pending)} slot(s) wait for the next launch of the same record"
        )
    return outcome


def _finish(night: Path, slot: Slot, exit_code: int, outcome: LaunchOutcome) -> str | None:
    """Collect one exited cell; the infrastructure reason it stops the night for, if any."""
    path = slot_path(night, slot)
    if not path.is_file():
        return f"slot {slot.name} ({slot.arm}): the cell process exited {exit_code} without an attempt record"
    result = json.loads(path.read_text(encoding="utf-8"))
    outcome.finished.append(result)
    return infrastructure_reason(result)


def _stop_running(
    running: dict[int, tuple[Slot, CellProcess]],
    *,
    grace: float,
    clock: Callable[[], float],
    sleep: Callable[[float], None],
    poll_interval: float,
) -> None:
    """SIGTERM every running cell, wait up to ``grace`` for its teardown, then kill what is left.

    Runs under its own signal guard: a second signal during the grace (another Ctrl-C, a repeat
    SIGTERM/SIGHUP) is swallowed here rather than left to escape ``launch_cells`` — cells run in
    their own sessions, so an escape would orphan them holding the GPU with no ledger written.
    """
    with _abort_on_signals():
        for _, process in running.values():
            process.terminate()
        stop = clock() + grace
        while any(process.poll() is None for _, process in running.values()) and clock() < stop:
            # a repeated SignalAbort/KeyboardInterrupt here must not escape: keep waiting out the grace
            with contextlib.suppress(BaseException):
                sleep(min(poll_interval, 0.1))
        for _, process in running.values():
            if process.poll() is None:
                process.kill()
