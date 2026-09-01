import pytest

from satyrn_evals.diff_filter import (
    ChangeKind,
    FileChange,
    is_test_path,
    parse_name_status_z,
    without_test_changes,
)
from satyrn_evals.errors import PatchParseError


def test_parse_empty_metadata_is_an_empty_change_set() -> None:
    assert parse_name_status_z("") == ()


def test_parse_ordinary_changes_repeat_the_path_on_both_sides() -> None:
    metadata = "M\0src/na\tme.py\0A\0src/日本語.py\0D\0src/old.py\0"

    assert parse_name_status_z(metadata) == (
        FileChange(ChangeKind.MODIFIED, "src/na\tme.py", "src/na\tme.py", None),
        FileChange(ChangeKind.ADDED, "src/日本語.py", "src/日本語.py", None),
        FileChange(ChangeKind.DELETED, "src/old.py", "src/old.py", None),
    )


def test_parse_rename_and_copy_retain_both_paths_and_scores() -> None:
    metadata = (
        "R100\0src/old name.py\0src/new name.py\0C075\0src/original.py\0src/copied.py\0"
    )

    assert parse_name_status_z(metadata) == (
        FileChange(ChangeKind.RENAMED, "src/old name.py", "src/new name.py", 100),
        FileChange(ChangeKind.COPIED, "src/original.py", "src/copied.py", 75),
    )


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ("M\0src/app.py", "not NUL-terminated"),
        ("\0path.py\0", "empty status"),
        ("Q\0path.py\0", "unknown name-status code"),
        ("M100\0path.py\0", "unexpected suffix"),
        ("R\0old.py\0new.py\0", "lacks a decimal similarity score"),
        ("Rabc\0old.py\0new.py\0", "lacks a decimal similarity score"),
        ("R１２\0old.py\0new.py\0", "lacks a decimal similarity score"),
        ("R101\0old.py\0new.py\0", "outside 0..100"),
        ("M\0", "incomplete name-status record"),
        ("R100\0old.py\0", "incomplete rename/copy record"),
        ("M\0\0", "empty path"),
        ("R100\0\0new.py\0", "empty path"),
        ("C100\0old.py\0\0", "empty path"),
    ],
    ids=[
        "unterminated",
        "empty-status",
        "unknown-status",
        "ordinary-score",
        "missing-rename-score",
        "nondigit-rename-score",
        "non-ascii-rename-score",
        "oversized-score",
        "missing-path",
        "missing-new-path",
        "empty-ordinary-path",
        "empty-old-path",
        "empty-new-path",
    ],
)
def test_parse_rejects_malformed_metadata(metadata: str, message: str) -> None:
    with pytest.raises(PatchParseError, match=message):
        parse_name_status_z(metadata)


@pytest.mark.parametrize(
    "status",
    [
        ChangeKind.TYPE_CHANGED,
        ChangeKind.UNMERGED,
        ChangeKind.UNKNOWN,
        ChangeKind.BROKEN_PAIRING,
    ],
)
def test_parse_accepts_other_git_ordinary_statuses(status: ChangeKind) -> None:
    assert parse_name_status_z(f"{status.value}\0path.py\0") == (
        FileChange(status, "path.py", "path.py", None),
    )


@pytest.mark.parametrize(
    "path",
    [
        "test_solution.py",
        "tests/test_util.py",
        "a/tests/test_util.py",
        "conftest.py",
        "my_test.py",
        "test_thing.py",
    ],
    ids=[
        "test-prefix",
        "tests-dir",
        "nested-tests-dir",
        "conftest",
        "suffix",
        "prefix",
    ],
)
def test_is_test_path_true(path: str) -> None:
    assert is_test_path(path)


@pytest.mark.parametrize(
    "path",
    ["solution.py", "src/app.py", "mytests.py", "setup.py", "tests_helpers.py"],
    ids=["solution", "src", "not-suffix", "setup", "prefix-not-test"],
)
def test_is_test_path_false(path: str) -> None:
    assert not is_test_path(path)


def test_filter_keeps_ordinary_source_changes_as_sibling_success() -> None:
    source = FileChange(ChangeKind.MODIFIED, "src/app.py", "src/app.py", None)
    test = FileChange(
        ChangeKind.MODIFIED, "tests/test_app.py", "tests/test_app.py", None
    )

    assert without_test_changes((source, test)) == (source,)


def test_filter_keeps_rename_and_copy_between_source_paths() -> None:
    rename = FileChange(ChangeKind.RENAMED, "src/old.py", "src/new.py", 100)
    copy = FileChange(ChangeKind.COPIED, "src/original.py", "src/copied.py", 90)

    assert without_test_changes((rename, copy)) == (rename, copy)


@pytest.mark.parametrize(
    "change",
    [
        FileChange(ChangeKind.RENAMED, "src/app.py", "tests/test_app.py", 100),
        FileChange(ChangeKind.RENAMED, "tests/test_app.py", "src/app.py", 100),
        FileChange(ChangeKind.COPIED, "src/app.py", "test_app.py", 80),
    ],
    ids=["rename-into-tests", "rename-out-of-tests", "copy-into-test-file"],
)
def test_filter_excludes_change_when_either_path_is_a_test(change: FileChange) -> None:
    assert without_test_changes((change,)) == ()
