"""Enforce the document caps in `docs/sdd.md`.

Caps alone do not work: a predecessor's `ROADMAP.md` reached roughly 1,000
lines, about 800 of them Backlog, under rules that capped cells and plans but
never the file. This checker is the other half.

No model, no network, no subprocess — it fits the default test tier and runs
from `just lint-docs`.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

type Failure = str

FILE_CAPS: dict[str, int] = {
    "ROADMAP.md": 400,
    "BACKLOG.md": 400,
}
GLOB_CAPS: tuple[tuple[str, int], ...] = (
    ("docs/superpowers/specs/*.md", 400),
    ("docs/superpowers/plans/*.md", 400),
)
# Documents that predate the caps. A sibling project hit the same wall and
# recorded the right answer: closed plans are not retrofitted, because the cap
# exists to stop a *live* document growing, and rewriting finished history is
# churn with no reader. New documents get no exemption.
GRANDFATHERED: frozenset[str] = frozenset({
    "docs/superpowers/specs/2026-08-18-v2-capture-by-revert-design.md",
    "docs/superpowers/plans/2026-08-16-v1-grade.md",
    "docs/superpowers/plans/2026-08-18-v2-capture-by-revert.md",
    "docs/superpowers/plans/2026-08-18-v3-attempt-persistence.md",
})

DIRECTION_CAP = 900
STATUS_CAP = 1_000
BACKLOG_ENTRY_CAP = 1_200

# Live documents only. `docs/superpowers/research/` is the preserved record —
# the same reasoning as GRANDFATHERED, taken one step further: a whitespace
# check that fails forever on committed history is a check that gets deleted.
WHITESPACE_SKIP_PARTS = frozenset({"_build", ".venv", "node_modules", "research"})


@dataclass(frozen=True, slots=True)
class Report:
    failures: list[Failure]

    def render(self) -> int:
        for line in self.failures:
            print(f"  {line}")
        if self.failures:
            print(f"\nlint-docs: {len(self.failures)} over cap. "
                  "See docs/sdd.md, 'Document caps'.")
            return 1
        print("lint-docs: all documents within cap")
        return 0


def _cells(line: str) -> list[str] | None:
    """Cells of a Markdown table row, or None if the line is not one."""
    if not line.startswith("|") or set(line) <= set("|- "):
        return None
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _column_index(header: list[str], *names: str) -> int | None:
    """Index of the first column whose header starts with one of `names`."""
    for i, cell in enumerate(header):
        lowered = cell.strip("* ").lower()
        if any(lowered.startswith(n) for n in names):
            return i
    return None


def _phase_rows(text: str) -> list[dict[str, str]]:
    """Phase-table rows keyed by column, or [] if the file has no phase table.

    **Keyed by header, not by position, on purpose.** A sibling project added an
    Excludes column between Direction and Status and its positional checker went
    on measuring the last two cells, so the Status cap silently began measuring
    Excludes — caught only at phase close-out. A cap that moves to another column
    when a column is added is not enforcing the cap it names.
    """
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if (cells := _cells(line)) is None:
            continue
        if header is None:
            if _column_index(cells, "status") is not None:
                header = cells
            continue
        if len(cells) != len(header):
            continue
        direction = _column_index(header, "direction", "ships")
        status = _column_index(header, "status")
        phase = _column_index(header, "#", "phase")
        rows.append({
            "phase": cells[phase] if phase is not None else "?",
            "direction": cells[direction] if direction is not None else "",
            "status": cells[status] if status is not None else "",
        })
    return rows


def _backlog_entries(text: str) -> list[tuple[str, str]]:
    """(label, body) per entry under `## Entries`.

    Only a bold label at the start of a line inside that section counts. An
    earlier version matched any bold span anywhere, so it fired on inline
    emphasis and on this file's own rules header — a detector that cannot tell
    an entry from a word is not a detector.
    """
    section = text.split("\n## Entries\n", 1)
    if len(section) != 2:
        return []
    body = section[1]
    entries = []
    for match in re.finditer(r"^\*\*(.+?)\*\*(.*?)(?=^\*\*|\Z)", body, re.S | re.M):
        entries.append((match.group(1).strip(), match.group(2)))
    return entries


def _whitespace_failures(root: Path) -> list[Failure]:
    """Trailing whitespace and blank lines at EOF in live documents.

    Added by the D1 amendment (2026-09-04): the D1 design and plan were
    committed with a trailing blank line each because `git diff --check` was
    run on the working tree rather than the branch range. The cap checker is
    the always-running half; this closes the same gap for whitespace.
    """
    failures: list[Failure] = []
    paths = sorted(
        {*root.glob("*.md"), *root.glob("docs/*.md"), *root.glob("docs/**/*.md")}
    )
    for path in paths:
        if not path.is_file():
            continue
        if any(part in WHITESPACE_SKIP_PARTS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        lines = path.read_text().splitlines()
        for lineno, line in enumerate(lines, 1):
            if line != line.rstrip():
                failures.append(f"{rel}:{lineno}: trailing whitespace")
        if lines and lines[-1] == "":
            failures.append(f"{rel}: blank line at EOF")
    return failures


def check(root: Path = ROOT) -> Report:
    failures: list[Failure] = []

    for name, cap in FILE_CAPS.items():
        path = root / name
        if not path.exists():
            continue
        n = len(path.read_text().splitlines())
        if n > cap:
            failures.append(f"{name}: {n} lines > {cap}")

    for pattern, cap in GLOB_CAPS:
        for path in sorted(root.glob(pattern)):
            if path.relative_to(root).as_posix() in GRANDFATHERED:
                continue
            n = len(path.read_text().splitlines())
            if n > cap:
                failures.append(f"{path.relative_to(root)}: {n} lines > {cap}")

    failures.extend(_whitespace_failures(root))

    roadmap = root / "ROADMAP.md"
    if roadmap.exists():
        for row in _phase_rows(roadmap.read_text()):
            phase, direction, status = row["phase"], row["direction"], row["status"]
            if len(direction) > DIRECTION_CAP:
                failures.append(
                    f"ROADMAP.md phase {phase}: Direction {len(direction)} chars "
                    f"> {DIRECTION_CAP}")
            if len(status) > STATUS_CAP:
                failures.append(
                    f"ROADMAP.md phase {phase}: Status {len(status)} chars "
                    f"> {STATUS_CAP}")

    backlog = root / "BACKLOG.md"
    if backlog.exists():
        for label, body in _backlog_entries(backlog.read_text()):
            if len(body) > BACKLOG_ENTRY_CAP:
                failures.append(
                    f"BACKLOG.md '{label[:44]}': {len(body)} chars "
                    f"> {BACKLOG_ENTRY_CAP} — a research doc is owed")

    return Report(failures)


if __name__ == "__main__":
    sys.exit(check().render())
