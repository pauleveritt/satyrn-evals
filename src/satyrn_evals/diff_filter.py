"""Unified-diff file-section splitting and the test-path rule.

Capture needs to strip hunks that touch test files from a fix diff: tests
stay at base, so the known-good patch may only touch source paths. This
module splits a unified diff into per-file sections, classifies each path
by the spec's test-path rule, and filters.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.errors import PatchParseError

_HEADER_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")


@dataclass(frozen=True, slots=True)
class FileSection:
    path: str
    text: str


def split_file_sections(patch_text: str) -> tuple[FileSection, ...]:
    """Split a unified diff into per-file sections, in order."""
    lines = patch_text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("diff --git ")]
    if not starts:
        raise PatchParseError("patch has no file sections")
    sections: list[FileSection] = []
    for j, start in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(lines)
        header = _HEADER_RE.match(lines[start])
        if not header:
            raise PatchParseError(f"malformed diff header: {lines[start]}")
        a_side, b_side = header.group(1), header.group(2)
        path = b_side if b_side != "/dev/null" else a_side
        if not path:
            raise PatchParseError(f"diff header names no file: {lines[start]}")
        sections.append(FileSection(path=path, text="\n".join(lines[start:end]) + "\n"))
    return tuple(sections)


def is_test_path(path: str) -> bool:
    """The spec's test-path rule: test_*, *_test.py, conftest.py, tests/ component."""
    parts = Path(path).parts
    if "tests" in parts:
        return True
    base = parts[-1]
    return base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py"


def strip_test_hunks(patch_text: str) -> tuple[str, tuple[str, ...]]:
    """Return (source-only patch text, source paths in order).

    Test-path sections are dropped. Every section a test path yields
    ("", ()), which the caller maps to the NO_SOURCE_CHANGE refusal.
    """
    sections = split_file_sections(patch_text)
    kept = [s for s in sections if not is_test_path(s.path)]
    return ("".join(s.text for s in kept), tuple(s.path for s in kept))
