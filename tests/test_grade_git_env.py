"""T8: grading's git subprocesses run in the cleaned environment."""

from pathlib import Path

import pytest

from satyrn_evals import grade as grade_module
from satyrn_evals.errors import ApplyError
from satyrn_evals.workspace import GIT_SAFETY_CONFIG


def test_apply_patch_passes_env_through_and_leads_with_safety_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(argv: list[str], **kwargs: object) -> object:
        env = kwargs.get("env")
        calls.append((argv, env if isinstance(env, dict) else {}))
        return type("R", (), {"returncode": 0, "stderr": b""})()

    monkeypatch.setattr(grade_module.subprocess, "run", fake_run)
    git_env = {"MARKER": "1"}  # whatever clean_git_environment produced
    grade_module._apply_patch(
        tmp_path / "work", "diff --git a/x b/x\n", git_env
    )
    assert len(calls) == 2  # init then apply
    for argv, env in calls:
        assert argv[1 : 1 + len(GIT_SAFETY_CONFIG)] == list(GIT_SAFETY_CONFIG)
        assert env == git_env  # the cleaned env is passed verbatim


def test_apply_patch_raises_apply_error_on_git_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing(argv: list[str], **kwargs: object) -> object:
        return type("R", (), {"returncode": 1, "stderr": b"nope"})()

    monkeypatch.setattr(grade_module.subprocess, "run", failing)
    with pytest.raises(ApplyError, match="patch did not apply"):
        grade_module._apply_patch(tmp_path / "work", "x", {})
