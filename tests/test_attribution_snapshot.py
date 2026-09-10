"""HP5.1 -- the snapshot and the mutation.

Default tier: these write into a temporary directory and nothing spawns.
"""

from pathlib import Path

from satyrn_evals.attribution import (
    HARNESS_FILES,
    Mutation,
    diff_snapshots,
    snapshot,
)


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_an_unchanged_tree_yields_no_mutation(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", "x\n")
    before = snapshot(tmp_path)
    assert diff_snapshots(before, snapshot(tmp_path)) == ()


def test_a_created_file_is_a_creation(tmp_path: Path) -> None:
    before = snapshot(tmp_path)
    _write(tmp_path, "templates/base.html", "<p>\n")
    assert diff_snapshots(before, snapshot(tmp_path)) == (
        Mutation("templates/base.html", "created"),
    )


def test_a_deleted_file_is_a_deletion(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", "x\n")
    before = snapshot(tmp_path)
    (tmp_path / "app.py").unlink()
    assert diff_snapshots(before, snapshot(tmp_path)) == (
        Mutation("app.py", "deleted"),
    )


def test_a_same_length_edit_is_still_a_modification(tmp_path: Path) -> None:
    """Why this compares digests rather than sizes: an edit that keeps a
    file's length would be invisible to a length check, and a chain replayed
    quickly can leave two different trees sharing a timestamp."""
    _write(tmp_path, "app.py", "aaa\n")
    before = snapshot(tmp_path)
    _write(tmp_path, "app.py", "bbb\n")
    assert len((tmp_path / "app.py").read_text()) == 4
    assert diff_snapshots(before, snapshot(tmp_path)) == (
        Mutation("app.py", "modified"),
    )


def test_mutations_are_path_ordered(tmp_path: Path) -> None:
    before = snapshot(tmp_path)
    for name in ("z.py", "a.py", "m/n.py"):
        _write(tmp_path, name, "x\n")
    assert [m.path for m in diff_snapshots(before, snapshot(tmp_path))] == [
        "a.py",
        "m/n.py",
        "z.py",
    ]


def test_every_harness_file_is_excluded_by_name(tmp_path: Path) -> None:
    """Asserted per name rather than through a pattern, so that adding a
    bookkeeping file to the seam is a visible decision here."""
    assert {
        ".satyrn-packet.json",
        ".satyrn-result.json",
        ".phase-counter",
        ".satyrn-implementer-transcript.jsonl",
        ".satyrn-implementer-stderr.log",
        ".satyrn-implementer-call-counter",
        ".satyrn-self-test-result.json",
    } == HARNESS_FILES
    before = snapshot(tmp_path)
    for name in HARNESS_FILES:
        _write(tmp_path, name, "bookkeeping\n")
    assert diff_snapshots(before, snapshot(tmp_path)) == ()


def test_a_file_named_like_a_harness_file_but_nested_is_not_excluded(
    tmp_path: Path,
) -> None:
    """The exclusion is a workspace-root path, not a basename, so a worker
    cannot hide a mutation by choosing a name."""
    before = snapshot(tmp_path)
    _write(tmp_path, "sub/.satyrn-packet.json", "mine\n")
    assert diff_snapshots(before, snapshot(tmp_path)) == (
        Mutation("sub/.satyrn-packet.json", "created"),
    )


def test_a_directory_is_not_a_mutation(tmp_path: Path) -> None:
    """Only files carry content; an empty directory is not a change anyone
    made to the code."""
    before = snapshot(tmp_path)
    (tmp_path / "empty").mkdir()
    assert diff_snapshots(before, snapshot(tmp_path)) == ()
