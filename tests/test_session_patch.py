"""``build_cumulative_patch``'s ``deadline`` argument (F2): a total budget
across its four git calls, not a per-call one. Default tier: fakes
``subprocess.run`` and ``time.monotonic``, no real git or filesystem I/O
beyond the throwaway alternate index.
"""

import subprocess
from pathlib import Path

import pytest

import satyrn_evals.session_patch as session_patch_module
from satyrn_evals.session_patch import build_cumulative_patch


class _FakeResult:
    returncode = 0
    stdout = b""
    stderr = b""


def _fake_clock(monkeypatch: pytest.MonkeyPatch, *, step: float) -> list[float | None]:
    """Fake ``time.monotonic`` and ``subprocess.run``: each git call advances
    the clock by ``step`` and records the ``timeout`` it was called with."""
    clock = {"t": 0.0}
    seen: list[float | None] = []

    def fake_monotonic() -> float:
        return clock["t"]

    def fake_run(_args: object, **kwargs: object) -> _FakeResult:
        seen.append(kwargs.get("timeout"))  # type: ignore[arg-type]
        clock["t"] += step
        return _FakeResult()

    monkeypatch.setattr(session_patch_module.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(session_patch_module.subprocess, "run", fake_run)
    return seen


def test_a_total_deadline_shrinks_across_the_four_git_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _fake_clock(monkeypatch, step=5.0)
    build_cumulative_patch(tmp_path, "a" * 40, {}, deadline=20.0)
    assert len(seen) == 4  # read-tree, add, diff, status
    assert seen == pytest.approx([20.0, 15.0, 10.0, 5.0])


def test_a_deadline_already_passed_raises_before_the_first_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(session_patch_module.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(
        session_patch_module.subprocess,
        "run",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not run git")),
    )
    with pytest.raises(subprocess.TimeoutExpired):
        build_cumulative_patch(tmp_path, "a" * 40, {}, deadline=50.0)


def test_a_deadline_exhausted_mid_harvest_stops_before_the_next_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _fake_clock(monkeypatch, step=100.0)  # blows the whole budget on call 1
    with pytest.raises(subprocess.TimeoutExpired):
        build_cumulative_patch(tmp_path, "a" * 40, {}, deadline=20.0)
    assert len(seen) == 1  # never reached the second git call


def test_without_a_deadline_the_per_call_timeout_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _fake_clock(monkeypatch, step=5.0)
    build_cumulative_patch(tmp_path, "a" * 40, {}, timeout=30.0)
    assert seen == [30.0, 30.0, 30.0, 30.0]
