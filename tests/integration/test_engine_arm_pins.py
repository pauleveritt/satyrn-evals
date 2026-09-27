"""The committed Engine arm's pins against the engine checkout (SATYRN_V4_ENGINE_REPO): git reads only, no model."""

import ast
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from integration.test_attempt import (
    _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
)
from satyrn_evals.arms import ENGINE_SOURCES, load_arm
from satyrn_evals.pathology import GUARD_KINDS

pytestmark = pytest.mark.integration

ENGINE_ARM = Path(__file__).resolve().parents[2] / "arms" / "engine-ornith15-9b.json"


def _git(*argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(_engine_repo()), *argv], capture_output=True, check=True)


def test_every_pinned_digest_is_the_bytes_of_that_source_at_the_pinned_commit() -> None:
    arm = load_arm(ENGINE_ARM)
    for name in ENGINE_SOURCES:
        blob = _git("show", f"{arm.pins.engine_commit}:packages/engine/{name}").stdout
        assert hashlib.sha256(blob).hexdigest() == arm.pins.digests[name], name


def test_the_pinned_sources_are_every_typescript_file_of_the_engine_package_at_the_pinned_commit() -> None:
    """A new module the extensions import would otherwise run unpinned."""
    arm = load_arm(ENGINE_ARM)
    listed = _git("ls-tree", "--name-only", arm.pins.engine_commit, "packages/engine/").stdout.decode().split()
    assert sorted(Path(path).name for path in listed if path.endswith(".ts")) == sorted(ENGINE_SOURCES)


def test_the_pinned_engine_commit_is_a_full_sha_the_checkout_holds() -> None:
    commit = json.loads(ENGINE_ARM.read_text(encoding="utf-8"))["pins"]["engine_commit"]
    assert _git("rev-parse", "--verify", f"{commit}^{{commit}}").stdout.decode().strip() == commit


def _engine_guard_kinds(commit: str) -> tuple[str, ...]:
    """`GUARD_KINDS` out of the engine's own `budget.py` at the pinned commit,
    parsed by AST -- not imported, so the engine's own venv need not be
    active (a pure git read, same isolation as this module's digest checks)."""
    source = _git("show", f"{commit}:src/satyrn_engine/budget.py").stdout.decode()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "GUARD_KINDS"
            and node.value is not None
        ):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError("GUARD_KINDS not found in the engine's budget.py at the pinned commit")


def test_the_two_trees_guard_kinds_sets_agree() -> None:
    """Whole-path review Minor 3, ruled into the fix wave: the lists are two
    literals in two repositories and nothing pinned them together. A future
    engine kind added without a matching evals add makes every cell where it
    fires read `unknown_event` -- the exact defect Task 7 closed, recurring
    silently. Integration-tier only (never default): the whole-branch
    review's Important 3 already ruled that the default tier must not read
    another repo."""
    arm = load_arm(ENGINE_ARM)
    assert arm.pins.engine_commit is not None
    assert set(_engine_guard_kinds(arm.pins.engine_commit)) == set(GUARD_KINDS)
