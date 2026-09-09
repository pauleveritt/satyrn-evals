"""HP2: run one workload's ordered requests against a bounded implementer.

The implementer is a **callable** here, and the executable that a live run
drives is adapted to it by ``command_implementer``. That is this repository's
existing shape rather than a new one: the attempt path, the session executor,
the Pi adapter and the grader each keep an executable as the public parameter
and an in-process double at an internal boundary (``adapters/pi_session.py``
``_PiHandle``/``_serve`` is the closest analogue). The result crosses the
process boundary as a document, so the default tier tests the wire contract
on the same bytes a real process writes.

What this module does **not** do: apply patches (every applier here is
``git apply``, which the default tier's tripwire forbids), decide verdicts
(``SessionGrader`` does), or enforce scope with a new rule
(``patch.within_source`` does, and it is pure).
"""

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from satyrn_evals.errors import RouteError
from satyrn_evals.manifest import TaskManifest
from satyrn_evals.packet import HandoffPacket, build_packet, packet_to_dict
from satyrn_evals.patch import within_source
from satyrn_evals.session_manifest import SessionSpec

type ReportedOutcome = Literal["delivered", "refused"]
type Implementer = Callable[[HandoffPacket], "ImplementerResult"]
type PhaseGrader = Callable[[str, Path], tuple[str, str]]
"""``(step_id, workspace) -> (verdict, reason)``. The route never computes a
verdict itself; the default tier scripts this and the integration tier passes
the real ``SessionGrader``."""

RESULT_VERSION: int = 1

PACKET_ENV = "SATYRN_HANDOFF_PACKET"
RESULT_ENV = "SATYRN_IMPLEMENTER_RESULT"
"""The seam an implementer executable reads and writes, mirroring the attempt
path's ``SATYRN_ATTEMPT_PATCH``/``SATYRN_ATTEMPT_TRANSCRIPT``."""

_RESULT_KEYS = frozenset(
    {"changed_files", "reported_outcome", "message", "version"}
)


@dataclass(frozen=True, slots=True)
class ImplementerResult:
    """What one implementer reports. **Never a verdict.**"""

    changed_files: tuple[str, ...]
    reported_outcome: ReportedOutcome
    message: str | None
    version: int = RESULT_VERSION

    def __post_init__(self) -> None:
        if self.version != RESULT_VERSION:
            raise RouteError(f"unknown result version {self.version!r}")
        if self.reported_outcome not in ("delivered", "refused"):
            raise RouteError(
                f"unknown reported_outcome: {self.reported_outcome!r}"
            )
        if not isinstance(self.changed_files, tuple) or any(
            not isinstance(f, str) or not f.strip() for f in self.changed_files
        ):
            raise RouteError("changed_files must be a tuple of non-blank strings")
        if self.reported_outcome == "delivered" and not self.changed_files:
            raise RouteError(
                "a delivered result must name its changed_files; delivering "
                "nothing is a refusal, not a silent success"
            )


def implementer_result_to_dict(result: ImplementerResult) -> dict[str, object]:
    return {
        "changed_files": list(result.changed_files),
        "reported_outcome": result.reported_outcome,
        "message": result.message,
        "version": result.version,
    }


def implementer_result_from_dict(data: Mapping[str, object]) -> ImplementerResult:
    """Parse a persisted result, checking shape **before** conversion.

    ``tuple("app.py")`` is a well-formed result of six single-character
    filenames, so conversion first would launder a malformed document into a
    valid object.
    """
    if missing := sorted(_RESULT_KEYS - set(data)):
        raise RouteError(f"persisted result is missing {', '.join(missing)}")
    version = data["version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise RouteError(f"persisted version must be an integer: {version!r}")
    files = data["changed_files"]
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise RouteError("persisted changed_files must be a list of strings")
    outcome = data["reported_outcome"]
    if not isinstance(outcome, str):
        raise RouteError("persisted reported_outcome must be a string")
    message = data["message"]
    if message is not None and not isinstance(message, str):
        raise RouteError("persisted message must be a string or null")
    return ImplementerResult(
        changed_files=tuple(files),
        reported_outcome=outcome,  # type: ignore[arg-type]
        message=message,
        version=version,
    )


type PhaseFiles = Mapping[str, Mapping[str, str]]

ROUTE_SCENARIO: PhaseFiles = {
    "phase-1-home": {
        "app.py": "# phase-1\n",
        "templates/base.html": "<!-- phase-1 -->\n",
        "tests/test_app.py": "# phase-1\n",
    },
    "phase-2-board": {
        "app.py": "# phase-1\n# phase-2\n",
        "models.py": "# phase-2\n",
        "templates/complaints.html": "<!-- phase-2 -->\n",
    },
    "phase-3-add": {
        "app.py": "# phase-1\n# phase-2\n# phase-3\n",
        "templates/complaints.html": "<!-- phase-2 -->\n<!-- phase-3 -->\n",
    },
}
"""The one scenario both tiers assert against, so the in-process seam and the
executable seam cannot drift apart while both stay green."""


def scripted_implementer(files: PhaseFiles, workspace: Path) -> Implementer:
    """A fake that writes one phase's declared files per call, in order.

    It enforces the packet's declared scope on itself. An obliging fake would
    mask a route defect, which is the same failure shape as a test that
    cannot fail. Scope is checked for **every** file before any is written,
    so a refusal never leaves a half-delivered workspace.

    Phases are consumed **in call order** rather than matched against the
    packet's text. The first version keyed on the step id appearing in
    ``objective``; the prompts say "## Phase 2 - Complaints Board" and never
    "phase-2-board", so every phase silently fell back to the first entry and
    wrote phase 1's files three times. A packet carries no step id on purpose
    -- it is what an implementer sees, and an implementer has no use for the
    harness's labels -- so the fake tracks its own position instead of
    inferring one.
    """
    remaining = list(files.values())

    def implement(packet: HandoffPacket) -> ImplementerResult:
        if not remaining:
            raise RouteError("scripted implementer called more times than it has phases")
        step_files = remaining.pop(0)
        for name in step_files:
            if not within_source(name, packet.writable_paths):
                raise RouteError(
                    f"{name!r} is outside the declared scope "
                    f"{packet.writable_paths}"
                )
        for name, text in step_files.items():
            path = workspace / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return ImplementerResult(
            changed_files=tuple(step_files),
            reported_outcome="delivered" if step_files else "refused",
            message=None,
        )

    return implement


@dataclass(frozen=True, slots=True)
class PhaseDecision:
    """One accept-or-reject, with the reason that produced it."""

    step_id: str
    accepted: bool
    reason: str
    result: ImplementerResult


def run_phases(
    task_dir: Path,
    manifest: TaskManifest,
    spec: SessionSpec,
    implementer: Implementer,
    workspace: Path,
    grader: PhaseGrader,
    *,
    base_revision: str,
    turn_budget: int,
    tool_call_budget: int,
) -> list[PhaseDecision]:
    """Run the spec's steps in order, stopping at the first rejection.

    No partial chain: a rejected phase ends the route rather than letting a
    later phase build on a state nobody accepted. HP3 implements that
    properly against chained worktrees; holding it here keeps the two cycles
    from disagreeing.
    """
    decisions: list[PhaseDecision] = []
    for step in spec.steps:
        packet = build_packet(
            task_dir, manifest, spec, step.id,
            base_revision=base_revision,
            turn_budget=turn_budget,
            tool_call_budget=tool_call_budget,
        )
        result = implementer(packet)
        match result.reported_outcome:
            case "refused":
                decisions.append(
                    PhaseDecision(
                        step.id, False,
                        f"implementer refused: {result.message or 'no reason given'}",
                        result,
                    )
                )
                return decisions
            case _:
                verdict, reason = grader(step.id, workspace)
                accepted = verdict == "pass"
                decisions.append(PhaseDecision(step.id, accepted, reason, result))
                if not accepted:
                    return decisions
    return decisions


def command_implementer(argv: list[str], workspace: Path) -> Implementer:
    """Adapt an implementer **executable** to the callable seam.

    Shipped here rather than in a test: if this adapter lived only in the
    integration test, the callable would be a different contract from the one
    a live run drives, and that test would prove only its own fixture.

    The packet is handed over as a file and the result read back from one, so
    neither crosses on stdout -- the same reason a verdict never comes from
    stdout anywhere else in this repository.
    """

    def implement(packet: HandoffPacket) -> ImplementerResult:  # pragma: no cover
        # Integration tier only: this body spawns, which the default tier's
        # planted tripwire forbids. `tests/integration/test_hp2_route.py`
        # drives it through a real executable and asserts the same decision
        # sequence the in-process seam produces, which is the drift guard.
        packet_path = workspace / ".satyrn-packet.json"
        result_path = workspace / ".satyrn-result.json"
        packet_path.write_text(json.dumps(packet_to_dict(packet), indent=2))
        result_path.unlink(missing_ok=True)
        env = {
            **os.environ,
            PACKET_ENV: str(packet_path),
            RESULT_ENV: str(result_path),
        }
        subprocess.run(argv, cwd=workspace, env=env, check=True)
        if not result_path.is_file():
            raise RouteError(
                f"implementer wrote no result to {RESULT_ENV}; an absent "
                "result is not a refusal"
            )
        return implementer_result_from_dict(json.loads(result_path.read_text()))

    return implement  # pragma: no cover
