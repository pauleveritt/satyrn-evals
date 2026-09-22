"""Fetch the pinned engine checkout and sync its docs into the site.

The engine is a separate repository. A collaborator fetches it at the commit
the Engine arm pins; the sync copies the engine's own docs into a committed
``_engine/`` directory outside the site's source directory, with a manifest of
the pinned commit and each file's sha256, so the site shows the engine's own
bytes and a test can prove it. A second, rendered copy under
``_engine/rendered/`` converts the engine's MyST/Sphinx markup to Markdown for
publication; both digests are recorded. No model and no harness behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

DEFAULT_ARM = Path("arms/engine-ornith15-9b.json")
DEFAULT_OUTPUT = Path("_engine")
DEFAULT_ENGINE_URL = "https://github.com/pauleveritt/satyrn-engine.git"
MANIFEST_NAME = "manifest.json"
RENDERED_DIR = "rendered"
#: The transform that turns the engine's MyST/Sphinx markup into Markdown.
TRANSFORM_VERSION = "myst-to-markdown-v1"
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_ROLE = re.compile(r"\{(?:term|doc)\}`([^`]+)`")


def _rst_literals(text: str) -> str:
    """Turn RST ``literal`` spans into Markdown `code` spans.

    Token-aware: only a run of exactly two backticks becomes a code span, so
    the triple-backtick fences around code blocks pass through untouched.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "`":
            out.append(text[i])
            i += 1
            continue
        j = i
        while j < n and text[j] == "`":
            j += 1
        if j - i == 2:
            end = text.find("``", j)
            if end != -1:
                out.append("`" + text[j:end] + "`")
                i = end + 2
                continue
        out.append(text[i:j])
        i = j
    return "".join(out)


def _inline(text: str) -> str:
    """Convert MyST roles and RST inline literals on one line of prose."""
    return _rst_literals(_ROLE.sub(r"\1", text))


def _fence_body(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect a fenced block's body, returning it and the index after the close."""
    body: list[str] = []
    i = start
    while i < len(lines):
        if lines[i].strip().startswith("```"):
            return body, i + 1
        body.append(lines[i])
        i += 1
    return body, i


def _glossary_entries(body: list[str]) -> list[tuple[str, list[str]]]:
    entries: list[tuple[str, list[str]]] = []
    term: str | None = None
    definition: list[str] = []
    for raw in body:
        if raw.strip() == "":
            if term is not None:
                entries.append((term, definition))
                term, definition = None, []
            continue
        if raw[0] in " \t" and term is not None:
            definition.append(raw)
        else:
            if term is not None:
                entries.append((term, definition))
            term = raw.strip()
            definition = []
    if term is not None:
        entries.append((term, definition))
    return entries


def _render_glossary(body: list[str]) -> list[str]:
    """Turn a ``{glossary}`` block into bold-term Markdown paragraphs."""
    blocks: list[str] = []
    for term, definition in _glossary_entries(body):
        dedented = [line[2:] if line.startswith("  ") else line.lstrip() for line in definition]
        text = "\n".join(_inline(line) for line in dedented).strip()
        blocks.append(f"**{_inline(term)}**\n\n{text}")
    return "\n\n".join(blocks).splitlines()


def render_myst(text: str) -> str:
    """Render the engine's MyST/Sphinx markup as Markdown.

    Pure and offline. Converts ``{term}``/``{doc}`` roles to their text, RST
    ``literal`` spans to Markdown code spans, and a fenced ``{glossary}`` block
    to bold-term paragraphs. Ordinary prose, GFM tables, and code fences pass
    through unchanged.
    """
    trailing = text.endswith("\n")
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            if stripped[3:].strip() == "{glossary}":
                body, i = _fence_body(lines, i + 1)
                out.extend(_render_glossary(body))
                continue
            out.append(line)
            i += 1
            while i < len(lines):
                out.append(lines[i])
                if lines[i].strip().startswith("```"):
                    i += 1
                    break
                i += 1
            continue
        out.append(_inline(line))
        i += 1
    result = "\n".join(out)
    return result + "\n" if trailing else result


def load_arm(path: Path) -> Mapping:
    return json.loads(path.read_text())


def engine_pin(arm: Mapping) -> str:
    pin = arm.get("pins", {}).get("engine_commit")
    if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{40}", pin):
        raise EngineSyncError("the arm's engine_commit is not a 40-hex commit sha")
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
        data = path.read_bytes()
        rendered = render_myst(data.decode("utf-8")).encode("utf-8")
        files[dest] = {
            "source": source,
            "sha256": _sha256_bytes(data),
            "rendered_sha256": _sha256_bytes(rendered),
        }
    return {
        "engine_commit": commit,
        "source_repository": repository,
        "transform": TRANSFORM_VERSION,
        "files": files,
    }


def check_manifest(
    engine_dir: Path,
    expected_commit: str,
    docs: Sequence[tuple[str, str]] = ENGINE_DOCS,
) -> list[str]:
    manifest_path = engine_dir / MANIFEST_NAME
    try:
        text = manifest_path.read_text()
    except OSError:
        return [f"no manifest at {manifest_path}"]
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError:
        return [f"{manifest_path}: manifest is not valid JSON"]
    if not isinstance(manifest, dict):
        return [f"{manifest_path}: manifest is not an object"]
    problems: list[str] = []
    if manifest.get("engine_commit") != expected_commit:
        problems.append(
            f"{manifest_path}: engine_commit {manifest.get('engine_commit')!r} "
            f"is not the arm's {expected_commit!r}"
        )
    if manifest.get("transform") != TRANSFORM_VERSION:
        problems.append(
            f"{manifest_path}: transform {manifest.get('transform')!r} "
            f"is not {TRANSFORM_VERSION!r}"
        )
    files = manifest.get("files")
    if not isinstance(files, dict):
        return [*problems, f"{manifest_path}: no files mapping"]
    wanted = {dest: source for dest, source in docs}
    if set(files) != set(wanted):
        problems.append(f"{manifest_path}: files are {sorted(files)}, expected {sorted(wanted)}")
    for dest, source in docs:
        entry = files.get(dest)
        if entry is None:
            # An absent entry is already named by the wrong-file-set problem.
            continue
        if not isinstance(entry, dict):
            problems.append(f"{manifest_path}: {dest} has no source mapping, expected {source!r}")
            continue
        if entry.get("source") != source:
            problems.append(
                f"{manifest_path}: {dest} has source {entry.get('source')!r}, expected {source!r}"
            )
        path = engine_dir / dest
        if not path.is_file():
            problems.append(f"{path} is missing")
        elif sha256(path) != entry.get("sha256"):
            problems.append(f"{path} does not match its manifest digest")
        rendered = engine_dir / RENDERED_DIR / dest
        if not rendered.is_file():
            problems.append(f"{rendered} is missing")
        elif sha256(rendered) != entry.get("rendered_sha256"):
            problems.append(f"{rendered} does not match its manifest rendered digest")
    return problems


def head_commit(engine_repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", os.fspath(engine_repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise EngineSyncError(f"cannot read HEAD of {engine_repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def dirty_paths(engine_repo: Path, docs: Sequence[tuple[str, str]] = ENGINE_DOCS) -> list[str]:
    """The porcelain status lines for the synced docs, empty when they are clean.

    A clean tree at the pinned commit is byte-identical to the commit, so
    refusing a dirty pathspec keeps the copy faithful without reading blobs.
    """
    pathspec = [source for _, source in docs]
    result = subprocess.run(
        ["git", "-C", os.fspath(engine_repo), "status", "--porcelain", "--", *pathspec],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise EngineSyncError(f"cannot read the status of {engine_repo}: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def fetch_engine(dest: Path, commit: str, *, repository: str = DEFAULT_ENGINE_URL) -> Path:
    if dest.exists():
        actual = head_commit(dest)
        if actual == commit:
            return dest
        raise EngineSyncError(
            f"{dest} is at {actual}, not the pinned {commit}; remove it deliberately"
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
    record_provenance: bool = True,
) -> dict:
    actual = head_commit(engine_repo)
    if actual != commit:
        raise EngineSyncError(f"{engine_repo} is at {actual}, not the pinned {commit}")
    dirty = dirty_paths(engine_repo)
    if dirty:
        raise EngineSyncError(
            f"{engine_repo} has uncommitted changes to engine docs: {', '.join(dirty)}"
        )
    manifest = build_manifest(engine_repo, commit)
    engine_dir.mkdir(parents=True, exist_ok=True)
    rendered_dir = engine_dir / RENDERED_DIR
    rendered_dir.mkdir(parents=True, exist_ok=True)
    for dest, source in ENGINE_DOCS:
        data = (engine_repo / source).read_bytes()
        (engine_dir / dest).write_bytes(data)
        (rendered_dir / dest).write_bytes(render_myst(data.decode("utf-8")).encode("utf-8"))
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
            f"rendered from satyrn-engine @ {commit} by tools/engine_sync.py ({TRANSFORM_VERSION})",
            [f"{engine_dir.name}/{RENDERED_DIR}/{dest}" for dest, _ in ENGINE_DOCS],
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
    default_url = os.environ.get("SATYRN_ENGINE_URL", DEFAULT_ENGINE_URL)
    fetch = sub.add_parser("fetch", help="clone the pinned engine commit into a checkout")
    fetch.add_argument("--arm", default=os.fspath(DEFAULT_ARM))
    fetch.add_argument("--engine-repo", default=None)
    fetch.add_argument("--url", default=default_url)
    sync = sub.add_parser("sync", help="copy the pinned engine's docs into the committed _engine/ copy")
    sync.add_argument("--arm", default=os.fspath(DEFAULT_ARM))
    sync.add_argument("--engine-repo", default=None)
    sync.add_argument("--output", default=os.fspath(DEFAULT_OUTPUT))
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parents[1]
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
