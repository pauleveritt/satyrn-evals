"""Committed arm definitions, read as executable inputs.

An arm file states the exact command surface one arm runs under: the argv
prefix, the tool surface, the model in both naming forms, and the pins a
preflight re-verifies. Reading it here — rather than restating it in a
script and again in a document — is what keeps the file from becoming
parallel documentation that drifts from what actually ran.

**Two files and one reader, deliberately.** `CLAUDE.md`: no framework
before three concrete implementations need the same shape. There is no
registry, no discovery, and no plugin point; a caller names a path.

**The tool surface is a predeclared confound.** Baseline holds
`read,bash,edit,write`; Engine holds `read,edit` and wraps its prompt with
its own handoff builder (`satyrn-engine` `build_pi_command`, pinned at
commit `75d4863`). Any comparison between the two is meaningful only as
"the shipped Engine versus bare Pi as shipped" — a product-level
comparison that supports no sentence about a mechanism.
"""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from satyrn_evals.errors import UsageError

type ArmName = Literal["baseline", "baseline-compaction", "envelope", "engine"]
#: ``baseline-compaction`` is **historical**. It named the arm of the
#: 2026-09-05 compaction probe, run while ``baseline`` still declared a
#: 262,144 context window; the name kept those cells from pooling with
#: cells that ran with compaction unreachable. Since the window was
#: corrected for every arm, ``baseline`` *is* the compacting
#: configuration and no arm file carries this name. It stays in the
#: vocabulary so the probe's schedule remains readable — deleting it
#: would make a recorded batch unloadable to make a tidier enum.

#: The pi tool names an arm file may name. pi 0.84.4 accepts these four
#: through `--tools`; an unknown name is an authoring error that would
#: otherwise reach the model as a silently dropped capability.
KNOWN_TOOLS: frozenset[str] = frozenset({"read", "bash", "edit", "write"})

#: The two Engine sources whose bytes the Engine arm pins. They are the
#: two `--extension` files `satyrn-engine`'s `build_pi_command` hands pi.
ENGINE_SOURCES: tuple[str, ...] = ("engine.ts", "mutator.ts")

_COMMIT_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")


class ArmError(UsageError):
    """Exit 2: an arm file is missing a pin or names something unknown."""


@dataclass(frozen=True, slots=True)
class ArmPins:
    """What a preflight re-verifies before the first cell of a batch."""

    pi: str
    engine_commit: str | None
    digests: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Arm:
    """One committed arm definition."""

    arm: ArmName
    argv: tuple[str, ...]
    tools: tuple[str, ...]
    #: The pi-facing model string, `omlx/<id>`.
    model: str
    #: The bare id the omlx server advertises. Both surfaces are recorded
    #: because they differ, and a preflight talks to the server.
    server_model: str
    pins: ArmPins


def _arm_name(raw: str, source: Path) -> ArmName:
    """The arm identity, narrowed to the arms this phase defines."""
    match raw:
        case "baseline" | "baseline-compaction" | "envelope" | "engine":
            return raw
        case _:
            raise ArmError(f"{source}: unknown arm {raw!r}")


def _require_str(data: Mapping[str, object], key: str, source: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ArmError(f"{source}: {key} must be a non-empty string")
    return value


def _require_list(data: Mapping[str, object], key: str, source: Path) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise ArmError(f"{source}: {key} must be a non-empty list")
    if any(not isinstance(item, str) or not item for item in value):
        raise ArmError(f"{source}: {key} must hold non-empty strings")
    return list(value)


def _load_pins(raw: object, arm: ArmName, source: Path) -> ArmPins:
    """The pin block, validated against what this arm can actually pin.

    Baseline pins pi alone; Engine additionally pins the commit and the
    bytes of the two extension sources. A pin that cannot apply to the
    arm is refused rather than ignored: preflight would otherwise verify
    an engine checkout the Baseline arm never launches.
    """
    if not isinstance(raw, dict):
        raise ArmError(f"{source}: pins must be an object")
    pi = _require_str(raw, "pi", source)
    commit = raw.get("engine_commit")
    digests = raw.get("digests", {})
    if not isinstance(digests, dict) or any(
        not isinstance(value, str) for value in digests.values()
    ):
        raise ArmError(f"{source}: pins.digests must map a name to a digest string")
    if arm == "engine":
        if not isinstance(commit, str) or not _COMMIT_SHA.match(commit):
            raise ArmError(
                f"{source}: pins.engine_commit must be a 40-hex commit sha, "
                f"got {commit!r}"
            )
        for name in ENGINE_SOURCES:
            if (digest := digests.get(name)) is None:
                raise ArmError(f"{source}: pins.digests is missing {name}")
            if not _SHA256.match(digest):
                raise ArmError(
                    f"{source}: pins.digests[{name!r}] must be a 64-hex "
                    f"sha256, got {digest!r}"
                )
    else:
        if commit is not None:
            raise ArmError(
                f"{source}: the baseline arm launches no engine; "
                "pins.engine_commit must be null"
            )
        if digests:
            raise ArmError(
                f"{source}: the baseline arm pins no sources; "
                "pins.digests must be empty"
            )
    return ArmPins(pi=pi, engine_commit=commit, digests=dict(digests))


def load_arm(path: Path) -> Arm:
    """Read one committed arm file, refusing anything under-specified.

    Every field is required. An arm file that loads is one a preflight can
    verify in full; there is no partially pinned arm.
    """
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ArmError(f"{source}: an arm file must be a JSON object")
    arm_name = _arm_name(_require_str(data, "arm", source), source)
    tools = _require_list(data, "tools", source)
    if unknown := sorted(set(tools) - KNOWN_TOOLS):
        raise ArmError(f"{source}: unknown tool name(s) {', '.join(unknown)}")
    model = _require_str(data, "model", source)
    server_model = _require_str(data, "server_model", source)
    if not model.endswith(f"/{server_model}"):
        raise ArmError(
            f"{source}: model {model!r} does not address server_model {server_model!r}"
        )
    if "pins" not in data:
        raise ArmError(f"{source}: pins is required")
    return Arm(
        arm=arm_name,
        argv=tuple(_require_list(data, "argv", source)),
        tools=tuple(tools),
        model=model,
        server_model=server_model,
        pins=_load_pins(data["pins"], arm_name, source),
    )


def build_argv(arm: Arm) -> list[str]:
    """The attempt command Evals invokes for this arm.

    The model is always two tokens. pi 0.84.4's hand-rolled parser matches
    the literal token `--model` and records `--model=VALUE` as an unknown
    flag; that defect cost the V8 smoke a run and is what engine commit
    `75d4863` fixed. Evals never builds the equals form.
    """
    if not arm.model:
        raise ArmError(f"arm {arm.arm!r} has no model; cannot build argv")
    match arm.arm:
        case "baseline" | "baseline-compaction" | "envelope":
            # Baseline and Baseline-compaction differ only in pi's own
            # configuration, which is why that difference is pinned in the
            # arm record and checked by preflight rather than passed on the
            # command line. Envelope is bare pi run against Engine's own
            # tool surface, so it is the same in-tree pi adapter as
            # Baseline; its argv is Baseline's argv with a different
            # `--tools` value, and for these arms the tool surface really
            # is passed on the command line (unlike the engine arm below,
            # where it is recorded only).
            return [*arm.argv, "--model", arm.model, "--tools", ",".join(arm.tools)]
        case "engine":
            # `satyrn-engine attempt` takes --model and a contract path;
            # its tool surface is fixed inside build_pi_command, so the
            # arm file records it for the record, not for the argv.
            return [*arm.argv, "--model", arm.model]
        case _:
            # `Arm` is a public frozen dataclass a caller can build by
            # hand; an unrecognized arm must never yield an argv that
            # silently drops the tool surface.
            raise ArmError(f"unknown arm {arm.arm!r}; cannot build argv")
