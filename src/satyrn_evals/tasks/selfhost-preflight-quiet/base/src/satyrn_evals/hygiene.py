"""Answer-key hygiene: find copies of a hidden task's grader files elsewhere.

A hunting model reads whatever the machine holds. On 2026-09-14 the only
``depth-3`` pass read a hidden suite that ``tests/test_agentclinic_manifests.py``
had copied into pytest's temp directory (spec, "What the evidence settled").
This finds such copies by content, so the default test tier can refuse to
leave one and a maintainer can check a directory before a sitting. It deletes
nothing. Empty overlay files are not keys and are ignored: every empty file
would match them.
"""

import hashlib
import json
import os
from pathlib import Path

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT


def overlay_digests(tasks_root: Path = DEFAULT_TASKS_ROOT) -> dict[str, str]:
    """SHA-256 of every non-empty grader overlay file of every hidden task,
    mapped to its path relative to ``tasks_root``."""
    digests: dict[str, str] = {}
    for manifest_path in sorted(tasks_root.glob("*/manifest.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        overlay = data.get("grader_overlay")
        if data.get("oracle_visibility") != "hidden" or not isinstance(overlay, str):
            continue
        for path in sorted((manifest_path.parent / overlay).rglob("*")):
            if path.is_file() and not path.is_symlink() and path.stat().st_size > 0:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                digests.setdefault(digest, path.relative_to(tasks_root).as_posix())
    return digests


def overlay_copies(root: Path, digests: dict[str, str]) -> list[Path]:
    """Regular files under ``root`` whose bytes equal a grader overlay file.

    Unreadable entries and symlinks are skipped, never fatal: a test that
    made a file unreadable on purpose must not break the scan.
    """
    found: list[Path] = []
    for directory, _dirs, files in os.walk(root):
        for name in files:
            path = Path(directory) / name
            try:
                if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
                    continue
                if hashlib.sha256(path.read_bytes()).hexdigest() in digests:
                    found.append(path)
            except OSError:
                continue
    return sorted(found)
