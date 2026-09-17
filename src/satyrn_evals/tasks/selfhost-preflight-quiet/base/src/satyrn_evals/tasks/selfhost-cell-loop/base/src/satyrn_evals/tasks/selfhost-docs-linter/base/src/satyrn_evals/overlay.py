"""Grader-only overlay: validate its tree, record digests, materialize it.

The overlay carries hidden tests that the executor is never shown. Its
files are stored below the manifest's ``grader_overlay`` directory and are
copied into a *fresh grader workspace* at paths relative to that directory,
so ``grader/overlay/tests/test_hidden.py`` lands at ``tests/test_hidden.py``
beside the base's public tests (2026-09-01 spec, Task layout).

Correction (V9, 2026-09-04): load no longer refuses group/other-writable
stored files. Git's index stores regular files as 100644/100755
regardless of the working-tree mode, so the on-disk mode at load is a
property of the checkout umask, not of the store: umask 002 (Debian/
Ubuntu default) yields 664 (group-writable), umask 000 yields 666
(other-writable) for the same clean 100644 store. The old check refused
clean checkouts on both systems and could catch nothing git would not
normalize. Materialization chmods 0o444 after digest verification, and the
real invariant -- overlays never materialize in executor-reachable paths
-- is unchanged (assert_overlay_absent).
"""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from satyrn_evals.contamination import overlay_absent_from_inventory
from satyrn_evals.errors import OverlayError
from satyrn_evals.manifest import TaskManifest


@dataclass(frozen=True, slots=True)
class OverlaySpec:
    """A validated overlay: root dir, root-relative file paths, digests, texts."""

    root: Path
    rel_paths: tuple[str, ...]
    digests: dict[str, str]
    texts: dict[str, str]


def assert_overlay_absent(tree: Path, spec: OverlaySpec) -> None:
    """Refuse an executor tree that carries overlay paths or overlay bytes.

    The real invariant behind V7's prevention requirement (spec §3 check
    (a)): read-only modes are secondary; absence is primary.
    """
    inventory: dict[str, str] = {}
    for path in sorted(tree.rglob("*")):
        if path.is_file() and not path.is_symlink():
            inventory[path.relative_to(tree).as_posix()] = sha256(
                path.read_bytes()
            ).hexdigest()
    if not overlay_absent_from_inventory(inventory, spec):
        raise OverlayError(
            "executor workspace contains overlay content "
            "(path or byte-identical file); base must never carry grader content"
        )


def load_overlay(task_dir: Path, manifest: TaskManifest) -> OverlaySpec:
    """Validate the overlay tree and record its relative paths and digests."""
    if manifest.grader_overlay is None:
        raise OverlayError("manifest declares no grader_overlay")
    root = task_dir / manifest.grader_overlay
    if root.is_symlink():
        raise OverlayError("grader_overlay must not contain symbolic links")
    if not root.is_dir():
        raise OverlayError(f"grader_overlay must name a directory: {manifest.grader_overlay}")
    source_paths = set(manifest.source_paths)
    rel_paths: list[str] = []
    digests: dict[str, str] = {}
    texts: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise OverlayError(f"grader overlay must not contain symbolic links: {rel}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise OverlayError(f"grader overlay entries must be regular files: {rel}")
        if rel in source_paths or any(
            rel == source or rel.startswith(f"{source}/") for source in source_paths
        ):
            raise OverlayError(f"grader overlay overlaps source_paths: {rel}")
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OverlayError(
                f"grader overlay file must be UTF-8 text: {rel}"
            ) from exc
        rel_paths.append(rel)
        digests[rel] = sha256(data).hexdigest()
        texts[rel] = text
    if not rel_paths:
        raise OverlayError("grader overlay directory is empty")
    return OverlaySpec(root=root, rel_paths=tuple(rel_paths), digests=digests, texts=texts)


def materialize_overlay(spec: OverlaySpec, workspace: Path) -> None:
    """Copy overlay files into a fresh grader workspace at their rel paths.

    The recorded digests are load-bearing: each written file is verified
    against its digest, so overlay drift between load and materialize is
    a refused error, not a silent change in what the grader ran.

    Written files are chmod'ed 0o444. That is accidental-exposure prevention,
    not security isolation: the real invariant is that overlays are never
    materialized in executor-reachable paths (spec §5).
    """
    resolved_workspace = workspace.resolve()
    for rel in spec.rel_paths:
        target = workspace / rel
        if not target.resolve().is_relative_to(resolved_workspace):
            raise OverlayError(f"overlay path escapes the workspace: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        data = (spec.root / rel).read_bytes()
        target.write_bytes(data)
        if sha256(data).hexdigest() != spec.digests.get(rel):
            raise OverlayError(f"overlay file digest mismatch: {rel}")
        target.chmod(0o444)
