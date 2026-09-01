"""End-to-end attempt: a fake command through the seam. Real subprocess, real oracle."""

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptOutcome, load_attempt_record
from satyrn_evals.cli import main
from satyrn_evals.errors import UsageError
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.receipt import patch_digest
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

FAKE = Path(__file__).parent / "fake_attempt.py"
FAKE_PI = Path(__file__).parent / "fake_pi_v4.py"
KNOWN_GOOD = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"
KNOWN_BROKEN = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-broken.patch"


def _cmd(*args: str) -> list[str]:
    return [sys.executable, str(FAKE), *args]


def _attempt_dir(output: Path) -> Path:
    dirs = [p for p in output.iterdir() if p.is_dir()]
    assert len(dirs) == 1, dirs
    return dirs[0]


def test_known_good_attempt_grades_pass(tmp_path: Path) -> None:
    """Evidence floor: the delivered known-good patch grades pass, fixture named."""
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_GOOD), "--transcript", "wrote the fix"),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.code == "OK"
    assert record.verdict is Verdict.PASS
    attempt_dir = _attempt_dir(output)
    assert (attempt_dir / "patch.diff").read_bytes() == KNOWN_GOOD.read_bytes()
    assert record.patch_digest == patch_digest(KNOWN_GOOD.read_bytes())
    assert record.receipt_path == "receipt.json"
    receipt = json.loads((attempt_dir / "receipt.json").read_text())
    assert receipt["verdict"] == "pass"
    assert receipt["patch_digest"] == record.patch_digest
    assert load_attempt_record(attempt_dir / "attempt.json") == record


def test_known_broken_attempt_grades_fail(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_BROKEN)),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.FAIL


def test_no_patch_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--no-patch"),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "NO_PATCH"
    attempt_dir = _attempt_dir(output)
    assert not (attempt_dir / "patch.diff").exists()
    assert (attempt_dir / "transcript.txt").exists()  # transcript still persisted
    assert not (attempt_dir / "receipt.json").exists()


def test_invalid_patch_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--bad-patch"),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "PATCH_INVALID"


def test_invalid_utf8_patch_is_refused(tmp_path: Path) -> None:
    """A patch with invalid UTF-8 bytes is refused as PATCH_INVALID, never
    reaching grading (which reads the patch strictly): refusal is the default
    outcome of a failure, not a traceback from grade()."""
    bad = tmp_path / "invalid-utf8.patch"
    bad.write_bytes(
        b"diff --git a/solution.py b/solution.py\n"
        b"--- a/solution.py\n"
        b"+++ b/solution.py\n"
        b"@@ -1,2 +1,2 @@\n"
        b" def format_number(n):\n"
        b"-    return n\n"
        b"+    return n + \xff\n"
    )
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(bad)),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "PATCH_INVALID"
    assert not (_attempt_dir(output) / "receipt.json").exists()  # refused => no receipt


def test_no_transcript_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_GOOD), "--no-transcript"),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "TRANSCRIPT_MISSING"
    attempt_dir = _attempt_dir(output)
    assert (attempt_dir / "patch.diff").exists()  # patch still persisted
    assert not (attempt_dir / "transcript.txt").exists()


def test_empty_transcript_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_GOOD), "--empty-transcript"),
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "TRANSCRIPT_EMPTY"


def test_nonzero_exit_still_graded(tmp_path: Path) -> None:
    """Artifact-driven: a nonzero exit with valid artifacts is still attempted + graded."""
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(KNOWN_GOOD), "--exit", "7"),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.PASS
    assert record.command_exit == 7


def test_non_allowlisted_patch_is_unavailable(tmp_path: Path) -> None:
    bad = tmp_path / "touches-tests.patch"
    bad.write_text(
        "diff --git a/test_solution.py b/test_solution.py\n"
        "--- a/test_solution.py\n"
        "+++ b/test_solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " from solution import format_number\n"
        "+# tampered\n"
    )
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(bad)),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.UNAVAILABLE
    receipt = json.loads((_attempt_dir(output) / "receipt.json").read_text())
    assert "non-source" in receipt["reason"]


def test_unappliable_patch_is_unavailable(tmp_path: Path) -> None:
    bad = tmp_path / "no-apply.patch"
    bad.write_text(
        "diff --git a/solution.py b/solution.py\n"
        "--- a/solution.py\n"
        "+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def double(n):\n"
        "-    return n + 999\n"
        "+    return n * 2\n"
    )
    output = tmp_path / "attempts"
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_cmd("--patch", str(bad)),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.UNAVAILABLE
    receipt = json.loads((_attempt_dir(output) / "receipt.json").read_text())
    assert "apply" in receipt["reason"]


def test_command_not_found_is_usage_error(tmp_path: Path) -> None:
    output = tmp_path / "attempts"
    with pytest.raises(UsageError, match="cannot start"):
        attempt(
            task="format_number",
            tasks_root=DEFAULT_TASKS_ROOT,
            output=output,
            command=["definitely-not-a-real-command-xyz-123"],
        )
    # usage writes nothing: the attempt directory was removed again
    assert not any(output.iterdir())


def test_relative_output_resolves_in_caller_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A relative --output must not leak relative seam paths to the command:
    the command's cwd is the disposable workspace, so the env paths it
    receives must be absolute (regression: default `--output attempts`)."""
    monkeypatch.chdir(tmp_path)
    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=Path("attempts"),
        command=_cmd("--patch", str(KNOWN_GOOD)),
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.PASS
    dirs = [p for p in (tmp_path / "attempts").iterdir() if p.is_dir()]
    assert len(dirs) == 1
    assert (dirs[0] / "patch.diff").exists()
    assert (dirs[0] / "attempt.json").exists()
    assert (dirs[0] / "receipt.json").exists()


def test_attempt_cli_success_refusal_and_usage(tmp_path: Path) -> None:
    ok_output = tmp_path / "ok"
    code = main(
        [
            "attempt",
            "--tasks-root", str(DEFAULT_TASKS_ROOT),
            "--output", str(ok_output),
            "format_number",
            "--", sys.executable, str(FAKE), "--patch", str(KNOWN_GOOD),
        ]
    )
    assert code == 0
    record = load_attempt_record(_attempt_dir(ok_output) / "attempt.json")
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.PASS

    refused_output = tmp_path / "refused"
    code = main(
        [
            "attempt",
            "--tasks-root", str(DEFAULT_TASKS_ROOT),
            "--output", str(refused_output),
            "format_number",
            "--", sys.executable, str(FAKE), "--no-patch",
        ]
    )
    assert code == 3
    record = load_attempt_record(_attempt_dir(refused_output) / "attempt.json")
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "NO_PATCH"

    usage_output = tmp_path / "usage"
    code = main(
        [
            "attempt",
            "--tasks-root", str(DEFAULT_TASKS_ROOT),
            "--output", str(usage_output),
            "format_number",
            "--", "definitely-not-a-real-command-xyz-123",
        ]
    )
    assert code == 2
    assert not any(usage_output.iterdir())


def _engine_repo() -> Path:
    configured = os.environ.get("SATYRN_V4_ENGINE_REPO")
    root = (
        Path(configured)
        if configured is not None
        else Path(__file__).parents[3] / "satyrn-engine"
    )
    required = (
        root / "src" / "satyrn_engine" / "attempt.py",
        root / "packages" / "engine" / "mutator.ts",
        root / "tools" / "exercise_mutator.mjs",
    )
    if not all(path.is_file() for path in required):
        pytest.skip("an E5 satyrn-engine source checkout is required")
    if shutil.which("node") is None:
        pytest.skip("Node is required for the real E5 integration")
    if shutil.which("uv") is None:
        pytest.skip("uv is required for the real E5 integration")
    if not (root / ".venv" / "bin" / "satyrn-engine").is_file():
        pytest.skip("the E5 checkout needs an installed satyrn-engine environment")
    return root.resolve()


def _engine_command(engine_repo: Path, uv: Path) -> list[str]:
    return [
        os.fspath(uv),
        "run",
        "--project",
        os.fspath(engine_repo),
        "satyrn-engine",
        "attempt",
        "--model=fixture/model",
        "--",
    ]


def _configure_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    engine_repo: Path,
) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pi = bin_dir / "pi"
    shutil.copyfile(FAKE_PI, pi)
    pi.chmod(0o755)
    monkeypatch.setenv(
        "PATH", os.fspath(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    )
    monkeypatch.setenv("SATYRN_ENGINE_REPO", os.fspath(engine_repo))
    monkeypatch.setenv("UV_NO_SYNC", "1")
    monkeypatch.setenv("UV_PYTHON_DOWNLOADS", "never")
    monkeypatch.setenv("UV_CACHE_DIR", os.fspath(tmp_path / "uv-cache"))
    uv = shutil.which("uv")
    assert uv is not None
    return Path(uv).resolve()


def test_real_e5_attempt_produces_persisted_patch_and_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine_repo = _engine_repo()
    uv = _configure_engine(tmp_path, monkeypatch, engine_repo)
    output = tmp_path / "attempts"

    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_engine_command(engine_repo, uv),
        timeout=30,
    )

    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is Verdict.PASS
    assert record.command_exit == 0
    assert record.workspace_base_sha is not None
    attempt_dir = _attempt_dir(output)
    patch = (attempt_dir / "patch.diff").read_text()
    assert "solution.py" in patch
    assert 'sign = "-" if n < 0 else ""' in patch
    transcript = (attempt_dir / "transcript.txt").read_text()
    assert '"type": "agent_start"' in transcript
    agent_start = json.loads(transcript.splitlines()[0])
    assert not Path(agent_start["cwd"]).exists()
    assert record.command[-1] == os.fspath(
        DEFAULT_TASKS_ROOT / "format_number" / "engine-contract.yaml"
    )
    assert (DEFAULT_TASKS_ROOT / "format_number" / "base" / "solution.py").read_text() == (
        "def format_number(n: int) -> str:\n    return str(n)\n"
    )


def test_real_e5_failure_preserves_transcript_and_refuses_without_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine_repo = _engine_repo()
    uv = _configure_engine(tmp_path, monkeypatch, engine_repo)
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", "fail")
    output = tmp_path / "attempts"

    record = attempt(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=output,
        command=_engine_command(engine_repo, uv),
        timeout=30,
    )

    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == "NO_PATCH"
    assert record.command_exit is not None and record.command_exit != 0
    assert record.patch_path is None
    assert record.transcript_path == "transcript.txt"
    attempt_dir = _attempt_dir(output)
    transcript_path = attempt_dir / "transcript.txt"
    transcript = transcript_path.read_text()
    assert '"reason": "fixture failure"' in transcript
    assert record.transcript_digest == patch_digest(transcript_path.read_bytes())
    agent_start = json.loads(transcript.splitlines()[0])
    assert not Path(agent_start["cwd"]).exists()
    assert not (attempt_dir / "receipt.json").exists()
