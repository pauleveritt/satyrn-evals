"""Preflight a task's own self-test on the unmodified base and the known-good state.

The 2026-09-18 route proof was void because the Engine's self-test could not
go green on the real task tree: the whole-path review checked that the
instruments could read a firing, but never ran the self-test once on the base.
This runs the task manifest's ``public_suite`` in a copy of the base, then
again after the task's known-good patch.

The hard requirement is the known-good row: a task whose green is unreachable
is refused. A red **base** with a green known-good is a *repair* task -- the
base is the defect the prompt asks the model to fix -- so it is recorded in
``checked`` (``base_exit``, ``repair_base``) and not refused. A build task
whose base regresses is caught because its known-good state is then red too.

This is a base-sanity check on the task's declared suite, not the Engine's
``run_tests`` path: the Engine's own test pins the preserve-appended run, and
evals does not import engine internals (BRIEF, the executable seam).

The runner is a seam so the default tier can drive both directions without
spawning; the real check is the integration tier and the operator's preflight.
"""

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from satyrn_evals.manifest import TaskManifest

SELF_TEST_TIMEOUT = 900
TAIL_CHARS = 400
ENGINE_PROTOCOL_VERSION = 1
CONTRACT_PREFIX = "satyrn-engine: contract "
type Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class TaskSelfTest:
    """The check's refusals and the facts behind them."""

    problems: list[str]
    checked: dict[str, object] = field(default_factory=dict)


def _tail(text: str) -> str:
    text = text.strip()
    return text if len(text) <= TAIL_CHARS else "..." + text[-TAIL_CHARS:]


def _run_suite(
    work: Path, command: tuple[str, ...], *, run: Runner, timeout: float
) -> tuple[int, str]:
    completed = run(
        list(command), cwd=work, capture_output=True, text=True, timeout=timeout, check=False
    )
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def _apply_known_good(work: Path, patch: Path, *, run: Runner) -> int:
    """``git init`` then ``git apply`` the task's known-good patch; the apply's exit code."""
    run(["git", "init", "-q"], cwd=work, capture_output=True, text=True, check=False)
    applied = run(
        ["git", "apply", os.fspath(patch)], cwd=work, capture_output=True, text=True, check=False
    )
    return applied.returncode


def task_self_test(
    task_dir: Path,
    manifest: TaskManifest,
    *,
    run: Runner = subprocess.run,
    timeout: float = SELF_TEST_TIMEOUT,
) -> TaskSelfTest:
    """The task's ``public_suite`` on the base, and again after its known-good patch.

    An empty ``public_suite`` is not an Engine task and has nothing to check.
    A missing known-good patch leaves the base as the only row, and a red base
    is then refused. A red base with a green known-good state is a repair task:
    recorded, never refused.
    """
    if not manifest.public_suite:
        return TaskSelfTest([])
    base = task_dir / "base"
    patch_name = manifest.fixtures.get("known_good")
    problems: list[str] = []
    checked: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="satyrn-selftest-") as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(base, work, symlinks=True)
        base_code, base_output = _run_suite(work, manifest.public_suite, run=run, timeout=timeout)
        checked["base_exit"] = base_code
        if not patch_name:
            if base_code != 0:
                problems.append(
                    f"the self-test on the unmodified {manifest.name} base exited "
                    f"{base_code}: {_tail(base_output)}"
                )
            return TaskSelfTest(problems, checked)
        patch = task_dir / patch_name
        if not patch.is_file():
            problems.append(f"the {manifest.name} known-good patch is missing: {patch}")
            return TaskSelfTest(problems, checked)
        if _apply_known_good(work, patch, run=run) != 0:
            problems.append(f"the {manifest.name} known-good patch did not apply: {patch}")
            return TaskSelfTest(problems, checked)
        good_code, good_output = _run_suite(work, manifest.public_suite, run=run, timeout=timeout)
        checked["known_good_exit"] = good_code
        checked["repair_base"] = base_code != 0 and good_code == 0
        if good_code != 0:
            if base_code != 0:
                problems.append(
                    f"the self-test on the unmodified {manifest.name} base exited "
                    f"{base_code}: {_tail(base_output)}"
                )
            problems.append(
                f"the self-test on the {manifest.name} known-good state exited "
                f"{good_code}: {_tail(good_output)}"
            )
    return TaskSelfTest(problems, checked)


def _git_init_commit(work: Path, *, run: Runner) -> str:
    """``git init`` + one commit; the HEAD sha, or empty on failure."""
    run(["git", "init", "-q"], cwd=work, capture_output=True, text=True, check=False)
    run(["git", "add", "-A"], cwd=work, capture_output=True, text=True, check=False)
    run(
        ["git", "-c", "user.email=preflight@satyrn.invalid", "-c", "user.name=preflight",
         "commit", "-qm", "base"],
        cwd=work, capture_output=True, text=True, check=False,
    )
    head = run(["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=False)
    return (head.stdout or "").strip()


def _engine_row(
    work: Path,
    engine: tuple[str, ...],
    request: str,
    *,
    token_budget: int,
    turn_budget: int,
    run: Runner,
    timeout: float,
) -> tuple[int | None, str]:
    """(self-test exit code, detail) of the Engine's derived contract on ``work``.

    The Engine executable is the seam: ``engine`` is the argv prefix the cell
    runs (``uv run --project <export> satyrn-engine``). ``None`` means the row
    could not produce an exit code -- a derive failure or a protocol refusal --
    and the detail names it.
    """
    derived = run(
        [
            *engine, "derive", "--repo", os.fspath(work),
            "--token-budget", str(token_budget), "--turn-budget", str(turn_budget),
            "--", request,
        ],
        cwd=work, capture_output=True, text=True, timeout=timeout, check=False,
    )
    if derived.returncode != 0:
        return None, f"derive exited {derived.returncode}: {_tail(derived.stderr or derived.stdout)}"
    contract = next(
        (line.removeprefix(CONTRACT_PREFIX).strip() for line in reversed(derived.stderr.splitlines())
         if line.startswith(CONTRACT_PREFIX)),
        None,
    )
    if not contract:
        return None, f"derive named no contract: {_tail(derived.stderr)}"
    head = run(["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=False)
    protocol_request = json.dumps({
        "version": ENGINE_PROTOCOL_VERSION,
        "operation": "test",
        "repo": os.fspath(work),
        "contract": contract,
        "command": None,
        "base_commit": (head.stdout or "").strip() or None,
    })
    response = run(
        [*engine, "protocol"],
        cwd=work, input=protocol_request, capture_output=True, text=True, timeout=timeout, check=False,
    )
    try:
        payload = json.loads(response.stdout)
    except json.JSONDecodeError:
        return None, f"protocol returned no JSON: {_tail(response.stdout or response.stderr)}"
    result = payload.get("result")
    if not payload.get("ok") or not isinstance(result, dict):
        return None, f"self-test refused: {payload.get('code')}: {_tail(str(payload.get('message', '')))}"
    return result.get("exit_code"), _tail(str(result.get("output", "")))


def engine_self_test(
    task_dir: Path,
    manifest: TaskManifest,
    *,
    engine: tuple[str, ...],
    request: str,
    token_budget: int,
    turn_budget: int,
    run: Runner = subprocess.run,
    timeout: float = SELF_TEST_TIMEOUT,
) -> TaskSelfTest:
    """The Engine's own self-test on the base, and again after its known-good patch.

    This is the path the route proof died in: the Engine derives a contract
    from the tree and runs it with the carried paths appended, not the plain
    public suite. The hard requirement is the known-good row -- a red
    known-good state refuses the record. A red base with a green known-good is
    a repair task, recorded not refused. A derive failure or protocol refusal
    on either row is named and refuses.
    """
    if not manifest.public_suite:
        return TaskSelfTest([])
    base = task_dir / "base"
    patch_name = manifest.fixtures.get("known_good")
    problems: list[str] = []
    checked: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="satyrn-engine-selftest-") as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(base, work, symlinks=True)
        _git_init_commit(work, run=run)
        base_code, base_detail = _engine_row(
            work, engine, request, token_budget=token_budget, turn_budget=turn_budget,
            run=run, timeout=timeout,
        )
        checked["base_exit"] = base_code
        if base_code is None:
            problems.append(f"the Engine self-test could not run on the unmodified {manifest.name} base: {base_detail}")
        patch = task_dir / patch_name if patch_name else None
        if patch is not None and not patch.is_file():
            problems.append(f"the {manifest.name} known-good patch is missing: {patch}")
            return TaskSelfTest(problems, checked)
        if patch is not None:
            if _apply_known_good(work, patch, run=run) != 0:
                problems.append(f"the {manifest.name} known-good patch did not apply: {patch}")
                return TaskSelfTest(problems, checked)
            _git_init_commit(work, run=run)
        good_code, good_detail = _engine_row(
            work, engine, request, token_budget=token_budget, turn_budget=turn_budget,
            run=run, timeout=timeout,
        )
        checked["known_good_exit"] = good_code
        checked["repair_base"] = base_code not in (None, 0) and good_code == 0
        if good_code is None:
            if base_code is not None and base_code != 0:
                problems.append(
                    f"the Engine self-test on the unmodified {manifest.name} base exited "
                    f"{base_code}: {base_detail}"
                )
            problems.append(
                f"the Engine self-test could not run on the {manifest.name} known-good state: {good_detail}"
            )
        elif good_code != 0:
            if base_code is not None and base_code != 0:
                problems.append(
                    f"the Engine self-test on the unmodified {manifest.name} base exited "
                    f"{base_code}: {base_detail}"
                )
            problems.append(
                f"the Engine self-test on the {manifest.name} known-good state exited "
                f"{good_code}: {good_detail}"
            )
    return TaskSelfTest(problems, checked)
