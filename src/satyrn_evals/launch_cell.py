"""One launcher cell in its own process: the attempt, then its slot record.

``launch_record`` writes ``slots/NN.spec.json`` and starts
``python -m satyrn_evals.launch_cell SPEC`` in its own session. The child runs
``attempt`` with the record's budget, rung and profile, and only when
``attempt`` returns a record writes ``slots/NN.json`` (atomically), the file
that makes the slot finished. SIGTERM and SIGHUP raise ``SignalAbort`` inside
the attempt, so the workspace's own teardown stops the model (the cell-side
kill included under isolation) before the process exits without a slot record.
"""

import contextlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptRecord
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.cell import Isolation
from satyrn_evals.errors import SatyrnError
from satyrn_evals.launch import write_atomically
from satyrn_evals.run import SignalAbort, _abort_on_signals

#: The spec's backstop on this machine ("Budget, both arms"): per attempt command, and the attempt deadline.
COMMAND_BACKSTOP = 1800.0
ATTEMPT_DEADLINE = 2100.0


def slot_result(*, slot: int, arm: str, record: AttemptRecord) -> dict[str, object]:
    """What the loop reads back about a finished slot."""
    return {
        "slot": slot,
        "arm": arm,
        "attempt_dir": record.attempt_dir,
        "code": record.code.value,
        "verdict": None if record.verdict is None else record.verdict.value,
        "message": record.message,
        "command_exit": record.command_exit,
        "deadline_phase": None if record.deadline is None else record.deadline.phase.value,
    }


def run_cell(spec: dict) -> int:
    with _abort_on_signals():
        record = attempt(
            task=spec["task"],
            tasks_root=Path(spec["tasks_root"]),
            output=Path(spec["output"]),
            command=list(spec["command"]),
            timeout=spec["timeout"],
            attempt_timeout=spec["attempt_timeout"],
            rung=spec["rung"],
            budget=AttemptBudget(output_tokens=spec["token_budget"], turns=spec["turn_budget"]),
            isolation=Isolation(spec["isolation"]),
        )
    write_atomically(Path(spec["result"]), slot_result(slot=spec["slot"], arm=spec["arm"], record=record))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        return run_cell(json.loads(Path(args[0]).read_text(encoding="utf-8")))
    except SignalAbort as stop:
        print(f"launch_cell: stopped by {stop}", file=sys.stderr)
        return 128 + stop.signum
    except KeyboardInterrupt:
        print("launch_cell: stopped by SIGINT", file=sys.stderr)
        return 128 + signal.SIGINT
    except SatyrnError as error:
        print(f"launch_cell: {error}", file=sys.stderr)
        return error.exit_code


class PopenCell:
    """A running cell process: its own session, SIGTERM for teardown, SIGKILL to its group as a last resort."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process

    def poll(self) -> int | None:
        return self.process.poll()

    def terminate(self) -> None:
        with contextlib.suppress(ProcessLookupError):
            self.process.send_signal(signal.SIGTERM)

    def kill(self) -> None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(self.process.pid, signal.SIGKILL)
        self.process.wait()


def popen_cell(spec_path: Path, log_path: Path) -> PopenCell:
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "satyrn_evals.launch_cell", os.fspath(spec_path)],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    return PopenCell(process)


if __name__ == "__main__":
    sys.exit(main())
