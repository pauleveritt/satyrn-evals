"""The adapter process: spawn once, line deadlines, group teardown.

The adapter is started once per session in the detached worktree and
owns one conversation (2026-09-01 spec). Evals owns the lifecycle: raw
lines are returned unparsed so the executor can spool them before any
interpretation, and teardown escalates SIGTERM to SIGKILL across the
whole process group, confirming reap before returning.
"""

import os
import select
from collections.abc import Sequence
import signal
import subprocess
import time
from pathlib import Path
from typing import IO

from satyrn_evals.errors import SatyrnError


class AdapterTimeout(SatyrnError):
    """A deadline passed while waiting for the adapter."""


class AdapterCleanupError(SatyrnError):
    """The adapter process group could not be confirmed reaped."""


class AdapterProcess:
    """One live adapter subprocess and its process group."""

    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        self._proc = proc
        self._buf = b""
        assert proc.stdin is not None and proc.stdout is not None

    @classmethod
    def start(
        cls,
        argv: Sequence[str],
        cwd: Path,
        *,
        stderr_path: Path | None = None,
    ) -> "AdapterProcess":
        stderr: IO[bytes] | int
        handle = None
        if stderr_path is None:
            stderr = subprocess.DEVNULL
        else:
            handle = open(stderr_path, "wb")
            stderr = handle  # type: ignore[assignment]
        try:
            proc = subprocess.Popen(
                list(argv),
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr,
                start_new_session=True,
            )
        finally:
            if handle is not None:
                handle.close()
        return cls(proc)

    def read_line(self, timeout: float) -> str | None:
        """One raw line without its newline; None at EOF; AdapterTimeout on deadline."""
        deadline = time.monotonic() + timeout
        while b"\n" not in self._buf:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AdapterTimeout("adapter line deadline passed")
            ready, _, _ = select.select([self._proc.stdout], [], [], remaining)
            if not ready:
                continue
            assert self._proc.stdout is not None
            chunk = os.read(self._proc.stdout.fileno(), 65536)
            if not chunk:
                if not self._buf:
                    return None
                line, self._buf = self._buf, b""
                return line.decode("utf-8", "surrogateescape")
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\n")
        return line.decode("utf-8", "surrogateescape")

    def send_line(self, line: str) -> None:
        assert self._proc.stdin is not None
        try:
            self._proc.stdin.write(line.encode("utf-8"))
            self._proc.stdin.flush()
        except BrokenPipeError as e:
            raise SatyrnError(f"adapter closed stdin: {e}") from e

    def close_stdin(self) -> None:
        if self._proc.stdin is not None:
            self._proc.stdin.close()

    def _signal_group(self, sig: int) -> None:
        os.killpg(os.getpgid(self._proc.pid), sig)

    def terminate_and_reap(self, timeout: float) -> None:
        """SIGTERM the group, escalate to SIGKILL, confirm reap."""
        try:
            self._signal_group(signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                self._signal_group(signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                self._proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired as e:
                raise AdapterCleanupError(
                    f"adapter process group did not reap: pid {self._proc.pid}"
                ) from e
        deadline = time.monotonic() + timeout
        while True:
            try:
                os.killpg(os.getpgid(self._proc.pid), 0)
            except ProcessLookupError:
                break
            if time.monotonic() > deadline:
                raise AdapterCleanupError(
                    f"adapter group still present after reap: pid {self._proc.pid}"
                )
            time.sleep(0.01)

    def returncode(self) -> int | None:
        return self._proc.returncode
