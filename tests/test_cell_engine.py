"""``verify_export``'s pure safety checks (F2/R11): no subprocess, no cell.

Every refusal has a success sibling over the same shape.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.cell_engine import (
    EXPORT_PATHS,
    EngineExportError,
    export_leaks,
    verify_export,
)
from satyrn_evals.hygiene import overlay_digests

SHA = "d" * 40


def _export(tmp_path: Path, *, mode: int = 0o750, marker: str | None = SHA) -> Path:
    export = tmp_path / "engine-x"
    export.mkdir()
    if marker is not None:
        (export / ".satyrn-engine-export").write_text(f"{marker}\n")
    export.chmod(mode)
    return export


def test_a_maintainer_owned_read_only_export_with_a_marker_is_verified(tmp_path: Path) -> None:
    export = _export(tmp_path)
    assert verify_export(export) == SHA


def test_a_group_writable_export_is_refused(tmp_path: Path) -> None:
    export = _export(tmp_path, mode=0o770)
    with pytest.raises(EngineExportError, match="group- or other-writable"):
        verify_export(export)


def test_an_other_writable_export_is_refused(tmp_path: Path) -> None:
    export = _export(tmp_path, mode=0o752)
    with pytest.raises(EngineExportError, match="group- or other-writable"):
        verify_export(export)


def test_an_export_without_a_marker_is_refused(tmp_path: Path) -> None:
    export = _export(tmp_path, marker=None)
    with pytest.raises(EngineExportError, match="no complete marker"):
        verify_export(export)


def test_an_export_with_an_empty_marker_is_refused(tmp_path: Path) -> None:
    export = _export(tmp_path, marker="")
    with pytest.raises(EngineExportError, match="empty marker"):
        verify_export(export)


def test_a_missing_export_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(EngineExportError, match="cannot stat"):
        verify_export(tmp_path / "does-not-exist")


# --- the export holds no answer key (the 2026-09-15 01:10 hunt) -------------

KEY = "def test_caps():\n    assert 42\n"


def _digests(tmp_path: Path) -> dict[str, str]:
    """A hidden task whose overlay holds ``tests/test_doc_caps.py``, as selfhost-docs-linter's does."""
    task = tmp_path / "tasks" / "hidden"
    (task / "overlay" / "tests").mkdir(parents=True)
    (task / "overlay" / "tests" / "test_doc_caps.py").write_text(KEY)
    (task / "manifest.json").write_text(json.dumps({"grader_overlay": "overlay", "oracle_visibility": "hidden"}))
    return overlay_digests(tmp_path / "tasks")


def _export_with(tmp_path: Path, relative: str, text: str) -> Path:
    export = _export(tmp_path)
    (export / relative).parent.mkdir(parents=True, exist_ok=True)
    (export / relative).write_text(text)
    return export


def test_an_export_of_only_engine_sources_is_verified_against_the_answer_keys(tmp_path: Path) -> None:
    export, digests = _export_with(tmp_path, "src/satyrn_engine/cli.py", "def main():\n    return 0\n"), _digests(tmp_path)
    assert export_leaks(export, digests) == []
    assert verify_export(export, digests) == SHA


def test_an_export_holding_a_file_named_like_a_hidden_test_is_refused(tmp_path: Path) -> None:
    """The engine's own ``tests/test_doc_caps.py`` is not the hidden suite, but a hunting model finds it by name."""
    export, digests = _export_with(tmp_path, "tests/test_doc_caps.py", "def test_engine_caps():\n    pass\n"), _digests(tmp_path)
    assert export_leaks(export, digests) == [
        f"{export / 'tests' / 'test_doc_caps.py'} is named like the hidden hidden/overlay/tests/test_doc_caps.py"
    ]
    with pytest.raises(EngineExportError, match="holds grader material"):
        verify_export(export, digests)


def test_an_export_holding_a_hidden_files_bytes_under_another_name_is_refused(tmp_path: Path) -> None:
    export, digests = _export_with(tmp_path, "docs/notes.py", KEY), _digests(tmp_path)
    assert export_leaks(export, digests) == [
        f"{export / 'docs' / 'notes.py'} holds the bytes of the hidden hidden/overlay/tests/test_doc_caps.py"
    ]
    with pytest.raises(EngineExportError, match="holds grader material"):
        verify_export(export, digests)


def test_the_export_allowlist_is_what_the_cell_runs_and_never_tests_or_docs() -> None:
    assert EXPORT_PATHS == ("src", "packages", "pyproject.toml", "uv.lock", "README.md", "LICENSE")
    assert not {"tests", "docs", "tools", "BACKLOG.md", "conftest.py"} & set(EXPORT_PATHS)
