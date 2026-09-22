"""Two-uid isolation at the workspace boundary: real sudo, real git, no model.

Skips when the cell user is not set up (``cell_support.cell_scratch``).
"""

import os
import stat
import subprocess
import time
from pathlib import Path

import pytest

from integration.cell_support import cell_process_alive, run_as_cell
from satyrn_evals.attempt_pi import harvest_patch
from satyrn_evals.cell import (
    CELLS_ROOT,
    Isolation,
    cell_command,
    cell_environment,
    cell_paths,
    kill_cell_group,
)
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.workspace import (
    WorkspaceCode,
    _teardown_process,
    prepare_workspace,
    release_workspace,
    run_prepared_command,
)

pytestmark = pytest.mark.integration

CALC = Path(__file__).parent / "data" / "tasks" / "calc-build"
WRITE_AND_COMMIT = (
    "mkdir -p calc && printf 'def add_all(xs):\\n    return sum(xs)\\n' > calc/helpers.py"
    " && printf 'def render(n):\\n    return f\"{n:,}\"\\n' > calc/format.py"
    " && git add calc/helpers.py && git commit -qm model"
)


def _isolated(tmp_path: Path):
    return prepare_workspace(
        base=CALC / "base", protected_paths=(CALC, tmp_path), environment=dict(os.environ), isolation=Isolation.ISOLATED
    )


def test_an_isolated_workspace_is_shared_with_the_cell_group_under_the_cells_root(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    try:
        assert lease.parent.parent == CELLS_ROOT.resolve()
        tmpdir, uv_environment, gitconfig = cell_paths(lease.parent)
        for directory in (lease.parent, lease.worktree, tmpdir, uv_environment, lease.repository / ".git" / "objects"):
            assert stat.S_IMODE(directory.stat().st_mode) == 0o2770, directory
        assert f"directory = {lease.worktree}" in gitconfig.read_text()
    finally:
        assert release_workspace(lease) is None
    assert not lease.parent.exists()


def test_the_cell_cannot_use_the_maintainers_worktree_without_its_git_config(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    try:
        bare = {"HOME": "/Users/satyrn-cell", "PATH": "/opt/homebrew/bin:/usr/bin:/bin"}
        refused = run_as_cell(["git", "status", "--short"], cwd=lease.worktree, environment=bare)
        assert refused.returncode == 128 and "dubious ownership" in refused.stderr
    finally:
        assert release_workspace(lease) is None


def test_the_cell_commits_in_its_worktree_and_the_maintainer_harvests_every_change(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    try:
        wrote = run_as_cell(["/bin/sh", "-c", WRITE_AND_COMMIT], cwd=lease.worktree, environment=cell_environment(parent=lease.parent))
        assert wrote.returncode == 0, wrote.stderr
        assert (lease.worktree / "calc" / "format.py").stat().st_uid != os.getuid()
        patch = harvest_patch(lease.worktree, lease.base_sha)
        assert sorted(parse_patch_paths(patch)) == ["calc/format.py", "calc/helpers.py"]
    finally:
        assert release_workspace(lease) is None
    assert not lease.parent.exists()


def _stubborn(lease, pidfile: Path) -> list[str]:
    """A cell command that ignores SIGTERM and leaves a background child in the group."""
    script = f"trap '' TERM; sleep 60 & echo $! > {pidfile}; wait"
    return cell_command(["/bin/sh", "-c", script], cwd=lease.worktree, environment=cell_environment(parent=lease.parent))


def test_an_isolated_command_that_ignores_sigterm_is_killed_from_the_cell_side(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    pidfile = lease.parent / "tmp" / "child.pid"
    try:
        result = run_prepared_command(lease, command=_stubborn(lease, pidfile), timeout=2)
        assert result.code is WorkspaceCode.COMMAND_TIMEOUT, result.message
        assert not cell_process_alive(int(pidfile.read_text()))
    finally:
        assert release_workspace(lease) is None


def test_without_the_cell_side_kill_the_maintainer_cannot_confirm_teardown(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    pidfile = lease.parent / "tmp" / "child.pid"
    process = subprocess.Popen(_stubborn(lease, pidfile), cwd=lease.worktree, start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        safe, detail = _teardown_process(process, 0.25)
        assert safe is False and "unconfirmed" in (detail or "")
        assert cell_process_alive(int(pidfile.read_text()))
    finally:
        assert kill_cell_group(process.pid, timeout=5) is None
        process.wait(timeout=5)
        lease._state.process_cleanup_safe = True
        assert release_workspace(lease) is None
