import json
from pathlib import Path

import pytest

from satyrn_evals.errors import ManifestError
from satyrn_evals.manifest import (
    DEFAULT_TASKS_ROOT,
    _validate_contracts,
    is_valid_task_name,
    load_manifest,
    resolve_task,
)


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


def test_grader_overlay_absent_defaults_to_none(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    assert load_manifest(task_dir).grader_overlay is None


def test_grader_overlay_accepts_existing_directory(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    (task_dir / "grader" / "overlay").mkdir(parents=True)
    (task_dir / "grader" / "overlay" / "tests").mkdir()
    _write_manifest_with_overlay(task_dir, "grader/overlay")
    assert load_manifest(task_dir).grader_overlay == "grader/overlay"


def test_grader_overlay_refuses_missing_directory(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    _write_manifest_with_overlay(task_dir, "grader/overlay")
    with pytest.raises(ManifestError, match="grader_overlay"):
        load_manifest(task_dir)


def test_grader_overlay_refuses_escape(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    _write_manifest_with_overlay(task_dir, "../outside")
    with pytest.raises(ManifestError, match="grader_overlay"):
        load_manifest(task_dir)


def test_grader_overlay_refuses_symlink_component(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    real = tmp_path / "elsewhere"
    real.mkdir()
    (task_dir / "grader").mkdir()
    (task_dir / "grader" / "overlay").symlink_to(real)
    _write_manifest_with_overlay(task_dir, "grader/overlay")
    with pytest.raises(ManifestError, match="symbolic links"):
        load_manifest(task_dir)


def test_grader_overlay_refuses_file(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    (task_dir / "grader").mkdir()
    (task_dir / "grader" / "overlay").write_text("not a dir")
    _write_manifest_with_overlay(task_dir, "grader/overlay")
    with pytest.raises(ManifestError, match="must name a directory"):
        load_manifest(task_dir)


def test_grader_overlay_refuses_empty_string(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    _write_manifest_with_overlay(task_dir, "")
    with pytest.raises(ManifestError, match="grader_overlay"):
        load_manifest(task_dir)


def _write_manifest_with_overlay(task_dir: Path, value: str) -> None:
    data = json.loads((task_dir / "manifest.json").read_text())
    data["grader_overlay"] = value
    # An overlay is only legal alongside a hidden oracle (the ⇔ rule), so the
    # shared overlay builder declares hidden to keep its callers on the happy
    # path; refusal tests still fail inside _validate_grader_overlay first.
    data["oracle_visibility"] = "hidden"
    (task_dir / "manifest.json").write_text(json.dumps(data))


def test_grader_overlay_refuses_uninspectable_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_dir = _valid_task(tmp_path)
    (task_dir / "grader" / "overlay").mkdir(parents=True)
    _write_manifest_with_overlay(task_dir, "grader/overlay")
    original_lstat = Path.lstat

    def deny_overlay(path: Path):
        if path == task_dir / "grader" / "overlay":
            raise PermissionError("permission denied")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", deny_overlay)
    with pytest.raises(
        ManifestError, match="cannot inspect grader overlay.*permission denied"
    ):
        load_manifest(task_dir)


def test_grader_overlay_refuses_file_parent(tmp_path: Path) -> None:
    task_dir = _valid_task(tmp_path)
    (task_dir / "grader").write_text("a file, not a directory")
    _write_manifest_with_overlay(task_dir, "grader/overlay/deeper")
    with pytest.raises(ManifestError, match="parent must be a directory"):
        load_manifest(task_dir)


def _write_task(tmp_path: Path, *, visibility: str | None = None, overlay: bool = True) -> Path:
    """Minimal hidden-oracle task dir; caller adds visibility/overlay as needed."""
    task = tmp_path / "task"
    (task / "base").mkdir(parents=True)
    if overlay:
        (task / "grader" / "overlay" / "tests").mkdir(parents=True)
        (task / "grader" / "overlay" / "tests" / "t_hidden.py").write_text(
            "def test_x():\n    assert True\n"
        )
    data = {
        "name": "task",
        "contract": "do the thing",
        "oracle": ["python", "-m", "pytest"],
        "expected_test_ids": ["tests/t_hidden.py::test_x"],
        "source_paths": ["src"],
        "fixtures": {"known_good": "fixtures/kg.patch"},
    }
    if overlay:
        data["grader_overlay"] = "grader/overlay"
    if visibility is not None:
        data["oracle_visibility"] = visibility
    (task / "manifest.json").write_text(json.dumps(data))
    (task / "fixtures").mkdir()
    (task / "fixtures" / "kg.patch").write_text("")
    return task


def test_hidden_without_overlay_refused(tmp_path: Path) -> None:
    task = _write_task(tmp_path, visibility="hidden", overlay=False)
    with pytest.raises(ManifestError, match="hidden oracle requires grader_overlay"):
        load_manifest(task)


def test_no_visibility_key_and_no_overlay_is_visible(tmp_path: Path) -> None:
    task = _write_task(tmp_path, overlay=False)
    assert load_manifest(task).oracle_visibility == "visible"  # key absent


def test_overlay_without_hidden_refused(tmp_path: Path) -> None:
    task = _write_task(tmp_path, visibility="visible")
    with pytest.raises(ManifestError, match="grader_overlay requires a hidden oracle"):
        load_manifest(task)


def test_hidden_with_overlay_declares_hidden(tmp_path: Path) -> None:
    task = _write_task(tmp_path, visibility="hidden")
    assert load_manifest(task).oracle_visibility == "hidden"


def test_invalid_visibility_value_refused(tmp_path: Path) -> None:
    task = _write_task(tmp_path, visibility="secret")
    with pytest.raises(ManifestError, match="oracle_visibility"):
        load_manifest(task)


def test_bundled_tasks_default_visible() -> None:
    for name in ("format_number",):
        manifest = load_manifest(DEFAULT_TASKS_ROOT / name)
        assert manifest.oracle_visibility == "visible"


def test_hidden_contract_naming_overlay_path_refused(tmp_path: Path) -> None:
    task = _write_task(tmp_path, visibility="hidden")
    data = json.loads((task / "manifest.json").read_text())
    data["contract"] = "make tests/t_hidden.py pass"
    (task / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="contract names grader-only path"):
        load_manifest(task)


def test_hidden_contract_without_overlay_name_loads(tmp_path: Path) -> None:
    task = _write_task(tmp_path, visibility="hidden")
    manifest = load_manifest(task)
    assert manifest.oracle_visibility == "hidden"


def test_visible_task_may_name_any_path(tmp_path: Path) -> None:
    task = _write_task(tmp_path, visibility=None, overlay=False)
    data = json.loads((task / "manifest.json").read_text())
    data["contract"] = "make tests/t_hidden.py pass"
    (task / "manifest.json").write_text(json.dumps(data))
    assert load_manifest(task).contract.startswith("make tests")


# --- V11a Task 1/2: the open `contracts` rung map ---
#
# The map is deliberately OPEN (spec §3): production code carries no enum of
# rung names, so R0 and R2 are later authoring additions rather than a code
# change. These tests pin that openness in both directions -- a key the code
# has never heard of loads, and a malformed entry is refused.


def _write_task_with_contracts(tmp_path: Path, contracts: object) -> Path:
    """A hidden task whose manifest carries the given `contracts` value."""
    task = _write_task(tmp_path, visibility="hidden")
    data = json.loads((task / "manifest.json").read_text())
    data["contracts"] = contracts
    (task / "manifest.json").write_text(json.dumps(data))
    return task


def test_contracts_absent_loads_as_empty_map(tmp_path: Path) -> None:
    """Success sibling: a task with no rungs is not an error."""
    assert load_manifest(_write_task(tmp_path, visibility="hidden")).contracts == {}


def test_contracts_two_rungs_load_with_both_texts(tmp_path: Path) -> None:
    task = _write_task_with_contracts(
        tmp_path, {"R1": "bare test_x fails", "R3": "do the thing"}
    )
    assert load_manifest(task).contracts == {
        "R1": "bare test_x fails",
        "R3": "do the thing",
    }


def test_contracts_key_unknown_to_the_code_loads(tmp_path: Path) -> None:
    """The map is open: `R7` is authoring, not a code change (spec §3)."""
    task = _write_task_with_contracts(tmp_path, {"R7": "a rung nobody declared"})
    assert load_manifest(task).contracts == {"R7": "a rung nobody declared"}


def test_contracts_not_an_object_refused(tmp_path: Path) -> None:
    task = _write_task_with_contracts(tmp_path, ["R1", "R3"])
    with pytest.raises(ManifestError, match="contracts must be an object"):
        load_manifest(task)


def test_contracts_empty_key_refused(tmp_path: Path) -> None:
    task = _write_task_with_contracts(tmp_path, {"": "text"})
    with pytest.raises(ManifestError, match="contracts keys must be non-empty"):
        load_manifest(task)


def test_contracts_non_string_value_refused(tmp_path: Path) -> None:
    task = _write_task_with_contracts(tmp_path, {"R1": 3})
    with pytest.raises(ManifestError, match="contracts\\['R1'\\] must be a non-empty"):
        load_manifest(task)


def test_contracts_whitespace_value_refused(tmp_path: Path) -> None:
    task = _write_task_with_contracts(tmp_path, {"R1": "   \n"})
    with pytest.raises(ManifestError, match="contracts\\['R1'\\] must be a non-empty"):
        load_manifest(task)


def test_contracts_non_string_key_refused_by_the_validator() -> None:
    """A JSON object cannot carry a non-string key, so this refusal is only
    reachable through the validator itself -- exercised here so the guard is
    not dead code. Its success sibling is the two-rung load above."""
    with pytest.raises(ManifestError, match="contracts keys must be non-empty"):
        _validate_contracts({1: "text"})


def test_rung_text_naming_overlay_file_refused(tmp_path: Path) -> None:
    """Task 2: the name check widens to every rung, and names the rung."""
    task = _write_task_with_contracts(
        tmp_path, {"R1": "make tests/t_hidden.py pass", "R3": "do the thing"}
    )
    with pytest.raises(
        ManifestError, match=r"contracts\['R1'\] names grader-only path"
    ):
        load_manifest(task)


def test_rung_text_naming_overlay_root_refused(tmp_path: Path) -> None:
    task = _write_task_with_contracts(tmp_path, {"R1": "look in grader/overlay"})
    with pytest.raises(
        ManifestError, match=r"contracts\['R1'\] names grader-only path"
    ):
        load_manifest(task)


def test_rung_text_with_bare_function_names_loads(tmp_path: Path) -> None:
    """Success sibling: the same digest carrying BARE hidden function names is
    exactly what R1 is authored from (spec §3), and must load."""
    task = _write_task_with_contracts(
        tmp_path, {"R1": "test_x fails: assert 307 == 303", "R3": "do the thing"}
    )
    assert load_manifest(task).contracts["R1"].startswith("test_x fails")


def test_default_contract_still_refuses_when_rungs_are_present(tmp_path: Path) -> None:
    """The widening must not regress the existing check: a clean rung map does
    not excuse a default `contract` that names a grader-only path."""
    task = _write_task_with_contracts(tmp_path, {"R1": "test_x fails"})
    data = json.loads((task / "manifest.json").read_text())
    data["contract"] = "make tests/t_hidden.py pass"
    (task / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="contract names grader-only path"):
        load_manifest(task)


def test_visible_task_rung_may_name_any_path(tmp_path: Path) -> None:
    """No overlay, no hidden oracle, no check -- the visible sibling."""
    task = _write_task(tmp_path, visibility=None, overlay=False)
    data = json.loads((task / "manifest.json").read_text())
    data["contracts"] = {"R1": "make tests/t_hidden.py pass"}
    (task / "manifest.json").write_text(json.dumps(data))
    assert load_manifest(task).contracts["R1"].startswith("make tests")


def _task_with_public_suite(tmp_path: Path, suite: object, *, overlay: str | None = None) -> Path:
    """A valid task whose manifest carries `public_suite` (and maybe an overlay)."""
    task_dir = _valid_task(tmp_path)
    data = json.loads((task_dir / "manifest.json").read_text())
    data["public_suite"] = suite
    if overlay is not None:
        (task_dir / overlay).mkdir(parents=True, exist_ok=True)
        data["grader_overlay"] = overlay
        data["oracle_visibility"] = "hidden"  # the manifest requires the pair
    (task_dir / "manifest.json").write_text(json.dumps(data))
    return task_dir


def test_a_manifest_without_public_suite_declares_none(tmp_path: Path) -> None:
    """The success sibling for every refusal below, and the default: a task
    that has not opted in gets no `test_command` and no new tool surface."""
    assert load_manifest(_valid_task(tmp_path)).public_suite == ()


def test_a_public_suite_is_loaded_as_a_command_tuple(tmp_path: Path) -> None:
    task = _task_with_public_suite(tmp_path, ["uv", "run", "python", "-m", "pytest", "tests/"])

    assert load_manifest(task).public_suite == (
        "uv", "run", "python", "-m", "pytest", "tests/",
    )


def test_a_public_suite_naming_the_oracle_hook_is_refused(tmp_path: Path) -> None:
    """The leak refusal: handing the executor the hook runs the hidden
    grader inside the executor's own process."""
    task = _task_with_public_suite(
        tmp_path, ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"]
    )

    with pytest.raises(ManifestError, match="public_suite must not name"):
        load_manifest(task)


def test_a_public_suite_naming_the_grader_overlay_is_refused(tmp_path: Path) -> None:
    task = _task_with_public_suite(
        tmp_path, ["python", "-m", "pytest", "overlay"], overlay="overlay"
    )

    with pytest.raises(ManifestError, match="public_suite must not name"):
        load_manifest(task)


def test_a_public_suite_beside_an_overlay_it_does_not_name_is_accepted(
    tmp_path: Path,
) -> None:
    """The sibling for the two refusals: a hidden-oracle task may still
    declare a public suite, as long as it names neither."""
    task = _task_with_public_suite(
        tmp_path, ["python", "-m", "pytest", "tests/"], overlay="overlay"
    )

    assert load_manifest(task).public_suite == ("python", "-m", "pytest", "tests/")


@pytest.mark.parametrize("bad", [[], "pytest", ["python", ""], ["python", 3], {}])
def test_a_malformed_public_suite_is_refused(tmp_path: Path, bad: object) -> None:
    task = _task_with_public_suite(tmp_path, bad)

    with pytest.raises(ManifestError, match="public_suite must be a non-empty list"):
        load_manifest(task)


def _task_with_ignored(tmp_path: Path, ignored: object) -> Path:
    task = _valid_task(tmp_path)
    data = json.loads((task / "manifest.json").read_text())
    data["ignored_paths"] = ignored
    (task / "manifest.json").write_text(json.dumps(data))
    return task


def test_a_manifest_without_ignored_paths_ignores_nothing(tmp_path: Path) -> None:
    assert load_manifest(_valid_task(tmp_path)).ignored_paths == ()


def test_declared_ignored_paths_load_in_order(tmp_path: Path) -> None:
    task = _task_with_ignored(tmp_path, ["PROVENANCE.md", "docs/notes.md"])
    assert load_manifest(task).ignored_paths == ("PROVENANCE.md", "docs/notes.md")


@pytest.mark.parametrize(
    ("ignored", "message"),
    [
        ("PROVENANCE.md", "must be a list of non-empty strings"),
        ([""], "must be a list of non-empty strings"),
        (["/PROVENANCE.md"], "safe relative POSIX path"),
        (["docs/../PROVENANCE.md"], "safe relative POSIX path"),
        (["PROVENANCE.md", "PROVENANCE.md"], "repeats entry"),
        (["solution.py"], "inside source_paths"),
    ],
)
def test_malformed_ignored_paths_are_refused(tmp_path: Path, ignored: object, message: str) -> None:
    with pytest.raises(ManifestError, match=message):
        load_manifest(_task_with_ignored(tmp_path, ignored))
