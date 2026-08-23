"""Real Git/process evidence for the V4 workspace lifecycle."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

import satyrn_evals.workspace as workspace_module
from satyrn_evals.workspace import WorkspaceCode, run_workspace

pytestmark = pytest.mark.integration

PROBE = Path(__file__).parent / "workspace_probe.py"


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
    )


def _base(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    base.mkdir()
    (base / "plain.txt").write_text("plain\n")
    executable = base / "run"
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    (base / "link").symlink_to("plain.txt")
    return base


def test_real_detached_workspace_is_exact_clean_and_environment_isolated(
    tmp_path: Path,
) -> None:
    base = _base(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    observation = output / "observation.json"
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_DIR": "/caller/.git",
            "GIT_WORK_TREE": "/caller",
            "GIT_NAMESPACE": "caller",
        }
    )

    result = run_workspace(
        base=base,
        protected_paths=(tmp_path, output),
        command=(sys.executable, os.fspath(PROBE), "--observation", os.fspath(observation)),
        environment=environment,
    )

    assert result.code is WorkspaceCode.OK
    assert result.command_exit == 0
    assert result.base_sha is not None
    recorded = json.loads(observation.read_text())
    assert recorded == {
        "cwd": recorded["cwd"],
        "head": result.base_sha,
        "detached": True,
        "status": "",
        "git_dir": None,
        "git_work_tree": None,
        "git_namespace": None,
        "terminal_prompt": "0",
        "plain": "plain\n",
        "link_target": "plain.txt",
        "executable": True,
        "filtered": None,
    }
    assert not Path(recorded["cwd"]).exists()
    assert (base / "plain.txt").read_text() == "plain\n"


def test_hostile_tmpdir_inside_base_is_not_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _base(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    observation = output / "observation.json"
    monkeypatch.setattr(workspace_module.tempfile, "tempdir", os.fspath(base))

    result = run_workspace(
        base=base,
        protected_paths=(tmp_path, output),
        command=(sys.executable, os.fspath(PROBE), "--observation", os.fspath(observation)),
        environment=os.environ,
    )

    assert result.code is WorkspaceCode.OK
    recorded = json.loads(observation.read_text())
    assert not Path(recorded["cwd"]).is_relative_to(base)
    assert set(base.iterdir()) == {
        base / "plain.txt",
        base / "run",
        base / "link",
    }


def test_hostile_tmpdir_inside_registered_sibling_worktree_is_not_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caller = tmp_path / "caller"
    caller.mkdir()
    _git(caller, "init", "-q")
    (caller / "tracked.txt").write_text("caller\n")
    _git(caller, "add", "tracked.txt")
    _git(
        caller,
        "-c",
        "user.name=fixture",
        "-c",
        "user.email=fixture@example.com",
        "commit",
        "-qm",
        "base",
    )
    sibling = tmp_path / "sibling"
    _git(caller, "worktree", "add", "--detach", os.fspath(sibling), "HEAD")
    hostile = sibling / "tmp"
    hostile.mkdir()
    base = _base(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    observation = output / "observation.json"
    monkeypatch.setattr(workspace_module.tempfile, "tempdir", os.fspath(hostile))

    try:
        result = run_workspace(
            base=base,
            protected_paths=(caller / "nested", output),
            command=(
                sys.executable,
                os.fspath(PROBE),
                "--observation",
                os.fspath(observation),
            ),
            environment=os.environ,
        )
        assert result.code is WorkspaceCode.OK
        synthetic = Path(json.loads(observation.read_text())["cwd"])
        assert not synthetic.is_relative_to(sibling)
        assert subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=caller,
            check=True,
            capture_output=True,
        ).stdout == b""
    finally:
        _git(caller, "worktree", "remove", "--force", os.fspath(sibling))


def test_hostile_tmpdir_inside_outer_enclosing_repository_is_not_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outer = tmp_path / "outer"
    outer.mkdir()
    _git(outer, "init", "-q")
    (outer / ".gitignore").write_text("nested/\ntmp/\n")
    _git(outer, "add", ".gitignore")
    _git(
        outer,
        "-c",
        "user.name=fixture",
        "-c",
        "user.email=fixture@example.com",
        "commit",
        "-qm",
        "outer",
    )
    nested = outer / "nested"
    nested.mkdir()
    _git(nested, "init", "-q")
    (nested / "tracked.txt").write_text("nested\n")
    _git(nested, "add", "tracked.txt")
    _git(
        nested,
        "-c",
        "user.name=fixture",
        "-c",
        "user.email=fixture@example.com",
        "commit",
        "-qm",
        "nested",
    )
    hostile = outer / "tmp"
    hostile.mkdir()
    base = _base(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    observation = output / "observation.json"
    monkeypatch.setattr(workspace_module.tempfile, "tempdir", os.fspath(hostile))

    result = run_workspace(
        base=base,
        protected_paths=(nested / "missing", output),
        command=(
            sys.executable,
            os.fspath(PROBE),
            "--observation",
            os.fspath(observation),
        ),
        environment=os.environ,
    )

    assert result.code is WorkspaceCode.OK
    synthetic = Path(json.loads(observation.read_text())["cwd"])
    assert not synthetic.is_relative_to(outer)
    assert not synthetic.is_relative_to(nested)
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=outer,
        check=True,
        capture_output=True,
    ).stdout == b""


def test_hostile_tmpdir_inside_enclosing_bare_repository_is_not_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bare = tmp_path / "caller.git"
    bare.mkdir()
    _git(bare, "init", "--bare", "-q")
    hostile = bare / "hostile"
    hostile.mkdir()
    base = _base(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    observation = output / "observation.json"
    monkeypatch.setattr(workspace_module.tempfile, "tempdir", os.fspath(hostile))

    result = run_workspace(
        base=base,
        protected_paths=(bare / "objects", output),
        command=(
            sys.executable,
            os.fspath(PROBE),
            "--observation",
            os.fspath(observation),
        ),
        environment=os.environ,
    )

    assert result.code is WorkspaceCode.OK
    synthetic = Path(json.loads(observation.read_text())["cwd"])
    assert not synthetic.is_relative_to(bare)
    assert set(hostile.iterdir()) == set()


def test_ignored_task_base_file_is_materialized(tmp_path: Path) -> None:
    base = _base(tmp_path)
    (base / ".gitignore").write_text("ignored.txt\n")
    (base / "ignored.txt").write_text("persisted\n")
    output = tmp_path / "output"
    output.mkdir()
    observation = output / "ignored.txt"

    result = run_workspace(
        base=base,
        protected_paths=(tmp_path, output),
        command=(
            sys.executable,
            "-c",
            "from pathlib import Path; "
            f"Path({os.fspath(observation)!r}).write_text(Path('ignored.txt').read_text())",
        ),
        environment=os.environ,
    )

    assert result.code is WorkspaceCode.OK
    assert observation.read_text() == "persisted\n"


@pytest.mark.skipif(os.name != "posix", reason="process-group proof is POSIX-only")
def test_timeout_reaps_group_before_workspace_cleanup(tmp_path: Path) -> None:
    base = _base(tmp_path)
    marker = tmp_path / "late-marker"

    result = run_workspace(
        base=base,
        protected_paths=(tmp_path,),
        command=(sys.executable, os.fspath(PROBE), "--delay-marker", os.fspath(marker)),
        environment=os.environ,
        timeout=0.1,
        teardown_grace=0.1,
    )

    assert result.code is WorkspaceCode.COMMAND_TIMEOUT
    assert result.command_exit is None
    time.sleep(0.7)
    assert not marker.exists()


def test_locked_worktree_reports_retained_recovery_path(tmp_path: Path) -> None:
    base = _base(tmp_path)

    result = run_workspace(
        base=base,
        protected_paths=(tmp_path,),
        command=(sys.executable, os.fspath(PROBE), "--lock"),
        environment=os.environ,
    )

    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert result.retained_path is not None
    retained_parent = Path(result.retained_path)
    assert retained_parent.is_dir()
    retained = retained_parent / "worktree"
    repository = retained_parent / "seed"
    try:
        subprocess.run(
            ["git", "worktree", "unlock", os.fspath(retained)],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "remove", "--force", os.fspath(retained)],
            cwd=repository,
            check=True,
            capture_output=True,
        )
    finally:
        shutil.rmtree(retained_parent)


def test_missing_locked_worktree_reports_existing_parent(tmp_path: Path) -> None:
    base = _base(tmp_path)

    result = run_workspace(
        base=base,
        protected_paths=(tmp_path,),
        command=(sys.executable, os.fspath(PROBE), "--lock-and-remove"),
        environment=os.environ,
    )

    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert result.retained_path is not None
    retained_parent = Path(result.retained_path)
    retained = retained_parent / "worktree"
    repository = retained_parent / "seed"
    assert retained_parent.is_dir()
    assert not retained.exists()
    try:
        subprocess.run(
            ["git", "worktree", "unlock", os.fspath(retained)],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "remove", "--force", os.fspath(retained)],
            cwd=repository,
            check=True,
            capture_output=True,
        )
    finally:
        shutil.rmtree(retained_parent)


def test_command_not_found_is_reported_after_clean_workspace_cleanup(
    tmp_path: Path,
) -> None:
    base = _base(tmp_path)
    result = run_workspace(
        base=base,
        protected_paths=(tmp_path,),
        command=("definitely-not-a-command-satyrn",),
        environment=os.environ,
    )
    assert result.code is WorkspaceCode.COMMAND_UNAVAILABLE
    assert "cannot start" in result.message


def test_top_level_git_metadata_is_refused_before_command(tmp_path: Path) -> None:
    base = _base(tmp_path)
    (base / ".git").write_text("gitdir: elsewhere\n")
    result = run_workspace(
        base=base,
        protected_paths=(tmp_path,),
        command=("must-not-run",),
        environment=os.environ,
    )
    assert result.code is WorkspaceCode.WORKSPACE_FAILED
    assert "must not contain" in result.message


def test_child_git_cannot_run_repository_hooks_or_fsmonitor(tmp_path: Path) -> None:
    base = _base(tmp_path)
    sentinel = tmp_path / "hook-fired"
    result = run_workspace(
        base=base,
        protected_paths=(tmp_path,),
        command=(
            sys.executable,
            os.fspath(PROBE),
            "--git-sentinel",
            os.fspath(sentinel),
        ),
        environment=os.environ,
    )
    assert result.code is WorkspaceCode.OK
    assert result.command_exit == 0
    assert not sentinel.exists()


def test_normal_clean_and_smudge_filters_remain_active(tmp_path: Path) -> None:
    base = _base(tmp_path)
    (base / ".gitattributes").write_text("filtered.txt filter=fixture\n")
    (base / "filtered.txt").write_text("working\n")
    clean = tmp_path / "clean-filter"
    sentinel = tmp_path / "filter-called"
    clean.write_text(
        "#!/bin/sh\n"
        f"printf 'clean\\n' >> {os.fspath(sentinel)!r}\n"
        "sed 's/working/stored/g'\n"
    )
    clean.chmod(0o755)
    smudge = tmp_path / "smudge-filter"
    smudge.write_text(
        "#!/bin/sh\n"
        f"printf 'smudge\\n' >> {os.fspath(sentinel)!r}\n"
        "sed 's/stored/working/g'\n"
    )
    smudge.chmod(0o755)
    output = tmp_path / "output"
    output.mkdir()
    observation = output / "observation.json"
    global_config = tmp_path / "gitconfig"
    for key, value in (
        ("filter.fixture.clean", os.fspath(clean)),
        ("filter.fixture.smudge", os.fspath(smudge)),
        ("filter.fixture.required", "true"),
    ):
        subprocess.run(
            ["git", "config", "--file", os.fspath(global_config), key, value],
            check=True,
            capture_output=True,
        )
    environment = dict(os.environ)
    environment["GIT_CONFIG_GLOBAL"] = os.fspath(global_config)
    result = run_workspace(
        base=base,
        protected_paths=(tmp_path, output),
        command=(
            sys.executable,
            os.fspath(PROBE),
            "--observation",
            os.fspath(observation),
            "--filtered",
        ),
        environment=environment,
    )
    assert result.code is WorkspaceCode.OK
    assert json.loads(observation.read_text())["filtered"] == "working\n"
    assert set(sentinel.read_text().splitlines()) == {"clean", "smudge"}


def test_worktree_add_side_effect_then_reported_failure_is_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _base(tmp_path)
    real_git = workspace_module._git
    created: list[Path] = []

    def fail_after_add(
        root: Path,
        args: tuple[str, ...],
        environment: dict[str, str],
        *,
        input_bytes: bytes | None = None,
        allowed: tuple[int, ...] = (0,),
    ) -> subprocess.CompletedProcess[bytes]:
        result = real_git(
            root,
            args,
            environment,
            input_bytes=input_bytes,
            allowed=allowed,
        )
        if "worktree" in args and "add" in args:
            created.append(Path(args[args.index("--detach") + 1]))
            raise workspace_module._WorkspaceError("add reported failure")
        return result

    monkeypatch.setattr(workspace_module, "_git", fail_after_add)
    result = run_workspace(
        base=base,
        protected_paths=(tmp_path,),
        command=("must-not-run",),
        environment=os.environ,
    )
    assert result.code is WorkspaceCode.WORKSPACE_FAILED
    assert "add reported failure" in result.message
    assert len(created) == 1
    assert not created[0].parent.exists()


def test_interrupt_after_registration_preserves_primary_and_cleans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _base(tmp_path)
    real_registered = workspace_module._worktree_registered
    primary = KeyboardInterrupt()
    observed: list[Path] = []

    def interrupt_once(
        repository: Path, worktree: Path, environment: dict[str, str]
    ) -> bool | None:
        value = real_registered(repository, worktree, environment)
        observed.append(worktree)
        if len(observed) == 1:
            raise primary
        return value

    monkeypatch.setattr(workspace_module, "_worktree_registered", interrupt_once)
    with pytest.raises(KeyboardInterrupt) as raised:
        run_workspace(
            base=base,
            protected_paths=(tmp_path,),
            command=("must-not-run",),
            environment=os.environ,
        )
    assert raised.value is primary
    assert len(observed) >= 2
    assert not observed[0].parent.exists()
