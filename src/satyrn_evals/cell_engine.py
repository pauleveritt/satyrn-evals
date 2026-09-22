"""The engine the cell user runs: an export of one engine commit under the cells root.

The Engine arm's ``derive`` and ``deliver`` run as the cell user, and the
cell cannot read the maintainer's engine checkout (his home is 700). So the
maintainer exports the pinned commit -- ``git archive`` of ``EXPORT_PATHS``
only, no history -- into ``CELLS_ROOT/engine-<commit>``, syncs its
environment offline from his own uv cache against a Python the cell can
execute (Homebrew's, world-readable;
uv's managed Pythons live under his home), and shares it with the group
read-only (Ruling 10: the pinned engine stays enforceable only if the cell
cannot write into its export -- source or ``.venv``). The marker file is
written last, so a half-made export is never reused.

The cell can read the export, and a hunting model reads whatever it can
reach: on 2026-09-15 the launch preflight's hunt found the engine's own
``tests/test_doc_caps.py`` in a whole-tree export, the basename of
selfhost-docs-linter's hidden suite. So the export holds only what
``uv sync`` builds and the cell runs, and an export holding any file named
like, or with the bytes of, a bundled hidden grader file is refused when it
is made and every time it is verified.
"""

import hashlib
import io
import os
import stat
import subprocess
import tarfile
from collections.abc import Mapping
from pathlib import Path

from satyrn_evals.arms import Arm
from satyrn_evals.cell import CELLS_ROOT, grant_maintainer, share_with_cell
from satyrn_evals.errors import UsageError
from satyrn_evals.hygiene import overlay_copies, overlay_digests

MARKER = ".satyrn-engine-export"
CELL_PYTHON = Path("/opt/homebrew/bin/python3.14")
#: What an export holds: the package sources ``uv sync`` builds (``src``,
#: ``pyproject.toml``, ``uv.lock``, and ``README.md``, which hatchling's
#: ``readme`` field refuses to build without), the extensions pi loads
#: (``packages``), and the licence that travels with a copy. Never ``tests``,
#: ``docs``, ``tools`` or anything else of the engine repository.
EXPORT_PATHS: tuple[str, ...] = ("src", "packages", "pyproject.toml", "uv.lock", "README.md", "LICENSE")


class EngineExportError(UsageError):
    """The export could not be made; the message says which step failed."""


def export_path(commit: str, root: Path = CELLS_ROOT) -> Path:
    return root / f"engine-{commit}"


def export_leaks(dest: Path, digests: Mapping[str, str]) -> list[str]:
    """Every file under ``dest`` named like, or holding the bytes of, a hidden grader file.

    ``digests`` is ``hygiene.overlay_digests``: grader-file SHA-256 to its
    path under the tasks root. A name match is a leak even with other bytes,
    because the preflight hunt (``cell_preflight.hunt_names``) and a hunting
    model both look by name.
    """
    names = {Path(relative).name: relative for relative in digests.values()}
    leaks = [
        f"{Path(directory) / name} is named like the hidden {names[name]}"
        for directory, _dirs, files in os.walk(dest)
        for name in files
        if name in names
    ]
    for path in overlay_copies(dest, dict(digests)):
        leaks.append(f"{path} holds the bytes of the hidden {digests[hashlib.sha256(path.read_bytes()).hexdigest()]}")
    return sorted(leaks)


def verify_export(dest: Path, digests: Mapping[str, str] | None = None) -> str:
    """The commit this export holds, once it is confirmed safe to reuse or run (F2/R11).

    A cell able to rename or remove entries under a non-sticky cells root
    could plant its own directory with a matching marker; this refuses
    anything the maintainer does not still exclusively control: owned by
    the current uid, no group-write and no other-write bit, and a complete
    marker. It also refuses an export holding grader material
    (``export_leaks`` against ``digests``, default the bundled tasks').
    Raises ``EngineExportError`` naming which check failed.
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
    if leaks := export_leaks(dest, overlay_digests() if digests is None else digests):
        raise EngineExportError(f"export {dest} holds grader material: {'; '.join(leaks)}")
    return sha


def arm_export(arm: Arm) -> Path | None:
    """The export path an Engine arm's argv names, or ``None`` for another arm."""
    if arm.arm != "engine":
        return None
    argv = list(arm.argv)
    if "--engine-repo" not in argv[:-1]:
        return None
    return Path(argv[argv.index("--engine-repo") + 1])


def arm_export_problems(arm: Arm, cells_root: Path = CELLS_ROOT) -> list[str]:
    """Why the export an Engine arm's argv names is not the engine the arm pins; empty when it is.

    ``launch`` and ``launch --preflight`` run this before any cell: the arm
    file names its export (``--engine-repo``), and the pins are claims until
    the export is checked against them. The export must be
    ``engine-<engine_commit>`` under ``cells_root``, pass ``verify_export``
    (maintainer-owned, read-only, a complete marker, no grader material),
    hold the pinned commit in its marker, and hold every pinned
    ``packages/engine`` source byte for byte. Other arms have no export.
    """
    export = arm_export(arm)
    if export is None:
        return [] if arm.arm != "engine" else [
            "the engine arm's argv names no --engine-repo export (satyrn-evals cell-engine)"
        ]
    if export.name != f"engine-{arm.pins.engine_commit}":
        return [f"the engine export {export} is not engine-{arm.pins.engine_commit}, the arm's pinned commit"]
    if not export.resolve().is_relative_to(cells_root.resolve()):
        return [f"the engine export {export} is not under {cells_root}"]
    try:
        sha = verify_export(export)
    except EngineExportError as exc:
        return [str(exc)]
    if sha != arm.pins.engine_commit:
        return [f"the engine export {export} holds {sha}, not the arm's pinned {arm.pins.engine_commit}"]
    problems: list[str] = []
    for name, digest in sorted(arm.pins.digests.items()):
        source = export / "packages" / "engine" / name
        try:
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
        except OSError:
            problems.append(f"the engine export {export} has no packages/engine/{name}")
            continue
        if actual != digest:
            problems.append(f"the engine export {export} has packages/engine/{name} other than the pinned bytes")
    return problems


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
    archive = subprocess.run(
        ["git", "-C", os.fspath(engine_repo), "archive", "--format=tar", sha, "--", *EXPORT_PATHS],
        capture_output=True, check=False,
    )
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
    if leaks := export_leaks(dest, overlay_digests()):
        raise EngineExportError(f"{dest} holds grader material; no marker written: {'; '.join(leaks)}")
    share_with_cell(dest, writable=False)
    (dest / MARKER).write_text(sha + "\n")
    share_with_cell(dest, writable=False)
    return dest
