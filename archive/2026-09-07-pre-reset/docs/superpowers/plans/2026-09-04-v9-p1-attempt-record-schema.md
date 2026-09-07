> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V9 P1 — Attempt record schema: GRADE_FAILED and the timeout generation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The attempt record can represent a grading failure durably and
carries the timeout, and `attempt` writes the record before grading so no
admitted cell is ever invisible.

**Architecture:** Three mechanical changes in `attempt_record.py` and one
reordering in `attempt.py`, plus the default-timeout bump in
`workspace.py`. The policy table gains explicit verdict/receipt presence so
a new code (`GRADE_FAILED`, outcome `attempted`) can legally carry no
verdict; the record gains a `timeout` field as a new field-set generation;
`_finish_attempt` writes the admitted cell's record before calling `grade`.
No `version` bump.

**Tech Stack:** Python ≥3.14, dataclasses, StrEnum, stdlib only.

**Spec:** `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md`
— §1 (mid-batch representation), §2 (record-before-grade), §3 (timeout
generation), §8 (default timeout).

## Global Constraints

- **No commits.** Commits are maintainer-controlled (`docs/sdd.md`); leave
  the worktree dirty for review. Do not run `git commit` at any step.
- Python ≥3.14 house style: real return type annotations; `type` aliases
  for recurred shapes; `match`/`case` for dispatch over unions; `:=` for
  bind-and-test where the file already uses it.
- Default-tier tests must not spawn subprocesses (the tripwire fails the
  build); run `uv run pytest -q` and confirm green.
- A refusal-direction test always gets a success sibling.
- Never weaken the planted spawn tripwire, coverage gate, or doc caps.
- Run ruff on touched files before finishing a task
  (`uv run ruff check src/satyrn_evals tests`).

---

### Task 1: `GRADE_FAILED` with explicit verdict/receipt presence in the policy table

**Files:**
- Modify: `src/satyrn_evals/attempt_record.py` (enum, `_AttemptPolicy`,
  `_ATTEMPT_POLICIES`, `AttemptRecord.__post_init__`)
- Test: `tests/test_attempt_record.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `AttemptCode.GRADE_FAILED`; `_AttemptPolicy` gains `verdict:
  _Presence` and `receipt: _Presence` fields (private to the module);
  `AttemptRecord.__post_init__` enforces presence from the policy instead
  of from the outcome alone.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_attempt_record.py`. Task 1's records are built
without `timeout` (the field lands in Task 2, defaulting to `None`),
following the file's existing full-kwargs pattern (see
`test_legacy_marker_rejects_v4_values`, which constructs
`AttemptRecord(**values, ...)`):

```python
def test_grade_failed_policy_allows_no_verdict_or_receipt() -> None:
    """An admitted-but-ungraded cell is attempted, never refused."""
    record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.GRADE_FAILED,
        message="attempt preserved and admitted; grading did not complete",
        task="t",
        command=("fake",),
        command_exit=0,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest="a" * 64,
        transcript_digest="b" * 64,
        verdict=None,
        receipt_path=None,
        workspace_base_sha="c" * 40,
        attempt_dir="t-1",
    )
    assert record.outcome is AttemptOutcome.ATTEMPTED


def test_grade_failed_refuses_a_verdict_or_receipt() -> None:
    """A GRADE_FAILED record carrying verdict/receipt is a contradiction."""
    kwargs = dict(
        version=1, outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.GRADE_FAILED, message="m", task="t",
        command=("fake",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt",
        patch_digest="a" * 64, transcript_digest="b" * 64,
        verdict=None, receipt_path=None,
        workspace_base_sha="c" * 40, attempt_dir="t-1",
    )
    with pytest.raises(ValueError, match="verdict"):
        AttemptRecord(**{**kwargs, "verdict": Verdict.PASS})
    with pytest.raises(ValueError, match="receipt"):
        AttemptRecord(**{**kwargs, "receipt_path": "receipt.json"})
```
- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_attempt_record.py -k grade_failed`
Expected: FAIL — `AttemptCode.GRADE_FAILED` does not exist.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/attempt_record.py`:

1. Add the code to the enum (after `CLEANUP_FAILED`):

```python
    GRADE_FAILED = "GRADE_FAILED"
```

2. Extend `_AttemptPolicy` and every row. The dataclass becomes:

```python
@dataclass(frozen=True, slots=True)
class _AttemptPolicy:
    outcome: AttemptOutcome
    command_exit: _Presence
    base_sha: _Presence
    retained_path: _Presence
    artifacts: _ArtifactPolicy
    verdict: _Presence = _Presence.FORBIDDEN
    receipt: _Presence = _Presence.FORBIDDEN
```

3. Give every existing `OK`-adjacent row its presence: only
   `AttemptCode.OK` is outcome `ATTEMPTED`; add
   `_Presence.REQUIRED` for both `verdict` and `receipt` on that row. All
   refused rows keep the defaults (forbidden). Add the new row:

```python
    AttemptCode.GRADE_FAILED: _AttemptPolicy(
        AttemptOutcome.ATTEMPTED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.BOTH,
    ),
```

4. Replace the outcome-implied verdict/receipt checks in
   `AttemptRecord.__post_init__`. Keep the existing outcome-equality check
   (`if self.outcome is not policy.outcome: raise ...`) untouched, and
   replace only the block below it — the two `raise` branches that follow
   from the outcome:

```python
        if policy.verdict is _Presence.REQUIRED and self.verdict is None:
            raise ValueError(f"{self.code} requires a verdict")
        if policy.verdict is _Presence.FORBIDDEN and self.verdict is not None:
            raise ValueError(f"{self.code} requires no verdict")
        if policy.receipt is _Presence.REQUIRED and self.receipt_path is None:
            raise ValueError(f"{self.code} requires a receipt path")
        if policy.receipt is _Presence.FORBIDDEN and self.receipt_path is not None:
            raise ValueError(f"{self.code} requires no receipt path")
```

   (The old second block was `if policy.outcome is
   AttemptOutcome.ATTEMPTED: if self.verdict is None or self.receipt_path is
   None: raise ... elif self.verdict is not None or self.receipt_path is not
   None: raise`.)

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_attempt_record.py`
Expected: PASS (full file, so the refactor did not disturb existing rows).

- [ ] **Step 5: Whole default tier**

Run: `uv run pytest -q`
Expected: PASS.

### Task 2: `timeout` field, V9 field-set generation, loader

**Files:**
- Modify: `src/satyrn_evals/attempt_record.py`
- Test: `tests/test_attempt_record.py`

**Interfaces:**
- Consumes: `AttemptRecord` dataclass.
- Produces: `AttemptRecord.timeout: float | None`; `_V9_FIELDS`; loader
  accepts legacy/V4/V7-era/V9 field sets; a V9-set record with a null
  timeout is refused.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_attempt_record.py`, using the file's established
write-then-mutate pattern (`write_attempt_record` -> edit the JSON ->
re-load) and its record factories (`_attempted()`/`_refused()`); import
`replace` from `dataclasses`:

```python
def test_record_round_trips_timeout(tmp_path: Path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, replace(_attempted(), timeout=900.0))
    assert load_attempt_record(path).timeout == 900.0


def test_v9_record_requires_a_timeout_value(tmp_path: Path) -> None:
    """A V9-generation file with a null timeout is corrupt, not legacy."""
    path = tmp_path / "attempt.json"
    write_attempt_record(path, replace(_attempted(), timeout=900.0))
    data = json.loads(path.read_text())
    data["timeout"] = None
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="timeout"):
        load_attempt_record(path)


def test_legacy_set_without_timeout_still_loads(tmp_path: Path) -> None:
    """A V7-era file (no timeout key) loads with timeout None."""
    path = tmp_path / "attempt.json"
    write_attempt_record(path, replace(_attempted(), timeout=None))
    data = json.loads(path.read_text())
    assert "timeout" not in data  # None-timeout writes stay exact
    assert load_attempt_record(path).timeout is None


def test_timeout_must_be_a_positive_finite_float() -> None:
    for bad in (0.0, -1.0, float("nan"), float("inf"), 900):
        with pytest.raises(ValueError, match="timeout"):
            AttemptRecord(
                **{k: v for k, v in asdict(_refused()).items() if k != "_legacy"},
                timeout=bad,
            )
```

(The int `900` is refused because the field is float-only. If the file's
factories do not accept a full-kwargs construction, mirror the kwargs dict
of `test_legacy_marker_rejects_v4_values` instead.)
- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_attempt_record.py -k "timeout"`
Expected: FAIL — no `timeout` field.

- [ ] **Step 3: Implement**

In `attempt_record.py`:

1. Add `_V9_FIELDS = frozenset({"timeout"})` next to `_V7_FIELDS`.
2. Add the field to the dataclass, after `receipt_path` and before
   `workspace_base_sha`:

```python
    timeout: float | None = None
```

3. In `__post_init__`, after the digest checks:

```python
        if self.timeout is not None and (
            type(self.timeout) is not float
            or not math.isfinite(self.timeout)
            or self.timeout <= 0
        ):
            raise ValueError("attempt record timeout must be a positive finite float")
```

   Add `import math` at the top.

4. In `write_attempt_record`, pop a null timeout so legacy-generation
   writes stay exact (parallel to `attempt_dir`):

```python
    if data.get("timeout") is None:
        data.pop("timeout", None)
```

5. In `load_attempt_record`, grow the accepted generations and pass the
   value through:

```python
    v7_fields = v4_fields | _V7_FIELDS
    current_fields = v7_fields | _V9_FIELDS
    if fields not in {legacy_fields, v4_fields, v7_fields, current_fields}:
        ...
    ...
    if fields == current_fields and data.get("timeout") is None:
        raise ValueError("current attempt record requires a timeout")
```

   and add `timeout=data.get("timeout"),` to the `AttemptRecord(...)`
   constructor call. (Keep the existing per-field error branches; the new
   null-timeout check runs after the set membership check.)

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_attempt_record.py`
Expected: PASS.

- [ ] **Step 5: Whole default tier**

Run: `uv run pytest -q`
Expected: PASS. Fix any construction site that now trips float-only
validation (e.g. an int timeout in a test) by passing a float.