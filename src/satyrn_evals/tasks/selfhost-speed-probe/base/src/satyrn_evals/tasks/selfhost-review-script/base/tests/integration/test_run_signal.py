"""V11d F3: what a signal-killed ``run`` leaves behind.

``run.py``'s abort path is an ``except BaseException`` around the cell
loop, and a ``UsageError`` demonstrably reaches it — the aborted Engine
smoke of 2026-09-05 recorded ``completed: 0`` and its cause. A signal is
the open question: the interrupted ``misleading-locus`` batch left three
cell directories, no ``summary.json`` and **no** ``aborted.json``.

These tests send a real signal to a real ``run`` process, so they spawn
subprocesses and are integration-tier by construction. The planted-spawn
tripwire is untouched; the ``integration`` marker is what opens the gate
(``tests/conftest.py``).
"""

import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.summary import ABORTED_NAME, SUMMARY_NAME

pytestmark = pytest.mark.integration

SLOW = Path(__file__).parent / "fake_attempt_slow.py"
KNOWN_GOOD = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"
TASK = "format_number"


_ENTRY = "import sys; from satyrn_evals.cli import main; sys.exit(main())"


def _spawn_run(
    output: Path, started: Path, *, n: int, fast_after: int
) -> subprocess.Popen:
    """A live ``satyrn-evals run`` in its own process group.

    Its own group so the test can reap the blocked child adapter without
    depending on the run process to do it.
    """
    argv = [
        sys.executable, "-c", _ENTRY, "run", TASK,
        "--n", str(n),
        "--output", str(output),
        "--tasks-root", str(DEFAULT_TASKS_ROOT),
        "--",
        sys.executable, str(SLOW),
        "--patch", str(KNOWN_GOOD),
        "--started", str(started),
        "--fast-after", str(fast_after),
    ]
    return subprocess.Popen(argv, start_new_session=True)


def _wait_for_sentinels(started: Path, count: int, *, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if started.is_dir() and len(list(started.glob("*.started"))) >= count:
            return
        time.sleep(0.05)
    raise AssertionError(f"no {count} started sentinels within {timeout}s")


def _reap(proc: subprocess.Popen) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=30)


def _cell_dirs(output: Path) -> list[Path]:
    return sorted(p for p in output.iterdir() if p.is_dir())


@pytest.mark.parametrize(
    "sig", [signal.SIGTERM, signal.SIGHUP], ids=["SIGTERM", "SIGHUP"]
)
def test_a_terminating_signal_mid_cell_leaves_an_abort_record(
    tmp_path: Path, sig: signal.Signals
) -> None:
    """Acceptance (V11d slice 2): a signal arriving mid-cell leaves an
    abort record naming the signal, the completed cells stay readable,
    and the incomplete cell is distinguishable from a completed one.

    The first cell runs to completion (``--fast-after 1``); the second
    blocks, and that is when the signal lands. SIGHUP rides along because
    the batch that produced this finding was interrupted, and a closed
    terminal delivers SIGHUP rather than SIGTERM -- neither default
    disposition gives Python a chance to raise.
    """
    output = tmp_path / "runs"
    started = tmp_path / "started"
    proc = _spawn_run(output, started, n=3, fast_after=1)
    try:
        _wait_for_sentinels(started, 2)  # cell 1 done, cell 2 in flight
        proc.send_signal(sig)
        proc.wait(timeout=30)
    finally:
        _reap(proc)

    assert not (output / SUMMARY_NAME).exists(), "an aborted batch is not complete"
    aborted = output / ABORTED_NAME
    assert aborted.exists(), "a signal-killed run wrote no abort record"
    marker = json.loads(aborted.read_text(encoding="utf-8"))
    assert marker["requested"] == 3
    assert marker["completed"] == 1
    assert sig.name in marker["error"], marker["error"]

    dirs = _cell_dirs(output)
    assert len(dirs) == 2, dirs
    completed, incomplete = dirs
    assert (completed / "attempt.json").is_file()
    assert not (incomplete / "attempt.json").exists()


def test_a_clean_run_writes_a_summary_and_no_abort_record(tmp_path: Path) -> None:
    """The sibling of the pin above, through the same live-process path:
    an uninterrupted run writes ``summary.json`` and no abort record, so
    the abort record above is evidence of the signal and not of the way
    these tests drive ``run``."""
    output = tmp_path / "runs"
    started = tmp_path / "started"
    proc = _spawn_run(output, started, n=2, fast_after=99)
    try:
        assert proc.wait(timeout=120) == 0
    finally:
        _reap(proc)

    assert (output / SUMMARY_NAME).is_file()
    assert not (output / ABORTED_NAME).exists()
    assert len(_cell_dirs(output)) == 2
