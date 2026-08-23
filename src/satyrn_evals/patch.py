"""Unified-diff parsing and the source-path allowlist."""

import ast
import re

from satyrn_evals.errors import PatchParseError, PatchRejected

_PATH_RE = re.compile(r"^[+-]{3} (.*)$")
_EXTENDED_PATH_PREFIXES = ("rename from ", "rename to ", "copy from ", "copy to ")
_OCTAL_ESCAPE_RE = re.compile(r"\\[0-7]{3}")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


def _decode_git_path(value: str, *, strip_side_prefix: bool) -> str:
    """Decode one path from Git's unified-diff header representation."""
    if value.startswith('"'):
        quoted = value
        try:
            decoded = ast.literal_eval(value)
        except (SyntaxError, ValueError) as e:
            raise PatchParseError(f"malformed quoted patch path: {value}") from e
        value = decoded
        if _OCTAL_ESCAPE_RE.search(quoted):
            value = value.encode("latin-1").decode(
                "utf-8", errors="surrogateescape"
            )
    if strip_side_prefix and value.startswith(("a/", "b/")):
        return value[2:]
    return value


def _take_git_token(value: str) -> tuple[str, str]:
    """Take one raw token while preserving Git's C-style quoted spelling."""
    if not value:
        raise PatchParseError("Git patch header is missing a path")
    if not value.startswith('"'):
        token, separator, rest = value.partition(" ")
        return token, rest.lstrip() if separator else ""
    escaped = False
    for index, character in enumerate(value[1:], start=1):
        if character == '"' and not escaped:
            return value[: index + 1], value[index + 1 :].lstrip()
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    raise PatchParseError(f"malformed quoted patch path: {value}")


def _diff_header_paths(line: str) -> tuple[str, str]:
    """Decode an unambiguous ``diff --git`` header.

    Git does not quote ordinary spaces, so splitting at the first space is
    wrong. A section without ``---``/``+++`` or extended rename/copy headers
    is a same-path binary, empty-file, or mode-only change. Find the split
    whose ``a/`` and ``b/`` suffixes agree. Fully quoted headers remain
    independently tokenizable.
    """
    value = line.removeprefix("diff --git ")
    if value.startswith('"'):
        first, remaining = _take_git_token(value)
        second, trailing = _take_git_token(remaining)
        if trailing:
            raise PatchParseError(f"malformed diff header: {line}")
        return _decode_git_path(
            first, strip_side_prefix=True
        ), _decode_git_path(second, strip_side_prefix=True)

    matches = [
        (value[:index], value[index + 1 :])
        for match in re.finditer(r" b/", value)
        if (index := match.start()) > 0
        and value[:index].startswith("a/")
        and value[index + 1 :].startswith("b/")
        and value[:index].removeprefix("a/")
        == value[index + 1 :].removeprefix("b/")
    ]
    if len(matches) != 1:
        raise PatchParseError(f"ambiguous diff header: {line}")
    first, second = matches[0]
    return _decode_git_path(first, strip_side_prefix=True), _decode_git_path(
        second, strip_side_prefix=True
    )


def _header_path(value: str) -> str:
    """Decode a ``---``/``+++`` path, excluding an optional tab timestamp."""
    return _decode_git_path(value.split("\t", 1)[0], strip_side_prefix=True)


def _traditional_paths(lines: list[str]) -> tuple[str, ...]:
    """Read file headers from traditional unified diff sections safely."""
    paths: list[str] = []
    old_remaining = new_remaining = 0
    for line in lines:
        if old_remaining or new_remaining:
            match line[:1]:
                case " ":
                    old_remaining -= 1
                    new_remaining -= 1
                case "-":
                    old_remaining -= 1
                case "+":
                    new_remaining -= 1
            continue
        if hunk := _HUNK_RE.match(line):
            old_remaining = int(hunk.group(1) or "1")
            new_remaining = int(hunk.group(2) or "1")
        elif header := _PATH_RE.match(line):
            paths.append(_header_path(header.group(1)))
    return tuple(paths)


def parse_patch_paths(patch_text: str) -> tuple[str, ...]:
    """Return the paths a unified diff touches, in order.

    Git extended patches may represent binary, rename/copy, empty-file, and
    mode-only changes without ``@@`` hunks or ``---``/``+++`` lines. Paths
    therefore come from every ``diff --git`` header as well as traditional
    file headers and rename/copy metadata. Quoted control characters are
    decoded; ``/dev/null`` contributes no path.
    """
    lines = patch_text.splitlines()
    paths: list[str] = []
    seen: set[str] = set()
    sections: list[list[str]] = []
    for line in lines:
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)

    for path in _traditional_paths(lines):
        if path != "/dev/null" and path and path not in seen:
            seen.add(path)
            paths.append(path)

    for section in sections:
        candidates: list[str] = []
        has_traditional_headers = bool(_traditional_paths(section[1:]))
        for line in section[1:]:
            if line.startswith(("@@ ", "GIT binary patch", "Binary files ")):
                break
            if m := _PATH_RE.match(line):
                candidates.append(_header_path(m.group(1)))
                continue
            for prefix in _EXTENDED_PATH_PREFIXES:
                if line.startswith(prefix):
                    candidates.append(
                        _decode_git_path(
                            line.removeprefix(prefix), strip_side_prefix=False
                        )
                    )
                    break
        if not candidates and not has_traditional_headers:
            candidates.extend(_diff_header_paths(section[0]))
        for path in candidates:
            if path == "/dev/null" or not path or path in seen:
                continue
            seen.add(path)
            paths.append(path)
    if not paths:
        raise PatchParseError("patch touches no files")
    return tuple(paths)


def check_allowlist(paths: tuple[str, ...], source_paths: tuple[str, ...]) -> None:
    allowed = set(source_paths)
    for path in paths:
        if path not in allowed:
            raise PatchRejected(f"patch touches non-source path: {path}")
