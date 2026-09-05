# V9 P4 — The disk commands: summarize and regrade

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `summarize OUTPUT_DIR` rebuilds a run's `summary.json` from disk
through the same code path as `run` (T3, T4), and `regrade ATTEMPT_DIR`
re-scores a preserved patch and rewrites receipt + record (rule 3
executable). CLI wiring and exit codes per spec §5–§6.

**Architecture:** A new focused module `rescore.py` holds pure,
argparse-free functions (`summarize_output`, `regrade_attempt`); the CLI
adds two subparsers under the `grade`/`capture` pattern (`cli.py:129`).
From-disk discovery = subdirectories holding `attempt.json`, ordered by
name; identity comes from the records; a rebuild goes through
`compute_summary`/`write_summary` so it equals `run`'s own output.

**Tech Stack:** Python ≥3.14, stdlib only.

**Spec:** `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md`
§3, §5, §6. Depends on P1–P3 (record fields, `GRADE_FAILED`, `Summary`
identity, `compute_summary` invariants).

## Global Constraints

- **No commits.** Commits are maintainer-controlled (`docs/sdd.md`).
- Default tier must not spawn (tripwire). `rescore.py` is pure file I/O —
  fully default-tier testable; only the real-grade integration round trip
  is marked integration.
- Refusal tests get success siblings.
- Exit codes are spec §6, exactly: summarize `0/2/3`; regrade `0/2/3`.
- House style: `type` aliases, `match`/`case`, `:=`; real annotations.
- `docs/sdd.md` cap: this plan stays ≤400 lines.

---

### Task 1: `summarize_output` — rebuild a summary from disk

**Files:**
- Create: `src/satyrn_evals/rescore.py`
- Test: `tests/test_rescore.py` (new)

**Interfaces:**
- Consumes: `AttemptRecord` loader, `compute_summary`, `write_summary`,
  `load_manifest`, `resolve_task`, `AttemptCode`, `AttemptOutcome`.
- Produces: `summarize_output(output_dir: Path, *, tasks_root: Path) ->
  Summary`. Raises `UsageError` (exit 2) for: missing/not-a-directory,
  no cell subdirectories, unknown task. Raises `SatyrnError`/`ValueError`
  surfaced as operational (3) for: an unparseable `attempt.json`, an
  attempted record whose named `receipt.json` is missing or unparseable,
  mixed/unresolvable record identity, `compute_summary` inconsistencies.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_rescore.py` with a task+run-dir builder (pure file I/O,
no spawning — write `attempt.json`, `receipt.json`, `patch.diff` by hand):

```python
"""summarize_output/regrade_attempt: pure from-disk rebuild and re-score."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import (
    AttemptCode, AttemptOutcome, AttemptRecord, write_attempt_record,
)
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.rescore import summarize_output
from satyrn_evals.verdict import Verdict

TASK = "format_number"


def record(**overrides: object) -> AttemptRecord:
    base = dict(
        version=1, outcome=AttemptOutcome.ATTEMPTED, code=AttemptCode.OK,
        message="ok", task=TASK, command=("fake",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt",
        patch_digest="a" * 64, transcript_digest="b" * 64,
        verdict=Verdict.PASS, receipt_path="receipt.json",
        timeout=123.0, workspace_base_sha="c" * 40, attempt_dir="cell-1",
    )
    base.update(overrides)
    return AttemptRecord(**base)


def write_cell(
    output: Path, name: str, rec: AttemptRecord, receipt: dict | None = None
) -> None:
    """Write a complete V9 cell: record (attempt_dir == dir name) + artifacts.

    A receipt is written only when the caller passes one; summarize treats
    an attempted record that names a receipt whose file is absent as an
    operational error, so callers of this helper must keep record and
    receipt in agreement.
    """
    cell = output / name
    cell.mkdir(parents=True, exist_ok=True)
    write_attempt_record(cell / "attempt.json", replace(rec, attempt_dir=name))
    (cell / "patch.diff").write_text("diff --git a/x b/x\n")
    (cell / "transcript.txt").write_text("t\n")
    if receipt is not None:
        (cell / "receipt.json").write_text(json.dumps(receipt))


_CLEAN_RECEIPT = {"verdict": "pass", "reason": ""}
```


```python
def _bundled() -> Path:
    return DEFAULT_TASKS_ROOT


def test_summarize_rebuilds_counts_from_disk(tmp_path: Path) -> None:
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    write_cell(out, "format_number-2",
               record(code=AttemptCode.GRADE_FAILED, verdict=None,
                      receipt_path=None))
    summary = summarize_output(out, tasks_root=_bundled())
    assert summary.n == 2 and summary.attempted == 2
    assert summary.code_counts["OK"] == 1
    assert summary.code_counts["GRADE_FAILED"] == 1
    assert summary.task == TASK and summary.timeout == 123.0
    assert (out / "summary.json").exists()
    assert json.loads((out / "summary.json").read_text())["task"] == TASK


def test_summarize_ignores_sibling_dirs_without_records(tmp_path: Path) -> None:
    out = tmp_path / "run"
    (out / "stray").mkdir(parents=True)
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    summary = summarize_output(out, tasks_root=_bundled())
    assert len(summary.cells) == 1


def test_summarize_refuses_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="not a directory"):
        summarize_output(tmp_path / "missing", tasks_root=_bundled())


def test_summarize_refuses_an_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(UsageError, match="no attempt cells"):
        summarize_output(tmp_path / "empty", tasks_root=_bundled())


def test_summarize_refuses_unparseable_record_and_missing_receipt(
    tmp_path: Path,
) -> None:
    out = tmp_path / "run"
    cell = out / "format_number-1"
    cell.mkdir(parents=True)
    (cell / "attempt.json").write_text("{not json")
    with pytest.raises(SatyrnError, match="cannot read"):
        summarize_output(out, tasks_root=_bundled())
    (cell / "attempt.json").unlink()
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    (cell / "receipt.json").unlink()
    with pytest.raises(SatyrnError, match="receipt"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_mixed_task_identity(tmp_path: Path) -> None:
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    write_cell(out, "other-task-1", record(task="other-task"),
               receipt=_CLEAN_RECEIPT)
    with pytest.raises(SatyrnError, match="mixed"):
        summarize_output(out, tasks_root=_bundled())
```


- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_rescore.py`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

Create `src/satyrn_evals/rescore.py`:

```python
"""Offline re-scoring from preserved artifacts (rule 3, executable).

summarize_output rebuilds a run's summary.json from the attempt records on
disk through the same compute_summary/write_summary path run() uses, so a
rebuilt summary is byte-identical to the run's own. regrade_attempt re-runs
the grader over a preserved patch and rewrites receipt + record. Pure file
I/O up to the grade call: default-tier testable without argparse.
"""

import json
from dataclasses import replace
from pathlib import Path

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest, resolve_task
from satyrn_evals.summary import (
    AttemptCell,
    Summary,
    compute_summary,
    write_summary,
)
from satyrn_evals.verdict import Verdict


def _root(tasks_root: Path | None) -> Path:
    return tasks_root if tasks_root is not None else DEFAULT_TASKS_ROOT


def _cell_dirs(output: Path) -> list[Path]:
    """Cell subdirectories in name order; dirs without a record are ignored."""
    return sorted(
        (
            path
            for path in output.iterdir()
            if path.is_dir() and (path / "attempt.json").is_file()
        ),
        key=lambda path: path.name,
    )


def _load_cell(cell_dir: Path) -> tuple[Path, AttemptRecord, dict | None]:
    """Load one cell: an identity mismatch is usage; an unreadable record or
    receipt is operational."""
    try:
        record = load_attempt_record(cell_dir / "attempt.json")
    except ValueError as exc:
        raise SatyrnError(f"cannot read {cell_dir.name}: {exc}") from exc
    if record.attempt_dir is not None and record.attempt_dir != cell_dir.name:
        raise UsageError(
            f"record in {cell_dir.name} names {record.attempt_dir!r} "
            "(moved or renamed cell)"
        )
    receipt: dict | None = None
    if record.receipt_path is not None:
        receipt_path = cell_dir / record.receipt_path
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SatyrnError(
                f"cannot read receipt for {cell_dir.name}: {exc}"
            ) from exc
    return cell_dir, record, receipt


def summarize_output(
    output: Path, *, tasks_root: Path | None = None
) -> Summary:
    """Rebuild OUTPUT_DIR/summary.json from the preserved attempt cells.

    Usage (2): missing dir / no cells / unknown task. Operational (3):
    an unreadable record or receipt, mixed identity, or inconsistent cells.
    """
    output = Path(output)
    if not output.is_dir():
        raise UsageError(f"summarize: not a directory: {output}")
    cell_dirs = _cell_dirs(output)
    if not cell_dirs:
        raise UsageError(f"summarize: no attempt cells under {output}")
    cells: list[AttemptCell] = [_load_cell(cell_dir) for cell_dir in cell_dirs]
    root = _root(tasks_root)
    task_dir = resolve_task(cells[0][1].task, tasks_root=root)
    manifest = load_manifest(task_dir)
    try:
        summary = compute_summary(
            cells, oracle_visibility=manifest.oracle_visibility
        )
    except ValueError as exc:
        raise SatyrnError(f"summarize: {exc}") from exc
    write_summary(output / "summary.json", summary)
    return summary


def _gradeable(record: AttemptRecord) -> bool:
    """A patch was admitted to grading: OK (re-score) or GRADE_FAILED."""
    return record.code in (AttemptCode.OK, AttemptCode.GRADE_FAILED)


def regrade_attempt(
    attempt_dir: Path, *, tasks_root: Path | None = None
) -> AttemptRecord | None:
    """Re-grade a preserved patch; rewrite receipt + record in place.

    Returns the rewritten record on PASS/FAIL; ``None`` for a no-op (a
    refusal-code cell was never graded, so nothing re-scores). Usage (2):
    no attempt.json or an identity mismatch. Operational (3): unreadable
    record or UNAVAILABLE verdict.
    """
    attempt_dir = Path(attempt_dir)
    record_path = attempt_dir / "attempt.json"
    if not record_path.is_file():
        raise UsageError(f"regrade: no attempt record under {attempt_dir}")
    try:
        record = load_attempt_record(record_path)
    except ValueError as exc:
        raise SatyrnError(f"regrade: {exc}") from exc
    if record.attempt_dir is not None and record.attempt_dir != attempt_dir.name:
        raise UsageError(
            f"regrade: record names {record.attempt_dir!r}, "
            f"not {attempt_dir.name!r}"
        )
    if not _gradeable(record) or record.patch_path is None:
        return None  # nothing was graded, so nothing re-scores (no-op)
    root = _root(tasks_root)
    task_dir = resolve_task(record.task, tasks_root=root)
    receipt = grade(
        task_dir, attempt_dir / record.patch_path, attempt_dir / "receipt.json"
    )
    write_attempt_record(
        record_path,
        replace(
            record,
            code=AttemptCode.OK,
            verdict=receipt.verdict,
            receipt_path="receipt.json",
            message="attempt re-graded",
        ),
    )
    if receipt.verdict is Verdict.UNAVAILABLE:
        raise SatyrnError(
            f"regrade: verdict unavailable for {attempt_dir.name}: "
            f"{receipt.reason}"
        )
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_rescore.py`
Expected: PASS. (The helper writes `receipt.json` exactly when the record's
`receipt_path` names it; keep record and receipt in agreement.)

- [ ] **Step 5: Convergence test (run then summarize byte-identical)**

```python
def test_summarize_reproduces_run_summary_byte_for_byte(
    tmp_path: Path, monkeypatch
) -> None:
    """T3: a rebuilt summary equals the run's own, exactly."""
    from datetime import UTC, datetime

    import satyrn_evals.run as run_module
    from satyrn_evals.attempt import attempt_dir_name
    from satyrn_evals.attempt_record import write_attempt_record
    # Self-contained double: mirrors attempt() on disk (P3's double shape).
    def fake(*, task: str, tasks_root: Path, output: Path, command: list[str],
             timeout: float) -> object:
        from satyrn_evals.attempt_record import (
            AttemptCode, AttemptOutcome, AttemptRecord,
        )
        from satyrn_evals.verdict import Verdict

        output.mkdir(parents=True, exist_ok=True)
        name = attempt_dir_name(task, datetime.now(UTC))
        cell = output / name
        cell.mkdir()
        (cell / "receipt.json").write_text('{"verdict": "pass"}')
        record = AttemptRecord(
            version=1, outcome=AttemptOutcome.ATTEMPTED,
            code=AttemptCode.OK, message="ok", task=task,
            command=tuple(command), command_exit=0,
            patch_path="patch.diff", transcript_path="transcript.txt",
            patch_digest="a" * 64, transcript_digest="b" * 64,
            verdict=Verdict.PASS, receipt_path="receipt.json",
            timeout=timeout, workspace_base_sha="c" * 40,
            attempt_dir=name,
        )
        write_attempt_record(cell / "attempt.json", record)
        return record

    monkeypatch.setattr(run_module, "attempt", fake)
    run_module.run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "out", command=["fake"], n=2, timeout=123.0,
    )
    before = (tmp_path / "out" / "summary.json").read_text()
    summarize_output(tmp_path / "out", tasks_root=DEFAULT_TASKS_ROOT)
    after = (tmp_path / "out" / "summary.json").read_text()
    assert before == after
```

- [ ] **Step 6: Whole default tier + gate**

Run: `uv run pytest -q`
Expected: PASS. Then `uv run ruff check src/satyrn_evals tests`.
