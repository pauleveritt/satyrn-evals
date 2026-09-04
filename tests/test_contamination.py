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
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.overlay import OverlaySpec, load_overlay


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
    patch = "--- a/src/m.py\n+++ b/src/m.py\n@@ -0,0 +1,4 @@\n+    x = 1\n+    y = 2\n+    z = 3\n+    assert x + y == z\n"
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


TASK = "session-mechanics"


def _bundled_spec():
    task_dir = DEFAULT_TASKS_ROOT / TASK
    return load_overlay(task_dir, load_manifest(task_dir))


def _overlay_block(spec, count=5):
    rel = next(rel for rel in spec.rel_paths if rel.endswith(".py"))
    lines = [line for line in spec.texts[rel].splitlines() if line.strip()]
    return rel, lines[:count]


def _patch_adding(path, body):
    return (
        f"--- a/{path}\n+++ b/{path}\n@@ -0,0 +1,{len(body.splitlines())} @@\n"
        + "".join(f"+{line}\n" for line in body.splitlines())
    )


def test_detector_fires_on_contaminated_patch_built_from_bundled_overlay():
    spec = _bundled_spec()
    rel, lines = _overlay_block(spec)
    body = "from textkit import slugify\n\n" + "\n".join(lines) + "\n"
    result = scan_patch(_patch_adding("src/textkit/_leak.py", body), spec)
    assert result.outcome == "flagged"
    assert result.evidence[0].overlay_path == rel
    assert result.evidence[0].in_path == "src/textkit/_leak.py"


def test_detector_silent_on_bundled_known_good():
    spec = _bundled_spec()
    good = (DEFAULT_TASKS_ROOT / TASK / "fixtures" / "known-good.patch").read_text()
    assert scan_patch(good, spec).outcome == "clean"


def test_detector_silent_on_model_authored_restatement():
    spec = _bundled_spec()
    body = (
        "from textkit import slugify\n\n"
        "def test_slug_lowercases():\n    assert slugify('A B') == 'a-b'\n"
    )
    result = scan_patch(_patch_adding("tests/test_restatement.py", body), spec)
    assert result.outcome == "clean"


def test_scan_texts_matches_task_relative_overlay_name_too():
    # passes via rel-suffix subsumption: the task-relative mention
    # "grader/overlay/tests/t_hidden.py" contains the rel path
    # "tests/t_hidden.py" as a substring, which scan_texts matches
    # without emitting any machine-specific absolute candidate.
    spec = make_spec()
    sources = [("step2/tool_end", "opened grader/overlay/tests/t_hidden.py")]
    assert scan_texts(sources, spec).outcome == "flagged"


def test_evidence_serializes_with_in_key() -> None:
    """The wire shape keys the artifact ``in``, per V7 spec §7 — never in_path."""
    from satyrn_evals.contamination import Evidence, evidence_dict

    item = evidence_dict(Evidence("block", "tests/t_hidden.py", "src/m.py", 3))
    assert item == {
        "kind": "block",
        "overlay_path": "tests/t_hidden.py",
        "in": "src/m.py",
        "line": 3,
    }
    assert "in_path" not in item


# The shared redirect idiom: present BOTH in the vendored public tests
# (base/tests/test_app.py) and in the 13-test overlay. Re-derived 2026-09-04
# on the committed task trees: 13 shared non-blank lines, 1 shared window at
# width 4, 0 at width 5.
IDIOM = (
    "        follow_redirects=False,\n"
    "    )\n"
    "    assert response.status_code == 303\n"
    '    assert response.headers["location"] == "/complaints"\n'
)


def _spec_with(body: str) -> OverlaySpec:
    return OverlaySpec(
        root=Path("overlay"),
        rel_paths=("test_acceptance.py",),
        digests={"test_acceptance.py": "d"},
        texts={"test_acceptance.py": body},
    )


def test_window_shared_with_visible_text_stays_silent():
    overlay = "def test_redirect():\n" + IDIOM       # 5 non-blank lines
    spec = _spec_with(overlay)
    patch = _patch_adding("tests/test_new.py", IDIOM)  # the 4 shared lines only
    # the identical window sits in a model-visible file -> not evidence
    assert scan_patch(patch, spec, visible_texts=[IDIOM]).outcome == "clean"
    # without the visible text the same patch is exactly today's flag
    assert scan_patch(patch, spec).outcome == "flagged"


def test_visible_subtraction_still_fires_on_overlay_only_content():
    secret = "    assert SECRET_FLAG is True\n    x = 1\n    y = 2\n    z = 3\n"
    overlay = "def test_hidden():\n" + secret
    spec = _spec_with(overlay)
    patch = _patch_adding("app.py", "def test_hidden():\n" + secret)
    result = scan_patch(patch, spec, visible_texts=[IDIOM])  # visible lacks secret
    assert result.outcome == "flagged"
    assert result.evidence[0].overlay_path == "test_acceptance.py"


def test_default_visible_preserves_current_behavior():
    body = "def test_a():\n    x = 1\n    y = 2\n    z = 3\n    assert x + y == z\n"
    spec = _spec_with(body)
    patch = _patch_adding("src/m.py", body)
    assert scan_patch(patch, spec).outcome == "flagged"
    assert scan_patch(patch, spec, visible_texts=[]).outcome == "flagged"


def test_whole_file_visible_subtraction():
    body = "a = 1\nb = 2\n"  # shorter than GRADER_BLOCK_LINES -> whole-file match
    spec = _spec_with(body)
    patch = _patch_adding("y.py", body)
    assert scan_patch(patch, spec, visible_texts=[body]).outcome == "clean"
