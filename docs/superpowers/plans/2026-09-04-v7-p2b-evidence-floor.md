# V7 P2b — Detector evidence floor and name candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the detector discriminates in both directions against the bundled `session-mechanics` task by name (BRIEF rule 8), widen the payload scan to the full candidate-name set, and pin the adapter's constructed argv/env surfaces.

**Architecture:** No production code beyond one loop change in `scan_texts`; the substance is the evidence floor — fire on a known-contaminated patch built from the bundled overlay, silence on the bundled known-good patch and on a model-authored restating test.

**Tech:** Python ≥3.14, pytest, no subprocess, no network.

**Spec:** `docs/superpowers/specs/2026-09-04-v7-task-visibility-leak-detection-design.md` (§1 candidate names, §3 evidence floor, §11 done-when 3). Plan order: P1 → P2 → P2b → P3 → P4.

## Global Constraints

- Default tier only — pure functions, no subprocess (tripwire green).
- If the known-good test fails, the block rule is over-firing: fix P2's `scan_patch`, never weaken these tests.
- House style: `type` aliases, full annotations.

---

### Task 1: The evidence floor, asserted by naming bundled fixtures

**Files:**
- Test: `tests/test_contamination.py`

**Interfaces:**
- Consumes: `scan_patch`, the bundled `session-mechanics` task (`DEFAULT_TASKS_ROOT`), its `grader/overlay/` files via `load_overlay` (so `spec.texts`, P1 Task 4), its `fixtures/known-good.patch`.
- Produces: the BRIEF-rule-8 proof the spec's done-when 3 requires — fire on known-bad, silence on known-good, both asserted by name, plus the restating-test silence the sixfold-overstatement lesson demands.

- [ ] **Step 1: Write the failing-or-proving tests**

Append to `tests/test_contamination.py`:

```python
import json
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.overlay import load_overlay

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
```

- [ ] **Step 2: Run to verify the floor holds**

Run: `.venv/bin/pytest tests/test_contamination.py -k "bundled or known_good or restatement" -q`
Expected: PASS. These may pass immediately after P2 — that is the floor proving itself. If the known-good or restatement test fails, the block rule over-fires: fix P2 Task 2, do not touch these tests.

- [ ] **Step 3: Commit**

```bash
git add tests/test_contamination.py
git commit -m "test: contamination evidence floor on named session-mechanics fixtures"
```

---

### Task 2: Payload scan matches task-relative overlay names too

**Files:**
- Modify: `src/satyrn_evals/contamination.py` (`scan_texts` only)
- Test: `tests/test_contamination.py`

**Interfaces:**
- Consumes: `OverlaySpec.root` (P1 Task 4) — a real relative `Path`, whose `.name` yields the task-relative prefix without touching the disk.
- Produces: `scan_texts` matches BOTH the overlay-root-relative name (`tests/t_hidden.py`) and the task-relative name (`grader/overlay/tests/t_hidden.py`), per spec §1's candidate set. All P2 tests pass unchanged.

- [ ] **Step 1: Write the failing test**

```python
def test_scan_texts_matches_task_relative_overlay_name_too():
    spec = make_spec()
    sources = [("step2/tool_end", "opened grader/overlay/tests/t_hidden.py")]
    assert scan_texts(sources, spec).outcome == "flagged"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_contamination.py -k task_relative -q`
Expected: FAIL — only the root-relative name matches today.

- [ ] **Step 3: Implement**

In `contamination.py`, replace the `spec.rel_paths` loop in `scan_texts` with a candidate-name expansion — the same set `manifest._overlay_declared_names` (P1 Task 2) computes from the filesystem, derived here from the spec alone:

```python
def _name_candidates(spec: "OverlaySpec") -> tuple[str, ...]:
    """Root-relative and task-relative forms of every overlay path."""
    names: list[str] = []
    for rel in spec.rel_paths:
        names.append(rel)
        if spec.root is not None:
            names.append(f"{spec.root.as_posix()}/{rel}")
    return tuple(dict.fromkeys(names))
```

and iterate `_name_candidates(spec)` in `scan_texts`. State the shared rule in both docstrings: P1 Task 2 enumerates from the filesystem, this enumerates from the spec; both must cover root-relative and task-relative forms.

- [ ] **Step 4: Run everything**

Run: `.venv/bin/pytest tests/test_contamination.py tests/test_manifest.py tests/test_session_manifest.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
ruff check src/satyrn_evals/contamination.py
git add src/satyrn_evals/contamination.py tests/test_contamination.py
git commit -m "feat: payload scan matches task-relative overlay names as well"
```

---

### Task 3: The adapter's constructed argv and runtime env carry no overlay names (spec §4)

**Files:**
- Test: `tests/test_pi_session_driver.py`

**Interfaces:**
- Consumes: `build_pi_argv` (`adapters/pi_session.py:86`), `_SESSION_RUNTIME_ENV` (the fixed dict merged over `os.environ` at `pi_session.py:334`), `_overlay_declared_names` (P1 Task 2).
- Produces: the spec §4 "not scanned, with reasons" companion — the surfaces evals *constructs* are pinned by test. The `os.environ` pass-through is the contributor's own environment, not evals-constructed content; the test says so in its docstring.

- [ ] **Step 1: Write the test**

```python
def test_pi_child_argv_and_runtime_env_carry_no_overlay_names():
    """Pins what evals constructs: the pi argv and _SESSION_RUNTIME_ENV.

    The inherited os.environ is the contributor's own environment, not
    evals-constructed content, and is out of scope here (spec §4).
    """
    from satyrn_evals.adapters.pi_session import (
        _SESSION_RUNTIME_ENV,
        build_pi_argv,
    )
    from satyrn_evals.manifest import (
        DEFAULT_TASKS_ROOT,
        _overlay_declared_names,
        load_manifest,
    )

    task_dir = DEFAULT_TASKS_ROOT / "session-mechanics"
    manifest = load_manifest(task_dir)
    names = _overlay_declared_names(task_dir, manifest.grader_overlay)
    argv_text = " ".join(build_pi_argv(provider="p", model="m", pi_bin="pi"))
    env_text = " ".join(f"{k}={v}" for k, v in _SESSION_RUNTIME_ENV.items())
    for name in names:
        assert name not in argv_text
        assert name not in env_text
```

- [ ] **Step 2: Run**

Run: `.venv/bin/pytest tests/test_pi_session_driver.py -k overlay_names -q`
Expected: PASS. This is an invariant pin, not a behavior change — if it fails, the adapter is leaking task paths into its child process, and the adapter is wrong.

- [ ] **Step 3: Commit**

```bash
git add tests/test_pi_session_driver.py
git commit -m "test: adapter-constructed argv and runtime env never carry overlay names"
```
