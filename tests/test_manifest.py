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
    assert m.engine_contract is None


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


def test_load_missing_manifest_rejected(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="cannot read manifest"):
        load_manifest(tmp_path / "missing")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (None, [], "not a JSON object"),
        ("expected_test_ids", "test", "expected_test_ids must be a list"),
        ("source_paths", "solution.py", "source_paths must be a list"),
        ("name", "", "name and contract"),
        ("oracle", [], "oracle must be a non-empty list"),
        ("expected_test_ids", [], "expected_test_ids must be a non-empty list"),
        ("source_paths", [], "source_paths must be a non-empty list"),
        ("fixtures", {"known_good": ""}, "fixtures.known_good"),
        (
            "provenance",
            {"repo": "", "base_sha": "b" * 40, "fix_sha": "f" * 40},
            "provenance fields",
        ),
    ],
)
def test_load_rejects_invalid_manifest_values(
    tmp_path: Path, field: str | None, value: object, message: str
) -> None:
    task_dir = _valid_task(tmp_path)
    if field is None:
        data = value
    else:
        data = json.loads((task_dir / "manifest.json").read_text())
        data[field] = value
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match=message):
        load_manifest(task_dir)


def test_load_missing_base_rejected(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    (task_dir / "base").rmdir()
    with pytest.raises(ManifestError, match="base directory missing"):
        load_manifest(task_dir)


def test_load_manifest_with_opaque_engine_contract(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    contract = task_dir / "engine" / "contract.yaml"
    contract.parent.mkdir()
    contract.write_bytes(b"opaque engine bytes\n")
    data = json.loads((task_dir / "manifest.json").read_text())
    data["engine_contract"] = "engine/contract.yaml"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    manifest = load_manifest(task_dir)
    assert manifest.engine_contract == "engine/contract.yaml"


@pytest.mark.parametrize(
    "value",
    ["", "/absolute.yaml", "../escape.yaml", "a/../escape.yaml", "a\\contract.yaml", "a//b"],
)
def test_load_rejects_unsafe_engine_contract_path(
    tmp_path: Path, value: str
) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["engine_contract"] = value
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="engine_contract"):
        load_manifest(task_dir)


def test_load_rejects_nul_engine_contract_as_manifest_error(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["engine_contract"] = "contract\0.yaml"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="safe relative POSIX path"):
        load_manifest(task_dir)


def test_load_reports_uninspectable_engine_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_dir = _valid_task(tmp_path)
    contract = task_dir / "contract.yaml"
    contract.write_text("opaque")
    data = json.loads((task_dir / "manifest.json").read_text())
    data["engine_contract"] = contract.name
    (task_dir / "manifest.json").write_text(json.dumps(data))
    original_lstat = Path.lstat

    def deny_contract(path: Path):
        if path == contract:
            raise PermissionError("permission denied")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", deny_contract)
    with pytest.raises(
        ManifestError, match="cannot inspect engine contract.*permission denied"
    ):
        load_manifest(task_dir)


def test_load_rejects_missing_symlink_and_nonregular_engine_contract(
    tmp_path: Path,
) -> None:
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())

    data["engine_contract"] = "missing.yaml"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="missing"):
        load_manifest(task_dir)

    outside = tmp_path / "outside.yaml"
    outside.write_text("opaque")
    (task_dir / "link.yaml").symlink_to(outside)
    data["engine_contract"] = "link.yaml"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="symbolic"):
        load_manifest(task_dir)

    (task_dir / "contract-dir").mkdir()
    data["engine_contract"] = "contract-dir"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="regular file"):
        load_manifest(task_dir)

    (task_dir / "parent-file").write_text("not a directory")
    data["engine_contract"] = "parent-file/contract.yaml"
    (task_dir / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="parent"):
        load_manifest(task_dir)
