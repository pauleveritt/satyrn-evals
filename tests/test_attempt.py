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
    load_attempt_record,
)
from satyrn_evals.errors import HookError, UsageError
from satyrn_evals.receipt import Receipt, write_receipt
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import WorkspaceCode, WorkspaceResult

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

    monkeypatch.setattr(attempt_module, "run_workspace", fake_run_workspace)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=output,
        command=["fake-agent"],
        timeout=timeout,
    )
    return record, _cells(output)[0]


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

    monkeypatch.setattr(attempt_module, "run_workspace", cannot_start)
    output = tmp_path / "attempts"
    with pytest.raises(UsageError, match="cannot start"):
        attempt_module.attempt(
            task="t", tasks_root=tasks_root, output=output, command=["missing-agent"]
        )
    # usage writes nothing: no attempt directory, no record. The
    # content-addressed contract directory is an input, not an artifact.
    assert _cells(output) == []
    assert list(output.rglob("attempt.json")) == []


def test_attempt_uses_an_external_temporary_uv_environment(
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
        assert not environment_root.is_relative_to(task_dir)
        return WorkspaceResult(WorkspaceCode.OK, "ok", 0, "b" * 40)

    monkeypatch.setattr(attempt_module, "run_workspace", fake_workspace)
    attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
    )

    assert observed["PYTHONDONTWRITEBYTECODE"] == "1"
    assert not Path(observed["UV_PROJECT_ENVIRONMENT"]).exists()


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

    monkeypatch.setattr(attempt_module, "run_workspace", refused)
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

    monkeypatch.setattr(attempt_module, "run_workspace", run)
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

    monkeypatch.setattr(
        attempt_module,
        "run_workspace",
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
    monkeypatch.setattr(
        attempt_module,
        "run_workspace",
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

    monkeypatch.setattr(attempt_module, "run_workspace", run)
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

    monkeypatch.setattr(attempt_module, "run_workspace", run)
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

    monkeypatch.setattr(attempt_module, "run_workspace", run)
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

    monkeypatch.setattr(attempt_module, "run_workspace", fake_workspace)
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

    monkeypatch.setattr(attempt_module, "run_workspace", fake_run_workspace)
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

    monkeypatch.setattr(attempt_module, "run_workspace", fake_run_workspace)
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

    monkeypatch.setattr(attempt_module, "run_workspace", fake_run_workspace)
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
