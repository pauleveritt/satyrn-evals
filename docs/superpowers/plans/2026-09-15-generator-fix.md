# Phase 2b.1 — The self-hosted generator fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-15 at the maintainer's request ("Plan the generator fix and rerun the self-hosted admissions"); he delegated the two design choices, taken below as Rulings 1 and 2.** Planned against evals `release-one` at `2b04227` (Phase 2c done; the 2026-09-14 admission records and results under `records/`). Every test below was run before hand-back (see "Test verification"). Two tasks, about an hour.

**Goal:** The four self-hosted tasks measure the work they name: a model that follows the base's `AGENTS.md` and writes `PROVENANCE.md` keeps its verdict, and the R1-plan prompt names a real directory for the model's own tests instead of "its test module"; then the operator reruns the four self-hosted admission records.

**Architecture:** Task 1 is grading: the manifest gains an optional, validated `ignored_paths`; `patch.drop_ignored` removes a patch's sections that touch only those files; `grade` drops them before the allowlist and the apply and the receipt lists them. Task 2 is the generator and qualification: `tools/cut_task.py` writes `ignored_paths: ["PROVENANCE.md"]` and replaces a hidden path with its directory; `qualify` gains an `r1-plan-prompt` check and its fake attempt also writes `PROVENANCE.md` on generated tasks; the four self-hosted tasks are re-cut (only their `manifest.json` files change) and all six candidates re-qualify.

**Tech Stack:** Python 3.14, uv, pytest (default tier: audit-hook spawn tripwire; `integration` marker), ruff, just, git.

**Spec:** `docs/superpowers/specs/2026-09-13-release-one-design.md` — "The self-hosted generator" (base contents, manifest, qualification), "Rungs" (R1-plan), "Process" (docs caps; plans tested up front). Contract: Phase 2b plan `docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md` and its ledger `.superpowers/sdd/2026-09-14-phase-2b-isolation-and-tasks/progress.md` (R8; Ruling 12, which this plan amends). Evidence: `~/satyrn-runs/2026-09-14-admission-selfhost-review-script/baseline/*/patch.diff` and `receipt.json` (all four: `patch touches non-source path: PROVENANCE.md`; two created `its/test_review.py` and `tests/its.py`). House style: the 2b and 2c plans.

## Rulings

1. **`PROVENANCE.md` is ignored by grading, not restored to the base.** The manifest gains `ignored_paths` (repo-relative files; default empty; each a safe relative POSIX path, distinct, and outside `source_paths`). The generator sets `["PROVENANCE.md"]` on every self-hosted task. `grade` drops every `diff --git` section whose paths are all ignored before the allowlist and before `git apply`, and the receipt carries `ignored_paths` when anything was dropped. The patch digest and the contamination scan still read the patch as harvested. A section that renames an ignored file into a source path stays whole, so the allowlist still judges it. A patch of nothing but ignored sections grades BASE (a fail, not `unavailable`). The base stays as the spec defines it (no `PROVENANCE.md`; `AGENTS.md` unchanged): editing the repository's conventions out would make the task less like real work. Both arms are graded by the same rule. Cost if wrong: a model spends turns on provenance rows that do not count.
2. **A hidden path is written as its directory.** `tests/test_review.py` becomes `tests/`; a bare hidden basename becomes `a test module under tests/`. So the prompts read "Create: `tools/review.py`, `tests/`" and "`uv run pytest tests/ -q`". The spec loader refuses a hidden file with no directory (all four specs have one). The prompt never names the hidden file and always names a real directory. Cost if wrong: the model writes its own tests elsewhere under `tests/`, and `uv run pytest tests/ -q` runs BASE's whole `tests/` (more wall time per run); the overlay still decides.
3. **The Engine arm's writable paths are not widened.** `writable_paths` still derives from `source_paths` alone, so under Satyrn a `PROVENANCE.md` write is refused while bare Pi's is dropped at grading. The grading rule is the same for both arms. Widening the declared scope would change the Engine contract digests of all four tasks and the declared-against-enforced check, and release-one's pending work is Baseline admission. Cost if wrong: an Engine cell spends a turn on a refused write; a later plan widens `writable_paths` by `ignored_paths` if Phase 4 shows it.
4. **The qualification checks that would have caught both defects.** (a) On a task cut by the generator (its manifest has a `generator` block), the live-harvest fake applies known-good plus a new `PROVENANCE.md`. It passes only when the harvest holds both, the verdict is pass, and the receipt lists `PROVENANCE.md` as ignored. Against the committed 2026-09-14 manifests it fails all four with `verdict unavailable`. (b) `r1-plan-prompt`: the R1-plan text must not contain the retired stand-in "its test module". Every path named in its `- Create:`/`- Modify:`/`- Test:` lines, and every argument of a backticked `uv run pytest` command, must be a `source_paths` entry, a file in `base/`, or a directory in `base/` written with a trailing slash. Base files are admitted because run-record-gate's plan runs `tests/test_cli.py`, which BASE has. Prose paths such as `/tmp/rec.json` are not judged. Against the committed manifests it fails run-record-gate, review-script and docs-linter. Tasks without an R1-plan rung pass it vacuously, so every task reports six checks. Cost if wrong: a path in prose outside those lines could still point nowhere; the check targets the lines the defect lived in.
5. **The re-cut changes only the four `manifest.json` files.** `base/`, `overlay/` and the fixtures are byte-identical, so each `digests.task_tree` is unchanged. `contract`, `contracts["R1-plan"]` and `digests.prompt` change for three tasks; guard-prefixes' prompt named no hidden file and gains only `ignored_paths`. 2b R8 holds: run-record-gate's `formats` text comes from its unchanged spec. The AgentClinic task directories are untouched. The 2026-09-14 self-hosted admission results stay committed and unedited; the Phase 3 reading marks them superseded by the 2026-09-15 records.
6. **The spec's generator paragraph gains the two rules and the new check** (+5 lines; the spec is 399 lines against its 400 cap; `just lint-docs` exit 0).

## Global Constraints

- **Roles: Sonnet implements, Opus reviews each task, Sonnet re-reviews a fix diff (scoped). No haiku. No Fable.** One fresh implementer per task; one Opus review per task before the next starts.
- **The controller blocks on every dispatch; nothing runs in the background.**
- **No inference.** No `launch` of a real model, no `pi -p`, no request to oMLX. The rerun commands at the end are the operator's, not the controller's.
- **Default test tier: no subprocess, no network, no model** (the audit hook in `tests/conftest.py`). Anything that spawns is `@pytest.mark.integration`.
- **Every refusal test has a sibling success test**; every detector has a firing row and a silent row.
- **Every task ends with `just gates` exit 0** (read the exit code; never pipe a gate). New files get `PROVENANCE.md` rows (`uv run python tools/provenance.py new <paths>`); edited files keep theirs. This plan creates no file. Run `uv run ruff check --fix` before gates.
- **Four integration rows fail on this Mac before any change**: `tests/test_workspace_failures.py::test_prepare_repository_fails_closed_on_verification[*]` (the Xcode license). Reported, never fixed here, never counted against a task.
- **Commit at the end of every task** on evals `release-one`, with the plan's message. Never `--amend`, merge or push. A task whose gates are red is not committed.
- **Evals tree only.** The engine is read, never edited.
- **Nothing is written to `/tmp` or `/private/tmp`** except under the session scratchpad `$SCR` (`/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/genfix-exec/`). Integration runs pass `--basetemp "$SCR/bt"` and remove it right after.
- **No test copies a bundled hidden task into pytest's temp directory.** Default-tier rows read bundled trees in place.
- **Docs caps stand:** spec ≤ 400 lines, `ROADMAP.md` ≤ 150; `just lint-docs` exit 0.
- **Starting point:** evals `release-one` at `2b04227` plus this plan's commit. The diff blocks below apply with `git apply` from the repository root; if one does not apply, apply it by hand to the same effect and say so in the task report.

---

## File structure

```
src/satyrn_evals/manifest.py      # TaskManifest.ignored_paths; _validate_ignored_paths                      (modify, T1)
src/satyrn_evals/patch.py         # drop_ignored                                                              (modify, T1)
src/satyrn_evals/receipt.py       # Receipt.ignored_paths, written when non-empty                            (modify, T1)
src/satyrn_evals/grade.py         # drop before allowlist and apply; empty remainder grades BASE             (modify, T1)
tests/test_patch.py, tests/test_manifest.py, tests/test_receipt.py, tests/integration/test_grade.py        (modify, T1)
tools/cut_task.py                 # IGNORED_PATHS; hidden_directory; hidden files need a directory           (modify, T2)
src/satyrn_evals/qualify.py       # SELF_HOSTED_CONVENTION_FILES; judge_prompt; harvest writes PROVENANCE.md (modify, T2)
src/satyrn_evals/tasks/selfhost-{run-record-gate,guard-prefixes,review-script,docs-linter}/manifest.json   (re-cut, T2)
tests/test_cut_task.py, tests/test_qualify.py, tests/integration/test_qualify.py                           (modify, T2)
docs/superpowers/specs/2026-09-13-release-one-design.md   # generator paragraph                             (modify, T2)
```

---

### Task 1: Grading drops a manifest's ignored paths and lists them

**Files:**
- Modify: `src/satyrn_evals/patch.py` (append `drop_ignored`), `src/satyrn_evals/manifest.py` (import; `TaskManifest.ignored_paths`; `_validate_ignored_paths`; loader), `src/satyrn_evals/receipt.py` (field; `write_receipt`), `src/satyrn_evals/grade.py` (import; `grade`; `_apply_patch`)
- Test: `tests/test_patch.py`, `tests/test_manifest.py`, `tests/test_receipt.py` (appended rows, one import), `tests/integration/test_grade.py` (three rows)

**Interfaces:**
- Consumes: `patch.parse_patch_paths`, `patch.within_source`, `patch.check_allowlist`; `grade.grade`, `grade._apply_patch`; `receipt.Receipt`, `receipt.write_receipt`.
- Produces: `patch.drop_ignored(patch_text: str, ignored: tuple[str, ...]) -> tuple[str, tuple[str, ...]]` (remaining text, dropped paths sorted; unchanged and unparsed when `ignored` is empty); `TaskManifest.ignored_paths: tuple[str, ...] = ()` (manifest key `ignored_paths`, a JSON list; `ManifestError` for a non-list, an empty or unsafe entry, a repeat, or an entry inside `source_paths`); `Receipt.ignored_paths: tuple[str, ...] = ()` (receipt JSON key `ignored_paths`, a list, present only when non-empty). `grade` behaviour: ignored sections never reach `check_allowlist` or `git apply`; a remainder with no sections grades BASE.

- [ ] **Step 1: Write the failing tests.** Save this block as `$SCR/t1-tests.diff` and run `git apply "$SCR/t1-tests.diff"`:

```diff
diff --git a/tests/integration/test_grade.py b/tests/integration/test_grade.py
index 4c77cf5..8aea984 100644
--- a/tests/integration/test_grade.py
+++ b/tests/integration/test_grade.py
@@ -211,6 +211,48 @@ def test_patch_touching_tests_records_unavailable(tmp_task: Path, tmp_path: Path
     assert "non-source" in data["reason"]


+PROVENANCE_SECTION = (
+    "diff --git a/PROVENANCE.md b/PROVENANCE.md\n"
+    "new file mode 100644\n"
+    "--- /dev/null\n"
+    "+++ b/PROVENANCE.md\n"
+    "@@ -0,0 +1 @@\n"
+    "+| solution.py | created |\n"
+)
+
+
+def _ignore_provenance(task_dir: Path) -> None:
+    manifest_path = task_dir / "manifest.json"
+    data = json.loads(manifest_path.read_text())
+    data["ignored_paths"] = ["PROVENANCE.md"]
+    manifest_path.write_text(json.dumps(data))
+
+
+def test_an_ignored_path_is_dropped_and_listed_and_the_rest_grades(tmp_task: Path, tmp_path: Path) -> None:
+    _ignore_provenance(tmp_task)
+    patch = tmp_path / "with-provenance.patch"
+    patch.write_text(PROVENANCE_SECTION + GOOD_PATCH)
+    receipt_path = tmp_path / "r.json"
+    receipt = grade(tmp_task, patch, receipt_path)
+    assert receipt.verdict is Verdict.PASS
+    assert json.loads(receipt_path.read_text())["ignored_paths"] == ["PROVENANCE.md"]
+
+
+def test_a_patch_of_only_ignored_paths_grades_the_base(tmp_task: Path, tmp_path: Path) -> None:
+    _ignore_provenance(tmp_task)
+    patch = tmp_path / "only-provenance.patch"
+    patch.write_text(PROVENANCE_SECTION)
+    receipt = grade(tmp_task, patch, tmp_path / "r.json")
+    assert (receipt.verdict, receipt.ignored_paths) == (Verdict.FAIL, ("PROVENANCE.md",))
+
+
+def test_an_undeclared_provenance_file_still_makes_the_verdict_unavailable(tmp_task: Path, tmp_path: Path) -> None:
+    patch = tmp_path / "with-provenance.patch"
+    patch.write_text(PROVENANCE_SECTION + GOOD_PATCH)
+    receipt = grade(tmp_task, patch, tmp_path / "r.json")
+    assert (receipt.verdict, receipt.reason) == (Verdict.UNAVAILABLE, "patch touches non-source path: PROVENANCE.md")
+
+
 def test_unreadable_patch_is_a_usage_error(tmp_task: Path, tmp_path: Path) -> None:
     with pytest.raises(PatchReadError, match="cannot read patch"):
         grade(tmp_task, tmp_path / "missing.patch", tmp_path / "r.json")
diff --git a/tests/test_manifest.py b/tests/test_manifest.py
index 49af59a..996eb6e 100644
--- a/tests/test_manifest.py
+++ b/tests/test_manifest.py
@@ -659,3 +659,36 @@ def test_a_malformed_public_suite_is_refused(tmp_path: Path, bad: object) -> Non

     with pytest.raises(ManifestError, match="public_suite must be a non-empty list"):
         load_manifest(task)
+
+
+def _task_with_ignored(tmp_path: Path, ignored: object) -> Path:
+    task = _valid_task(tmp_path)
+    data = json.loads((task / "manifest.json").read_text())
+    data["ignored_paths"] = ignored
+    (task / "manifest.json").write_text(json.dumps(data))
+    return task
+
+
+def test_a_manifest_without_ignored_paths_ignores_nothing(tmp_path: Path) -> None:
+    assert load_manifest(_valid_task(tmp_path)).ignored_paths == ()
+
+
+def test_declared_ignored_paths_load_in_order(tmp_path: Path) -> None:
+    task = _task_with_ignored(tmp_path, ["PROVENANCE.md", "docs/notes.md"])
+    assert load_manifest(task).ignored_paths == ("PROVENANCE.md", "docs/notes.md")
+
+
+@pytest.mark.parametrize(
+    ("ignored", "message"),
+    [
+        ("PROVENANCE.md", "must be a list of non-empty strings"),
+        ([""], "must be a list of non-empty strings"),
+        (["/PROVENANCE.md"], "safe relative POSIX path"),
+        (["docs/../PROVENANCE.md"], "safe relative POSIX path"),
+        (["PROVENANCE.md", "PROVENANCE.md"], "repeats entry"),
+        (["solution.py"], "inside source_paths"),
+    ],
+)
+def test_malformed_ignored_paths_are_refused(tmp_path: Path, ignored: object, message: str) -> None:
+    with pytest.raises(ManifestError, match=message):
+        load_manifest(_task_with_ignored(tmp_path, ignored))
diff --git a/tests/test_patch.py b/tests/test_patch.py
index cea003a..e638a57 100644
--- a/tests/test_patch.py
+++ b/tests/test_patch.py
@@ -1,7 +1,7 @@
 import pytest

 from satyrn_evals.errors import PatchParseError, PatchRejected
-from satyrn_evals.patch import check_allowlist, parse_patch_paths
+from satyrn_evals.patch import check_allowlist, drop_ignored, parse_patch_paths

 GOOD = (
     "diff --git a/solution.py b/solution.py\n"
@@ -263,3 +263,37 @@ def test_check_allowlist_directory_entry_accepts_children() -> None:
                     ("src/textkit",))  # must not raise
     with pytest.raises(PatchRejected, match="non-source"):
         check_allowlist(("tests/test_slugify.py",), ("src/textkit",))
+
+
+PROVENANCE_SECTION = (
+    "diff --git a/PROVENANCE.md b/PROVENANCE.md\n"
+    "new file mode 100644\n"
+    "--- /dev/null\n"
+    "+++ b/PROVENANCE.md\n"
+    "@@ -0,0 +1 @@\n"
+    "+| solution.py | created |\n"
+)
+
+
+def test_an_ignored_section_is_dropped_and_the_rest_kept_byte_for_byte() -> None:
+    assert drop_ignored(PROVENANCE_SECTION + GOOD, ("PROVENANCE.md",)) == (GOOD, ("PROVENANCE.md",))
+    assert drop_ignored(GOOD + PROVENANCE_SECTION, ("PROVENANCE.md",)) == (GOOD, ("PROVENANCE.md",))
+
+
+def test_nothing_ignored_returns_the_patch_unchanged() -> None:
+    assert drop_ignored(PROVENANCE_SECTION + GOOD, ()) == (PROVENANCE_SECTION + GOOD, ())
+    assert drop_ignored(GOOD, ("PROVENANCE.md",)) == (GOOD, ())
+
+
+def test_a_section_touching_an_ignored_and_another_path_is_kept() -> None:
+    rename = "diff --git a/PROVENANCE.md b/solution.py\nsimilarity index 100%\nrename from PROVENANCE.md\nrename to solution.py\n"
+    assert drop_ignored(rename, ("PROVENANCE.md",)) == (rename, ())
+
+
+def test_a_patch_of_only_ignored_sections_leaves_nothing() -> None:
+    assert drop_ignored(PROVENANCE_SECTION, ("PROVENANCE.md",)) == ("", ("PROVENANCE.md",))
+
+
+def test_hunk_text_that_looks_like_a_diff_header_does_not_split_a_section() -> None:
+    added = GOOD.replace("+    return n * 2\n", "+    return n * 2\n+diff --git a/PROVENANCE.md b/PROVENANCE.md\n")
+    assert drop_ignored(added, ("PROVENANCE.md",)) == (added, ())
diff --git a/tests/test_receipt.py b/tests/test_receipt.py
index 4c3b4c9..396b3b7 100644
--- a/tests/test_receipt.py
+++ b/tests/test_receipt.py
@@ -106,3 +106,15 @@ def test_receipt_serializes_resolved_versions_when_present(tmp_path) -> None:
     write_receipt(path, receipt)
     data = json.loads(path.read_text())
     assert data["resolved_versions"] == {"fastapi": "0.115.10"}
+
+
+def test_receipt_omits_ignored_paths_when_none_were_dropped(tmp_path) -> None:
+    path = tmp_path / "receipt.json"
+    write_receipt(path, Receipt("t", "d", Verdict.PASS, "ok", None))
+    assert "ignored_paths" not in json.loads(path.read_text())
+
+
+def test_receipt_lists_the_ignored_paths_it_dropped(tmp_path) -> None:
+    path = tmp_path / "receipt.json"
+    write_receipt(path, Receipt("t", "d", Verdict.PASS, "ok", None, ignored_paths=("PROVENANCE.md",)))
+    assert json.loads(path.read_text())["ignored_paths"] == ["PROVENANCE.md"]
```

- [ ] **Step 2: Run them to verify they fail.**

Run: `uv run pytest -q tests/test_patch.py tests/test_manifest.py tests/test_receipt.py`
Expected: collection error in `tests/test_patch.py`, `ImportError: cannot import name 'drop_ignored'`. Then `uv run pytest -q tests/test_manifest.py tests/test_receipt.py` → `9 failed, 93 passed` (the ignored-paths refusals and loads, and `test_receipt_lists_the_ignored_paths_it_dropped`). Then `uv run pytest -m integration -q --basetemp "$SCR/bt" tests/integration/test_grade.py; rm -rf "$SCR/bt"` → `2 failed, 18 passed` (the dropped-and-listed and only-ignored rows; the undeclared row already passes).

- [ ] **Step 3: Implement.** Save as `$SCR/t1-src.diff` and run `git apply "$SCR/t1-src.diff"`:

```diff
diff --git a/src/satyrn_evals/grade.py b/src/satyrn_evals/grade.py
index 943d5fa..f56cb24 100644
--- a/src/satyrn_evals/grade.py
+++ b/src/satyrn_evals/grade.py
@@ -24,7 +24,7 @@ from satyrn_evals.errors import (
 )
 from satyrn_evals.manifest import TaskManifest, load_manifest
 from satyrn_evals.overlay import OverlaySpec, load_overlay, materialize_overlay
-from satyrn_evals.patch import check_allowlist, parse_patch_paths
+from satyrn_evals.patch import check_allowlist, drop_ignored, parse_patch_paths
 from satyrn_evals.receipt import Receipt, patch_digest, write_receipt
 from satyrn_evals.taskenv import has_locked_project, parse_freeze
 from satyrn_evals.verdict import (
@@ -158,14 +158,18 @@ def grade(
     evidence: HookResultData | None = None
     reason = ""
     resolved_versions: dict[str, str] | None = None
+    # The manifest's ignored files leave the patch before the allowlist and
+    # the apply; the receipt lists them. Digest and contamination scan still
+    # read the patch as harvested.
+    graded_text, ignored = drop_ignored(patch_text, manifest.ignored_paths)
     try:
-        paths = parse_patch_paths(patch_text)
+        paths = parse_patch_paths(graded_text) if graded_text.strip() or not ignored else ()
         if enforce_allowlist:
             check_allowlist(paths, manifest.source_paths)
         hook, resolved_versions = _run_oracle(
             manifest,
             task_dir,
-            patch_text,
+            graded_text,
             overlay=overlay,
             selectors=selectors,
             workspace_parent=receipt_path.parent,
@@ -225,6 +229,7 @@ def grade(
         evidence=evidence,
         contamination=contamination,
         resolved_versions=resolved_versions,
+        ignored_paths=ignored,
     )
     if deadline is not None:
         deadline.remaining(DeadlinePhase.GRADING)
@@ -302,6 +307,8 @@ def _apply_patch(
         raise
     except (OSError, subprocess.CalledProcessError) as e:
         raise ApplyError(f"cannot run git: {e}") from e
+    if not patch_text.strip():
+        return  # every section was an ignored path: the oracle grades BASE
     applied = _run_grading_subprocess(
         ["git", *GIT_SAFETY_CONFIG, "apply", "-"],
         input=os.fsencode(patch_text),
diff --git a/src/satyrn_evals/manifest.py b/src/satyrn_evals/manifest.py
index a14b4ea..1db507a 100644
--- a/src/satyrn_evals/manifest.py
+++ b/src/satyrn_evals/manifest.py
@@ -8,6 +8,7 @@ from pathlib import Path
 from typing import Literal

 from satyrn_evals.errors import ManifestError
+from satyrn_evals.patch import within_source

 #: The oracle hook plugin name. A public suite naming it would run the
 #: hidden grader through the executor's own process.
@@ -55,6 +56,12 @@ class TaskManifest:
     #: task has no directory entries, and the renderer refuses it against a
     #: tree that holds one. HP4.
     source_dirs: tuple[str, ...] | None = None
+    #: Repository files a patch may touch that grading drops before the
+    #: allowlist and the apply, listing them on the receipt. A self-hosted
+    #: base keeps ``AGENTS.md``, which requires a ``PROVENANCE.md`` row for
+    #: every file, while the generator strips ``PROVENANCE.md``; a model that
+    #: follows the repository's conventions must not lose its verdict for it.
+    ignored_paths: tuple[str, ...] = ()


 def _validate_source_dirs(
@@ -88,6 +95,34 @@ def _validate_source_dirs(
     return declared


+def _validate_ignored_paths(
+    value: object, source_paths: tuple[str, ...]
+) -> tuple[str, ...]:
+    """Validate the optional ignored files: safe, distinct, outside ``source_paths``.
+
+    An ignored path inside ``source_paths`` is refused: grading would drop
+    the very work the task asks for.
+    """
+    match value:
+        case None:
+            return ()
+        case list() if all(isinstance(entry, str) and entry for entry in value):
+            declared = tuple(value)
+        case _:
+            raise ManifestError("ignored_paths must be a list of non-empty strings")
+    for entry in declared:
+        parts = entry.split("/")
+        if entry.startswith("/") or "\\" in entry or "\0" in entry or any(
+            part in ("", ".", "..") for part in parts
+        ):
+            raise ManifestError(f"ignored_paths entry must be a safe relative POSIX path: {entry!r}")
+        if declared.count(entry) > 1:
+            raise ManifestError(f"ignored_paths repeats entry: {entry}")
+        if within_source(entry, source_paths):
+            raise ManifestError(f"ignored_paths names {entry!r}, which is inside source_paths")
+    return declared
+
+
 def _validate_public_suite(value: object, grader_overlay: str | None) -> tuple[str, ...]:
     """Validate the optional public suite command, refusing a leak.

@@ -321,6 +356,7 @@ def load_manifest(task_dir: Path) -> TaskManifest:
     grader_overlay = _validate_grader_overlay(task_dir, data.get("grader_overlay"))
     public_suite = _validate_public_suite(data.get("public_suite"), grader_overlay)
     source_dirs = _validate_source_dirs(data.get("source_dirs"), sources)
+    ignored_paths = _validate_ignored_paths(data.get("ignored_paths"), sources)
     visibility_raw = data.get("oracle_visibility", "visible")
     if visibility_raw not in ("visible", "hidden"):
         raise ManifestError(
@@ -352,6 +388,7 @@ def load_manifest(task_dir: Path) -> TaskManifest:
         contracts=contracts,
         public_suite=public_suite,
         source_dirs=source_dirs,
+        ignored_paths=ignored_paths,
     )


diff --git a/src/satyrn_evals/patch.py b/src/satyrn_evals/patch.py
index aacc259..1c7dd13 100644
--- a/src/satyrn_evals/patch.py
+++ b/src/satyrn_evals/patch.py
@@ -182,3 +182,31 @@ def check_allowlist(paths: tuple[str, ...], source_paths: tuple[str, ...]) -> No
     for path in paths:
         if not within_source(path, source_paths):
             raise PatchRejected(f"patch touches non-source path: {path}")
+
+
+def drop_ignored(patch_text: str, ignored: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
+    """Remove every ``diff --git`` section whose paths are all in ``ignored``.
+
+    Returns the remaining patch text and the paths dropped, sorted. A section
+    that also touches any other path stays whole, so the allowlist still
+    judges it; text before the first section is kept. Lines split on ``\\n``
+    only, so the kept sections are the original bytes. With nothing ignored
+    the patch comes back unchanged and unparsed.
+    """
+    if not ignored:
+        return patch_text, ()
+    sections: list[list[str]] = [[]]
+    for line in re.split(r"(?<=\n)", patch_text):
+        if line.startswith("diff --git "):
+            sections.append([])
+        sections[-1].append(line)
+    wanted = set(ignored)
+    kept = list(sections[0])
+    dropped: set[str] = set()
+    for section in sections[1:]:
+        paths = set(parse_patch_paths("".join(section)))
+        if paths <= wanted:
+            dropped |= paths
+        else:
+            kept.extend(section)
+    return "".join(kept), tuple(sorted(dropped))
diff --git a/src/satyrn_evals/receipt.py b/src/satyrn_evals/receipt.py
index 8994fe6..62d0d2e 100644
--- a/src/satyrn_evals/receipt.py
+++ b/src/satyrn_evals/receipt.py
@@ -19,6 +19,9 @@ class Receipt:
     evidence: HookResultData | None
     contamination: dict | None = None
     resolved_versions: dict[str, str] | None = None
+    #: Paths the patch touched that the manifest's ``ignored_paths`` names,
+    #: dropped before the allowlist and the apply. Written only when non-empty.
+    ignored_paths: tuple[str, ...] = ()


 def patch_digest(data: bytes) -> str:
@@ -52,4 +55,8 @@ def write_receipt(path: Path, receipt: Receipt) -> None:
         data.pop("contamination")
     if receipt.resolved_versions is None:
         data.pop("resolved_versions")
+    if not receipt.ignored_paths:
+        data.pop("ignored_paths")
+    else:
+        data["ignored_paths"] = list(receipt.ignored_paths)
     write_json_atomically(path, data)
```

- [ ] **Step 4: Run the tests to verify they pass.**

Run: `uv run pytest -q tests/test_patch.py tests/test_manifest.py tests/test_receipt.py` → `135 passed`.
Run: `uv run pytest -m integration -q --basetemp "$SCR/bt" tests/integration/test_grade.py; echo "EXIT: $?"; rm -rf "$SCR/bt"` → `EXIT: 0` (20 passed).
Run: `uv run ruff check --fix && just gates; echo "EXIT: $?"` → `EXIT: 0` (default tier 2,024 passed).

- [ ] **Step 5: Commit.**

```bash
git add src/satyrn_evals/patch.py src/satyrn_evals/manifest.py src/satyrn_evals/receipt.py src/satyrn_evals/grade.py tests/test_patch.py tests/test_manifest.py tests/test_receipt.py tests/integration/test_grade.py
git commit -m "Phase 2b.1: a manifest's ignored_paths leave the patch before the allowlist and the apply, and the receipt lists them"
```

---

### Task 2: The generator names a real directory and ignores PROVENANCE.md; qualification catches both; the four tasks re-cut

**Files:**
- Modify: `tools/cut_task.py` (docstring; import; `IGNORED_PATHS`; drop `HIDDEN_STAND_IN`; `load_spec`; `r1_plan_prompt`; new `hidden_directory`; `manifest_body`), `src/satyrn_evals/qualify.py` (docstring; imports; constants; `judge_harvest`; new `prompt_paths`, `judge_prompt`, `convention_files_patch`; `qualify`), `docs/superpowers/specs/2026-09-13-release-one-design.md` (generator paragraph)
- Re-cut: `src/satyrn_evals/tasks/selfhost-run-record-gate/`, `selfhost-guard-prefixes/`, `selfhost-review-script/`, `selfhost-docs-linter/` (only `manifest.json` changes)
- Test: `tests/test_cut_task.py`, `tests/test_qualify.py`, `tests/integration/test_qualify.py`

**Interfaces:**
- Consumes (Task 1): `TaskManifest.ignored_paths`; the receipt key `ignored_paths`. Also `manifest.load_manifest`, `DEFAULT_TASKS_ROOT`; `qualify.CEILING_CANDIDATES`, `FLOOR_CANDIDATES`, `judge_harvest`; `tools.cut_task.cut`, `main`, `r1_plan_prompt`, `manifest_body`, `load_spec`.
- Produces: `qualify.PLAN_RUNG = "R1-plan"`, `SELF_HOSTED_CONVENTION_FILES = ("PROVENANCE.md",)`, `RETIRED_STAND_IN = "its test module"`; `judge_harvest(code, verdict, patch_text, known_good, *, extra: tuple[str, ...] = (), dropped: tuple[str, ...] = ()) -> Check`; `prompt_paths(prompt: str) -> list[str]`; `judge_prompt(contracts: dict[str, str], source_paths: tuple[str, ...], base: Path) -> Check` (name `r1-plan-prompt`); `convention_files_patch(paths: tuple[str, ...]) -> str`; `qualify(task_dir)` returns six checks in the order `known-good run 1..3`, `known-broken`, `r1-plan-prompt`, `live-harvest`. `tools.cut_task.IGNORED_PATHS` (is `SELF_HOSTED_CONVENTION_FILES`), `hidden_directory(path: str) -> str` (`"tests/test_x.py"` → `"tests/"`); `HIDDEN_STAND_IN` is removed; manifests carry `"ignored_paths": ["PROVENANCE.md"]` after `source_paths`.

- [ ] **Step 1: Write the failing tests.** Save as `$SCR/t2-tests.diff` and run `git apply "$SCR/t2-tests.diff"`:

```diff
diff --git a/tests/integration/test_qualify.py b/tests/integration/test_qualify.py
index 77d31a1..092e4e5 100644
--- a/tests/integration/test_qualify.py
+++ b/tests/integration/test_qualify.py
@@ -22,7 +22,7 @@ FIXTURE_TASKS = Path(__file__).parent / "data" / "tasks"
 @pytest.mark.parametrize("name", [*CEILING_CANDIDATES, *FLOOR_CANDIDATES])
 def test_every_candidate_qualifies_offline(name: str) -> None:
     checks = qualify(DEFAULT_TASKS_ROOT / name)
-    assert [check.name for check in checks] == ["known-good run 1", "known-good run 2", "known-good run 3", "known-broken", "live-harvest"]
+    assert [check.name for check in checks] == ["known-good run 1", "known-good run 2", "known-good run 3", "known-broken", "r1-plan-prompt", "live-harvest"]
     assert all(check.passed for check in checks), "\n".join(check.line(name) for check in checks)


@@ -36,4 +36,4 @@ def test_a_task_whose_known_broken_fixture_passes_does_not_qualify(tmp_path: Pat

 def test_the_qualify_command_exits_zero_for_a_qualifying_task(capsys: pytest.CaptureFixture[str]) -> None:
     assert main(["qualify", "calc-build", "--tasks-root", str(FIXTURE_TASKS)]) == 0
-    assert capsys.readouterr().out.count(" ok: ") == 5
+    assert capsys.readouterr().out.count(" ok: ") == 6
diff --git a/tests/test_cut_task.py b/tests/test_cut_task.py
index f7200fe..a646c49 100644
--- a/tests/test_cut_task.py
+++ b/tests/test_cut_task.py
@@ -7,7 +7,7 @@ import pytest

 from satyrn_evals.attempt import contract_digest
 from tools.cut_task import (
-    HIDDEN_STAND_IN,
+    IGNORED_PATHS,
     RUNG,
     CutError,
     broken_patch,
@@ -72,6 +72,7 @@ def test_a_complete_spec_loads(tmp_path: Path) -> None:
         ({"broken": {}}, "broken must name at least one file"),
         ({"broken": {"tools/x.py": "no newline"}}, "must end with a newline"),
         ({"hidden": ["tests/a/test_x.py", "tests/b/test_x.py"]}, "basenames must be distinct"),
+        ({"hidden": ["test_x.py"]}, "must sit under a directory"),
         ({"plan": {"path": "p", "heading": "h"}}, "plan must be"),
     ],
 )
@@ -122,10 +123,16 @@ def test_the_r1_plan_rung_keeps_prose_and_produces_and_drops_code_consumes_and_h
     assert prompt.startswith("Chunk 1: The x tool\n\nFiles:\n")
     assert "Produces: `f() -> int`" in prompt
     assert "Consumes" not in prompt and "def test_f" not in prompt and "**" not in prompt and "- [ ]" not in prompt
-    assert "test_x.py" not in prompt and f"`tools/x.py`, `{HIDDEN_STAND_IN}`" in prompt
+    assert "test_x.py" not in prompt and "its test module" not in prompt
+    assert "- Create: `tools/x.py`, `tests/`" in prompt and "`uv run pytest tests/ -q`" in prompt
     assert prompt.endswith("Message formats the acceptance suite asserts, match them exactly: `f` returns `1`.\n")


+def test_a_bare_hidden_basename_is_written_as_a_test_module_under_its_directory() -> None:
+    prompt = r1_plan_prompt("### Task 1: X\n\nPut the cases in test_x.py.\n", ["tests/unit/test_x.py"], "")
+    assert prompt == "Task 1: X\n\nPut the cases in a test module under tests/unit/.\n"
+
+
 def test_the_r1_plan_rung_has_no_formats_paragraph_when_the_suite_asserts_none() -> None:
     assert "Message formats" not in r1_plan_prompt(plan_section(PLAN, "### Chunk 1: The x tool"), ["tests/test_x.py"], "")

@@ -155,6 +162,7 @@ def test_the_manifest_pins_the_rung_the_provenance_and_both_digests(tmp_path: Pa
     assert body["contract"] == "prompt\n" and body["contracts"] == {RUNG: "prompt\n"}
     assert body["oracle"] == ["env", "PYTHONPATH=src", "python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"]
     assert body["source_paths"] == ["tools/x.py", "tests"]
+    assert body["ignored_paths"] == list(IGNORED_PATHS) == ["PROVENANCE.md"]
     assert body["provenance"] == {"repo": "https://github.com/pauleveritt/satyrn-evals.git", "base_sha": SHA_A, "fix_sha": SHA_B}
     assert body["digests"] == {"task_tree": "d" * 64, "prompt": contract_digest("prompt\n")}

diff --git a/tests/test_qualify.py b/tests/test_qualify.py
index e40b727..979b1b2 100644
--- a/tests/test_qualify.py
+++ b/tests/test_qualify.py
@@ -1,14 +1,22 @@
 """Offline qualification's pure judgements and the candidate list."""

+import json
+from pathlib import Path
+
 import pytest

 from satyrn_evals.attempt_record import AttemptCode
 from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
+from satyrn_evals.patch import parse_patch_paths
 from satyrn_evals.qualify import (
     CEILING_CANDIDATES,
     FLOOR_CANDIDATES,
+    SELF_HOSTED_CONVENTION_FILES,
+    convention_files_patch,
     judge_fixture,
     judge_harvest,
+    judge_prompt,
+    prompt_paths,
 )
 from satyrn_evals.qualify_fake_pi import committed_paths
 from satyrn_evals.receipt import Receipt
@@ -68,3 +76,70 @@ def test_every_candidate_is_bundled_hidden_and_carries_its_rung(name: str, rung:
     manifest = load_manifest(DEFAULT_TASKS_ROOT / name)
     assert manifest.oracle_visibility == "hidden"
     assert rung in manifest.contracts
+
+
+def test_a_harvest_with_the_convention_files_qualifies_only_when_grading_dropped_them() -> None:
+    patch = convention_files_patch(("PROVENANCE.md",)) + GOOD_PATCH
+    assert parse_patch_paths(patch) == ("PROVENANCE.md", "x.py")
+    assert judge_harvest(AttemptCode.OK, Verdict.PASS, patch, GOOD_PATCH, extra=("PROVENANCE.md",), dropped=("PROVENANCE.md",)).passed
+    assert not judge_harvest(AttemptCode.OK, Verdict.PASS, patch, GOOD_PATCH, extra=("PROVENANCE.md",)).passed
+    assert not judge_harvest(AttemptCode.OK, Verdict.UNAVAILABLE, patch, GOOD_PATCH, extra=("PROVENANCE.md",), dropped=()).passed
+
+
+PROMPT = """Task 9: The review script
+
+Files:
+- Create: `tools/review.py`, `tests/`
+- Modify: `src/cli.py` (add `launch --check RECORD`)
+
+Step 2: Run `uv run pytest tests/ tests/test_cli.py -q > /tmp/log 2>&1` → FAIL
+"""
+
+
+def _base(tmp_path: Path) -> Path:
+    base = tmp_path / "base"
+    (base / "tests").mkdir(parents=True)
+    (base / "tests" / "test_cli.py").write_text("")
+    (base / "src").mkdir()
+    (base / "src" / "cli.py").write_text("")
+    return base
+
+
+def test_prompt_paths_are_the_files_lines_and_the_pytest_arguments() -> None:
+    assert prompt_paths(PROMPT) == ["tools/review.py", "tests/", "src/cli.py", "tests/", "tests/test_cli.py"]
+
+
+def test_a_prompt_whose_paths_all_resolve_qualifies(tmp_path: Path) -> None:
+    check = judge_prompt({"R1-plan": PROMPT}, ("tools/review.py", "src/cli.py", "tests"), _base(tmp_path))
+    assert check.passed, check.detail
+
+
+@pytest.mark.parametrize(
+    ("prompt", "detail"),
+    [
+        (PROMPT.replace("`tests/`", "`its test module`"), "retired stand-in"),
+        (PROMPT.replace("`tests/`", "`tests/test_review.py`"), "tests/test_review.py"),
+        (PROMPT.replace("pytest tests/ ", "pytest its/ "), "its/"),
+        (PROMPT.replace("`tools/review.py`", "`tools/other.py`"), "tools/other.py"),
+    ],
+)
+def test_a_prompt_with_the_stand_in_or_an_unresolved_path_does_not_qualify(tmp_path: Path, prompt: str, detail: str) -> None:
+    check = judge_prompt({"R1-plan": prompt}, ("tools/review.py", "src/cli.py", "tests"), _base(tmp_path))
+    assert not check.passed and detail in check.detail
+
+
+def test_a_task_without_an_r1_plan_rung_has_no_prompt_to_judge(tmp_path: Path) -> None:
+    assert judge_prompt({"R1": "its test module"}, ("x.py",), tmp_path).passed
+
+
+@pytest.mark.parametrize("name", [*CEILING_CANDIDATES, *FLOOR_CANDIDATES])
+def test_every_candidate_prompt_qualifies(name: str) -> None:
+    manifest = load_manifest(DEFAULT_TASKS_ROOT / name)
+    check = judge_prompt(manifest.contracts, manifest.source_paths, DEFAULT_TASKS_ROOT / name / "base")
+    assert check.passed, check.detail
+
+
+@pytest.mark.parametrize("name", [*CEILING_CANDIDATES, *FLOOR_CANDIDATES])
+def test_every_generated_candidate_ignores_the_convention_files_and_no_other_task_ignores_any(name: str) -> None:
+    generated = "generator" in json.loads((DEFAULT_TASKS_ROOT / name / "manifest.json").read_text())
+    assert load_manifest(DEFAULT_TASKS_ROOT / name).ignored_paths == (SELF_HOSTED_CONVENTION_FILES if generated else ())
```

- [ ] **Step 2: Run them to verify they fail.**

Run: `uv run pytest -q tests/test_cut_task.py tests/test_qualify.py`
Expected: two collection errors, `ImportError: cannot import name 'IGNORED_PATHS' from 'tools.cut_task'` and `cannot import name 'SELF_HOSTED_CONVENTION_FILES' from 'satyrn_evals.qualify'`.

- [ ] **Step 3: Implement the generator and the checks.** Save as `$SCR/t2-src.diff` and run `git apply "$SCR/t2-src.diff"`:

```diff
diff --git a/src/satyrn_evals/qualify.py b/src/satyrn_evals/qualify.py
index 27015d4..359a070 100644
--- a/src/satyrn_evals/qualify.py
+++ b/src/satyrn_evals/qualify.py
@@ -11,11 +11,25 @@ candidate whatever its source:
    and grades pass;
 3. the hidden suite passes GOOD (known-good) three times running.

-`judge_fixture` and `judge_harvest` are pure; `qualify` runs the grades and
-the attempt, so it spawns and belongs to the integration tier.
+Two more, for the generator's defects the 2026-09-14 admission cells found:
+
+4. on a task cut by ``tools/cut_task.py`` (its manifest has a ``generator``
+   block) the fake attempt also writes ``PROVENANCE.md``, as a model
+   following the base's ``AGENTS.md`` does, and still grades pass, with the
+   receipt listing the dropped file;
+5. the ``R1-plan`` prompt never writes the retired stand-in "its test
+   module", and every path its Files lines and ``uv run pytest`` commands
+   name is a ``source_paths`` entry, a file in ``base/``, or a directory in
+   ``base/`` written with a trailing slash -- so it never names a hidden file.
+
+`judge_fixture`, `judge_harvest` and `judge_prompt` are pure but for
+`judge_prompt`'s look at ``base/``; `qualify` runs the grades and the attempt,
+so it spawns and belongs to the integration tier.
 """

+import json
 import os
+import re
 import shutil
 import sys
 import tempfile
@@ -34,6 +48,15 @@ from satyrn_evals.receipt import Receipt
 from satyrn_evals.verdict import Verdict

 GOOD_RUNS = 3
+PLAN_RUNG = "R1-plan"
+#: Files a self-hosted base's conventions require that its ``base/`` lacks.
+#: The generator ignores exactly these (``ignored_paths``) and the fake writes them.
+SELF_HOSTED_CONVENTION_FILES: tuple[str, ...] = ("PROVENANCE.md",)
+#: The stand-in the generator used for hidden names until 2026-09-15.
+RETIRED_STAND_IN = "its test module"
+_BACKTICKED = re.compile(r"`([^`\n]+)`")
+_PATH_LIKE = re.compile(r"\A[\w.\-/]+\Z")
+_FILES_LINE = ("- Create:", "- Modify:", "- Test:")
 #: The spec's candidates ("Workloads"), each with the rung it runs at.
 CEILING_CANDIDATES: dict[str, str] = {
     "agentclinic-repair-depth-3": "R1",
@@ -71,15 +94,67 @@ def judge_fixture(name: str, receipt: Receipt, *, expect: Verdict, expected_ids:
     return Check(name, passed, detail)


-def judge_harvest(code: AttemptCode, verdict: Verdict | None, patch_text: str | None, known_good: str) -> Check:
-    """The live harvest: whole (the known-good paths) and graded pass."""
-    want = sorted(parse_patch_paths(known_good))
+def judge_harvest(
+    code: AttemptCode,
+    verdict: Verdict | None,
+    patch_text: str | None,
+    known_good: str,
+    *,
+    extra: tuple[str, ...] = (),
+    dropped: tuple[str, ...] = (),
+) -> Check:
+    """The live harvest: whole (the known-good paths plus ``extra``), graded pass, ``extra`` dropped."""
+    want = sorted({*parse_patch_paths(known_good), *extra})
     got = sorted(parse_patch_paths(patch_text)) if patch_text else []
-    detail = f"code {code}, verdict {verdict}, paths {got} (known-good {want})"
-    passed = code is AttemptCode.OK and verdict is Verdict.PASS and got == want
+    detail = f"code {code}, verdict {verdict}, paths {got} (want {want}), ignored {sorted(dropped)}"
+    passed = code is AttemptCode.OK and verdict is Verdict.PASS and got == want and sorted(dropped) == sorted(extra)
     return Check("live-harvest", passed, detail)


+def prompt_paths(prompt: str) -> list[str]:
+    """The paths a prompt's Files lines and ``uv run pytest`` commands name, in order."""
+    found: list[str] = []
+    for line in prompt.splitlines():
+        if line.lstrip().startswith(_FILES_LINE):
+            found += [token for token in _BACKTICKED.findall(line) if _PATH_LIKE.match(token) and ("/" in token or "." in token)]
+    for command in _BACKTICKED.findall(prompt):
+        words = command.split()
+        if words[:3] != ["uv", "run", "pytest"]:
+            continue
+        for word in words[3:]:
+            if any(mark in word for mark in "<>|;&"):
+                break
+            if not word.startswith("-"):
+                found.append(word)
+    return found
+
+
+def judge_prompt(contracts: dict[str, str], source_paths: tuple[str, ...], base: Path) -> Check:
+    """The R1-plan prompt names no stand-in and no path the model cannot find or is not asked to write."""
+    prompt = contracts.get(PLAN_RUNG)
+    if prompt is None:
+        return Check("r1-plan-prompt", True, "no R1-plan rung")
+    if RETIRED_STAND_IN in prompt:
+        return Check("r1-plan-prompt", False, f"names the retired stand-in {RETIRED_STAND_IN!r}")
+    unresolved = [
+        path
+        for path in prompt_paths(prompt)
+        if path not in source_paths
+        and not (base / path).is_file()
+        and not (path.endswith("/") and (base / path).is_dir())
+    ]
+    detail = f"unresolved paths {unresolved}" if unresolved else f"{len(prompt_paths(prompt))} paths resolve"
+    return Check("r1-plan-prompt", not unresolved, detail)
+
+
+def convention_files_patch(paths: tuple[str, ...]) -> str:
+    """New-file sections for ``paths``, as a model following the base's conventions writes them."""
+    return "".join(
+        f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+| qualify | row |\n"
+        for path in paths
+    )
+
+
 @contextmanager
 def _fake_pi_on_path(scratch: Path, patch: Path) -> Iterator[None]:
     bin_dir = scratch / "bin"
@@ -120,7 +195,12 @@ def qualify(task_dir: Path, *, scratch: Path | None = None) -> list[Check]:
         checks.append(
             judge_fixture("known-broken", grade(task_dir, broken, root / "broken.json"), expect=Verdict.FAIL, expected_ids=expected)
         )
-        with _fake_pi_on_path(root, good):
+        checks.append(judge_prompt(manifest.contracts, manifest.source_paths, task_dir / "base"))
+        generated = "generator" in json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
+        extra = SELF_HOSTED_CONVENTION_FILES if generated else ()
+        harvest = root / "harvest.patch"
+        harvest.write_text(convention_files_patch(extra) + good.read_text(encoding="utf-8"), encoding="utf-8")
+        with _fake_pi_on_path(root, harvest):
             record = attempt(
                 task=manifest.name,
                 tasks_root=task_dir.parent,
@@ -130,7 +210,11 @@ def qualify(task_dir: Path, *, scratch: Path | None = None) -> list[Check]:
             )
         patch = root / "attempts" / record.attempt_dir / "patch.diff" if record.attempt_dir else None
         patch_text = patch.read_text(encoding="utf-8") if patch is not None and patch.is_file() else None
-        checks.append(judge_harvest(record.code, record.verdict, patch_text, good.read_text(encoding="utf-8")))
+        receipt = root / "attempts" / record.attempt_dir / "receipt.json" if record.attempt_dir else None
+        dropped = tuple(json.loads(receipt.read_text(encoding="utf-8")).get("ignored_paths", [])) if receipt is not None and receipt.is_file() else ()
+        checks.append(
+            judge_harvest(record.code, record.verdict, patch_text, good.read_text(encoding="utf-8"), extra=extra, dropped=dropped)
+        )
         return checks
     finally:
         shutil.rmtree(root, ignore_errors=True)
diff --git a/tools/cut_task.py b/tools/cut_task.py
index 0bb33f0..f817799 100644
--- a/tools/cut_task.py
+++ b/tools/cut_task.py
@@ -18,8 +18,15 @@ spec file under ``tools/task_specs/`` (spec, "The self-hosted generator"):
 The R1-plan prompt is the plan task's title, Files, Interfaces minus its
 Consumes lines, and the prose of every step with fenced code removed, plus
 the literal message formats the hidden suite asserts (the spec's ``formats``
-text). HIDDEN paths and basenames are written as "its test module": a
-contract that names a grader-only path is refused at load.
+text). A HIDDEN path is written as its directory (``tests/test_x.py`` becomes
+``tests/``) and a bare HIDDEN basename as "a test module under tests/": a
+contract that names a grader-only path is refused at load, and the prompt
+must still name a directory the model can put its own tests in.
+
+The manifest's ``ignored_paths`` is ``PROVENANCE.md``: ``base/`` drops it but
+keeps ``AGENTS.md``, which requires a row per file, so grading drops a
+patch's ``PROVENANCE.md`` instead of refusing the verdict. Qualification's
+fake attempt writes the same files (``SELF_HOSTED_CONVENTION_FILES``).

 The expected test ids are the hidden suite collected at GOOD by this
 interpreter's pytest, with the spec's ``oracle_env`` applied.
@@ -47,6 +54,7 @@ from dataclasses import dataclass
 from pathlib import Path

 from satyrn_evals.attempt import contract_digest
+from satyrn_evals.qualify import SELF_HOSTED_CONVENTION_FILES
 from satyrn_evals.task_tree import tree_digest

 ROOT = Path(__file__).resolve().parent.parent
@@ -55,8 +63,8 @@ RUNG = "R1-plan"
 REPO_URL = "https://github.com/pauleveritt/satyrn-evals.git"
 EXCLUDED_PREFIXES = ("docs/superpowers/plans/", "docs/superpowers/specs/", ".claude/", ".github/")
 EXCLUDED_FILES = frozenset({"PROVENANCE.md"})
+IGNORED_PATHS = SELF_HOSTED_CONVENTION_FILES
 RESIDUE_IGNORES = (".pytest_cache/", "__pycache__/", ".ruff_cache/", ".venv/")
-HIDDEN_STAND_IN = "its test module"
 ORACLE = ("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook")
 PUBLIC_SUITE = ("uv", "run", "pytest", "-q")
 _SHA = re.compile(r"\A[0-9a-f]{40}\Z")
@@ -123,6 +131,8 @@ def load_spec(path: Path) -> TaskSpec:
     if not isinstance(body["formats"], str):
         raise CutError(f"spec {path}: formats must be a string (empty when the suite asserts none)")
     hidden = _strings(body["hidden"], "hidden")
+    if any("/" not in h for h in hidden):
+        raise CutError(f"spec {path}: every hidden file must sit under a directory (the prompt names the directory)")
     if len({Path(h).name for h in hidden}) != len(hidden):
         raise CutError(f"spec {path}: hidden basenames must be distinct (the overlay is flattened)")
     return TaskSpec(
@@ -186,12 +196,17 @@ def r1_plan_prompt(section: str, hidden: Sequence[str], formats: str) -> str:
     if formats.strip():
         prompt += "\n\nMessage formats the acceptance suite asserts, match them exactly: " + formats.strip()
     for path in sorted(hidden, key=len, reverse=True):
-        prompt = prompt.replace(path, HIDDEN_STAND_IN)
+        prompt = prompt.replace(path, hidden_directory(path))
     for path in hidden:
-        prompt = prompt.replace(Path(path).name, HIDDEN_STAND_IN)
+        prompt = prompt.replace(Path(path).name, f"a test module under {hidden_directory(path)}")
     return prompt + "\n"


+def hidden_directory(path: str) -> str:
+    """The directory a HIDDEN path is written as, with a trailing slash (``tests/``)."""
+    return f"{Path(path).parent.as_posix()}/"
+
+
 def broken_patch(base_texts: Mapping[str, str | None], broken: Mapping[str, str]) -> str:
     """A git-style patch replacing each broken file with its stub (new file when absent at BASE)."""
     chunks: list[str] = []
@@ -224,6 +239,7 @@ def manifest_body(
         "oracle": oracle,
         "expected_test_ids": list(expected_test_ids),
         "source_paths": [*spec.files, "tests"],
+        "ignored_paths": list(IGNORED_PATHS),
         "public_suite": list(PUBLIC_SUITE),
         "fixtures": {"known_good": "fixtures/known-good.patch", "known_broken": "fixtures/known-broken.patch"},
         "grader_overlay": "overlay",
```

- [ ] **Step 4: The new checks fail against the committed tasks.**

Run: `uv run pytest -q tests/test_cut_task.py tests/test_qualify.py`
Expected: `7 failed, 63 passed`. The failures are `test_every_candidate_prompt_qualifies[selfhost-run-record-gate|selfhost-review-script|selfhost-docs-linter]` and `test_every_generated_candidate_ignores_the_convention_files_and_no_other_task_ignores_any[...]` for all four self-hosted tasks.
Run: `uv run satyrn-evals qualify selfhost-run-record-gate selfhost-guard-prefixes selfhost-review-script selfhost-docs-linter > "$SCR/qualify-old.txt" 2>&1; echo "EXIT: $?"; grep FAILED "$SCR/qualify-old.txt"`
Expected: `EXIT: 1` and seven `FAILED` lines: `r1-plan-prompt FAILED: names the retired stand-in 'its test module'` for run-record-gate, review-script and docs-linter, and `live-harvest FAILED: code OK, verdict unavailable, ...` for all four. This is the evidence that the checks catch both defects.

- [ ] **Step 5: Re-cut the four self-hosted tasks.**

```bash
for t in selfhost-run-record-gate selfhost-guard-prefixes selfhost-review-script selfhost-docs-linter; do rm -rf "src/satyrn_evals/tasks/$t"; done
uv run python tools/cut_task.py cut tools/task_specs/selfhost-run-record-gate.json tools/task_specs/selfhost-guard-prefixes.json tools/task_specs/selfhost-review-script.json tools/task_specs/selfhost-docs-linter.json; echo "EXIT: $?"
uv run python tools/cut_task.py check tools/task_specs/*.json; echo "EXIT: $?"
git status --short src/satyrn_evals/tasks
```

Expected: both `EXIT: 0`; four `matches a fresh cut` lines. `git status` shows exactly the four `manifest.json` files modified (nothing untracked, no AgentClinic path). `git diff --stat -- src/satyrn_evals/tasks` shows 9 lines changed for docs-linter, review-script and run-record-gate and 3 for guard-prefixes. The new prompt digests are docs-linter `c30a17fa437b6b24858c5657bfd41c3945caceca96996ed31e9d66624965e080`, review-script `68d85f2f2ba6dc43769e7c5bc801f78aaf5e8d240318cc7c8471aabb6aedcb49` and run-record-gate `f9b4fa968d71ee04252b9608ab7eafae20f71a6258272498ccb9e4d72f8f1eef`. `grep -c "its test module" src/satyrn_evals/tasks/*/manifest.json` prints 0 for every task.

- [ ] **Step 6: The spec's generator paragraph.** Save as `$SCR/t2-spec.diff` and run `git apply "$SCR/t2-spec.diff"`:

```diff
diff --git a/docs/superpowers/specs/2026-09-13-release-one-design.md b/docs/superpowers/specs/2026-09-13-release-one-design.md
index a7e685f..f82e4c2 100644
--- a/docs/superpowers/specs/2026-09-13-release-one-design.md
+++ b/docs/superpowers/specs/2026-09-13-release-one-design.md
@@ -219,12 +219,17 @@ plan-anchor)`. `base/` is `git archive BASE` minus plans, specs, `.claude`,
 `.github`, `PROVENANCE.md` and the hidden files, plus a `.gitignore` for
 runtime residue. `overlay/` holds HIDDEN at GOOD. `known-good.patch` is GOOD's
 diff restricted to `files`; `known-broken.patch` stubs the target.
-`manifest.json` carries provenance shas, the task-tree digest and the prompt
-digest. `tools/cut_task.py` builds it deterministically. Qualification is
-offline: `grade` passes known-good and fails known-broken with zero
-collection errors; a fake attempt that writes GOOD's files, leaves some
-untracked and commits the rest is harvested whole and graded pass; the hidden
-suite passes GOOD three times running. Every merged phase yields candidates.
+`manifest.json` carries provenance shas, the task-tree digest, the prompt
+digest and `ignored_paths: ["PROVENANCE.md"]`: the base keeps `AGENTS.md`,
+which asks for provenance rows, so grading drops those files from a patch
+before the allowlist and lists them on the receipt. The prompt writes a
+hidden path as its directory (`tests/`). `tools/cut_task.py` builds it
+deterministically. Qualification is offline: `grade` passes known-good and
+fails known-broken with zero collection errors; a fake attempt that writes
+GOOD's files and `PROVENANCE.md`, leaves some untracked and commits the rest
+is harvested whole and graded pass; the R1-plan prompt names no path outside
+`base/` and `files`; the hidden suite passes GOOD three times running. Every
+merged phase yields candidates.

 **Conditions.** Every workload runs cold. Warm is a declared secondary on
 `complaint-lifecycle` only: a recorded developer prefix replayed
```

- [ ] **Step 7: Run everything to verify it passes.**

Run: `uv run pytest -q tests/test_cut_task.py tests/test_qualify.py` → `70 passed`.
Run: `uv run satyrn-evals qualify agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-guard-prefixes selfhost-review-script agentclinic-repair-depth-2 selfhost-docs-linter > "$SCR/qualify.txt" 2>&1; echo "EXIT: $?"; grep -c " ok: " "$SCR/qualify.txt"` → `EXIT: 0`, `36`. The review-script `live-harvest` line reads `paths ['PROVENANCE.md', 'tools/review.py'] (want ['PROVENANCE.md', 'tools/review.py']), ignored ['PROVENANCE.md']`.
Run: `uv run pytest -m integration -q --basetemp "$SCR/bt" tests/integration/test_qualify.py tests/integration/test_cut_task.py tests/integration/test_grade.py tests/integration/test_harvest_qualification.py; echo "EXIT: $?"; rm -rf "$SCR/bt"` → `EXIT: 0` (38 passed, under a minute).
Run: `uv run pytest -m integration -q --basetemp "$SCR/bt" tests/integration/test_attempt.py tests/integration/test_grade_git_env.py tests/integration/test_capture.py tests/integration/test_grade_overlay.py tests/integration/test_grade_materialized_env.py tests/integration/test_grade_preservation_auto_overlay.py; echo "EXIT: $?"; rm -rf "$SCR/bt"` → `EXIT: 0` (86 passed, 3 skipped: every receipt-writing integration row still passes with Task 1's grading).
Run: `uv run ruff check --fix && just gates; echo "EXIT: $?"` → `EXIT: 0` (default tier 2,046 passed; `lint-docs: all documents within cap`; spec 399 lines).

- [ ] **Step 8: Commit.**

```bash
git add tools/cut_task.py src/satyrn_evals/qualify.py tests/test_cut_task.py tests/test_qualify.py tests/integration/test_qualify.py docs/superpowers/specs/2026-09-13-release-one-design.md src/satyrn_evals/tasks/selfhost-run-record-gate src/satyrn_evals/tasks/selfhost-guard-prefixes src/satyrn_evals/tasks/selfhost-review-script src/satyrn_evals/tasks/selfhost-docs-linter
git commit -m "Phase 2b.1: the generator writes a hidden path as its directory and ignores PROVENANCE.md; qualification checks both; the four self-hosted tasks re-cut"
```

- [ ] **Step 9: Hand the operator the rerun commands (the controller does not run them).** Copy the section "Operator: the self-hosted admission reruns" below verbatim into the task report.

---

## Operator: the self-hosted admission reruns

Not executed by the controller: these spend inference. Run them from the evals checkout after both task commits, one record at a time, each launch in the background. Before the first, check the machine as the 2c checklist does (items 4–6: settings provenance as the cell, the isolated preflight with the full hunt, no stale cell process). The k is 3, as on 2026-09-14. A launch exit of 4 means the sitting's 60 minutes capped it: run the same `launch` again until it exits 0. Exit 1, 2 or 3 stops the reruns; report the result's `reason` and the launcher's stderr verbatim. Between records, `git log --oneline -2` shows the result commit.

```bash
AUTH="maintainer-requested rerun after the generator fix, 2026-09-15"

# 1. selfhost-run-record-gate
uv run satyrn-evals record new --output records/2026-09-15-admission-selfhost-run-record-gate.json --task selfhost-run-record-gate --rung R1-plan --arm baseline --n 4 --k 3 --purpose admission --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 --previous-result records/2026-09-14-admission-agentclinic-repair-depth-2.result.json --authority "$AUTH"
git add records/2026-09-15-admission-selfhost-run-record-gate.json && git commit -m "Phase 3 admission record: selfhost-run-record-gate (Baseline, n=4, k=3, 32,000 tokens and 48 turns, isolated; $AUTH)"
uv run satyrn-evals launch records/2026-09-15-admission-selfhost-run-record-gate.json --arm arms/baseline-ornith15-9b.json; echo "EXIT: $?"
git add records/2026-09-15-admission-selfhost-run-record-gate.result.json && git commit -m "Phase 3 admission result: selfhost-run-record-gate ($(python3 -c 'import json; print(json.load(open("records/2026-09-15-admission-selfhost-run-record-gate.result.json"))["status"])'))"

# 2. selfhost-guard-prefixes
uv run satyrn-evals record new --output records/2026-09-15-admission-selfhost-guard-prefixes.json --task selfhost-guard-prefixes --rung R1-plan --arm baseline --n 4 --k 3 --purpose admission --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 --previous-result records/2026-09-15-admission-selfhost-run-record-gate.result.json --authority "$AUTH"
git add records/2026-09-15-admission-selfhost-guard-prefixes.json && git commit -m "Phase 3 admission record: selfhost-guard-prefixes (Baseline, n=4, k=3, 32,000 tokens and 48 turns, isolated; $AUTH)"
uv run satyrn-evals launch records/2026-09-15-admission-selfhost-guard-prefixes.json --arm arms/baseline-ornith15-9b.json; echo "EXIT: $?"
git add records/2026-09-15-admission-selfhost-guard-prefixes.result.json && git commit -m "Phase 3 admission result: selfhost-guard-prefixes ($(python3 -c 'import json; print(json.load(open("records/2026-09-15-admission-selfhost-guard-prefixes.result.json"))["status"])'))"

# 3. selfhost-review-script
uv run satyrn-evals record new --output records/2026-09-15-admission-selfhost-review-script.json --task selfhost-review-script --rung R1-plan --arm baseline --n 4 --k 3 --purpose admission --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 --previous-result records/2026-09-15-admission-selfhost-guard-prefixes.result.json --authority "$AUTH"
git add records/2026-09-15-admission-selfhost-review-script.json && git commit -m "Phase 3 admission record: selfhost-review-script (Baseline, n=4, k=3, 32,000 tokens and 48 turns, isolated; $AUTH)"
uv run satyrn-evals launch records/2026-09-15-admission-selfhost-review-script.json --arm arms/baseline-ornith15-9b.json; echo "EXIT: $?"
git add records/2026-09-15-admission-selfhost-review-script.result.json && git commit -m "Phase 3 admission result: selfhost-review-script ($(python3 -c 'import json; print(json.load(open("records/2026-09-15-admission-selfhost-review-script.result.json"))["status"])'))"

# 4. selfhost-docs-linter
uv run satyrn-evals record new --output records/2026-09-15-admission-selfhost-docs-linter.json --task selfhost-docs-linter --rung R1-plan --arm baseline --n 4 --k 3 --purpose admission --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 --previous-result records/2026-09-15-admission-selfhost-review-script.result.json --authority "$AUTH"
git add records/2026-09-15-admission-selfhost-docs-linter.json && git commit -m "Phase 3 admission record: selfhost-docs-linter (Baseline, n=4, k=3, 32,000 tokens and 48 turns, isolated; $AUTH)"
uv run satyrn-evals launch records/2026-09-15-admission-selfhost-docs-linter.json --arm arms/baseline-ornith15-9b.json; echo "EXIT: $?"
git add records/2026-09-15-admission-selfhost-docs-linter.result.json && git commit -m "Phase 3 admission result: selfhost-docs-linter ($(python3 -c 'import json; print(json.load(open("records/2026-09-15-admission-selfhost-docs-linter.result.json"))["status"])'))"
```

For each cell, read `receipt.json` under `~/satyrn-runs/2026-09-15-admission-<task>/baseline/*/`: `ignored_paths` should list `PROVENANCE.md` wherever the model wrote one, and no verdict should read `patch touches non-source path: PROVENANCE.md`. The 2026-09-14 results for run-record-gate, guard-prefixes and review-script stay committed and unedited. The Phase 3 reading lists them as superseded by these records, naming the two generator defects. Docs-linter had no 2026-09-14 record.

---

## Self-review against the spec and the brief

- **Defect 1 (`PROVENANCE.md`)**: T1 gives the manifest `ignored_paths` (validated), `drop_ignored`, grading order (drop, then allowlist, then apply) and the receipt listing. T2 has the generator write `["PROVENANCE.md"]`. Base and `AGENTS.md` are unchanged (Ruling 1); T2 Step 5 shows only manifests change.
- **Defect 2 (the stand-in)**: T2 `hidden_directory`; `load_spec` refuses a hidden file with no directory; the unit row asserts "Create: `tools/x.py`, `tests/`" and "`uv run pytest tests/ -q`"; the basename row asserts "a test module under tests/unit/".
- **Re-cut, check, qualify**: T2 Steps 5 and 7 (`cut_task.py check` exit 0; `qualify` 36 of 36 ok, EXIT 0). R8 holds and the AgentClinic trees are untouched (Ruling 5).
- **The qualification check that would have caught both**: Ruling 4, T2 Step 4 (seven FAILED lines against the old manifests), plus default-tier rows over the bundled candidates.
- **The spec's qualification paragraph** now matches the code (Ruling 6).
- **Rerun commands**: four records `records/2026-09-15-admission-<task>.json`, Baseline, n=4, k=3, R1-plan, 32,000/48, isolated, `--purpose admission`, the authority text. They chain from `records/2026-09-14-admission-agentclinic-repair-depth-2.result.json`, are committed before launch, launched one at a time, and their results committed. The superseded results are left unedited.
- **Placeholders**: none. Names are consistent across tasks: `ignored_paths` in manifest, `TaskManifest`, `Receipt` and the receipt JSON; `SELF_HOSTED_CONVENTION_FILES` is `IGNORED_PATHS`.

## Test verification (plan review, 2026-09-15)

Every test this plan specifies was run in a scratch clone of evals `release-one` at `2b04227` (`$SCR`-sibling `.../scratchpad/genfix-plan/clone`, never the main checkout), with no inference. A prototype was committed there as `p1` (Task 1) and `p2` (Task 2); every diff block above was extracted from those commits.

- **Before each task, its new tests fail for the missing implementation only**: T1 `ImportError` for `drop_ignored`; 9 failed in `test_manifest.py`/`test_receipt.py`; 2 failed in `tests/integration/test_grade.py`. T2 `ImportError` for `IGNORED_PATHS` and `SELF_HOSTED_CONVENTION_FILES`; with the implementation but the old manifests, 7 failed in the default tier and `satyrn-evals qualify` on the four self-hosted tasks exited 1 with the seven FAILED lines quoted in Step 4.
- **After each task**: T1 `just gates` EXIT 0, default tier 2,024 passed; `tests/integration/test_grade.py` 20 passed. T2 `cut_task.py cut` and `check` EXIT 0 (four matches); only the four manifests changed. `satyrn-evals qualify` on all six candidates gave EXIT 0 and 36 ok. Integration `test_qualify.py`, `test_cut_task.py`, `test_grade.py` and `test_harvest_qualification.py` passed 38 in 46 s. `test_attempt.py`, `test_grade_git_env.py`, `test_capture.py`, `test_grade_overlay.py`, `test_grade_materialized_env.py` and `test_grade_preservation_auto_overlay.py` gave 86 passed, 3 skipped. `just gates` EXIT 0, default tier 2,046 passed; the spec is 399 lines. `record new` for `selfhost-review-script` with the Operator section's flags wrote a record (EXIT 0) to scratch, then deleted.
- **The plan text reproduces the commits**: the diff blocks applied with `git apply` in order on a fresh clone at `2b04227`, followed by Step 5's re-cut, give a tree identical to `p2`.

Found by running the draft, and fixed here. guard-prefixes' prompt never named its hidden file, so the prompt check alone does not catch it; the harvest check does (Ruling 4). The committed prompts name BASE files in `uv run pytest` commands (`tests/test_cli.py`) and `/tmp` paths in prose, so a check requiring "a directory in base or a file in `files`" for every path would refuse correct prompts; the check judges Files lines and pytest arguments and admits base files. The live-harvest detail's label now reads `want`, since the expected paths include `PROVENANCE.md`.
