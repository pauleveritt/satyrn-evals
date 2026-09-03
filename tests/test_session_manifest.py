"""session.json loader: spec shapes and the refusal table."""

import copy
import json
from pathlib import Path

import pytest

from satyrn_evals.errors import SessionSpecError
from satyrn_evals.session_manifest import load_session_spec

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


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda p: p.update(steps=VALID["steps"][:1]), "fewer than two steps"),
        (lambda p: p["steps"].__setitem__(1, {**p["steps"][0]}), "duplicate id"),
        (lambda p: p["steps"][0].update(prompt=""), "empty prompt"),
        (lambda p: p["steps"][0].update(id="bad id!"), "filesystem-safe"),
        (lambda p: p["steps"][0].update(new_feature_selectors=[]), "feature step"),
        (lambda p: p.update(base_preservation_selectors=[]), "preservation"),
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


def test_session_spec_missing_file_refused(tmp_path: Path) -> None:
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
