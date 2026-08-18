import json
from pathlib import Path

import pytest

from satyrn_evals.errors import ManifestError
from satyrn_evals.manifest import is_valid_task_name, load_manifest, resolve_task


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


def test_load_string_oracle_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["oracle"] = "python"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="oracle must be a list"):
        load_manifest(task_dir)


def test_load_string_fixtures_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["fixtures"] = "notadict"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="fixtures must be an object"):
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


def test_load_manifest_without_known_broken(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    del data["fixtures"]["known_broken"]
    (task_dir / "manifest.json").write_text(json.dumps(data))
    m = load_manifest(task_dir)
    assert "known_broken" not in m.fixtures
    assert m.provenance is None


def test_load_manifest_with_provenance(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["provenance"] = {"repo": "/src/app", "base_sha": "b" * 40, "fix_sha": "f" * 40}
    (task_dir / "manifest.json").write_text(json.dumps(data))
    m = load_manifest(task_dir)
    assert m.provenance == {"repo": "/src/app", "base_sha": "b" * 40, "fix_sha": "f" * 40}


def test_load_manifest_with_malformed_known_broken_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["fixtures"]["known_broken"] = ""
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="known_broken"):
        load_manifest(task_dir)


def test_load_manifest_with_malformed_provenance_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["provenance"] = {"repo": "/src/app"}
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="provenance"):
        load_manifest(task_dir)


def test_load_manifest_with_non_object_provenance_rejected(tmp_path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["provenance"] = ["not", "an", "object"]
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="provenance"):
        load_manifest(task_dir)


def test_is_valid_task_name() -> None:
    assert is_valid_task_name("format_number")
    assert is_valid_task_name("a-b_c.1")


@pytest.mark.parametrize("name", ["", "../etc", "a/b", "a\\b", ".", ".."])
def test_is_valid_task_name_rejects(name: str) -> None:
    assert not is_valid_task_name(name)


def test_resolve_task_uses_same_rule(tmp_path) -> None:
    with pytest.raises(ManifestError, match="invalid task name"):
        resolve_task("../etc", tasks_root=tmp_path)
