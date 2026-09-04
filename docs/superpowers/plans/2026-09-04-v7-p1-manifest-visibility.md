# V7 P1 — Manifest visibility and overlay texts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every task manifest declares `oracle_visibility` (`"visible"` default, `"hidden"`), enforced symmetrically against `grader_overlay`, with hidden tasks' authored texts scanned for overlay path names; and `OverlaySpec` carries overlay file texts so later slices never re-read the disk.

**Architecture:** One new `TaskManifest` field plus validation in `load_manifest` (`src/satyrn_evals/manifest.py`), a session-prompt name check in `session_manifest.py`, and the `session-mechanics` bundle flagged hidden. No CLI changes; all failures are existing `SatyrnError` subclasses so exit codes are unchanged.

**Tech:** Python ≥3.14, pytest, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-04-v7-task-visibility-leak-detection-design.md` (§1 governs this plan; the plan argues from the spec, executors read both).

## Global Constraints

- Default tier tests: no model, no network, no subprocess — the planted tripwire (`tests/test_tripwire.py`) fails the build otherwise.
- Every refusal test has a success sibling (BRIEF rule 6).
- House style: semantic `type` aliases via `type` statements; `match`/`case` for dispatch; `:=` for bind-and-test; full annotations on every function.
- Exit codes unchanged: manifest/session-spec violations are `UsageError` subclasses → exit 2 (`src/satyrn_evals/errors.py:26-31`).
- Verify with `.venv/bin/pytest -q` and `ruff check .` at every task end.

---

### Task 1: The `oracle_visibility` field with the ⇔ rule

**Files:**
- Modify: `src/satyrn_evals/manifest.py`
- Test: `tests/test_manifest.py`

**Interfaces:**
- Consumes: existing `TaskManifest` (`manifest.py:18-27`), `ManifestError`.
- Produces: `type OracleVisibility = Literal["visible", "hidden"]` (module level, exported); `TaskManifest.oracle_visibility: OracleVisibility = "visible"`; `load_manifest` enforces the ⇔ rule.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_manifest.py` (self-contained task dirs; follow the file's existing tmp_path manifest pattern if it has a helper — otherwise this literal form):

```python
def _write_task(tmp_path, *, visibility=None, overlay=True):
    """Minimal hidden-oracle task dir; caller adds visibility/overlay as needed."""
    task = tmp_path / "task"
    (task / "base").mkdir(parents=True)
    if overlay:
        (task / "grader" / "overlay").mkdir(parents=True)
        (task / "grader" / "overlay" / "tests" / "t_hidden.py").write_text("def test_x():\n    assert True\n")
    data = {
        "name": "task",
        "contract": "do the thing",
        "oracle": ["python", "-m", "pytest"],
        "expected_test_ids": ["tests/t_hidden.py::test_x"],
        "source_paths": ["src"],
        "fixtures": {"known_good": "fixtures/kg.patch"},
    }
    if visibility is not None:
        data["oracle_visibility"] = visibility
    (task / "manifest.json").write_text(json.dumps(data))
    (task / "fixtures").mkdir()
    (task / "fixtures" / "kg.patch").write_text("")
    return task


def test_hidden_without_overlay_refused(tmp_path):
    task = _write_task(tmp_path, visibility="hidden", overlay=False)
    with pytest.raises(ManifestError, match="hidden oracle requires grader_overlay"):
        load_manifest(task)


def test_hidden_with_overlay_loads_visible_by_default(tmp_path):
    task = _write_task(tmp_path)
    assert load_manifest(task).oracle_visibility == "visible"  # key absent


def test_overlay_without_hidden_refused(tmp_path):
    task = _write_task(tmp_path, visibility="visible")
    with pytest.raises(ManifestError, match="grader_overlay requires a hidden oracle"):
        load_manifest(task)


def test_hidden_with_overlay_declares_hidden(tmp_path):
    task = _write_task(tmp_path, visibility="hidden")
    assert load_manifest(task).oracle_visibility == "hidden"


def test_invalid_visibility_value_refused(tmp_path):
    task = _write_task(tmp_path, visibility="secret")
    with pytest.raises(ManifestError, match="oracle_visibility"):
        load_manifest(task)


def test_bundled_tasks_default_visible():
    for name in ("format_number", "local-pings"):
        manifest = load_manifest(DEFAULT_TASKS_ROOT / name)
        assert manifest.oracle_visibility == "visible"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_manifest.py -k visibility -q`
Expected: FAIL — `TaskManifest` has no `oracle_visibility`; the ⇔ refusals do not exist.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/manifest.py`:

```python
type OracleVisibility = Literal["visible", "hidden"]
```

(add `Literal` to the `typing` import). Extend the dataclass:

```python
@dataclass(frozen=True)
class TaskManifest:
    ...
    grader_overlay: str | None = None
    oracle_visibility: OracleVisibility = "visible"
```

In `load_manifest`, after `engine_contract = _validate_engine_contract(...)`:

```python
    visibility_raw = data.get("oracle_visibility", "visible")
    if visibility_raw not in ("visible", "hidden"):
        raise ManifestError(
            f"oracle_visibility must be 'visible' or 'hidden', got {visibility_raw!r}"
        )
    visibility: OracleVisibility = visibility_raw
    # grader_overlay was resolved earlier via _validate_grader_overlay into
    # the local `grader_overlay`; match against that resolved value.
    match (visibility, grader_overlay):
        case ("hidden", None):
            raise ManifestError("hidden oracle requires grader_overlay")
        case ("visible", str()):
            raise ManifestError("grader_overlay requires a hidden oracle")
        case _:
            pass
```

Pass `oracle_visibility=visibility` into the `TaskManifest(...)` constructor call.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_manifest.py -q`
Expected: PASS (new tests and all existing manifest tests).

- [ ] **Step 5: Lint and commit**

```bash
ruff check src/satyrn_evals/manifest.py tests/test_manifest.py
git add src/satyrn_evals/manifest.py tests/test_manifest.py
git commit -m "feat: manifest oracle_visibility with the hidden-overlay equivalence rule"
```

---

### Task 2: Authoring-time overlay-name check (contract)

**Files:**
- Modify: `src/satyrn_evals/manifest.py`
- Test: `tests/test_manifest.py`

**Interfaces:**
- Consumes: `OverlaySpec`-style tree listing (plain `Path.rglob`, no overlay loading).
- Produces: hidden-task manifests whose `contract` names an overlay path are refused with `ManifestError`. Candidate names pinned: the overlay root's task-relative path (`grader/overlay`), and each overlay file's overlay-root-relative (`tests/t_hidden.py`) and task-relative (`grader/overlay/tests/t_hidden.py`) paths.

- [ ] **Step 1: Write the failing tests**

```python
def test_hidden_contract_naming_overlay_path_refused(tmp_path):
    task = _write_task(tmp_path, visibility="hidden")
    data = json.loads((task / "manifest.json").read_text())
    data["contract"] = "make tests/t_hidden.py pass"
    (task / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="contract names grader-only path"):
        load_manifest(task)


def test_hidden_contract_without_overlay_name_loads(tmp_path):
    task = _write_task(tmp_path, visibility="hidden")
    manifest = load_manifest(task)
    assert manifest.oracle_visibility == "hidden"


def test_visible_task_may_name_any_path(tmp_path):
    task = _write_task(tmp_path, visibility=None, overlay=False)
    data = json.loads((task / "manifest.json").read_text())
    data["contract"] = "make tests/t_hidden.py pass"
    (task / "manifest.json").write_text(json.dumps(data))
    assert load_manifest(task).contract.startswith("make tests")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_manifest.py -k naming -q`
Expected: FAIL — no such check exists.

- [ ] **Step 3: Implement**

In `manifest.py`, a module function:

```python
def _overlay_declared_names(task_dir: Path, overlay_root: str) -> tuple[str, ...]:
    """Names whose appearance in authored text leaks a hidden oracle."""
    names = [overlay_root]
    root = task_dir / overlay_root
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            names.append(rel)
            names.append(f"{overlay_root}/{rel}")
    return tuple(names)


def _assert_contract_names_no_overlay(
    task_dir: Path, contract: str, overlay_root: str | None
) -> None:
    if overlay_root is None:
        return
    for name in _overlay_declared_names(task_dir, overlay_root):
        if name in contract:
            raise ManifestError(
                f"contract names grader-only path: {name} "
                "(hidden oracle; the docstring limit is: a paraphrase passes)"
            )
```

Call it in `load_manifest` after the ⇔ rule with the resolved `grader_overlay` value. Docstring carries the limitation verbatim (exact, case-sensitive substring; a paraphrase passes).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_manifest.py -q`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
ruff check src/satyrn_evals/manifest.py tests/test_manifest.py
git add src/satyrn_evals/manifest.py tests/test_manifest.py
git commit -m "feat: hidden-task contract must not name overlay paths"
```

---

### Task 3: Session-prompt name check, and `session-mechanics` flagged hidden

**Files:**
- Modify: `src/satyrn_evals/session_manifest.py`, `src/satyrn_evals/tasks/session-mechanics/manifest.json`
- Test: `tests/test_session_manifest.py`, `tests/test_session_mechanics_fixture.py`

**Interfaces:**
- Consumes: `SessionSpec.steps[].prompt` (`session_manifest.py:25-31`), `TaskManifest.oracle_visibility` and the Task 2 candidate-names helper.
- Produces: `assert_no_overlay_names(spec: SessionSpec, manifest: TaskManifest, task_dir: Path) -> None`, raising `SessionSpecError`; called by `session.py` (P4 wires the call site; here it exists and is unit-tested).

- [ ] **Step 1: Write the failing tests**

In `tests/test_session_manifest.py` (reuse the file's existing spec-loading fixtures; the shape below is self-contained if none fits):

```python
def test_prompt_naming_overlay_path_refuses(tmp_path, hidden_task):
    spec = load_session_spec(hidden_task)  # existing helper or built inline
    manifest = load_manifest(hidden_task)
    with pytest.raises(SessionSpecError, match="prompt names grader-only path"):
        assert_no_overlay_names(spec, manifest)


def test_clean_prompts_pass(tmp_path, hidden_task):
    spec = load_session_spec(hidden_task)
    manifest = load_manifest(hidden_task)
    assert_no_overlay_names(spec, manifest)  # does not raise
```

In `tests/test_session_mechanics_fixture.py`:

```python
def test_session_mechanics_declares_hidden():
    manifest = load_manifest(DEFAULT_TASKS_ROOT / "session-mechanics")
    assert manifest.oracle_visibility == "hidden"
    assert manifest.grader_overlay == "grader/overlay"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_session_manifest.py tests/test_session_mechanics_fixture.py -q`
Expected: FAIL — `assert_no_overlay_names` undefined; the fixture manifest lacks the key.

- [ ] **Step 3: Implement**

In `session_manifest.py`:

```python
def assert_no_overlay_names(
    spec: SessionSpec, manifest: TaskManifest, task_dir: Path
) -> None:
    """Refuse a session whose prompts name a hidden overlay path.

    Exact, case-sensitive substring check — a tripwire for the mistake
    that actually happened (a prompt naming the grader), not a proof of
    ignorance; a paraphrase passes.
    """
    if manifest.oracle_visibility != "hidden" or manifest.grader_overlay is None:
        return
    from satyrn_evals.manifest import _overlay_declared_names

    names = _overlay_declared_names(task_dir, manifest.grader_overlay)
    for step in spec.steps:
        for name in names:
            if name in step.prompt:
                raise SessionSpecError(
                    f"prompt {step.id!r} names grader-only path: {name}"
                )
```

(Callers that already hold the task dir pass it — `session.py`'s `run_session` loads both spec and manifest beside `task_dir` and will call this in P4's wiring. Edit `tasks/session-mechanics/manifest.json` to add `"oracle_visibility": "hidden"`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_session_manifest.py tests/test_session_mechanics_fixture.py tests/test_manifest.py -q`
Expected: PASS.

- [ ] **Step 5: Full default tier, lint, commit**

```bash
.venv/bin/pytest -q && ruff check .
git add -u
git commit -m "feat: session prompts refuse hidden-overlay names; session-mechanics declares hidden"
```

---

### Task 4: `OverlaySpec` carries overlay file texts

**Files:**
- Modify: `src/satyrn_evals/overlay.py`
- Test: `tests/test_overlay.py`

**Interfaces:**
- Consumes: `load_overlay` (`overlay.py:34-62`) — it already reads every file's bytes for its digest.
- Produces: `OverlaySpec.texts: dict[str, str]` — overlay-root-relative path → decoded file text. Every later slice reads `spec.texts`, never the disk.

- [ ] **Step 1: Write the failing tests**

In `tests/test_overlay.py` (reuse the file's existing overlay-tree fixture; if it builds task dirs with `tmp_path`, extend that builder):

```python
def test_overlay_spec_carries_texts(overlay_task):
    manifest = load_manifest(overlay_task)
    spec = load_overlay(overlay_task, manifest)
    assert set(spec.texts) == set(spec.rel_paths)
    assert "def test_x" in spec.texts[spec.rel_paths[0]]


def test_overlay_spec_refuses_non_utf8_file(overlay_task):
    bad = overlay_task / "grader" / "overlay" / "tests" / "bad.py"
    bad.write_bytes(b"\xff\xfe not utf-8")
    manifest = load_manifest(overlay_task)
    with pytest.raises(OverlayError, match="must be UTF-8 text"):
        load_overlay(overlay_task, manifest)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_overlay.py -k texts -q`
Expected: FAIL — `OverlaySpec` has no `texts`.

- [ ] **Step 3: Implement**

In `overlay.py`, extend the dataclass and loader:

```python
@dataclass(frozen=True, slots=True)
class OverlaySpec:
    root: Path
    rel_paths: tuple[str, ...]
    digests: dict[str, str]
    texts: dict[str, str]
```

In `load_overlay`'s file loop, where `data = path.read_bytes()` already happens:

```python
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OverlayError(
                f"grader overlay file must be UTF-8 text: {rel}"
            ) from exc
        texts[rel] = text
```

and pass `texts=texts` to the constructor. `load_overlay` is the only construction site; update it and nothing else.

- [ ] **Step 4: Run to verify pass, lint, commit**

Run: `.venv/bin/pytest tests/test_overlay.py -q`
Expected: PASS.

```bash
ruff check src/satyrn_evals/overlay.py tests/test_overlay.py
git add src/satyrn_evals/overlay.py tests/test_overlay.py
git commit -m "feat: OverlaySpec carries overlay file texts for content detection"
```
