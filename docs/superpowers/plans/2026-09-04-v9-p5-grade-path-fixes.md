# V9 P5 — Grade-path fixes: T5 auto-overlay opt-out, T6 stored-file check removal

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The V6 preservation grade stops triggering V7's auto-overlay
(T5), and the umask-002 portability hole in `load_overlay`'s stored-file
mode check is removed with a recorded V7 §5 correction (T6).

**Architecture:** `grade()` gains `auto_overlay: bool = True`; the session
preservation call passes `False`, restoring "public selectors, no overlay".
`load_overlay` drops its `mode & 0o022` refusal; materialization `0o444`
and the absence invariant remain the protection.

**Tech Stack:** Python ≥3.14, stdlib only.

**Spec:** `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md`
§4 T5/T6. Depends on nothing in P1–P4b (independent slice).

## Global Constraints

- **No commits.** Commits are maintainer-controlled (`docs/sdd.md`).
- Default tier must not spawn (tripwire). T5's pair is integration-tier (a
  real grade is a subprocess — kickoff guardrail); T6 is pure filesystem
  (default tier).
- Refusal tests get success siblings.
- House style: real annotations; `type` aliases; `match`/`case`; `:=`.
- `docs/sdd.md` cap: this plan stays ≤400 lines.

---

### Task 1: T5 — `grade(auto_overlay=...)` and the preservation opt-out

**Files:**
- Modify: `src/satyrn_evals/grade.py`, `src/satyrn_evals/session_grader.py`
- Test: `tests/integration/test_grade_preservation_auto_overlay.py` (new)

**Interfaces:**
- Consumes: `OverlaySpec`, `manifest.oracle_visibility` — unchanged.
- Produces: `grade(task_dir, patch_path, receipt_path, *, overlay=None,
  selectors=(), expected=None, enforce_allowlist=True,
  auto_overlay=True)`. When `auto_overlay` is False the auto-load and
  selector swap are skipped even on a hidden task with `overlay=None`.

- [ ] **Step 1: Build the divergent fixture**

Copy `tests/integration/data/mini-session` to
`tests/integration/data/mini-session-divergent`. In the copy, edit
`manifest.json` so the bare-grade target differs from the session's
preservation selectors:

```json
{
  "name": "mini-session-divergent",
  "contract": "Add feature_a and feature_b across a session, then review.",
  "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"],
  "expected_test_ids": [
    "test_solution.py::test_existing_preserved",
    "test_hidden_a.py::test_a"
  ],
  "source_paths": ["solution.py"],
  "fixtures": {
    "known_good": "fixtures/known-good.patch",
    "known_broken": "fixtures/known-broken.patch"
  },
  "grader_overlay": "grader/overlay",
  "oracle_visibility": "hidden",
  "provenance": { "repo": "bundled synthetic fixture", "base_sha": "unrecorded", "fix_sha": "unrecorded" }
}
```

`session.json` keeps `base_preservation_selectors =
["test_solution.py::test_existing_preserved"]` (public only) and the
step feature selectors. `known-good.patch` must keep `existing()` intact
while adding `feature_a`/`feature_b` — verify by copying mini-session's
own fixtures and running the pair below; if the copied known-good does not
make both the hidden feature tests and the public preservation test pass,
hand-edit `solution.py`'s expected end state in the patch (the fixture is
tiny and synthetic — this is a grader fixture, not a diagnostic workload).

- [ ] **Step 2: Write the failing tests (integration)**

```python
"""T5: preservation grading must not trigger V7's auto-overlay."""

from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

SPEC = Path(__file__).resolve().parents[1] / "data" / "mini-session-divergent"
PRESERVATION = ("test_solution.py::test_existing_preserved",)


def test_preservation_with_auto_overlay_hijack_is_unavailable(tmp_path: Path) -> None:
    """The old call shape (default auto_overlay=True) breaks preservation.

    Auto-overlay swaps selectors to manifest.expected_test_ids (which now
    include the hidden feature test), while the verdict's expected set is
    the public preservation selector -- executed ids land outside the
    expected set, so the verdict is UNAVAILABLE. This pins the hazard the
    fix removes.
    """
    receipt = grade(
        SPEC, SPEC / "fixtures" / "known-good.patch", tmp_path / "r.json",
        overlay=None, selectors=PRESERVATION, expected=PRESERVATION,
    )
    assert receipt.verdict is Verdict.UNAVAILABLE


def test_preservation_without_auto_overlay_passes_known_good(
    tmp_path: Path,
) -> None:
    """auto_overlay=False runs the public selectors with no overlay."""
    receipt = grade(
        SPEC, SPEC / "fixtures" / "known-good.patch", tmp_path / "r.json",
        overlay=None, selectors=PRESERVATION, expected=PRESERVATION,
        auto_overlay=False,
    )
    assert receipt.verdict is Verdict.PASS
    assert receipt.contamination is None  # no overlay materialized, no scan


def test_bare_grade_still_auto_overlays_and_annotates(tmp_path: Path) -> None:
    """The default behavior -- bare grade on a hidden task -- is unchanged."""
    receipt = grade(SPEC, SPEC / "fixtures" / "known-good.patch",
                    tmp_path / "r.json")
    assert receipt.verdict is Verdict.PASS
    assert receipt.contamination is not None
    assert receipt.contamination["visibility"] == "hidden"
```

- [ ] **Step 3: Run to verify the hazard test fails (red, pre-fix)**

Run: `uv run pytest -q tests/integration/test_grade_preservation_auto_overlay.py -m integration`
Expected: `test_preservation_without_auto_overlay_passes_known_good` and
`test_bare_grade_still_auto_overlays_and_annotates` FAIL (no
`auto_overlay` parameter); the hijack test may already pass. Do not delete
the hijack test when the signature lands — it pins the hazard.

- [ ] **Step 4: Implement**

In `src/satyrn_evals/grade.py`:

1. Change the signature (keep default behavior identical):

```python
def grade(
    task_dir: Path,
    patch_path: Path,
    receipt_path: Path,
    *,
    overlay: OverlaySpec | None = None,
    selectors: tuple[str, ...] = (),
    expected: tuple[str, ...] | None = None,
    enforce_allowlist: bool = True,
    auto_overlay: bool = True,
) -> Receipt:
```

2. Guard the auto path:

```python
    auto_overlay = (
        auto_overlay and overlay is None
        and manifest.oracle_visibility == "hidden"
    )
```

3. Extend the docstring: "``auto_overlay=False`` suppresses the auto-load
   for callers (the session preservation grader) that grade a hidden task
   against explicitly declared selectors with no overlay."

In `src/satyrn_evals/session_grader.py`, the preservation `_grade` call
(`:122-128`) gains the opt-out:

```python
                receipt = self._grade(
                    session_dir / last.patch_path,
                    preservation_receipt,
                    None,
                    spec.base_preservation_selectors,
                    enforce_allowlist=False,
                    auto_overlay=False,
                )
```

   and `_grade`'s signature gains `auto_overlay: bool = True`, forwarded to
   `grade(...)`.

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest -q tests/integration/test_grade_preservation_auto_overlay.py -m integration`
Expected: PASS. The hijack test still passes (it asserts the old shape's
`UNAVAILABLE`).

- [ ] **Step 6: Bundled fixtures stay green**

Run: `uv run pytest -q -m integration tests/integration/test_session_grading.py tests/integration/test_session_run.py tests/integration/test_grade_overlay.py tests/integration/test_agentclinic_gate.py`
Expected: PASS. (Any preservation-grade test over the coinciding bundled
fixtures must be unaffected.)

- [ ] **Step 7: Whole default tier**

Run: `uv run pytest -q`
Expected: PASS (the signature change is additive).

### Task 2: T6 — remove the stored-file writability refusal

**Files:**
- Modify: `src/satyrn_evals/overlay.py` (module docstring, `load_overlay`)
- Test: `tests/test_overlay.py`

**Interfaces:**
- Produces: `load_overlay` accepts group/other-writable overlay files (a
  umask-002 checkout); the remaining stored-file refusals (symlink,
  non-regular, non-UTF-8, source-path overlap, unsafe rel path) are
  unchanged; materialized copies are still `0o444`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_overlay.py`:

```python
def test_overlay_load_accepts_umask_002_checkout_modes(
    tmp_hidden_task: Path,
) -> None:
    """T6: group/other-writable files (664 on Debian/Ubuntu) must load.

    git stores regular files as 100644/100755; the on-disk mode at load is
    a property of the checkout umask, not of the store. The old refusal
    made every hidden task unusable on umask-002 systems.
    """
    overlay_root = tmp_hidden_task / "grader" / "overlay"
    for path in overlay_root.rglob("*"):
        if path.is_file():
            path.chmod(0o664)
    spec = load_overlay(tmp_hidden_task, load_manifest(tmp_hidden_task))
    assert spec.rel_paths  # loaded, digests recorded


def test_overlay_materialization_still_read_only(
    tmp_hidden_task: Path, tmp_path: Path,
) -> None:
    """The 0o444 materialization is unchanged: defense in depth remains."""
    spec = load_overlay(tmp_hidden_task, load_manifest(tmp_hidden_task))
    materialize_overlay(spec, tmp_path / "work")
    for rel in spec.rel_paths:
        mode = (tmp_path / "work" / rel).stat().st_mode & 0o777
        assert mode == 0o444


def test_overlay_still_refuses_a_symlink(tmp_path: Path) -> None:
    """A genuine stored-file defect still refuses (success sibling)."""
    task_dir = tmp_path / "t"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "grader" / "overlay").mkdir(parents=True)
    (task_dir / "grader" / "overlay" / "link").symlink_to("/etc/passwd")
    manifest = TaskManifest(
        name="t", contract="c", oracle=("python", "-m", "pytest"),
        expected_test_ids=("test_x.py::test_a",), source_paths=("src",),
        fixtures={"known_good": "fixtures/known-good.patch"},
        grader_overlay="grader/overlay", oracle_visibility="hidden",
    )
    with pytest.raises(OverlayError, match="symbolic link"):
        load_overlay(task_dir, manifest)
```

(Reuse the file's existing `tmp_hidden_task`-style fixtures and imports —
`OverlayError`, `TaskManifest`, `load_overlay`, `materialize_overlay`,
`load_manifest`. If the file's hidden-task fixture writes files at 644,
chmod to 664 inside the first test as shown.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_overlay.py -k "umask or still_refuses"`
Expected: FAIL — the 664 tree refuses with "group/other-writable".

- [ ] **Step 3: Implement**

In `src/satyrn_evals/overlay.py`, delete the mode check inside
`load_overlay` (today `overlay.py:74-79`):

```python
        if stat.S_IMODE(path.stat().st_mode) & 0o022:
            raise OverlayError(...)
```

If `stat` is then unused in the module, remove its import. Extend the
module docstring with the correction:

```
Correction (V9, 2026-09-04): load no longer refuses group/other-writable
stored files. Git's index stores regular files as 100644/100755, so the
on-disk mode at load is a property of the checkout umask (002 on
Debian/Ubuntu yields 664 for a clean store), not of the store; the old
check refused clean checkouts on default-Linux systems and could catch
nothing git would not normalize. Materialization chmods 0o444 after digest
verification, and the real invariant -- overlays never materialize in
executor-reachable paths -- is unchanged (assert_overlay_absent).
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_overlay.py`
Expected: PASS.

- [ ] **Step 5: Amend the V7 spec record**

Append to `docs/superpowers/specs/2026-09-04-v7-task-visibility-leak-detection-design.md`
§5 (after the "At load, bounded by git's mode vocabulary" bullet) a note:

```
> **Superseded by V9 (2026-09-04):** the stored-file group/other-writable
> refusal was removed. Git's mode vocabulary argument stands, but the
> *checkout* umask (002 on Debian/Ubuntu) makes a clean 100644 store land
> 664 on disk, so the check refused clean checkouts and could catch nothing
> git would not normalize. V9 spec §4 T6 records the correction; the
> materialization 0o444 and the absence invariant remain.
```

- [ ] **Step 6: Whole default tier**

Run: `uv run pytest -q`
Expected: PASS. Then `uv run ruff check src/satyrn_evals tests` and
`uv run python tools/lint_docs.py` (the V7 spec edit must stay ≤400 — the
note replaces nothing, so check the amended line count stays at or under
the current total; if over, trim the note's prose).
