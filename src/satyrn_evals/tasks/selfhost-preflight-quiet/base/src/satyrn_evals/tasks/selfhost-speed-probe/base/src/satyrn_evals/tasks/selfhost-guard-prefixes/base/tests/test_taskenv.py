from pathlib import Path

from satyrn_evals.taskenv import has_locked_project, parse_freeze


def test_stdlib_base_is_not_dependency_bearing(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "setup.py").write_text("")          # vendored/legacy marker, not a project
    assert has_locked_project(base) is False


def test_project_with_lock_is_dependency_bearing(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
    (base / "uv.lock").write_text("version = 1\n")
    assert has_locked_project(base) is True


def test_pyproject_without_lock_is_not_dependency_bearing(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "pyproject.toml").write_text("[project]\n")
    assert has_locked_project(base) is False


def test_parse_freeze_maps_name_to_exact_version() -> None:
    text = "fastapi==0.115.10\nstarlette==0.41.3\n"
    assert parse_freeze(text) == {"fastapi": "0.115.10", "starlette": "0.41.3"}


def test_parse_freeze_ignores_editable_and_comment_lines() -> None:
    text = "-e /tmp/project\n# comment\npytest==8.3.4\n"
    assert parse_freeze(text) == {"pytest": "8.3.4"}
