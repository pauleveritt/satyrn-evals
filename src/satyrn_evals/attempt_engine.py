"""The Engine attempt adapter: the task text run through `/implement`.

The Engine arm is bare Pi's arm with each task run through the engine's
`/implement` (spec, "The eval"): the same task text, the same model and
Pi's native tools. `/implement` is derive, then deliver; outside a Pi
session its two steps are the engine CLI calls the command makes
(satyrn-engine Phase 1 Task 10: `buildDeriveInvocation`,
`buildDeliveryInvocation`):

1. ``satyrn-engine derive --repo WORKTREE -- TASK`` writes the contract under
   the worktree's git dir and names it on stderr;
2. ``satyrn-engine deliver --repo WORKTREE --timeout S CONTRACT -- satyrn-engine
   attempt --model=M -- CONTRACT`` runs one fresh Pi with every guard in its
   own isolated worktree, commits a candidate, validates it, and prints the
   receipt on stdout.

The adapter then checks the candidate out into the Evals worktree and
harvests it exactly as the Baseline adapter harvests (``attempt_pi``), so
both arms' patches come from one rule. The engine's own `attempt` writes
Pi's stream straight into ``SATYRN_ATTEMPT_TRANSCRIPT``, where the harness
reads it live for the budget and the timeline. The receipt is kept beside
the transcript as ``engine-receipt.json``; it is the engine's account and
never the verdict.
"""

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.attempt_pi import (
    PATCH_ENV,
    AdapterError,
    clean_pi_environment,
    harvest_patch,
    read_artifact_paths,
    read_base_sha,
    read_prompt,
)

ENGINE_REPO_ENV = "SATYRN_ENGINE_REPO"
RECEIPT_NAME = "engine-receipt.json"
DERIVE_LOG_NAME = "engine-derive.txt"
DELIVER_LOG_NAME = "engine-deliver.txt"
#: The deliver timeout: the spec's attempt-command backstop on this machine.
#: The harness's own command timeout and budget stop the cell first.
DELIVER_TIMEOUT_SECONDS = 1800
_CONTRACT_PREFIX = "satyrn-engine: contract "


@dataclass(frozen=True, slots=True)
class EngineArgs:
    model: str
    engine_repo: Path
    uv_bin: str


def parse_args(args: list[str], environment: Mapping[str, str]) -> EngineArgs:
    """``--model`` (required), ``--engine-repo`` (default ``$SATYRN_ENGINE_REPO``),
    ``--uv-bin``; one trailing positional (the rendered contract Evals
    appends) is accepted and ignored, because `/implement` derives its own."""
    model, engine_repo, uv_bin = "", environment.get(ENGINE_REPO_ENV, ""), "uv"
    seen_positional = False
    index = 0
    while index < len(args):
        token = args[index]
        if token in ("--model", "--engine-repo", "--uv-bin"):
            if index + 1 >= len(args):
                raise AdapterError(f"{token} needs a value")
            value = args[index + 1]
            if token == "--model":
                model = value
            elif token == "--engine-repo":
                engine_repo = value
            else:
                uv_bin = value
            index += 2
        elif token.startswith("-"):
            raise AdapterError(f"unknown adapter argument {token!r}")
        elif seen_positional:
            raise AdapterError(f"unexpected extra argument {token!r}")
        else:
            seen_positional = True
            index += 1
    if not model:
        raise AdapterError("--model is required")
    if not engine_repo:
        raise AdapterError(f"--engine-repo or {ENGINE_REPO_ENV} is required")
    return EngineArgs(model=model, engine_repo=Path(engine_repo), uv_bin=uv_bin)


def _engine(args: EngineArgs) -> list[str]:
    return [args.uv_bin, "run", "--project", os.fspath(args.engine_repo), "satyrn-engine"]


def derive_argv(args: EngineArgs, worktree: Path, request: str) -> list[str]:
    return [*_engine(args), "derive", "--repo", os.fspath(worktree), "--", request]


def deliver_argv(args: EngineArgs, worktree: Path, contract: Path) -> list[str]:
    return [
        *_engine(args), "deliver", "--repo", os.fspath(worktree),
        "--timeout", str(DELIVER_TIMEOUT_SECONDS), os.fspath(contract),
        "--", *_engine(args), "attempt", f"--model={args.model}", "--", os.fspath(contract),
    ]


def contract_path(stderr: str) -> Path:
    """The contract `derive` wrote, from its ``satyrn-engine: contract PATH`` line."""
    for line in reversed(stderr.splitlines()):
        if line.startswith(_CONTRACT_PREFIX):
            return Path(line.removeprefix(_CONTRACT_PREFIX).strip())
    raise AdapterError(f"derive named no contract: {stderr.strip()!r}")


def candidate_commit(receipt: str) -> str | None:
    """The receipt's candidate commit, or None when deliver created none."""
    try:
        data = json.loads(receipt)
    except json.JSONDecodeError:
        return None
    commit = data.get("candidate_commit") if isinstance(data, dict) else None
    return commit if isinstance(commit, str) and commit else None


def delivery_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Evals' environment for the engine, minus two entries.

    ``SATYRN_ATTEMPT_PATCH``: the engine's `attempt` would publish its own
    patch there; this adapter harvests the candidate instead, so both arms'
    patches follow one rule. ``UV_PROJECT_ENVIRONMENT``: Evals points it at
    the attempt's private environment for the model's own ``uv run``; left
    set, ``uv run --project ENGINE satyrn-engine`` would look for the engine
    there and fail to spawn.
    """
    cleaned = clean_pi_environment(environment)
    cleaned.pop(PATCH_ENV, None)
    cleaned.pop("UV_PROJECT_ENVIRONMENT", None)
    return cleaned


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv), os.environ)
    request = read_prompt(os.environ)
    patch_path, transcript_path = read_artifact_paths(os.environ)
    base_sha = read_base_sha(os.environ)
    worktree = Path.cwd()
    environment = delivery_environment(os.environ)
    derived = subprocess.run(
        derive_argv(args, worktree, request), capture_output=True, text=True, env=environment, check=False
    )
    (transcript_path.parent / DERIVE_LOG_NAME).write_text(derived.stderr, encoding="utf-8")
    exit_code = derived.returncode
    if derived.returncode == 0:
        with (transcript_path.parent / DELIVER_LOG_NAME).open("w", encoding="utf-8") as log:
            delivered = subprocess.run(
                deliver_argv(args, worktree, contract_path(derived.stderr)),
                stdout=subprocess.PIPE, stderr=log, text=True, env=environment, check=False,
            )
        (transcript_path.parent / RECEIPT_NAME).write_text(delivered.stdout, encoding="utf-8")
        exit_code = delivered.returncode
        if (commit := candidate_commit(delivered.stdout)) is not None:
            subprocess.run(["git", "checkout", "-q", "--detach", commit], check=True, capture_output=True)
    patch_path.write_text(harvest_patch(worktree, base_sha), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
