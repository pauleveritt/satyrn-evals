"""The engine the cell user runs: an export of one engine commit under the cells root.

The Engine arm's ``derive`` and ``deliver`` run as the cell user, and the
cell cannot read the maintainer's engine checkout (his home is 700). So the
maintainer exports the pinned commit -- ``git archive``, no history -- into
``CELLS_ROOT/engine-<commit>``, syncs its environment offline from his own
uv cache against a Python the cell can execute (Homebrew's, world-readable;
uv's managed Pythons live under his home), and shares it with the group
read-only (Ruling 10: the pinned engine stays enforceable only if the cell
cannot write into its export -- source or ``.venv``). The marker file is
written last, so a half-made export is never reused.
"""

import io
import os
import stat
import subprocess
import tarfile
from pathlib import Path

from satyrn_evals.cell import CELLS_ROOT, grant_maintainer, share_with_cell
from satyrn_evals.errors import UsageError

MARKER = ".satyrn-engine-export"
CELL_PYTHON = Path("/opt/homebrew/bin/python3.14")


class EngineExportError(UsageError):
    """The export could not be made; the message says which step failed."""


def export_path(commit: str, root: Path = CELLS_ROOT) -> Path:
    return root / f"engine-{commit}"


def verify_export(dest: Path) -> str:
    """The commit this export holds, once it is confirmed safe to reuse or run (F2/R11).

    A cell able to rename or remove entries under a non-sticky cells root
    could plant its own directory with a matching marker; this refuses
    anything the maintainer does not still exclusively control: owned by
    the current uid, no group-write and no other-write bit, and a complete
    marker. Raises ``EngineExportError`` naming which check failed.
    """
    try:
        info = dest.stat()
    except OSError as exc:
        raise EngineExportError(f"cannot stat export {dest}: {exc}") from exc
    if info.st_uid != os.getuid():
        raise EngineExportError(f"export {dest} is not owned by the maintainer")
    if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise EngineExportError(f"export {dest} is group- or other-writable")
    marker = dest / MARKER
    try:
        sha = marker.read_text().strip()
    except OSError as exc:
        raise EngineExportError(f"export {dest} has no complete marker: {exc}") from exc
    if not sha:
        raise EngineExportError(f"export {dest} has an empty marker")
    return sha


def export_engine(engine_repo: Path, commit: str, *, root: Path = CELLS_ROOT, python: Path = CELL_PYTHON) -> Path:
    """The export directory for ``commit``, made once; an existing safe, complete export is reused."""
    resolved = subprocess.run(
        ["git", "-C", os.fspath(engine_repo), "rev-parse", "--verify", f"{commit}^{{commit}}"],
        capture_output=True, text=True, check=False,
    )
    if resolved.returncode != 0:
        raise EngineExportError(f"{commit} is not a commit in {engine_repo}: {resolved.stderr.strip()}")
    sha = resolved.stdout.strip()
    dest = export_path(sha, root)
    if dest.exists():
        try:
            existing_sha = verify_export(dest)
        except EngineExportError as exc:
            raise EngineExportError(
                f"{dest} exists without a safe, complete export marker; remove it deliberately: {exc}"
            ) from exc
        if existing_sha != sha:
            raise EngineExportError(f"{dest} exists without a complete export marker; remove it deliberately")
        return dest
    archive = subprocess.run(["git", "-C", os.fspath(engine_repo), "archive", "--format=tar", sha], capture_output=True, check=False)
    if archive.returncode != 0:
        raise EngineExportError(f"git archive {sha} failed: {os.fsdecode(archive.stderr).strip()}")
    dest.mkdir()
    if failure := grant_maintainer(dest):
        raise EngineExportError(failure)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(dest, filter="data")
    environment = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    synced = subprocess.run(
        ["uv", "sync", "--frozen", "--offline", "--python", os.fspath(python)],
        cwd=dest, env=environment, capture_output=True, text=True, check=False,
    )
    if synced.returncode != 0:
        raise EngineExportError(f"uv sync in {dest} failed: {synced.stderr.strip()}")
    share_with_cell(dest, writable=False)
    (dest / MARKER).write_text(sha + "\n")
    share_with_cell(dest, writable=False)
    return dest
