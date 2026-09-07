> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V9 P2 — The attempt path: record-before-grade, CLI, default timeout

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `attempt` writes the admitted cell's record before grading (T2)
so no cell is invisible, threads the timeout into records, prints the
`GRADE_FAILED` message on the single-attempt CLI, and raises the default
attempt timeout (T14).

**Architecture:** Reorders `_finish_attempt` in `attempt.py`, adds one
stderr print in `cli.py`, bumps `DEFAULT_TIMEOUT` in `workspace.py`.
Depends on plan P1's `AttemptCode.GRADE_FAILED` and `timeout` field.

**Tech Stack:** Python >=3.14, dataclasses, stdlib only.

**Spec:** `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md`
— §1 (representation), §2 (record-before-grade), §8 (default timeout).

## Global Constraints

- **No commits.** Commits are maintainer-controlled (`docs/sdd.md`); leave
  the worktree dirty for review.
- Default-tier tests must not spawn (the planted tripwire fails the build):
  run `uv run pytest -q` and confirm green.
- A refusal-direction test gets a success sibling.
- Python ≥3.14 house style: real return-type annotations, `type` aliases,
  `match`/`case`, `:=`. Run `uv run ruff check src/satyrn_evals tests`
  after finishing a task.
- Never weaken the planted spawn tripwire, coverage gate, or doc caps.


### Task 1: `attempt` threads timeout into its records

**Files:**
- Modify: `src/satyrn_evals/attempt.py`
- Test: `tests/test_attempt.py`

**Interfaces:**
- Consumes: `AttemptRecord.timeout` from Task 2.
- Produces: every record `attempt` writes — refused and admitted — carries
  the attempt's `timeout`.

- [ ] **Step 1: Write the failing test**

The file's shared driver `_run_attempt(tmp_path, monkeypatch, patch,
transcript)` (tests/test_attempt.py:48) needs one new parameter so the
timeout is observable; add `timeout: float = 123.0` to its signature and
pass it to `attempt_module.attempt(...)`:

```python
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output,
        command=["fake-agent"], timeout=timeout,
    )
```

Then add the test:

```python
def test_refusal_record_carries_the_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The timeout is durable on refused cells too — summarize needs it."""
    record, _attempt_dir = _run_attempt(
        tmp_path, monkeypatch, None, TRANSCRIPT.encode(), timeout=123.0
    )
    assert record.code is AttemptCode.NO_PATCH
    assert record.timeout == 123.0
```

(A `patch=None` refusal never reaches grading, so no grade mock is needed
and the default tier stays subprocess-free.)

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_attempt.py -k timeout`
Expected: FAIL — `record.timeout` raises `AttributeError` (no such field).

- [ ] **Step 3: Implement**

In `src/satyrn_evals/attempt.py`:

1. `_finish_attempt` gains `timeout: float` (add the parameter and pass it
   from `attempt()`'s call site).
2. Both `AttemptRecord(...)` constructions — the refusal branch and the
   admitted branch — gain `timeout=timeout,`.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_attempt.py`
Expected: PASS.

- [ ] **Step 5: Whole default tier**

Run: `uv run pytest -q`
Expected: PASS.

### Task 2: record-before-grade (T2)

**Files:**
- Modify: `src/satyrn_evals/attempt.py`
- Test: `tests/test_attempt.py`

**Interfaces:**
- Consumes: `AttemptCode.GRADE_FAILED` (plan p1, Task 1), `AttemptRecord.timeout`
  (plan p1, Tasks 1–2).
- Produces: for an admitted cell, `attempt` writes `attempt.json` before
  calling `grade`; a grading `SatyrnError` returns a `GRADE_FAILED` record
  whose message carries the exception; success rewrites `OK` with verdict +
  receipt. `attempt()` never raises a `SatyrnError` from grading.

- [ ] **Step 1: Write the failing tests**

The two tests drive the *admitted* path — valid patch + transcript — so
they monkeypatch `attempt_module.grade` (attempt calls
`grade(task_dir, patch_path, receipt_path)`, positionally). Add the grade
doubles and tests:

```python
class _FailingGrade(Exception):
    pass


def _grade_boom(*_args, **_kwargs) -> Receipt:
    raise HookError("oracle exploded")


def _grade_pass(*_args, **_kwargs) -> Receipt:
    return Receipt(
        task="t",
        patch_digest="a" * 64,
        verdict=Verdict.PASS,
        reason="",
        evidence=None,
    )


def test_record_is_written_before_grade_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T2: a grading crash must leave a durable, loadable record."""
    monkeypatch.setattr(attempt_module, "grade", _grade_boom)
    record, attempt_dir = _run_attempt(
        tmp_path, monkeypatch, GOOD_PATCH.encode(), TRANSCRIPT.encode()
    )
    assert record.code is AttemptCode.GRADE_FAILED
    assert record.outcome is AttemptOutcome.ATTEMPTED
    assert record.verdict is None and record.receipt_path is None
    assert "oracle exploded" in record.message
    loaded = load_attempt_record(attempt_dir / "attempt.json")
    assert loaded.code is AttemptCode.GRADE_FAILED
    assert (attempt_dir / "patch.diff").exists()


def test_successful_grade_rewrites_the_record_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful grade leaves the record OK with verdict + receipt."""
    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    record, attempt_dir = _run_attempt(
        tmp_path, monkeypatch, GOOD_PATCH.encode(), TRANSCRIPT.encode()
    )
    assert record.code is AttemptCode.OK
    assert record.verdict is Verdict.PASS
    assert record.receipt_path == "receipt.json"
    loaded = load_attempt_record(attempt_dir / "attempt.json")
    assert loaded.code is AttemptCode.OK and loaded.verdict is Verdict.PASS
```

(`_run_attempt` writes patch/transcript from the workspace-env paths and
returns the cell directory; the added `timeout` parameter from Task 1
applies. Import `Receipt` from `satyrn_evals.receipt`, `HookError` from
`satyrn_evals.errors`, `load_attempt_record` from
`satyrn_evals.attempt_record`, and `Path` from `pathlib` at the top of the
test file.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_attempt.py -k "written_before_grade or rewrites_the_record"`
Expected: FAIL — a grading raise propagates today (no `GRADE_FAILED`
record on disk), and the success test's record lacks the `GRADE_FAILED`
pre-write shape or fails on the missing rewrite.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/attempt.py`, replace the admitted branch of
`_finish_attempt` (today: `receipt = grade(...)` followed by building and
writing one record at the end of the function):

```python
    base_record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.GRADE_FAILED,
        message="attempt preserved and admitted; grading did not complete",
        task=manifest.name,
        command=tuple(effective_command),
        command_exit=command_exit,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest=patch_hash,
        transcript_digest=transcript_hash,
        verdict=None,
        receipt_path=None,
        timeout=timeout,
        workspace_base_sha=workspace.base_sha,
        attempt_dir=attempt_dir.name,
    )
    write_attempt_record(attempt_dir / "attempt.json", base_record)
    try:
        receipt = grade(task_dir, patch_path, attempt_dir / "receipt.json")
    except SatyrnError as exc:
        record = dataclasses.replace(
            base_record, message=f"{base_record.message}: {exc}"
        )
        write_attempt_record(attempt_dir / "attempt.json", record)
        return record
    record = dataclasses.replace(
        base_record,
        code=AttemptCode.OK,
        message="attempt recorded and graded",
        verdict=receipt.verdict,
        receipt_path="receipt.json",
    )
    write_attempt_record(attempt_dir / "attempt.json", record)
    return record
```

Add `import dataclasses` and import `SatyrnError` from
`satyrn_evals.errors` (already partially imported there as `PatchParseError,
UsageError`). Remove the old single `AttemptRecord(...)` + write at the end
of `_finish_attempt`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_attempt.py`
Expected: PASS.

- [ ] **Step 5: Whole default tier**

Run: `uv run pytest -q`
Expected: PASS. Expect ripple in tests that asserted a grade *raise*
propagates out of `attempt` — those tests now assert the returned
`GRADE_FAILED` record instead (convert them; do not weaken assertions).

### Task 3: single-attempt CLI prints the GRADE_FAILED message

**Files:**
- Modify: `src/satyrn_evals/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `AttemptCode.GRADE_FAILED` (plan p1, Task 1).
- Produces: exit 3 with a stderr message for a returned `GRADE_FAILED`
  record (parity with the old `SatyrnError` print).

- [ ] **Step 1: Write the failing tests**

```python
def test_attempt_grade_failed_exits_3_and_prints_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
    from satyrn_evals.attempt_record import AttemptRecord

    record = AttemptRecord(
        version=1, outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.GRADE_FAILED,
        message="attempt preserved and admitted; grading did not complete: boom",
        task="t", command=("fake",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt",
        patch_digest="a" * 64, transcript_digest="b" * 64,
        verdict=None, receipt_path=None, timeout=900.0,
        workspace_base_sha="c" * 40, attempt_dir="t-1",
    )
    monkeypatch.setattr(cli_module, "attempt", lambda **kw: record)
    assert cli_module.main(["attempt", "t", "--", "cmd"]) == 3
    assert "boom" in capsys.readouterr().err
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests/test_cli.py -k grade_failed`
Expected: FAIL — nothing prints the message today.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/cli.py`'s `attempt` dispatch branch, after the
`attempt(...)` call:

```python
            if record.code is AttemptCode.GRADE_FAILED:
                print(f"satyrn-evals: {record.message}", file=sys.stderr)
```

and import `AttemptCode` from `satyrn_evals.attempt_record` (the module is
already imported for `AttemptOutcome`).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -q tests/test_cli.py`
Expected: PASS.

- [ ] **Step 5: Whole default tier**

Run: `uv run pytest -q`
Expected: PASS.

### Task 4: default attempt timeout raised (T14)

**Files:**
- Modify: `src/satyrn_evals/workspace.py`
- Test: `tests/test_attempt.py` or `tests/test_workspace.py` (value pin)

**Interfaces:**
- Produces: `DEFAULT_TIMEOUT == 900.0`; CLI help derives from it already.

- [ ] **Step 1: Write the failing test**

```python
def test_default_attempt_timeout_is_900_seconds() -> None:
    from satyrn_evals.workspace import DEFAULT_TIMEOUT

    assert DEFAULT_TIMEOUT == 900.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -q tests -k default_attempt_timeout`
Expected: FAIL — 30.0.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/workspace.py` change line 28 to:

```python
# 900 s = the corrected probes' observed per-cell ceiling (2-15 min).
# Longer paths pass --timeout explicitly.
DEFAULT_TIMEOUT = 900.0
```

- [ ] **Step 4: Run to verify it passes and nothing pinned 30**

Run: `uv run pytest -q`
Expected: PASS. Also run `grep -rn "30\.0" src/satyrn_evals/cli.py` — the
remaining `30.0` at `cli.py:236` is the session `close_timeout` default,
untouched.

- [ ] **Step 5: Gate**

Run: `uv run ruff check src/satyrn_evals tests`
Expected: clean.
