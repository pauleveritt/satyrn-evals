"""The task-tree digest a manifest carries and a run record pins.

One function, two uses. ``tree_digest(task_dir, exclude={"manifest.json"})``
is what a generated manifest records about the files beside it (a manifest
cannot hold its own digest). ``tree_digest(task_dir)`` is what a run record's
``task_tree_sha256`` pins: every file, the manifest included, so a changed
contract, oracle or expected id is drift too. Runtime residue never counts.
"""

import hashlib
from collections.abc import Iterable
from pathlib import Path

RESIDUE_PARTS = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".venv"})


def tree_digest(root: Path, *, exclude: Iterable[str] = ()) -> str:
    """SHA-256 over (root-relative POSIX path, NUL, bytes, NUL) of every file, sorted.

    ``exclude`` names root-relative paths left out. Symbolic links are hashed
    as their target text, never followed.
    """
    skipped = frozenset(exclude)
    digest = hashlib.sha256()
    paths = sorted(
        path
        for path in root.rglob("*")
        if (path.is_file() or path.is_symlink())
        and not RESIDUE_PARTS.intersection(path.relative_to(root).parts)
        and path.relative_to(root).as_posix() not in skipped
    )
    for path in paths:
        relative = path.relative_to(root).as_posix()
        body = str(path.readlink()).encode() if path.is_symlink() else path.read_bytes()
        digest.update(relative.encode() + b"\0" + body + b"\0")
    return digest.hexdigest()
