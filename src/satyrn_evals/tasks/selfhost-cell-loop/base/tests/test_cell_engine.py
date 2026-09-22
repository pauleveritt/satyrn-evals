"""``verify_export``'s pure safety checks (F2/R11): no subprocess, no cell.

Every refusal has a success sibling over the same shape.
"""


from pathlib import Path

import pytest

from satyrn_evals.cell_engine import EngineExportError, verify_export

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
