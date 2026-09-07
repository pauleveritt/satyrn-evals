> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V7 P4 — Session detection, cheap prevention, and workspace absence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sessions record per-checkpoint contamination findings; hidden overlays materialize read-only as defense-in-depth; the executor workspace carries **no** overlay content by construction, proven both ways; docs, glossary, and the two V7 backlog entries close out.

**Architecture:** `session.py` detects at capture time (where the cumulative patch and retained transcript prefix already exist) and annotates `StepRecord`; `overlay.py` gains the mode checks and the `assert_overlay_absent` tree walk; the two workspace builders accept an optional overlay and assert the invariant between reconstruction and command start. No CLI or exit-code changes.

**Tech:** Python ≥3.14, pytest; integration tier for real workspaces and the fake session adapter.

**Spec:** `docs/superpowers/specs/2026-09-04-v7-task-visibility-leak-detection-design.md` (§3 check (a), §4, §5, §7, §11.4, §12 slice 4 govern this plan). Plan order: P1 → P2 → P2b → P3 → P4.

## Global Constraints

- 0o444 is accidental-exposure prevention, not security isolation — the docstrings say so plainly (spec §5).
- Absence is the real invariant: a test proves the overlay is absent from the executor workspace, not merely read-only (spec §11.4).
- Detection is capture-side for sessions and still runs on scope-violated checkpoints whose hidden grading skips.
- Additive record keys: loaders tolerate absence; writers omit the key when `None` (same pattern as `write_receipt` in P3).
- Verify with `.venv/bin/pytest -q` and `ruff check .` per task; integration with `.venv/bin/pytest -m integration -q tests/integration/...`.

---

### Task 1: Cheap prevention — materialization modes and the stored-file check

**Files:**
- Modify: `src/satyrn_evals/overlay.py`
- Test: `tests/test_overlay.py`, `tests/integration/test_grade_overlay.py` (integration sibling for a real materialization)

**Interfaces:**
- Produces: `materialize_overlay` chmods every written file `0o444` after digest verification; `load_overlay` refuses any overlay file with group/other write bits (`mode & 0o022`). Bounded by git's mode vocabulary — committed files are `100644` and pass; `666`-style storage fails.

- [ ] **Step 1: Write the failing tests**

In `tests/test_overlay.py`:

```python
def test_load_overlay_refuses_group_or_other_writable_file(overlay_task):
    bad = overlay_task / "grader" / "overlay" / "tests" / "t_hidden.py"
    bad.chmod(0o666)
    manifest = load_manifest(overlay_task)
    with pytest.raises(OverlayError, match="must not be group/other-writable"):
        load_overlay(overlay_task, manifest)


def test_load_overlay_accepts_git_default_modes(overlay_task):
    (overlay_task / "grader" / "overlay" / "tests" / "t_hidden.py").chmod(0o644)
    manifest = load_manifest(overlay_task)
    assert load_overlay(overlay_task, manifest).rel_paths  # does not raise
```

In `tests/integration/test_grade_overlay.py` (beside the existing materialization tests):

```python
def test_materialized_overlay_files_are_read_only(tmp_path, overlay_task):
    manifest = load_manifest(overlay_task)
    spec = load_overlay(overlay_task, manifest)
    work = tmp_path / "work"
    work.mkdir()
    materialize_overlay(spec, work)
    for rel in spec.rel_paths:
        assert (work / rel).stat().st_mode & 0o222 == 0
        with pytest.raises(PermissionError):
            (work / rel).write_text("overwrite")
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_overlay.py -k writable -q`
Expected: FAIL — no mode check.

- [ ] **Step 3: Implement**

In `overlay.py`'s `load_overlay` file loop (which already `lstat`s each path for the symlink check):

```python
        if stat.S_IMODE(mode) & 0o022:
            raise OverlayError(
                f"grader overlay file must not be group/other-writable: {rel} "
                "(defense-in-depth only; the real invariant is that the overlay "
                "is never materialized in executor-reachable paths)"
            )
```

In `materialize_overlay`, after the digest verification line:

```python
        target.chmod(0o444)
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_overlay.py -q && .venv/bin/pytest -m integration -q tests/integration/test_grade_overlay.py`
Expected: PASS (the bundled `session-mechanics` overlay is `100644` — git's only non-executable mode — so every existing overlay test still passes).

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/overlay.py tests/test_overlay.py tests/integration/test_grade_overlay.py
git commit -m "feat: read-only overlay modes at load and materialization, limits stated"
```

---

### Task 2: The absence invariant in both workspace builders

**Files:**
- Modify: `src/satyrn_evals/overlay.py` (tree-walking helper), `src/satyrn_evals/workspace.py` (`run_workspace` `workspace.py:900`, `prepare_session_workspace` `workspace.py:1076`), `src/satyrn_evals/attempt.py:119` call site, `src/satyrn_evals/session.py:191` call site
- Test: `tests/integration/test_session_workspace.py`

**Interfaces:**
- Consumes: `overlay_absent_from_inventory` (P2), `load_overlay` (P1), the `workspace.release()` teardown the file already uses.
- Produces: `assert_overlay_absent(tree: Path, spec: OverlaySpec) -> None` in `overlay.py` — walks the tree, digests every regular file, raises `OverlayError` naming the invariant; `run_workspace(..., overlay: OverlaySpec | None = None)` and `prepare_session_workspace(..., overlay: OverlaySpec | None = None)` call it after reconstruction, before the command/adapters can run. Callers pass the overlay exactly when `manifest.oracle_visibility == "hidden"` (both call sites already hold the manifest: `attempt.py:95-96`, `session.py:180-183`).

- [ ] **Step 1: Write the failing integration tests**

In `tests/integration/test_session_workspace.py`:

```python
def test_hidden_overlay_absent_from_executor_worktree():
    task_dir = DEFAULT_TASKS_ROOT / "session-mechanics"
    manifest = load_manifest(task_dir)
    spec = load_overlay(task_dir, manifest)
    workspace = prepare_session_workspace(
        base=task_dir / "base",
        protected_paths=(task_dir,),
        overlay=spec,
    )
    try:
        assert_overlay_absent(workspace.worktree, spec)  # does not raise
    finally:
        workspace.release()


def test_overlay_content_in_base_refuses_the_build(tmp_path):
    task_dir = tmp_path / "session-mechanics"
    shutil.copytree(DEFAULT_TASKS_ROOT / "session-mechanics", task_dir)
    # an overlay file's bytes inside base are exactly the authoring defect
    # the invariant catches (digest hit, whatever the path is named)
    shutil.copy(
        task_dir / "grader" / "overlay" / "tests" / "test_slugify.py",
        task_dir / "base" / "test_slugify.py",
    )
    manifest = load_manifest(task_dir)
    spec = load_overlay(task_dir, manifest)
    with pytest.raises((OverlayError, WorkspacePrepareError), match="overlay"):
        prepare_session_workspace(
            base=task_dir / "base", protected_paths=(task_dir,), overlay=spec
        )
```

(Expect `OverlayError`; if the builder's error handling wraps foreign errors — the session path already maps build failures to `WorkspacePrepareError`, `session.py:193` — the tuple above accepts either. After the first run, narrow the expectation to the type actually raised and note which in a one-line comment.)

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest -m integration tests/integration/test_session_workspace.py -k absent -q`
Expected: FAIL — `assert_overlay_absent` undefined; builders take no `overlay`.

- [ ] **Step 3: Implement**

In `overlay.py`:

```python
def assert_overlay_absent(tree: Path, spec: OverlaySpec) -> None:
    """Refuse an executor tree that carries overlay paths or overlay bytes.

    The real invariant behind V7's prevention requirement (spec §3 check
    (a)): read-only modes are secondary; absence is primary.
    """
    inventory: dict[str, str] = {}
    for path in sorted(tree.rglob("*")):
        if path.is_file() and not path.is_symlink():
            inventory[path.relative_to(tree).as_posix()] = sha256(
                path.read_bytes()
            ).hexdigest()
    if not overlay_absent_from_inventory(inventory, spec):
        raise OverlayError(
            "executor workspace contains overlay content "
            "(path or byte-identical file); base must never carry grader content"
        )
```

(`from satyrn_evals.contamination import overlay_absent_from_inventory` at the top of `overlay.py` — no cycle: contamination imports `OverlaySpec` under `TYPE_CHECKING` only, per P2.) In `workspace.py`, add `overlay: OverlaySpec | None = None` to both builders' keyword parameters; after the worktree is reconstructed and before the command starts (`run_workspace`) / before return (`prepare_session_workspace`):

```python
    if overlay is not None:
        assert_overlay_absent(worktree, overlay)
```

Call sites: `attempt.py` — `run_workspace(..., overlay=load_overlay(task_dir, manifest) if manifest.oracle_visibility == "hidden" else None)`; `session.py` — pass the already-loaded `overlay` variable into `prepare_session_workspace(..., overlay=overlay)`.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest -m integration tests/integration/test_session_workspace.py -q && .venv/bin/pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat: executor workspaces assert hidden-overlay absence at build time"
```

---

### Task 3: Per-checkpoint session detection on retained artifacts

**Files:**
- Modify: `src/satyrn_evals/session_record.py` (`StepRecord`), `src/satyrn_evals/session.py` (`_capture_checkpoint` `session.py:118-167`)
- Test: `tests/test_session_record.py`, `tests/integration/test_session_run.py`

**Interfaces:**
- Consumes: `scan_patch`, `scan_texts`, `payload_strings` (P2); `parse_session_line`/`EventLine` (`session_protocol.py`); the cumulative patch text and transcript prefix already captured in `_capture_checkpoint`.
- Produces: `StepRecord.contamination: dict | None = None` — same shape as the receipt key (`{"visibility": "hidden", "checks": [...]}` with (b) `grader_content_in_patch` and (c) `grader_name_in_payload`); writer omits when `None`; loader accepts records with and without the key. Detection runs whenever the session task is hidden — including scope-violated checkpoints.

- [ ] **Step 1: Write the failing tests**

In `tests/test_session_record.py`:

```python
def _record_with(contamination):
    step = StepRecord(
        step_id="s1",
        prompt_digest="d",
        outcome="settled",
        patch_path="checkpoints/00-s1.patch",
        patch_digest="p",
        patch_bytes=10,
        contamination=contamination,
    )
    return SessionRecord(
        version=1,
        task="session-mechanics",
        adapter_command=("fake",),
        base_commit="a" * 40,
        code=SessionCode.COMPLETE,
        steps=(step,),
    )


def test_step_record_contamination_round_trips(tmp_path):
    finding = {"visibility": "hidden", "checks": [
        {"check": "grader_content_in_patch", "outcome": "clean", "evidence": []},
        {"check": "grader_name_in_payload", "outcome": "unmeasured", "evidence": []},
    ]}
    path = tmp_path / "session-record.json"
    write_session_record(path, _record_with(finding))
    loaded = load_session_record(path)
    assert loaded.steps[0].contamination == finding


def test_legacy_step_record_without_contamination_loads(tmp_path):
    path = tmp_path / "session-record.json"
    write_session_record(path, _record_with(None))
    data = json.loads(path.read_text())
    del data["steps"][0]["contamination"]  # simulate a pre-V7 record on disk
    path.write_text(json.dumps(data))
    loaded = load_session_record(path)
    assert loaded.steps[0].contamination is None
```

In `tests/integration/test_session_run.py` (the fake-adapter integration pattern):

```python
def test_hidden_session_annotates_checkpoints(fake_clean_session):
    record = fake_clean_session  # run_session driven by the existing fake adapter
    for step in record.steps:
        if step.patch_path is None:
            continue
        assert step.contamination is not None
        checks = {c["check"]: c["outcome"] for c in step.contamination["checks"]}
        assert set(checks) == {"grader_content_in_patch", "grader_name_in_payload"}


def test_contaminating_step_flags_and_session_still_captures(fake_leaky_session):
    # fixture: the fake adapter's step-1 script additionally writes
    # src/textkit/_leak.py containing the first five non-blank lines of the
    # bundled grader/overlay/tests/test_slugify.py (read via load_overlay);
    # everything else is the clean-session script
    record = fake_leaky_session
    flagged = [s for s in record.steps if s.contamination and any(
        c["outcome"] == "flagged" for c in s.contamination["checks"]
    )]
    assert flagged, "the leaky step must flag"
    assert record.steps  # capture completed; detection never stops the session
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_session_record.py -q && .venv/bin/pytest -m integration tests/integration/test_session_run.py -k contamination -q`
Expected: FAIL.

- [ ] **Step 3: Implement**

`session_record.py`: add `contamination: dict | None = None` to `StepRecord`; in the loader's `StepRecord(...)` construction (`session_record.py:163`) read `contamination=raw.get("contamination")`; in `write_session_record` (`session_record.py:146-150`) replace the flat `asdict` with a dict build that drops `contamination` when `None` (mirror P3's `write_receipt`).

`session.py`: `_capture_checkpoint` gains `overlay: OverlaySpec | None` and `visibility: str` parameters; after the patch and transcript prefix are computed:

```python
    contamination = None
    if overlay is not None:
        patch_result = scan_patch(capture.patch_text, overlay)
        sources: list[tuple[str, str | None]] = []
        if transcript_path.exists():
            for line in transcript_path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines():
                try:
                    message = parse_session_line(line)
                except ProtocolError:
                    continue  # malformed lines are not retained, not claimed
                if isinstance(message, EventLine):
                    text = "\n".join(payload_strings(message.payload))
                    sources.append((f"{spec_step.id}/{message.kind}", text or None))
        payload_result = scan_texts(sources, overlay)
        contamination = {
            "visibility": visibility,
            "checks": [
                {
                    "check": result.check,
                    "outcome": result.outcome,
                    "evidence": [asdict(item) for item in result.evidence],
                }
                for result in (patch_result, payload_result)
            ],
        }
```

pass `contamination=contamination` into the `StepRecord(...)` construction, and from `run_session` pass `overlay=overlay` and `visibility=manifest.oracle_visibility` at both `_capture_checkpoint` call sites. Import `scan_patch`, `scan_texts`, `payload_strings`, `EventLine`, `parse_session_line`, and `asdict` (if not already imported).

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_session_record.py -q && .venv/bin/pytest -m integration tests/integration/test_session_run.py -q && .venv/bin/pytest -q`
Expected: PASS (the four-prompt scripted-RPC proof from V6 is untouched; its assertions do not read `contamination`).

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat: session checkpoints record contamination from retained artifacts"
```

---

### Task 4: Docs, glossary, and backlog close-out

**Files:**
- Modify: `README.md`, `docs/glossary.md`, `BACKLOG.md`, `ROADMAP.md`

**Interfaces:**
- Consumes: everything shipped in P1–P4.
- Produces: user-facing documentation; the concept-budget terms; the two backlog entries closed with their outcomes recorded in the V7 roadmap row (backlog rule 3: prune, do not archive in place).

- [ ] **Step 1: README**

Add a short section under the existing grading/usage docs: the `oracle_visibility` field and its ⇔ rule with `grader_overlay`; what a receipt's `contamination` block means (`flagged`/`clean`/`unmeasured`; detection is a verbatim tripwire; an ordinary attempt's `clean` covers the preserved patch and workspace invariant only); the summary's `cells`/`oracle_visibility`/`contamination` fields. No new CLI flags exist — say so.

- [ ] **Step 2: Glossary (close-out additions per the spec's concept budget)**

Add to `docs/glossary.md`, in the established definition style: **visible oracle**, **hidden oracle**, **contamination**, **unmeasured** (absence of signal is not cleanliness), **cell set** (the named attempt directories a summary was computed over). Cross-reference `verdict` and `preservation`.

- [ ] **Step 3: Backlog and roadmap close-out**

In `BACKLOG.md`, remove both entries — "**Cheap partial prevention**" and "**V5 evidence-provenance correction**" — their outcomes land in the V7 roadmap row: V7 required read-only modes with their stated limit, and every summary from V7 on names its cell set. In `ROADMAP.md`, move V7's row to complete in the `Now` section with the spec link and a one-line outcome; keep the row's Excludes cell (containment stays deferred — its own backlog entry survives, its "V7 uses after-the-fact content detection" sentence now points at the shipped spec). Respect all caps: `just lint-docs` must pass.

- [ ] **Step 4: Full verification, then commit**

```bash
.venv/bin/pytest -q && ruff check . && just lint-docs
git add -u
git commit -m "docs: V7 close-out — visibility and contamination documented, backlog entries closed"
```
