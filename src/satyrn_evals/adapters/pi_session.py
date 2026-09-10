"""The shipped Pi session adapter.

A narrow executable owning one conversation with Pi: it speaks the
2026-09-01 session JSONL protocol on its own stdin/stdout and drives one
``pi --mode rpc --no-session`` child (docs/rpc.md, consulted at 0.84.4 and
reconfirmed unchanged at 0.85.1). The RPC mapping and the terminal-outcome
derivation are pure functions; the driver loop (``serve``) takes its
streams and child process as parameters so the whole loop is verifiable in
process — the coverage gate's subprocess patch does not reach this child,
and unverified branches in an adapter are review findings, not
assumptions. The complete original Pi event is carried unmodified under
``payload`` so every count is recomputable.

The child shares this adapter's process group (no start_new_session), so
the executor's group teardown reaches Pi too. Model argv is space-form —
pi 0.80-0.85 rejects ``--model=VALUE`` (recorded satyrn-engine defect,
reconfirmed at 0.85.1 2026-09-10); a shim is a failed stock-adapter proof,
not a workaround to ship.
"""

import contextlib
import json
import os
import select
import subprocess
import sys
import uuid
from collections.abc import Mapping, Sequence
from typing import BinaryIO, Protocol, TextIO, cast

from satyrn_evals.attempt_pi import clean_pi_environment
from satyrn_evals.errors import ProtocolError

# Session runtime policy: the model's python tool runs must not leave
# bytecode in the session workspace. A `__pycache__` tree under the
# evolving checkout is predictable runtime detritus — it lands in every
# cumulative patch and trips scope detection, so a self-verifying model
# would have every checkpoint marked out-of-scope. The policy is
# environment-side (PYTHONDONTWRITEBYTECODE on the pi child, inherited by
# the model's subprocesses), deliberately NOT a fixture `.gitignore`:
# a gitignore would change the evidence boundary and could hide
# unrelated mutations under ignored paths, whereas the environment
# policy leaves source_paths enforcement untouched.
_SESSION_RUNTIME_ENV = {"PYTHONDONTWRITEBYTECODE": "1"}


_SESSION_KINDS = {
    "turn_end": "turn_end",
    "tool_execution_end": "tool_end",
    "compaction_start": "context_compacted",
    "compaction_end": "context_compacted",
    # Pi's genuine streaming model event: retained (kind "other") so the
    # transcript carries positive evidence that the model actually ran —
    # the smoke's discriminator. The original event stays in payload.
    "message_update": "other",
    # Retained for evidence; terminal state is derived from them below.
    "agent_end": "other",
    "auto_retry_end": "other",
}


def terminal_outcome_from_agent_end(obj: dict[str, object]) -> str | None:
    """The step outcome Pi declared via agent_end, or None if not terminal.

    ``willRetry`` means an automatic retry follows — not terminal. The
    last message that declares a ``stopReason`` (rpc.md:1469) is Pi's own
    declaration: "length" is the output limit, "error"/"aborted" are
    agent errors, anything else settles normally. Evals never infers a
    limit from prose.
    """
    if obj.get("willRetry"):
        return None
    messages = obj.get("messages")
    stop = None
    if isinstance(messages, list):
        for message in reversed(messages):
            if isinstance(message, dict) and "stopReason" in message:
                stop = message["stopReason"]
                break
    match stop:
        case "length":
            return "output-limit"
        case "error" | "aborted":
            return "agent-error"
        case _:
            return "settled"


def build_pi_argv(
    provider: str,
    model: str,
    tools: Sequence[str],
    pi_bin: str = "pi",
) -> list[str]:
    """The Pi invocation: space-form flags only, on a declared tool surface.

    Every discovery path is off and the surface is the ``tools`` allowlist.
    This is not decoration. Launched without it (before 2026-09-08) a session
    ran on whatever the installed runtime exposed; the first bounded Baseline
    session reached the installed ``pi-subagents`` extension and dispatched a
    **detached** worker that wrote files across two checkpoint boundaries with
    no retained events. ``--tools`` alone would not have prevented it, because
    the tool came from an extension -- so extension discovery is disabled too,
    exactly as the attempt adapter does.
    """
    if not tools:
        raise ProtocolError(
            "--tools is required: a session with an unstated tool surface "
            "cannot produce accountable evidence"
        )
    return [
        pi_bin,
        "--mode",
        "rpc",
        "--no-session",
        "--provider",
        provider,
        "--model",
        model,
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-context-files",
        "--tools",
        ",".join(tools),
    ]


def _session_line(obj: dict[str, object]) -> str:
    return json.dumps(obj) + "\n"


def map_rpc_event(
    obj: Mapping[str, object], *, step_id: str, conversation_id: str
) -> str | None:
    """Map one Pi RPC message to a session line, or None when unmapped.

    ``agent_settled`` is the terminal; the driver supplies the tracked
    outcome. A response (command acknowledgement) is not an event; the
    driver handles it.
    """
    event_type = obj.get("type")
    if event_type == "agent_settled":
        return None
    kind = _SESSION_KINDS.get(event_type)  # type: ignore[arg-type]
    if kind is None:
        return None
    return _session_line(
        {
            "version": 1,
            "type": "event",
            "step_id": step_id,
            "conversation_id": conversation_id,
            "kind": kind,
            "payload": obj,
        }
    )


class _PiHandle(Protocol):
    """The subset of ``Popen`` the driver loop touches."""

    stdin: BinaryIO
    stdout: BinaryIO

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float) -> int: ...


def _parse_args(args: list[str]) -> tuple[str, str, tuple[str, ...], str]:
    provider, model, pi_bin = "anthropic", "", "pi"
    tools: tuple[str, ...] = ()
    index = 0
    while index < len(args):
        match args[index]:
            case "--provider":
                provider = args[index + 1]
                index += 2
            case "--model":
                model = args[index + 1]
                index += 2
            case "--tools":
                tools = tuple(
                    name for name in args[index + 1].split(",") if name.strip()
                )
                index += 2
            case "--pi-bin":
                pi_bin = args[index + 1]
                index += 2
            case _:
                raise ProtocolError(f"unknown adapter argument: {args[index]!r}")
    if not model:
        raise ProtocolError("--model is required")
    if not tools:
        # Required rather than defaulted: a default of "everything" is the
        # defect this fixes, and a default of "nothing" would silently
        # disarm the session instead of refusing it.
        raise ProtocolError("--tools is required")
    return provider, model, tools, pi_bin


def _serve(
    stdin_file: TextIO, stdout_file: TextIO, proc: _PiHandle,
    *, conversation_id: str,
) -> None:
    """Drive one conversation between session stdin and the pi child.

    Both streams and the child handle are parameters so the loop runs
    in-process under the coverage gate; ``main`` is the executable shell.
    Stdin is read from its raw descriptor with an explicit line buffer: a
    buffered reader would hide lines from ``select`` and stall the loop.
    """
    current_step: str | None = None
    request = 0
    pending_prompt = False
    pending_outcome = "settled"
    pi_buf = b""
    stdin_buf = b""
    stdin_eof = False
    stdin_fd = stdin_file.fileno()

    def emit(line: str) -> None:
        stdout_file.write(line)
        stdout_file.flush()

    def step_finished(outcome: str, message: str | None) -> str:
        return _session_line(
            {
                "version": 1,
                "type": "step_finished",
                "step_id": current_step,
                "conversation_id": conversation_id,
                "outcome": outcome,
                "message": message,
            }
        )

    def send_prompt(message: dict[str, object]) -> None:
        nonlocal current_step, request, pending_prompt, pending_outcome
        if pending_prompt:
            return  # protocol: no prompt before settled
        current_step = message["step_id"]  # type: ignore[assignment]
        request += 1
        pending_prompt = True
        pending_outcome = "settled"
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

    def handle_input(line: str) -> bool:
        """One decoded session line; returns True when the loop must close."""
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return False  # malformed session line: skipped, like pi output
        match message.get("type"):
            case "prompt":
                send_prompt(message)
            case "close":
                return True
        return False

    closed = False
    while not closed:
        readable = [fd for fd in (stdin_fd, proc.stdout.fileno()) if fd >= 0]
        ready, _, _ = select.select(readable, [], [], 1.0)
        if stdin_fd in ready and not stdin_eof:
            chunk = os.read(stdin_fd, 65536)
            if not chunk:
                stdin_eof = True
            else:
                stdin_buf += chunk
                while b"\n" in stdin_buf:
                    raw_line, _, stdin_buf = stdin_buf.partition(b"\n")
                    line = raw_line.decode("utf-8", "surrogateescape").strip()
                    if not line:
                        continue
                    if handle_input(line):
                        closed = True
                        break
        if stdin_eof and not pending_prompt:
            break
        if proc.stdout.fileno() in ready:
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                if pending_prompt and current_step is not None:
                    emit(step_finished("agent-error", "pi exited before settling the step"))
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
                        emit(
                            step_finished(
                                "agent-error", str(obj.get("error", "prompt failed"))
                            )
                        )
                        pending_prompt = False
                        current_step = None
                    continue
                if current_step is None:
                    continue
                # terminal state is tracked from agent_end / auto_retry_end
                # BEFORE agent_settled (review finding 3): the settled
                # terminal carries the outcome Pi declared, never a
                # blanket "settled".
                match obj.get("type"):
                    case "agent_end":
                        declared = terminal_outcome_from_agent_end(obj)
                        if declared is not None:
                            pending_outcome = declared
                    case "auto_retry_end":
                        if obj.get("success") is False:
                            pending_outcome = "agent-error"
                mapped = map_rpc_event(
                    obj, step_id=current_step, conversation_id=conversation_id
                )
                if mapped is not None:
                    emit(mapped)
                if obj.get("type") == "agent_settled":
                    emit(step_finished(pending_outcome, None))
                    pending_prompt = False
                    current_step = None


def session_child_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """The env for the Pi child: Evals' own virtualenv stripped, runtime overlaid.

    Reuses ``attempt_pi.clean_pi_environment`` rather than reimplementing
    it — the session adapter previously spawned Pi with a raw
    ``{**os.environ, **_SESSION_RUNTIME_ENV}``, which let this repo's own
    ``VIRTUAL_ENV``/``PATH`` reach the model's shell (see 2026-09-09
    session-phased-verify RESULT.md, finding 2).
    """
    cleaned = clean_pi_environment(environ)
    return {**cleaned, **_SESSION_RUNTIME_ENV}


def reap(proc: _PiHandle) -> None:
    """Stop and reap the pi child: close stdin, TERM, then KILL on refusal."""
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


def main(argv: list[str] | None = None) -> int:
    provider, model, tools, pi_bin = _parse_args(
        list(sys.argv[1:] if argv is None else argv)
    )
    conversation_id = f"pi-{uuid.uuid4().hex[:12]}"
    proc = subprocess.Popen(
        build_pi_argv(provider, model, tools, pi_bin),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=session_child_environment(os.environ),
    )
    assert proc.stdin is not None and proc.stdout is not None
    # Popen satisfies the _PiHandle seam at runtime; pyrefly's structural
    # protocol check cannot match typeshed's `IO[Any] | None` members, so
    # the real handle is cast to the seam once, at its construction.
    handle = cast(_PiHandle, proc)
    sys.stdout.write(
        _session_line(
            {
                "version": 1,
                "type": "session_started",
                "conversation_id": conversation_id,
            }
        )
    )
    sys.stdout.flush()
    _serve(sys.stdin, sys.stdout, handle, conversation_id=conversation_id)
    reap(handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
