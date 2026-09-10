"""HP7's real implementer: one Pi turn per phase, behind HP2's executable seam.

Adapts a single ``pi --print --mode json`` turn to ``command_implementer``'s
contract (``SATYRN_HANDOFF_PACKET`` in, ``SATYRN_IMPLEMENTER_RESULT`` out):
read the worker's own packet projection, render it with
``packet.render_projection`` -- the same rendering ``render_packet`` proves
against the golden fixture, now actually read by something -- run one Pi turn
on a ``read,write,edit`` surface, and report whatever the workspace shows
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

A Pi process that exits non-zero is not handled here: ``command_implementer``
runs it under ``subprocess.run(..., check=True)``, and ``route.run_phases``
(HP6) converts that ``CalledProcessError`` into a retained, refused decision
rather than losing the chain.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from satyrn_evals.adapters.pi_session import session_child_environment
from satyrn_evals.attribution import diff_snapshots, snapshot
from satyrn_evals.errors import UsageError
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

TRANSCRIPT_NAME = ".satyrn-implementer-transcript.jsonl"
"""Written into the workspace itself, alongside `.satyrn-packet.json` and
`.satyrn-result.json` -- and, like them, listed in
`attribution.HARNESS_FILES` so it is retained evidence, never a mutation
attributed to either role."""


class AdapterError(UsageError):
    """Exit 2: this adapter was invoked or wired in a way it cannot honour."""


def _value(args: list[str], index: int, flag: str) -> str:
    if index + 1 >= len(args):
        raise AdapterError(f"{flag} needs a value")
    return args[index + 1]


def parse_args(args: list[str]) -> tuple[str, tuple[str, ...], str]:
    """``--model`` (required), ``--tools`` (default `read,write,edit`),
    ``--pi-bin``."""
    model, tools, pi_bin = "", DEFAULT_TOOLS, "pi"
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
            case token:
                raise AdapterError(f"unknown adapter argument: {token!r}")
    if not model:
        raise AdapterError("--model is required")
    return model, tools, pi_bin


def build_pi_argv(
    model: str, tools: tuple[str, ...], prompt: str, pi_bin: str = "pi"
) -> list[str]:
    """One bounded Pi turn. Space-form model flag, matching every other
    adapter in this repository (pi 0.84.4 rejects the equals form)."""
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
    model, tools, pi_bin = parse_args(list(sys.argv[1:] if argv is None else argv))
    packet_path = Path(os.environ[PACKET_ENV])
    result_path = Path(os.environ[RESULT_ENV])
    workspace = result_path.parent

    projection = json.loads(packet_path.read_text())
    prompt = render_projection(projection)

    before = snapshot(workspace)
    transcript_path = workspace / TRANSCRIPT_NAME
    with open(transcript_path, "wb") as transcript:
        subprocess.run(
            build_pi_argv(model, tools, prompt, pi_bin),
            cwd=workspace,
            stdout=transcript,
            stderr=subprocess.DEVNULL,
            check=True,
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
