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
    DELIVER_TIMEOUT_SECONDS,
    ENGINE_REPO_ENV,
    RECEIPT_NAME,
    AdapterError,
    candidate_commit,
    contract_path,
    deliver_argv,
    delivery_environment,
    derive_argv,
    main,
    parse_args,
)

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
    assert calls[2] == ["git", "checkout", "-q", "--detach", COMMIT]
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
