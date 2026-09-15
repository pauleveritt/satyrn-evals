"""HP4.2 -- the renderer consults the declaration instead of probing.

The golden table below is the whole shipped fleet. Ten of the thirteen
tasks declare nothing and are here to prove HP4 did not move them.
``agentclinic-session-phased`` is the one HP4 exists for: an empty-skeleton
base where ``templates``/``tests`` do not exist on disk until the model
creates them, so the probe cannot tell they are meant to be directories.
``agentclinic-complaint-lifecycle`` (TE4) and
``agentclinic-phase2-guardrail-candidate`` (a bounded candidate probe,
docs/current/phase-2-board-runaway-investigation.md) share that exact
topology -- same bare base, directories built from nothing -- so they
declare the same way, not as further instances of the defect HP4 fixes.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.engine_contract import writable_paths
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest

#: The rendered patterns every shipped task produces, pinned as data.
FLEET: dict[str, tuple[str, ...]] = {
    "agentclinic-complaint-lifecycle": (
        "app.py",
        "models.py",
        "templates/*",
        "tests/*",
    ),
    "agentclinic-repair-misleading-locus": (
        "app.py",
        "models.py",
        "templates/*",
        "tests/*",
    ),
    "agentclinic-repair-depth-2": ("app.py", "models.py", "templates/*", "tests/*"),
    "agentclinic-repair-depth-3": ("app.py", "models.py", "templates/*", "tests/*"),
    "format_number": ("solution.py",),
    "selfhost-docs-linter": ("tools/lint_docs.py", "tests/*"),
    "selfhost-guard-prefixes": ("tools/hooks/guard.py", "tests/*"),
    "selfhost-review-script": ("tools/review.py", "tests/*"),
    "selfhost-run-record-gate": ("src/satyrn_evals/run_record.py", "src/satyrn_evals/cli.py", "tests/*"),
}


def _shipped() -> list[str]:
    return sorted(
        d.name for d in DEFAULT_TASKS_ROOT.iterdir() if (d / "manifest.json").is_file()
    )


def test_the_golden_table_covers_every_shipped_task() -> None:
    """A task added without a row would otherwise never be checked."""
    assert sorted(FLEET) == _shipped()


@pytest.mark.parametrize("name", sorted(FLEET))
def test_each_shipped_task_renders_its_pinned_patterns(name: str) -> None:
    task_dir = DEFAULT_TASKS_ROOT / name
    manifest = load_manifest(task_dir)
    rendered = writable_paths(task_dir, manifest.source_paths, manifest.source_dirs)
    assert rendered == FLEET[name]


def test_only_the_empty_skeleton_tasks_declare() -> None:
    """HP4 is scoped to the tasks the probe gets wrong -- an empty base
    where the model builds `templates`/`tests` from nothing. Every task
    with that topology declares; no other shipped task does."""
    declaring = [n for n in _shipped() if load_manifest(DEFAULT_TASKS_ROOT / n).source_dirs is not None]
    assert declaring == [
        "agentclinic-complaint-lifecycle",
    ]


def _tree(tmp_path: Path, entries: dict[str, str]) -> Path:
    """A task tree whose ``base/`` holds the named files and directories."""
    task_dir = tmp_path / "t"
    for name, kind in entries.items():
        target = task_dir / "base" / name
        if kind == "dir":
            target.mkdir(parents=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x")
    (task_dir / "base").mkdir(parents=True, exist_ok=True)
    return task_dir


def test_a_declared_directory_that_is_a_file_on_disk_is_refused(tmp_path) -> None:
    task_dir = _tree(tmp_path, {"templates": "file"})
    with pytest.raises(ValueError, match="declares 'templates' a directory"):
        writable_paths(task_dir, ("templates",), ("templates",))


def test_the_same_tree_renders_once_the_entry_is_not_declared(tmp_path) -> None:
    """The sibling of the refusal above, differing only in the declaration."""
    task_dir = _tree(tmp_path, {"templates": "file"})
    assert writable_paths(task_dir, ("templates",), ()) == ("templates",)


def test_an_undeclared_directory_on_disk_is_refused(tmp_path) -> None:
    """An empty declaration must not silently narrow a real directory task."""
    task_dir = _tree(tmp_path, {"templates": "dir"})
    with pytest.raises(ValueError, match="does not declare it one"):
        writable_paths(task_dir, ("templates",), ())


def test_the_same_tree_renders_once_the_entry_is_declared(tmp_path) -> None:
    task_dir = _tree(tmp_path, {"templates": "dir"})
    assert writable_paths(task_dir, ("templates",), ("templates",)) == ("templates/*",)


def test_an_absent_entry_is_free_to_be_either(tmp_path) -> None:
    """Nothing on disk contradicts either reading, which is the whole point:
    the declaration decides where the probe could not."""
    task_dir = _tree(tmp_path, {})
    assert writable_paths(task_dir, ("templates",), ("templates",)) == ("templates/*",)
    assert writable_paths(task_dir, ("templates",), ()) == ("templates",)


def test_the_rendered_contract_carries_the_declared_patterns(tmp_path) -> None:
    """The declaration reaches the bytes the model reads, not just the tuple."""
    from satyrn_evals.engine_contract import render_engine_contract

    task_dir = _tree(tmp_path, {})
    (task_dir / "fixtures").mkdir(parents=True)
    (task_dir / "fixtures" / "known-good.patch").write_text("ok")
    (task_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "t",
                "contract": "Build it.",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["tests/test_app.py::test_one"],
                "source_paths": ["app.py", "templates"],
                "source_dirs": ["templates"],
                "fixtures": {"known_good": "fixtures/known-good.patch"},
            }
        )
    )
    manifest = load_manifest(task_dir)
    rendered = render_engine_contract(
        task_dir, manifest, rung=None, contract_text="Build it."
    ).decode()
    assert '  - "templates/*"' in rendered
    assert '  - "templates"\n' not in rendered
