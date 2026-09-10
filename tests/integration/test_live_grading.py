"""`live_session_grader` against the real oracle: no satyrn-engine, no
model -- just real git commits standing in for real candidate commits,
and the same checkpoint fixtures `test_hp2_route.py` already proves the
oracle distinguishes. What's new here is cumulative-from-base grading fed
by commit shas rather than pre-made per-step patch files.
"""

import subprocess
from pathlib import Path

import pytest

from satyrn_evals.live_grading import live_session_grader
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.session_manifest import load_session_spec

pytestmark = pytest.mark.integration

TASK_NAME = "agentclinic-session-phased"
STEPS = ["phase-1-home", "phase-2-board", "phase-3-add"]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _commit_over_base(task_dir: Path, repo: Path, patch_name: str) -> str:
    """A fresh checkout of `base/`, one checkpoint patch applied, committed
    -- independent of any other commit, since `git diff` between two
    commits needs no ancestry between them, only their trees."""
    worktree = repo.parent / f"apply-{patch_name}"
    subprocess.run(
        ["git", "checkout", "-b", f"tmp-{patch_name}"],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    subprocess.run(["git", "worktree", "add", "--detach", str(worktree)], cwd=repo, check=True)
    patch_path = task_dir / "fixtures" / f"{patch_name}.patch"
    subprocess.run(["git", "apply", str(patch_path)], cwd=worktree, check=True)
    subprocess.run(["git", "add", "-A"], cwd=worktree, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", patch_name],
        cwd=worktree, check=True,
    )
    sha = _git(worktree, "rev-parse", "HEAD")
    subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=repo, check=True)
    return sha


def _make_repo(task_dir: Path, repo: Path) -> str:
    import shutil
    shutil.copytree(task_dir / "base", repo)
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                     "commit", "--quiet", "--allow-empty", "-m", "base"], cwd=repo, check=True)
    return _git(repo, "rev-parse", "HEAD")


def test_a_cumulative_good_chain_grades_pass_at_every_checkpoint(tmp_path: Path) -> None:
    task_dir = resolve_task(TASK_NAME)
    repo = tmp_path / "repo"
    initial = _make_repo(task_dir, repo)
    receipts: list[dict[str, object]] = []
    grade = live_session_grader(
        task_dir, load_manifest(task_dir), load_session_spec(task_dir),
        repo, initial, receipts, tmp_path / "grading",
    )

    for step_id, patch_name in zip(
        STEPS, ["checkpoint-1", "checkpoint-2", "known-good"], strict=True
    ):
        receipts.append({"candidate_commit": _commit_over_base(task_dir, repo, patch_name)})
        verdict, reason = grade(step_id, tmp_path)
        assert verdict == "pass", (step_id, reason)


def test_a_broken_final_checkpoint_grades_fail(tmp_path: Path) -> None:
    task_dir = resolve_task(TASK_NAME)
    repo = tmp_path / "repo"
    initial = _make_repo(task_dir, repo)
    receipts: list[dict[str, object]] = []
    grade = live_session_grader(
        task_dir, load_manifest(task_dir), load_session_spec(task_dir),
        repo, initial, receipts, tmp_path / "grading",
    )

    for step_id, patch_name in zip(
        STEPS, ["checkpoint-1", "checkpoint-2", "known-broken"], strict=True
    ):
        receipts.append({"candidate_commit": _commit_over_base(task_dir, repo, patch_name)})
        verdict, reason = grade(step_id, tmp_path)

    assert verdict == "fail", reason
