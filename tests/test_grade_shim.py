"""T7 hook shim: PYTHONPATH carries only the running evals package."""

from pathlib import Path

import pytest

from satyrn_evals import grade as grade_module


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
