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


def test_hunk_content_that_looks_like_a_header_is_not_a_path() -> None:
    text = (
        "diff --git a/source.txt b/source.txt\n"
        "--- a/source.txt\n"
        "+++ b/source.txt\n"
        "@@ -1 +1 @@\n"
        "--- option\n"
        "+fixed\n"
    )
    assert parse_patch_paths(text) == ("source.txt",)


def test_traditional_unified_diff_without_git_headers_is_supported() -> None:
    text = (
        "--- a/first.py\n"
        "+++ b/first.py\n"
        "@@ -1 +1 @@\n"
        "--- option\n"
        "+fixed\n"
        "--- a/second.py\n"
        "+++ b/second.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    assert parse_patch_paths(text) == ("first.py", "second.py")


@pytest.mark.parametrize("traditional_first", [True, False])
def test_mixed_traditional_and_git_sections_cannot_bypass_allowlist(
    traditional_first: bool,
) -> None:
    traditional = (
        "--- a/test_solution.py\n"
        "+++ b/test_solution.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    text = traditional + GOOD if traditional_first else GOOD + traditional
    paths = parse_patch_paths(text)
    assert set(paths) == {"test_solution.py", "solution.py"}
    with pytest.raises(PatchRejected, match="test_solution.py"):
        check_allowlist(paths, ("solution.py",))


def test_parse_accepts_header_without_hunks() -> None:
    text = "diff --git a/x b/x\n--- a/x\n+++ b/x\n"
    assert parse_patch_paths(text) == ("x",)


def test_parse_rejects_patch_without_file_section() -> None:
    with pytest.raises(PatchParseError, match="touches no files"):
        parse_patch_paths("@@ -1 +1 @@\n nothing\n")


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


def test_parse_decodes_git_quoted_control_characters() -> None:
    text = (
        'diff --git "a/src/na\\tme.py" "b/src/na\\tme.py"\n'
        '--- "a/src/na\\tme.py"\n'
        '+++ "b/src/na\\tme.py"\n'
        "@@ -1 +1 @@\n"
        "-x\n"
        "+y\n"
    )
    assert parse_patch_paths(text) == ("src/na\tme.py",)


def test_parse_preserves_spaces_and_nested_prefix_components() -> None:
    text = (
        "diff --git a/a/b/space.py b/a/b/space.py\n"
        "--- a/a/b/space.py\n"
        "+++ b/a/b/space.py\n"
        "@@ -1 +1 @@\n"
        "-x\n"
        "+y\n"
    )
    assert parse_patch_paths(text) == ("a/b/space.py",)


def test_parse_preserves_space_in_same_path_header() -> None:
    text = (
        "diff --git a/src/space name.py b/src/space name.py\n"
        "index 1234567..89abcde 100644\n"
        "GIT binary patch\n"
        "literal 1\n"
        "Ic${MZ000310RR91\n"
    )
    assert parse_patch_paths(text) == ("src/space name.py",)


def test_parse_extended_rename_and_copy_without_hunks() -> None:
    text = (
        "diff --git a/old name.py b/new name.py\n"
        "similarity index 100%\n"
        "rename from a/old name.py\n"
        "rename to a/new name.py\n"
        "diff --git a/source.py b/copied.py\n"
        "similarity index 100%\n"
        "copy from source.py\n"
        "copy to copied.py\n"
    )
    assert parse_patch_paths(text) == (
        "a/old name.py",
        "a/new name.py",
        "source.py",
        "copied.py",
    )


def test_parse_binary_and_empty_deletion_without_hunks() -> None:
    text = (
        "diff --git a/data.bin b/data.bin\n"
        "index 1234567..89abcde 100644\n"
        "GIT binary patch\n"
        "literal 1\n"
        "Ic${MZ000310RR91\n"
        "diff --git a/empty.py b/empty.py\n"
        "deleted file mode 100644\n"
        "index e69de29..0000000\n"
    )
    assert parse_patch_paths(text) == ("data.bin", "empty.py")


def test_parse_decodes_git_octal_utf8_path() -> None:
    text = (
        'diff --git "a/src/\\346\\227\\245.py" "b/src/\\346\\227\\245.py"\n'
        '--- "a/src/\\346\\227\\245.py"\n'
        '+++ "b/src/\\346\\227\\245.py"\n'
    )
    assert parse_patch_paths(text) == ("src/日.py",)


def test_parse_header_only_diff_with_mixed_quoted_tokens() -> None:
    text = 'diff --git "a/source.py" b/source.py\nold mode 100644\nnew mode 100755\n'
    assert parse_patch_paths(text) == ("source.py",)


def test_parse_header_only_diff_with_escaped_quote() -> None:
    text = (
        'diff --git "a/src/na\\\"me.py" "b/src/na\\\"me.py"\n'
        "old mode 100644\n"
        "new mode 100755\n"
    )
    assert parse_patch_paths(text) == ('src/na"me.py',)


def test_traditional_hunk_ignores_no_newline_marker() -> None:
    text = (
        "--- a/source.py\n"
        "+++ b/source.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "\\ No newline at end of file\n"
        "+new\n"
        "\\ No newline at end of file\n"
    )
    assert parse_patch_paths(text) == ("source.py",)


@pytest.mark.parametrize(
    "header",
    [
        'diff --git "a/x"',
        "diff --git a/old.py b/new.py",
        "diff --git a/x b/x trailing",
        'diff --git "a/x" "b/x" trailing',
        'diff --git "a/x" "b/x',
    ],
)
def test_parse_rejects_ambiguous_or_malformed_diff_header(header: str) -> None:
    with pytest.raises(PatchParseError, match="ambiguous|malformed|missing"):
        parse_patch_paths(header + "\n")


def test_parse_rejects_invalid_quoted_path() -> None:
    text = (
        "diff --git a/x.py b/x.py\n"
        '--- "unterminated\n'
        "+++ b/x.py\n"
        "@@ -1 +1 @@\n-x\n+y\n"
    )
    with pytest.raises(PatchParseError, match="quoted patch path"):
        parse_patch_paths(text)


def test_allowlist_accepts_source_paths() -> None:
    check_allowlist(("solution.py",), ("solution.py",))  # must not raise


def test_allowlist_rejects_other_paths() -> None:
    with pytest.raises(PatchRejected, match="non-source"):
        check_allowlist(("test_solution.py",), ("solution.py",))
