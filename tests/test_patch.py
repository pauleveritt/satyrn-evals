import pytest

from satyrn_evals.errors import PatchParseError, PatchRejected
from satyrn_evals.patch import check_allowlist, parse_patch_paths

GOOD = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)


def test_parse_paths_extracts_b_side() -> None:
    assert parse_patch_paths(GOOD) == ("solution.py",)


def test_parse_paths_multiple_files() -> None:
    text = (
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n"
        "+++ b/a.py\n"
        "@@ -1 +1 @@\n"
        "-x\n"
        "+y\n"
        "diff --git a/b.py b/b.py\n"
        "--- a/b.py\n"
        "+++ b/b.py\n"
        "@@ -1 +1 @@\n"
        "-x\n"
        "+y\n"
    )
    assert parse_patch_paths(text) == ("a.py", "b.py")


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("diff --git a/x b/x\n--- a/x\n+++ b/x\n", "no hunks"),
        ("@@ -1 +1 @@\n nothing\n", "touches no files"),
    ],
    ids=["no-hunks", "no-paths"],
)
def test_parse_rejects_malformed(text: str, message: str) -> None:
    with pytest.raises(PatchParseError, match=message):
        parse_patch_paths(text)


def test_parse_handles_deleted_file() -> None:
    text = (
        "diff --git a/deleted.py b/deleted.py\n"
        "deleted file mode 100644\n"
        "--- a/deleted.py\n"
        "+++ /dev/null\n"
        "@@ -1 +0,0 @@\n"
        "-gone\n"
    )
    assert parse_patch_paths(text) == ("deleted.py",)


def test_allowlist_accepts_source_paths() -> None:
    check_allowlist(("solution.py",), ("solution.py",))  # must not raise


def test_allowlist_rejects_other_paths() -> None:
    with pytest.raises(PatchRejected, match="non-source"):
        check_allowlist(("test_solution.py",), ("solution.py",))
