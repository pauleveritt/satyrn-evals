> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V5b Diagnostic Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add `satyrn-evals run TASK --n 8 -- COMMAND...` that repeats the existing `attempt` seam n times and writes `summary.json` (counts only) from the persisted attempt records.

**Architecture:** `run` is a thin loop over the existing `attempt()` (`src/satyrn_evals/attempt.py:80`); each iteration persists an `attempt.json`. A pure `compute_summary` tallies those records into a `Summary`, and `write_summary` persists it. No transcript parsing — the transcript tier is deferred (spec's Out of scope; `BACKLOG.md`).

**Tech Stack:** Python 3.14, `dataclasses`, `argparse`, `pytest`, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-02-v5b-diagnostic-loop-design.md`

## Global Constraints

- Python `>=3.14`; real return type annotations; `match`/`case`/walrus house style.
- Default tier: no model/network/subprocess (planted spawn tripwire, `BRIEF.md:80-83`).
- A refusal test has a sibling success test (`BRIEF.md:84-85`).
- Capture separate from grading (`BRIEF.md:72-75`); counts only, never wall-clock (`BRIEF.md:39-40`).
- Exit codes `0`/`2`/`3`; the summary is authoritative, never the exit code (`BRIEF.md:76-79`).

---

### Task 1: `Summary` record, its tally, and its writer

**Files:** Create `src/satyrn_evals/summary.py`; test `tests/test_summary.py`.

**Interfaces produced:** `Summary` (`n`, `attempted`, `refused`, `code_counts: dict[str, int]`, `verdict_counts: dict[str, int]`, `timeouts`), `compute_summary(records: Sequence[AttemptRecord]) -> Summary`, `write_summary(path: Path, summary: Summary) -> None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_summary.py
import json
from pathlib import Path
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.summary import Summary, compute_summary, write_summary
from satyrn_evals.verdict import Verdict

def make_record(code: AttemptCode, verdict: Verdict | None, *, command_exit: int | None = 0) -> AttemptRecord:
    outcome = AttemptOutcome.ATTEMPTED if verdict is not None else AttemptOutcome.REFUSED
    attempted = verdict is not None
    return AttemptRecord(
        version=1, outcome=outcome, code=code, message="test", task="format_number",
        command=("fake",), command_exit=command_exit,
        patch_path="patch.diff" if attempted else None,
        transcript_path="transcript.txt" if attempted else None,
        patch_digest="a" * 64 if attempted else None,
        transcript_digest="b" * 64 if attempted else None,
        verdict=verdict, receipt_path="receipt.json" if attempted else None,
        workspace_base_sha="c" * 40,
    )

def test_summary_round_trip_and_tally(tmp_path: Path) -> None:
    summary = compute_summary([make_record(AttemptCode.OK, Verdict.PASS)])
    path = tmp_path / "summary.json"
    write_summary(path, summary)
    data = json.loads(path.read_text())
    assert data["n"] == 1 and data["attempted"] == 1 and data["refused"] == 0
    assert data["code_counts"][AttemptCode.OK.value] == 1
    assert data["verdict_counts"][Verdict.PASS.value] == 1
    assert data["timeouts"] == 0

def test_compute_summary_all_refused_is_the_sibling() -> None:
    summary = compute_summary([
        make_record(AttemptCode.NO_PATCH, None),
        make_record(AttemptCode.COMMAND_TIMEOUT, None, command_exit=None),
    ])
    assert summary.n == 2 and summary.attempted == 0 and summary.refused == 2
    assert summary.code_counts[AttemptCode.NO_PATCH.value] == 1
    assert summary.timeouts == 1

def test_compute_summary_tallies_verdicts_over_attempted_only() -> None:
    summary = compute_summary([
        make_record(AttemptCode.OK, Verdict.PASS),
        make_record(AttemptCode.OK, Verdict.FAIL),
        make_record(AttemptCode.NO_PATCH, None),
    ])
    assert summary.attempted == 2 and summary.refused == 1
    assert summary.verdict_counts[Verdict.PASS.value] == 1
    assert summary.verdict_counts[Verdict.FAIL.value] == 1
    assert summary.verdict_counts[Verdict.UNAVAILABLE.value] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_summary.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'satyrn_evals.summary'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/satyrn_evals/summary.py
"""The diagnostic-loop summary: counts only, computed from attempt records."""
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.verdict import Verdict

_ATTEMPT_CODES = frozenset(code.value for code in AttemptCode)
_VERDICTS = frozenset(verdict.value for verdict in Verdict)

@dataclass(frozen=True, slots=True)
class Summary:
    n: int
    attempted: int
    refused: int
    code_counts: dict[str, int]
    verdict_counts: dict[str, int]
    timeouts: int

    def __post_init__(self) -> None:
        if self.n < 0 or self.attempted < 0 or self.refused < 0:
            raise ValueError("counts must be non-negative")
        if self.attempted + self.refused != self.n:
            raise ValueError("attempted + refused must equal n")
        if set(self.code_counts) != _ATTEMPT_CODES or set(self.verdict_counts) != _VERDICTS:
            raise ValueError("counts must hold one key per AttemptCode and per Verdict")
        if self.timeouts != self.code_counts[AttemptCode.COMMAND_TIMEOUT.value]:
            raise ValueError("timeouts must equal code_counts[COMMAND_TIMEOUT]")

def compute_summary(records: Sequence[AttemptRecord]) -> Summary:
    n = len(records)
    attempted = sum(1 for r in records if r.outcome is AttemptOutcome.ATTEMPTED)
    code_counts = {code.value: 0 for code in AttemptCode}
    verdict_counts = {verdict.value: 0 for verdict in Verdict}
    for record in records:
        code_counts[record.code.value] += 1
        if record.verdict is not None:
            verdict_counts[record.verdict.value] += 1
    return Summary(
        n=n, attempted=attempted, refused=n - attempted,
        code_counts=code_counts, verdict_counts=verdict_counts,
        timeouts=code_counts[AttemptCode.COMMAND_TIMEOUT.value],
    )

def write_summary(path: Path, summary: Summary) -> None:
    path.write_text(json.dumps(asdict(summary), indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_summary.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/summary.py tests/test_summary.py && git commit -m "feat: diagnostic Summary, tally, writer"
```

---

### Task 2: `run` orchestration over the attempt seam

**Files:** Create `src/satyrn_evals/run.py`; test `tests/test_run.py`.

**Interfaces:** Consumes `attempt` (`src/satyrn_evals/attempt.py:80`), `compute_summary`, `write_summary`, `UsageError`, `DEFAULT_TIMEOUT`. Produces `run(*, task: str, tasks_root: Path, output: Path, command: list[str], n: int, timeout: float = DEFAULT_TIMEOUT) -> Summary`.

- [ ] **Step 1: Write the failing test (monkeypatched seam, no subprocess)**

```python
# tests/test_run.py
from pathlib import Path
import satyrn_evals.run as run_module
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.verdict import Verdict

def ok_record() -> AttemptRecord:
    return AttemptRecord(
        version=1, outcome=AttemptOutcome.ATTEMPTED, code=AttemptCode.OK,
        message="ok", task="t", command=("fake",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt",
        patch_digest="a" * 64, transcript_digest="b" * 64,
        verdict=Verdict.PASS, receipt_path="receipt.json", workspace_base_sha="c" * 40,
    )

def test_run_calls_attempt_n_times_and_writes_summary(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []
    def fake_attempt(*, task: str, tasks_root: Path, output: Path, command: list[str], timeout: float) -> AttemptRecord:
        calls.append(task)
        return ok_record()
    monkeypatch.setattr(run_module, "attempt", fake_attempt)
    summary = run_module.run(task="t", tasks_root=tmp_path, output=tmp_path, command=["fake"], n=2, timeout=1.5)
    assert len(calls) == 2
    assert summary.n == 2 and summary.attempted == 2 and summary.refused == 0
    assert (tmp_path / "summary.json").exists()

def test_run_refuses_non_positive_n(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_module, "attempt", lambda **kwargs: ok_record())
    try:
        run_module.run(task="t", tasks_root=tmp_path, output=tmp_path, command=["fake"], n=0)
    except run_module.UsageError:
        pass
    else:
        raise AssertionError("run accepted n=0")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'satyrn_evals.run'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/satyrn_evals/run.py
"""Run the attempt seam n times and write a counts-only summary."""
from pathlib import Path
from satyrn_evals.attempt import DEFAULT_TIMEOUT, attempt
from satyrn_evals.errors import UsageError
from satyrn_evals.summary import Summary, compute_summary, write_summary

def run(
    *, task: str, tasks_root: Path, output: Path, command: list[str],
    n: int, timeout: float = DEFAULT_TIMEOUT,
) -> Summary:
    if n < 1:
        raise UsageError("run requires a positive --n")
    if not command:
        raise UsageError("run command is required: run TASK [flags] -- COMMAND...")
    records = [
        attempt(task=task, tasks_root=tasks_root, output=output, command=command, timeout=timeout)
        for _ in range(n)
    ]
    summary = compute_summary(records)
    output.mkdir(parents=True, exist_ok=True)
    write_summary(output / "summary.json", summary)
    return summary
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/run.py tests/test_run.py && git commit -m "feat: run the attempt seam n times and write a summary"
```

---

### Task 3: `run` CLI subcommand with `--n`

**Files:** Modify `src/satyrn_evals/cli.py`; test `tests/test_cli.py`.

**Interfaces:** Consumes `run` (Task 2), `split_attempt_argv` (`src/satyrn_evals/cli.py:36`), `positive_finite_timeout`, `DEFAULT_TASKS_ROOT`, `DEFAULT_TIMEOUT`. Produces `positive_int(value: str) -> int` and the `run` subparser + branch in `main`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py (additions)
def test_cli_run_rejects_non_positive_n() -> None:
    from satyrn_evals.cli import main
    assert main(["run", "format_number", "--n", "0", "--", "fake"]) == 2

def test_cli_run_requires_command() -> None:
    from satyrn_evals.cli import main
    assert main(["run", "format_number"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -q -k cli_run`
Expected: FAIL — `run` is not a recognized subcommand (SystemExit).

- [ ] **Step 3: Write minimal implementation**

```python
# src/satyrn_evals/cli.py (additions)
from satyrn_evals.run import run

def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--n must be an integer greater than zero") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("--n must be an integer greater than zero")
    return number

# inside main(), beside the existing "attempt" fast path:
        if argv[:1] == ["run"]:
            flags, command = split_attempt_argv(argv[1:])
            if not command:
                raise UsageError("run command is required: run TASK [flags] -- COMMAND...")
            args = parser.parse_args(["run", *flags])
            run(task=args.task, tasks_root=Path(args.tasks_root), output=Path(args.output),
                command=command, n=args.n, timeout=args.timeout)
            return 0

# subparser, beside attempt_p:
run_p = sub.add_parser("run", help="run an attempt command n times and write a summary")
run_p.add_argument("task", help="task name")
run_p.add_argument("--n", type=positive_int, default=8, help="attempts per run (default: 8)")
run_p.add_argument("--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)")
run_p.add_argument("--output", default="runs", help="run output directory (default: ./runs)")
run_p.add_argument("--timeout", type=positive_finite_timeout, default=DEFAULT_TIMEOUT,
                   help=f"command timeout in seconds (default: {DEFAULT_TIMEOUT:g})")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py -q -k cli_run`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full default tier**

Run: `uv run pytest -q`
Expected: PASS; the planted spawn tripwire stays green.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/cli.py tests/test_cli.py && git commit -m "feat: add the run subcommand with --n"
```

---

### Task 4: Integration-tier run (real fake command)

**Files:** Test `tests/integration/test_run.py`. Marked `@pytest.mark.integration`; not in CI.

- [ ] **Step 1: Write the test**

```python
# tests/integration/test_run.py
import sys
from pathlib import Path
import pytest
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run import run

pytestmark = pytest.mark.integration

FAKE = Path(__file__).parent / "fake_attempt.py"
KNOWN_GOOD = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"

def _cmd(*args: str) -> list[str]:
    return [sys.executable, str(FAKE), *args]

def test_run_names_success_and_failure_fixtures(tmp_path: Path) -> None:
    success = run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=tmp_path / "ok",
        command=_cmd("--patch", str(KNOWN_GOOD), "--transcript", "wrote the fix"), n=1,
    )
    assert success.attempted == 1
    assert success.verdict_counts["pass"] == 1
    assert (tmp_path / "ok" / "summary.json").exists()
    failure = run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=tmp_path / "fail",
        command=_cmd("--no-patch"), n=1,
    )
    assert failure.refused == 1
    assert failure.code_counts["NO_PATCH"] == 1
```

- [ ] **Step 2: Run it with the integration marker**

Run: `uv run pytest -m integration tests/integration/test_run.py -q`
Expected: PASS (known-good patch grades `pass`; no-patch refuses `NO_PATCH`).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_run.py && git commit -m "test: integration run against the fake seam command"
```

---

## Self-review against the spec

- **Spec coverage:** Task 1 implements the summary shape and tally (`code_counts`, `verdict_counts`, `timeouts`, `n/attempted/refused`); Task 2 the n-loop, persistence, and the summary write; Task 3 the CLI surface and exit codes; Task 4 the integration tier. The transcript tier is out of scope and does not appear.
- **Placeholder scan:** no TBD/TODO; every code step has real code.
- **Type consistency:** `Summary` field names are identical across Tasks 1-2; `run`'s keyword signature matches the CLI call in Task 3.
