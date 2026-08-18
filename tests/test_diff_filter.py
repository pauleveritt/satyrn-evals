import pytest

from satyrn_evals.diff_filter import (
    is_test_path,
    split_file_sections,
    strip_test_hunks,
)
from satyrn_evals.errors import PatchParseError


def _patch(*sections: str) -> str:
    return "\n".join(sections) + "\n"


SOLUTION = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)
TEST_FILE = (
    "diff --git a/test_solution.py b/test_solution.py\n"
    "--- a/test_solution.py\n"
    "+++ b/test_solution.py\n"
    "@@ -1,2 +1,3 @@\n"
    " from solution import double\n"
    "+# regression test comment\n"
)
TESTS_DIR = (
    "diff --git a/tests/test_util.py b/tests/test_util.py\n"
    "--- a/tests/test_util.py\n"
    "+++ b/tests/test_util.py\n"
    "@@ -1 +1 @@\n"
    "-x\n"
    "+y\n"
)


def test_split_sections_single_file() -> None:
    sections = split_file_sections(SOLUTION)
    assert len(sections) == 1
    assert sections[0].path == "solution.py"
    assert sections[0].text.startswith("diff --git a/solution.py")


def test_split_sections_multiple_files() -> None:
    sections = split_file_sections(_patch(SOLUTION, TEST_FILE))
    assert [s.path for s in sections] == ["solution.py", "test_solution.py"]


def test_split_rejects_no_sections() -> None:
    with pytest.raises(PatchParseError, match="no file sections"):
        split_file_sections("@@ -1 +1 @@\n nothing\n")


def test_split_rejects_malformed_header() -> None:
    with pytest.raises(PatchParseError, match="malformed diff header"):
        split_file_sections("diff --git a/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-x\n+y\n")


@pytest.mark.parametrize(
    "path",
    ["test_solution.py", "tests/test_util.py", "a/tests/test_util.py", "conftest.py",
     "my_test.py", "test_thing.py"],
    ids=["test-prefix", "tests-dir", "nested-tests-dir", "conftest", "suffix", "prefix"],
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


def test_strip_keeps_only_source_sections() -> None:
    text, paths = strip_test_hunks(_patch(SOLUTION, TEST_FILE, TESTS_DIR))
    assert paths == ("solution.py",)
    assert "test_solution.py" not in text
    assert "tests/test_util.py" not in text
    assert "solution.py" in text


def test_strip_all_test_paths_returns_empty() -> None:
    text, paths = strip_test_hunks(_patch(TEST_FILE, TESTS_DIR))
    assert text == ""
    assert paths == ()


def test_strip_preserves_source_ordering() -> None:
    text, paths = strip_test_hunks(_patch(TEST_FILE, SOLUTION, TESTS_DIR))
    assert paths == ("solution.py",)


def test_strip_handles_deleted_source_file() -> None:
    deleted = (
        "diff --git a/old.py b/old.py\n"
        "deleted file mode 100644\n"
        "--- a/old.py\n"
        "+++ /dev/null\n"
        "@@ -1 +0,0 @@\n"
        "-gone\n"
    )
    text, paths = strip_test_hunks(deleted)
    assert paths == ("old.py",)
    assert "old.py" in text
