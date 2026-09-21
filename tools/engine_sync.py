"""Fetch the pinned engine checkout and sync its docs into the site.

The engine is a separate repository. A collaborator fetches it at the commit
the Engine arm pins; the sync copies the engine's own docs into a committed
``_engine/`` directory outside the site's source directory, with a manifest of
the pinned commit and each file's sha256, so the site shows the engine's own
bytes and a test can prove it. No model and no harness behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
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


def head_commit(engine_repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", os.fspath(engine_repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise EngineSyncError(f"cannot read HEAD of {engine_repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def fetch_engine(dest: Path, commit: str, *, repository: str = DEFAULT_ENGINE_URL) -> Path:
    if dest.exists():
        if head_commit(dest) == commit:
            return dest
        raise EngineSyncError(
            f"{dest} is at {head_commit(dest)}, not the pinned {commit}; remove it deliberately"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    cloned = subprocess.run(
        ["git", "clone", "--quiet", repository, os.fspath(dest)],
        capture_output=True, text=True, check=False,
    )
    if cloned.returncode != 0:
        raise EngineSyncError(f"git clone {repository} failed: {cloned.stderr.strip()}")
    checked_out = subprocess.run(
        ["git", "-C", os.fspath(dest), "checkout", "--quiet", "--detach", commit],
        capture_output=True, text=True, check=False,
    )
    if checked_out.returncode != 0:
        raise EngineSyncError(f"git checkout {commit} in {dest} failed: {checked_out.stderr.strip()}")
    return dest


def sync_engine(
    engine_repo: Path,
    engine_dir: Path,
    commit: str,
    *,
    repository: str = DEFAULT_ENGINE_URL,
    record_provenance: bool = True,
) -> dict:
    if head_commit(engine_repo) != commit:
        raise EngineSyncError(f"{engine_repo} is not at the pinned {commit}")
    manifest = build_manifest(engine_repo, commit, repository=repository)
    engine_dir.mkdir(parents=True, exist_ok=True)
    for dest, source in ENGINE_DOCS:
        shutil.copyfile(engine_repo / source, engine_dir / dest)
    (engine_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if record_provenance:
        from tools.provenance import record_source

        record_source(
            engine_dir.parent,
            f"satyrn-engine @ {commit}",
            [f"{engine_dir.name}/{dest}" for dest, _ in ENGINE_DOCS],
        )
        record_source(
            engine_dir.parent,
            f"generated by tools/engine_sync.py from satyrn-engine @ {commit}",
            [f"{engine_dir.name}/{MANIFEST_NAME}"],
        )
    return manifest


def _engine_repo(argument: str | None, root: Path) -> Path:
    if argument:
        return Path(argument)
    env = os.environ.get("SATYRN_ENGINE_REPO")
    if env:
        return Path(env)
    return (root / ".." / "satyrn-engine").resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine_sync")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="clone the pinned engine commit into a checkout")
    fetch.add_argument("--arm", default=os.fspath(DEFAULT_ARM))
    fetch.add_argument("--engine-repo", default=None)
    fetch.add_argument("--url", default=DEFAULT_ENGINE_URL)
    sync = sub.add_parser("sync", help="copy the pinned engine's docs into the committed _engine/ copy")
    sync.add_argument("--arm", default=os.fspath(DEFAULT_ARM))
    sync.add_argument("--engine-repo", default=None)
    sync.add_argument("--output", default=os.fspath(DEFAULT_OUTPUT))
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    try:
        commit = engine_pin(load_arm(root / args.arm))
        engine_repo = _engine_repo(args.engine_repo, root)
        if args.command == "fetch":
            fetch_engine(engine_repo, commit, repository=args.url)
            print(f"export SATYRN_ENGINE_REPO={engine_repo}")
            return 0
        manifest = sync_engine(engine_repo, root / args.output, commit)
        print(f"synced {len(manifest['files'])} engine docs at {commit} into {root / args.output}")
        return 0
    except EngineSyncError as exc:
        print(f"engine-sync: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
