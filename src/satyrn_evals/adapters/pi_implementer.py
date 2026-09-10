"""HP7's real implementer: one Pi invocation per phase, behind HP2's
executable seam.

**Corrected 2026-09-10.** "One Pi turn" was this module's own wording, and
it is wrong: `pi --print --mode json` runs a complete agent interaction, not
a single model generation. Tool execution inside that one process
invocation can lead to another generation, repeatedly, each with its own
``turn_start``/``turn_end`` pair in the event stream (pi's own
``docs/json.md``, "Turn lifecycle"). Nothing on this seam bounds that --
``turn_budget``/``tool_call_budget`` are declared in the packet and never
applied (``chain_record.declaration_ledger``), and this invocation runs
with ``--no-extensions --no-skills``, so none of Engine's own guards (the
loop breaker, the progress rule) are loaded either. A doom loop is
possible inside one phase's single process invocation, exactly as it is in
a continuous Baseline session, and nothing here currently measures how
many internal turns one invocation actually took.

Adapts a single ``pi --print --mode json`` **process invocation** to
``command_implementer``'s contract (``SATYRN_HANDOFF_PACKET`` in,
``SATYRN_IMPLEMENTER_RESULT`` out): read the worker's own packet
projection, render it with ``packet.render_projection`` -- the same
rendering ``render_packet`` proves against the golden fixture, now
actually read by something -- run one such invocation on a
``read,write,edit`` surface, and report whatever the workspace shows
changed. Changes are found by content digest (``attribution.snapshot``), not
``git diff``: a route workspace is a plain directory the route builds up
phase by phase, not a git checkout the way an attempt's workspace is.

**No ``bash``, on purpose.** The packet's own ``self_test_command`` is
declared and never applied on this seam (HP6.3's ``declaration_ledger``) --
this is *why*: nothing this adapter runs can execute it. Phase HP runs no
orchestrating model either (`orchestrated-delivery-design.md`, "Amended
2026-09-09"), so a bounded ``read,write,edit`` implementer is the whole of
what this seam is proving.

**This adapter does not enforce ``writable_paths`` on itself.**
``fake_implementer.py`` does, deliberately, so a fixture bug cannot
masquerade as a route defect in a test. A real adapter policing its own
declared scope would recreate exactly the capture-integrity gap HP6.3 exists
to catch: ``declaration_ledger``'s ``writable_paths`` state would be true by
construction rather than by observation. So every mutation Pi actually made
is reported, in or out of scope, and HP6's ``check_chain`` -- which now
checks exactly this -- is what says whether the scope held.

A Pi process that exits non-zero, or that outlives ``--timeout``, is not
handled here: ``command_implementer`` runs this adapter under
``subprocess.run(..., check=True)``, and ``route.run_phases`` (HP6) converts
a ``CalledProcessError`` (which a ``subprocess.TimeoutExpired`` on the Pi
child also becomes, once it propagates out of ``main`` unhandled) into a
retained, refused decision rather than losing the chain.

**Corrected 2026-09-10, by the Astra-style acceptance review.** The first
version opened the transcript and stderr files in truncating (``wb``) mode,
so a three-phase chain retained only its last phase's evidence -- silently
contradicting the HP7 pre-run record's own precondition that model identity
comes from "the transcript's own field" after the run. Both now open in
append (``ab``) mode with a marker line ahead of each turn's bytes, driven by
a small on-disk counter -- the same shape ``fake_implementer.py`` already
uses to track its own position without a packet carrying a step id. The
first version also had no timeout anywhere on this seam, while the pre-run
record declared one; ``--timeout`` now reaches ``subprocess.run`` directly.
And Pi's stderr went to ``DEVNULL``; it is now captured for the same reason
the transcript is -- a live model failure retained with no diagnostic at all
is worse than one retained late.
"""

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from satyrn_evals.adapters.pi_session import session_child_environment
from satyrn_evals.attribution import diff_snapshots, snapshot
from satyrn_evals.errors import PacketError, UsageError
from satyrn_evals.packet import render_projection
from satyrn_evals.route import (
    PACKET_ENV,
    RESULT_ENV,
    ImplementerResult,
    implementer_result_to_dict,
)

#: `read,write,edit`, never `bash` -- see the module docstring. Distinct from
#: `attempt_pi.DEFAULT_TOOLS`, which is the whole-conversation Baseline
#: surface; this is HP2's bounded-implementer surface.
DEFAULT_TOOLS: tuple[str, ...] = ("read", "write", "edit")

#: Matches the HP7 pre-run record's frozen `--step-timeout 600s`
#: (`docs/current/hp7-live-route-proof-pre-run-record.md`). A record naming a
#: figure no code applies is the declared-vs-applied defect HP6.3 exists to
#: name; this constant is what closes that gap on this seam.
DEFAULT_TIMEOUT_SECONDS = 600

TRANSCRIPT_NAME = ".satyrn-implementer-transcript.jsonl"
STDERR_NAME = ".satyrn-implementer-stderr.log"
COUNTER_NAME = ".satyrn-implementer-call-counter"
"""Written into the workspace itself, alongside `.satyrn-packet.json` and
`.satyrn-result.json` -- and, like them, listed in
`attribution.HARNESS_FILES` so they are retained evidence, never a mutation
attributed to either role. One fixed name apiece, appended to across phases,
rather than one file per phase: `attribution.snapshot`'s exclusion list
matches exact relative paths, not a pattern, so a per-phase filename would
need a wider change to that shared module for three bookkeeping files' sake."""


def _next_call_index(workspace: Path) -> int:
    """This adapter's own position, tracked the way `fake_implementer.py`
    tracks its: a packet carries no step id on purpose, so nothing here can
    read one, and the workspace is the only shared state across calls."""
    counter = workspace / COUNTER_NAME
    index = int(counter.read_text()) if counter.is_file() else 0
    counter.write_text(str(index + 1))
    return index


def _marker(index: int) -> bytes:
    return json.dumps({"adapter_marker": "turn_start", "index": index}).encode() + b"\n"


class AdapterError(UsageError):
    """Exit 2: this adapter was invoked or wired in a way it cannot honour."""


def _value(args: list[str], index: int, flag: str) -> str:
    if index + 1 >= len(args):
        raise AdapterError(f"{flag} needs a value")
    return args[index + 1]


def parse_args(args: list[str]) -> tuple[str, tuple[str, ...], str, int]:
    """``--model`` (required), ``--tools`` (default `read,write,edit`),
    ``--pi-bin``, ``--timeout`` seconds (default `DEFAULT_TIMEOUT_SECONDS`)."""
    model, tools, pi_bin, timeout = "", DEFAULT_TOOLS, "pi", DEFAULT_TIMEOUT_SECONDS
    index = 0
    while index < len(args):
        match args[index]:
            case "--model":
                model = _value(args, index, "--model")
                index += 2
            case "--tools":
                raw = _value(args, index, "--tools")
                names = tuple(name for name in raw.split(",") if name)
                if not names:
                    raise AdapterError("--tools needs at least one tool name")
                tools = names
                index += 2
            case "--pi-bin":
                pi_bin = _value(args, index, "--pi-bin")
                index += 2
            case "--timeout":
                raw_timeout = _value(args, index, "--timeout")
                try:
                    timeout = int(raw_timeout)
                except ValueError:
                    raise AdapterError(
                        f"--timeout must be an integer number of seconds: "
                        f"{raw_timeout!r}"
                    ) from None
                if timeout <= 0:
                    raise AdapterError(
                        f"--timeout must be positive: {timeout!r}"
                    )
                index += 2
            case token:
                raise AdapterError(f"unknown adapter argument: {token!r}")
    if not model:
        raise AdapterError("--model is required")
    return model, tools, pi_bin, timeout


def build_pi_argv(
    model: str, tools: tuple[str, ...], prompt: str, pi_bin: str = "pi"
) -> list[str]:
    """One Pi process invocation, not one model turn -- see the module
    docstring's 2026-09-10 correction. Space-form model flag, matching
    every other adapter in this repository (pi 0.84.4 rejects the equals
    form)."""
    if not prompt.strip():
        raise AdapterError("refusing to launch pi with an empty prompt")
    return [
        pi_bin,
        "--print",
        "--mode",
        "json",
        "--no-session",
        "--model",
        model,
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-context-files",
        "--no-approve",
        "--tools",
        ",".join(tools),
        prompt,
    ]


def read_env_paths(environment: Mapping[str, str]) -> tuple[Path, Path]:
    """Where the packet crosses in and the result must cross out.

    Mirrors ``attempt_pi.read_artifact_paths``: a missing or blank variable
    is refused by name rather than reaching a bare ``KeyError`` from
    ``os.environ[...]``. Both paths are resolved, so a relative
    ``SATYRN_IMPLEMENTER_RESULT`` is anchored to the caller's cwd rather than
    silently producing a workspace directory nothing else agrees on.
    """
    packet = environment.get(PACKET_ENV, "")
    if not packet:
        raise AdapterError(f"{PACKET_ENV} is required")
    result = environment.get(RESULT_ENV, "")
    if not result:
        raise AdapterError(f"{RESULT_ENV} is required")
    return Path(packet).resolve(), Path(result).resolve()


def read_projection(packet_path: Path) -> dict[str, object]:
    """The worker's own packet projection: read and parsed legibly.

    Corrected 2026-09-10: the first version read this with a bare
    ``json.loads(packet_path.read_text())``, so a missing file, an unreadable
    one, or malformed JSON each surfaced as a raw traceback rather than an
    ``AdapterError`` -- the same loud-but-illegible shape every other
    exception this adapter can hit was already refused for.
    """
    try:
        text = packet_path.read_text()
    except OSError as exc:
        raise AdapterError(
            f"cannot read {PACKET_ENV} ({packet_path}): {exc}"
        ) from exc
    try:
        projection = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterError(
            f"{PACKET_ENV} ({packet_path}) is not valid JSON: {exc}"
        ) from exc
    if not isinstance(projection, dict):
        raise AdapterError(
            f"{PACKET_ENV} ({packet_path}) must be a JSON object"
        )
    return projection


def result_from_mutation(paths: tuple[str, ...]) -> ImplementerResult:
    """The one honest reading of a diff: something changed, or nothing did.

    Pi's own stop reason (length, error, aborted) is not distinguished here
    -- ``ImplementerResult`` has only ``delivered``/``refused``, and a Pi
    process that fails outright already takes a different path (its non-zero
    exit propagates through ``command_implementer`` to HP6's crash handling
    in ``run_phases``). A settled turn that touched nothing is a refusal, not
    a silent delivery of no work -- the same rule ``ImplementerResult``
    itself enforces.
    """
    if paths:
        return ImplementerResult(
            changed_files=paths, reported_outcome="delivered", message=None
        )
    return ImplementerResult(
        changed_files=(),
        reported_outcome="refused",
        message="no workspace change observed",
    )


def main(argv: list[str] | None = None) -> int:
    model, tools, pi_bin, timeout = parse_args(
        list(sys.argv[1:] if argv is None else argv)
    )
    packet_path, result_path = read_env_paths(os.environ)
    workspace = result_path.parent

    projection = read_projection(packet_path)
    try:
        prompt = render_projection(projection)
    except PacketError as exc:
        # `render_projection` refuses a shape defect (a non-object, an
        # empty one, a missing objective) as `PacketError`. Re-raised as
        # this adapter's own exception type so every failure this module can
        # produce -- a bad env var, malformed JSON, a shape defect -- is one
        # kind of thing to catch, not three.
        raise AdapterError(str(exc)) from exc

    index = _next_call_index(workspace)
    marker = _marker(index)
    before = snapshot(workspace)
    with (
        open(workspace / TRANSCRIPT_NAME, "ab") as transcript,
        open(workspace / STDERR_NAME, "ab") as stderr_log,
    ):
        transcript.write(marker)
        stderr_log.write(marker)
        # Reviewed 2026-09-10 (Sol, reproduced with a real /bin/echo child,
        # no inference): `subprocess.run` hands the child the file's raw
        # descriptor via dup2 and writes straight to it, bypassing Python's
        # userspace buffer entirely -- so an unflushed marker sits in that
        # buffer while the child's bytes land in the file first, and the
        # marker appears *after* the turn it was meant to open. `flush()`
        # forces the marker to the OS-level file before the child ever
        # writes to the same descriptor.
        transcript.flush()
        stderr_log.flush()
        subprocess.run(
            build_pi_argv(model, tools, prompt, pi_bin),
            cwd=workspace,
            stdout=transcript,
            stderr=stderr_log,
            check=True,
            timeout=timeout,
            env=session_child_environment(os.environ),
        )
    after = snapshot(workspace)
    changed = tuple(m.path for m in diff_snapshots(before, after))

    result_path.write_text(
        json.dumps(implementer_result_to_dict(result_from_mutation(changed)))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
