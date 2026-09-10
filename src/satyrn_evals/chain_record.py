"""HP6: the chain retained and re-scorable.

``run_phases`` returns a ``list[PhaseDecision]`` and keeps nothing once the
caller drops it (``route.py``); the packets it built and HP5's attribution
are gone with it. This module turns one run's ``BoundaryEvent`` stream and
attribution ledger into a durable ``ChainRecord`` from which the
accept-or-reject sequence reads back losslessly (``decisions_from_record`` --
a read-back, not an independent recomputation from raw evidence; see its own
docstring), and it names three things a chain can otherwise hide: an
unobserved implementer step, an implementer mutation outside its own packet's
declared scope, and a packet declaration the runtime never applied
(together, ``check_chain`` and ``declaration_ledger``).

Nothing here applies a declaration the ledger records as unapplied, decides a
cost threshold, or runs a real engine -- HP6 retains what happened; it does
not change what the route does. What is retained is mutation **paths and
kinds**, not patch content -- "re-scorable" here means every accept/reject
decision reads back from the document, not that a candidate's bytes can be
regraded from it; regrading the candidate itself is not attempted.
"""

import json
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import get_args

from satyrn_evals.attribution import ChainLedger, Mutation, MutationKind
from satyrn_evals.engine_contract import admits
from satyrn_evals.errors import ChainRecordError
from satyrn_evals.packet import (
    HandoffPacket,
    packet_from_dict,
    packet_to_dict,
)
from satyrn_evals.route import (
    BoundaryEvent,
    ImplementerResult,
    PhaseDecision,
    implementer_result_from_dict,
    implementer_result_to_dict,
)

CHAIN_RECORD_VERSION: int = 1

# `__value__` is the TypeAliasType accessor, same trick `packet.py` uses for
# `PacketRole`: it unwraps `type X = ...` to the Literal underneath, so the
# alias stays the single source of the valid kinds.
_MUTATION_KINDS: frozenset[str] = frozenset(get_args(MutationKind.__value__))

#: The packet declarations this cycle tracks. Not every ``HandoffPacket``
#: field: ``objective``, ``facts`` and ``preserve`` are content the
#: implementer reads, not a runtime obligation, so there is nothing for the
#: route to apply or not.
DECLARATION_FIELDS: tuple[str, ...] = (
    "turn_budget",
    "tool_call_budget",
    "self_test_command",
    "base_revision",
    "writable_paths",
    "redacts",
)


class AppliedState(StrEnum):
    """What the runtime did with one packet declaration.

    Three values on purpose, so absent is never spelled as applied and
    unapplied is never spelled as absent: ``UNKNOWN`` is for a field this
    build has not yet classified, never a silent default for one it has.
    """

    APPLIED = "applied"
    DECLARED_NOT_APPLIED = "declared_not_applied"
    UNKNOWN = "unknown"


def declaration_ledger(
    *,
    executable_seam: bool,
    packet: HandoffPacket,
    implementer_mutations: tuple[Mutation, ...] | None,
) -> dict[str, AppliedState]:
    """What this run's own evidence says about each tracked declaration.

    ``turn_budget``, ``tool_call_budget``, ``self_test_command`` and
    ``base_revision`` are built into every packet and read nowhere outside
    ``packet.py`` and the ``build_packet`` call (``route.py``) -- no code
    counts a turn, runs the self-test command, or checks out the named
    revision, so all four are always declared and unapplied on this route.
    ``redacts`` is the one field that takes both values from the same task:
    ``assert_projection_is_clean`` runs only inside ``command_implementer``,
    so it is applied on the executable seam and declared-and-unapplied on the
    in-process one.

    ``writable_paths`` is **derived from observation, not asserted.**
    ``scripted_implementer`` happens to enforce its own scope, but that is a
    property of one fixture, not of the route -- a real implementer on the
    executable seam enforces nothing the route checks. So: ``unknown`` when
    the implementer window was never observed (nothing to check);
    ``declared_not_applied`` when an observed mutation lands outside the
    packet's own ``writable_paths`` (proof the scope was not honoured);
    ``applied`` only when every observed mutation admits within it. Staying
    in scope does not *prove* enforcement -- nothing here does -- but a
    mutation caught outside it proves the opposite, and that asymmetry is
    the honest one to keep.
    """
    if implementer_mutations is None:
        writable_state = AppliedState.UNKNOWN
    elif any(
        not admits(packet.writable_paths, mutation.path)
        for mutation in implementer_mutations
    ):
        writable_state = AppliedState.DECLARED_NOT_APPLIED
    else:
        writable_state = AppliedState.APPLIED
    return {
        "turn_budget": AppliedState.DECLARED_NOT_APPLIED,
        "tool_call_budget": AppliedState.DECLARED_NOT_APPLIED,
        "self_test_command": AppliedState.DECLARED_NOT_APPLIED,
        "base_revision": AppliedState.DECLARED_NOT_APPLIED,
        "writable_paths": writable_state,
        "redacts": (
            AppliedState.APPLIED
            if executable_seam
            else AppliedState.DECLARED_NOT_APPLIED
        ),
    }


@dataclass(frozen=True, slots=True)
class PhaseRecord:
    """One phase, retained: what it was asked, what happened, who did it.

    ``implementer_mutations``/``orchestrator_mutations`` are ``None`` when
    that window was never observed -- HP5's unobserved-is-not-zero rule,
    carried into the retained document rather than only into the live
    ledger. ``implementer_cost``/``orchestrator_cost`` are ``None`` when
    nothing measured them, which the offline route always is; a zero must
    never stand in for unmeasured (HP6.4), so the constructor refuses one.
    """

    step_id: str
    packet: HandoffPacket
    result: ImplementerResult
    accepted: bool
    reason: str
    implementer_mutations: tuple[Mutation, ...] | None
    orchestrator_mutations: tuple[Mutation, ...] | None
    declaration_ledger: Mapping[str, AppliedState]
    implementer_cost: float | None = None
    orchestrator_cost: float | None = None

    def __post_init__(self) -> None:
        for name in ("implementer_cost", "orchestrator_cost"):
            value = getattr(self, name)
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ChainRecordError(
                    f"{name} must be a positive, finite number or null: "
                    f"{value!r}; a zero, negative, NaN or infinite value is "
                    "not a stand-in for unmeasured"
                )

    @property
    def fallback(self) -> bool:
        """Whether this phase's orchestrator window holds any mutation.

        States what was observed; it does not judge whether the fallback was
        warranted (HP6.5). ``None`` (unobserved) is not fallback -- there is
        nothing to hold, and calling an unobserved window a clean one is
        exactly what ``check_chain`` exists to catch instead.
        """
        return bool(self.orchestrator_mutations)


@dataclass(frozen=True, slots=True)
class ChainRecord:
    """The durable record of one route run, from which decisions recompute."""

    version: int
    phases: tuple[PhaseRecord, ...]
    final_decision: PhaseDecision | None

    def __post_init__(self) -> None:
        if self.version != CHAIN_RECORD_VERSION:
            raise ChainRecordError(
                f"unknown chain record version {self.version!r}; this build "
                f"reads and writes version {CHAIN_RECORD_VERSION}"
            )


def build_chain_record(
    decisions: Sequence[PhaseDecision],
    events: Sequence[BoundaryEvent],
    ledger: ChainLedger,
    *,
    executable_seam: bool,
    costs: Mapping[str, tuple[float | None, float | None]] | None = None,
) -> ChainRecord:
    """Assemble one ``ChainRecord`` from one run's retained observations.

    ``decisions`` is ``run_phases``'s own return value -- the authoritative
    per-phase accept-or-reject, including the exit path (delivered, refused,
    rejected) that stopped the chain early. ``events`` supplies each phase's
    packet, taken from its ``before_handoff`` edge, and the run's closing
    decision, taken from ``chain_end``; the packet does not otherwise survive
    the call that built it. ``ledger`` is HP5's attribution, already computed
    from the same run's boundary snapshots. Nothing here re-derives a verdict
    -- it retains what three already-computed sources produced.
    """
    packets: dict[str, HandoffPacket] = {
        event.step_id: event.packet
        for event in events
        if event.boundary == "before_handoff" and event.packet is not None
    }
    final_decision = next(
        (event.decision for event in events if event.boundary == "chain_end"),
        None,
    )
    attribution_by_step = {phase.step_id: phase for phase in ledger.phases}
    costs = costs or {}
    phases: list[PhaseRecord] = []
    for decision in decisions:
        packet = packets.get(decision.step_id)
        if packet is None:
            raise ChainRecordError(
                f"no retained packet for step {decision.step_id!r}; every "
                "decided phase must have opened a before_handoff window"
            )
        attribution = attribution_by_step.get(decision.step_id)
        implementer_mutations = (
            None if attribution is None else attribution.implementer
        )
        implementer_cost, orchestrator_cost = costs.get(
            decision.step_id, (None, None)
        )
        phases.append(
            PhaseRecord(
                step_id=decision.step_id,
                packet=packet,
                result=decision.result,
                accepted=decision.accepted,
                reason=decision.reason,
                implementer_mutations=implementer_mutations,
                orchestrator_mutations=(
                    None if attribution is None else attribution.orchestrator
                ),
                declaration_ledger=declaration_ledger(
                    executable_seam=executable_seam,
                    packet=packet,
                    implementer_mutations=implementer_mutations,
                ),
                implementer_cost=implementer_cost,
                orchestrator_cost=orchestrator_cost,
            )
        )
    return ChainRecord(
        version=CHAIN_RECORD_VERSION,
        phases=tuple(phases),
        final_decision=final_decision,
    )


@dataclass(frozen=True, slots=True)
class ChainFinding:
    """One thing ``check_chain`` found wrong with a retained record."""

    step_id: str
    reason: str


def check_chain(record: ChainRecord) -> tuple[ChainFinding, ...]:
    """Findings a retained chain record exposes on its own -- no re-run.

    Three kinds, and only three, because widening this into a pathology
    detector is explicitly out of scope:

    - a phase whose implementer window went unobserved;
    - a phase whose implementer left a mutation outside its own packet's
      declared ``writable_paths`` -- the same evidence
      ``declaration_ledger`` reads to mark that field
      ``declared_not_applied``, surfaced here as a finding rather than left
      for a reader to notice only by inspecting the ledger by hand;
    - a phase whose two independently-captured copies of its closing
      decision disagree: the one taken at the route's ``chain_end`` boundary
      (``final_decision``) against the one retained on its own
      ``PhaseRecord``. This is a **consistency check between two captures of
      the same run**, not a re-derivation from raw evidence -- nothing here
      recomputes a verdict from anything but the record's own fields.

    A phase with a real, observed zero mutations is **not** a finding --
    that is the seed-221 shape HP5 exists to report, and conflating it with
    "nobody looked" is the one mistake this function exists to refuse
    (HP6.6).
    """
    findings: list[ChainFinding] = []
    for phase in record.phases:
        if phase.implementer_mutations is None:
            findings.append(
                ChainFinding(
                    phase.step_id,
                    "implementer window was never observed",
                )
            )
        elif any(
            not admits(phase.packet.writable_paths, mutation.path)
            for mutation in phase.implementer_mutations
        ):
            findings.append(
                ChainFinding(
                    phase.step_id,
                    "implementer mutation lies outside the packet's declared "
                    "writable_paths",
                )
            )
    if record.final_decision is not None:
        closing = next(
            (p for p in record.phases if p.step_id == record.final_decision.step_id),
            None,
        )
        if closing is not None and (
            closing.accepted != record.final_decision.accepted
            or closing.reason != record.final_decision.reason
        ):
            findings.append(
                ChainFinding(
                    closing.step_id,
                    "the chain_end-captured decision disagrees with the "
                    "decision retained on the phase record",
                )
            )
    return tuple(findings)


def decisions_from_record(record: ChainRecord) -> list[PhaseDecision]:
    """Read the accept-or-reject sequence back from the record alone.

    This is a **lossless read-back**, not an independent recomputation from
    raw evidence: every field a ``PhaseDecision`` needs is already retained
    verbatim on the matching ``PhaseRecord``, so this cannot disagree with
    what was stored by construction. What it proves is narrower and still the
    point -- BRIEF.md invariant 1's "recomputes from retained artifacts" --
    that the document alone, with no task directory, no manifest and no
    grader, carries everything ``PhaseDecision`` needs, across all three exit
    paths run_phases can take (delivered to the end, an implementer refusal,
    a grader rejection), since each leaves a different-length ``phases``
    tuple and this reads whichever it is handed. It is **not** evidence that
    the retained decision was itself correct; that would require re-grading
    the retained candidate, which HP6 does not attempt.
    """
    return [
        PhaseDecision(phase.step_id, phase.accepted, phase.reason, phase.result)
        for phase in record.phases
    ]


def _mutation_to_dict(mutation: Mutation) -> dict[str, object]:
    return {"path": mutation.path, "kind": mutation.kind}


def _mutation_from_dict(data: Mapping[str, object]) -> Mutation:
    path, kind = data.get("path"), data.get("kind")
    if not isinstance(path, str) or not path.strip():
        raise ChainRecordError("persisted mutation path must be non-blank text")
    if kind not in _MUTATION_KINDS:
        raise ChainRecordError(
            f"persisted mutation kind must be one of {sorted(_MUTATION_KINDS)}: "
            f"{kind!r}"
        )
    return Mutation(path, kind)  # type: ignore[arg-type]


def _mutations_to_list(
    mutations: tuple[Mutation, ...] | None,
) -> list[dict[str, object]] | None:
    return None if mutations is None else [_mutation_to_dict(m) for m in mutations]


def _mutations_from_list(
    data: object,
) -> tuple[Mutation, ...] | None:
    if data is None:
        return None
    if not isinstance(data, list):
        raise ChainRecordError("persisted mutations must be a list or null")
    return tuple(_mutation_from_dict(entry) for entry in data)


def _phase_decision_to_dict(decision: PhaseDecision) -> dict[str, object]:
    return {
        "step_id": decision.step_id,
        "accepted": decision.accepted,
        "reason": decision.reason,
        "result": implementer_result_to_dict(decision.result),
    }


def _phase_decision_from_dict(data: Mapping[str, object]) -> PhaseDecision:
    keys = {"step_id", "accepted", "reason", "result"}
    if missing := sorted(keys - set(data)):
        raise ChainRecordError(
            f"persisted final_decision is missing {', '.join(missing)}"
        )
    step_id, accepted, reason, result = (
        data["step_id"], data["accepted"], data["reason"], data["result"],
    )
    if not isinstance(step_id, str) or not isinstance(reason, str):
        raise ChainRecordError("persisted final_decision has the wrong shape")
    if not isinstance(accepted, bool):
        raise ChainRecordError("persisted final_decision.accepted must be a bool")
    if not isinstance(result, dict):
        raise ChainRecordError("persisted final_decision.result must be an object")
    return PhaseDecision(
        step_id, accepted, reason, implementer_result_from_dict(result)
    )


_PHASE_KEYS: frozenset[str] = frozenset(
    {
        "step_id",
        "packet",
        "result",
        "accepted",
        "reason",
        "implementer_mutations",
        "orchestrator_mutations",
        "declaration_ledger",
        "implementer_cost",
        "orchestrator_cost",
    }
)


def _phase_record_to_dict(phase: PhaseRecord) -> dict[str, object]:
    return {
        "step_id": phase.step_id,
        "packet": packet_to_dict(phase.packet),
        "result": implementer_result_to_dict(phase.result),
        "accepted": phase.accepted,
        "reason": phase.reason,
        "implementer_mutations": _mutations_to_list(phase.implementer_mutations),
        "orchestrator_mutations": _mutations_to_list(phase.orchestrator_mutations),
        "declaration_ledger": {
            name: state.value for name, state in phase.declaration_ledger.items()
        },
        "implementer_cost": phase.implementer_cost,
        "orchestrator_cost": phase.orchestrator_cost,
    }


def _phase_record_from_dict(data: Mapping[str, object]) -> PhaseRecord:
    if missing := sorted(_PHASE_KEYS - set(data)):
        raise ChainRecordError(f"persisted phase is missing {', '.join(missing)}")
    step_id = data["step_id"]
    if not isinstance(step_id, str):
        raise ChainRecordError("persisted phase step_id must be a string")
    packet = data["packet"]
    result = data["result"]
    accepted = data["accepted"]
    reason = data["reason"]
    if not isinstance(packet, dict) or not isinstance(result, dict):
        raise ChainRecordError("persisted phase packet/result must be objects")
    if not isinstance(accepted, bool) or not isinstance(reason, str):
        raise ChainRecordError("persisted phase accepted/reason has the wrong shape")
    ledger_data = data["declaration_ledger"]
    if not isinstance(ledger_data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in ledger_data.items()
    ):
        raise ChainRecordError("persisted declaration_ledger must be a str->str map")
    for cost_name in ("implementer_cost", "orchestrator_cost"):
        cost = data[cost_name]
        if cost is not None and (
            isinstance(cost, bool) or not isinstance(cost, (int, float))
        ):
            raise ChainRecordError(f"persisted {cost_name} must be a number or null")
    declaration: dict[str, AppliedState] = {}
    for name, value in ledger_data.items():
        try:
            declaration[name] = AppliedState(value)
        except ValueError as exc:
            raise ChainRecordError(
                f"persisted declaration_ledger[{name!r}] is not a known "
                f"applied state: {value!r}"
            ) from exc
    return PhaseRecord(
        step_id=step_id,
        packet=packet_from_dict(packet),
        result=implementer_result_from_dict(result),
        accepted=accepted,
        reason=reason,
        implementer_mutations=_mutations_from_list(data["implementer_mutations"]),
        orchestrator_mutations=_mutations_from_list(data["orchestrator_mutations"]),
        declaration_ledger=declaration,
        implementer_cost=data["implementer_cost"],
        orchestrator_cost=data["orchestrator_cost"],
    )


def chain_record_to_dict(record: ChainRecord) -> dict[str, object]:
    """A record as plain JSON-ready data, for persistence and for the golden."""
    return {
        "version": record.version,
        "phases": [_phase_record_to_dict(phase) for phase in record.phases],
        "final_decision": (
            None
            if record.final_decision is None
            else _phase_decision_to_dict(record.final_decision)
        ),
    }


def chain_record_from_dict(data: Mapping[str, object]) -> ChainRecord:
    """Load a persisted record, checking shape **before** conversion.

    A truncated document (a missing top-level key) and a document written by
    a future version are each refused before any field is touched; a
    well-formed sibling loads (``BRIEF.md`` invariant 5).
    """
    keys = {"version", "phases", "final_decision"}
    if missing := sorted(keys - set(data)):
        raise ChainRecordError(f"persisted chain record is missing {', '.join(missing)}")
    version = data["version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise ChainRecordError(f"persisted version must be an integer: {version!r}")
    if version != CHAIN_RECORD_VERSION:
        raise ChainRecordError(
            f"unknown chain record version {version!r}; this build reads "
            f"version {CHAIN_RECORD_VERSION}"
        )
    phases_data = data["phases"]
    if not isinstance(phases_data, list):
        raise ChainRecordError("persisted phases must be a list")
    final_data = data["final_decision"]
    if final_data is not None and not isinstance(final_data, dict):
        raise ChainRecordError("persisted final_decision must be an object or null")
    return ChainRecord(
        version=version,
        phases=tuple(_phase_record_from_dict(p) for p in phases_data),
        final_decision=(
            None if final_data is None else _phase_decision_from_dict(final_data)
        ),
    )


def write_chain_record(path: Path, record: ChainRecord) -> None:
    """Write the record durably: fsync the file, then replace atomically.

    Mirrors ``session_record.write_session_record``'s shape exactly, so a
    reader of either finds the same durability guarantee. ``allow_nan=False``
    is defense in depth, not the primary guard: ``PhaseRecord.__post_init__``
    already refuses a non-finite cost at construction, so this only fires if
    some other ``float`` field ever goes non-finite -- a silent ``NaN``
    written as the bare JSON token is precisely the "unmeasured wearing a
    number" shape HP6.4 exists to refuse, and a loud ``ValueError`` here beats
    a value that reads back silently.
    """
    data = chain_record_to_dict(record)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_chain_record(path: Path) -> ChainRecord:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ChainRecordError("chain record is not an object")
    return chain_record_from_dict(data)
