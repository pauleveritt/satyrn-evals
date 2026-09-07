> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V6 Plan 2 of 3 — Session executor and offline grading (slices 3–4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `satyrn-evals session TASK [--tasks-root DIR] [--output DIR] [--start-timeout S] [--step-timeout S] [--close-timeout S] -- ADAPTER...` — one conversation against one evolving checkout, cumulative checkpoints captured before cleanup, graded offline after confirmed teardown.

**Architecture:** Plan 2 of 3 (cap split; slices 3–4 of the 2026-09-01 spec). New `session_patch.py` (alternate-index cumulative patch), `adapter_process.py` (process-group lifecycle with deadlines), and `session.py` (the state machine). Process behavior is **marked integration tier, excluded from CI**; pure decision helpers are extracted default-tier. Consumes Plan 1's `OverlaySpec`/`grade`/`load_session_spec`/`SessionRecord`/protocol parser. A deterministic fake adapter (`tests/integration/fake_session_adapter.py`) and a minimal test session task prove the seam.

**Tech Stack:** Python 3.14, `subprocess` (integration tier), real Git (integration tier), `pytest -m integration`.

**Spec:** `docs/superpowers/specs/2026-09-03-v6-session-eval-design.md` + 2026-09-01 spec ("Checkpoint and close lifecycle", "Offline grading", "Artifacts and record").

## Global Constraints

- Same house rules as Plan 1 (annotations, match/walrus, refusal+siblings, hook-file verdicts, 100% coverage gate).
- **Capture is separate from grading, always:** patch, snapshot, transcript prefix, and step record are written and fsynced *before* the next prompt; grading reads only retained artifacts.
- The record is written for every session that starts — adapter-error and timeout terminations included; usage refusals (exit 2) write nothing.
- Integration tests run via `uv run pytest tests/integration -m integration -q`; they never run in CI.

---

### Task 1: Cumulative patch via alternate index — `session_patch.py`

**Files:** Create `src/satyrn_evals/session_patch.py`; test `tests/integration/test_session_patch.py` (integration).

**Interfaces produced:**

```python
@dataclass(frozen=True, slots=True)
class PatchCapture:
    patch_text: str            # cumulative from base; --binary --full-index
    changed_paths: tuple[str, ...]   # from full status through the alt index
    status_lines: tuple[str, ...]

def build_cumulative_patch(worktree: Path, base_commit: str) -> PatchCapture
```

Implementation (the 2026-09-01 spec's exact technique): set `GIT_INDEX_FILE` to a fresh temp file **outside** the worktree; `git read-tree <base_commit>`; `git add -N --all .`; `git diff --binary --full-index <base_commit>`; `git status --porcelain --untracked-files=all`; remove the temp index. The worktree's real index is never touched — the next prompt observes it unchanged.

- [x] **Step 1: Failing integration test** — build a real repo (reuse the clone-cache pattern from `tests/integration/test_workspace.py`), commit base, mutate: edit a tracked file, add an untracked file, delete a file, `chmod +x` one; assert the patch contains all four change classes, `changed_paths` names them, and a second `build_cumulative_patch` call is byte-identical (idempotent) and the worktree's `git status` still shows the real index clean of the temp additions.
- [x] **Step 2: Run** `uv run pytest tests/integration/test_session_patch.py -m integration -q` — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS. **Step 5: Commit** `feat: alternate-index cumulative patch`.

### Task 2: Adapter process lifecycle — `adapter_process.py`

**Files:** Create `src/satyrn_evals/adapter_process.py`; test `tests/integration/test_adapter_process.py` (integration).

**Interfaces produced:**

```python
class AdapterProcess:
    @classmethod
    def start(cls, argv: Sequence[str], cwd: Path, *, start_timeout: float) -> AdapterProcess
    def read_line(self, timeout: float) -> str          # raises AdapterTimeout on deadline
    def send_line(self, line: str, timeout: float) -> None
    def close_stdin(self) -> None
    def terminate_and_reap(self, timeout: float) -> None # process group; raises CleanupError
```

Started with `start_new_session=True` (own process group). `terminate_and_reap` escalates: SIGTERM group → wait → SIGKILL group → wait; raises `_CleanupError` if any descendant survives, retaining the recovery path (`WORKSPACE_FAILED`/`CLEANUP_FAILED` semantics). Spooling rule: **every raw line read is appended to the transcript file and fsynced before parsing** — the executor owns this ordering, not the process class; the class returns raw lines only.

- [ ] **Step 1: Failing integration tests** — start an echo adapter; read its banner within deadline; `read_line` raises `AdapterTimeout` on a silent adapter; `terminate_and_reap` reaps a process that spawned a grandchild (the V4 descendant rule); a `CleanupError` sibling when the script traps SIGTERM and ignores SIGKILL is *not* testable portably — instead assert the escalation path issues SIGKILL (script writes a marker file only if SIGKILLed).
- [x] **Step 2: Run** — FAIL. **Step 3: Implement** with `os.killpg`; deadlines via `select.select` on stdout. **Step 4: Run** — PASS. **Step 5: Commit** `feat: adapter process lifecycle`.

### Task 3: Fake session adapter and minimal test task

**Files:** Create `tests/integration/fake_session_adapter.py`; create `tests/integration/data/mini-session/` (manifest + `session.json` + `base/` + `grader/overlay/` + fixtures, mirroring `tests/data/overlay-task` plus session fields); test wiring in later tasks.

**Behavior:** scenario from `sys.argv[1]`: `clean` (settled per step, emits `turn_end`/`tool_end`/one `compaction`-kind event, edits a file per step), `scope` (also writes `outside.txt`), `wrong-id` (changes `conversation_id` at step 2), `output-limit` (`step_finished` outcome `output-limit` at step 2), `hang` (never answers step 2). First message: `session_started` with a fixed id.

- [x] **Step 1: Write the adapter** (deterministic, no network, no model; ~60 lines of scripted `print(json.dumps(...), flush=True)` + file edits relative to cwd).
- [x] **Step 2: Wire the mini-session task** — 2 feature steps + 1 review; selectors resolve in the overlaid task.
- [x] **Step 3: Commit** `test: fake session adapter and mini-session task` (with the capture-loop commit).

### Task 4: The executor — capture loop

**Files:** Create `src/satyrn_evals/session.py`; test `tests/integration/test_session_run.py` (integration).

**Interfaces produced:**

```python
def run_session(
    task: str, tasks_root: Path, output: Path, adapter_command: Sequence[str],
    *, start_timeout: float = 60.0, step_timeout: float = 600.0,
    close_timeout: float = 30.0, grader: SessionGrader | None = None,
) -> SessionRecord
```

State machine per the 2026-09-01 lifecycle, with Plan 1 types:

```python
spec = load_session_spec(task_dir)
overlay = load_overlay(task_dir, manifest)
ws = allocate_session_workspace(task_dir, output)   # V4 lifecycle; NOT a fork
proc = AdapterProcess.start(adapter_command, ws.worktree, start_timeout=start_timeout)
first = parse_session_line(proc.read_line(start_timeout))   # spool raw line first
match first:  # session_started or PROTOCOL_ERROR
    case SessionStarted(version=1, conversation_id=cid): ...
# per step: send serialize_prompt -> read/spool lines until StepFinished for
# that step; only "settled" permits the next prompt; anything else stops:
#   timeout -> terminate_and_reap before snapshot (V4 ordering: no late
#   descendant mutates a patch after its digest is recorded)
# checkpoint: build_cumulative_patch -> write patch file -> fsync -> digest
#   -> snapshot_tree -> write snapshot -> write transcript prefix ->
#   write step record atomically (unchanged tree still gets patch + digest)
# after last step: serialize_close(); adapter exits 0 within close_timeout
#   else ADAPTER_ERROR with bounded group teardown
```

Refusal/stop mapping: timeout → `STEP_TIMEOUT`; `output-limit` → `OUTPUT_LIMIT`; adapter exit/EOF pre-terminal → `ADAPTER_ERROR`; parser/state faults (second `session_started`, changed identity, context reset, wrong/duplicate step, unknown version/type) → `PROTOCOL_ERROR`; workspace allocation failure → `WORKSPACE_FAILED`; unconfirmed reap → `CLEANUP_FAILED` — in all captured cases the session record is still finalized and written (normative). Counts (`turn_count`, `tool_count`, `context_events`) derive from retained `EventLine`s — the terminal message supplies no totals.

- [x] **Step 1: Failing integration tests** — concrete core (remaining scenarios follow the same shape):

```python
def test_clean_session_captures_three_checkpoints(tmp_path: Path) -> None:
    record = run_session("mini-session", TASKS_ROOT, tmp_path,
                         [str(FAKE_ADAPTER), "clean"])
    assert record.code is SessionCode.COMPLETE
    assert len(record.steps) == 3
    assert len({s.prompt_digest for s in record.steps}) == 3
    assert all(s.patch_digest for s in record.steps)   # unchanged tree still captured
    assert record.steps[0].tool_count >= 1             # derived from retained events

def test_scope_violation_stops_and_retains(tmp_path: Path) -> None:
    marker = tmp_path / "later-prompt-marker"
    record = run_session("mini-session", TASKS_ROOT, tmp_path,
                         [str(FAKE_ADAPTER), "scope", "--marker", str(marker)])
    assert record.code is SessionCode.COMPLETE      # safely captured and graded
    assert record.steps[-1].scope_violations        # retained as evidence
    assert not marker.exists()                      # no prompt after the violation
```

`wrong-id` asserts `PROTOCOL_ERROR` and a parseable finalized record; `output-limit` asserts `OUTPUT_LIMIT` with the captured first checkpoint still on disk; `hang` asserts `STEP_TIMEOUT` and that the patch digest was recorded *after* reap (fake adapter writes a post-kill file; assert it is absent from the snapshot). Plus a start-refusal sibling (missing adapter binary → recorded refusal, nothing graded).
- [x] **Step 2: Run** — FAIL. **Step 3: Implement** (`session.py`; workspace allocation reuses `workspace.py`'s private-repo + detached-worktree lifecycle exactly — extract shared helpers, do not fork).
- [x] **Step 4: Run** — PASS. **Step 5: Commit** `feat: session capture loop` (corrections recorded in the commit).

### Task 5: The grader stage and record finalization

**Files:** Modify `src/satyrn_evals/session.py`; test `tests/integration/test_session_grading.py` (integration).

**Interfaces produced:**

```python
@dataclass(frozen=True, slots=True)
class CheckpointArtifacts:
    step_id: str; patch_path: Path; snapshot_path: Path
    transcript_prefix_path: Path; record: StepRecord

@dataclass(frozen=True, slots=True)
class GradedSession:
    feature_verdicts: dict[str, str]          # step id -> Verdict value
    preservation_verdict: str | None          # last captured checkpoint only
    graded_steps: tuple[str, ...]             # steps whose hidden grading ran

@dataclass(frozen=True, slots=True)
class SessionGrader:
    """Grades retained checkpoint patches after teardown; pure offline reads."""
    def grade_session(self, spec: SessionSpec, overlay: OverlaySpec,
                      checkpoints: Sequence[CheckpointArtifacts]) -> GradedSession
```

Rules (2026-09-01, "Offline grading"): runs only after `terminate_and_reap`/graceful close confirmed; feature grader copies `base/`, applies the checkpoint patch, **overlays**, runs the ordered union of `new_feature_selectors` through that step (review repeats current union, never advances); preservation grader runs `base_preservation_selectors` **without** overlay on the last captured checkpoint only; a scope violation skips hidden grading for that checkpoint and is a candidate failure, not unavailability; collection error/missing hook result → verdict `unavailable` → `GRADE_UNAVAILABLE` only when grading itself is unavailable, never for model failure. Receipts keep `feature_verdict`/`base_preservation_verdict` separate; final pass requires all settled + last feature selection pass + preservation pass + all checkpoints scope-valid.

- [ ] **Step 1: Failing integration tests** — `clean` mini-session: every checkpoint graded, last-checkpoint preservation receipt present and separate; `scope`: hidden grading skipped for the violating checkpoint, patch retained in evidence; a corrupted hook-result sibling: `unavailable`, not `fail`. Assert the finalized `SessionRecord` fields fill (`feature_verdict`, `preservation_verdict`, `scope_violations`) and `session_outcomes` matches.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement** — compose Plan 1's `grade(...)` per checkpoint in fresh workspaces; delete grader workspaces after reading receipts (verdicts retained).
- [ ] **Step 4: Run** — PASS. **Step 5: Commit** `feat: session offline grading`.

### Task 6: CLI `session` branch and exit codes

**Files:** Modify `src/satyrn_evals/cli.py`; test `tests/test_cli.py` (default tier, monkeypatched `run_session`) + `tests/integration/test_session_cli.py`.

- [ ] **Step 1: Failing tests** — `session TASK -- anything` usage refusal (no `--`) → exit 2, nothing written; monkeypatched `run_session` returning `code=COMPLETE` → exit **0**; `SCOPE_VIOLATION` → still 0 (safely captured and graded); `GRADE_UNAVAILABLE`/`WORKSPACE_FAILED`/`CLEANUP_FAILED` → 3. Flags: `--tasks-root --output --start-timeout --step-timeout --close-timeout`.
- [x] **Step 2: Run** — FAIL. **Step 3: Implement** — mirror the `attempt`/`run` dispatch (`cli.py:64-93`), one `match` over `SessionCode` for the coarse status. **Step 4: Run** — PASS. **Step 5: Commit** `feat: session CLI`.
- [ ] **Step 6: Coverage gate** — `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100 -q` and `uv run pytest tests/integration -m integration -q`; commit residue `chore: plan-2 gates`.

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
