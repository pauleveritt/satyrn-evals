"""Fetch the pinned engine checkout and sync its docs into the site.

The engine is a separate repository. A collaborator fetches it at the commit
the Engine arm pins; the sync copies the engine's own docs into a committed
``_engine/`` directory outside the site's source directory, with a manifest of
the pinned commit and each file's sha256, so the site shows the engine's own
bytes and a test can prove it. No model and no harness behavior.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

DEFAULT_ARM = Path("arms/engine-ornith15-9b.json")
DEFAULT_OUTPUT = Path("_engine")
DEFAULT_ENGINE_URL = "https://github.com/pauleveritt/satyrn-engine.git"
MANIFEST_NAME = "manifest.json"
#: (destination name under _engine/, source path in the engine repository)
ENGINE_DOCS: tuple[tuple[str, str], ...] = (
    ("README.md", "README.md"),
    ("usage.md", "docs/usage.md"),
    ("glossary.md", "docs/glossary.md"),
)


class EngineSyncError(Exception):
    """The fetch or sync could not proceed; the message names the step."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_arm(path: Path) -> Mapping:
    return json.loads(path.read_text())


def engine_pin(arm: Mapping) -> str:
    pin = arm.get("pins", {}).get("engine_commit")
    if not isinstance(pin, str) or not pin:
        raise EngineSyncError("the arm pins no engine_commit")
    return pin


def build_manifest(
    engine_repo: Path,
    commit: str,
    *,
    repository: str = DEFAULT_ENGINE_URL,
    docs: Sequence[tuple[str, str]] = ENGINE_DOCS,
) -> dict:
    files: dict[str, dict[str, str]] = {}
    for dest, source in docs:
        path = engine_repo / source
        if not path.is_file():
            raise EngineSyncError(f"the engine checkout has no {source}")
        files[dest] = {"source": source, "sha256": sha256(path)}
    return {"engine_commit": commit, "source_repository": repository, "files": files}


def check_manifest(
    engine_dir: Path,
    expected_commit: str,
    docs: Sequence[tuple[str, str]] = ENGINE_DOCS,
) -> list[str]:
    manifest_path = engine_dir / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text())
    except OSError:
        return [f"no manifest at {manifest_path}"]
    problems: list[str] = []
    if manifest.get("engine_commit") != expected_commit:
        problems.append(
            f"{manifest_path}: engine_commit {manifest.get('engine_commit')!r} "
            f"is not the arm's {expected_commit!r}"
        )
    files = manifest.get("files")
    if not isinstance(files, dict):
        return [*problems, f"{manifest_path}: no files mapping"]
    wanted = {dest: source for dest, source in docs}
    if set(files) != set(wanted):
        problems.append(f"{manifest_path}: files are {sorted(files)}, expected {sorted(wanted)}")
    for dest, source in docs:
        entry = files.get(dest)
        if not isinstance(entry, dict) or entry.get("source") != source:
            continue
        path = engine_dir / dest
        if not path.is_file():
            problems.append(f"{path} is missing")
        elif sha256(path) != entry.get("sha256"):
            problems.append(f"{path} does not match its manifest digest")
    return problems
