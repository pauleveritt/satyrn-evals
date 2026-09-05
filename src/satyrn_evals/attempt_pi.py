"""The Baseline attempt adapter: bare Pi behind the Evals attempt seam.

One `pi --print --mode json` turn against the workspace Evals allocated,
its stream-JSON written to ``SATYRN_ATTEMPT_TRANSCRIPT`` and the tracked
diff harvested into ``SATYRN_ATTEMPT_PATCH`` after pi exits. Derived from
the wrapper recorded in
`docs/superpowers/research/2026-09-03-local-pings-reprobe-protocol.md`,
with the deliberate changes recorded in
`docs/superpowers/research/2026-09-05-v11b-adapter-derivation.md`.

**The adapter takes no ``--rung``.** The rung reaches it as the contract
text Evals exports in ``SATYRN_TASK_CONTRACT`` (`attempt.py:109-112`).
That is the seam that keeps the ladder (V11a) and the arm substrate
(V11b) independent of each other.

**Model flags are space-form, always.** pi 0.84.4's hand-rolled parser
matches the literal token ``--model`` and records ``--model=VALUE`` as an
unknown flag; the V8 smoke lost a run to exactly that, and engine commit
``75d4863`` is the fix on the Engine side.

Stated limits, neither of them papered over:

- **``git diff HEAD`` drops files the model created with ``write``.**
  Untracked files are invisible to it. That is harmless on pure-edit
  repair and fatal for build shapes and for `framing-2`. ``git add -A``
  is **not** the fix: it would sweep a model's ``uv run pytest`` residue
  into the patch and trip the allowlist check. Creation-capable capture
  is a V12 entry gate, so a task that needs it must not be measured on
  this adapter.
- **The diff is harvested only after pi exits**, so a cell killed by the
  attempt timeout retains no intermediate patch. Report that beside
  retained-patch production; never read a completion floor under this
  adapter as a capability wall.
"""

import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.arms import KNOWN_TOOLS
from satyrn_evals.errors import UsageError

#: The three variables Evals exports around an attempt command
#: (`attempt.py:109-112`). A default-tier test pins them to that module.
CONTRACT_ENV = "SATYRN_TASK_CONTRACT"
PATCH_ENV = "SATYRN_ATTEMPT_PATCH"
TRANSCRIPT_ENV = "SATYRN_ATTEMPT_TRANSCRIPT"

#: The Baseline arm's declared tool surface (`arms/baseline.json`).
DEFAULT_TOOLS: tuple[str, ...] = ("read", "bash", "edit", "write")


class AdapterError(UsageError):
    """Exit 2: the adapter was invoked or wired in a way it cannot honour."""


@dataclass(frozen=True, slots=True)
class AdapterArgs:
    """The adapter's own arguments, after parsing."""

    model: str
    tools: tuple[str, ...]
    pi_bin: str


def _value(args: list[str], index: int, flag: str) -> str:
    if index + 1 >= len(args):
        raise AdapterError(f"{flag} needs a value")
    return args[index + 1]


def parse_args(args: list[str]) -> AdapterArgs:
    """The adapter's argument surface: ``--model``, ``--tools``, ``--pi-bin``.

    A single trailing positional is accepted and ignored: Evals appends
    the task's engine-contract path when the manifest declares one
    (`attempt.py:115-119`), and the Baseline arm's prompt comes from the
    environment instead.
    """
    model, tools, pi_bin = "", DEFAULT_TOOLS, "pi"
    seen_positional = False
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
                if unknown := sorted(set(names) - KNOWN_TOOLS):
                    raise AdapterError(f"unknown tool name(s) {', '.join(unknown)}")
                tools = names
                index += 2
            case "--pi-bin":
                pi_bin = _value(args, index, "--pi-bin")
                index += 2
            case "--rung":
                raise AdapterError(
                    "the adapter takes no --rung; the rung reaches it as the "
                    f"contract text in {CONTRACT_ENV}"
                )
            case token if token.startswith("-"):
                raise AdapterError(
                    f"unknown adapter argument {token!r}"
                    + (
                        "; pi 0.84.4 rejects the equals form, pass --model VALUE"
                        if token.startswith("--model=")
                        else ""
                    )
                )
            case _ if seen_positional:
                raise AdapterError(f"unexpected extra argument {args[index]!r}")
            case _:
                seen_positional = True  # the appended engine-contract path
                index += 1
    if not model:
        raise AdapterError("--model is required")
    return AdapterArgs(model=model, tools=tools, pi_bin=pi_bin)


def build_pi_argv(args: AdapterArgs, prompt: str) -> list[str]:
    """The exact pi child argv. Space-form model; one joined ``--tools``."""
    if not prompt.strip():
        raise AdapterError("refusing to launch pi with an empty prompt")
    return [
        args.pi_bin,
        "--print",
        "--mode",
        "json",
        "--no-session",
        "--model",
        args.model,
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-context-files",
        "--no-approve",
        "--tools",
        ",".join(args.tools),
        prompt,
    ]


def read_prompt(environment: Mapping[str, str]) -> str:
    """The model-visible contract Evals exported, refusing an empty one.

    An empty prompt would produce a transcript with no model turn, which
    reads downstream as a refusal rather than as the wiring fault it is.
    """
    prompt = environment.get(CONTRACT_ENV, "")
    if not prompt.strip():
        raise AdapterError(f"{CONTRACT_ENV} is missing or empty")
    return prompt


def read_artifact_paths(environment: Mapping[str, str]) -> tuple[Path, Path]:
    """Where the patch and transcript must be delivered."""
    if not (patch := environment.get(PATCH_ENV, "")):
        raise AdapterError(f"{PATCH_ENV} is required")
    if not (transcript := environment.get(TRANSCRIPT_ENV, "")):
        raise AdapterError(f"{TRANSCRIPT_ENV} is required")
    return Path(patch), Path(transcript)


def harvest_patch() -> str:
    """The tracked diff of the workspace, as a unified patch.

    ``git diff HEAD`` and nothing wider: see this module's stated limits.
    A git failure refuses rather than returning "", because an empty
    patch is a *legible* outcome downstream (`NO_PATCH`) and would hide
    the fault.
    """
    completed = subprocess.run(
        ["git", "diff", "HEAD"], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise AdapterError(
            f"git diff HEAD failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    return completed.stdout


def main(argv: list[str] | None = None) -> int:
    """Run one pi turn and preserve both artifacts before returning.

    pi's stderr goes to ``DEVNULL``, as the shipped session adapter's does
    (`adapters/pi_session.py` `main`). Folding it into the transcript — as
    the recorded 2026-09-03 wrapper did — puts non-JSON lines in the
    stream, and V10 reports a transcript with one unparseable line as
    ``measured: false`` for the whole cell (`pathology.py:88-89`).
    """
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    prompt = read_prompt(os.environ)
    patch_path, transcript_path = read_artifact_paths(os.environ)
    command = build_pi_argv(args, prompt)
    with open(transcript_path, "wb") as transcript:
        completed = subprocess.run(
            command,
            stdout=transcript,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    patch_path.write_text(harvest_patch(), encoding="utf-8")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
