> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V9 P3 — The summary names its arm, and run survives a failing cell

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Summary` names task/command/timeout (T4) derived from the cell
records, `compute_summary` enforces consistent identity, and `run`'s loop
survives cell-level failures and never loses the summary over completed
cells (T1).

**Architecture:** `summary.py` grows three required fields and derives them
in `compute_summary` from non-empty cells (one task, one command, one
timeout, all present). `run.py` gains a per-loop boundary: a returned
record is appended normally (a `GRADE_FAILED` cell flows through the
existing tally); an exception writes the completed-cell summary before
re-raising. Test doubles carry real task/command/timeout.

**Tech Stack:** Python ≥3.14, dataclasses, stdlib only.

**Spec:** `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md`
§1 (T1), §3 (T4). Depends on P1 (`timeout` field) and P2 (`GRADE_FAILED`
records from `attempt`).

## Global Constraints

- **No commits.** Commits are maintainer-controlled (`docs/sdd.md`); leave
  the worktree dirty.
- Default tier must not spawn: run `uv run pytest -q`; the tripwire fails
  the build on any `subprocess`/`os.exec`/etc.
- Refusal tests get success siblings. House style: real return type
  annotations; `type` aliases; `match`/`case`; `:=`.
- The 100% branch gate will flag any new `Summary` field never read — every
  field must be readable in some test. `docs/sdd.md` caps: ≤400 lines here.

---

### Task 1: `Summary` names task/command/timeout

**Files:**
- Modify: `src/satyrn_evals/summary.py` (dataclass, `compute_summary`)
- Test: `tests/test_summary.py`, `tests/test_run.py`

**Interfaces:**
- Consumes: `AttemptRecord.task/command/timeout` (P1).
- Produces: `Summary.task: str`, `Summary.command: list[str]`,
  `Summary.timeout: float` (required); `compute_summary(cells, *,
  oracle_visibility)` requires ≥1 cell and validates that all cells agree
  on task, command, and timeout and that timeout is present; a mismatch or
  absence is a `ValueError` naming the offending cells.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_summary.py`:

```python
def test_summary_names_its_arm_from_the_records() -> None:
    cells = [
        ("t-1", make_record(AttemptCode.OK, Verdict.PASS), None),
        ("t-2", make_record(AttemptCode.OK, Verdict.FAIL), None),
    ]
    summary = compute_summary(cells, oracle_visibility="visible")
    assert summary.task == "format_number"
    assert summary.command == ["fake"]
    assert summary.timeout == 123.0


def test_compute_summary_refuses_cells_without_a_timeout() -> None:
    record = dataclasses.replace(make_record(AttemptCode.OK, Verdict.PASS), timeout=None)
    with pytest.raises(ValueError, match="timeout"):
        compute_summary([("t-1", record, None)], oracle_visibility="visible")


def test_compute_summary_refuses_empty_cells() -> None:
    with pytest.raises(ValueError, match="at least one cell"):
        compute_summary([], oracle_visibility="visible")


def test_compute_summary_refuses_mixed_identity() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, command=("other",))
    with pytest.raises(ValueError, match="command"):
        compute_summary([("t-1", a, None), ("t-2", b, None)], oracle_visibility="visible")
```

(The file's `make_record` helper must gain a `timeout: float = 123.0` value
so existing constructions keep working while the new assertions hold.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_summary.py -k "arm or timeout or empty or mixed"`
Expected: FAIL — `Summary` has no `task` attribute.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/summary.py`:

1. Extend the dataclass (fields before `oracle_visibility`):

```python
    task: str
    command: list[str]
    timeout: float
```

2. Rewrite the top of `compute_summary`:

```python
def compute_summary(
    cells: Sequence[AttemptCell], *, oracle_visibility: str
) -> Summary:
    if not cells:
        raise ValueError("compute_summary requires at least one cell")
    task = cells[0][1].task
    command = cells[0][1].command
    timeout = cells[0][1].timeout
    if timeout is None:
        raise ValueError(
            f"cell {cells[0][0]} has no recorded timeout "
            "(pre-V9 record); cannot summarize"
        )
    for name, record, _ in cells[1:]:
        if record.task != task:
            raise ValueError(f"mixed tasks in cells ({task!r} vs {record.task!r} at {name})")
        if record.command != command:
            raise ValueError(f"mixed commands in cells ({name})")
        if record.timeout is None:
            raise ValueError(f"cell {name} has no recorded timeout")
        if record.timeout != timeout:
            raise ValueError(f"mixed timeouts in cells ({name})")
```

3. Pass them into the `Summary(...)` construction:

```python
        task=task,
        command=list(command),
        timeout=timeout,
```

- [ ] **Step 4: Update construction sites that pass empty cells**

`tests/test_summary.py::test_write_summary_omits_contamination_when_visible`
calls `compute_summary([], ...)` — change it to one cell and assert
`task`/`command`/`timeout` appear in the JSON instead. Any other
`compute_summary([], ...)` call is converted the same way.

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest -q tests/test_summary.py tests/test_run.py`
Expected: PASS (after fixing test constructs that asserted the old field
set — e.g. exact-JSON assertions gain the three keys).

### Task 2: run's doubles carry identity, and run still converges

**Files:**
- Modify: `tests/test_run.py` (doubles)
- Test: unchanged tests in `tests/test_run.py`

**Interfaces:**
- Consumes: Task 1's derived fields.
- Produces: a default-tier double whose records carry `task`/`command`/
  `timeout` and write `attempt.json` + `receipt.json` to disk.

- [ ] **Step 1: Update the double, then assert derivation**

Edit `tests/test_run.py`: `ok_record` gains identity parameters with
defaults so existing call sites compile, and the `_fake_attempt` wrapper
threads its `task`/`command`/`timeout` kwargs into the records **and writes
the record to disk exactly as a real attempt does** (summarize-from-disk in
P4 reads `attempt.json`, so the double must produce it):

```python
def ok_record(
    cell_name: str,
    *,
    task: str = "format_number",
    command: tuple[str, ...] = ("fake",),
    timeout: float = 123.0,
) -> AttemptRecord:
    return AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.OK,
        message="ok",
        task=task,
        command=command,
        command_exit=0,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest="a" * 64,
        transcript_digest="b" * 64,
        verdict=Verdict.PASS,
        receipt_path="receipt.json",
        timeout=timeout,
        workspace_base_sha="c" * 40,
        attempt_dir=cell_name,
    )


def _fake_attempt(receipt_text: str = '{"verdict": "pass"}'):
    """A non-spawning attempt double bound to one directory identity.

    Mirrors attempt()'s contract end to end on disk: run() hands the double
    task/output/command/timeout as keyword arguments (exactly as it calls
    attempt()), so the double creates the <task>-<stamp> directory holding
    receipt.json AND attempt.json, and returns a record whose attempt_dir
    names it.
    """

    def fake(
        *, task: str, tasks_root: Path, output: Path, command: list[str],
        timeout: float,
    ) -> AttemptRecord:
        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name(task, datetime.now(UTC))
        cell_dir = output / name
        cell_dir.mkdir()
        (cell_dir / "receipt.json").write_text(receipt_text, encoding="utf-8")
        record = ok_record(name, task=task, command=tuple(command),
                           timeout=timeout)
        write_attempt_record(cell_dir / "attempt.json", record)
        return record

    return fake
```

(Import `write_attempt_record` from `satyrn_evals.attempt_record` at the top
of the test file.)

Existing `_fake_attempt(task=..., output=..., ...)` call sites in
`tests/test_run.py` become `_fake_attempt()` — the double receives those
values from `run` at call time; a pre-binding factory is dead code.

Add one test:

```python
def test_run_summary_names_the_arm(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_module, "attempt", _fake_attempt())
    summary = run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out", command=["fake"], n=1, timeout=123.0,
    )
    assert summary.task == "format_number"
    assert summary.command == ["fake"]
    assert summary.timeout == 123.0
```

- [ ] **Step 2: Run to verify**

Run: `uv run pytest -q tests/test_run.py`
Expected: PASS.

### Task 3: run's per-cell boundary (T1)

**Files:**
- Modify: `src/satyrn_evals/run.py`
- Test: `tests/test_run.py`

**Interfaces:**
- Consumes: Task 1's `compute_summary`; P2's `GRADE_FAILED` records.
- Produces: `run()` returns a `Summary` over all n cells even when some
  cells are `GRADE_FAILED`; when `attempt()` raises (internal bug) `run`
  writes the summary over completed cells and re-raises.

- [ ] **Step 1: Write the failing tests**

```python
def test_run_counts_a_grade_failed_cell_and_continues(
    tmp_path: Path, monkeypatch
) -> None:
    """A grading failure in one cell must not discard the batch."""
    from satyrn_evals.attempt_record import AttemptCode

    calls = {"n": 0}

    def fake(**kwargs):
        calls["n"] += 1
        output = kwargs["output"]
        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name("format_number", datetime.now(UTC))
        cell = output / name
        cell.mkdir()
        if calls["n"] == 1:  # cell 1 graded OK, receipt on disk
            (cell / "receipt.json").write_text('{"verdict": "pass"}')
            record = ok_record(name)
            write_attempt_record(cell / "attempt.json", record)
            return record
        # cell 2: grading failed -- GRADE_FAILED record, no receipt
        record = replace(
            ok_record(name),
            code=AttemptCode.GRADE_FAILED,
            verdict=None,
            receipt_path=None,
            message=("attempt preserved and admitted; "
                     "grading did not complete: boom"),
        )
        write_attempt_record(cell / "attempt.json", record)
        return record

    monkeypatch.setattr(run_module, "attempt", fake)
    summary = run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out", command=["fake"], n=2, timeout=123.0,
    )
    assert summary.n == 2 and summary.attempted == 2
    assert summary.code_counts["GRADE_FAILED"] == 1
    assert summary.code_counts["OK"] == 1
    assert len(summary.cells) == 2
    assert (tmp_path / "out" / "summary.json").exists()


def test_run_writes_partial_summary_then_reraises(
    tmp_path: Path, monkeypatch
) -> None:
    """An internal bug aborts after persisting the completed cells."""
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("boom")
        output = kwargs["output"]
        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name("format_number", datetime.now(UTC))
        cell = output / name
        cell.mkdir()
        (cell / "receipt.json").write_text('{"verdict": "pass"}')
        record = ok_record(name)
        write_attempt_record(cell / "attempt.json", record)
        return record

    monkeypatch.setattr(run_module, "attempt", flaky)
    with pytest.raises(OSError, match="boom"):
        run_module.run(
            task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
            output=tmp_path / "out", command=["fake"], n=3, timeout=123.0,
        )
    summary = json.loads((tmp_path / "out" / "summary.json").read_text())
    assert summary["n"] == 1 and summary["attempted"] == 1
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_run.py -k "grade_failed or partial_summary"`
Expected: the partial-summary test FAILS — an `OSError` escapes today and
no `summary.json` exists. The grade-failed test PASSES already (after
P1/P2, returned `GRADE_FAILED` records flow through the unchanged loop):
it is a regression guard pinning the batch-continuation behavior, not the
red driver for this task.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/run.py`, wrap the loop and move the write:

```python
    manifest = load_manifest(resolve_task(task, tasks_root=tasks_root))
    cells: list[AttemptCell] = []
    try:
        for _ in range(n):
            record = attempt(
                task=task, tasks_root=tasks_root, output=output, command=command,
                timeout=timeout,
            )
            if record.attempt_dir is None:
                raise RuntimeError("attempt record does not name its attempt directory")
            receipt: dict | None = None
            if record.receipt_path is not None:
                receipt_path = output / record.attempt_dir / record.receipt_path
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            cells.append((record.attempt_dir, record, receipt))
    except BaseException:
        # never lose the summary over completed cells (T1)
        if cells:
            summary = compute_summary(
                cells, oracle_visibility=manifest.oracle_visibility
            )
            output.mkdir(parents=True, exist_ok=True)
            write_summary(output / "summary.json", summary)
        raise
    summary = compute_summary(cells, oracle_visibility=manifest.oracle_visibility)
    output.mkdir(parents=True, exist_ok=True)
    write_summary(output / "summary.json", summary)
    return summary
```

(Usage errors — unknown task, empty command — still raise before any cell;
a `GRADE_FAILED` record is returned by `attempt`, never raised, so the
`except BaseException` branch is only the internal-bug class.)

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_run.py`
Expected: PASS.

- [ ] **Step 5: Whole default tier + gate**

Run: `uv run pytest -q`
Expected: PASS. Then:
`uv run ruff check src/satyrn_evals tests`
Expected: clean. (If the branch gate complains that the partial-summary
path is not covered, point to `test_run_writes_partial_summary_then_reraises`.)
