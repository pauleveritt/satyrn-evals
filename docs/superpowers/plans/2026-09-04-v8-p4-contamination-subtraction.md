# V8 Plan 4 of 5 — Contamination base-window subtraction (slice 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the contamination detector from flagging overlay content the model was legitimately shown: subtract any overlay raw-line window that also occurs in the model-visible `base/` from the detector's needle set, additively (default empty), with its own fire/silent sibling pair.

**Architecture:** Plan 4 of 5 for V8 (`docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` §5). `contamination.scan_patch` stays pure and gains a `visible_texts` parameter; the subtraction happens inside `_match_block`'s window loop (minimal change — evidence order and whole-file/block semantics are untouched). The only caller passing visible texts is `grade()`'s auto-overlay path; `session.py:160` stays default (byte-identical). Runs after P3 (its integration test grades a dependency-bearing task, which needs P3's materialization).

**Tech Stack:** Python 3.14, `pytest` (pure functions — default tier, no subprocess; one integration test).

**Spec:** `docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` (§3 change 2, §5, §11.5/§11.7).

## Global Constraints

- Python `>=3.14`; real return annotations; `match`/`case`/walrus house style.
- Default tier: no model/network/subprocess — the subtraction itself is pure and default-tier.
- A refusal test has a sibling success test, always.
- Detection is annotation-only; it never changes a verdict or an exit code.
- Matching stays verbatim raw lines, window `GRADER_BLOCK_LINES = 4` — unchanged semantics except the needle subtraction.
- 100% coverage gate: `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100`.
- `ruff check .` clean; `just lint-docs` green.

### Task 1: Visible-window subtraction in the pure scanner

**Files:**
- Modify: `src/satyrn_evals/contamination.py` (`_match_block` at `:91-108`, `scan_patch` at `:110-119`)
- Test: `tests/test_contamination.py`

**Interfaces:**
- Consumes: existing `_nonblank`, `_added_files`, `OverlaySpec` (unchanged).
- Produces: `scan_patch(patch_text, spec, visible_texts: Sequence[str] = ())` — an overlay window (4 raw lines, or the whole file when shorter) that also occurs verbatim in a visible text is skipped as a needle. Default `()` preserves every pre-V8 result byte-for-byte.
- Consumed by: `grade.py:104` (auto path) in Task 2.

- [ ] **Step 1: Read the current scanner and its tests before editing**

Run: `sed -n 88,120p src/satyrn_evals/contamination.py && sed -n 1,40p tests/test_contamination.py`
The existing helpers are `make_spec()`, `_patch_adding(path, body)`, and bundled-overlay helpers; `_match_block` returns the first hit only, so evidence stays one item per (overlay file, patch file).

- [ ] **Step 2: Write the failing tests** (append to `tests/test_contamination.py`)

```python
# The shared redirect idiom: present BOTH in reference/tests/test_app.py (the
# vendored public tests) and in the 13-test overlay (re-derived 2026-09-04:
# 13 shared non-blank lines, 1 shared window at width 4, 0 at width 5).
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
```

- [ ] **Step 3: Run to verify the new tests fail**

Run: `uv run pytest tests/test_contamination.py -q -k "visible or default_visible or whole_file_visible"`
Expected: FAIL — `TypeError: scan_patch() got an unexpected keyword argument 'visible_texts'` and the shared-window flag (first test's second assert is the live pre-change signal).

- [ ] **Step 4: Implement the subtraction** (`contamination.py`)

Add a containment helper above `_match_block`:

```python
def _window_in_visible(needle: list[str], visible_seqs: Sequence[tuple[tuple[int, str], ...]]) -> bool:
    """True when the raw-line window appears verbatim in any visible text."""
    size = len(needle)
    if size == 0:
        return False
    for seq in visible_seqs:
        texts = [text for _, text in seq]
        for pos in range(len(texts) - size + 1):
            if texts[pos:pos + size] == needle:
                return True
    return False
```

Thread it through `_match_block` (only the signature and the loop change; evidence order and kind semantics are untouched):

```python
def _match_block(
    overlay_seq: tuple[tuple[int, str], ...],
    patch_seq: tuple[tuple[int, str], ...],
    visible_seqs: Sequence[tuple[tuple[int, str], ...]] = (),
) -> tuple[str, int] | None:
    """First verbatim window hit not present in any visible text."""
    window = min(GRADER_BLOCK_LINES, len(overlay_seq))
    if window == 0 or len(patch_seq) < window:
        return None
    kind = "whole_file" if window == len(overlay_seq) else "block"
    overlay_texts = [text for _, text in overlay_seq]
    patch_texts = [text for _, text in patch_seq]
    for start in range(len(overlay_texts) - window + 1):
        needle = overlay_texts[start : start + window]
        if _window_in_visible(needle, visible_seqs):
            continue  # shown content: not evidence of seeing the overlay
        for pos in range(len(patch_texts) - window + 1):
            if patch_texts[pos : pos + window] == needle:
                return kind, patch_seq[pos][0]
    return None
```

And `scan_patch` gains the parameter and builds the sequences once:

```python
def scan_patch(
    patch_text: str | None,
    spec: OverlaySpec,
    visible_texts: Sequence[str] = (),
) -> CheckResult:
    """Check (b): grader content inside a retained patch.

    ``visible_texts`` is model-visible content (the task's ``base/``
    files). An overlay window occurring there is not evidence of having
    seen the hidden overlay, so those needles are subtracted. Default
    empty: pre-V8 behavior is byte-identical.
    """
    if patch_text is None:
        return CheckResult("grader_content_in_patch", "unmeasured", ())
    evidence: list[Evidence] = []
    added = _added_files(patch_text)
    visible_seqs = tuple(_nonblank(text) for text in visible_texts)
    for overlay_path, text in spec.texts.items():
        overlay_seq = _nonblank(text)
        for patch_path, patch_body in added.items():
            if (hit := _match_block(overlay_seq, _nonblank(patch_body), visible_seqs)) is not None:
                kind, line = hit
                evidence.append(Evidence(kind, overlay_path, patch_path, line))
    return CheckResult(
        "grader_content_in_patch", "flagged" if evidence else "clean", tuple(evidence)
    )
```

- [ ] **Step 5: Run the whole contamination suite**

Run: `uv run pytest tests/test_contamination.py -q`
Expected: PASS — every pre-existing test unchanged (payload, whole-file, one-line idiom, blank-run, missing patch, clean patch, bundled trio), plus the four new tests. The bundled trio (`_bundled_spec` on `session-mechanics`) passes with no visible texts — the additive guard is proven by the unchanged default.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/contamination.py tests/test_contamination.py
git commit -m "feat: contamination subtracts base-visible overlay windows"
```

### Task 2: Wire the visible base texts through `grade()`'s auto path

**Files:**
- Modify: `src/satyrn_evals/grade.py` (auto-overlay branch at `:102-107`)
- Test: `tests/integration/test_grade_overlay.py` (extend) — integration, real grade; requires P2's materialization

**Interfaces:**
- Consumes: `scan_patch(patch, spec, visible_texts=())` (Task 1).
- Produces: for hidden tasks, the contamination annotation reflects subtraction: a patch re-adding the shared public-test idiom grades `clean` on the contamination check; an overlay-only block still flags. Session grading (`session.py:160`) is untouched this plan.

- [ ] **Step 1: Write the failing integration test** (extend `tests/integration/test_grade_overlay.py`, mirroring its existing grade-call helper `_grade`)

```python
def test_grade_subtracts_visible_public_test_idiom(tmp_path) -> None:
    task_dir = resolve_task("agentclinic-repair-plausible-wrong-fix")
    public = (task_dir / "base" / "tests" / "test_app.py").read_text()
    assert "follow_redirects=False" in public  # precondition: the idiom is visible
    idiom_lines = [
        line for line in public.splitlines()
        if "follow_redirects" in line or "status_code == 303" in line
        or 'location' in line and '/complaints' in line
    ]
    body = "\n".join(idiom_lines) + "\n"
    patch = (
        "--- a/tests/test_new.py\n+++ b/tests/test_new.py\n"
        "@@ -0,0 +1,4 @@\n"
        + "".join(f"+{line}\n" for line in idiom_lines)
    )
    receipt = _grade(task_dir, patch, tmp_path)
    finding = receipt["contamination"]["checks"][0]
    assert finding["check"] == "grader_content_in_patch"
    assert finding["outcome"] == "clean"
```

Run it once BEFORE wiring: Expected FAIL — `finding["outcome"] == "flagged"` (the pre-change false positive), confirming the test is live.

- [ ] **Step 2: Implement the wiring**

`grade.py` — in the `auto_overlay` branch, read the base texts and pass them:

```python
    contamination: dict | None = None
    if auto_overlay:
        base_root = task_dir / "base"
        visible_texts = (
            [
                path.read_text(encoding="utf-8", errors="replace")
                for path in sorted(base_root.rglob("*"))
                if path.is_file()
            ]
            if base_root.is_dir()
            else []
        )
        result = scan_patch(patch_text, overlay, visible_texts=visible_texts)
```

- [ ] **Step 3: Run to verify**

Run: `uv run pytest tests/integration/test_grade_overlay.py -q`
Expected: PASS — shared-idiom patch clean; the file's existing overlay-leak tests still flag (their content is not in the task's `base/`).

- [ ] **Step 4: Full default tier as the additive regression guard**

Run: `uv run pytest -q`
Expected: all default-tier tests pass, including the planted no-subprocess tripwire and the session `scan_patch` call sites (unchanged, default visible).

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/grade.py tests/integration/test_grade_overlay.py
git commit -m "feat: grade passes visible base texts to the contamination scanner"
```

### Task 3: Slice-3 self-review

- [ ] **Step 1: Coverage gate**

Run: `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-report=term-missing --cov-fail-under=100`
Expected: 100% (the new `_window_in_visible` and the subtraction branch are covered by the default-tier tests; `visible_seqs` empty path by the untouched pre-existing tests).

- [ ] **Step 2: Ruff and doc caps**

Run: `ruff check . && just lint-docs`
Expected: clean.

- [ ] **Step 3: Spec cross-check.** Spec §5's fire/silent pair and additive-defaults guard exist as tests; §3 names this production change 2. Interfaces match P4's expectations (hidden-task contamination annotations are now truthful on graded cells). No placeholders. Hand off to P4.
