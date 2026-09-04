"""The adapter process: spawn once, line deadlines, group teardown.

The adapter is started once per session in the detached worktree and
owns one conversation (2026-09-01 spec). Evals owns the lifecycle: raw
lines are returned unparsed so the executor can spool them before any
interpretation, and teardown escalates SIGTERM to SIGKILL across the
whole process group, confirming reap before returning.
"""

import contextlib
import os
import select
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from satyrn_evals.errors import SatyrnError


class AdapterTimeout(SatyrnError):
    """A deadline passed while waiting for the adapter."""


class AdapterCleanupError(SatyrnError):
    """The adapter process group could not be confirmed reaped."""


def _raise_closed_channel(exc: BrokenPipeError) -> None:
    """Raise the broken channel's exception here, so the exit arc is
    attributed in-process rather than during the session's unwinding."""
    raise SatyrnError(f"adapter closed stdin: {exc}") from exc


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
        env: Mapping[str, str] | None = None,
    ) -> AdapterProcess:
        # The child's environment must be the session's cleaned Git
        # environment (V4's own-git-op discipline), never the raw caller
        # environment: a GIT_DIR/GIT_WORK_TREE/GIT_OBJECT_DIRECTORY in
        # the surrounding process could redirect the model's Git
        # operations outside the detached workspace.
        if stderr_path is None:
            proc = subprocess.Popen(
                list(argv),
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        else:
            with open(stderr_path, "wb") as handle:
                # the child keeps its own descriptor; the parent need not
                proc = subprocess.Popen(
                    list(argv),
                    cwd=cwd,
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=handle,
                    start_new_session=True,
                )
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
            _raise_closed_channel(e)

    def close_stdin(self) -> None:
        if self._proc.stdin is not None:
            self._proc.stdin.close()

    def _signal_group(self, sig: int) -> None:
        os.killpg(os.getpgid(self._proc.pid), sig)

    def terminate_and_reap(self, timeout: float) -> None:
        """SIGTERM the group, escalate to SIGKILL, confirm reap."""
        with contextlib.suppress(ProcessLookupError):
            self._signal_group(signal.SIGTERM)
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                self._signal_group(signal.SIGKILL)
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

    def wait(self, timeout: float) -> int | None:
        """Reap the adapter; None if it did not exit within the timeout."""
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        return self._proc.returncode

    def returncode(self) -> int | None:
        return self._proc.returncode
