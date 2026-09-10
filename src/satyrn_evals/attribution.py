"""HP5: which role changed each file in a completed chain.

Attribution is **observed, never reported**. ``ImplementerResult`` carries
what an implementer *says* it changed, and the route already refuses to treat
that claim as a verdict. A silent implementer naming three files it never
wrote is the exact failure this module exists to catch, so a ledger built
from its claims would report the incident as healthy. Everything counted here
comes from workspace state the harness observed on both sides of a hand-off.

The module observes and never gates. A chain that passes with zero
implementer mutations still passes; the record says both things.
"""

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

type Snapshot = Mapping[str, str]
"""Workspace-relative path to a digest of that path's content."""

type MutationKind = Literal["created", "deleted", "modified"]

#: Files the harness itself writes into a worker's workspace. They are the
#: seam's own bookkeeping, not anybody's mutation, and they are listed by
#: name rather than matched by a pattern so that adding one is a visible
#: decision. ``.satyrn-packet.json`` and ``.satyrn-result.json`` are written
#: by ``route.command_implementer``; ``.phase-counter`` by the executable
#: fake, which stands in for a worker that tracks its own position. The
#: remaining three are the real Pi implementer adapter's own
#: (``adapters/pi_implementer.py``) -- ``.satyrn-implementer-transcript.jsonl``
#: and ``.satyrn-implementer-stderr.log``, each appended to once per phase
#: rather than named per phase, since this set matches exact relative paths
#: and not a pattern; and ``.satyrn-implementer-call-counter``, its own
#: position-tracker, the same shape as ``.phase-counter``. All three are
#: retained evidence, never a mutation to attribute to either role.
HARNESS_FILES: frozenset[str] = frozenset(
    {
        ".satyrn-packet.json",
        ".satyrn-result.json",
        ".phase-counter",
        ".satyrn-implementer-transcript.jsonl",
        ".satyrn-implementer-stderr.log",
        ".satyrn-implementer-call-counter",
    }
)


@dataclass(frozen=True, slots=True)
class Mutation:
    """One path whose observed content differs across a window.

    Not a line count and not a diff size. The seed-221 shape is a count of
    zero, and zero is unambiguous whatever the unit; a richer measure invites
    a threshold, and a threshold is a budget verdict that ``BACKLOG.md``
    defers on its own merits.
    """

    path: str
    kind: MutationKind


def snapshot(workspace: Path, *, skip: Iterable[str] = HARNESS_FILES) -> Snapshot:
    """Digest every file under ``workspace``, skipping harness bookkeeping.

    Content is compared by digest rather than by size or mtime: an edit that
    keeps a file's length is still a mutation, and a chain replayed quickly
    enough can leave two different trees sharing a timestamp.
    """
    skipped = frozenset(skip)
    digests: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(workspace).as_posix()
        if name in skipped:
            continue
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def diff_snapshots(before: Snapshot, after: Snapshot) -> tuple[Mutation, ...]:
    """The mutations between two snapshots, path-ordered."""
    mutations: list[Mutation] = []
    for name in sorted(set(before) | set(after)):
        match (name in before, name in after):
            case (False, True):
                mutations.append(Mutation(name, "created"))
            case (True, False):
                mutations.append(Mutation(name, "deleted"))
            case _ if before[name] != after[name]:
                mutations.append(Mutation(name, "modified"))
            case _:
                pass
    return tuple(mutations)


@dataclass(frozen=True, slots=True)
class PhaseAttribution:
    """Who changed what during one phase, and what the implementer claimed.

    ``implementer`` and ``orchestrator`` are ``None`` when that window was
    never observed, which is **not** the same finding as an observed zero. A
    ``0`` that means "we did not look" is the 2026-09-08 detached-worker gap
    in a new place, and the two are kept apart at the type level so a reader
    cannot conflate them by accident.
    """

    step_id: str
    implementer: tuple[Mutation, ...] | None
    orchestrator: tuple[Mutation, ...] | None
    reported: tuple[str, ...]

    @property
    def claimed_not_made(self) -> tuple[str, ...]:
        """Paths the implementer reported that its window does not show.

        Stated, never classified. What a discrepancy *means* is a pathology
        judgment, and this cycle excludes those.
        """
        if self.implementer is None:
            return ()
        observed = {mutation.path for mutation in self.implementer}
        return tuple(p for p in self.reported if p not in observed)

    @property
    def made_not_claimed(self) -> tuple[str, ...]:
        """Paths the implementer's window shows that it did not report."""
        if self.implementer is None:
            return ()
        return tuple(
            m.path for m in self.implementer if m.path not in set(self.reported)
        )


@dataclass(frozen=True, slots=True)
class ChainLedger:
    """Every phase's attribution, plus totals recomputed from them."""

    phases: tuple[PhaseAttribution, ...]

    def _total(self, role: str) -> int | None:
        counts = [getattr(phase, role) for phase in self.phases]
        if any(c is None for c in counts):
            return None
        return sum(len(c) for c in counts)

    @property
    def implementer_mutations(self) -> int | None:
        """``None`` when any phase's implementer window went unobserved."""
        return self._total("implementer")

    @property
    def orchestrator_mutations(self) -> int | None:
        return self._total("orchestrator")

    @property
    def unobserved_phases(self) -> tuple[str, ...]:
        return tuple(
            p.step_id
            for p in self.phases
            if p.implementer is None or p.orchestrator is None
        )


def attribute(
    boundaries: Iterable[tuple[str, str, Snapshot]],
    reported: Mapping[str, tuple[str, ...]],
) -> ChainLedger:
    """Build the ledger from recorded boundary snapshots.

    ``boundaries`` is the sequence a ``BoundaryObserver`` recorded: for each
    entry, the step id, the boundary name, and the snapshot taken there. The
    windows follow from the order, not from anybody's account of it:

    - the **implementer window** is a phase's ``before_handoff`` to its own
      ``after_handoff``;
    - the **orchestrator window** is a phase's ``after_handoff`` to the next
      ``before_handoff``, or to ``chain_end`` for the last phase.

    A window missing either end is ``None`` -- unobserved, not zero. A window
    recorded twice for the same step is **refused**: silently keeping the
    later snapshot would report a number computed from an arbitrary half of
    the evidence, which is worse than saying the recording is malformed.
    """
    records = list(boundaries)
    opens: dict[str, Snapshot] = {}
    closes: dict[str, Snapshot] = {}
    order: list[str] = []
    end: Snapshot | None = None
    for step_id, boundary, taken in records:
        match boundary:
            case "before_handoff":
                if step_id in opens:
                    raise ValueError(
                        f"step {step_id!r} opened twice; a repeated window "
                        "makes attribution ambiguous rather than richer"
                    )
                order.append(step_id)
                opens[step_id] = taken
            case "after_handoff":
                if step_id in closes:
                    raise ValueError(
                        f"step {step_id!r} closed twice; a repeated window "
                        "makes attribution ambiguous rather than richer"
                    )
                closes[step_id] = taken
            case "chain_end":
                end = taken
            case _:
                raise ValueError(f"unknown boundary: {boundary!r}")

    phases: list[PhaseAttribution] = []
    for index, step_id in enumerate(order):
        before, after = opens.get(step_id), closes.get(step_id)
        implementer = (
            None if before is None or after is None
            else diff_snapshots(before, after)
        )
        following = order[index + 1] if index + 1 < len(order) else None
        next_open = opens.get(following) if following is not None else end
        orchestrator = (
            None if after is None or next_open is None
            else diff_snapshots(after, next_open)
        )
        phases.append(
            PhaseAttribution(
                step_id, implementer, orchestrator, reported.get(step_id, ())
            )
        )
    return ChainLedger(tuple(phases))
