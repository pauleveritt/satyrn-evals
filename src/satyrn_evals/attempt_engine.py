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

from satyrn_evals.attempt import COMMAND_BACKSTOP_ENV, TOKEN_BUDGET_ENV, TURN_BUDGET_ENV
from satyrn_evals.attempt_pi import (
    PATCH_ENV,
    TRANSCRIPT_ENV,
    AdapterError,
    clean_pi_environment,
    harvest_patch,
    read_artifact_paths,
    read_base_sha,
    read_prompt,
)
from satyrn_evals.cell import (
    CELLS_ROOT,
    Isolation,
    cell_command,
    isolation_from,
    model_environment,
)
from satyrn_evals.cell_engine import EngineExportError, verify_export
from satyrn_evals.workspace import GIT_SAFETY_CONFIG

ENGINE_REPO_ENV = "SATYRN_ENGINE_REPO"
RECEIPT_NAME = "engine-receipt.json"
DERIVE_LOG_NAME = "engine-derive.txt"
DELIVER_LOG_NAME = "engine-deliver.txt"
CHECKOUT_LOG_NAME = "engine-checkout.txt"
#: How far below the record's per-attempt-command backstop the Engine's own
#: deliver timeout sits (design §5.4; plan Ruling 9). Parity: until release
#: two, `DELIVER_TIMEOUT_SECONDS = 1800` stopped an Engine cell earlier than
#: Baseline's 3,000 or 4,800 s backstop, which `STATE.md` lists as an open
#: arm-parity defect. The margin makes the Engine's own deliver stop just
#: before the harness kills the command, so the Engine writes its receipt and
#: leaves its candidate rather than dying with no evidence.
DELIVER_MARGIN_SECONDS = 60
_CONTRACT_PREFIX = "satyrn-engine: contract "


def deliver_timeout(backstop_s: int) -> int:
    return max(backstop_s - DELIVER_MARGIN_SECONDS, 1)


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


def _engine(args: EngineArgs, no_sync: bool) -> list[str]:
    sync = ["--no-sync"] if no_sync else []
    return [args.uv_bin, "run", *sync, "--project", os.fspath(args.engine_repo), "satyrn-engine"]


def derive_argv(
    args: EngineArgs,
    worktree: Path,
    request: str,
    *,
    no_sync: bool = False,
    token_budget: int,
    turn_budget: int,
) -> list[str]:
    return [
        *_engine(args, no_sync), "derive", "--repo", os.fspath(worktree),
        "--token-budget", str(token_budget), "--turn-budget", str(turn_budget), "--", request,
    ]


def deliver_argv(
    args: EngineArgs, worktree: Path, contract: Path, *, no_sync: bool = False, backstop_s: int
) -> list[str]:
    return [
        *_engine(args, no_sync), "deliver", "--repo", os.fspath(worktree),
        "--timeout", str(deliver_timeout(backstop_s)), os.fspath(contract),
        "--", *_engine(args, no_sync), "attempt", f"--model={args.model}", "--", os.fspath(contract),
    ]


def _read_positive(env_name: str, unit: str, environment: Mapping[str, str]) -> int:
    raw = environment.get(env_name, "")
    try:
        value = int(raw)
    except ValueError:
        raise AdapterError(f"{env_name} must name {unit}, got {raw!r}") from None
    if value < 1:
        raise AdapterError(f"{env_name} must be a positive integer, got {value!r}")
    return value


def read_command_backstop(environment: Mapping[str, str]) -> int:
    """The record's command backstop Evals exported, refusing anything else.

    Absent, unparseable, or non-positive is an AdapterError, never a default:
    the only plausible fallback is the old fixed 1800 s this task exists to
    remove (plan dispatch ruling, Tasks 7/8). Non-positive is refused so this
    guard agrees with `run_record.py`'s own `command_backstop_s < 1` refusal
    -- a record could not have frozen a non-positive value, so a cell that
    reaches here with one is a wiring fault, not a legal 1-second attempt.
    """
    return _read_positive(COMMAND_BACKSTOP_ENV, "the command backstop in seconds", environment)


def read_budget(environment: Mapping[str, str]) -> tuple[int, int]:
    """The record's token and turn limits Evals exported, refusing anything else.

    Same rule as the backstop: absent, unparseable, or non-positive is an
    AdapterError, never a default. The Engine must have no stop the record
    does not name (maintainer ruling 2026-09-18), so the product's 32,000/48
    must never leak into an eval cell through a missing variable.
    """
    return (
        _read_positive(TOKEN_BUDGET_ENV, "the output-token limit", environment),
        _read_positive(TURN_BUDGET_ENV, "the turn limit", environment),
    )


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


def isolated(args: EngineArgs, environment: Mapping[str, str]) -> bool:
    """Whether the engine runs as the cell user; refuses an engine the cell cannot read."""
    try:
        if isolation_from(environment) is Isolation.LOCAL:
            return False
    except ValueError as exc:
        raise AdapterError(str(exc)) from exc
    if not args.engine_repo.resolve().is_relative_to(CELLS_ROOT.resolve()):
        raise AdapterError(
            f"under isolation the engine must be an export under {CELLS_ROOT} "
            f"(satyrn-evals cell-engine), not {args.engine_repo}"
        )
    try:
        verify_export(args.engine_repo)
    except EngineExportError as exc:
        raise AdapterError(f"engine export {args.engine_repo} is not safe to run: {exc}") from exc
    return True


def as_cell(argv: list[str], args: EngineArgs, environment: Mapping[str, str], worktree: Path) -> list[str]:
    """An engine call run as the cell user: the transcript path and the engine
    export are passed through; the model's ``UV_PROJECT_ENVIRONMENT`` is not
    (Ruling 7 of Phase 2a, unchanged under isolation)."""
    try:
        cell = model_environment(
            environment,
            {TRANSCRIPT_ENV: environment[TRANSCRIPT_ENV], ENGINE_REPO_ENV: os.fspath(args.engine_repo)},
        )
    except (KeyError, ValueError) as exc:
        raise AdapterError(f"cannot build the cell environment: {exc}") from exc
    cell.pop("UV_PROJECT_ENVIRONMENT", None)
    return cell_command(argv, cwd=worktree, environment=cell)


def checkout_candidate(commit: str, log: Path) -> int:
    """Check the candidate out into the Evals worktree; a failure is logged, never raised."""
    checkout = subprocess.run(
        ["git", *GIT_SAFETY_CONFIG, "checkout", "-q", "--detach", commit],
        capture_output=True,
        text=True,
        check=False,
    )
    if checkout.returncode != 0:
        log.write_text(f"git checkout {commit} exited {checkout.returncode}\n{checkout.stderr}", encoding="utf-8")
    return checkout.returncode


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv), os.environ)
    request = read_prompt(os.environ)
    patch_path, transcript_path = read_artifact_paths(os.environ)
    base_sha = read_base_sha(os.environ)
    backstop_s = read_command_backstop(os.environ)
    token_budget, turn_budget = read_budget(os.environ)
    worktree = Path.cwd()
    cell = isolated(args, os.environ)
    environment = delivery_environment(os.environ)

    def command(engine_argv: list[str]) -> list[str]:
        return as_cell(engine_argv, args, os.environ, worktree) if cell else engine_argv

    derived = subprocess.run(
        command(derive_argv(
            args, worktree, request, no_sync=cell,
            token_budget=token_budget, turn_budget=turn_budget,
        )),
        capture_output=True, text=True, env=environment, check=False,
    )
    (patch_path.parent / DERIVE_LOG_NAME).write_text(derived.stderr, encoding="utf-8")
    exit_code = derived.returncode
    if derived.returncode == 0:
        with (patch_path.parent / DELIVER_LOG_NAME).open("w", encoding="utf-8") as log:
            delivered = subprocess.run(
                command(
                    deliver_argv(
                        args, worktree, contract_path(derived.stderr), no_sync=cell, backstop_s=backstop_s
                    )
                ),
                stdout=subprocess.PIPE, stderr=log, text=True, env=environment, check=False,
            )
        (patch_path.parent / RECEIPT_NAME).write_text(delivered.stdout, encoding="utf-8")
        exit_code = delivered.returncode
        if (commit := candidate_commit(delivered.stdout)) is not None and (
            checkout := checkout_candidate(commit, patch_path.parent / CHECKOUT_LOG_NAME)
        ):
            exit_code = checkout
    patch_path.write_text(harvest_patch(worktree, base_sha), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
