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

import hashlib
import json
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import get_args

from satyrn_evals.attribution import (
    ChainLedger,
    Mutation,
    MutationKind,
    Snapshot,
    attribute,
    diff_snapshots,
    snapshot,
)
from satyrn_evals.engine_contract import admits
from satyrn_evals.errors import ChainRecordError
from satyrn_evals.manifest import TaskManifest
from satyrn_evals.packet import (
    HandoffPacket,
    packet_from_dict,
    packet_to_dict,
)
from satyrn_evals.route import (
    BoundaryEvent,
    Implementer,
    ImplementerResult,
    PhaseDecision,
    PhaseGrader,
    implementer_result_from_dict,
    implementer_result_to_dict,
    is_executable_seam,
    run_phases,
)
from satyrn_evals.session_manifest import SessionSpec

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

    Four values on purpose, so absent is never spelled as applied and
    unapplied is never spelled as absent: ``UNKNOWN`` is for a field this
    build has not yet classified, never a silent default for one it has.

    ``APPLIED`` is reserved for a declaration whose enforcement is **known
    to have run** -- a code path this build can name and point to, such as
    ``assert_projection_is_clean`` actually executing on the executable seam
    (``route.is_executable_seam``). ``OBSERVED_COMPLIANT`` is different and
    deliberately weaker: every mutation this run observed happened to stay
    in bounds, which is consistent with enforcement but does not establish
    it -- nothing an implementer merely declines to do proves a restriction
    would have stopped it from doing so. Corrected 2026-09-10 (Sol): the
    first version of ``declaration_ledger`` spelled that second case
    ``APPLIED`` too, so "the implementer happened not to leave scope" and
    "something checked and blocked it" were the same recorded value.
    """

    APPLIED = "applied"
    OBSERVED_COMPLIANT = "observed_compliant"
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

    ``writable_paths`` is **derived from observation, not asserted,** and
    never reaches ``applied``: nothing this build observes can name a code
    path that actively enforces scope on an implementer's behalf --
    ``scripted_implementer`` happens to enforce its own, but that is a
    property of one fixture policing itself, not something the route or this
    ledger can see or take credit for, and the real adapter deliberately
    does not self-enforce at all (``adapters/pi_implementer.py``). So:
    ``unknown`` when the implementer window was never observed (nothing to
    check); ``declared_not_applied`` when an observed mutation lands outside
    the packet's own ``writable_paths`` (unambiguous: the scope was not
    honoured); ``observed_compliant`` when every observed mutation admits
    within it -- **compliance, not enforcement.** An implementer that never
    tried to leave scope looks identical to one a restriction actually
    stopped, and this ledger does not have the evidence to tell them apart,
    so it does not claim to.
    """
    if implementer_mutations is None:
        writable_state = AppliedState.UNKNOWN
    elif any(
        not admits(packet.writable_paths, mutation.path)
        for mutation in implementer_mutations
    ):
        writable_state = AppliedState.DECLARED_NOT_APPLIED
    else:
        writable_state = AppliedState.OBSERVED_COMPLIANT
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

    ``accepted``/``reason`` are ``None`` together, and only together: a
    **candidate persisted, not yet graded**. Corrected 2026-09-10 (Sol): the
    first version required a decision to exist before a phase could be
    retained at all, which is backwards -- "preserve before judging" means
    the candidate must survive a grader that never returns.
    ``candidate_snapshot_path``/``_digest`` reference the actual file content
    an implementer produced this phase, captured before grading and written
    durably (``run_and_record_chain``) -- distinct from
    ``implementer_mutations``, which names only paths and kinds. ``None``
    when nothing captured it (``build_chain_record``, the lower-level API,
    never does; it has no workspace to read from).
    """

    step_id: str
    packet: HandoffPacket
    result: ImplementerResult
    accepted: bool | None
    reason: str | None
    implementer_mutations: tuple[Mutation, ...] | None
    orchestrator_mutations: tuple[Mutation, ...] | None
    declaration_ledger: Mapping[str, AppliedState]
    candidate_snapshot_path: str | None = None
    candidate_snapshot_digest: str | None = None
    implementer_cost: float | None = None
    orchestrator_cost: float | None = None

    def __post_init__(self) -> None:
        if (self.accepted is None) != (self.reason is None):
            raise ChainRecordError(
                "accepted and reason must both be set (graded) or both be "
                "null (a persisted candidate awaiting grading), never one "
                "without the other"
            )
        if (self.candidate_snapshot_path is None) != (
            self.candidate_snapshot_digest is None
        ):
            raise ChainRecordError(
                "candidate_snapshot_path and candidate_snapshot_digest must "
                "both be set or both be null"
            )
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
    def graded(self) -> bool:
        """Whether this phase has a decision yet -- the opposite of a
        candidate persisted while grading was still in flight, or never
        reached, because the chain crashed or the process died first."""
        return self.accepted is not None

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


def _write_text_durably(path: Path, text: str) -> None:
    """Fsync then atomic replace -- the same durability shape as
    ``write_chain_record``, factored out so candidate evidence gets the same
    guarantee the chain record itself does."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def run_and_record_chain(
    task_dir: Path,
    manifest: TaskManifest,
    spec: SessionSpec,
    implementer: Implementer,
    workspace: Path,
    grader: PhaseGrader,
    output_path: Path,
    *,
    base_revision: str,
    turn_budget: int,
    tool_call_budget: int,
    costs: Mapping[str, tuple[float | None, float | None]] | None = None,
) -> ChainRecord:
    """Run one chain and retain it durably -- HP2, HP5 and HP6 composed the
    way a real driver must, since nothing else in this repository does.

    Wires one ``BoundaryObserver`` for both HP5's attribution (a snapshot per
    boundary) and HP6's retention (the raw event stream), the way every test
    that exercises both already has to -- this is that wiring, shipped once
    rather than copied per caller. ``executable_seam`` is never asked for: it
    is derived from ``implementer`` itself via ``route.is_executable_seam``,
    so a caller cannot mis-assert which seam a chain ran on.

    **Corrected 2026-09-10 (Sol).** The first version ran the whole chain --
    every phase, every grader call -- before writing anything durable, so a
    grader that raised on phase 2 lost phase 1's already-accepted evidence
    too. "Written before returning" is not "preserve before judging" when
    everything happens inside one un-persisted call. This version persists
    twice per phase and once more on any exit, success or not:

    1. At ``after_handoff``, before the grader is even called: the packet,
       the implementer's own reported result, and (new) the actual content
       of every file the implementer's window touched -- ``candidate_files``
       is not enough on its own to answer "what would a grader see"; this is
       that answer, captured while it still exists.
    2. The instant the grader returns for that phase (wrapped, not awaited
       from ``run_phases``'s return value, which does not exist until the
       whole chain is over): the decision lands on disk before the next
       phase's packet is even built.
    3. In a ``finally`` around the whole run: whatever is true at that point
       -- complete, or a partial chain with its last phase still a persisted
       candidate and no decision -- is what ``output_path`` holds.

    What this function does **not** do: materialize a workspace, apply a
    task's fixture, or decide a live run's budget or authorization. Those are
    a CLI driver's job, not retention's, and none exists yet for the packet
    route -- the HP7 pre-run record names that gap. It also does not compose
    HP3's chained isolation (a different repository, ``satyrn-engine``) --
    the workspace here is one plain directory across the whole chain, not a
    sequence of isolated candidates, and that gap is named, not hidden, in
    the HP7 pre-run record.
    """
    events: list[BoundaryEvent] = []
    records: list[tuple[str, str, Snapshot]] = []
    packets_by_step: dict[str, HandoffPacket] = {}
    results_by_step: dict[str, ImplementerResult] = {}
    graded: dict[str, tuple[bool, str]] = {}
    snapshots_by_step: dict[str, tuple[str, str]] = {}
    order: list[str] = []
    seam = is_executable_seam(implementer)
    evidence_dir = output_path.with_name(output_path.stem + "-evidence")

    def persist_partial() -> ChainRecord:
        reported = {s: r.changed_files for s, r in results_by_step.items()}
        ledger = attribute(records, reported)
        attribution_by_step = {p.step_id: p for p in ledger.phases}
        phases: list[PhaseRecord] = []
        for step_id in order:
            if step_id not in results_by_step:
                continue  # opened, no candidate yet -- nothing to retain
            attribution = attribution_by_step.get(step_id)
            implementer_mutations = (
                None if attribution is None else attribution.implementer
            )
            accepted, reason = graded.get(step_id, (None, None))
            snap_path, snap_digest = snapshots_by_step.get(step_id, (None, None))
            implementer_cost, orchestrator_cost = (costs or {}).get(
                step_id, (None, None)
            )
            phases.append(
                PhaseRecord(
                    step_id=step_id,
                    packet=packets_by_step[step_id],
                    result=results_by_step[step_id],
                    accepted=accepted,
                    reason=reason,
                    implementer_mutations=implementer_mutations,
                    orchestrator_mutations=(
                        None if attribution is None else attribution.orchestrator
                    ),
                    declaration_ledger=declaration_ledger(
                        executable_seam=seam,
                        packet=packets_by_step[step_id],
                        implementer_mutations=implementer_mutations,
                    ),
                    candidate_snapshot_path=snap_path,
                    candidate_snapshot_digest=snap_digest,
                    implementer_cost=implementer_cost,
                    orchestrator_cost=orchestrator_cost,
                )
            )
        final_decision = next(
            (e.decision for e in events if e.boundary == "chain_end"), None
        )
        record = ChainRecord(
            version=CHAIN_RECORD_VERSION,
            phases=tuple(phases),
            final_decision=final_decision,
        )
        write_chain_record(output_path, record)
        return record

    def capture_candidate(step_id: str) -> None:
        """Everything the implementer's own window changed, as text content
        -- read now, because grading, cleanup, or a later phase can each
        change or remove it before anyone asks again. Binary content is out
        of scope here (read with ``surrogateescape``, which round-trips
        arbitrary bytes through ``str`` losslessly for retention purposes,
        but is not meant to be read as text by a consumer expecting one)."""
        before_snap = next(
            snap for sid, boundary, snap in reversed(records)
            if sid == step_id and boundary == "before_handoff"
        )
        after_snap = records[-1][2]
        mutations = diff_snapshots(before_snap, after_snap)
        content = {
            m.path: (workspace / m.path).read_text(
                encoding="utf-8", errors="surrogateescape"
            )
            for m in mutations
            if m.kind != "deleted" and (workspace / m.path).is_file()
        }
        payload = json.dumps(content, indent=2, sort_keys=True) + "\n"
        path = evidence_dir / f"{step_id}-candidate.json"
        _write_text_durably(path, payload)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        snapshots_by_step[step_id] = (str(path), digest)

    def observe(event: BoundaryEvent) -> None:
        events.append(event)
        records.append((event.step_id, event.boundary, snapshot(workspace)))
        if event.boundary == "before_handoff":
            packets_by_step[event.step_id] = event.packet
            if event.step_id not in order:
                order.append(event.step_id)
        elif event.boundary == "after_handoff":
            assert event.result is not None
            results_by_step[event.step_id] = event.result
            capture_candidate(event.step_id)  # candidate evidence --
            persist_partial()  # -- durable before grading runs
        elif event.boundary == "chain_end" and event.decision is not None:
            # The refusal and crash exit paths never call the grader, so
            # their decision is only ever seen here, not through
            # `instrumented_grader` below.
            graded[event.decision.step_id] = (
                event.decision.accepted, event.decision.reason
            )
            persist_partial()

    def instrumented_grader(step_id: str, ws: Path) -> tuple[str, str]:
        verdict, reason = grader(step_id, ws)
        # The one moment this phase's real verdict exists: before
        # `run_phases` decides whether to build the next packet or return,
        # and long before its own return value reaches this function.
        graded[step_id] = (verdict == "pass", reason)
        persist_partial()
        return verdict, reason

    try:
        run_phases(
            task_dir, manifest, spec, implementer, workspace,
            instrumented_grader, base_revision=base_revision,
            turn_budget=turn_budget, tool_call_budget=tool_call_budget,
            observer=observe,
        )
    finally:
        record = persist_partial()
    return record


@dataclass(frozen=True, slots=True)
class ChainFinding:
    """One thing ``check_chain`` found wrong with a retained record."""

    step_id: str
    reason: str


def check_chain(record: ChainRecord) -> tuple[ChainFinding, ...]:
    """Findings a retained chain record exposes on its own -- no re-run.

    Five kinds, and only five, because widening this into a pathology
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
    - a phase with retained mutations but no candidate snapshot, **when this
      record demonstrably retains candidate snapshots elsewhere** (any phase
      with one at all). A record built by the lower-level
      ``build_chain_record`` never captures snapshots and is not held to a
      standard it never claimed; a record built by
      ``run_and_record_chain``, which does, should have one for every phase
      that has mutations to explain, and a phase missing one despite that is
      the "missing worker evidence" case Sol asked to see rejected.
    - a phase that is not yet graded (``phase.graded`` is ``False``) --
      informational, not necessarily wrong (a live run interrupted
      mid-grading is expected to show this), but a reader must be told
      rather than left to notice ``accepted is None`` unaided.

    A phase with a real, observed zero mutations is **not** a finding --
    that is the seed-221 shape HP5 exists to report, and conflating it with
    "nobody looked" is the one mistake this function exists to refuse
    (HP6.6).
    """
    findings: list[ChainFinding] = []
    retains_candidates = any(
        phase.candidate_snapshot_path is not None for phase in record.phases
    )
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
        if (
            retains_candidates
            and phase.implementer_mutations
            and phase.candidate_snapshot_path is None
        ):
            findings.append(
                ChainFinding(
                    phase.step_id,
                    "phase has retained mutations but no candidate snapshot",
                )
            )
        if not phase.graded:
            findings.append(
                ChainFinding(phase.step_id, "phase candidate persisted but not yet graded")
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

    A phase with no decision yet (``phase.graded`` is ``False`` -- a
    candidate persisted while grading was in flight or never reached) is
    excluded: there is no ``PhaseDecision`` to read back for one, by
    definition, and a caller comparing this against ``run_phases``'s own
    return value for a completed run will never see one there either.
    """
    return [
        PhaseDecision(phase.step_id, phase.accepted, phase.reason, phase.result)
        for phase in record.phases
        if phase.graded
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
        "candidate_snapshot_path",
        "candidate_snapshot_digest",
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
        "candidate_snapshot_path": phase.candidate_snapshot_path,
        "candidate_snapshot_digest": phase.candidate_snapshot_digest,
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
    if accepted is not None and not isinstance(accepted, bool):
        raise ChainRecordError("persisted phase accepted must be a bool or null")
    if reason is not None and not isinstance(reason, str):
        raise ChainRecordError("persisted phase reason must be a string or null")
    for name in ("candidate_snapshot_path", "candidate_snapshot_digest"):
        value = data[name]
        if value is not None and not isinstance(value, str):
            raise ChainRecordError(f"persisted phase {name} must be a string or null")
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
        candidate_snapshot_path=data["candidate_snapshot_path"],
        candidate_snapshot_digest=data["candidate_snapshot_digest"],
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
