from datetime import UTC, datetime

from satyrn_evals.attempt import attempt_dir_name, decide_refusal

GOOD_PATCH = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)
TRANSCRIPT = "read the task; wrote the fix\n"


def test_valid_artifacts_proceed() -> None:
    assert decide_refusal(GOOD_PATCH, TRANSCRIPT) is None


def test_missing_patch_is_no_patch() -> None:
    assert decide_refusal(None, TRANSCRIPT) == "NO_PATCH"


def test_empty_patch_is_no_patch() -> None:
    assert decide_refusal("", TRANSCRIPT) == "NO_PATCH"


def test_whitespace_patch_is_no_patch() -> None:
    assert decide_refusal("   \n", TRANSCRIPT) == "NO_PATCH"


def test_non_diff_patch_is_patch_invalid() -> None:
    assert decide_refusal("this is not a unified diff\n", TRANSCRIPT) == "PATCH_INVALID"


def test_missing_transcript_is_transcript_missing() -> None:
    assert decide_refusal(GOOD_PATCH, None) == "TRANSCRIPT_MISSING"


def test_empty_transcript_is_transcript_empty() -> None:
    assert decide_refusal(GOOD_PATCH, "") == "TRANSCRIPT_EMPTY"


def test_whitespace_transcript_is_transcript_empty() -> None:
    assert decide_refusal(GOOD_PATCH, "  \n") == "TRANSCRIPT_EMPTY"


def test_patch_checked_before_transcript() -> None:
    # both bad: patch fails first (spec: patch checks run first)
    assert decide_refusal(None, None) == "NO_PATCH"
    assert decide_refusal("not a diff\n", None) == "PATCH_INVALID"


def test_attempt_dir_name_is_deterministic_given_when() -> None:
    when = datetime(2026, 8, 18, 14, 15, 23, 123456, tzinfo=UTC)
    assert attempt_dir_name("format_number", when) == "format_number-20260818-141523-123456"


def test_attempt_dir_name_changes_with_when() -> None:
    a = attempt_dir_name("t", datetime(2026, 8, 18, 14, 15, 23, 1, tzinfo=UTC))
    b = attempt_dir_name("t", datetime(2026, 8, 18, 14, 15, 23, 2, tzinfo=UTC))
    assert a != b
