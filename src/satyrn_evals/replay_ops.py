"""Delete-only interpretation of bash commands, for replay diagnosis columns.

Option A of the replay design (2026-10-04, ledger entry "Engine pin moved to
the merge commit 5b681b0"): ``rm``, ``rm -f``, ``rm -r`` and ``rm -rf`` on
literal in-tree paths become :class:`Delete` ops. Everything else (globs,
other variables, ``~``, paths outside ``cwd``, ``mv``, ``mkdir``, redirects,
``python``, ``sed -i``, ``ruff``, ``git``) yields no op and is returned
verbatim in ``Interpretation.skipped``. Nothing is ever run in a shell.

This module is for future diagnosis work. It is not wired into
``classify.py`` or ``counterfactual.py``, and the deciding read
(``line_read``) never uses it.
"""

from __future__ import annotations

import posixpath
import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

_HEREDOC = re.compile(r"<<(-?)[ \t]*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_][A-Za-z0-9_]*))")
_RM_FLAGS = set("rRfv")


@dataclass(frozen=True, slots=True)
class Delete:
    """Remove ``path`` (relative, posix, inside the tree)."""

    path: str
    recursive: bool = False


Op = Delete


@dataclass(frozen=True, slots=True)
class Interpretation:
    ops: tuple[Op, ...]
    skipped: tuple[str, ...]


def _logical_lines(command: str) -> list[str]:
    """Command lines with heredoc bodies removed (the opener line is kept)."""
    out: list[str] = []
    lines = command.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        match = _HEREDOC.search(line)
        if match:
            word = match.group(2) or match.group(3) or match.group(4)
            tabs = "\t*" if match.group(1) else ""
            end = re.compile(rf"^{tabs}{re.escape(word)}[ \t]*$")
            while i < len(lines) and not end.match(lines[i]):
                i += 1
            i += 1  # the terminator itself
    return out


def _split_segments(line: str) -> list[str]:
    """Split on ``;``, ``&&``, ``||`` outside quotes."""
    segments: list[str] = []
    buf: list[str] = []
    quote = ""
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch == ";" or line.startswith(("&&", "||"), i):
            segments.append("".join(buf))
            buf = []
            i += 1 if ch == ";" else 2
            continue
        else:
            buf.append(ch)
        i += 1
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


def _in_tree(token: str, cwd: str | None) -> str | None:
    """The relative in-tree path a literal token names, else None."""
    if not token or any(c in token for c in "*?[]{}`!<>|&\\") or token.startswith("~"):
        return None
    for prefix in ("$WT", "${WT}", "$(pwd)"):
        if token.startswith(prefix + "/"):
            token = token[len(prefix) + 1 :]
            break
    if "$" in token or "(" in token:
        return None
    if token.startswith("/"):
        if cwd is None:
            return None
        roots = {cwd.rstrip("/"), "/private" + cwd.rstrip("/"), cwd.rstrip("/").removeprefix("/private")}
        norm = posixpath.normpath(token)
        for root in sorted(roots, key=len, reverse=True):
            if norm == root or norm.startswith(root + "/"):
                token = norm[len(root) :].lstrip("/")
                break
        else:
            return None
    rel = posixpath.normpath(token) if token else ""
    if rel in ("", ".") or rel == ".." or rel.startswith("../") or rel.startswith("/"):
        return None
    return rel


def _rm(segment: str, cwd: str | None) -> tuple[Delete, ...] | None:
    try:
        words = shlex.split(segment)
    except ValueError:
        return None
    if not words or words[0] != "rm":
        return None
    recursive = False
    paths: list[str] = []
    options_done = False
    for word in words[1:]:
        if not options_done and word == "--":
            options_done = True
        elif not options_done and word.startswith("-") and len(word) > 1:
            letters = set(word[1:])
            if not letters <= _RM_FLAGS:
                return None
            recursive = recursive or bool(letters & set("rR"))
        else:
            rel = _in_tree(word, cwd)
            if rel is None:
                return None
            paths.append(rel)
    if not paths:
        return None
    return tuple(Delete(p, recursive) for p in paths)


def interpret_bash(command: str, cwd: str | None) -> Interpretation:
    """Delete ops for the literal in-tree ``rm`` segments; the rest is skipped."""
    ops: list[Op] = []
    skipped: list[str] = []
    for line in _logical_lines(command):
        for segment in _split_segments(line):
            if segment.split()[0] == "cd":
                continue
            found = _rm(segment, cwd) if not re.search(r"[<>]", segment) else None
            if found is None:
                skipped.append(segment)
            else:
                ops.extend(found)
    return Interpretation(tuple(ops), tuple(skipped))


def apply(ops: tuple[Op, ...] | list[Op], root: Path) -> tuple[Path, ...]:
    """Delete existing paths under ``root``; return what was removed.

    A path is acted on only when its parent resolves inside ``root``, so a
    symlinked directory cannot lead the delete outside. A symlink itself is
    unlinked, never followed. A plain ``rm`` leaves a directory alone.
    """
    base = root.resolve()
    removed: list[Path] = []
    for op in ops:
        rel = Path(op.path)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            continue
        target = base / rel
        if not target.parent.resolve().is_relative_to(base):
            continue
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir() and op.recursive:
            shutil.rmtree(target)
        else:
            continue
        removed.append(target)
    return tuple(removed)
