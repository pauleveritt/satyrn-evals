"""The Engine adapter's pure surface: arguments, the two engine argvs, the receipt.

No process: ``subprocess.run`` is replaced in the module namespace, as
``test_attempt_pi.py`` does for the Baseline adapter. Every refusal has a
sibling success over the same inputs.
"""

import json
import subprocess
from pathlib import Path

import pytest

from satyrn_evals import attempt_engine, attempt_pi
from satyrn_evals.attempt_engine import (
    CHECKOUT_LOG_NAME,
    DELIVER_TIMEOUT_SECONDS,
    ENGINE_REPO_ENV,
    RECEIPT_NAME,
    AdapterError,
    as_cell,
    candidate_commit,
    checkout_candidate,
    contract_path,
    deliver_argv,
    delivery_environment,
    derive_argv,
    isolated,
    main,
    parse_args,
)
from satyrn_evals.cell import CELL_PARENT_ENV, ISOLATION_ENV
from satyrn_evals.workspace import GIT_SAFETY_CONFIG

ENGINE = Path("/opt/satyrn-engine")
WORKTREE = Path("/w/worktree")
CONTRACT = Path("/w/seed/.git/worktrees/worktree/satyrn/contracts/implement-0123456789ab.yaml")
BASE = "c" * 40
COMMIT = "d" * 40


def test_arguments_take_the_engine_from_the_environment_and_ignore_the_rendered_contract() -> None:
    args = parse_args(["--model", "omlx/m", "/runs/engine-contracts/x.yaml"], {ENGINE_REPO_ENV: str(ENGINE)})
    assert (args.model, args.engine_repo, args.uv_bin) == ("omlx/m", ENGINE, "uv")


@pytest.mark.parametrize(
    ("argv", "environment", "message"),
    [
        ([], {ENGINE_REPO_ENV: "/e"}, "--model"),
        (["--model", "m"], {}, ENGINE_REPO_ENV),
        (["--model", "m", "--rung", "R1"], {ENGINE_REPO_ENV: "/e"}, "unknown adapter argument"),
        (["--model", "m", "a.yaml", "b.yaml"], {ENGINE_REPO_ENV: "/e"}, "unexpected extra argument"),
    ],
)
def test_bad_arguments_are_refused(argv: list[str], environment: dict[str, str], message: str) -> None:
    with pytest.raises(AdapterError, match=message):
        parse_args(argv, environment)


def test_derive_and_deliver_are_the_implement_invocations() -> None:
    args = parse_args(["--model", "omlx/m", "--engine-repo", str(ENGINE), "--uv-bin", "/bin/uv"], {})
    engine = ["/bin/uv", "run", "--project", str(ENGINE), "satyrn-engine"]
    assert derive_argv(args, WORKTREE, "Create calc/helpers.py") == [
        *engine, "derive", "--repo", str(WORKTREE), "--", "Create calc/helpers.py"]
    assert deliver_argv(args, WORKTREE, CONTRACT) == [
        *engine, "deliver", "--repo", str(WORKTREE), "--timeout", str(DELIVER_TIMEOUT_SECONDS), str(CONTRACT),
        "--", *engine, "attempt", "--model=omlx/m", "--", str(CONTRACT)]


def test_the_contract_path_is_read_from_derives_stderr_and_its_absence_refused() -> None:
    assert contract_path(f"warming\nsatyrn-engine: contract {CONTRACT}\n") == CONTRACT
    with pytest.raises(AdapterError, match="derive named no contract"):
        contract_path("satyrn-engine: DERIVE: name at least one tracked file\n")


def test_a_candidate_commit_is_read_from_the_receipt_or_absent() -> None:
    assert candidate_commit(json.dumps({"code": "OK", "candidate_commit": COMMIT})) == COMMIT
    assert candidate_commit(json.dumps({"code": "DIRTY_REPO", "candidate_commit": None})) is None
    assert candidate_commit("") is None


def test_the_engine_runs_without_the_patch_destination_or_the_models_uv_environment() -> None:
    cleaned = delivery_environment(
        {attempt_pi.PATCH_ENV: "/a/patch.diff", attempt_pi.TRANSCRIPT_ENV: "/a/transcript.txt",
         "UV_PROJECT_ENVIRONMENT": "/a/environment", "PATH": "/usr/bin"}
    )
    assert cleaned == {attempt_pi.TRANSCRIPT_ENV: "/a/transcript.txt", "PATH": "/usr/bin"}


@pytest.fixture()
def seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(attempt_pi.CONTRACT_ENV, "Create calc/helpers.py")
    monkeypatch.setenv(attempt_pi.PATCH_ENV, str(tmp_path / "patch.diff"))
    monkeypatch.setenv(attempt_pi.TRANSCRIPT_ENV, str(tmp_path / "transcript.txt"))
    monkeypatch.setenv(attempt_pi.BASE_SHA_ENV, BASE)
    monkeypatch.setenv(ENGINE_REPO_ENV, str(ENGINE))
    monkeypatch.setattr(attempt_engine, "harvest_patch", lambda worktree, base: f"harvested {base}\n")
    return tmp_path


def _fake_run(derive_exit: int, receipt: dict) -> tuple[list[list[str]], object]:
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if "derive" in argv:
            return subprocess.CompletedProcess(argv, derive_exit, "", f"satyrn-engine: contract {CONTRACT}\n")
        if "deliver" in argv:
            return subprocess.CompletedProcess(argv, 0, json.dumps(receipt), None)
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    return calls, run


def test_main_derives_delivers_checks_out_the_candidate_and_harvests(seam: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls, run = _fake_run(0, {"code": "OK", "candidate_commit": COMMIT})
    monkeypatch.setattr(attempt_engine.subprocess, "run", run)
    assert main(["--model", "omlx/m"]) == 0
    assert [call[5] if call[0] != "git" else "git" for call in calls] == ["derive", "deliver", "git"]
    assert calls[2] == ["git", *GIT_SAFETY_CONFIG, "checkout", "-q", "--detach", COMMIT]
    assert json.loads((seam / RECEIPT_NAME).read_text())["candidate_commit"] == COMMIT
    assert (seam / "patch.diff").read_text() == f"harvested {BASE}\n"


def test_main_without_a_candidate_checks_out_nothing_and_still_writes_the_patch(
    seam: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls, run = _fake_run(5, {})
    monkeypatch.setattr(attempt_engine.subprocess, "run", run)
    assert main(["--model", "omlx/m"]) == 5
    assert len(calls) == 1 and "derive" in calls[0]
    assert (seam / "patch.diff").read_text() == f"harvested {BASE}\n"


# --- 2b: the isolated profile ------------------------------------------------


def _args(engine: Path = ENGINE) -> attempt_engine.EngineArgs:
    return parse_args(["--model", "omlx/m", "--engine-repo", str(engine)], {})


def test_under_isolation_the_engine_calls_do_not_sync_the_shared_export() -> None:
    assert derive_argv(_args(), WORKTREE, "req", no_sync=True)[:3] == ["uv", "run", "--no-sync"]
    delivered = deliver_argv(_args(), WORKTREE, CONTRACT, no_sync=True)
    assert delivered.count("--no-sync") == 2
    assert "--no-sync" not in derive_argv(_args(), WORKTREE, "req")


def test_the_local_profile_is_not_isolated() -> None:
    assert isolated(_args(), {}) is False


def _safe_export(tmp_path: Path, name: str = "engine-abc", sha: str = "abc") -> Path:
    export = tmp_path / name
    export.mkdir()
    (export / ".satyrn-engine-export").write_text(f"{sha}\n")
    export.chmod(0o750)
    return export


def test_an_isolated_engine_outside_the_cells_root_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(attempt_engine, "CELLS_ROOT", tmp_path)
    with pytest.raises(AdapterError, match="must be an export under"):
        isolated(_args(Path("/Users/someone/satyrn-engine")), {ISOLATION_ENV: "isolated"})
    export = _safe_export(tmp_path)
    assert isolated(_args(export), {ISOLATION_ENV: "isolated"}) is True


def test_an_isolated_engine_without_a_safe_export_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """F2/R11: a cell-plantable directory under the cells root is refused even
    though it names a marker, once it is group-writable."""
    monkeypatch.setattr(attempt_engine, "CELLS_ROOT", tmp_path)
    export = _safe_export(tmp_path, name="engine-evil")
    export.chmod(0o770)  # group-writable: exactly what a planted directory would be
    with pytest.raises(AdapterError, match="not safe to run"):
        isolated(_args(export), {ISOLATION_ENV: "isolated"})


def test_an_engine_call_as_the_cell_carries_the_transcript_and_the_export_but_not_the_models_uv_environment() -> None:
    exported = {ISOLATION_ENV: "isolated", CELL_PARENT_ENV: "/cells/a", attempt_pi.TRANSCRIPT_ENV: "/cells/a/transcript.txt"}
    argv = as_cell(["uv", "run"], _args(Path("/cells/engine-abc")), exported, Path("/cells/a/worktree"))
    assert "SATYRN_ATTEMPT_TRANSCRIPT=/cells/a/transcript.txt" in argv
    assert "SATYRN_ENGINE_REPO=/cells/engine-abc" in argv
    assert not any(token.startswith("UV_PROJECT_ENVIRONMENT=") for token in argv)
    assert argv[-2:] == ["uv", "run"]


def test_an_engine_call_as_the_cell_without_the_harness_exports_is_refused() -> None:
    with pytest.raises(AdapterError, match="cell environment"):
        as_cell(["uv"], _args(), {ISOLATION_ENV: "isolated"}, WORKTREE)


def test_a_failed_candidate_checkout_is_logged_and_returned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        attempt_engine.subprocess, "run", lambda argv, **kw: subprocess.CompletedProcess(argv, 128, "", "fatal: bad object\n")
    )
    log = tmp_path / CHECKOUT_LOG_NAME
    assert checkout_candidate(COMMIT, log) == 128
    assert "fatal: bad object" in log.read_text()


def test_a_candidate_checkout_that_succeeds_writes_no_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attempt_engine.subprocess, "run", lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "", ""))
    assert checkout_candidate(COMMIT, tmp_path / CHECKOUT_LOG_NAME) == 0
    assert not (tmp_path / CHECKOUT_LOG_NAME).exists()


@pytest.mark.integration
def test_checkout_candidate_never_runs_repository_config_hooks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """F1/R10: a cell-writable repository config must not make the
    maintainer's candidate checkout run a hook."""
    repo = tmp_path / "wt"
    repo.mkdir()
    env = {**__import__("os").environ, "GIT_CONFIG_NOSYSTEM": "1"}

    def git(*args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)

    git("init", "-q")
    (repo / "f.txt").write_text("v1\n")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    marker = tmp_path / "pwned"
    hooks_dir = tmp_path / "evil-hooks"
    hooks_dir.mkdir()
    post_checkout = hooks_dir / "post-checkout"
    post_checkout.write_text(f'#!/bin/sh\ntouch "{marker}"\n')
    post_checkout.chmod(0o755)
    git("config", "core.hooksPath", str(hooks_dir))
    commit = git("rev-parse", "HEAD").stdout.decode().strip()
    monkeypatch.chdir(repo)
    monkeypatch.delenv("GIT_CONFIG_NOSYSTEM", raising=False)
    assert checkout_candidate(commit, tmp_path / CHECKOUT_LOG_NAME) == 0
    assert not marker.exists(), "checkout ran the repository's configured hook"


def test_main_returns_the_checkout_failure_and_still_writes_the_patch(seam: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls, run = _fake_run(0, {"code": "OK", "candidate_commit": COMMIT})

    def failing_checkout(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[0] == "git":
            return subprocess.CompletedProcess(argv, 128, "", "fatal: reference is not a tree\n")
        return run(argv, **kwargs)  # type: ignore[operator]

    monkeypatch.setattr(attempt_engine.subprocess, "run", failing_checkout)
    assert main(["--model", "omlx/m"]) == 128
    assert "reference is not a tree" in (seam / CHECKOUT_LOG_NAME).read_text()
    assert (seam / "patch.diff").read_text() == f"harvested {BASE}\n"
