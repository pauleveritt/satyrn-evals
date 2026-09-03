"""The shipped Pi session adapter.

A narrow executable owning one conversation with Pi: it speaks the
2026-09-01 session JSONL protocol on its own stdin/stdout and drives one
``pi --mode rpc --no-session`` child (pi 0.84.4 docs/rpc.md). The RPC
mapping is a pure function; the complete original Pi event is carried
unmodified under ``payload`` so every count is recomputable.

The child shares this adapter's process group (no start_new_session), so
the executor's group teardown reaches Pi too. Model argv is space-form —
pi 0.80-0.84 rejects ``--model=VALUE`` (recorded satyrn-engine defect);
a shim is a failed stock-adapter proof, not a workaround to ship.
"""

import contextlib
import json
import os
import select
import subprocess
import sys
import uuid

from satyrn_evals.errors import ProtocolError

_SESSION_KINDS = {
    "turn_end": "turn_end",
    "tool_execution_end": "tool_end",
    "compaction_start": "context_compacted",
    "compaction_end": "context_compacted",
}


def build_pi_argv(provider: str, model: str, pi_bin: str = "pi") -> list[str]:
    """The Pi invocation: space-form flags only."""
    return [
        pi_bin,
        "--mode",
        "rpc",
        "--no-session",
        "--provider",
        provider,
        "--model",
        model,
    ]


def _session_line(obj: dict[str, object]) -> str:
    return json.dumps(obj) + "\n"


def map_rpc_event(
    obj: dict[str, object], *, step_id: str, conversation_id: str
) -> str | None:
    """Map one Pi RPC message to a session line, or None when unmapped.

    ``agent_settled`` maps to the terminal message. A response (command
    acknowledgement) is not an event; the driver handles it.
    """
    event_type = obj.get("type")
    if event_type == "agent_settled":
        return _session_line(
            {
                "version": 1,
                "type": "step_finished",
                "step_id": step_id,
                "conversation_id": conversation_id,
                "outcome": "settled",
                "message": None,
            }
        )
    kind = _SESSION_KINDS.get(event_type)  # type: ignore[arg-type]
    if kind is None:
        return None
    return _session_line(
        {
            "version": 1,
            "type": "event",
            "step_id": step_id,
            "kind": kind,
            "payload": obj,
        }
    )


def _emit(line: str) -> None:
    sys.stdout.write(line)
    sys.stdout.flush()


def _parse_args(args: list[str]) -> tuple[str, str, str]:
    provider, model, pi_bin = "anthropic", "", "pi"
    index = 0
    while index < len(args):
        match args[index]:
            case "--provider":
                provider = args[index + 1]
                index += 2
            case "--model":
                model = args[index + 1]
                index += 2
            case "--pi-bin":
                pi_bin = args[index + 1]
                index += 2
            case _:
                raise ProtocolError(f"unknown adapter argument: {args[index]!r}")
    if not model:
        raise ProtocolError("--model is required")
    return provider, model, pi_bin


def main(argv: list[str] | None = None) -> int:
    provider, model, pi_bin = _parse_args(
        list(sys.argv[1:] if argv is None else argv)
    )
    conversation_id = f"pi-{uuid.uuid4().hex[:12]}"
    proc = subprocess.Popen(
        build_pi_argv(provider, model, pi_bin),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdin is not None and proc.stdout is not None
    _emit(
        _session_line(
            {
                "version": 1,
                "type": "session_started",
                "conversation_id": conversation_id,
            }
        )
    )
    current_step: str | None = None
    request = 0
    pending_prompt = False
    pi_buf = b""
    stdin_fd = sys.stdin.fileno()

    def fail_agent_error(reason: str) -> str:
        return _session_line(
            {
                "version": 1,
                "type": "step_finished",
                "step_id": current_step,
                "conversation_id": conversation_id,
                "outcome": "agent-error",
                "message": reason,
            }
        )

    closed = False
    while not closed:
        readable = [fd for fd in (stdin_fd, proc.stdout.fileno()) if fd >= 0]
        ready, _, _ = select.select(readable, [], [], 1.0)
        for fd in ready:
            if fd == stdin_fd:
                raw = sys.stdin.readline()
                if not raw:
                    closed = True
                    break
                line = raw.strip()
                if not line:
                    continue
                message = json.loads(line)
                match message.get("type"):
                    case "prompt":
                        if pending_prompt:
                            continue  # protocol: no prompt before settled
                        current_step = message["step_id"]
                        request += 1
                        pending_prompt = True
                        proc.stdin.write(
                            json.dumps(
                                {
                                    "id": f"req-{request}",
                                    "type": "prompt",
                                    "message": message["text"],
                                }
                            ).encode("utf-8")
                            + b"\n"
                        )
                        proc.stdin.flush()
                    case "close":
                        closed = True
                        break
        if closed:
            break
        if proc.stdout.fileno() in ready:
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                if pending_prompt and current_step is not None:
                    _emit(
                        fail_agent_error("pi exited before settling the step")
                    )
                break
            pi_buf += chunk
            while b"\n" in pi_buf:
                raw_pi, _, pi_buf = pi_buf.partition(b"\n")
                try:
                    obj = json.loads(raw_pi.decode("utf-8", "surrogateescape"))
                except json.JSONDecodeError:
                    continue
                if obj.get("type") == "response":
                    if (
                        obj.get("command") == "prompt"
                        and obj.get("success") is False
                        and pending_prompt
                        and current_step is not None
                    ):
                        _emit(
                            fail_agent_error(str(obj.get("error", "prompt failed")))
                        )
                        pending_prompt = False
                        current_step = None
                    continue
                if current_step is None:
                    continue
                mapped = map_rpc_event(
                    obj, step_id=current_step, conversation_id=conversation_id
                )
                if mapped is None:
                    continue
                _emit(mapped)
                mapped_obj = json.loads(mapped)
                if mapped_obj.get("type") == "step_finished":
                    pending_prompt = False
                    current_step = None
    with contextlib.suppress(OSError):
        proc.stdin.close()
    if proc.poll() is None:
        with contextlib.suppress(ProcessLookupError):
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            proc.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
