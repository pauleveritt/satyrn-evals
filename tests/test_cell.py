"""The cell module's pure pieces: command shape, environment, profile, kill."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.attempt import LIVE_TRANSCRIPT_NAME, _collect_live_transcript
from satyrn_evals.cell import (
    CELL_PARENT_ENV,
    CELL_PATH_PREFIX_ENV,
    CELL_USER,
    ISOLATION_ENV,
    Isolation,
    cell_command,
    cell_environment,
    cell_gitconfig,
    cell_kill_command,
    cell_unavailable_reason,
    isolation_from,
    kill_cell_group,
    maintainer_ace,
    model_environment,
    share_with_cell,
)


def _completed(code: int, stderr: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess([], code, b"", stderr)


def test_a_cell_command_switches_user_clears_the_environment_and_changes_directory() -> None:
    argv = cell_command(["pi", "--version"], cwd=Path("/w"), environment={"PATH": "/bin", "HOME": "/h"})
    assert argv[:6] == ["sudo", "-n", "-H", "-u", CELL_USER, "--"]
    assert argv[6:10] == ["/usr/bin/env", "-i", "HOME=/h", "PATH=/bin"]
    assert argv[10:13] == ["/bin/sh", "-c", 'umask 007 && cd "$1" && shift && exec "$@"']
    assert argv[13:] == ["satyrn-cell", "/w", "pi", "--version"]


def test_an_empty_cell_command_is_refused() -> None:
    with pytest.raises(ValueError, match="empty"):
        cell_command([], cwd=Path("/w"), environment={})


def test_the_cell_environment_is_the_cells_own_and_names_its_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_OF_THE_MAINTAINER", "x")
    environment = cell_environment(parent=Path("/cells/a"), extra={"K": "v"}, path_prefix=("/fake/bin",))
    assert environment["HOME"] == "/Users/satyrn-cell"
    assert environment["TMPDIR"] == "/cells/a/tmp"
    assert environment["UV_PROJECT_ENVIRONMENT"] == "/cells/a/environment"
    assert environment["GIT_CONFIG_GLOBAL"] == "/cells/a/gitconfig"
    assert environment["PATH"].split(os.pathsep)[0] == "/fake/bin"
    assert environment["K"] == "v"
    assert "SECRET_OF_THE_MAINTAINER" not in environment


def test_the_cell_git_config_names_one_safe_directory_and_an_identity() -> None:
    text = cell_gitconfig(Path("/cells/a/worktree"))
    assert "[safe]\n\tdirectory = /cells/a/worktree\n" in text
    assert f"name = {CELL_USER}" in text


def test_the_model_environment_comes_from_what_the_harness_exported() -> None:
    exported = {CELL_PARENT_ENV: "/cells/a", CELL_PATH_PREFIX_ENV: f"/p1{os.pathsep}/p2"}
    environment = model_environment(exported)
    assert environment["TMPDIR"] == "/cells/a/tmp"
    assert environment["PATH"].startswith(f"/p1{os.pathsep}/p2{os.pathsep}")


def test_the_model_environment_refuses_without_a_workspace_parent() -> None:
    with pytest.raises(ValueError, match=CELL_PARENT_ENV):
        model_environment({})


def test_the_profile_defaults_to_local_and_refuses_an_unknown_one() -> None:
    assert isolation_from({}) is Isolation.LOCAL
    assert isolation_from({ISOLATION_ENV: "isolated"}) is Isolation.ISOLATED
    with pytest.raises(ValueError, match="isolated or local"):
        isolation_from({ISOLATION_ENV: "docker"})


def test_the_cell_kill_targets_a_group_and_never_init() -> None:
    assert cell_kill_command(4242)[-3:] == ["-KILL", "--", "-4242"]
    with pytest.raises(ValueError, match="refusing"):
        cell_kill_command(1)


@pytest.mark.parametrize("code", [0, 1])
def test_a_cell_kill_that_ran_or_found_the_group_empty_succeeds(code: int) -> None:
    assert kill_cell_group(4242, timeout=1, run=lambda *a, **k: _completed(code)) is None


def test_a_cell_kill_that_sudo_refused_is_described() -> None:
    failure = kill_cell_group(4242, timeout=1, run=lambda *a, **k: _completed(2, b"a password is required"))
    assert failure is not None and "password" in failure


def test_the_cell_is_unavailable_when_sudo_refuses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("satyrn_evals.cell.CELLS_ROOT", tmp_path)
    assert "exited 1" in (cell_unavailable_reason(run=lambda *a, **k: _completed(1)) or "")
    assert cell_unavailable_reason(run=lambda *a, **k: _completed(0)) is None


def test_the_cell_is_unavailable_without_the_cells_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("satyrn_evals.cell.CELLS_ROOT", tmp_path / "absent")
    assert "does not exist" in (cell_unavailable_reason(run=lambda *a, **k: _completed(0)) or "")


def test_the_maintainer_ace_is_inherited_by_files_and_directories() -> None:
    ace = maintainer_ace()
    assert ace.startswith("user:") and "file_inherit" in ace and "directory_inherit" in ace and "delete_child" in ace


def test_sharing_widens_group_bits_on_the_maintainers_entries(tmp_path: Path) -> None:
    (tmp_path / "d").mkdir(mode=0o700)
    (tmp_path / "d" / "f").write_text("x")
    (tmp_path / "d" / "f").chmod(0o600)
    share_with_cell(tmp_path)
    assert stat.S_IMODE((tmp_path / "d").stat().st_mode) == 0o2770
    assert stat.S_IMODE((tmp_path / "d" / "f").stat().st_mode) == 0o660


def test_a_live_transcript_is_copied_into_the_attempt_directory(tmp_path: Path) -> None:
    live = tmp_path / "parent" / LIVE_TRANSCRIPT_NAME
    live.parent.mkdir()
    live.write_text('{"type": "agent_start"}\n')
    destination = tmp_path / "attempt" / "transcript.txt"
    destination.parent.mkdir()
    _collect_live_transcript(live, destination)
    assert destination.read_text() == live.read_text()


def test_a_local_transcript_or_a_missing_live_one_is_left_alone(tmp_path: Path) -> None:
    destination = tmp_path / "transcript.txt"
    _collect_live_transcript(destination, destination)
    _collect_live_transcript(tmp_path / "absent.txt", destination)
    assert not destination.exists()
