"""The committed Engine arm's pins against the engine checkout (SATYRN_V4_ENGINE_REPO): git reads only, no model."""

import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from integration.test_attempt import (
    _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
)
from satyrn_evals.arms import ENGINE_SOURCES, load_arm
from satyrn_evals.cell_engine import EXPORT_PATHS
from satyrn_evals.hygiene import overlay_digests

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


def _archived_names(commit: str, *paths: str) -> set[str]:
    """Basenames of every file ``git archive`` would write, read in memory: nothing lands on disk."""
    archive = _git("archive", "--format=tar", commit, *(["--", *paths] if paths else [])).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        return {Path(member.name).name for member in tar.getmembers() if member.isfile()}


def test_the_whole_tree_of_the_pinned_commit_names_a_hidden_suite_and_the_allowlist_does_not() -> None:
    """The firing row is the 2026-09-15 hunt's find; the silent row is what `export_engine` now archives."""
    commit = load_arm(ENGINE_ARM).pins.engine_commit
    assert commit is not None
    hidden = {Path(path).name for path in overlay_digests().values()}
    assert "test_doc_caps.py" in _archived_names(commit) & hidden
    assert _archived_names(commit, *EXPORT_PATHS) & hidden == set()
