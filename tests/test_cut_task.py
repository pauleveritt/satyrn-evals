"""The generator's pure core: spec, exclusions, residue, the R1-plan rung, the broken patch, the manifest."""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt import contract_digest
from tools.cut_task import (
    IGNORED_PATHS,
    RUNG,
    CutError,
    PromptEdit,
    apply_prompt_edits,
    broken_patch,
    excluded,
    excluded_evidence_validity_paths,
    load_spec,
    manifest_body,
    parse_collected,
    plan_section,
    r1_plan_prompt,
    residue_gitignore,
)

SPECS = Path(__file__).resolve().parent.parent / "tools" / "task_specs"
SPEC_PATH = SPECS / "selfhost-run-record-gate.json"
SHA_A, SHA_B = "a" * 40, "b" * 40
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


@pytest.fixture
def spec_body() -> dict:
    """A minimal valid spec dict; a test copies it and overlays one key."""
    return {
        "name": "t", "base": SHA_A, "good": SHA_B, "files": ["tools/x.py"], "hidden": ["tests/test_x.py"],
        "plan": {"path": "docs/plan.md", "heading": "### Task 1: X", "commit": SHA_A},
        "formats": "", "broken": {"tools/x.py": "def f():\n    return None\n"}, "oracle_env": {},
    }


def _spec(tmp_path: Path, spec_body: dict, **over: object) -> Path:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps({**spec_body, **over}))
    return path


def test_a_complete_spec_loads(tmp_path: Path, spec_body: dict) -> None:
    spec = load_spec(_spec(tmp_path, spec_body))
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
def test_a_malformed_spec_is_refused(tmp_path: Path, spec_body: dict, over: dict[str, object], message: str) -> None:
    with pytest.raises(CutError, match=message):
        load_spec(_spec(tmp_path, spec_body, **over))


def test_every_committed_spec_loads() -> None:
    names = sorted(load_spec(path).name for path in SPECS.glob("*.json"))
    assert names == [
        "selfhost-cell-loop", "selfhost-docs-linter", "selfhost-guard-prefixes", "selfhost-preflight-quiet",
        "selfhost-review-script", "selfhost-run-record-gate", "selfhost-speed-probe",
    ]


@pytest.mark.parametrize(
    "path",
    ["docs/superpowers/plans/p.md", "docs/superpowers/specs/s.md", ".claude/settings.json", ".github/w.yml", "PROVENANCE.md", "tests/test_x.py"],
)
def test_the_answer_bearing_paths_stay_out_of_the_base(path: str) -> None:
    assert excluded(path, ["tests/test_x.py"], "t")


@pytest.mark.parametrize(
    "path",
    [
        "docs/lessons.md", "tests/test_other.py", "tools/x.py", "docs/superpowers/research/r.md",
        "evidence/x/validity.md", "evidence/x/invalidity/y.diff",
    ],
)
def test_everything_else_stays_in_the_base(path: str) -> None:
    """The two evidence-shaped additions discriminate a path *segment* named
    ``validity`` from a mere substring: ``validity.md`` and ``invalidity``
    each contain the substring but neither has a ``validity`` segment, so
    both must be kept (M1) -- the pre-existing negative case
    (``evidence/2026-09-16-census/README.md``) lacked the substring
    entirely and could not tell the two apart."""
    assert not excluded(path, ["tests/test_x.py"], "t")


def test_a_tasks_own_cut_tree_stays_out_of_its_own_base() -> None:
    """Ruling R2-8: a task never ships its own cut tree in its own base -- a
    re-cut whose base already contains a prior committed cut would otherwise
    leak the overlay suite, the known-good patch and the manifest verbatim."""
    assert excluded("src/satyrn_evals/tasks/t/manifest.json", [], "t")
    assert excluded("src/satyrn_evals/tasks/t/fixtures/known-good.patch", [], "t")
    assert excluded("src/satyrn_evals/tasks/t/overlay/test_x.py", [], "t")


def test_another_tasks_cut_tree_stays_in_the_base() -> None:
    """The sibling: cutting `t` must not blind a cell to an unrelated task's
    already-committed tree."""
    assert not excluded("src/satyrn_evals/tasks/other/manifest.json", [], "t")


def test_a_tasks_own_cut_spec_stays_out_of_its_own_base() -> None:
    """Ruling R2-8: nor does a task ship its own cut spec, whose `formats`
    states every literal the acceptance suite matches."""
    assert excluded("tools/task_specs/t.json", [], "t")


def test_another_tasks_cut_spec_stays_in_the_base() -> None:
    assert not excluded("tools/task_specs/other.json", [], "t")


def test_a_validity_records_solution_stays_out_of_every_base() -> None:
    """Ruling R2-8: a validity `solution.diff` is by definition a complete
    solution to some census task, so the exclusion is global, not scoped to
    the task being cut."""
    assert excluded("evidence/2026-09-17-census-2/validity/anything/solution.diff", [], "t")


def test_evidence_without_a_validity_segment_stays_in_the_base() -> None:
    assert not excluded("evidence/2026-09-16-census/README.md", [], "t")


def test_a_validity_path_outside_evidence_stays_in_the_base() -> None:
    """The exclusion is scoped to `evidence/`; a same-named directory
    elsewhere in the tree is not a validity record and carries no answer."""
    assert not excluded("src/satyrn_evals/validity/x.py", [], "t")


def test_evidence_validity_exclusions_counts_only_matching_paths() -> None:
    """M5: the ``cut`` CLI's diagnostic is backed by a pure helper, testable
    without a git repository, so the count it reports cannot drift from
    ``excluded()``'s own final clause."""
    paths = [
        "evidence/2026-09-16-census/validity/a/solution.diff",
        "evidence/2026-09-16-census/validity/b/REPORT.md",
        "evidence/2026-09-16-census/README.md",
        "evidence/x/validity.md",
        "src/satyrn_evals/validity/z.py",
        "tools/x.py",
    ]
    assert excluded_evidence_validity_paths(paths) == (
        "evidence/2026-09-16-census/validity/a/solution.diff",
        "evidence/2026-09-16-census/validity/b/REPORT.md",
    )


def test_evidence_validity_exclusions_is_empty_when_nothing_matches() -> None:
    assert excluded_evidence_validity_paths(["tools/x.py", "evidence/README.md", "evidence/x/validity.md"]) == ()


def test_excluded_and_its_helper_agree_on_the_evidence_validity_clause() -> None:
    """M4: `excluded()`'s final clause and `excluded_evidence_validity_paths()`
    are now one function (`_evidence_validity_excluded`) called from both
    sites, so they cannot drift -- pinned here over a set of paths chosen to
    exercise the clause's edges: nested under `validity/`, a `validity.md`
    file (no `validity` path segment), a sibling `invalidity/` directory
    (substring but not a path segment), and a plain `evidence/` path."""
    paths = (
        "evidence/x/validity/y.diff",
        "evidence/x/validity.md",
        "evidence/x/invalidity/y",
        "src/satyrn_evals/validity/z.py",
        "evidence/x/README.md",
    )
    for path in paths:
        assert excluded(path, [], "t") == (path in excluded_evidence_validity_paths(paths))


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


def test_the_manifest_pins_the_rung_the_provenance_and_both_digests(tmp_path: Path, spec_body: dict) -> None:
    spec = load_spec(_spec(tmp_path, spec_body, oracle_env={"PYTHONPATH": "src"}))
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


EDITS = (
    PromptEdit(old="Gate rules:", new="Validation rules enforced by load_run_record:", reason="r1"),
    PromptEdit(old="enforced by load_run_record", new="enforced by load_run_record and re-checked by gate", reason="r2"),
)


def test_edits_apply_in_order_and_may_depend_on_an_earlier_one() -> None:
    assert apply_prompt_edits("Gate rules: a\n", EDITS) == (
        "Validation rules enforced by load_run_record and re-checked by gate: a\n"
    )


def test_an_old_string_that_is_absent_is_refused() -> None:
    with pytest.raises(CutError, match="occurs 0 times"):
        apply_prompt_edits("nothing here\n", EDITS[:1])


def test_an_old_string_that_occurs_twice_is_refused() -> None:
    with pytest.raises(CutError, match="occurs 2 times"):
        apply_prompt_edits("Gate rules: a\nGate rules: b\n", EDITS[:1])


def test_a_new_string_containing_its_own_old_string_is_refused_at_load(tmp_path: Path, spec_body: dict) -> None:
    """Ruling 5: qualification decides `new` present / `old` absent; an edit
    whose replacement re-introduces its own anchor makes that undecidable."""
    body = spec_body | {"prompt_edits": [{"old": "Gate rules", "new": "Gate rules, restated", "reason": "r"}]}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(body))
    with pytest.raises(CutError, match="must not contain its own old text"):
        load_spec(path)


@pytest.mark.parametrize(
    "edit",
    [
        {"old": "", "new": "x", "reason": "r"},
        {"old": "a", "new": "", "reason": "r"},
        {"old": "a", "new": "b", "reason": ""},
        {"old": "a", "new": "b"},
        {"old": "a", "new": "b", "reason": "r", "extra": 1},
    ],
)
def test_a_malformed_edit_is_refused_at_load(tmp_path: Path, spec_body: dict, edit: dict) -> None:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec_body | {"prompt_edits": [edit]}))
    with pytest.raises(CutError, match="prompt_edits"):
        load_spec(path)


def test_a_spec_without_prompt_edits_still_loads_and_writes_no_manifest_key(tmp_path: Path, spec_body: dict) -> None:
    """The compatibility direction: every already-cut task must re-cut byte-identically."""
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec_body))
    spec = load_spec(path)
    assert spec.prompt_edits == ()
    body = manifest_body(spec, "prompt\n", ["tests/test_x.py::test_y"], "0" * 64)
    assert "prompt_edits" not in body["generator"]


def test_recorded_edits_land_in_the_generator_block(tmp_path: Path, spec_body: dict) -> None:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec_body | {"prompt_edits": [{"old": "a", "new": "b", "reason": "r"}]}))
    body = manifest_body(load_spec(path), "b\n", ["tests/test_x.py::test_y"], "0" * 64)
    assert body["generator"]["prompt_edits"] == [{"old": "a", "new": "b", "reason": "r"}]


def test_a_spec_may_carry_an_authored_disclosure(tmp_path: Path) -> None:
    """Design section 5: an authored task discloses itself in the manifest's
    generator block, inside the body `check` compares -- not as a post-cut
    annotation anyone may edit."""
    body = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    body["authored"] = {"spec": "docs/superpowers/specs/x.md", "roles": {"heading": "Opus"}}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    spec = load_spec(path)
    from tools.cut_task import Authored

    assert spec.authored == Authored(spec="docs/superpowers/specs/x.md", roles={"heading": "Opus"})
    generator = manifest_body(spec, "prompt", ["a::b"], "digest")["generator"]
    assert generator["authored"] is True
    assert generator["authoring"] == {
        "spec": "docs/superpowers/specs/x.md", "roles": {"heading": "Opus"}
    }


def test_a_cut_spec_without_the_key_carries_no_disclosure(tmp_path: Path) -> None:
    """The sibling: the six cut tasks must re-cut byte-identically, so the key is
    optional and absent means absent -- never `authored: false`."""
    spec = load_spec(SPEC_PATH)
    assert spec.authored is None
    generator = manifest_body(spec, "prompt", ["a::b"], "digest")["generator"]
    assert "authored" not in generator
    assert "authoring" not in generator


@pytest.mark.parametrize(
    "value",
    [
        {"spec": "", "roles": {"heading": "Opus"}},
        {"spec": "docs/x.md", "roles": {}},
        {"spec": "docs/x.md", "roles": {"heading": ""}},
        {"spec": "docs/x.md"},
        {"spec": "docs/x.md", "roles": {"heading": "Opus"}, "extra": "no"},
        "yes",
        {"spec": "   ", "roles": {"heading": "Opus"}},
        {"spec": "docs/x.md", "roles": {" ": "Opus"}},
        {"spec": "docs/x.md", "roles": {"heading": "   "}},
    ],
)
def test_a_malformed_authored_block_is_refused(tmp_path: Path, value: object) -> None:
    body = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    body["authored"] = value
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(CutError):
        load_spec(path)


def test_check_ignores_a_post_cut_validity_annotation(tmp_path: Path) -> None:
    """A cut task annotated with `validity` still matches a fresh cut."""
    from tools.cut_task import comparable

    committed = tmp_path / "task"
    (committed / "base").mkdir(parents=True)
    (committed / "base" / "app.py").write_text("x = 1\n")
    body = {"name": "t", "contract": "c"}
    (committed / "manifest.json").write_text(json.dumps(body))
    before = comparable(committed)
    (committed / "manifest.json").write_text(json.dumps(body | {"validity": {"by": "s", "commit": "a" * 40, "passed": True}}))
    assert comparable(committed) == before


def test_check_still_sees_any_other_manifest_change(tmp_path: Path) -> None:
    from tools.cut_task import comparable

    committed = tmp_path / "task"
    (committed / "base").mkdir(parents=True)
    (committed / "base" / "app.py").write_text("x = 1\n")
    (committed / "manifest.json").write_text(json.dumps({"name": "t", "contract": "c"}))
    before = comparable(committed)
    (committed / "manifest.json").write_text(json.dumps({"name": "t", "contract": "d"}))
    assert comparable(committed) != before
