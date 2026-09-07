> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V6 Plan 3 of 3 — Session fixture, Pi adapter, integration proof, smoke (slice 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The bundled `session-mechanics` grader fixture, the shipped Python Pi adapter derived from official Pi RPC docs, the all-four-prompt scripted-RPC integration proof, the byte-for-byte svcs probe import, and the real-model smoke runbook.

**Architecture:** Plan 3 of 3 (cap split; 2026-09-01 slice 5 as replaced by the V6 delta spec's Delta 1). The adapter is a console-script executable (`satyrn-evals-session-pi`) that maps Pi RPC events to the session JSONL protocol; its mapping is a pure, default-tier-tested function; its process behavior is proven in the marked integration tier against a scripted RPC fixture standing in for Pi (the V4 substitution). The smoke is manual and uncounted — never automated, never CI.

**Tech Stack:** Python 3.14, `pi --mode rpc --no-session` (pi **0.84.4** — re-verify when pinning), subprocess (integration tier), pytest.

**Spec:** `docs/superpowers/specs/2026-09-03-v6-session-eval-design.md` (Deltas 2–5) + 2026-09-01 spec (protocol) + pi `docs/rpc.md` (`:9-31` mode/protocol, `:1526-1532` Python client).

## Global Constraints

- Same house rules as Plans 1–2.
- The fixture is a **grader fixture**: mechanics only; no admission, difficulty, or model-quality claim.
- No `engine_contract` in the fixture — its adapter protocol needs none; it avoids a second instance of the already-fired validation trigger.
- **No compatibility shim:** the adapter builds `pi` argv in space form (`--model VALUE`, never `--model=VALUE` — the recorded equals-form defect). If the smoke needs a shim, that is a failed stock-adapter proof, recorded as such.

---

### Task 1: The `session-mechanics` fixture task

**Files:** Create `src/satyrn_evals/tasks/session-mechanics/{manifest.json,session.json,base/**,grader/overlay/**,fixtures/*}`; tests `tests/test_session_mechanics_fixture.py` (default tier: manifest/shape assertions) and `tests/integration/test_session_mechanics_fixture.py` (integration — the grade() floor, per Plan 1's recorded correction).

**Contents:**

- `base/`: `pyproject.toml` (`[tool.pytest.ini_options] pythonpath = ["src"]`), `src/textkit/__init__.py` with existing functions (`normalize`, `wrap`), `tests/test_textkit.py` (public tests for those two only).
- `grader/overlay/`: `tests/test_slugify.py`, `tests/test_truncate.py`, `tests/test_pluralize.py` — one hidden module per milestone; each milestone's module imports and tests only functions that exist once its step is done.
- `session.json`: steps `add-slugify` (feature), `add-truncate` (feature), `add-pluralize` (feature), `review-and-regression` (review, no new selectors); `base_preservation_selectors: ["tests"]`.
- `manifest.json`: as `format_number`'s shape minus `engine_contract`, plus `"grader_overlay": "grader/overlay"`; `source_paths: ["src/textkit/__init__.py"]`; `fixtures` as usual.
- `fixtures/known-good.patch`: the complete three-function patch; `fixtures/known-broken.patch`: milestone-1-only. Generate both by committing successive states on a throwaway clone of `base/` and `git diff`ing from base — commit the resulting patch files.

- [x] **Step 1: Write the fixture files** exactly as above.
- [x] **Step 2: Failing tests** — default tier: manifest/shape assertions (`grader_overlay` set, `engine_contract` absent, session.json loads, overlay validates). Integration tier — floor, by name (consumes Plan 1; `TASK = Path("src/satyrn_evals/tasks/session-mechanics")`):

```python
TASK = Path("src/satyrn_evals/tasks/session-mechanics")

def test_known_good_passes_every_cumulative_milestone(tmp_path: Path) -> None:
    spec, overlay = load_session_spec(TASK), load_overlay(TASK, load_manifest(TASK))
    for step in (s for s in spec.steps if s.kind == "feature"):
        receipt = grade(TASK, TASK / "fixtures/known-good.patch",
                        tmp_path / "r.json", overlay=overlay,
                        selectors=cumulative_selectors(spec, step),  # helper in this test module
                        expected=spec_selectors(spec, step))
        assert receipt.verdict is Verdict.PASS

def test_known_broken_fails_milestones_two_and_three(tmp_path: Path) -> None:
    spec, overlay = load_session_spec(TASK), load_overlay(TASK, load_manifest(TASK))
    late = [s for s in spec.steps if s.id in ("add-truncate", "add-pluralize")]
    for step in late:
        receipt = grade(TASK, TASK / "fixtures/known-broken.patch",
                        tmp_path / "r.json", overlay=overlay,
                        selectors=cumulative_selectors(spec, step),
                        expected=spec_selectors(spec, step))
        assert receipt.verdict is Verdict.FAIL

def test_known_broken_preserves_base(tmp_path: Path) -> None:
    receipt = grade(TASK, TASK / "fixtures/known-broken.patch", tmp_path / "r.json")
    assert receipt.verdict is Verdict.PASS  # public suite intact; failure is milestone-shaped

def test_fixture_declares_no_engine_contract() -> None:
    assert load_manifest(TASK).engine_contract is None
```

Default-tier siblings (in `tests/test_session_mechanics_fixture.py`):

```python
def test_fixture_manifest_shape() -> None:
    manifest = load_manifest(TASK)
    assert manifest.grader_overlay == "grader/overlay"
    assert manifest.engine_contract is None
    spec = load_session_spec(TASK)
    assert [s.kind for s in spec.steps] == ["feature", "feature", "feature", "review"]
```

- [x] **Step 3: Run** — FAIL (fixture absent). **Step 4: Run after Step 1** — PASS. **Step 5: Commit** `feat: session-mechanics grader fixture`.

### Task 2: The Pi adapter — mapping (pure)

**Files:** Create `src/satyrn_evals/adapters/__init__.py`, `src/satyrn_evals/adapters/pi_session.py`; test `tests/test_pi_session_mapping.py`.

**Interfaces produced:**

```python
def map_rpc_event(obj: dict[str, object]) -> str | None
# None: line contributes no session event (e.g. message_update deltas)
# else: one session-protocol JSONL line, event kind mapped, full original
# pi event under "payload"

RPC_TO_KIND: mapping pinned to pi 0.84.4 rpc.md:
  turn_end            -> "turn_end"
  tool_execution_end  -> "tool_end"
  compaction_start    -> "context_compacted"
  compaction_end      -> "context_compacted"
  agent_settled       -> terminal: step_finished outcome "settled"
```

The adapter's own output lines carry the active `step_id` and the `conversation_id` from `session_started`. `agent_end` with `willRetry: true` emits nothing. Terminal mapping for model-runtime failure surfaces: the adapter maps a pi error terminal to `step_finished` `outcome: "agent-error"`; it never infers an output limit pi did not declare (2026-09-01: Evals does not infer a token limit from prose).

- [ ] **Step 1: Failing tests** — canned RPC lines from `rpc.md`'s event examples: each mapped kind asserted, `payload` byte-equal to the input object; `message_update` → `None`; unknown event → `None` (spooled, not dropped); malformed line → `PROTOCOL_ERROR` raised with the line retained (siblings for every mapping row).
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement** the pure mapping + `main()` skeleton (read stdin lines, write mapped lines to stdout, `flush=True`; state: current `step_id`, `conversation_id`). **Step 4: Run** — PASS. **Step 5: Commit** `feat: pi session adapter mapping`.

### Task 3: The Pi adapter — process behavior and argv

**Files:** Modify `src/satyrn_evals/adapters/pi_session.py`; test `tests/integration/test_pi_session_process.py` (integration).

**Behavior:** `main()` parses its own invocation (`--provider P --model M [--pi-bin PATH]`), then spawns `pi --mode rpc --no-session --provider P --model M` (**space form**; never equals form), forwarding: session JSONL `prompt` in → RPC `{"id": "...", "type": "prompt", "message": ...}` out; RPC events in → mapped session lines out; `agent_settled` → `step_finished` (settled) → wait for next prompt; session `close` in → RPC shutdown → adapter stdout closed, exit 0.

- [ ] **Step 1: Failing integration test against the scripted fixture** (Task 4): two prompts through the real adapter + one close; assert one `conversation_id` — the fixture echoes a session-scoped identity — and clean exit 0 within timeout.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement** process wiring; assert in a default-tier test that the built argv uses space form (unit test on the argv builder: no `--model=` token anywhere). **Step 4: Run** — PASS. **Step 5: Commit** `feat: pi adapter process`.

### Task 4: Scripted RPC fixture and the four-prompt integration proof

**Files:** Create `tests/integration/fake_pi_rpc.py`; test `tests/integration/test_pi_session_four_prompts.py` (integration).

**Fixture:** a deterministic stand-in for Pi speaking `rpc.md`'s wire protocol: accepts `prompt` commands; per prompt emits `turn_start`, `message_update` (noise), `tool_execution_end`, and — on prompts 2 and 3 — `compaction_start`/`compaction_end`; ends each prompt with `agent_settled`; echoes one fixed conversation identity; writes an **edit to the worktree** per prompt (it receives cwd via argv) so checkpoints have content; on `close`, exits 0.

- [ ] **Step 1: Failing integration test** — `run_session("session-mechanics", adapter=[satyrn-evals-session-pi, --pi-bin, fake_pi_rpc.py, ...])` through Plans 1–2's machinery; assert **all four** prompts: one `conversation_id` across all four `step_finished`s; cumulative union (checkpoint *n*'s feature selection is the union through that step — visible in the receipts' executed test ids); **review-does-not-advance** (final milestone unchanged by step 4); compaction non-vacuous (the fixture always emits it; the mapped `context_compacted` events carry the original RPC object unmodified in `payload`, and `context_events` counts them); teardown clean (no surviving process group; workspace gone).
- [ ] **Step 1b: The fixture's refusal path and sibling** — same bundled task, scripted `scope` scenario: the fixture writes outside `source_paths` on prompt 3; assert the checkpoint is retained as evidence, hidden grading skipped for it, and the record fails; the clean four-prompt run above is the sibling.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement** fixture + whatever wiring gaps it exposes (adapter/executor bugs are fixed here, not designed around). **Step 4: Run** — PASS. **Step 5: Commit** `test: four-prompt adapter integration proof`.

### Task 5: svcs probe import — byte-for-byte

**Files:** Create `docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md` (exact blob).

- [x] **Step 1: Import**

```bash
git show 577d540:docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md \
  > docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md
```

- [x] **Step 2: Verify before commit**

```bash
shasum -a 256 docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md
# -> 296a961fcb68cf66fbeef430df998d24e539bb1117a499751b9766d43915f664
```

No banner, no header, no edit of any kind inside the file — provenance lives in the V6 delta spec (Delta 5) and this commit message. **Step 3: Commit** `docs: import the svcs autowire session probe from 577d540, byte-for-byte (sha256 296a961f…)`. **Step 4: Verify after commit** with the same command on the checked-out file.

### Task 6: Smoke runbook and user documentation

**Files:** Modify `README.md` (session usage section); create `docs/session-smoke.md` (the manual runbook).

- [x] **Step 1: Write the runbook** — the V5d-consistent practice, session-side: one uncounted `session session-mechanics -- satyrn-evals-session-pi --provider … --model …` against a **durable, uniquely named** output directory (never `/tmp`); read `session-record.json` always, per-checkpoint receipts only when grading ran; plumbing-failure shapes (adapter/Pi exit before the model runs; no genuine model-stream events in retained payloads; plumbing code where model behavior was expected; receipt without verdict); **settled is not required** — any terminal state passes plumbing given a parseable record, the lifecycle-guaranteed artifacts for the prompts reached, and genuine model-stream events; if a shim was needed, record the stock-adapter proof as **failed**. State the five verification-record assertions verbatim from the delta spec.
- [x] **Step 2: README session section** — the `session` command, the fixture's mechanics-only classification, pointer to the smoke runbook and the delta spec.
- [x] **Step 3: Commit** `docs: session usage and the real-model smoke runbook`.

### Task 7: Verification record

- [x] Run and record (V4's shape, `docs/sdd.md`): `uv run pytest -q`; `uv run pytest tests/integration -m integration -q`; `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100`; `uv run ruff check .`; `just lint-docs`.
- [ ] Then — outside this plan's automation — run the smoke per the runbook against the supported Pi executable, and append the smoke section to `docs/sdd.md`'s V6 record: durable evidence path, each of the five assertions evidenced individually, the no-shim outcome, and the statement that model behavior may pass or fail with no admission, difficulty, or quality claim. Commit `docs: V6 verification record and smoke evidence`.

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
