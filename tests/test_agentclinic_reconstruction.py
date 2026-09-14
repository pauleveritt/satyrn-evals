"""AgentClinic repair bases: vendored tree inventory pinned by the spec rule."""

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

STATES = ["misleading-locus"]

# spec §2: per-state content overrides/additions, and .delete removals.
DELTA_FILES = {
    "misleading-locus": ["app.py"],
}
DELETED: dict[str, list[str]] = {}
SHARED = ["app.py", "models.py", "templates/home.html", "templates/base.html",
          "templates/complaints.html", "tests/test_app.py"]


def _base(state: str):
    return DEFAULT_TASKS_ROOT / f"agentclinic-repair-{state}" / "base"


@pytest.mark.parametrize("state", STATES)
def test_base_inventory_matches_reconstruction_rule(state: str) -> None:
    base = _base(state)
    assert base.is_dir(), f"missing base for {state}"
    # app-tree inventory only: project files (pyproject.toml, uv.lock) are
    # asserted separately by the Task-3 project test, which runs after lock.
    present = {
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and p.name not in ("pyproject.toml", "uv.lock")
    }
    expected = (set(SHARED) - set(DELETED.get(state, []))) | set(DELTA_FILES[state])
    assert present == expected, f"{state}: {sorted(present)} != {sorted(expected)}"


@pytest.mark.parametrize("state", STATES)
def test_no_junk_or_git_dirs_in_base(state: str) -> None:
    base = _base(state)
    bad = [p.name for p in base.rglob("*")
           if p.name in (".git", "__pycache__", ".delete", "README.md")]
    assert not bad, f"{state} base contains: {bad}"


@pytest.mark.parametrize("state", STATES)
def test_base_has_exactly_the_locked_project_files(state: str) -> None:
    base = _base(state)
    project = sorted(p.name for p in base.iterdir()
                     if p.name in ("pyproject.toml", "uv.lock"))
    assert project == ["pyproject.toml", "uv.lock"], state
    assert (base / "uv.lock").read_text().strip()
