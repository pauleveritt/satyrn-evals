"""The generator's pure core: spec, exclusions, residue, the R1-plan rung, the broken patch, the manifest."""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt import contract_digest
from tools.cut_task import (
    IGNORED_PATHS,
    RUNG,
    CutError,
    broken_patch,
    excluded,
    load_spec,
    manifest_body,
    parse_collected,
    plan_section,
    r1_plan_prompt,
    residue_gitignore,
)

SPECS = Path(__file__).resolve().parent.parent / "tools" / "task_specs"
SHA_A, SHA_B = "a" * 40, "b" * 40
SPEC = {
    "name": "t", "base": SHA_A, "good": SHA_B, "files": ["tools/x.py"], "hidden": ["tests/test_x.py"],
    "plan": {"path": "docs/plan.md", "heading": "### Task 1: X", "commit": SHA_A},
    "formats": "", "broken": {"tools/x.py": "def f():\n    return None\n"}, "oracle_env": {},
}
PLAN = """# Plan

### Chunk 1: The x tool

**Files:**
- Create: `tools/x.py`, `tests/test_x.py`

**Interfaces:**
- Consumes: `y()` from Task 0
- Produces: `f() -> int`

- [ ] **Stage 1: Failing test**

```python
def test_f():
    assert f() == 1
```

- [ ] **Stage 2: Run** `uv run pytest tests/test_x.py -q` → FAIL

---

### Chunk 2: Other
"""


def _spec(tmp_path: Path, **over: object) -> Path:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps({**SPEC, **over}))
    return path


def test_a_complete_spec_loads(tmp_path: Path) -> None:
    spec = load_spec(_spec(tmp_path))
    assert (spec.files, spec.hidden, spec.plan.heading) == (("tools/x.py",), ("tests/test_x.py",), "### Task 1: X")


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"base": "abc"}, "base must be a full 40-hex commit"),
        ({"extra": 1}, "keys must be exactly"),
        ({"broken": {}}, "broken must name at least one file"),
        ({"broken": {"tools/x.py": "no newline"}}, "must end with a newline"),
        ({"hidden": ["tests/a/test_x.py", "tests/b/test_x.py"]}, "basenames must be distinct"),
        ({"hidden": ["test_x.py"]}, "must sit under a directory"),
        ({"plan": {"path": "p", "heading": "h"}}, "plan must be"),
    ],
)
def test_a_malformed_spec_is_refused(tmp_path: Path, over: dict[str, object], message: str) -> None:
    with pytest.raises(CutError, match=message):
        load_spec(_spec(tmp_path, **over))


def test_every_committed_spec_loads() -> None:
    names = sorted(load_spec(path).name for path in SPECS.glob("*.json"))
    assert names == ["selfhost-docs-linter", "selfhost-guard-prefixes", "selfhost-review-script", "selfhost-run-record-gate"]


@pytest.mark.parametrize(
    "path",
    ["docs/superpowers/plans/p.md", "docs/superpowers/specs/s.md", ".claude/settings.json", ".github/w.yml", "PROVENANCE.md", "tests/test_x.py"],
)
def test_the_answer_bearing_paths_stay_out_of_the_base(path: str) -> None:
    assert excluded(path, ["tests/test_x.py"])


@pytest.mark.parametrize("path", ["docs/lessons.md", "tests/test_other.py", "tools/x.py", "docs/superpowers/research/r.md"])
def test_everything_else_stays_in_the_base(path: str) -> None:
    assert not excluded(path, ["tests/test_x.py"])


def test_a_gitignore_that_ignores_all_residue_is_left_alone() -> None:
    assert residue_gitignore(".venv/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n") is None


def test_missing_residue_patterns_are_appended_or_written() -> None:
    assert residue_gitignore("node_modules/") == "node_modules/\n.pytest_cache/\n__pycache__/\n.ruff_cache/\n.venv/\n"
    assert residue_gitignore(None) == ".pytest_cache/\n__pycache__/\n.ruff_cache/\n.venv/\n"


def test_the_plan_section_runs_to_the_next_rule_or_heading() -> None:
    section = plan_section(PLAN, "### Chunk 1: The x tool")
    assert section.startswith("### Chunk 1: The x tool") and "Chunk 2" not in section and "---" not in section


def test_a_plan_without_the_heading_is_refused() -> None:
    with pytest.raises(CutError, match="no heading"):
        plan_section(PLAN, "### Chunk 9: Absent")


def test_the_r1_plan_rung_keeps_prose_and_produces_and_drops_code_consumes_and_hidden_names() -> None:
    prompt = r1_plan_prompt(plan_section(PLAN, "### Chunk 1: The x tool"), ["tests/test_x.py"], "`f` returns `1`.")
    assert prompt.startswith("Chunk 1: The x tool\n\nFiles:\n")
    assert "Produces: `f() -> int`" in prompt
    assert "Consumes" not in prompt and "def test_f" not in prompt and "**" not in prompt and "- [ ]" not in prompt
    assert "test_x.py" not in prompt and "its test module" not in prompt
    assert "- Create: `tools/x.py`, `tests/`" in prompt and "`uv run pytest tests/ -q`" in prompt
    assert prompt.endswith("Message formats the acceptance suite asserts, match them exactly: `f` returns `1`.\n")


def test_a_bare_hidden_basename_is_written_as_a_test_module_under_its_directory() -> None:
    prompt = r1_plan_prompt("### Task 1: X\n\nPut the cases in test_x.py.\n", ["tests/unit/test_x.py"], "")
    assert prompt == "Task 1: X\n\nPut the cases in a test module under tests/unit/.\n"


def test_the_r1_plan_rung_has_no_formats_paragraph_when_the_suite_asserts_none() -> None:
    assert "Message formats" not in r1_plan_prompt(plan_section(PLAN, "### Chunk 1: The x tool"), ["tests/test_x.py"], "")


def test_a_broken_stub_for_a_new_file_is_a_new_file_patch() -> None:
    patch = broken_patch({"tools/x.py": None}, {"tools/x.py": "def f():\n    return None\n"})
    assert patch == (
        "diff --git a/tools/x.py b/tools/x.py\nnew file mode 100644\n--- /dev/null\n+++ b/tools/x.py\n"
        "@@ -0,0 +1,2 @@\n+def f():\n+    return None\n"
    )


def test_a_broken_stub_for_an_existing_file_is_a_unified_diff() -> None:
    patch = broken_patch({"tools/x.py": "a\nb\n"}, {"tools/x.py": "a\n# stub\nb\n"})
    assert patch.startswith("diff --git a/tools/x.py b/tools/x.py\n--- a/tools/x.py\n+++ b/tools/x.py\n@@ ")
    assert "+# stub\n" in patch


def test_a_broken_stub_identical_to_base_is_refused() -> None:
    with pytest.raises(CutError, match="identical to BASE"):
        broken_patch({"tools/x.py": "a\n"}, {"tools/x.py": "a\n"})


def test_the_manifest_pins_the_rung_the_provenance_and_both_digests(tmp_path: Path) -> None:
    spec = load_spec(_spec(tmp_path, oracle_env={"PYTHONPATH": "src"}))
    body = manifest_body(spec, "prompt\n", ["test_x.py::test_f"], "d" * 64)
    assert body["contract"] == "prompt\n" and body["contracts"] == {RUNG: "prompt\n"}
    assert body["oracle"] == ["env", "PYTHONPATH=src", "python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"]
    assert body["source_paths"] == ["tools/x.py", "tests"]
    assert body["ignored_paths"] == list(IGNORED_PATHS) == ["PROVENANCE.md"]
    assert body["provenance"] == {"repo": "https://github.com/pauleveritt/satyrn-evals.git", "base_sha": SHA_A, "fix_sha": SHA_B}
    assert body["digests"] == {"task_tree": "d" * 64, "prompt": contract_digest("prompt\n")}


def test_collected_ids_stop_at_the_summary_and_none_is_refused() -> None:
    assert parse_collected("test_x.py::test_f\ntest_x.py::test_g[a]\n\n2 tests collected in 0.01s\n") == [
        "test_x.py::test_f", "test_x.py::test_g[a]"]
    with pytest.raises(CutError, match="collected no tests"):
        parse_collected("\nno tests ran\n")
