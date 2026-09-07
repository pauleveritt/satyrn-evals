> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V6 Plan 1 of 3 — Overlay grading and session machinery (slices 1–2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the grader-only overlay to ordinary grading, and the pure session machinery — `session.json` loader, typed records, and the adapter protocol parser — entirely in the default tier.

**Architecture:** Plan 1 of 3 for V6; `sdd.md`'s 400-line plan cap splits the phase's plan along the 2026-09-01 spec's reviewable slices. `manifest.py` gains one validated field; a new `overlay.py` validates and materializes grader-only files; `grade()` grows optional overlay/selectors parameters. Three new pure modules (`session_manifest`, `session_record`, `session_protocol`) are consumed by Plan 2's executor. Tasks 1–2 and 4–6 are default tier; **Task 3's floor tests run the real oracle and live in the integration tier** — `grade()` spawns pytest (`grade.py:79-104`) and the planted tripwire blocks spawn outside `@mark.integration` (recorded correction during execution review: no default-tier test may call `grade()`; today's `grade()` tests are `tests/integration/test_grade.py`).

**Tech Stack:** Python 3.14, `dataclasses`, `pytest`, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-03-v6-session-eval-design.md` (deltas) + `docs/superpowers/specs/2026-09-01-svcs-session-eval-design.md` (design of record: Task layout, session.json schema, Adapter protocol sections).

## Global Constraints

- Python `>=3.14`; real return annotations; `match`/`case`/walrus house style.
- Default tier: no model/network/subprocess (planted spawn tripwire).
- A refusal test has a sibling success test, always.
- The verdict comes from hook files, never stdout or exit codes.
- 100% statement+branch coverage gate: `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100`.
- `ruff check .` clean; `just lint-docs` green.

---

### Task 1: The `grader_overlay` manifest field

**Files:** Modify `src/satyrn_evals/manifest.py`; test `tests/test_manifest.py`.

**Interfaces produced:** `TaskManifest.grader_overlay: str | None` — a safe relative directory path naming an existing directory below the task dir, or `None`. Ordinary tasks unchanged (field optional).

- [x] **Step 1: Write the failing tests** (refusal + sibling):

```python
def test_manifest_accepts_grader_overlay(tmp_path: Path) -> None:
    (tmp_path / "grader" / "overlay").mkdir(parents=True)
    manifest = _write_manifest(tmp_path, {"grader_overlay": "grader/overlay"})
    assert manifest.grader_overlay == "grader/overlay"

def test_manifest_refuses_missing_grader_overlay_dir(tmp_path: Path) -> None:
    _write_manifest(tmp_path, {"grader_overlay": "grader/overlay"})  # dir absent
    with pytest.raises(ManifestError, match="grader_overlay"):
        load_manifest(tmp_path)

def test_manifest_refuses_grader_overlay_outside_task(tmp_path: Path) -> None:
    _write_manifest(tmp_path, {"grader_overlay": "../outside"})
    with pytest.raises(ManifestError, match="grader_overlay"):
        load_manifest(tmp_path)
```

- [x] **Step 2: Run** `uv run pytest tests/test_manifest.py -q` — Expected: FAIL (no such field/validation).
- [x] **Step 3: Implement** in `manifest.py`, mirroring `_validate_engine_contract` (`manifest.py:28`): validate shape (relative, no `..`, names a directory), return `None` when absent; add the field to `TaskManifest`.
- [x] **Step 4: Run** — Expected: PASS, full file green.
- [x] **Step 5: Commit** `feat: grader_overlay manifest field`.

### Task 2: Overlay validation — `overlay.py`

**Files:** Create `src/satyrn_evals/overlay.py`; test `tests/test_overlay.py`.

**Interfaces produced:**

```python
@dataclass(frozen=True, slots=True)
class OverlaySpec:
    root: Path                       # task_dir / grader_overlay
    rel_paths: tuple[str, ...]       # sorted relative file paths
    digests: dict[str, str]          # rel path -> sha256 of bytes

def load_overlay(task_dir: Path, manifest: TaskManifest) -> OverlaySpec
def materialize_overlay(spec: OverlaySpec, workspace: Path) -> None
```

Refusals (each with a valid sibling): `grader_overlay` absent-for-session is fine here (session requirement enforced in Task 4); symlink anywhere under the overlay root; a non-regular file; a rel path that overlaps any `manifest.source_paths` entry; empty overlay directory.

- [x] **Step 1: Failing tests** — one per refusal plus the valid sibling; assert `rel_paths` sorted and digests recomputable:

```python
def test_load_overlay_records_sorted_paths_and_digests(tmp_path: Path) -> None:
    _make_task_with_overlay(tmp_path, {"tests/test_hidden.py": b"def test_x(): ...\n"})
    spec = load_overlay(tmp_path, load_manifest(tmp_path))
    assert spec.rel_paths == ("tests/test_hidden.py",)
    assert spec.digests["tests/test_hidden.py"] == hashlib.sha256(
        b"def test_x(): ...\n").hexdigest()

def test_load_overlay_refuses_symlink_under_root(tmp_path: Path) -> None:
    _make_task_with_overlay(tmp_path, {"tests/test_hidden.py": b"x = 1\n"})
    (tmp_path / "grader" / "overlay" / "tests" / "link.py").symlink_to("test_hidden.py")
    with pytest.raises(OverlayError, match="symlink"):
        load_overlay(tmp_path, load_manifest(tmp_path))

def test_load_overlay_refuses_overlap_with_source_paths(tmp_path: Path) -> None:
    _make_task_with_overlay(tmp_path, {"solution.py": b"NOWHERE"}, source_paths=("solution.py",))
    with pytest.raises(OverlayError, match="source_paths"):
        load_overlay(tmp_path, load_manifest(tmp_path))
```

- [x] **Step 2: Run** — Expected: FAIL (`No module named 'satyrn_evals.overlay'`).
- [x] **Step 3: Implement** — `load_overlay` walks `root.rglob("*")` (reject symlinks via `is_symlink()` on every component), builds digests; `materialize_overlay` copies each file to `workspace / rel_path` creating parents, refusing to write outside `workspace` (reuse the containment idea from `workspace.py:262` `_contains_path`).
- [x] **Step 4: Run** — PASS. **Step 5: Commit** `feat: overlay validation and materialization`.

### Task 3: Overlay-aware grading

**Files:** Modify `src/satyrn_evals/grade.py`; test `tests/integration/test_grade_overlay.py` (integration — real oracle execution); fixture task `tests/data/overlay-task/` committed.

**Interfaces produced:** `grade(task_dir, patch_path, receipt_path, *, overlay: OverlaySpec | None = None, selectors: tuple[str, ...] = (), expected: tuple[str, ...] | None = None) -> Receipt` — defaults preserve today's signature and behavior exactly (backward compatibility is a spec requirement).

Ordering is the invariant: copy `base/` → apply patch → **then** overlay → run oracle with `selectors` appended as pytest args and `expected` (default `manifest.expected_test_ids`) given to the hook.

- [x] **Step 1: Build the test fixture task** `tests/data/overlay-task/`: `manifest.json` (`source_paths: ["solution.py"]`, `expected_test_ids`, `grader_overlay: "grader/overlay"`, oracle as in `format_number`'s manifest), `base/` (`solution.py`, `test_solution.py`), `grader/overlay/tests/test_hidden.py`, `fixtures/known-good.patch` (adds `slugify` to `solution.py`), `fixtures/known-broken.patch` (leaves `slugify` absent/broken). Commit these files.
- [x] **Step 2: Failing tests** (floor, by name):

```python
TASK = tests_data / "overlay-task"

def test_known_good_passes_with_overlay(tmp_path: Path) -> None:
    spec = load_overlay(TASK, load_manifest(TASK))
    receipt = grade(TASK, TASK / "fixtures/known-good.patch",
                    tmp_path / "receipt.json", overlay=spec,
                    selectors=("tests/test_hidden.py",))
    assert receipt.verdict is Verdict.PASS

def test_known_broken_fails_with_overlay(tmp_path: Path) -> None:
    spec = load_overlay(TASK, load_manifest(TASK))
    receipt = grade(TASK, TASK / "fixtures/known-broken.patch",
                    tmp_path / "receipt.json", overlay=spec,
                    selectors=("tests/test_hidden.py",))
    assert receipt.verdict is Verdict.FAIL

def test_grading_without_overlay_is_unchanged(tmp_path: Path) -> None:
    receipt = grade(TASK, TASK / "fixtures/known-good.patch", tmp_path / "receipt.json")
    assert receipt.verdict is Verdict.PASS  # public suite passes; overlay never copied
```

- [x] **Step 3: Run** — FAIL (`grade() got an unexpected keyword argument`): `uv run pytest tests/integration/test_grade_overlay.py -m integration -q`.
- [x] **Step 4: Implement** in `grade.py`: thread `overlay`/`selectors`/`expected` into the workspace build (`materialize_overlay` after patch application) and into `_run_oracle` (`grade.py:74`) — append `*selectors` to the pytest argv; pass `expected` through to `compute_verdict` (`verdict.py:82`).
- [x] **Step 5: Run** — PASS. **Step 6: Commit** `feat: overlay-aware grading`.

### Task 4: `session.json` loader — `session_manifest.py`

**Files:** Create `src/satyrn_evals/session_manifest.py`; test `tests/test_session_manifest.py`.

**Interfaces produced:**

```python
type StepKind = Literal["feature", "review"]

@dataclass(frozen=True, slots=True)
class SessionStep:
    id: str
    kind: StepKind
    prompt: str
    new_feature_selectors: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class SessionSpec:
    steps: tuple[SessionStep, ...]
    base_preservation_selectors: tuple[str, ...]

def load_session_spec(task_dir: Path) -> SessionSpec
```

Loader refusals (2026-09-01 spec, Task layout): file missing for a task whose manifest declares `grader_overlay`-required session shape is *not* an error here — ordinary tasks simply have no `session.json` and this function is only called for session tasks; refuse: fewer than two steps; duplicate ids; empty prompt; ids not filesystem-safe tokens (`[A-Za-z0-9._-]+`); a `feature` step with no new selector; duplicate or missing `new_feature_selectors` across the spec; empty `base_preservation_selectors`; unknown `kind`; unknown top-level keys; wrong `version`.

- [x] **Step 1: Failing tests** — refusal table + valid sibling, both real:

```python
VALID = {"version": 1, "steps": [
    {"id": "add-slugify", "kind": "feature", "prompt": "Add slugify.",
     "new_feature_selectors": ["tests/test_slugify.py"]},
    {"id": "review", "kind": "review", "prompt": "Review.",
     "new_feature_selectors": []}],
  "base_preservation_selectors": ["tests"]}

@pytest.mark.parametrize("mutate, match", [
    (lambda p: p.update(steps=VALID["steps"][:1]), "fewer than two steps"),
    (lambda p: p["steps"].__setitem__(1, {**p["steps"][0]}), "duplicate id"),
    (lambda p: p["steps"][0].update(prompt=""), "empty prompt"),
    (lambda p: p["steps"][0].update(id="bad id!"), "filesystem-safe"),
    (lambda p: p["steps"][0].update(new_feature_selectors=[]), "feature step"),
    (lambda p: p.update(base_preservation_selectors=[]), "preservation"),
    (lambda p: p["steps"][1].update(kind="chaos"), "kind"),
    (lambda p: p.update(version=2), "version"),
])
def test_session_spec_refusals(tmp_path: Path, mutate, match: str) -> None:
    payload = copy.deepcopy(VALID); mutate(payload)
    _write_session_json(tmp_path, payload)
    with pytest.raises(SessionSpecError, match=match):
        load_session_spec(tmp_path)

def test_session_spec_valid_sibling(tmp_path: Path) -> None:
    _write_session_json(tmp_path, copy.deepcopy(VALID))
    spec = load_session_spec(tmp_path)
    assert [s.id for s in spec.steps] == ["add-slugify", "review"]
    assert spec.steps[1].new_feature_selectors == ()
```
- [x] **Step 2: Run** — FAIL. **Step 3: Implement** with a `match` over the payload structure and a single `SessionSpecError(SatyrnError)`. **Step 4: Run** — PASS. **Step 5: Commit** `feat: session.json loader`.

### Task 5: Session records — `session_record.py`

**Files:** Create `src/satyrn_evals/session_record.py`; test `tests/test_session_record.py`.

**Interfaces produced:**

```python
class SessionCode(StrEnum):
    COMPLETE = "complete"; STEP_TIMEOUT = "step_timeout"; OUTPUT_LIMIT = "output_limit"
    ADAPTER_ERROR = "adapter_error"; PROTOCOL_ERROR = "protocol_error"
    SCOPE_VIOLATION = "scope_violation"; GRADE_UNAVAILABLE = "grade_unavailable"
    WORKSPACE_FAILED = "workspace_failed"; CLEANUP_FAILED = "cleanup_failed"

@dataclass(frozen=True, slots=True)
class StepRecord:
    step_id: str
    prompt_digest: str
    outcome: str                       # "settled" | "output-limit" | "agent-error"
    patch_path: str | None; patch_digest: str | None
    snapshot_path: str | None
    scope_violations: tuple[str, ...] = ()
    feature_verdict: str | None = None     # Verdict value when graded
    preservation_verdict: str | None = None
    turn_count: int = 0; tool_count: int = 0; context_events: int = 0

@dataclass(frozen=True, slots=True)
class SessionRecord:
    version: int; task: str; adapter_command: tuple[str, ...]
    base_commit: str; conversation_id: str | None
    terminal_step: str | None; code: SessionCode; message: str | None
    steps: tuple[StepRecord, ...]

def deepest_feature_milestone(spec: SessionSpec, steps: Sequence[StepRecord]) -> int
def session_outcomes(record: SessionRecord, spec: SessionSpec) -> dict[str, bool | int | str | None]
```

`session_outcomes` derives, never conflates (2026-09-01 spec, Artifacts): `all_prompts_settled`, `deepest_milestone`, `retained_nonempty_patch`, `all_scope_valid`, `last_preservation_verdict`, `grading_available`. Counts derive from retained events only.

- [x] **Step 1: Failing tests** — round-trip via `write_session_record`/`load_session_record` (JSON, fsync'd); `deepest_feature_milestone` over a 3-feature spec: settled 3 → 3; step-2 `agent-error` → 1; review step never advances (a review `StepRecord` with selectors present still yields 3). Sibling pairs per derived flag: `all_scope_valid` True vs one violation; `grading_available` True vs `GRADE_UNAVAILABLE`; `retained_nonempty_patch` with a real digest vs `None`.
- [x] **Step 2: Run** — FAIL. **Step 3: Implement** (`write_session_record` mirrors `attempt_record`'s fsync-then-atomic-replace pattern; `match` over `SessionCode` for `grading_available`). **Step 4: Run** — PASS. **Step 5: Commit** `feat: session records`.

### Task 6: Protocol parser — `session_protocol.py`

**Files:** Create `src/satyrn_evals/session_protocol.py`; test `tests/test_session_protocol.py`.

**Interfaces produced** (message shapes verbatim from the 2026-09-01 spec's "Adapter protocol" section):

```python
@dataclass(frozen=True, slots=True)
class SessionStarted: version: int; conversation_id: str
@dataclass(frozen=True, slots=True)
class EventLine: version: int; step_id: str; kind: str; payload: dict[str, object]
@dataclass(frozen=True, slots=True)
class StepFinished: version: int; step_id: str; conversation_id: str; outcome: str; message: str | None
@dataclass(frozen=True, slots=True)
class CloseLine: version: int

def parse_session_line(line: str) -> SessionStarted | EventLine | StepFinished | CloseLine
def serialize_prompt(step_id: str, text: str) -> str
def serialize_close() -> str
```

Parser refusals: malformed JSON; unknown `version`; unknown `type`; `session_started` carried by anything but the first message is the *executor's* state rule (not the parser's) — the parser refuses only structural faults; `EventLine.kind` must be one of `turn_end|tool_end|context_compacted|context_reset|other`; `StepFinished.outcome` one of `settled|output-limit|agent-error`; required fields missing/empty (`step_id`, `conversation_id`, `text`).

- [x] **Step 1: Failing tests** — round-trip each type; one refusal per rule; each with a valid sibling line.
- [x] **Step 2: Run** — FAIL. **Step 3: Implement** — `match` on `obj["type"]`; raise `ProtocolError(SatyrnError)` with the offending line retained. **Step 4: Run** — PASS. **Step 5: Commit** `feat: session protocol parser`.

### Task 7: Coverage and lint gate

- [x] Run `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100 -q` — Expected: PASS (100%).
- [x] Run `uv run ruff check .` — Expected: clean.
- [x] Commit any residue: `chore: plan-1 coverage gate`.

## Execution record (2026-09-04)

This plan is a historical planning artifact and is **not current
truth**; it predates two independent review cycles and their
corrections. Implement, then review-fix, commits on the branch
supersede individual steps here. Where this plan and the delta spec's
recorded corrections disagree, the corrections win. See
`docs/superpowers/specs/2026-09-03-v6-session-eval-design.md`
(review corrections and remediation record) and the remediation plan
`2026-09-04-v6-remediation.md`. V6 is in remediation and re-verification,
not mergeable or complete.
