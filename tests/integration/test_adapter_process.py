"""The adapter process: line deadlines, EOF, and group teardown."""

import os
import signal
import subprocess
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
import os, signal, sys, time
signal.signal(signal.SIGTERM, lambda *a: None)
subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
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
    pgid = os.getpgid(proc._proc.pid)
    started = time.monotonic()
    try:
        proc.terminate_and_reap(5.0)
    except AdapterCleanupError:
        raise
    assert time.monotonic() - started < 5.0  # escalation happened, no full wait
    with pytest.raises(ProcessLookupError):
        os.killpg(pgid, 0)  # the whole group, grandchild included, is gone
