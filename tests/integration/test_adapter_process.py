"""The adapter process: line deadlines, EOF, and group teardown."""

import contextlib
import os
import sys
import time
from pathlib import Path

import pytest

from satyrn_evals.adapter_process import (
    AdapterCleanupError,
    AdapterProcess,
    AdapterTimeout,
)

pytestmark = pytest.mark.integration

ECHO_SCRIPT = """
import sys
print("banner", flush=True)
for line in sys.stdin:
    print(line.rstrip("\\n"), flush=True)
"""

HANG_SCRIPT = """
import json, os, signal, subprocess, sys, time
signal.signal(signal.SIGTERM, lambda *a: None)  # installed before "ready"
subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
print(json.dumps({"ready": True}), flush=True)
time.sleep(60)
"""

PARTIAL_SCRIPT = 'import sys; sys.stdout.write("partial"); sys.stdout.flush()'


def _start(script: str, tmp_path: Path) -> AdapterProcess:
    script_path = tmp_path / "adapter.py"
    script_path.write_text(script)
    return AdapterProcess.start([sys.executable, str(script_path)], tmp_path)


def test_banner_then_echo_round_trip(tmp_path: Path) -> None:
    proc = _start(ECHO_SCRIPT, tmp_path)
    try:
        assert proc.read_line(5.0) == "banner"
        proc.send_line('{"ping": true}\n')
        assert proc.read_line(5.0) == '{"ping": true}'
    finally:
        proc.terminate_and_reap(5.0)
    assert proc.returncode() is not None


def test_read_line_times_out_on_a_silent_adapter(tmp_path: Path) -> None:
    proc = _start("import time; time.sleep(30)", tmp_path)
    try:
        with pytest.raises(AdapterTimeout):
            proc.read_line(0.2)
    finally:
        proc.terminate_and_reap(5.0)


def test_read_line_returns_none_at_eof(tmp_path: Path) -> None:
    proc = _start("print('bye', flush=True)", tmp_path)
    try:
        assert proc.read_line(5.0) == "bye"
        assert proc.read_line(5.0) is None
    finally:
        proc.terminate_and_reap(5.0)


def test_partial_line_is_returned_before_eof(tmp_path: Path) -> None:
    proc = _start(PARTIAL_SCRIPT, tmp_path)
    try:
        assert proc.read_line(5.0) == "partial"
        assert proc.read_line(5.0) is None
    finally:
        proc.terminate_and_reap(5.0)


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX-only")
def test_terminate_escapes_a_term_ignoring_group(tmp_path: Path) -> None:
    proc = _start(HANG_SCRIPT, tmp_path)
    assert proc.read_line(5.0) == '{"ready": true}'  # handler installed
    pgid = os.getpgid(proc._proc.pid)
    started = time.monotonic()
    try:
        proc.terminate_and_reap(5.0)
    except AdapterCleanupError:
        raise
    assert 4.0 < time.monotonic() - started < 6.0  # TERM ignored; KILL escalated
    with pytest.raises(ProcessLookupError):
        os.killpg(pgid, 0)  # the whole group, grandchild included, is gone


def test_wait_returns_none_on_timeout(tmp_path: Path) -> None:
    proc = _start("import time; time.sleep(30)", tmp_path)
    try:
        assert proc.wait(0.2) is None
    finally:
        proc.terminate_and_reap(5.0)


def test_reap_reports_an_unreapable_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SIGKILL cannot be ignored on POSIX, so the still-present arm is
    exercised by faking the group check to persist past the deadline."""
    proc = _start(HANG_SCRIPT, tmp_path)

    real_killpg = os.killpg
    pgid = os.getpgid(proc._proc.pid)

    def fake_killpg(pgid_arg: int, sig: int) -> None:
        if sig == 0 and pgid_arg == pgid:
            return  # the group pretends to survive every confirmation
        real_killpg(pgid_arg, sig)

    monkeypatch.setattr(os, "killpg", fake_killpg)
    monkeypatch.setattr(os, "getpgid", lambda pid: pgid)
    try:
        with pytest.raises(AdapterCleanupError, match="still present after reap"):
            proc.terminate_and_reap(0.5)
    finally:
        monkeypatch.undo()
        with contextlib.suppress(ProcessLookupError):
            real_killpg(pgid, 9)  # already reaped by the escalation


def test_reap_raises_when_sigkill_cannot_reap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The child that survives SIGKILL is impossible on POSIX; the
    defensive arm is exercised with a fake process whose wait always
    times out."""
    import subprocess as _subprocess

    class _Unreapable:
        pid = 0

        def wait(self, timeout: float) -> int:
            raise _subprocess.TimeoutExpired(cmd="pi", timeout=timeout)

    proc = object.__new__(AdapterProcess)
    proc._buf = b""
    proc._proc = _Unreapable()  # type: ignore[bad-assignment]  # deliberate reap-refusal fake
    monkeypatch.setattr(proc, "_signal_group", lambda sig: None)
    with pytest.raises(AdapterCleanupError, match="did not reap"):
        proc.terminate_and_reap(0.1)
