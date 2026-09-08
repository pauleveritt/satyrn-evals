"""The Pi adapter's driver loop, verifiable in process.

The adapter child cannot be measured by the coverage gate's subprocess
patch (verified: COVERAGE_PROCESS_START never reaches it), so the driver
runs in-process against pipe-backed fakes: real os.pipes, no spawned
process. The four-prompt integration test separately proves the real
executable seam; this module proves every driver branch.
"""

import json
import os
import select
import threading
import time
from types import SimpleNamespace
from typing import BinaryIO, Literal, TextIO, overload

import pytest

from satyrn_evals.adapters import pi_session
from satyrn_evals.adapters.pi_session import main


class _PipePair:
    def __init__(self) -> None:
        self._r, self._w = os.pipe()

    @property
    def read_fd(self) -> int:
        return self._r

    def reader(self):
        return os.fdopen(self._r, "r", encoding="utf-8")

    @overload
    def writer(self, binary: Literal[True]) -> BinaryIO: ...

    @overload
    def writer(self, binary: Literal[False] = False) -> TextIO: ...

    def writer(self, binary: bool = False) -> TextIO | BinaryIO:
        if binary:
            return os.fdopen(self._w, "wb")
        return os.fdopen(self._w, "w", encoding="utf-8")

    def write(self, text: str) -> None:
        os.write(self._w, text.encode("utf-8"))

    def drain(self, seconds: float = 2.0) -> list[dict]:
        lines: list[dict] = []
        while True:
            ready, _, _ = select.select([self._r], [], [], seconds)
            if not ready:
                return lines
            data = os.read(self._r, 65536)
            if not data:
                return lines
            lines.extend(
                json.loads(line)
                for line in data.decode("utf-8", "surrogateescape").splitlines()
                if line
            )

    def close_read(self) -> None:
        os.close(self._r)

    def close_write(self) -> None:
        os.close(self._w)


class _FakePi:
    """A pi child stand-in over real pipes; the test plays pi."""

    def __init__(self) -> None:
        self.driver_to_pi = _PipePair()  # driver writes; test reads
        self.pi_to_driver = _PipePair()  # test writes; driver reads
        self.stdin = self.driver_to_pi.writer(binary=True)
        self.stdout = self.pi_to_driver.reader()
        self.terminated = False
        self.killed = False
        self._wait_calls = 0
        self.exit_code = 0

    def say(self, obj: dict) -> None:
        self.pi_to_driver.write(json.dumps(obj) + "\n")

    def prompts(self) -> list[dict]:
        prompts: list[dict] = []
        while True:
            ready, _, _ = select.select([self.driver_to_pi.read_fd], [], [], 0.2)
            if not ready:
                return prompts
            raw = os.read(self.driver_to_pi.read_fd, 65536)
            prompts.extend(
                json.loads(line) for line in raw.decode().splitlines() if line
            )

    def poll(self) -> int | None:
        return None  # looks alive; wait() reports the exit

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float) -> int:
        self._wait_calls += 1
        if self.terminated and self._wait_calls == 1 and self.exit_code != 0:
            raise TimeoutError("stub")
        return self.exit_code

    exit_code = 0


def _prompt(step: str) -> str:
    return json.dumps({"version": 1, "type": "prompt", "step_id": step, "text": "go"}) + "\n"


def _start(conversation: str = "conv-test"):
    """Start _serve in a thread with pipe-backed streams and a fake pi."""
    driver_stdin = _PipePair()  # test writes; driver reads
    driver_stdout = _PipePair()  # driver writes; test reads
    fake_pi = _FakePi()
    errors: list[BaseException] = []

    def run() -> None:
        try:
            with driver_stdin.reader() as stdin, driver_stdout.writer() as stdout:
                pi_session._serve(
                    stdin, stdout, fake_pi,  # type: ignore[bad-argument-type]  # _FakePi duck-types the _PiHandle seam in-process
                    conversation_id="conv-test",
                )
        except BaseException as exc:  # surfaced to the test on join
            errors.append(exc)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return SimpleNamespace(
        stdin=driver_stdin,
        stdout=driver_stdout,
        pi=fake_pi,
        thread=thread,
        errors=errors,
        finish=lambda timeout: (
            driver_stdin.close_write() or thread.join(timeout),
        ),
    )


def test_settle_then_close_round_trip() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "turn_end"})
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    kinds = [(obj["type"], obj.get("kind")) for obj in lines]
    assert ("event", "turn_end") in kinds
    finished = [obj for obj in lines if obj["type"] == "step_finished"]
    assert finished[-1]["outcome"] == "settled"
    # pi received exactly one rpc prompt
    prompts = driver.pi.prompts()
    assert len(prompts) == 1 and prompts[0]["message"] == "go"
    # graceful close: serve returns
    driver.stdin.write(json.dumps({"version": 1, "type": "close"}) + "\n")
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.thread.is_alive()
    assert not driver.errors


def test_second_prompt_while_pending_is_skipped() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    first: list[dict] = []
    while not first:
        first = driver.pi.prompts()
    time.sleep(0.02)  # pending is now true: the refusal arm is next
    driver.stdin.write(_prompt("add-b"))  # while pending: refused
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    assert len([obj for obj in lines if obj["type"] == "step_finished"]) == 1
    assert len(first) == 1 and driver.pi.prompts() == []  # only a reached pi
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_malformed_pi_line_is_skipped() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    driver.pi.pi_to_driver.write("not json at all\n")
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    assert [obj for obj in lines if obj["type"] == "step_finished"]
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_failed_response_maps_agent_error_and_frees_the_prompt() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say(
        {"type": "response", "command": "prompt", "success": False, "error": "no"}
    )
    lines = driver.stdout.drain()
    finished = [obj for obj in lines if obj["type"] == "step_finished"]
    assert finished[-1]["outcome"] == "agent-error"
    # the adapter accepts the next prompt after the error terminal
    driver.stdin.write(_prompt("add-b"))
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    assert [obj for obj in lines if obj["type"] == "step_finished"]
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_retry_failure_tracks_agent_error() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "auto_retry_end", "success": False, "finalError": "boom"})
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    finished = [obj for obj in lines if obj["type"] == "step_finished"]
    assert finished[-1]["outcome"] == "agent-error"
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_agent_end_length_terminal_maps_output_limit() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "agent_end", "messages": [{"stopReason": "length"}]})
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    finished = [obj for obj in lines if obj["type"] == "step_finished"]
    assert finished[-1]["outcome"] == "output-limit"
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_pi_eof_mid_prompt_maps_agent_error() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    driver.pi.pi_to_driver.close_write()  # pi stdout EOF mid-prompt
    lines = driver.stdout.drain()
    finished = [obj for obj in lines if obj["type"] == "step_finished"]
    assert finished[-1]["outcome"] == "agent-error"
    assert "pi exited" in finished[-1]["message"]
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_unsolicited_pi_events_before_any_prompt_are_ignored() -> None:
    driver = _start()
    time.sleep(0.2)  # the driver is parked in select; the event is consumed idle
    driver.pi.say({"type": "queue_update"})
    time.sleep(0.2)
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    assert [obj for obj in lines if obj["type"] == "step_finished"]
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_main_shell_spawns_serves_and_reaps(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """main(): parse, spawn, banner, serve, reap — in process via fakes."""
    fake = _FakePi()

    class _FakePopen:
        def __init__(self, argv: list[str], **kw: object) -> None:
            assert "--mode" in argv and "rpc" in argv
            assert "--no-session" in argv
            assert not any(token.startswith("--model=") for token in argv)
            self.argv = argv
            self.stdin = fake.stdin
            self.stdout = fake.stdout

        def poll(self) -> int | None:
            return fake.poll()

        def terminate(self) -> None:
            fake.terminate()

        def kill(self) -> None:
            fake.kill()

        def wait(self, timeout: float) -> int:
            return fake.wait(timeout)

    monkeypatch.setattr(pi_session.subprocess, "Popen", _FakePopen)
    # pipe-backed stdin/stdout for the adapter process
    r_stdin, w_stdin = os.pipe()
    r_stdout, w_stdout = os.pipe()
    monkeypatch.setattr(
        pi_session.sys, "stdin", os.fdopen(r_stdin, "r", encoding="utf-8")
    )
    monkeypatch.setattr(
        pi_session.sys, "stdout", os.fdopen(w_stdout, "w", encoding="utf-8")
    )
    result: dict[str, object] = {}
    thread = threading.Thread(
        target=lambda: result.update(
            code=main(["--provider", "fake", "--model", "m", "--tools", "read"])
        ),
        daemon=True,
    )
    thread.start()
    # the banner arrives on the adapter stdout pipe
    banner = []
    while not banner:
        banner = [
            obj for obj in _drain_fd(r_stdout) if obj["type"] == "session_started"
        ]
    assert banner[0]["conversation_id"].startswith("pi-")
    # a prompt through the whole shell
    os.write(w_stdin, _prompt("add-a").encode())
    fake.pi_to_driver.write(json.dumps({"type": "agent_settled"}) + "\n")
    found: list[dict] = []
    while not found:
        found = [obj for obj in _drain_fd(r_stdout) if obj["type"] == "step_finished"]
    assert found[-1]["outcome"] == "settled"
    # close stdin: the driver sees EOF and returns; main reaps
    os.close(w_stdin)
    thread.join(10.0)
    assert result["code"] == 0
    assert fake.terminated  # main reaps the (still-alive) fake child
    os.close(r_stdout)
    monkeypatch.undo()


def _drain_fd(fd: int, seconds: float = 5.0) -> list[dict]:
    lines: list[dict] = []
    while True:
        ready, _, _ = select.select([fd], [], [], 0.3)
        if not ready:
            return lines
        data = os.read(fd, 65536)
        if not data:
            return lines
        lines.extend(
            json.loads(line)
            for line in data.decode().splitlines()
            if line
        )


def test_blank_line_on_stdin_is_skipped() -> None:
    driver = _start()
    driver.stdin.write("\n")
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    assert [obj for obj in lines if obj["type"] == "step_finished"]
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_terminal_derivation_ignores_messages_without_stop_reason() -> None:

    derive = pi_session.terminal_outcome_from_agent_end
    assert derive({"type": "agent_end", "messages": [{"chaos": 1}]}) == "settled"
    assert derive(
        {"type": "agent_end", "messages": [{"a": 1}, {"stopReason": "length"}]}
    ) == "output-limit"  # the LAST message's stopReason wins


def test_reap_escalates_to_kill_on_a_term_refusing_child() -> None:
    """reap(): TERM refused, wait times out, KILL runs, reap confirms."""
    import subprocess as _subprocess

    class _Stub:
        def __init__(self) -> None:
            self.terminated = False
            self.killed = False
            self.calls = 0
            self.stdin = _Sink()
            self.stdout = _Sink()

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: float) -> int:
            self.calls += 1
            if self.terminated and self.calls == 1:
                raise _subprocess.TimeoutExpired(cmd="pi", timeout=timeout)
            return 0

    class _Sink:
        def close(self) -> None:
            pass

    stub = _Stub()
    pi_session.reap(stub)  # type: ignore[bad-argument-type]  # _Stub duck-types the _PiHandle seam
    assert stub.terminated and stub.killed and stub.calls == 2


def test_reap_skips_a_child_that_already_exited() -> None:
    class _Sink:
        def close(self) -> None:
            pass

    class _Done:
        stdin = _Sink()
        stdout = _Sink()
        calls = 0

        def poll(self) -> int:
            return 0  # already gone

        def terminate(self) -> None:
            raise AssertionError("must not terminate a reaped child")

    pi_session.reap(_Done())  # type: ignore[bad-argument-type]  # _Done duck-types the _PiHandle seam


def test_unknown_typed_input_line_is_ignored() -> None:
    driver = _start()
    driver.stdin.write(json.dumps({"version": 1, "type": "chaos"}) + "\n")
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    assert [obj for obj in lines if obj["type"] == "step_finished"]
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_agent_end_willretry_keeps_the_terminal_settled() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "agent_end", "willRetry": True,
                   "messages": [{"stopReason": "error"}]})
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    finished = [obj for obj in lines if obj["type"] == "step_finished"]
    assert finished[-1]["outcome"] == "settled"  # a retry follows; not terminal
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_successful_auto_retry_end_keeps_the_terminal_settled() -> None:
    driver = _start()
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "auto_retry_end", "success": True})
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    finished = [obj for obj in lines if obj["type"] == "step_finished"]
    assert finished[-1]["outcome"] == "settled"
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_pi_stdout_eof_while_idle_ends_the_loop() -> None:
    """Pi exits while no prompt is pending: the driver breaks quietly."""
    driver = _start()
    driver.pi.pi_to_driver.close_write()
    driver.thread.join(5.0)
    assert not driver.thread.is_alive()
    driver.stdin.close_write()
    assert not driver.errors


def test_malformed_session_input_line_is_skipped() -> None:
    driver = _start()
    driver.stdin.write("{not json\n")
    driver.stdin.write(_prompt("add-a"))
    driver.pi.say({"type": "agent_settled"})
    lines = driver.stdout.drain()
    assert [obj for obj in lines if obj["type"] == "step_finished"]
    driver.stdin.close_write()
    driver.thread.join(5.0)
    assert not driver.errors


def test_pi_child_argv_and_runtime_env_carry_no_overlay_names():
    """Pins what evals constructs: the pi argv and _SESSION_RUNTIME_ENV.

    The inherited os.environ is the contributor's own environment, not
    evals-constructed content, and is out of scope here (spec §4).
    """
    from satyrn_evals.adapters.pi_session import (
        _SESSION_RUNTIME_ENV,
        build_pi_argv,
    )
    from satyrn_evals.manifest import (
        DEFAULT_TASKS_ROOT,
        _overlay_declared_names,
        load_manifest,
    )

    task_dir = DEFAULT_TASKS_ROOT / "session-mechanics"
    manifest = load_manifest(task_dir)
    assert manifest.grader_overlay is not None
    names = _overlay_declared_names(task_dir, manifest.grader_overlay)
    argv_text = " ".join(
        build_pi_argv(provider="p", model="m", tools=("read",), pi_bin="pi")
    )
    env_text = " ".join(f"{k}={v}" for k, v in _SESSION_RUNTIME_ENV.items())
    for name in names:
        assert name not in argv_text
        assert name not in env_text
