"""Test root.

With a src layout the project is importable because uv installs it
editable into the venv; this file marks the tests root and hosts the
spawn tripwire.

The tripwire is a CPython audit hook: any subprocess spawn during the
default (non-integration) tier raises, failing the build. The
`integration` marker opens the gate for tests that legitimately spawn
(git, the oracle).
"""

import json
import sys
from pathlib import Path

import pytest

_BLOCKED_EVENTS = {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"}
_spawn_blocked = True


def _audit_hook(event: str, args: tuple) -> None:
    if _spawn_blocked and event in _BLOCKED_EVENTS:
        raise RuntimeError(f"subprocess spawn blocked by tripwire: {event}")


sys.addaudithook(_audit_hook)


@pytest.fixture(autouse=True)
def _tripwire_gate(request: pytest.FixtureRequest) -> None:
    global _spawn_blocked
    _spawn_blocked = request.node.get_closest_marker("integration") is None


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """The default tier leaves no bundled grader file in pytest's temp directory.

    pytest keeps the last three base temp directories, and on 2026-09-14 a
    hunting model read a hidden suite a test had copied there. The default
    tier (``-m "not integration"``, the addopts value) fails its session if
    any file under this run's base temp equals a bundled overlay file.
    """
    from satyrn_evals.hygiene import overlay_copies, overlay_digests

    factory = getattr(session.config, "_tmp_path_factory", None)
    if session.config.option.markexpr != "not integration" or factory is None:
        return
    copies = overlay_copies(factory.getbasetemp(), overlay_digests())
    if copies:
        for path in copies:
            print(f"bundled grader file copied into pytest's temp directory: {path}")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


# --- V7 P3 Task 1 fixtures: hidden/visible task dirs + clean/contaminated patches ---
# Reuses the P1 `_write_task` shape from tests/test_manifest.py: a hidden
# task declares `grader_overlay` + `oracle_visibility=hidden`; a visible
# task omits both. The base carries one allowlisted file the clean patch
# modifies; the contaminated patch embeds a verbatim copy of the hidden
# task's own overlay file (read at fixture time so the block matches).

_BASE_SOLUTION = "def double(n):\n    return n\n\n"
_BASE_TEST = (
    "from solution import double\n\n\n"
    "def test_doubles():\n    assert double(3) == 6\n"
)
_HIDDEN_OVERLAY = (
    "def test_hidden_doubles():\n"
    "    x = 2\n"
    "    y = 4\n"
    "    assert double(x) == y\n"
)
_ORACLE = ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"]


def _write_base(task_dir: Path) -> None:
    (task_dir / "base" / "src").mkdir(parents=True)
    (task_dir / "base" / "tests").mkdir()
    (task_dir / "base" / "src" / "solution.py").write_text(_BASE_SOLUTION)
    (task_dir / "base" / "tests" / "test_solution.py").write_text(_BASE_TEST)


def _write_manifest(
    task_dir: Path, *, visibility: str | None, overlay: bool
) -> None:
    data = {
        "name": task_dir.name,
        "contract": "Make double return twice its input.",
        "oracle": _ORACLE,
        "expected_test_ids": ["tests/test_solution.py::test_doubles"],
        "source_paths": ["src"],
        "fixtures": {
            "known_good": "fixtures/known-good.patch",
            "known_broken": "fixtures/known-broken.patch",
        },
    }
    if overlay:
        data["grader_overlay"] = "grader/overlay"
        data["oracle_visibility"] = "hidden"
        data["expected_test_ids"] = [
            "tests/test_solution.py::test_doubles",
            "tests/test_hidden.py::test_hidden_doubles",
        ]
    if visibility is not None and not overlay:
        data["oracle_visibility"] = visibility
    (task_dir / "manifest.json").write_text(json.dumps(data))


@pytest.fixture()
def tmp_hidden_task(tmp_path: Path) -> Path:
    task_dir = tmp_path / "tmp_hidden_task"
    _write_base(task_dir)
    overlay_dir = task_dir / "grader" / "overlay" / "tests"
    overlay_dir.mkdir(parents=True)
    (overlay_dir / "test_hidden.py").write_text(_HIDDEN_OVERLAY)
    _write_manifest(task_dir, visibility="hidden", overlay=True)
    (task_dir / "fixtures").mkdir()
    (task_dir / "fixtures" / "known-good.patch").write_text("")
    (task_dir / "fixtures" / "known-broken.patch").write_text("")
    return task_dir


@pytest.fixture()
def tmp_visible_task(tmp_path: Path) -> Path:
    task_dir = tmp_path / "tmp_visible_task"
    _write_base(task_dir)
    _write_manifest(task_dir, visibility=None, overlay=False)
    (task_dir / "fixtures").mkdir()
    (task_dir / "fixtures" / "known-good.patch").write_text("")
    (task_dir / "fixtures" / "known-broken.patch").write_text("")
    return task_dir


_CLEAN_PATCH = (
    "diff --git a/src/solution.py b/src/solution.py\n"
    "--- a/src/solution.py\n"
    "+++ b/src/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)


@pytest.fixture()
def clean_patch(tmp_path: Path) -> Path:
    path = tmp_path / "clean.patch"
    path.write_text(_CLEAN_PATCH)
    return path


@pytest.fixture()
def contaminated_patch(tmp_hidden_task: Path, tmp_path: Path) -> Path:
    """A patch adding a new source file that embeds the overlay verbatim."""
    overlay_file = tmp_hidden_task / "grader" / "overlay" / "tests" / "test_hidden.py"
    block = overlay_file.read_text()
    body_lines = block.splitlines()
    patch = (
        "diff --git a/src/leak.py b/src/leak.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/src/leak.py\n"
        f"@@ -0,0 +1,{len(body_lines)} @@\n"
        + "".join(f"+{line}\n" for line in body_lines)
    )
    path = tmp_path / "contaminated.patch"
    path.write_text(patch)
    return path
