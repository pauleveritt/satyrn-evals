"""``task_self_test`` both directions, with a fake runner: nothing spawns.

The real check is the integration tier and the operator's preflight; these
rows pin the decision logic -- which state is named, that a green base and a
green known-good state add no problem, and that a repair task's red base is
recorded rather than refused.
"""

import subprocess
from pathlib import Path

from satyrn_evals.manifest import TaskManifest
from satyrn_evals.task_selftest import task_self_test

SUITE = ("uv", "run", "pytest", "-q")


def _manifest(**over: object) -> TaskManifest:
    base = dict(
        name="t", contract="do it", oracle=("python", "-m", "pytest"),
        expected_test_ids=(), source_paths=("src/t.py",),
        fixtures={"known_good": "fixtures/known-good.patch"}, public_suite=SUITE,
    )
    return TaskManifest(**{**base, **over})  # type: ignore[arg-type]


def _task_dir(tmp_path: Path, *, known_good: bool = True) -> Path:
    task = tmp_path / "task"
    (task / "base").mkdir(parents=True)
    (task / "base" / "marker.txt").write_text("base\n", encoding="utf-8")
    if known_good:
        (task / "fixtures").mkdir()
        (task / "fixtures" / "known-good.patch").write_text("", encoding="utf-8")
    return task


class _FakeRun:
    """Answers git calls with exit 0 and the suite calls with a configured sequence."""

    def __init__(self, *suite_codes: int) -> None:
        self.suite_codes = list(suite_codes)
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        if argv[0] == "git":
            return subprocess.CompletedProcess(argv, 0, "", "")
        code = self.suite_codes.pop(0)
        return subprocess.CompletedProcess(argv, code, "out\n" if code == 0 else "boom\n", "")

    @property
    def suite_calls(self) -> int:
        return sum(1 for argv in self.calls if argv[0] != "git")


def test_a_green_base_and_a_green_known_good_state_add_no_problem(tmp_path: Path) -> None:
    run = _FakeRun(0, 0)
    report = task_self_test(_task_dir(tmp_path), _manifest(), run=run)
    assert report.problems == []
    assert report.checked == {"base_exit": 0, "known_good_exit": 0, "repair_base": False}
    assert run.suite_calls == 2  # the base row and the known-good row both ran


def test_a_red_base_with_a_red_known_good_state_names_both(tmp_path: Path) -> None:
    run = _FakeRun(2, 2)
    report = task_self_test(_task_dir(tmp_path), _manifest(), run=run)
    assert any("unmodified t base exited 2" in problem for problem in report.problems)
    assert any("known-good state exited 2" in problem for problem in report.problems)


def test_a_green_base_but_a_red_known_good_state_is_named(tmp_path: Path) -> None:
    run = _FakeRun(0, 1)
    report = task_self_test(_task_dir(tmp_path), _manifest(), run=run)
    assert len(report.problems) == 1
    assert "known-good state exited 1" in report.problems[0]
    assert report.checked["repair_base"] is False


def test_a_repair_task_with_a_red_base_and_a_green_known_good_state_is_recorded_not_refused(
    tmp_path: Path,
) -> None:
    run = _FakeRun(1, 0)
    report = task_self_test(_task_dir(tmp_path), _manifest(), run=run)
    assert report.problems == []
    assert report.checked["base_exit"] == 1
    assert report.checked["known_good_exit"] == 0
    assert report.checked["repair_base"] is True


def test_a_missing_known_good_patch_leaves_a_red_base_refused(tmp_path: Path) -> None:
    run = _FakeRun(2)
    report = task_self_test(_task_dir(tmp_path, known_good=False), _manifest(), run=run)
    assert len(report.problems) == 1
    assert "known-good patch is missing" in report.problems[0]
    assert run.suite_calls == 1


def test_a_task_with_no_public_suite_has_nothing_to_check(tmp_path: Path) -> None:
    run = _FakeRun()
    report = task_self_test(_task_dir(tmp_path), _manifest(public_suite=()), run=run)
    assert report.problems == []
    assert report.checked == {}
    assert run.calls == []
