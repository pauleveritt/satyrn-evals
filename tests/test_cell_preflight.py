"""The portable confinement preflight: the extension is present, and no task
materializes grader material into the ``base/`` the run tree is built from.

Default tier: pure, no subprocess. ``preflight_confinement`` replaced the
two-uid cell/sandbox preflight, and this is its both-directions proof -- a
normal corpus is clean, a corpus that carries grader material in its base is
reported.
"""

from pathlib import Path

from satyrn_evals.cell_preflight import preflight_confinement


def _task(tasks_root: Path, name: str = "selfhost-x") -> Path:
    task = tasks_root / name
    (task / "base").mkdir(parents=True)
    (task / "overlay").mkdir()
    (task / "overlay" / "test_hidden.py").write_text("x", encoding="utf-8")
    (task / "fixtures").mkdir()
    (task / "fixtures" / "known-good.patch").write_text("p", encoding="utf-8")
    return task


def test_a_corpus_under_the_working_directory_is_not_flagged(tmp_path: Path, monkeypatch) -> None:
    """The false positive this file exists for: the corpus lives inside the
    launcher's checkout, so a check that compared it with the working directory
    refused every normal launch. The corpus is not the run tree."""
    monkeypatch.chdir(tmp_path)
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    report = preflight_confinement(pinned_pi="pi", tasks_root=tasks_root)
    assert report.problems == []
    assert report.checked["tasks_root"] == str(tasks_root.resolve())


def test_a_base_carrying_the_overlay_is_flagged(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    task = _task(tasks_root)
    (task / "base" / "overlay").mkdir()
    [problem] = preflight_confinement(pinned_pi="pi", tasks_root=tasks_root).problems
    assert "selfhost-x" in problem
    assert "overlay" in problem


def test_a_base_carrying_the_fixtures_is_flagged(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    task = _task(tasks_root)
    (task / "base" / "fixtures").mkdir()
    [problem] = preflight_confinement(pinned_pi="pi", tasks_root=tasks_root).problems
    assert "selfhost-x" in problem
    assert "fixtures" in problem


def test_a_missing_corpus_is_reported_not_raised(tmp_path: Path) -> None:
    report = preflight_confinement(pinned_pi="pi", tasks_root=tmp_path / "gone")
    assert len(report.problems) == 1
    assert "gone" in report.problems[0]


def test_no_tasks_root_skips_the_corpus_check() -> None:
    assert preflight_confinement(pinned_pi="pi").problems == []
