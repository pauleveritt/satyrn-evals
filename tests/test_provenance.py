from pathlib import Path

import pytest

from tools.provenance import check, record_imported, record_new, record_source

SHA = "8633149" + "0" * 33


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "a.py").write_text("x = 1\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "b.py").write_text("y = 2\n")
    (tmp_path / "PROVENANCE.md").write_text("# Provenance\n\n| path | source |\n|---|---|\n")
    return tmp_path


def test_recording_an_import_writes_one_row_per_path(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    text = (root / "PROVENANCE.md").read_text()
    assert f"| src/pkg/a.py | pre-release-one-2026-09-13 @ {SHA} |" in text


def test_recording_a_new_file_names_this_tree_as_the_source(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_new(root, ["tools/b.py"])
    assert "| tools/b.py | created in release-one |" in (root / "PROVENANCE.md").read_text()


def test_check_names_every_tracked_shape_of_file_without_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    assert check(root) == ["tools/b.py"]


def test_check_is_empty_when_every_file_has_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    assert check(root) == []


def test_recording_a_path_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    with pytest.raises(FileNotFoundError):
        record_imported(root, SHA, ["src/pkg/missing.py"])


def test_check_names_a_github_workflow_file_without_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "gates.yml").write_text("name: gates\n")
    assert check(root) == [".github/workflows/gates.yml"]


def test_check_names_a_packages_file_without_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / "packages" / "sub").mkdir(parents=True)
    (root / "packages" / "sub" / "c.py").write_text("z = 3\n")
    assert check(root) == ["packages/sub/c.py"]


def test_check_names_claude_settings_json_without_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / ".claude").mkdir()
    (root / ".claude" / "settings.json").write_text("{}\n")
    assert check(root) == [".claude/settings.json"]


def test_check_does_not_name_claude_settings_json_once_recorded(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / ".claude").mkdir()
    (root / ".claude" / "settings.json").write_text("{}\n")
    record_new(root, [".claude/settings.json"])
    assert check(root) == []


def test_check_does_not_walk_claude_worktrees(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / ".claude" / "worktrees" / "release-one" / "src").mkdir(parents=True)
    (root / ".claude" / "worktrees" / "release-one" / "src" / "d.py").write_text("w = 4\n")
    assert check(root) == []


def test_check_names_a_site_file_without_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / "site").mkdir()
    (root / "site" / "index.md").write_text("# hi\n")
    assert check(root) == ["site/index.md"]


def test_check_does_not_name_a_site_file_once_recorded(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / "site").mkdir()
    (root / "site" / "index.md").write_text("# hi\n")
    record_new(root, ["site/index.md"])
    assert check(root) == []


def test_recording_a_source_writes_the_source_verbatim(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "_engine").mkdir()
    (root / "_engine" / "usage.md").write_text("engine bytes\n")
    record_source(root, "satyrn-engine @ " + "a" * 40, ["_engine/usage.md"])
    assert f"| _engine/usage.md | satyrn-engine @ {'a' * 40} |" in (root / "PROVENANCE.md").read_text()


def test_recording_a_source_twice_leaves_one_row_per_path(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "_engine").mkdir()
    (root / "_engine" / "usage.md").write_text("engine bytes\n")
    record_source(root, "satyrn-engine @ " + "a" * 40, ["_engine/usage.md"])
    record_source(root, "satyrn-engine @ " + "b" * 40, ["_engine/usage.md"])
    text = (root / "PROVENANCE.md").read_text()
    assert text.count("| _engine/usage.md |") == 1
    assert f"satyrn-engine @ {'b' * 40}" in text


def test_check_names_an_engine_file_without_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / "_engine").mkdir()
    (root / "_engine" / "usage.md").write_text("engine bytes\n")
    assert check(root) == ["_engine/usage.md"]
