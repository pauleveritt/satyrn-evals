
from satyrn_evals.capture import slugify_subject
from satyrn_evals.manifest import is_valid_task_name


def test_slugify_subject() -> None:
    assert slugify_subject("Fix off-by-one in index computation") == "fix-off-by-one-in-index-computation"


def test_slugify_subject_handles_punctuation() -> None:
    assert slugify_subject("  Fix: double(n) returns n  ") == "fix-double-n-returns-n"


def test_slugify_subject_lowercases() -> None:
    assert slugify_subject("Add SortedSet") == "add-sortedset"


def test_slugify_subject_empty_is_none() -> None:
    assert slugify_subject("") is None
    assert slugify_subject("!!!") is None


def test_slugify_subject_result_is_valid_task_name() -> None:
    assert is_valid_task_name(slugify_subject("Fix the broken thing: part 2!"))
