"""The document caps in `docs/sdd.md`, enforced in the default tier.

No model, no network, no subprocess.

**Why both directions.** A cap checker's normal state is silence, so a broken
one passes every day without anyone noticing — the exact shape of failure this
repository's rule about sibling tests exists to catch. `test_real_documents_pass`
alone would still pass if `check` returned an empty report unconditionally, so
each refusal below names the failure text it expects.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from lint_docs import (  # noqa: E402
    BACKLOG_ENTRY_CAP,
    DIRECTION_CAP,
    GRANDFATHERED,
    ROOT,
    STATUS_CAP,
    check,
)

PHASE_HEADER = "| # | Phase | Direction (one sentence) | Excludes | Status |"
PHASE_RULE = "|---|---|---|---|---|"


def _roadmap(root: Path, direction: str, excludes: str, status: str) -> None:
    (root / "ROADMAP.md").write_text(
        f"# Roadmap\n\n{PHASE_HEADER}\n{PHASE_RULE}\n"
        f"| V1 | A phase | {direction} | {excludes} | {status} |\n"
    )


def _write(root: Path, name: str, body: str) -> None:
    (root / name).write_text(body)


def test_real_documents_pass() -> None:
    """The success sibling: this repository's own documents are within cap."""
    assert check().failures == []


def test_over_cap_roadmap_is_refused(tmp_path: Path) -> None:
    _write(tmp_path, "ROADMAP.md", "# Roadmap\n" + "\n" * 500)

    failures = check(tmp_path).failures

    assert any("ROADMAP.md" in f and "> 400" in f for f in failures), failures


def test_over_cap_backlog_entry_is_refused(tmp_path: Path) -> None:
    body = "word " * ((BACKLOG_ENTRY_CAP // 5) + 50)
    _write(tmp_path, "BACKLOG.md", f"# Backlog\n\n## Entries\n\n**Too long.** {body}\n")

    failures = check(tmp_path).failures

    assert any("Too long." in f and "research doc is owed" in f for f in failures), failures


def test_backlog_entry_within_cap_is_accepted(tmp_path: Path) -> None:
    """The sibling of the refusal above: a short entry draws no complaint."""
    _write(tmp_path, "BACKLOG.md", "# Backlog\n\n## Entries\n\n**Short.** Reopens never.\n")

    assert check(tmp_path).failures == []


@pytest.mark.parametrize(
    "backlog",
    [
        pytest.param(
            "# Backlog\n\nProse with a **bold span** that is not an entry.\n" + "x" * 1300,
            id="bold-outside-entries-section",
        ),
        pytest.param(
            "# Backlog\n\n**Rules header**\n\n## Entries\n\n**Fine.** Short.\n",
            id="bold-header-before-entries-section",
        ),
    ],
)
def test_bold_text_that_is_not_an_entry_does_not_fire(tmp_path: Path, backlog: str) -> None:
    """An earlier version matched any bold span anywhere and fired on inline
    emphasis and on the file's own rules header. A detector that cannot tell an
    entry from a word is not a detector."""
    _write(tmp_path, "BACKLOG.md", backlog)

    assert check(tmp_path).failures == []


def test_status_cap_measures_status_not_excludes(tmp_path: Path) -> None:
    """Five columns: # | Phase | Direction | Excludes | Status.

    A sibling project added the Excludes column and its positional checker kept
    reading the last two cells, so the Status cap silently began measuring
    Excludes; it was caught only at phase close-out. This pins the mapping.
    """
    _roadmap(tmp_path, direction="short", excludes="Short", status="x" * (STATUS_CAP + 1))

    failures = check(tmp_path).failures

    assert any("Status" in f for f in failures), failures
    assert not any("Direction" in f for f in failures), failures


def test_direction_cap_measures_direction_not_excludes(tmp_path: Path) -> None:
    _roadmap(tmp_path, direction="x" * (DIRECTION_CAP + 1), excludes="Short", status="done")

    failures = check(tmp_path).failures

    assert any("Direction" in f for f in failures), failures
    assert not any("Status" in f for f in failures), failures


def test_a_long_excludes_cell_is_not_capped(tmp_path: Path) -> None:
    """Excludes is deliberately uncapped, matching the sibling project. This is
    the sibling success test for the two pins above: they must fire on the
    columns they name and stay silent on the one they do not."""
    _roadmap(tmp_path, direction="short", excludes="x" * (STATUS_CAP + 1), status="done")

    assert check(tmp_path).failures == []


def test_grandfathered_paths_all_exist() -> None:
    """Every grandfathered path is a real document in *this* repository.

    Copying this file between the two repositories silently carried the other
    one's set across, which both exempted documents that do not exist here and
    stopped exempting the ones that do.
    """
    missing = [p for p in GRANDFATHERED if not (ROOT / p).exists()]

    assert missing == [], missing


def test_trailing_whitespace_is_refused(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    _write(tmp_path, "docs/index.md", "# Docs\n\ntrailing spaces   \n")

    failures = check(tmp_path).failures

    assert (
        any("docs/index.md:3" in f and "trailing whitespace" in f for f in failures),
        failures,
    )


def test_blank_line_at_eof_is_refused(tmp_path: Path) -> None:
    """The D1 defect: the design and plan were committed with a trailing
    blank line because the whitespace check ran on the working tree only."""
    _write(tmp_path, "ROADMAP.md", "# Roadmap\n\ntext\n\n")

    failures = check(tmp_path).failures

    assert any("ROADMAP.md" in f and "blank line at EOF" in f for f in failures), failures


def test_clean_documents_and_the_preserved_record_are_accepted(tmp_path: Path) -> None:
    """The success sibling: clean files draw no complaint, and the preserved
    research record is exempt rather than failing forever."""
    (tmp_path / "docs" / "superpowers" / "research").mkdir(parents=True)
    (tmp_path / "docs" / "guides").mkdir(parents=True)
    _write(tmp_path, "README.md", "# Clean\n\nNo trailing spaces.\n")
    _write(tmp_path, "docs/guides/x.md", "# Guides\n\nClean too.\n")
    _write(tmp_path, "docs/superpowers/research/old.md", "History.   \n\n")

    assert check(tmp_path).failures == []
