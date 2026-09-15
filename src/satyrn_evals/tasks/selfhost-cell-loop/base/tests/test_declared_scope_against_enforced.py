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
