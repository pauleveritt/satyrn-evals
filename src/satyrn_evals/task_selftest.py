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
