"""``verify_export``'s pure safety checks (F2/R11) and an Engine arm's export against its pins: no subprocess, no cell.

Every refusal has a success sibling over the same shape.
"""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from satyrn_evals.arms import ENGINE_SOURCES, Arm, load_arm
from satyrn_evals.cell_engine import (
    EXPORT_PATHS,
    EngineExportError,
    arm_export_problems,
    export_leaks,
    export_path,
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


# --- an Engine arm's export against its pins (launch and launch --preflight) ---

ENGINE_ARM = Path(__file__).resolve().parents[1] / "arms" / "engine-ornith15-9b.json"


def _pinned_export(tmp_path: Path) -> tuple[Arm, Path]:
    """The committed Engine arm, its ``--engine-repo`` pointed at a stand-in export holding the pinned bytes."""
    committed = load_arm(ENGINE_ARM)
    commit = committed.pins.engine_commit
    assert commit is not None
    export = tmp_path / "cells" / f"engine-{commit}"
    (export / "packages" / "engine").mkdir(parents=True)
    for name in ENGINE_SOURCES:
        (export / "packages" / "engine" / name).write_text(f"// {name}\n")
    (export / ".satyrn-engine-export").write_text(f"{commit}\n")
    digests = {name: hashlib.sha256(f"// {name}\n".encode()).hexdigest() for name in ENGINE_SOURCES}
    arm = replace(
        committed,
        argv=("satyrn-evals-attempt-engine", "--engine-repo", str(export)),
        pins=replace(committed.pins, digests=digests),
    )
    return arm, export


def test_an_engine_arm_whose_export_is_its_pinned_commit_and_bytes_has_no_problems(tmp_path: Path) -> None:
    arm, _ = _pinned_export(tmp_path)
    assert arm_export_problems(arm, cells_root=tmp_path / "cells") == []


def test_the_committed_engine_arm_names_the_export_of_its_pinned_commit_under_the_cells_root() -> None:
    arm = load_arm(ENGINE_ARM)
    assert arm.pins.engine_commit is not None
    assert arm.argv[arm.argv.index("--engine-repo") + 1] == str(export_path(arm.pins.engine_commit))


def test_a_baseline_arm_has_no_export_to_check(tmp_path: Path) -> None:
    baseline = load_arm(ENGINE_ARM.parent / "baseline-ornith15-9b.json")
    assert arm_export_problems(baseline, cells_root=tmp_path / "missing") == []


def test_an_engine_arm_naming_no_export_is_a_problem(tmp_path: Path) -> None:
    arm, _ = _pinned_export(tmp_path)
    assert arm_export_problems(replace(arm, argv=("satyrn-evals-attempt-engine",)), cells_root=tmp_path / "cells") == [
        "the engine arm's argv names no --engine-repo export (satyrn-evals cell-engine)"
    ]


def test_an_export_named_for_another_commit_is_a_problem(tmp_path: Path) -> None:
    arm, export = _pinned_export(tmp_path)
    other = export.rename(export.with_name("engine-" + "e" * 40))
    moved = replace(arm, argv=("satyrn-evals-attempt-engine", "--engine-repo", str(other)))
    assert arm_export_problems(moved, cells_root=tmp_path / "cells") == [
        f"the engine export {other} is not engine-{arm.pins.engine_commit}, the arm's pinned commit"
    ]


def test_an_export_outside_the_cells_root_is_a_problem(tmp_path: Path) -> None:
    arm, export = _pinned_export(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    assert arm_export_problems(arm, cells_root=elsewhere) == [f"the engine export {export} is not under {elsewhere}"]


def test_an_export_whose_marker_names_another_commit_is_a_problem(tmp_path: Path) -> None:
    arm, export = _pinned_export(tmp_path)
    (export / ".satyrn-engine-export").write_text("e" * 40 + "\n")
    assert arm_export_problems(arm, cells_root=tmp_path / "cells") == [
        f"the engine export {export} holds {'e' * 40}, not the arm's pinned {arm.pins.engine_commit}"
    ]


def test_an_export_whose_source_bytes_differ_from_the_pins_is_a_problem(tmp_path: Path) -> None:
    arm, export = _pinned_export(tmp_path)
    (export / "packages" / "engine" / "scope.ts").write_text("// edited\n")
    (export / "packages" / "engine" / "paths.ts").unlink()
    assert arm_export_problems(arm, cells_root=tmp_path / "cells") == [
        f"the engine export {export} has no packages/engine/paths.ts",
        f"the engine export {export} has packages/engine/scope.ts other than the pinned bytes",
    ]


def test_an_unsafe_export_is_a_problem(tmp_path: Path) -> None:
    arm, export = _pinned_export(tmp_path)
    (export / "tests").mkdir()
    (export / "tests" / "test_doc_caps.py").write_text("x = 1\n")
    [problem] = arm_export_problems(arm, cells_root=tmp_path / "cells")
    assert problem.startswith(f"export {export} holds grader material")
