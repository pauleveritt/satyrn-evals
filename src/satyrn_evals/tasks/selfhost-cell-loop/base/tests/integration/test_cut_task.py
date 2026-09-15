"""The generator against real history: a synthetic repository, and this repository's committed cuts.

Integration tier: git and pytest run as subprocesses. The committed-cut rows
need this repository's own history (a full clone), as the tasks were cut from it.
"""

import json
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.manifest import load_manifest
from satyrn_evals.task_tree import tree_digest
from tools.cut_task import CutError, cut, load_spec, main

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
SPECS = sorted((REPO / "tools" / "task_specs").glob("*.json"))
PLAN = """### Chunk 1: The adder

**Files:**
- Create: `calc/add.py`, `tests/test_add.py`

**Interfaces:**
- Produces: `add(a: int, b: int) -> int`

- [ ] **Stage 1: Test**

```python
assert add(1, 2) == 3
```
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def _history(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    base = _commit(repo, {
        "calc/__init__.py": "", "docs/superpowers/plans/p.md": PLAN, "PROVENANCE.md": "rows\n",
        "tests/test_add.py": "def test_old():\n    pass\n", "pyproject.toml": "[project]\nname = 'calc'\n",
    }, "base")
    good = _commit(repo, {
        "calc/add.py": "def add(a, b):\n    return a + b\n",
        "tests/test_add.py": "from calc.add import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
    }, "good")
    spec = {
        "name": "calc-add", "base": base, "good": good, "files": ["calc/add.py"], "hidden": ["tests/test_add.py"],
        "plan": {"path": "docs/superpowers/plans/p.md", "heading": "### Chunk 1: The adder", "commit": base},
        "formats": "", "broken": {"calc/add.py": "def add(a, b):\n    return None\n"}, "oracle_env": {},
    }
    return repo, spec


def test_a_cut_task_has_the_generator_shape_and_loads(tmp_path: Path) -> None:
    repo, body = _history(tmp_path)
    (tmp_path / "spec.json").write_text(json.dumps(body))
    task = cut(load_spec(tmp_path / "spec.json"), repo, tmp_path / "tasks")
    assert sorted(p.relative_to(task / "base").as_posix() for p in (task / "base").rglob("*") if p.is_file()) == [
        ".gitignore", "calc/__init__.py", "pyproject.toml"]
    assert (task / "overlay" / "test_add.py").read_text().startswith("from calc.add import add")
    assert "+    return a + b" in (task / "fixtures" / "known-good.patch").read_text()
    manifest = load_manifest(task)
    assert manifest.expected_test_ids == ("test_add.py::test_add",)
    data = json.loads((task / "manifest.json").read_text())
    assert data["digests"]["task_tree"] == tree_digest(task, exclude={"manifest.json"})
    assert "test_add.py" not in manifest.contract and "assert add" not in manifest.contract


def test_cutting_over_an_existing_task_is_refused(tmp_path: Path) -> None:
    repo, body = _history(tmp_path)
    (tmp_path / "spec.json").write_text(json.dumps(body))
    (tmp_path / "tasks" / "calc-add").mkdir(parents=True)
    with pytest.raises(CutError, match="exists"):
        cut(load_spec(tmp_path / "spec.json"), repo, tmp_path / "tasks")


def test_the_same_spec_cuts_the_same_tree_twice(tmp_path: Path) -> None:
    repo, body = _history(tmp_path)
    (tmp_path / "spec.json").write_text(json.dumps(body))
    first = cut(load_spec(tmp_path / "spec.json"), repo, tmp_path / "one")
    second = cut(load_spec(tmp_path / "spec.json"), repo, tmp_path / "two")
    assert tree_digest(first) == tree_digest(second)


@pytest.mark.parametrize("spec", SPECS, ids=lambda p: p.stem)
def test_every_committed_self_hosted_task_matches_a_fresh_cut(spec: Path) -> None:
    assert main(["check", str(spec)]) == 0


def test_a_committed_task_that_drifted_from_its_spec_fails_the_check(tmp_path: Path) -> None:
    repo, body = _history(tmp_path)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(body))
    task = cut(load_spec(spec), repo, tmp_path / "tasks")
    args = ["check", str(spec), "--repo", str(repo), "--tasks-root", str(tmp_path / "tasks")]
    assert main(args) == 0
    (task / "base" / "pyproject.toml").write_text("[project]\nname = 'drifted'\n")
    assert main(args) == 1
