"""HP4.1 -- the optional directory declaration on a task manifest.

Every refusal here is paired with a sibling that differs only in the
offending entry and loads, per ``BRIEF.md`` invariant 5: a loader tested
only through its refusals passes when it refuses everything.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.errors import ManifestError
from satyrn_evals.manifest import load_manifest


def _task(tmp_path: Path, **overrides: object) -> Path:
    """A minimal valid task, with manifest keys overridden or added."""
    task_dir = tmp_path / "t"
    (task_dir / "base").mkdir(parents=True, exist_ok=True)
    (task_dir / "fixtures").mkdir(exist_ok=True)
    (task_dir / "fixtures" / "known-good.patch").write_text("ok")
    data: dict[str, object] = {
        "name": "t",
        "contract": "Build it.",
        "oracle": ["python", "-m", "pytest"],
        "expected_test_ids": ["tests/test_app.py::test_one"],
        "source_paths": ["app.py", "templates", "tests"],
        "fixtures": {"known_good": "fixtures/known-good.patch"},
    }
    data.update(overrides)
    (task_dir / "manifest.json").write_text(json.dumps(data))
    return task_dir


def test_a_manifest_that_does_not_declare_leaves_source_dirs_unset(
    tmp_path,
) -> None:
    assert load_manifest(_task(tmp_path)).source_dirs is None


def test_a_declared_manifest_carries_its_directories(tmp_path) -> None:
    manifest = load_manifest(_task(tmp_path, source_dirs=["templates", "tests"]))
    assert manifest.source_dirs == ("templates", "tests")


def test_an_empty_declaration_is_kept_as_empty_not_absent(tmp_path) -> None:
    """``[]`` is a claim that no entry is a directory, not a missing key."""
    assert load_manifest(_task(tmp_path, source_dirs=[])).source_dirs == ()


def test_a_non_list_declaration_is_refused(tmp_path) -> None:
    with pytest.raises(ManifestError, match="source_dirs must be a list"):
        load_manifest(_task(tmp_path, source_dirs="templates"))


def test_an_empty_string_entry_is_refused(tmp_path) -> None:
    with pytest.raises(ManifestError, match="source_dirs must be a list"):
        load_manifest(_task(tmp_path, source_dirs=["templates", ""]))


def test_a_repeated_entry_is_refused_and_named(tmp_path) -> None:
    with pytest.raises(ManifestError, match="repeats entry: templates"):
        load_manifest(_task(tmp_path, source_dirs=["templates", "templates"]))


def test_an_entry_outside_source_paths_is_refused_and_named(tmp_path) -> None:
    """A declaration the renderer would silently drop is worse than none."""
    with pytest.raises(ManifestError, match="'static'.*not in source_paths"):
        load_manifest(_task(tmp_path, source_dirs=["static"]))


def test_the_sibling_of_each_refusal_loads(tmp_path) -> None:
    """The same manifests, with only the offending entry corrected."""
    for corrected in (["templates"], ["templates", "tests"], []):
        manifest = load_manifest(_task(tmp_path, source_dirs=corrected))
        assert manifest.source_dirs == tuple(corrected)
