"""The handoff packet: one bounded request to one implementer.

HP1's data contract and nothing else — no I/O, no building, no rendering.
The field set is mapped from SwiftStar's exercised `HandoffPacket`
(`Sources/SwiftStarKit/HandoffPacket.swift:62-90`), with three deliberate
departures recorded in the HP1 design spec:

* **No parent validation command.** Sourcing one from a task's ``oracle``
  would put the hidden oracle hook into a document the implementer reads,
  which `manifest.py`'s ``_validate_public_suite`` already refuses for the
  public suite. Acceptance is decided by hidden per-phase grading the packet
  never names. A field that is always empty is a declaration the runtime does
  not apply, so the field is absent rather than ``None``.
* **No ``sampling``.** Recording a declared setting the runtime does not send
  is a capture-integrity defect SwiftStar names against itself
  (`PoolOrchestrator.swift:70-78`). Nothing here applies one.
* **No ``baselines``.** They need a revision to be read against, which
  arrives with HP3's chained checkouts; reading them here would also make the
  builder impure.

``facts`` emptiness is **not** refused here. The spec states that rule once,
on the builder (slice 3), so the two cannot drift apart.
"""

import json
import math
import shlex
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

import yaml

from satyrn_evals.contamination import scan_texts
from satyrn_evals.engine_contract import writable_paths
from satyrn_evals.errors import PacketError
from satyrn_evals.manifest import ORACLE_HOOK_PLUGIN, TaskManifest
from satyrn_evals.overlay import OverlaySpec
from satyrn_evals.session_manifest import SessionSpec

type PacketRole = Literal["implement"]
"""One member, because this path has one role. A second arrives with a
second implementation, not before."""

type PacketCommand = tuple[str, ...] | None
"""``None`` means the task offers no such command; ``()`` is refused. The
manifest spells absence ``()``, and this type deliberately differs: a packet
must distinguish "no command exists" from "a command that runs nothing"."""

PACKET_VERSION: int = 1
"""Schema version, so a persisted packet replays rather than silently
decoding under a shape it was not written for."""

_STRING_SEQUENCES = ("facts", "preserve", "writable_paths", "redacts")

# `__value__` is the TypeAliasType accessor: it unwraps `type X = ...` to the
# Literal underneath, so the alias stays the single source of the role names.
_ROLES: frozenset[str] = frozenset(get_args(PacketRole.__value__))
"""The alias is the single source of the role names; a second member is added
there and this set follows, so the two cannot disagree."""


def _check_text(name: str, value: object) -> None:
    match value:
        case str() as text if text.strip():
            return
        case _:
            raise PacketError(f"{name} must be non-empty text: {value!r}")


def _check_string_sequence(name: str, value: object) -> None:
    match value:
        case str():
            # A bare string is iterable, so it would pass a naive check and
            # then behave as a sequence of characters.
            raise PacketError(f"{name} must be a tuple of strings, not a string")
        case tuple() as entries if all(
            isinstance(e, str) and e.strip() for e in entries
        ):
            return
        case _:
            raise PacketError(f"{name} must be a tuple of non-blank strings")


def _check_command(name: str, value: object) -> None:
    match value:
        case None:
            return
        case str():
            raise PacketError(f"{name} must be a tuple of argv tokens, not a string")
        case tuple() as tokens if tokens and all(
            isinstance(t, str) and t.strip() for t in tokens
        ):
            return
        case _:
            raise PacketError(f"{name} must be a non-empty tuple of argv tokens")


def _check_budget(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PacketError(f"{name} must be a positive integer: {value!r}")


def _check_deadline(value: object) -> None:
    """A deadline is optional; when present it is a positive finite number."""
    if value is None:
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise PacketError(
            f"deadline_seconds must be a positive finite number or null: "
            f"{value!r}"
        )


@dataclass(frozen=True, slots=True)
class HandoffPacket:
    """One inspected request: what to do, what is pinned, what may be touched."""

    objective: str
    facts: tuple[str, ...]
    base_revision: str
    writable_paths: tuple[str, ...]
    preserve: tuple[str, ...]
    self_test_command: PacketCommand
    redacts: tuple[str, ...]
    turn_budget: int
    tool_call_budget: int
    deadline_seconds: float | None = None
    role: PacketRole = "implement"
    version: int = PACKET_VERSION

    def __post_init__(self) -> None:
        if self.version != PACKET_VERSION:
            raise PacketError(
                f"unknown packet version {self.version!r}; this build writes "
                f"and reads version {PACKET_VERSION}"
            )
        if self.role not in _ROLES:
            raise PacketError(f"unknown packet role: {self.role!r}")
        _check_text("objective", self.objective)
        _check_text("base_revision", self.base_revision)
        for name in _STRING_SEQUENCES:
            _check_string_sequence(name, getattr(self, name))
        _check_command("self_test_command", self.self_test_command)
        _check_budget("turn_budget", self.turn_budget)
        _check_budget("tool_call_budget", self.tool_call_budget)
        _check_deadline(self.deadline_seconds)


def build_packet(
    task_dir: Path,
    manifest: TaskManifest,
    spec: SessionSpec,
    step_id: str,
    *,
    base_revision: str,
    turn_budget: int,
    tool_call_budget: int,
    deadline_seconds: float | None = None,
    role: PacketRole = "implement",
) -> HandoffPacket:
    """One inspected packet for one session step.

    **Deterministic, not pure.** No clock, no randomness and no environment
    read, so slice 5's golden packet is reproducible and a difference between
    two packets is a difference in the task. It is not side-effect free:
    ``writable_paths`` probes ``base/`` on disk to decide whether an entry is
    a directory, so the result depends on the task tree as well as on the
    arguments. *(Corrected after review, which caught the spec and plan both
    claiming purity.)*

    ``facts`` is required here and optional in the loader. The rule lives in
    exactly one place so the two cannot drift: a spec written before the key
    existed still loads, and a packet built from a step that pins nothing is
    refused.

    ``writable_paths`` is reused from the Engine contract renderer rather
    than reimplemented, and is handed the manifest's own ``source_dirs``
    declaration. **HP4 closed the gap this docstring used to record:** the
    renderer probed ``base/`` and an absent path rendered as an exact
    filename, so on an empty skeleton the declared scope and the enforced
    scope disagreed about ``templates/base.html``. A declaring manifest now
    renders the directory pattern. What remains, deliberately, is that
    ``patch.within_source`` also admits the bare path ``templates`` and the
    declaration does not; the invariant this builder relies on is
    one-directional, that declared never exceeds enforced.
    """
    steps = {step.id: step for step in spec.steps}
    if (step := steps.get(step_id)) is None:
        raise PacketError(
            f"unknown step {step_id!r}; this spec declares "
            f"{', '.join(sorted(steps))}"
        )
    for token in spec.self_test_command or ():
        # Second line, at the boundary that actually produces the leak. The
        # authoring check in `session_manifest.assert_no_overlay_names` fires
        # first, but only for a caller that runs it; the packet is what
        # carries the string to an implementer.
        if ORACLE_HOOK_PLUGIN in token:
            raise PacketError(
                f"self_test_command names {ORACLE_HOOK_PLUGIN!r}: a packet "
                "must not hand the implementer the hidden oracle"
            )
    if not step.facts:
        raise PacketError(
            f"step {step_id!r} pins no facts; a packet that leaves the "
            "project's decisions unstated makes the implementer re-derive them"
        )
    position = next(i for i, s in enumerate(spec.steps) if s.id == step_id)
    earlier = tuple(s.prompt for s in spec.steps[:position])
    # Every step's selectors, not only this step's. The plan said "the
    # step's"; widening is deliberate and recorded here — a packet for phase 1
    # must not leak phase 3's hidden checks either, and a later phase's
    # selectors are exactly what a forward-looking implementer might guess at.
    redacts = tuple(
        dict.fromkeys(
            [sel for s in spec.steps for sel in s.new_feature_selectors]
            + ([manifest.grader_overlay] if manifest.grader_overlay else [])
        )
    )
    return HandoffPacket(
        objective=step.prompt,
        facts=step.facts,
        base_revision=base_revision,
        writable_paths=writable_paths(
            task_dir, manifest.source_paths, manifest.source_dirs
        ),
        preserve=earlier,
        self_test_command=spec.self_test_command,
        redacts=redacts,
        turn_budget=turn_budget,
        tool_call_budget=tool_call_budget,
        deadline_seconds=deadline_seconds,
        role=role,
    )


RENDERED_FIELDS: tuple[str, ...] = (
    "objective",
    "facts",
    "preserve",
    "writable_paths",
    "self_test_command",
)
"""Exactly what an implementer sees. Enumerated because three gates depend on
it. ``redacts`` is **not** here: a packet that printed its own forbidden
strings would refuse itself. ``role``, ``version`` and the budgets are
metadata, not instructions."""


def _render_blocks(get: Callable[[str], object]) -> str:
    """Build the rendered text for exactly ``RENDERED_FIELDS``, from any
    getter -- an attribute lookup on a real ``HandoffPacket``, or a plain
    ``dict.get`` on a worker's JSON projection. The two differ only in
    whether a sequence field arrives as a ``tuple`` or a JSON ``list``, which
    is why both are matched below rather than only ``tuple``.
    """
    blocks: list[str] = []
    for name in RENDERED_FIELDS:
        match get(name):
            case None:
                continue
            case str() as text:
                blocks.append(f"## {name}\n\n{text}")
            case (tuple() | list()) as argv if argv and name == "self_test_command":
                # An argv rendered one token per bullet is not a command. The
                # implementer needs something runnable, so it is joined with
                # shell quoting rather than listed.
                blocks.append(f"## {name}\n\n    {shlex.join(argv)}")
            case (tuple() | list()) as entries if entries:
                body = "\n".join(f"- {entry}" for entry in entries)
                blocks.append(f"## {name}\n\n{body}")
            case _:
                continue
    return "\n\n".join(blocks) + "\n"


def render_packet(packet: HandoffPacket) -> str:
    """The text an implementer receives, for exactly ``RENDERED_FIELDS``."""
    return _render_blocks(lambda name: getattr(packet, name))


def contract_yaml(packet: HandoffPacket, contract_id: str) -> str:
    """One phase's ``HandoffPacket``, rendered as a ``satyrn-engine``
    Contract (``id``, ``task``, ``writable_paths``, ``test_command``) --
    the only four fields that format understands. ``task`` reuses
    ``render_packet`` verbatim rather than a second rendering: the model
    sees the same words whether this packet crosses as a worker
    projection (HP2's seam) or a Contract (HP3's composed seam).
    ``redacts``, ``role`` and the two budgets do not cross -- ``redacts``
    especially must not, the same boundary the worker projection already
    enforces.

    Emitted with a real YAML library, not hand-assembled text: ``task`` is
    arbitrary prose (facts, objective text) that can contain colons,
    quotes and newlines, any of which a naive emitter would get wrong
    silently.
    """
    return yaml.safe_dump(
        {
            "id": contract_id,
            "task": render_packet(packet),
            "writable_paths": list(packet.writable_paths),
            "test_command": list(packet.self_test_command or ()),
        },
        sort_keys=False,
    )


def render_projection(projection: Mapping[str, object]) -> str:
    """The same rendering, over a worker's own JSON projection.

    This is what a real implementer adapter actually calls
    (``adapters/pi_implementer.py``): a worker never holds a ``HandoffPacket``
    object, only what crossed the process boundary as
    ``worker_projection``'s JSON. ``render_packet`` above renders the same
    ``RENDERED_FIELDS`` from the pre-projection object, which is what the
    golden fixture and every analysis path already use; this exists so the
    text a real implementer reads is provably the same rendering, not a
    second, divergent one.

    **Corrected 2026-09-10, by the Astra-style acceptance review.** The first
    version refused only a non-``Mapping`` or an empty projection, so a
    projection missing ``objective`` -- corrupted, or from a packet builder
    bug -- rendered whatever fields it did have and launched an implementer
    on an instruction that says nothing about what to do. ``objective`` is
    the one field ``HandoffPacket.__post_init__`` itself refuses to be blank
    (``_check_text``); a worker-facing render must refuse the same way, not
    silently degrade.
    """
    if not isinstance(projection, Mapping):
        raise PacketError("worker projection must be a JSON object")
    if not projection:
        raise PacketError(
            "worker projection is empty: nothing to render, which is not "
            "the same as nothing to say"
        )
    objective = projection.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        raise PacketError(
            "worker projection is missing a non-blank objective: "
            f"{objective!r}"
        )
    return _render_blocks(lambda name: projection.get(name))


def worker_projection(packet: HandoffPacket) -> dict[str, object]:
    """The **only** packet data a worker may be handed, as plain JSON data.

    Exactly ``RENDERED_FIELDS``. It carries no ``redacts``, no
    ``base_revision``, no budgets and no role -- the first because those are
    the hidden selectors themselves, the rest because a worker has no use for
    the harness's bookkeeping and every field handed over is a field that can
    leak.

    Review found the first version of the executable seam writing
    ``packet_to_dict`` into the worker's own workspace, which put all 14
    redacted selectors in a file the worker can read. Filtering a prompt would
    not have helped: the file was there. The full packet is retained
    host-side; this is what crosses.
    """
    projected = {name: getattr(packet, name) for name in RENDERED_FIELDS}
    return {
        name: list(value) if isinstance(value, tuple) else value
        for name, value in projected.items()
    }


def assert_projection_is_clean(packet: HandoffPacket, projection: dict[str, object]) -> None:
    """Refuse a projection carrying anything the packet withholds.

    Checked on the serialized bytes rather than field by field, because the
    question is what the worker can read, not what we intended to send.
    """
    serialized = json.dumps(projection, sort_keys=True)
    if not serialized.strip() or serialized == "{}":
        raise PacketError(
            "worker projection is empty: nothing to check, which is not the "
            "same as nothing found"
        )
    if leaked := [secret for secret in packet.redacts if secret in serialized]:
        raise PacketError(
            f"worker projection carries {len(leaked)} redacted string(s): "
            f"{leaked[0]!r}"
        )


def assert_redactions_absent(
    packet: HandoffPacket, *, rendered: str | None = None
) -> None:
    """Refuse a packet whose rendered text carries a string it must withhold.

    Blank text is refused rather than passed. "No secret appeared" in a
    document with no content is an absence of signal, and reporting that as
    a pass is the shape of defect this repository has recorded four times.
    """
    text = render_packet(packet) if rendered is None else rendered
    if not text.strip():
        raise PacketError(
            "rendered packet is empty: nothing to check, which is not the "
            "same as nothing found"
        )
    if leaked := [secret for secret in packet.redacts if secret in text]:
        raise PacketError(
            f"rendered packet carries {len(leaked)} redacted string(s): "
            f"{leaked[0]!r}"
        )


def assert_overlay_absent_from_packet(
    packet: HandoffPacket, overlay: OverlaySpec, *, rendered: str | None = None
) -> None:
    """Refuse a packet naming a hidden grader file, and refuse an unmeasured check.

    This is a **second, complementary** check rather than a second matcher
    for the first: ``assert_redactions_absent`` compares the packet's own
    declared strings, while ``scan_texts`` looks for the overlay's real
    relative paths, which the packet never enumerates.

    *(The HP1 plan said this gate would reuse ``scan_texts`` "rather than a
    second matcher". That was written believing ``scan_texts`` matched
    arbitrary strings; it matches overlay paths only
    (``contamination.py:211-247``). The two checks have different jobs, and
    this docstring records the correction rather than quietly diverging from
    the plan.)*
    """
    text = render_packet(packet) if rendered is None else rendered
    result = scan_texts([("packet", text)], overlay)
    match result.outcome:
        case "clean":
            return
        case "unmeasured":
            # Unreachable through this function today, because `render_packet`
            # always returns text. Kept because `scan_texts` can return it and
            # an unmeasured check reported as clean is the recorded shape of
            # four silent-zero incidents; the test drives `scan_texts` directly.
            raise PacketError(  # pragma: no cover
                "overlay check is unmeasured: no text was scanned, "
                "and an unmeasured check is not a clean one"
            )
        case _:
            raise PacketError(
                f"rendered packet names a grader overlay path: "
                f"{result.evidence[0].overlay_path!r}"
            )


_PERSISTED_KEYS: frozenset[str] = frozenset(
    {
        "objective",
        "facts",
        "base_revision",
        "writable_paths",
        "preserve",
        "self_test_command",
        "redacts",
        "turn_budget",
        "tool_call_budget",
        "deadline_seconds",
        "role",
        "version",
    }
)


def packet_to_dict(packet: HandoffPacket) -> dict[str, object]:
    """A packet as plain JSON-ready data, for persistence and for the golden."""
    return {
        "objective": packet.objective,
        "facts": list(packet.facts),
        "base_revision": packet.base_revision,
        "writable_paths": list(packet.writable_paths),
        "preserve": list(packet.preserve),
        "self_test_command": (
            None if packet.self_test_command is None
            else list(packet.self_test_command)
        ),
        "redacts": list(packet.redacts),
        "turn_budget": packet.turn_budget,
        "tool_call_budget": packet.tool_call_budget,
        "deadline_seconds": packet.deadline_seconds,
        "role": packet.role,
        "version": packet.version,
    }


def _persisted_sequence(name: str, value: object) -> tuple[str, ...]:
    """A persisted list of strings, checked **before** conversion.

    ``tuple(value)`` is the trap this exists to avoid: a JSON string converts
    happily into a tuple of single characters, so ``"facts": "FastAPI"`` would
    load as seven one-letter facts and satisfy every constructor check. Review
    reproduced exactly that, plus a ``None`` that raised a raw ``TypeError``
    instead of a ``PacketError``.
    """
    match value:
        case list() as entries if all(isinstance(e, str) for e in entries):
            return tuple(entries)
        case _:
            raise PacketError(f"persisted {name} must be a list of strings")


def packet_from_dict(data: dict[str, object]) -> HandoffPacket:
    """Load a persisted packet, refusing a malformed one as itself.

    Every field's **JSON shape** is checked before conversion, then the
    constructor re-checks the packet's own rules. Without the first pass a
    persisted packet bypasses the second: conversion would silently coerce
    the wrong type into a well-formed value.
    """
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise PacketError(f"persisted version must be an integer: {version!r}")
    if version != PACKET_VERSION:
        raise PacketError(
            f"unknown packet version {version!r}; this build reads "
            f"version {PACKET_VERSION}"
        )
    if missing := sorted(_PERSISTED_KEYS - set(data)):
        raise PacketError(f"persisted packet is missing {', '.join(missing)}")
    for name in ("objective", "base_revision", "role"):
        if not isinstance(data[name], str):
            raise PacketError(f"persisted {name} must be a string")
    for name in ("turn_budget", "tool_call_budget"):
        if not isinstance(data[name], int) or isinstance(data[name], bool):
            raise PacketError(f"persisted {name} must be an integer")
    deadline = data["deadline_seconds"]
    if deadline is not None and (
        isinstance(deadline, bool) or not isinstance(deadline, (int, float))
    ):
        raise PacketError("persisted deadline_seconds must be a number or null")
    command = data["self_test_command"]
    return HandoffPacket(
        objective=data["objective"],  # type: ignore[arg-type]
        facts=_persisted_sequence("facts", data["facts"]),
        base_revision=data["base_revision"],  # type: ignore[arg-type]
        writable_paths=_persisted_sequence(
            "writable_paths", data["writable_paths"]
        ),
        preserve=_persisted_sequence("preserve", data["preserve"]),
        self_test_command=(
            None
            if command is None
            else _persisted_sequence("self_test_command", command)
        ),
        redacts=_persisted_sequence("redacts", data["redacts"]),
        turn_budget=data["turn_budget"],  # type: ignore[arg-type]
        tool_call_budget=data["tool_call_budget"],  # type: ignore[arg-type]
        deadline_seconds=deadline,  # type: ignore[arg-type]
        role=data["role"],  # type: ignore[arg-type]
    )
