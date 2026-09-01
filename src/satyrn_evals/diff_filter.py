"""Parse Git's NUL-delimited change metadata and apply the test-path rule.

Capture asks Git for ``--name-status -z`` metadata separately from patch
content. Git therefore owns path quoting and rename detection; this module
only turns that unambiguous metadata into typed values and removes changes
that touch a test path.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from satyrn_evals.errors import PatchParseError


class ChangeKind(StrEnum):
    """Status letters emitted by ``git diff --name-status``."""

    ADDED = "A"
    COPIED = "C"
    DELETED = "D"
    MODIFIED = "M"
    RENAMED = "R"
    TYPE_CHANGED = "T"
    UNMERGED = "U"
    UNKNOWN = "X"
    BROKEN_PAIRING = "B"


@dataclass(frozen=True, slots=True)
class FileChange:
    """One changed path pair reported by Git.

    Ordinary changes repeat their single path on both sides. Renames and
    copies retain both paths and their similarity percentage.
    """

    kind: ChangeKind
    old_path: str
    new_path: str
    similarity: int | None


type NameStatus = tuple[FileChange, ...]


def _parse_status(token: str) -> tuple[ChangeKind, int | None]:
    if not token:
        raise PatchParseError("name-status record has an empty status")
    try:
        kind = ChangeKind(token[0])
    except ValueError:
        raise PatchParseError(f"unknown name-status code: {token!r}") from None

    suffix = token[1:]
    match kind:
        case ChangeKind.RENAMED | ChangeKind.COPIED:
            if not suffix.isascii() or not suffix.isdigit():
                raise PatchParseError(
                    f"rename/copy status lacks a decimal similarity score: {token!r}"
                )
            similarity = int(suffix)
            if similarity > 100:
                raise PatchParseError(f"similarity score is outside 0..100: {token!r}")
            return kind, similarity
        case _:
            if suffix:
                raise PatchParseError(
                    f"ordinary status has an unexpected suffix: {token!r}"
                )
            return kind, None


def parse_name_status_z(metadata: str) -> NameStatus:
    """Parse output from ``git diff --name-status -z --find-renames``.

    A non-empty stream must end in NUL. Rename and copy records contain a
    status plus old and new paths; every other record contains one path.
    Paths are returned exactly as Git emitted them, including tabs and
    Unicode characters.
    """
    if not metadata:
        return ()
    if not metadata.endswith("\0"):
        raise PatchParseError("name-status metadata is not NUL-terminated")

    fields = metadata[:-1].split("\0")
    changes: list[FileChange] = []
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        kind, similarity = _parse_status(status)

        match kind:
            case ChangeKind.RENAMED | ChangeKind.COPIED:
                if index + 1 >= len(fields):
                    raise PatchParseError(f"incomplete rename/copy record: {status!r}")
                old_path, new_path = fields[index], fields[index + 1]
                index += 2
            case _:
                if index >= len(fields):
                    raise PatchParseError(f"incomplete name-status record: {status!r}")
                old_path = new_path = fields[index]
                index += 1

        if not old_path or not new_path:
            raise PatchParseError(f"name-status record has an empty path: {status!r}")
        changes.append(
            FileChange(
                kind=kind,
                old_path=old_path,
                new_path=new_path,
                similarity=similarity,
            )
        )
    return tuple(changes)


def is_test_path(path: str) -> bool:
    """The spec's test-path rule: test_*, *_test.py, conftest.py, tests/ component."""
    parts = Path(path).parts
    if "tests" in parts:
        return True
    base = parts[-1]
    return (
        base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py"
    )


def without_test_changes(changes: Iterable[FileChange]) -> NameStatus:
    """Keep changes whose old and new paths are both non-test paths."""
    return tuple(
        change
        for change in changes
        if not is_test_path(change.old_path) and not is_test_path(change.new_path)
    )
