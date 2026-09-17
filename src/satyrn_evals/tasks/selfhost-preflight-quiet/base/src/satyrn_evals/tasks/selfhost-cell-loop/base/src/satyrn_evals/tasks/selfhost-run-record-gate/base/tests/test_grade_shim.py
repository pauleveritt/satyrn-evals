"""T7 hook shim: PYTHONPATH carries only the running evals package."""

from pathlib import Path

import pytest

from satyrn_evals import grade as grade_module
from satyrn_evals.attempt_record import DeadlinePhase
from satyrn_evals.deadline import AttemptDeadline, AttemptDeadlineExceeded


def test_hook_import_path_holds_one_symlink(tmp_path: Path) -> None:
    package = tmp_path / "pkg" / "satyrn_evals"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    shim = grade_module._hook_import_path(tmp_path / "work", package)
    assert shim.name == "hookpath"
    assert (shim / "satyrn_evals").is_symlink()
    assert (shim / "satyrn_evals").resolve() == package.resolve()
    # exactly one entry -- nothing else shadows the locked env
    assert list(shim.iterdir()) == [shim / "satyrn_evals"]


def test_hook_import_path_refuses_a_non_package_target(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(ValueError, match="package"):
        grade_module._hook_import_path(tmp_path / "work", missing)


def test_expired_grading_deadline_does_not_start_a_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The subprocess boundary rejects an already-expired whole deadline."""
    now = 0.0

    def clock() -> float:
        return now

    deadline = AttemptDeadline(1.0, clock=clock)
    now = 1.0
    started = False

    def fail_popen(*_args: object, **_kwargs: object) -> object:
        nonlocal started
        started = True
        raise AssertionError("expired deadline must not start a subprocess")

    monkeypatch.setattr(grade_module.subprocess, "Popen", fail_popen)

    with pytest.raises(AttemptDeadlineExceeded) as raised:
        grade_module._run_grading_subprocess(["never"], deadline=deadline)

    assert raised.value.phase is DeadlinePhase.GRADING
    assert not started


def test_grading_subprocess_reaps_after_communicate_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An owned child is torn down before a communicate failure escapes."""
    deadline = AttemptDeadline(10.0, clock=lambda: 0.0)
    torn_down: list[object] = []

    class BrokenProcess:
        def communicate(self, **_kwargs: object) -> tuple[bytes, bytes]:
            raise OSError("pipe failed")

    process = BrokenProcess()
    monkeypatch.setattr(grade_module.subprocess, "Popen", lambda *_a, **_kw: process)
    monkeypatch.setattr(
        grade_module,
        "_teardown_process",
        lambda candidate, _grace: torn_down.append(candidate),
    )

    with pytest.raises(OSError, match="pipe failed"):
        grade_module._run_grading_subprocess(["fake"], deadline=deadline)

    assert torn_down == [process]
