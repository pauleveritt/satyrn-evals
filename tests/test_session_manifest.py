"""session.json loader: spec shapes and the refusal table."""

import copy
import json
from pathlib import Path

import pytest

from satyrn_evals.errors import SessionSpecError
from satyrn_evals.manifest import load_manifest
from satyrn_evals.session_manifest import (
    assert_no_overlay_names,
    load_session_spec,
)

VALID: dict = {
    "version": 1,
    "steps": [
        {
            "id": "add-slugify",
            "kind": "feature",
            "prompt": "Add slugify.",
            "new_feature_selectors": ["test_hidden.py::test_slugify_basic"],
        },
        {
            "id": "review",
            "kind": "review",
            "prompt": "Review.",
            "new_feature_selectors": [],
        },
    ],
    "base_preservation_selectors": ["test_solution.py::test_normalize"],
}


def _write(tmp_path: Path, payload: object) -> None:
    (tmp_path / "session.json").write_text(json.dumps(payload))


def _step(id_: str, *, kind: str = "feature") -> dict:
    """One session step, defaulting to a feature step with one selector."""
    selectors = [] if kind == "review" else [f"test_hidden.py::test_{id_}"]
    return {
        "id": id_,
        "kind": kind,
        "prompt": f"Do {id_}.",
        "new_feature_selectors": selectors,
    }


def _write_and_load(
    tmp_path: Path,
    *,
    steps: list[dict],
    preservation: list[str] | None = None,
):
    """Write session.json from the given steps/preservation and load it.

    ``preservation`` defaults to the file's current non-empty value so every
    existing call keeps its exact meaning.
    """
    if preservation is None:
        preservation = ["test_solution.py::test_normalize"]
    _write(
        tmp_path,
        {
            "version": 1,
            "steps": steps,
            "base_preservation_selectors": preservation,
        },
    )
    return load_session_spec(tmp_path)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda p: p.update(steps=VALID["steps"][:1]), "fewer than two steps"),
        (lambda p: p["steps"].__setitem__(1, {**p["steps"][0]}), "duplicate id"),
        (lambda p: p["steps"][0].update(prompt=""), "empty prompt"),
        (lambda p: p["steps"][0].update(id="bad id!"), "filesystem-safe"),
        (lambda p: p["steps"][0].update(new_feature_selectors=[]), "feature step"),
        (lambda p: p.update(base_preservation_selectors=[""]), "preservation"),
        (lambda p: p["steps"][1].update(kind="chaos"), "kind"),
        (lambda p: p.update(version=2), "version"),
        (lambda p: p.update(extra=1), "unknown"),
    ],
)
def test_session_spec_refusals(
    tmp_path: Path, mutate, match: str
) -> None:
    payload = copy.deepcopy(VALID)
    mutate(payload)
    _write(tmp_path, payload)
    with pytest.raises(SessionSpecError, match=match):
        load_session_spec(tmp_path)


def test_session_spec_valid_sibling(tmp_path: Path) -> None:
    _write(tmp_path, copy.deepcopy(VALID))
    spec = load_session_spec(tmp_path)
    assert [s.id for s in spec.steps] == ["add-slugify", "review"]
    assert spec.steps[0].new_feature_selectors == (
        "test_hidden.py::test_slugify_basic",
    )
    assert spec.steps[1].new_feature_selectors == ()
    assert spec.base_preservation_selectors == ("test_solution.py::test_normalize",)


def test_empty_base_preservation_selectors_are_allowed(tmp_path) -> None:
    """A base that ships no application has no base behaviour to preserve.
    Cross-phase preservation comes from cumulative feature grading."""
    spec = _write_and_load(
        tmp_path, steps=[_step("one"), _step("two")], preservation=[]
    )
    assert spec.base_preservation_selectors == ()


def test_base_preservation_selectors_must_be_non_empty_strings(tmp_path) -> None:
    """Refusal, narrowed: an empty list is now legal, an empty entry is not."""
    with pytest.raises(SessionSpecError, match="base_preservation_selectors"):
        _write_and_load(
            tmp_path, steps=[_step("one"), _step("two")], preservation=[""]
        )


def _hidden_session_task(tmp_path: Path, *, prompts: tuple[str, ...]) -> Path:
    """Build a minimal hidden session task with the given step prompts.

    The overlay declares one grader-only module (``tests/t_hidden.py`` under
    ``grader/overlay``); the refusal check trips when a prompt names that
    path or the overlay root itself.
    """
    task = tmp_path / "task"
    (task / "base").mkdir(parents=True)
    (task / "grader" / "overlay" / "tests").mkdir(parents=True)
    (task / "grader" / "overlay" / "tests" / "t_hidden.py").write_text(
        "def test_x():\n    assert True\n"
    )
    (task / "fixtures").mkdir()
    (task / "fixtures" / "kg.patch").write_text("")
    (task / "manifest.json").write_text(
        json.dumps(
            {
                "name": "task",
                "contract": "do the thing without naming the grader",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["tests/t_hidden.py::test_x"],
                "source_paths": ["src"],
                "fixtures": {"known_good": "fixtures/kg.patch"},
                "grader_overlay": "grader/overlay",
                "oracle_visibility": "hidden",
            }
        )
    )
    steps = []
    for index, prompt in enumerate(prompts):
        kind = "feature" if index < len(prompts) - 1 else "review"
        steps.append(
            {
                "id": f"step-{index}",
                "kind": kind,
                "prompt": prompt,
                "new_feature_selectors": (
                    [f"tests/t_hidden.py::test_x_{index}"] if kind == "feature" else []
                ),
            }
        )
    (task / "session.json").write_text(
        json.dumps(
            {
                "version": 1,
                "steps": steps,
                "base_preservation_selectors": ["tests/t_hidden.py::test_base"],
            }
        )
    )
    return task


def test_prompt_naming_overlay_path_refuses(tmp_path: Path) -> None:
    task = _hidden_session_task(
        tmp_path,
        prompts=(
            "Wire grader/overlay into the build.",
            "Review the implementation and run the public suite.",
        ),
    )
    spec = load_session_spec(task)
    manifest = load_manifest(task)
    with pytest.raises(SessionSpecError, match="names grader-only path"):
        assert_no_overlay_names(spec, manifest, task)


def test_clean_prompts_pass(tmp_path: Path) -> None:
    task = _hidden_session_task(
        tmp_path,
        prompts=(
            "Add the slugify helper to the public module.",
            "Review the implementation and run the public suite.",
        ),
    )
    spec = load_session_spec(task)
    manifest = load_manifest(task)
    assert_no_overlay_names(spec, manifest, task)  # does not raise


def test_assert_no_overlay_names_skips_visible_task(tmp_path: Path) -> None:
    # A visible task with no overlay is never refused, even if a prompt
    # mentions a path that would otherwise look overlay-shaped.
    task = _hidden_session_task(
        tmp_path,
        prompts=(
            "Add tests/t_hidden.py to the public module.",
            "Review the implementation and run the public suite.",
        ),
    )
    data = json.loads((task / "manifest.json").read_text())
    data["oracle_visibility"] = "visible"
    data.pop("grader_overlay")
    (task / "manifest.json").write_text(json.dumps(data))
    spec = load_session_spec(task)
    manifest = load_manifest(task)
    assert manifest.oracle_visibility == "visible"
    assert manifest.grader_overlay is None
    assert_no_overlay_names(spec, manifest, task)  # does not raise


def test_session_spec_missing_file_refuses(tmp_path: Path) -> None:
    with pytest.raises(SessionSpecError, match="session.json"):
        load_session_spec(tmp_path)


def test_session_spec_duplicate_selector_refused(tmp_path: Path) -> None:
    payload = copy.deepcopy(VALID)
    payload["steps"][0]["new_feature_selectors"] = ["a.py::t_one"]
    payload["steps"][1]["kind"] = "feature"
    payload["steps"][1]["new_feature_selectors"] = ["a.py::t_one"]
    _write(tmp_path, payload)
    with pytest.raises(SessionSpecError, match="duplicate"):
        load_session_spec(tmp_path)


def test_session_spec_refuses_step_with_unknown_keys(tmp_path: Path) -> None:
    payload = copy.deepcopy(VALID)
    payload["steps"][0]["chaos"] = 1
    _write(tmp_path, payload)
    with pytest.raises(SessionSpecError, match="exactly"):
        load_session_spec(tmp_path)


def test_session_spec_refuses_non_string_selector(tmp_path: Path) -> None:
    payload = copy.deepcopy(VALID)
    payload["steps"][0]["new_feature_selectors"] = [3]
    _write(tmp_path, payload)
    with pytest.raises(SessionSpecError, match="non-empty strings"):
        load_session_spec(tmp_path)


def test_session_spec_refuses_review_with_selectors(tmp_path: Path) -> None:
    payload = copy.deepcopy(VALID)
    payload["steps"][1]["new_feature_selectors"] = ["a.py::t"]
    _write(tmp_path, payload)
    with pytest.raises(SessionSpecError, match="review step"):
        load_session_spec(tmp_path)


def test_session_spec_refuses_malformed_json(tmp_path: Path) -> None:
    (tmp_path / "session.json").write_text("{not json")
    with pytest.raises(SessionSpecError, match="malformed session.json"):
        load_session_spec(tmp_path)


def test_session_spec_refuses_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "session.json"
    path.write_text("{}")

    def deny(path: Path):
        raise PermissionError("permission denied")

    monkeypatch.setattr(Path, "read_text", deny)
    with pytest.raises(SessionSpecError, match="cannot read"):
        load_session_spec(tmp_path)


def test_session_spec_refuses_malformed_json_names_the_given_file(
    tmp_path: Path,
) -> None:
    """A non-default --session-spec name appears in the failure message.

    Regression for a bug where the three failure branches hardcoded the
    literal ``"session.json"``, so a malformed ``other.json`` reported the
    wrong filename.
    """
    (tmp_path / "other.json").write_text("{not json")
    with pytest.raises(SessionSpecError, match="malformed other.json"):
        load_session_spec(tmp_path, spec_name="other.json")


def test_session_spec_refuses_unreadable_named_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "other.json"
    path.write_text("{}")

    def deny(path: Path):
        raise PermissionError("permission denied")

    monkeypatch.setattr(Path, "read_text", deny)
    with pytest.raises(SessionSpecError, match="cannot read other.json"):
        load_session_spec(tmp_path, spec_name="other.json")


def test_session_spec_refuses_bad_keys_names_the_given_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "other.json").write_text(json.dumps({"version": 1}))
    with pytest.raises(SessionSpecError, match="in other.json"):
        load_session_spec(tmp_path, spec_name="other.json")


def test_session_spec_name_loads_a_named_file(tmp_path: Path) -> None:
    """--session-spec picks a different file inside the task dir.

    The default caller still gets session.json's steps; a caller that asks
    for other.json gets that file's steps instead — proving both the
    default path and the selector both resolve to the file they name.
    """
    _write(tmp_path, copy.deepcopy(VALID))
    other = copy.deepcopy(VALID)
    other["steps"][0]["id"] = "add-other"
    (tmp_path / "other.json").write_text(json.dumps(other))

    default_spec = load_session_spec(tmp_path)
    other_spec = load_session_spec(tmp_path, spec_name="other.json")

    assert default_spec.steps[0].id == "add-slugify"
    assert other_spec.steps[0].id == "add-other"


@pytest.mark.parametrize(
    ("spec_name", "match"),
    [
        ("sub/other.json", "bare filename"),
        ("../other.json", "traverse"),
        ("/etc/passwd.json", "absolute"),
        ("other.txt", "\\.json"),
    ],
)
def test_session_spec_name_refusals(
    tmp_path: Path, spec_name: str, match: str
) -> None:
    _write(tmp_path, copy.deepcopy(VALID))
    with pytest.raises(SessionSpecError, match=match):
        load_session_spec(tmp_path, spec_name=spec_name)


def test_session_spec_name_traversal_cannot_read_outside_task_dir(
    tmp_path: Path,
) -> None:
    """The traversal refusal actually blocks escape, not just bad names.

    A sibling directory holds a *readable, well-formed* session.json. Absent
    the validation this loader would happily follow ``../secret/session.json``
    and return the secret's steps; the refusal must fire before any read.
    """
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    _write(task_dir, copy.deepcopy(VALID))

    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret = copy.deepcopy(VALID)
    secret["steps"][0]["id"] = "exfiltrated"
    (secret_dir / "session.json").write_text(json.dumps(secret))

    with pytest.raises(SessionSpecError, match="traverse"):
        load_session_spec(task_dir, spec_name="../secret/session.json")
