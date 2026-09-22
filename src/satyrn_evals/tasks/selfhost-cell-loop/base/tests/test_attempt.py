import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import satyrn_evals.attempt as attempt_module
from satyrn_evals.attempt import attempt_dir_name, decide_refusal
from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    DeadlinePhase,
    load_attempt_record,
)
from satyrn_evals.deadline import AttemptDeadline
from satyrn_evals.errors import HookError, UsageError
from satyrn_evals.receipt import Receipt, write_receipt
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import (
    WorkspaceCode,
    WorkspacePrepareError,
    WorkspaceReleaseError,
    WorkspaceResult,
)

GOOD_PATCH = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)
TRANSCRIPT = "read the task; wrote the fix\n"


class _FakeLease:
    """Default-tier stand-in for the neutral prepared-workspace boundary.

    ``_environment`` mirrors the real ``PreparedWorkspace``'s private field
    (`src/satyrn_evals/workspace.py:1452`): a copy of the environment handed
    to ``prepare_workspace``, so a caller that mutates
    ``lease._environment`` after the lease is returned -- exactly what
    ``attempt.py``'s engine-spawn fix does -- observably changes what the
    fake "spawn" (``run_prepared_command``) sees, the same as it would for
    the real lease.
    """

    def __init__(self, prepared: dict[str, Any]) -> None:
        self.prepared = prepared
        self.parent = Path("/tmp/fake-prepared-workspace")
        self.base_sha = "b" * 40
        self._environment = dict(prepared.get("environment", {}))


def _install_workspace_double(
    monkeypatch: pytest.MonkeyPatch,
    run: Any,
    *,
    release: Any | None = None,
) -> None:
    """Adapt former ``run_workspace`` doubles to the explicit lease seam."""
    leases: list[_FakeLease] = []

    def prepare(**kwargs: Any) -> _FakeLease:
        lease = _FakeLease(kwargs)
        leases.append(lease)
        return lease

    def run_prepared(lease: _FakeLease, **kwargs: Any) -> WorkspaceResult:
        return run(
            base=lease.prepared["base"],
            protected_paths=lease.prepared["protected_paths"],
            environment=lease._environment,
            overlay=lease.prepared["overlay"],
            **kwargs,
        )

    def release_prepared(lease: _FakeLease, **kwargs: Any) -> str | None:
        if release is None:
            return None
        return release(lease, **kwargs)

    monkeypatch.setattr(attempt_module, "prepare_workspace", prepare)
    monkeypatch.setattr(attempt_module, "run_prepared_command", run_prepared)
    monkeypatch.setattr(attempt_module, "release_workspace", release_prepared)


def _cells(output: Path) -> list[Path]:
    """The attempt directories under `output`.

    V11a Task 7: a task with no hand-authored engine_contract renders one at
    a deterministic, content-addressed path under the output root. That
    directory is a run INPUT, not an attempt artifact, so cell-identity
    assertions skip it.
    """
    from satyrn_evals.engine_contract import CONTRACTS_DIRNAME

    return [p for p in output.iterdir() if p.name != CONTRACTS_DIRNAME]


def _task(tasks_root: Path) -> Path:
    task_dir = tasks_root / "t"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "base" / "solution.py").write_text("def double(n): return n\n")
    (task_dir / "fixtures").mkdir()
    (task_dir / "fixtures" / "known-good.patch").write_text(GOOD_PATCH)
    (task_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "t",
                "contract": "Fix it.",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["test_solution.py::test_one"],
                "source_paths": ["solution.py"],
                "fixtures": {"known_good": "fixtures/known-good.patch"},
            }
        )
    )
    return task_dir


def _run_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patch: bytes | None,
    transcript: bytes | None,
    timeout: float = 123.0,
) -> tuple[AttemptRecord, Path]:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def fake_run_workspace(**kwargs: Any) -> WorkspaceResult:
        command = kwargs["command"]
        env = kwargs["environment"]
        # the generated contract path is appended (V11a Task 7)
        assert command[0] == "fake-agent"
        assert Path(command[-1]).is_file()
        assert kwargs["base"] == tasks_root / "t" / "base"
        assert env[attempt_module.TASK_NAME_ENV] == "t"
        assert env[attempt_module.TASK_CONTRACT_ENV] == "Fix it."
        if patch is not None:
            Path(env[attempt_module.PATCH_ENV]).write_bytes(patch)
        if transcript is not None:
            Path(env[attempt_module.TRANSCRIPT_ENV]).write_bytes(transcript)
        return WorkspaceResult(
            WorkspaceCode.OK,
            "attempt command completed",
            7,
            "b" * 40,
        )

    _install_workspace_double(monkeypatch, fake_run_workspace)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=output,
        command=["fake-agent"],
        timeout=timeout,
    )
    return record, _cells(output)[0]


# --- F8/R13: the local profile never inherits the maintainer's cell variables ---


def test_local_profile_strips_a_stray_isolation_and_cell_parent_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stray SATYRN_ISOLATION/SATYRN_CELL_PARENT in the maintainer's own
    shell must not reach the local-profile command: the adapter would then
    believe it is isolated and try to run as the cell."""
    from satyrn_evals.cell import CELL_PARENT_ENV, ISOLATION_ENV

    monkeypatch.setenv(ISOLATION_ENV, "isolated")
    monkeypatch.setenv(CELL_PARENT_ENV, "/Users/Shared/satyrn-cells/stray")
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    seen: dict[str, str] = {}

    def fake_run_workspace(**kwargs: Any) -> WorkspaceResult:
        seen.update(kwargs["environment"])
        # Leave the patch/transcript unwritten: the attempt refuses NO_PATCH
        # before grading, so nothing here spawns a subprocess (this row is
        # about the exported environment, not the grade path).
        return WorkspaceResult(WorkspaceCode.OK, "attempt command completed", 0, "b" * 40)

    _install_workspace_double(monkeypatch, fake_run_workspace)
    attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts", command=["fake-agent"], timeout=1.0
    )
    assert seen[ISOLATION_ENV] == "local"
    assert CELL_PARENT_ENV not in seen


def test_valid_artifacts_proceed() -> None:
    assert decide_refusal(GOOD_PATCH, TRANSCRIPT) is None


def test_missing_patch_is_no_patch() -> None:
    assert decide_refusal(None, TRANSCRIPT) == "NO_PATCH"


def test_empty_patch_is_no_patch() -> None:
    assert decide_refusal("", TRANSCRIPT) == "NO_PATCH"


def test_whitespace_patch_is_no_patch() -> None:
    assert decide_refusal("   \n", TRANSCRIPT) == "NO_PATCH"


def test_non_diff_patch_is_patch_invalid() -> None:
    assert decide_refusal("this is not a unified diff\n", TRANSCRIPT) == "PATCH_INVALID"


def test_missing_transcript_is_transcript_missing() -> None:
    assert decide_refusal(GOOD_PATCH, None) == "TRANSCRIPT_MISSING"


def test_empty_transcript_is_transcript_empty() -> None:
    assert decide_refusal(GOOD_PATCH, "") == "TRANSCRIPT_EMPTY"


def test_whitespace_transcript_is_transcript_empty() -> None:
    assert decide_refusal(GOOD_PATCH, "  \n") == "TRANSCRIPT_EMPTY"


def test_patch_checked_before_transcript() -> None:
    # both bad: patch fails first (spec: patch checks run first)
    assert decide_refusal(None, None) == "NO_PATCH"
    assert decide_refusal("not a diff\n", None) == "PATCH_INVALID"


def test_attempt_dir_name_is_deterministic_given_when() -> None:
    when = datetime(2026, 8, 18, 14, 15, 23, 123456, tzinfo=UTC)
    assert (
        attempt_dir_name("format_number", when)
        == "format_number-20260818-141523-123456"
    )


def test_attempt_dir_name_changes_with_when() -> None:
    a = attempt_dir_name("t", datetime(2026, 8, 18, 14, 15, 23, 1, tzinfo=UTC))
    b = attempt_dir_name("t", datetime(2026, 8, 18, 14, 15, 23, 2, tzinfo=UTC))
    assert a != b


def test_attempt_rejects_empty_command_before_creating_output(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    output = tmp_path / "attempts"
    with pytest.raises(UsageError, match="command is empty"):
        attempt_module.attempt(
            task="t", tasks_root=tasks_root, output=output, command=[]
        )
    assert not output.exists()


def test_attempt_start_failure_removes_fresh_attempt_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def cannot_start(**_kwargs: object) -> WorkspaceResult:
        return WorkspaceResult(
            WorkspaceCode.COMMAND_UNAVAILABLE,
            "attempt command cannot start: not executable",
            None,
            "b" * 40,
        )

    _install_workspace_double(monkeypatch, cannot_start)
    output = tmp_path / "attempts"
    with pytest.raises(UsageError, match="cannot start"):
        attempt_module.attempt(
            task="t", tasks_root=tasks_root, output=output, command=["missing-agent"]
        )
    # usage writes nothing: no attempt directory, no record. The
    # content-addressed contract directory is an input, not an artifact.
    assert _cells(output) == []
    assert list(output.rglob("attempt.json")) == []


def test_command_unavailable_releases_before_removing_attempt_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    output = tmp_path / "attempts"
    released: list[bool] = []

    def cannot_start(**_kwargs: object) -> WorkspaceResult:
        return WorkspaceResult(
            WorkspaceCode.COMMAND_UNAVAILABLE,
            "attempt command cannot start",
            None,
            "b" * 40,
        )

    def release(_lease: _FakeLease) -> None:
        assert len(_cells(output)) == 1
        released.append(True)
        return None

    _install_workspace_double(monkeypatch, cannot_start, release=release)
    with pytest.raises(UsageError, match="cannot start"):
        attempt_module.attempt(
            task="t", tasks_root=tasks_root, output=output, command=["missing-agent"]
        )
    assert released == [True]
    assert _cells(output) == []


def test_command_unavailable_release_error_names_the_recovery_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def cannot_start(**_kwargs: object) -> WorkspaceResult:
        return WorkspaceResult(
            WorkspaceCode.COMMAND_UNAVAILABLE,
            "attempt command cannot start",
            None,
            "b" * 40,
        )

    primary = MemoryError("release")
    _install_workspace_double(
        monkeypatch,
        cannot_start,
        release=lambda _lease: (_ for _ in ()).throw(primary),
    )
    with pytest.raises(MemoryError) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["missing-agent"],
        )

    assert raised.value is primary
    assert primary.__notes__ == [
        "command start failed and workspace release is unconfirmed; "
        "retained at /tmp/fake-prepared-workspace"
    ]


def test_attempt_uses_a_durable_temporary_uv_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The model workspace gets no project venv or bytecode residue."""
    tasks_root = tmp_path / "tasks"
    task_dir = _task(tasks_root)
    observed: dict[str, str] = {}

    def fake_workspace(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        observed.update(environment)
        environment_root = Path(environment["UV_PROJECT_ENVIRONMENT"])
        assert environment_root.is_dir()
        assert environment_root.is_relative_to(tmp_path / "attempts")
        assert not environment_root.is_relative_to(task_dir)
        return WorkspaceResult(WorkspaceCode.OK, "ok", 0, "b" * 40)

    _install_workspace_double(monkeypatch, fake_workspace)
    attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
    )

    assert observed["PYTHONDONTWRITEBYTECODE"] == "1"
    assert not Path(observed["UV_PROJECT_ENVIRONMENT"]).exists()


def test_engine_spawn_drops_uv_project_environment_workspace_prep_keeps_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 13b: the E5 wrapper's own env lacks it; workspace prep's has it.

    `uv run --project ENGINE satyrn-engine ...` names its own project; a
    UV_PROJECT_ENVIRONMENT pointed at the attempt's empty private directory
    makes uv treat that directory as the engine's virtualenv and, under
    UV_NO_SYNC=1, fail to spawn `satyrn-engine` at all (Task 13 report).
    """
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    prepared_environment: dict[str, str] = {}
    spawned_environment: dict[str, str] = {}

    def fake_workspace(**kwargs: Any) -> WorkspaceResult:
        spawned_environment.update(kwargs["environment"])
        return WorkspaceResult(WorkspaceCode.OK, "ok", 0, "b" * 40)

    _install_workspace_double(monkeypatch, fake_workspace)
    installed_prepare = attempt_module.prepare_workspace

    def capturing_prepare(**kwargs: Any) -> _FakeLease:
        lease = installed_prepare(**kwargs)
        prepared_environment.update(lease.prepared["environment"])
        return lease

    monkeypatch.setattr(attempt_module, "prepare_workspace", capturing_prepare)

    attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["uv", "run", "--project", "/engine/repo", "satyrn-engine", "attempt"],
    )

    assert "UV_PROJECT_ENVIRONMENT" in prepared_environment
    assert "UV_PROJECT_ENVIRONMENT" not in spawned_environment


def test_non_engine_spawn_keeps_uv_project_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling of the engine test: a Bare-Pi command's spawn env keeps it."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    spawned_environment: dict[str, str] = {}

    def fake_workspace(**kwargs: Any) -> WorkspaceResult:
        spawned_environment.update(kwargs["environment"])
        return WorkspaceResult(WorkspaceCode.OK, "ok", 0, "b" * 40)

    _install_workspace_double(monkeypatch, fake_workspace)
    attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
    )

    assert "UV_PROJECT_ENVIRONMENT" in spawned_environment


def test_attempt_environment_cleanup_failure_is_not_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unremoved private environment remains visible to the caller."""
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    cleanup_error = PermissionError("environment is busy")

    def fail_cleanup(path: Path) -> None:
        assert path == attempt_dir / "environment"
        raise cleanup_error

    monkeypatch.setattr(attempt_module.shutil, "rmtree", fail_cleanup)

    with (
        pytest.raises(PermissionError) as raised,
        attempt_module._attempt_environment(attempt_dir, None) as environment,
    ):
        assert Path(environment) == attempt_dir / "environment"

    assert raised.value is cleanup_error
    assert (attempt_dir / "environment").is_dir()


@pytest.mark.parametrize(
    ("patch", "transcript", "code"),
    [
        (None, TRANSCRIPT.encode(), AttemptCode.NO_PATCH),
        (GOOD_PATCH.encode(), None, AttemptCode.TRANSCRIPT_MISSING),
        (
            GOOD_PATCH.encode() + b"\xff\n",
            TRANSCRIPT.encode(),
            AttemptCode.PATCH_INVALID,
        ),
    ],
)
def test_attempt_records_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patch: bytes | None,
    transcript: bytes | None,
    code: AttemptCode,
) -> None:
    record, attempt_dir = _run_attempt(tmp_path, monkeypatch, patch, transcript)
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == code
    assert record.command_exit == 7
    assert record.patch_path == ("patch.diff" if patch is not None else None)
    assert record.transcript_path == (
        "transcript.txt" if transcript is not None else None
    )
    assert json.loads((attempt_dir / "attempt.json").read_text())["code"] == code


def test_refusal_record_carries_the_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The timeout is durable on refused cells too — summarize needs it."""
    record, _attempt_dir = _run_attempt(
        tmp_path, monkeypatch, None, TRANSCRIPT.encode(), timeout=123.0
    )
    assert record.code is AttemptCode.NO_PATCH
    assert record.timeout == 123.0


@pytest.mark.parametrize(
    ("workspace_code", "attempt_code", "retained"),
    [
        (WorkspaceCode.WORKSPACE_FAILED, AttemptCode.WORKSPACE_FAILED, None),
        (WorkspaceCode.COMMAND_TIMEOUT, AttemptCode.COMMAND_TIMEOUT, None),
        (
            WorkspaceCode.CLEANUP_FAILED,
            AttemptCode.CLEANUP_FAILED,
            "/tmp/retained-worktree",
        ),
    ],
)
def test_attempt_records_workspace_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workspace_code: WorkspaceCode,
    attempt_code: AttemptCode,
    retained: str | None,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def refused(**_kwargs: object) -> WorkspaceResult:
        return WorkspaceResult(
            workspace_code,
            f"workspace result: {workspace_code}",
            None,
            "b" * 40,
            retained,
        )

    _install_workspace_double(monkeypatch, refused)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code is attempt_code
    assert record.message == f"workspace result: {workspace_code}"
    assert record.command_exit is None
    assert record.workspace_base_sha == "b" * 40
    assert record.retained_path == retained


def test_preparation_retention_becomes_a_durable_cleanup_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A preparation lease that cannot be cleaned is never silently lost."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    monkeypatch.setattr(
        attempt_module,
        "prepare_workspace",
        lambda **_kwargs: (_ for _ in ()).throw(
            WorkspacePrepareError("repository setup failed", "/tmp/retained")
        ),
    )
    monkeypatch.setattr(
        attempt_module,
        "run_prepared_command",
        lambda *_args, **_kwargs: pytest.fail("command must not start"),
    )

    record = attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
    )

    assert record.code is AttemptCode.CLEANUP_FAILED
    assert record.retained_path == "/tmp/retained"


def test_workspace_refusal_rejects_unhandled_code() -> None:
    unavailable = WorkspaceResult(
        WorkspaceCode.COMMAND_UNAVAILABLE,
        "unavailable",
        None,
        "a" * 40,
    )
    with pytest.raises(AssertionError, match="unexpected workspace outcome"):
        attempt_module._workspace_refusal(unavailable)


@pytest.mark.parametrize(
    ("workspace_code", "expected_code", "retained"),
    [
        (
            WorkspaceCode.CLEANUP_FAILED,
            AttemptCode.CLEANUP_FAILED,
            "/tmp/retained-worktree",
        ),
        (WorkspaceCode.OK, AttemptCode.PATCH_INVALID, None),
    ],
)
def test_artifact_read_failure_cannot_hide_workspace_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workspace_code: WorkspaceCode,
    expected_code: AttemptCode,
    retained: str | None,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        Path(kwargs["environment"][attempt_module.PATCH_ENV]).mkdir()
        return WorkspaceResult(
            workspace_code,
            "workspace cleanup failed" if retained else "attempt command completed",
            0 if workspace_code is WorkspaceCode.OK else None,
            "b" * 40,
            retained,
        )

    _install_workspace_double(monkeypatch, run)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )

    assert record.code is expected_code
    assert record.retained_path == retained
    assert "not a regular file" in record.message
    attempt_dir = _cells(output)[0]
    assert (
        json.loads((attempt_dir / "attempt.json").read_text())["code"] == expected_code
    )


@pytest.mark.parametrize("primary", [KeyboardInterrupt(), MemoryError("read")])
def test_artifact_baseexception_preserves_cleanup_recovery_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    primary: BaseException,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    retained = "/tmp/retained-worktree"

    _install_workspace_double(
        monkeypatch,
        lambda **_kwargs: WorkspaceResult(
            WorkspaceCode.CLEANUP_FAILED,
            "workspace cleanup failed",
            None,
            "b" * 40,
            retained,
        ),
    )
    monkeypatch.setattr(
        attempt_module,
        "_read_artifact",
        lambda *_args: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(type(primary)) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["fake-agent"],
        )

    assert raised.value is primary
    assert primary.__notes__ == [f"workspace cleanup failed; retained at {retained}"]


def test_artifact_baseexception_without_cleanup_evidence_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    primary = KeyboardInterrupt()
    _install_workspace_double(
        monkeypatch,
        lambda **_kwargs: WorkspaceResult(
            WorkspaceCode.OK, "attempt command completed", 0, "b" * 40
        ),
    )
    monkeypatch.setattr(
        attempt_module,
        "_read_artifact",
        lambda *_args: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(KeyboardInterrupt) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["fake-agent"],
        )

    assert raised.value is primary
    assert not hasattr(primary, "__notes__")


@pytest.mark.parametrize("failure", ["digest", "record"])
def test_post_workspace_baseexception_preserves_cleanup_recovery_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    retained = "/tmp/retained-worktree"
    primary = MemoryError(failure)

    def run(**kwargs: Any) -> WorkspaceResult:
        Path(kwargs["environment"][attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(kwargs["environment"][attempt_module.TRANSCRIPT_ENV]).write_text(
            TRANSCRIPT
        )
        return WorkspaceResult(
            WorkspaceCode.CLEANUP_FAILED,
            "workspace cleanup failed",
            0,
            "b" * 40,
            retained,
        )

    _install_workspace_double(monkeypatch, run)
    if failure == "digest":
        monkeypatch.setattr(
            attempt_module,
            "patch_digest",
            lambda _value: (_ for _ in ()).throw(primary),
        )
    else:
        monkeypatch.setattr(
            attempt_module,
            "write_attempt_record",
            lambda *_args: (_ for _ in ()).throw(primary),
        )

    with pytest.raises(MemoryError) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["fake-agent"],
        )

    assert raised.value is primary
    assert primary.__notes__ == [f"workspace cleanup failed; retained at {retained}"]


def test_transcript_read_failure_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        Path(kwargs["environment"][attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(kwargs["environment"][attempt_module.TRANSCRIPT_ENV]).mkdir()
        return WorkspaceResult(
            WorkspaceCode.OK,
            "attempt command completed",
            0,
            "b" * 40,
        )

    _install_workspace_double(monkeypatch, run)
    record = attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
    )
    assert record.code is AttemptCode.TRANSCRIPT_MISSING
    assert "not a regular file" in record.message


@pytest.mark.parametrize("patch", [None, b"  \n"])
def test_patch_absence_precedes_transcript_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patch: bytes | None,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        if patch is not None:
            Path(kwargs["environment"][attempt_module.PATCH_ENV]).write_bytes(patch)
        Path(kwargs["environment"][attempt_module.TRANSCRIPT_ENV]).mkdir()
        return WorkspaceResult(
            WorkspaceCode.OK,
            "attempt command completed",
            0,
            "b" * 40,
        )

    _install_workspace_double(monkeypatch, run)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )

    assert record.code is AttemptCode.NO_PATCH
    attempt_dir = _cells(output)[0]
    assert json.loads((attempt_dir / "attempt.json").read_text())["code"] == "NO_PATCH"


def test_artifact_read_oserror_is_contained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "artifact"
    artifact.write_text("value")
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda _path: (_ for _ in ()).throw(OSError("read")),
    )
    value, error = attempt_module._read_artifact(artifact, "patch")
    assert value is None
    assert error is not None and "cannot read" in error


def test_attempt_appends_opaque_engine_contract_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    task_dir = _task(tasks_root)
    contract = task_dir / "engine-contract.yaml"
    contract.write_bytes(b"opaque\n")
    data = json.loads((task_dir / "manifest.json").read_text())
    data["engine_contract"] = "engine-contract.yaml"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    observed: list[str] = []

    def fake_workspace(**kwargs: Any) -> WorkspaceResult:
        observed.extend(kwargs["command"])
        return WorkspaceResult(WorkspaceCode.OK, "ok", 0, "b" * 40)

    _install_workspace_double(monkeypatch, fake_workspace)
    record = attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["engine", "attempt", "--"],
    )
    expected = os.fspath(contract.resolve())
    assert observed == ["engine", "attempt", "--", expected]
    assert record.command == ("engine", "attempt", "--", expected)


def _grade_boom(*_args: Path, **_kwargs: object) -> Receipt:
    raise HookError("oracle exploded")


def _grade_pass(*_args: Path, **_kwargs: object) -> Receipt:
    """Return PASS only after proving the pre-grade record exists on disk.

    Pins T2's ORDERING: when grading runs, attempt.json must already exist
    as a GRADE_FAILED record. The old code wrote nothing until after
    grading returned, so this double's load fails pre-fix and the success
    sibling is genuinely red.
    """
    receipt_path = Path(_args[2])  # grade(task_dir, patch_path, receipt_path)
    record = load_attempt_record(receipt_path.parent / "attempt.json")
    assert record.code is AttemptCode.GRADE_FAILED
    return Receipt(
        task="t",
        patch_digest="a" * 64,
        verdict=Verdict.PASS,
        reason="",
        evidence=None,
    )


def test_record_is_written_before_grade_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T2: a grading crash must leave a durable, loadable record."""
    monkeypatch.setattr(attempt_module, "grade", _grade_boom)
    record, attempt_dir = _run_attempt(
        tmp_path, monkeypatch, GOOD_PATCH.encode(), TRANSCRIPT.encode()
    )
    assert record.code is AttemptCode.GRADE_FAILED
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is None and record.receipt_path is None
    assert "oracle exploded" in record.message
    loaded = load_attempt_record(attempt_dir / "attempt.json")
    assert loaded.code is AttemptCode.GRADE_FAILED
    assert (attempt_dir / "patch.diff").exists()


def test_successful_grade_rewrites_the_record_ok(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful grade leaves the record OK with verdict + receipt."""
    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    record, attempt_dir = _run_attempt(
        tmp_path, monkeypatch, GOOD_PATCH.encode(), TRANSCRIPT.encode()
    )
    assert record.code is AttemptCode.OK
    assert record.verdict is Verdict.PASS
    assert record.receipt_path == "receipt.json"
    loaded = load_attempt_record(attempt_dir / "attempt.json")
    assert loaded.code is AttemptCode.OK and loaded.verdict is Verdict.PASS


@pytest.mark.parametrize("verdict", [Verdict.PASS, Verdict.FAIL, Verdict.UNAVAILABLE])
def test_grading_deadline_reconciles_a_matching_durable_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verdict: Verdict
) -> None:
    monkeypatch.setattr(attempt_module, "grade", _grade_boom)
    record, attempt_dir = _run_attempt(
        tmp_path, monkeypatch, GOOD_PATCH.encode(), TRANSCRIPT.encode()
    )
    write_receipt(
        attempt_dir / "receipt.json",
        Receipt(record.task, record.patch_digest or "", verdict, "", None),
    )

    class Clock:
        now = 0.0

        def __call__(self) -> float:
            return self.now

    clock = Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    clock.now = 1.0
    finalized = attempt_module._finalize_deadline_from_record(
        attempt_dir, deadline, _FakeLease({})
    )

    assert finalized.code is AttemptCode.OK
    assert finalized.verdict is verdict
    assert finalized.deadline is not None
    assert finalized.deadline.phase is DeadlinePhase.GRADING
    assert finalized.retained_path == "/tmp/fake-prepared-workspace"
    assert load_attempt_record(attempt_dir / "attempt.json") == finalized


def test_grading_deadline_never_promotes_mismatched_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(attempt_module, "grade", _grade_boom)
    record, attempt_dir = _run_attempt(
        tmp_path, monkeypatch, GOOD_PATCH.encode(), TRANSCRIPT.encode()
    )
    write_receipt(
        attempt_dir / "receipt.json",
        Receipt("wrong-task", record.patch_digest or "", Verdict.PASS, "", None),
    )

    class Clock:
        now = 0.0

        def __call__(self) -> float:
            return self.now

    clock = Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    clock.now = 1.0
    finalized = attempt_module._finalize_deadline_from_record(
        attempt_dir, deadline, _FakeLease({})
    )

    assert finalized.code is AttemptCode.GRADE_FAILED
    assert finalized.verdict is None
    assert finalized.deadline is not None


def test_grading_deadline_keeps_grade_failed_when_receipt_read_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(attempt_module, "grade", _grade_boom)
    _record, attempt_dir = _run_attempt(
        tmp_path, monkeypatch, GOOD_PATCH.encode(), TRANSCRIPT.encode()
    )
    receipt_path = attempt_dir / "receipt.json"
    receipt_path.write_text("{}")
    original_read_text = Path.read_text

    def fail_receipt(path: Path, *args: object, **kwargs: object) -> str:
        if path == receipt_path:
            raise OSError("receipt disappeared")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_receipt)

    class Clock:
        now = 0.0

        def __call__(self) -> float:
            return self.now

    clock = Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    clock.now = 1.0
    finalized = attempt_module._finalize_deadline_from_record(
        attempt_dir, deadline, _FakeLease({})
    )

    assert finalized.code is AttemptCode.GRADE_FAILED
    assert finalized.deadline is not None
    assert load_attempt_record(attempt_dir / "attempt.json") == finalized


def test_within_budget_refusal_records_configured_attempt_timeout(
    tmp_path: Path,
) -> None:
    tasks_root = tmp_path / "tasks"
    task_dir = _task(tasks_root)
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()

    class Clock:
        def __call__(self) -> float:
            return 0.0

    record = attempt_module._finish_attempt(
        workspace=WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40),
        task_dir=task_dir,
        attempt_dir=attempt_dir,
        patch_path=attempt_dir / "patch.diff",
        transcript_path=attempt_dir / "transcript.txt",
        manifest=attempt_module.load_manifest(task_dir),
        effective_command=["fake-agent"],
        timeout=30.0,
        rung=None,
        digest="a" * 64,
        deadline=AttemptDeadline(10.0, clock=Clock()),
    )

    assert record.code is AttemptCode.NO_PATCH
    assert record.attempt_timeout == 10.0
    assert record.deadline is None
    assert load_attempt_record(attempt_dir / "attempt.json") == record


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _bounded_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    deadline: AttemptDeadline,
) -> AttemptRecord:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    return attempt_module._attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
        timeout=30.0,
        deadline=deadline,
    )


def test_private_deadline_setup_expiry_writes_refusal_before_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    launched = False

    def prepare(**_kwargs: Any) -> _FakeLease:
        clock.now = 1.0
        with pytest.raises(TimeoutError) as caught:
            deadline.remaining(DeadlinePhase.SETUP)
        raise WorkspacePrepareError("deadline", deadline=caught.value)

    def run(**_kwargs: Any) -> WorkspaceResult:
        nonlocal launched
        launched = True
        raise AssertionError("command must not launch")

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "prepare_workspace", prepare)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert not launched
    assert record.code is AttemptCode.DEADLINE_EXCEEDED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.SETUP
    assert record.retained_path is None


def test_within_budget_attempt_removes_its_temporary_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bounded success still releases its private environment."""
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    _install_workspace_double(
        monkeypatch,
        lambda **_kwargs: WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40),
    )

    _bounded_attempt(tmp_path, monkeypatch, deadline)

    attempt_dir = _cells(tmp_path / "attempts")[0]
    assert not (attempt_dir / "environment").exists()


def test_no_lease_cleanup_expiry_keeps_the_workspace_failure_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A setup failure can cross cleanup without requiring a fake lease."""
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    original_write = attempt_module.write_attempt_record

    def setup_failure(**_kwargs: object) -> _FakeLease:
        raise WorkspacePrepareError("setup failed")

    def write_then_expire(path: Path, record: AttemptRecord) -> None:
        original_write(path, record)
        if record.code is AttemptCode.WORKSPACE_FAILED:
            clock.now = 1.0

    monkeypatch.setattr(attempt_module, "prepare_workspace", setup_failure)
    monkeypatch.setattr(attempt_module, "write_attempt_record", write_then_expire)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.WORKSPACE_FAILED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.CLEANUP
    attempt_dir = _cells(tmp_path / "attempts")[0]
    assert (attempt_dir / "environment").is_dir()


def test_no_lease_preservation_expiry_writes_the_workspace_failure_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A setup failure can expire during artifact preservation without a lease."""
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def setup_failure(**_kwargs: object) -> _FakeLease:
        raise WorkspacePrepareError("setup failed")

    original_read = attempt_module._read_artifact

    def read_then_expire(path: Path, label: str) -> tuple[bytes | None, str | None]:
        result = original_read(path, label)
        if label == "patch":
            clock.now = 1.0
        return result

    monkeypatch.setattr(attempt_module, "prepare_workspace", setup_failure)
    monkeypatch.setattr(attempt_module, "_read_artifact", read_then_expire)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.WORKSPACE_FAILED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.PRESERVATION


def test_private_deadline_after_setup_error_still_writes_setup_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def prepare(**_kwargs: Any) -> _FakeLease:
        clock.now = 1.0
        raise WorkspacePrepareError("repository setup failed")

    _install_workspace_double(monkeypatch, lambda **_kwargs: pytest.fail("launched"))
    monkeypatch.setattr(attempt_module, "prepare_workspace", prepare)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.DEADLINE_EXCEEDED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.SETUP


def test_private_deadline_after_setup_error_keeps_latched_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BetweenSetupClock(_Clock):
        def __call__(self) -> float:
            observed = self.now
            if observed == 0.5:
                self.now = 1.0
            return observed

    clock = BetweenSetupClock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def prepare(**_kwargs: Any) -> _FakeLease:
        clock.now = 0.5
        raise WorkspacePrepareError("repository setup failed")

    _install_workspace_double(monkeypatch, lambda **_kwargs: pytest.fail("launched"))
    monkeypatch.setattr(attempt_module, "prepare_workspace", prepare)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.WORKSPACE_FAILED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.PRESERVATION
    assert record.retained_path is None


def test_private_deadline_command_expiry_retains_available_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        clock.now = 1.0
        deadline.remaining(DeadlinePhase.COMMAND)
        raise AssertionError("unreachable")

    _install_workspace_double(monkeypatch, run)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.DEADLINE_EXCEEDED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.COMMAND
    assert record.patch_digest is not None and record.transcript_digest is not None
    assert record.retained_path == "/tmp/fake-prepared-workspace"


def test_deadline_refusal_keeps_unreadable_artifact_path_without_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deadline missingness distinguishes an unreadable file from no file."""
    tasks_root = tmp_path / "tasks"
    task_dir = _task(tasks_root)
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    patch_path = attempt_dir / "patch.diff"
    patch_path.write_text(GOOD_PATCH)
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    clock.now = 1.0
    with pytest.raises(TimeoutError):
        deadline.remaining(DeadlinePhase.COMMAND)
    original_read = attempt_module._read_artifact

    def unreadable(path: Path, label: str) -> tuple[bytes | None, str | None]:
        if label == "patch":
            return None, "cannot read patch: permission denied"
        return original_read(path, label)

    monkeypatch.setattr(attempt_module, "_read_artifact", unreadable)
    record = attempt_module._write_deadline_refusal(
        attempt_dir=attempt_dir,
        patch_path=patch_path,
        transcript_path=attempt_dir / "transcript.txt",
        manifest=attempt_module.load_manifest(task_dir),
        effective_command=["fake-agent"],
        timeout=30,
        rung=None,
        digest="a" * 64,
        deadline=deadline,
        workspace_base_sha="b" * 40,
    )

    assert record.patch_path == "patch.diff"
    assert record.patch_digest is None
    assert record.transcript_path is None


def test_private_deadline_precedes_command_unavailable_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)
    released = False

    def run(**_kwargs: Any) -> WorkspaceResult:
        clock.now = 1.0
        return WorkspaceResult(
            WorkspaceCode.COMMAND_UNAVAILABLE, "agent missing", None, "b" * 40
        )

    def release(_lease: _FakeLease) -> str | None:
        nonlocal released
        released = True
        return None

    _install_workspace_double(monkeypatch, run, release=release)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert not released
    assert record.code is AttemptCode.DEADLINE_EXCEEDED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.COMMAND
    assert record.retained_path == "/tmp/fake-prepared-workspace"


def test_private_deadline_preservation_expiry_retains_artifacts_without_grading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class PreservationClock(_Clock):
        def __call__(self) -> float:
            observed = self.now
            if observed == 0.5:
                self.now = 1.0
            return observed

    clock = PreservationClock()
    deadline = AttemptDeadline(1.0, clock=clock)
    graded = False

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        clock.now = 0.5
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    def grade(*_args: Path) -> Receipt:
        nonlocal graded
        graded = True
        raise AssertionError("grading must not start after preservation expiry")

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "grade", grade)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert not graded
    assert record.code is AttemptCode.DEADLINE_EXCEEDED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.PRESERVATION
    assert record.patch_digest is not None and record.transcript_digest is not None
    assert record.retained_path == "/tmp/fake-prepared-workspace"


def test_private_deadline_preservation_keeps_command_timeout_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class PreservationClock(_Clock):
        def __call__(self) -> float:
            observed = self.now
            if observed == 0.5:
                self.now = 1.0
            return observed

    clock = PreservationClock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        clock.now = 0.5
        return WorkspaceResult(
            WorkspaceCode.COMMAND_TIMEOUT, "command timed out", None, "b" * 40
        )

    _install_workspace_double(monkeypatch, run)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.COMMAND_TIMEOUT
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.PRESERVATION
    assert record.retained_path == "/tmp/fake-prepared-workspace"


def test_private_deadline_preservation_keeps_null_exit_workspace_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class PreservationClock(_Clock):
        def __call__(self) -> float:
            observed = self.now
            if observed == 0.5:
                self.now = 1.0
            return observed

    clock = PreservationClock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def run(**_kwargs: Any) -> WorkspaceResult:
        clock.now = 0.5
        return WorkspaceResult(
            WorkspaceCode.WORKSPACE_FAILED, "spool failed", None, None
        )

    _install_workspace_double(monkeypatch, run)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.WORKSPACE_FAILED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.PRESERVATION
    assert record.retained_path == "/tmp/fake-prepared-workspace"


def test_private_deadline_grading_expiry_retains_pregrade_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    def grade(*_args: Path, deadline: AttemptDeadline) -> Receipt:
        clock.now = 1.0
        deadline.remaining(DeadlinePhase.GRADING)
        raise AssertionError("unreachable")

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "grade", grade)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.GRADE_FAILED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.GRADING
    assert record.retained_path == "/tmp/fake-prepared-workspace"


def test_private_deadline_reconciles_receipt_written_before_grading_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    def grade(*args: Path, deadline: AttemptDeadline) -> Receipt:
        receipt = Receipt(
            "t",
            attempt_module.patch_digest(GOOD_PATCH.encode()),
            Verdict.UNAVAILABLE,
            "",
            None,
        )
        write_receipt(args[2], receipt)
        clock.now = 1.0
        deadline.remaining(DeadlinePhase.GRADING)
        raise AssertionError("unreachable")

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "grade", grade)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.OK
    assert record.verdict is Verdict.UNAVAILABLE
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.GRADING


def test_private_deadline_cleanup_expiry_keeps_completed_grade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class CleanupClock(_Clock):
        armed = False
        calls = 0

        def __call__(self) -> float:
            observed = self.now
            if self.armed:
                self.calls += 1
            if self.calls == 3:
                self.now = 1.0
            return observed

    clock = CleanupClock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    def grade(*_args: Path, deadline: AttemptDeadline) -> Receipt:
        clock.now = 0.5
        clock.armed = True
        return Receipt(
            "t",
            attempt_module.patch_digest(GOOD_PATCH.encode()),
            Verdict.PASS,
            "",
            None,
        )

    def release(_lease: _FakeLease, *, deadline: AttemptDeadline) -> str | None:
        deadline.remaining(DeadlinePhase.CLEANUP)
        return None

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "grade", grade)
    monkeypatch.setattr(attempt_module, "release_workspace", release)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.OK
    assert record.verdict is Verdict.PASS
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.CLEANUP
    assert record.deadline.workspace_retained is False
    assert record.retained_path is None


def test_private_deadline_expiry_during_artifact_read_is_preservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    original_read = attempt_module._read_artifact

    def read(path: Path, label: str) -> tuple[bytes | None, str | None]:
        result = original_read(path, label)
        if label == "patch":
            clock.now = 1.0
        return result

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "_read_artifact", read)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.DEADLINE_EXCEEDED
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.PRESERVATION


def test_private_deadline_after_matching_record_write_is_grading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _Clock()
    deadline = AttemptDeadline(1.0, clock=clock)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    def grade(*_args: Path, deadline: AttemptDeadline) -> Receipt:
        return Receipt(
            "t",
            attempt_module.patch_digest(GOOD_PATCH.encode()),
            Verdict.PASS,
            "",
            None,
        )

    original_write = attempt_module.write_attempt_record

    def write(path: Path, record: AttemptRecord) -> None:
        original_write(path, record)
        if record.code is AttemptCode.OK:
            clock.now = 1.0

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "grade", grade)
    monkeypatch.setattr(attempt_module, "write_attempt_record", write)
    record = _bounded_attempt(tmp_path, monkeypatch, deadline)

    assert record.code is AttemptCode.OK
    assert record.deadline is not None
    assert record.deadline.phase is DeadlinePhase.GRADING


def test_attempt_grades_and_records_before_releasing_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lease is not released until receipt and matching record are durable."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    output = tmp_path / "attempts"
    observed: list[str] = []

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    def grade_before_release(*args: Path) -> Receipt:
        receipt = Receipt("t", "a" * 64, Verdict.PASS, "ok", None)
        write_receipt(args[2], receipt)
        return receipt

    def release(_lease: _FakeLease) -> None:
        attempt_dir = _cells(output)[0]
        record = load_attempt_record(attempt_dir / "attempt.json")
        assert record.code is AttemptCode.OK
        assert record.receipt_path == "receipt.json"
        assert (attempt_dir / "receipt.json").is_file()
        observed.append("released")
        return None

    _install_workspace_double(monkeypatch, run, release=release)
    monkeypatch.setattr(attempt_module, "grade", grade_before_release)
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )

    assert record.code is AttemptCode.OK
    assert observed == ["released"]


@pytest.mark.parametrize(
    "release",
    [
        lambda _lease: "/tmp/unsafe-worktree",
        lambda _lease: (_ for _ in ()).throw(
            WorkspaceReleaseError("workspace cleanup is unconfirmed", "/tmp/locked")
        ),
    ],
)
def test_late_workspace_retention_keeps_graded_evidence_regradeable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    release: Any,
) -> None:
    """A late cleanup problem must not replace receipt-derived truth."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    _install_workspace_double(monkeypatch, run, release=release)
    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )

    assert record.code is AttemptCode.OK
    assert record.verdict is Verdict.PASS
    assert record.receipt_path == "receipt.json"
    assert record.retained_path in {"/tmp/unsafe-worktree", "/tmp/locked"}
    assert load_attempt_record(_cells(output)[0] / "attempt.json") == record


def test_late_retention_keeps_a_grade_failure_regradeable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    _install_workspace_double(
        monkeypatch, run, release=lambda _lease: "/tmp/unsafe-worktree"
    )
    monkeypatch.setattr(attempt_module, "grade", _grade_boom)
    record = attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
    )

    assert record.code is AttemptCode.GRADE_FAILED
    assert record.retained_path == "/tmp/unsafe-worktree"
    assert record.receipt_path is None


def test_late_release_baseexception_names_the_recovery_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late release crash does not hide its already-durable evidence."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        environment = kwargs["environment"]
        Path(environment[attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(environment[attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    primary = MemoryError("release")
    _install_workspace_double(
        monkeypatch,
        run,
        release=lambda _lease: (_ for _ in ()).throw(primary),
    )
    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    output = tmp_path / "attempts"
    with pytest.raises(MemoryError) as raised:
        attempt_module.attempt(
            task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
        )

    assert raised.value is primary
    assert primary.__notes__ == [
        "workspace release is unconfirmed; retained at /tmp/fake-prepared-workspace; "
        f"the durable attempt record remains at {_cells(output)[0] / 'attempt.json'}"
    ]
    assert (
        load_attempt_record(_cells(output)[0] / "attempt.json").code is AttemptCode.OK
    )


def test_command_baseexception_releases_the_prepared_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    primary = KeyboardInterrupt()
    released: list[bool] = []

    def run(*_args: object, **_kwargs: object) -> WorkspaceResult:
        raise primary

    def release(_lease: _FakeLease) -> None:
        released.append(True)
        return None

    _install_workspace_double(monkeypatch, run, release=release)
    with pytest.raises(KeyboardInterrupt) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["fake-agent"],
        )
    assert raised.value is primary
    assert released == [True]


def test_primary_command_error_keeps_the_lease_path_when_release_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Release failure is evidence attached to, never replacing, the primary."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    primary = KeyboardInterrupt()

    def run(*_args: object, **_kwargs: object) -> WorkspaceResult:
        raise primary

    _install_workspace_double(
        monkeypatch,
        run,
        release=lambda _lease: (_ for _ in ()).throw(MemoryError("release")),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["fake-agent"],
        )

    assert raised.value is primary
    assert primary.__notes__ == [
        "workspace release raised MemoryError: release; "
        "retained at /tmp/fake-prepared-workspace"
    ]


def test_default_attempt_timeout_is_900_seconds() -> None:
    from satyrn_evals.workspace import DEFAULT_TIMEOUT

    assert DEFAULT_TIMEOUT == 900.0


# --- V11a Task 4: --rung selects the exported contract ---
#
# The rung reaches the executable ONLY as SATYRN_TASK_CONTRACT (spec §4);
# the adapter never sees --rung, which is what keeps V11a and V11b
# independent. These tests read the env the seam is handed.

R1_TEXT = "test_one fails: assert 307 == 303"
R3_TEXT = "Fix it."


def _rung_task(tasks_root: Path, *, contracts: dict[str, str] | None) -> Path:
    """The `_task` fixture above, plus an optional rung map."""
    task_dir = _task(tasks_root)
    data = json.loads((task_dir / "manifest.json").read_text())
    if contracts is not None:
        data["contracts"] = contracts
    (task_dir / "manifest.json").write_text(json.dumps(data))
    return task_dir


def _attempt_with_rung(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    contracts: dict[str, str] | None,
    rung: str | None,
) -> tuple[AttemptRecord, str]:
    """Run one attempt and return (record, the exported contract text)."""
    tasks_root = tmp_path / "tasks"
    _rung_task(tasks_root, contracts=contracts)
    exported: dict[str, str] = {}

    def fake_run_workspace(**kwargs: Any) -> WorkspaceResult:
        env = kwargs["environment"]
        exported["contract"] = env[attempt_module.TASK_CONTRACT_ENV]
        Path(env[attempt_module.PATCH_ENV]).write_bytes(GOOD_PATCH.encode())
        Path(env[attempt_module.TRANSCRIPT_ENV]).write_bytes(TRANSCRIPT.encode())
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    _install_workspace_double(monkeypatch, fake_run_workspace)
    monkeypatch.setattr(
        attempt_module,
        "grade",
        lambda *a, **k: Receipt(
            task="t",
            patch_digest="a" * 64,
            verdict=Verdict.PASS,
            reason="ok",
            evidence=None,
        ),
    )
    record = attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
        timeout=123.0,
        rung=rung,
    )
    return record, exported["contract"]


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_rung_exports_that_rungs_text_and_records_the_rung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record, exported = _attempt_with_rung(
        tmp_path,
        monkeypatch,
        contracts={"R1": R1_TEXT, "R3": R3_TEXT},
        rung="R1",
    )
    assert exported == R1_TEXT
    assert record.rung == "R1"
    assert record.contract_digest == _sha256(R1_TEXT)


def test_no_rung_exports_the_default_contract_and_still_records_a_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling success: the default path records rung=None and a real digest."""
    record, exported = _attempt_with_rung(
        tmp_path,
        monkeypatch,
        contracts={"R1": R1_TEXT, "R3": R3_TEXT},
        rung=None,
    )
    assert exported == "Fix it."
    assert record.rung is None
    assert record.contract_digest == _sha256("Fix it.")


def test_no_rung_on_a_task_with_no_contracts_is_the_default_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling success for the refusal below: no rungs is not an error."""
    record, exported = _attempt_with_rung(
        tmp_path, monkeypatch, contracts=None, rung=None
    )
    assert exported == "Fix it."
    assert record.rung is None


def test_unknown_rung_is_a_usage_error_naming_the_available_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(UsageError, match="R1, R3"):
        _attempt_with_rung(
            tmp_path,
            monkeypatch,
            contracts={"R1": R1_TEXT, "R3": R3_TEXT},
            rung="R9",
        )


def test_rung_on_a_task_with_no_contracts_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(UsageError, match="declares no contracts"):
        _attempt_with_rung(tmp_path, monkeypatch, contracts=None, rung="R1")


# --- V11a Task 7: the generated contract lives at a digest-keyed path ---
#
# Proposal correction 8: a fresh per-attempt path changes the recorded
# command, and compute_summary refuses mixed commands, so a batch would not
# summarize. The path is keyed by the SHA-256 of the rendered bytes, so it is
# stable across the cells of a run and pins the exact bytes.


def _fake_grade(task_dir: Path, patch_path: Path, receipt_path: Path) -> Receipt:
    """A non-spawning grade that writes the receipt summarize later reads."""
    receipt = Receipt(
        task="t",
        patch_digest="a" * 64,
        verdict=Verdict.PASS,
        reason="ok",
        evidence=None,
    )
    write_receipt(receipt_path, receipt)
    return receipt


def _two_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    rungs: tuple[str | None, str | None],
) -> tuple[list[AttemptRecord], Path]:
    tasks_root = tmp_path / "tasks"
    _rung_task(tasks_root, contracts={"R1": R1_TEXT, "R3": R3_TEXT})

    def fake_run_workspace(**kwargs: Any) -> WorkspaceResult:
        env = kwargs["environment"]
        Path(env[attempt_module.PATCH_ENV]).write_bytes(GOOD_PATCH.encode())
        Path(env[attempt_module.TRANSCRIPT_ENV]).write_bytes(TRANSCRIPT.encode())
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    _install_workspace_double(monkeypatch, fake_run_workspace)
    monkeypatch.setattr(attempt_module, "grade", _fake_grade)
    output = tmp_path / "attempts"
    records = [
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=output,
            command=["fake-agent"],
            timeout=123.0,
            rung=rung,
        )
        for rung in rungs
    ]
    return records, output


def test_two_attempts_at_one_rung_record_the_same_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records, output = _two_attempts(tmp_path, monkeypatch, rungs=("R1", "R1"))
    first, second = records
    assert first.command == second.command
    appended = Path(first.command[-1])
    assert appended.is_file()
    assert appended.parent == output / "engine-contracts"
    assert appended.name.endswith(".yaml")


def test_two_attempts_at_one_rung_summarize_and_re_summarize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point of the digest-keyed path: the batch summarizes."""
    from satyrn_evals.rescore import summarize_output
    from satyrn_evals.summary import (
        SUMMARY_NAME,
        absent_pathology,
        compute_summary,
        write_summary,
    )

    records, output = _two_attempts(tmp_path, monkeypatch, rungs=("R1", "R1"))
    cells = [(r.attempt_dir, r, None) for r in records]
    summary = compute_summary(
        cells,
        oracle_visibility="visible",
        pathology=absent_pathology(cells),  # type: ignore[bad-argument-type]  # the doubles' attempt_dir is always set
    )
    assert summary.n == 2 and summary.rung == "R1"
    # the anchor names the run's own cells; summarize rebuilds over it
    write_summary(output / SUMMARY_NAME, summary)
    rebuilt = summarize_output(output, tasks_root=tmp_path / "tasks")
    assert rebuilt.rung == "R1" and rebuilt.command == summary.command
    first = (output / SUMMARY_NAME).read_bytes()
    summarize_output(output, tasks_root=tmp_path / "tasks")
    assert (output / SUMMARY_NAME).read_bytes() == first


def test_two_attempts_at_different_rungs_are_refused_by_the_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling refusal: different rungs render different bytes, so the
    digest-keyed paths differ and the batch is not one batch."""
    from satyrn_evals.summary import absent_pathology, compute_summary

    records, _ = _two_attempts(tmp_path, monkeypatch, rungs=("R1", "R3"))
    first, second = records
    assert first.command[-1] != second.command[-1]
    cells = [(r.attempt_dir, r, None) for r in records]
    with pytest.raises(ValueError, match="mixed commands"):
        compute_summary(
            cells,
            oracle_visibility="visible",
            pathology=absent_pathology(cells),  # type: ignore[bad-argument-type]  # the doubles' attempt_dir is always set
        )


def test_hand_authored_engine_contract_keeps_todays_behaviour(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """format_number declares engine_contract: its own file is appended and
    nothing is generated under the output root."""
    from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

    def fake_run_workspace(**kwargs: Any) -> WorkspaceResult:
        env = kwargs["environment"]
        Path(env[attempt_module.PATCH_ENV]).write_bytes(GOOD_PATCH.encode())
        Path(env[attempt_module.TRANSCRIPT_ENV]).write_bytes(TRANSCRIPT.encode())
        return WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40)

    _install_workspace_double(monkeypatch, fake_run_workspace)
    monkeypatch.setattr(
        attempt_module,
        "grade",
        lambda *a, **k: Receipt(
            task="format_number",
            patch_digest="a" * 64,
            verdict=Verdict.PASS,
            reason="ok",
            evidence=None,
        ),
    )
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=["fake-agent"],
        timeout=123.0,
    )
    assert record.command[-1].endswith("format_number/engine-contract.yaml")
    assert not (output / "engine-contracts").exists()


def test_the_command_learns_the_workspace_base_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The adapter harvests against the commit Evals built, not HEAD."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    seen: dict[str, Any] = {}

    def run(**kwargs: Any) -> WorkspaceResult:
        seen.update(kwargs)
        Path(kwargs["environment"][attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(kwargs["environment"][attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "attempt command completed", 0, "b" * 40)

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts", command=["fake-agent"]
    )
    assert record.code is AttemptCode.OK
    assert seen["extra_environment"] == {attempt_module.BASE_SHA_ENV: "b" * 40}
    assert attempt_module.BASE_SHA_ENV not in seen["environment"]
