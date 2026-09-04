"""The session adapter protocol: versioned JSONL over stdin/stdout.

Message shapes are the 2026-09-01 spec's, verbatim. The parser is
structural only: state rules (one session_started, stable conversation
identity, no duplicate steps) live with the executor.
"""

import json
from dataclasses import dataclass

from satyrn_evals.errors import ProtocolError

type EventKind = str
"""turn_end | tool_end | context_compacted | context_reset | other."""

_EVENT_KINDS = frozenset(
    {"turn_end", "tool_end", "context_compacted", "context_reset", "other"}
)
_OUTCOMES = frozenset({"settled", "output-limit", "agent-error"})


@dataclass(frozen=True, slots=True)
class SessionStarted:
    version: int
    conversation_id: str


@dataclass(frozen=True, slots=True)
class EventLine:
    version: int
    step_id: str
    conversation_id: str
    kind: EventKind
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class StepFinished:
    version: int
    step_id: str
    conversation_id: str
    outcome: str
    message: str | None


@dataclass(frozen=True, slots=True)
class CloseLine:
    version: int


type SessionMessage = SessionStarted | EventLine | StepFinished | CloseLine


def parse_session_line(line: str) -> SessionMessage:
    """Parse one adapter line; refuse structural faults."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"malformed protocol line: {e}") from e
    if not isinstance(obj, dict):
        raise ProtocolError("protocol line must be a JSON object")
    version = obj.get("version")
    if isinstance(version, bool) or version != 1:
        raise ProtocolError(f"unknown protocol version: {version!r}")
    type_ = obj.get("type")
    match type_:
        case "session_started":
            if set(obj) != {"version", "type", "conversation_id"}:
                raise ProtocolError(
                    "session_started must hold exactly version, type, "
                    "conversation_id"
                )
            cid = obj["conversation_id"]
            if not isinstance(cid, str) or not cid:
                raise ProtocolError(
                    "session_started conversation_id must be a non-empty string"
                )
            return SessionStarted(version=1, conversation_id=cid)
        case "event":
            if set(obj) != {
                "version",
                "type",
                "step_id",
                "conversation_id",
                "kind",
                "payload",
            }:
                raise ProtocolError(
                    "event must hold exactly version, type, step_id, "
                    "conversation_id, kind, payload"
                )
            step_id = obj["step_id"]
            if not isinstance(step_id, str) or not step_id:
                raise ProtocolError("event step_id must be a non-empty string")
            kind = obj["kind"]
            if kind not in _EVENT_KINDS:
                raise ProtocolError(f"unknown event kind: {kind!r}")
            cid = obj["conversation_id"]
            if not isinstance(cid, str) or not cid:
                raise ProtocolError(
                    "event conversation_id must be a non-empty string"
                )
            payload = obj["payload"]
            if not isinstance(payload, dict):
                raise ProtocolError("event payload must be an object")
            return EventLine(
                version=1,
                step_id=step_id,
                conversation_id=cid,
                kind=kind,
                payload=payload,
            )
        case "step_finished":
            if set(obj) != {
                "version",
                "type",
                "step_id",
                "conversation_id",
                "outcome",
                "message",
            }:
                raise ProtocolError(
                    "step_finished must hold exactly version, type, step_id, "
                    "conversation_id, outcome, message"
                )
            step_id = obj["step_id"]
            if not isinstance(step_id, str) or not step_id:
                raise ProtocolError("step_finished step_id must be non-empty")
            cid = obj["conversation_id"]
            if not isinstance(cid, str) or not cid:
                raise ProtocolError(
                    "step_finished conversation_id must be non-empty"
                )
            outcome = obj["outcome"]
            if outcome not in _OUTCOMES:
                raise ProtocolError(f"unknown outcome: {outcome!r}")
            message = obj["message"]
            if message is not None and not isinstance(message, str):
                raise ProtocolError("step_finished message must be a string or null")
            return StepFinished(
                version=1,
                step_id=step_id,
                conversation_id=cid,
                outcome=outcome,
                message=message,
            )
        case "close":
            if set(obj) != {"version", "type"}:
                raise ProtocolError("close must hold exactly version and type")
            return CloseLine(version=1)
        case _:
            raise ProtocolError(f"unknown protocol type: {type_!r}")


def serialize_prompt(step_id: str, text: str) -> str:
    """The prompt Evals sends to the adapter for one step."""
    return (
        json.dumps({"version": 1, "type": "prompt", "step_id": step_id, "text": text})
        + "\n"
    )


def serialize_close() -> str:
    """The close Evals sends after the final settled checkpoint."""
    return json.dumps({"version": 1, "type": "close"}) + "\n"
