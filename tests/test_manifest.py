import json
from pathlib import Path

import pytest

from satyrn_evals.errors import ManifestError
from satyrn_evals.manifest import load_manifest, resolve_task


def _valid_task(tmp_path: Path) -> Path:
    task_dir = tmp_path / "t"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "fixtures").mkdir()
    (task_dir / "fixtures" / "known-good.patch").write_text("ok")
    (task_dir / "fixtures" / "known-broken.patch").write_text("ok")
    (task_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "t",
                "contract": "Fix it.",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["test_solution.py::test_one"],
                "source_paths": ["solution.py"],
                "fixtures": {
                    "known_good": "fixtures/known-good.patch",
                    "known_broken": "fixtures/known-broken.patch",
                },
            }
        )
    )
    return task_dir


def test_load_valid_manifest(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    m = load_manifest(task_dir)
    assert m.name == "t"
    assert m.oracle == ("python", "-m", "pytest")
    assert m.expected_test_ids == ("test_solution.py::test_one",)
    assert m.source_paths == ("solution.py",)
    assert m.fixtures["known_good"] == "fixtures/known-good.patch"


def test_load_malformed_json_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    (task_dir / "manifest.json").write_text("{not json")
    with pytest.raises(ManifestError, match="malformed manifest JSON"):
        load_manifest(task_dir)


def test_load_missing_key_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    del data["oracle"]
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="missing key"):
        load_manifest(task_dir)


def test_load_missing_fixture_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    (task_dir / "fixtures" / "known-good.patch").unlink()
    with pytest.raises(ManifestError, match="fixture file missing"):
        load_manifest(task_dir)


def test_resolve_task_found(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    assert resolve_task("t", tasks_root=tmp_path) == task_dir


def test_resolve_task_unknown_rejected(tmp_path) -> None:
    with pytest.raises(ManifestError, match="unknown task"):
        resolve_task("nope", tasks_root=tmp_path)


def test_resolve_task_path_traversal_rejected(tmp_path) -> None:
    with pytest.raises(ManifestError, match="invalid task name"):
        resolve_task("../etc", tasks_root=tmp_path)
