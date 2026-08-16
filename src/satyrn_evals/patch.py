"""Unified-diff parsing and the source-path allowlist."""

import re

from satyrn_evals.errors import PatchParseError, PatchRejected

_PATH_RE = re.compile(r"^[+-]{3} (?:[ab]/)?(.*)$")


def parse_patch_paths(patch_text: str) -> tuple[str, ...]:
    """Return the paths a unified diff touches, in order.

    Raises PatchParseError when the text is not a parseable unified diff
    (no hunks, or no file paths). `---`/`+++` lines with a/ b/ prefixes
    are normalized; /dev/null (pure deletions) contributes no path.
    """
    lines = patch_text.splitlines()
    if not any(line.startswith("@@") for line in lines):
        raise PatchParseError("patch has no hunks")
    paths: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if not (m := _PATH_RE.match(line)):
            continue
        path = m.group(1).strip()
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
