"""HP4.3 -- the declared scope against the scope the grader enforces.

Two different rules meet here. ``engine_contract.writable_paths`` renders
fnmatch patterns that the implementer reads; ``patch.within_source`` decides
what the grader's allowlist accepts. HP4 does not merge them -- relaxing
enforcement is out of the cycle's scope -- it pins the one direction that
matters: **declared never exceeds enforced**, so the packet cannot invite a
write the grader will reject.
"""

import pytest

from satyrn_evals.engine_contract import admits, writable_paths
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.patch import within_source

#: Paths probed against every task. Deliberately mixed: descendants, near
#: misses, siblings that a prefix rule must not admit, and one path per
#: shipped source tree.
PROBES: tuple[str, ...] = (
    "app.py",
    "app.pyc",
    "models.py",
    "templates/base.html",
    "templates/nested/deep.html",
    "tests/test_app.py",
    "tests-adjacent/test_app.py",
    "templates.html",
    "static/app.css",
    "solution.py",
    "solution.pyc",
    "src/textkit/core.py",
    "src/svcs/_core.py",
    "README.md",
)


def _tasks() -> list[str]:
    return sorted(
        d.name for d in DEFAULT_TASKS_ROOT.iterdir() if (d / "manifest.json").is_file()
    )


@pytest.mark.parametrize("name", _tasks())
def test_the_declared_scope_never_exceeds_the_enforced_scope(name: str) -> None:
    task_dir = DEFAULT_TASKS_ROOT / name
    manifest = load_manifest(task_dir)
    patterns = writable_paths(task_dir, manifest.source_paths, manifest.source_dirs)
    exceeded = [
        path
        for path in PROBES
        if admits(patterns, path) and not within_source(path, manifest.source_paths)
    ]
    assert exceeded == [], (
        f"{name} declares paths its grader would reject: {exceeded}"
    )


def test_the_phased_task_now_admits_its_three_creation_targets() -> None:
    """The three files phase 1 must create, and the reason HP4 exists."""
    task_dir = DEFAULT_TASKS_ROOT / "agentclinic-session-phased"
    manifest = load_manifest(task_dir)
    patterns = writable_paths(task_dir, manifest.source_paths, manifest.source_dirs)
    for target in ("app.py", "templates/base.html", "tests/test_app.py"):
        assert admits(patterns, target), target
        assert within_source(target, manifest.source_paths), target


def test_the_undeclared_form_would_have_refused_one_of_them() -> None:
    """Reconstruct the defect, so the test above can fail. Under the probe
    ``templates`` renders exact, and ``templates/base.html`` falls outside
    the declaration while enforcement still admits it."""
    task_dir = DEFAULT_TASKS_ROOT / "agentclinic-session-phased"
    manifest = load_manifest(task_dir)
    probed = writable_paths(task_dir, manifest.source_paths, None)
    assert not admits(probed, "templates/base.html")
    assert within_source("templates/base.html", manifest.source_paths)


def test_a_path_outside_the_declaration_is_still_refused() -> None:
    """Widening a directory entry did not widen the task."""
    task_dir = DEFAULT_TASKS_ROOT / "agentclinic-session-phased"
    manifest = load_manifest(task_dir)
    patterns = writable_paths(task_dir, manifest.source_paths, manifest.source_dirs)
    for outside in ("static/app.css", "templates.html", "tests-adjacent/x.py"):
        assert not admits(patterns, outside), outside


def test_the_remaining_asymmetry_is_recorded_not_closed() -> None:
    """``within_source`` admits the bare directory path and the declaration
    does not. Narrowing enforcement to match is out of HP4's scope, so the
    asymmetry is asserted rather than left to be discovered."""
    task_dir = DEFAULT_TASKS_ROOT / "agentclinic-session-phased"
    manifest = load_manifest(task_dir)
    patterns = writable_paths(task_dir, manifest.source_paths, manifest.source_dirs)
    assert within_source("templates", manifest.source_paths)
    assert not admits(patterns, "templates")
