from pathlib import Path

import pytest

from satyrn_evals.contamination import (
    CheckResult,
    overall,
    overlay_absent_from_inventory,
    payload_strings,
    scan_patch,
    scan_texts,
)
from satyrn_evals.overlay import OverlaySpec


def make_spec() -> OverlaySpec:
    return OverlaySpec(
        root=Path("grader/overlay"),
        rel_paths=("tests/t_hidden.py",),
        digests={"tests/t_hidden.py": "abc"},
        texts={
            "tests/t_hidden.py": (
                "def test_a():\n\n    x = 1\n    y = 2\n    z = 3\n"
                "    assert x + y == z\n"
            )
        },
    )


def test_patch_copying_overlay_block_flags():
    leaked = (
        "from textkit import x\n\ndef test_copy():\n    x = 1\n    y = 2\n"
        "    z = 3\n    assert x + y == z\n"
    )
    patch = (
        "--- a/src/m.py\n+++ b/src/m.py\n@@ -0,0 +1,6 @@\n"
        + "".join(f"+{line}\n" for line in leaked.splitlines())
    )
    result = scan_patch(patch, make_spec())
    assert result.outcome == "flagged"
    assert result.evidence[0].overlay_path == "tests/t_hidden.py"
    assert result.evidence[0].in_path == "src/m.py"
    assert result.evidence[0].line >= 1
    assert result.evidence[0].kind == "block"


def test_patch_with_one_idiomatic_line_stays_clean():
    patch = "--- a/src/m.py\n+++ b/src/m.py\n@@ -0,0 +1,2 @@\n+import pytest\n+assert True\n"
    assert scan_patch(patch, make_spec()).outcome == "clean"


def test_blank_lines_never_interrupt_a_run():
    # the overlay's interior blank line separates def from body; the patch
    # omits it — the non-blank sequences still align and the run matches
    patch = "--- a/src/m.py\n+++ b/src/m.py\n@@ -0,0 +1,4 @@\n+x = 1\n+y = 2\n+z = 3\n+assert x + y == z\n"
    assert scan_patch(patch, make_spec()).outcome == "flagged"


def test_short_overlay_file_flags_only_as_whole_file():
    spec = OverlaySpec(
        root=Path("grader/overlay"), rel_paths=("t.py",),
        digests={"t.py": "d"}, texts={"t.py": "a = 1\nb = 2\n"},
    )
    patch = "--- a/src/m.py\n+++ b/src/m.py\n@@ -0,0 +1,2 @@\n+a = 1\n+b = 2\n"
    result = scan_patch(patch, spec)
    assert result.outcome == "flagged"
    assert result.evidence[0].kind == "whole_file"


def test_missing_patch_is_unmeasured():
    assert scan_patch(None, make_spec()).outcome == "unmeasured"


def test_clean_patch_stays_clean():
    patch = "--- a/src/m.py\n+++ b/src/m.py\n@@ -0,0 +1,1 @@\n+plain code\n"
    assert scan_patch(patch, make_spec()).outcome == "clean"


def test_payload_substring_of_overlay_path_flags():
    sources = [("step1/turn_end", '{"file": "tests/t_hidden.py"}')]
    result = scan_texts(sources, make_spec())
    assert result.outcome == "flagged"
    assert result.evidence[0].kind == "path"


def test_no_retained_sources_is_unmeasured():
    assert scan_texts([], make_spec()).outcome == "unmeasured"
    assert scan_texts([("step1/turn_end", None)], make_spec()).outcome == "unmeasured"


def test_payload_strings_walks_nested_values():
    payload = {"a": "x", "b": {"c": ["y", 1, {"d": "z"}]}}
    assert sorted(payload_strings(payload)) == ["x", "y", "z"]


def test_absence_predicate_both_ways():
    spec = make_spec()
    assert overlay_absent_from_inventory({"src/m.py": "ddd"}, spec)
    assert not overlay_absent_from_inventory({"tests/t_hidden.py": "abc"}, spec)
    assert not overlay_absent_from_inventory({"src/copy.py": "abc"}, spec)  # digest hit


def test_overall_precedence():
    assert overall([CheckResult("grader_content_in_patch", "clean", ())]) == "clean"
    assert overall([
        CheckResult("grader_content_in_patch", "clean", ()),
        CheckResult("grader_name_in_payload", "unmeasured", ()),
    ]) == "unmeasured"
    assert overall([
        CheckResult("grader_name_in_payload", "unmeasured", ()),
        CheckResult("grader_content_in_patch", "flagged", ()),
    ]) == "flagged"
    with pytest.raises(ValueError):
        overall([])
