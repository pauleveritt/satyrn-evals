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

from lint_docs import BACKLOG_ENTRY_CAP, check  # noqa: E402


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
            "# Backlog\n\nProse with a **bold span** that is not an entry.\n" + "x " * 900,
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
