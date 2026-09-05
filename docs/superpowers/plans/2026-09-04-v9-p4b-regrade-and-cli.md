# V9 P4b — Regrade, the CLI subcommands, and their tests

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Default-tier tests for `regrade_attempt` (spec done-when 6:
`GRADE_FAILED → OK`, refusal-code no-op, identity-mismatch refusal,
UNAVAILABLE), the `summarize`/`regrade` CLI wiring with spec §6 exit
codes, and one real fake-seam round trip.

**Architecture:** `regrade_attempt` already joins `summarize_output` in
`rescore.py` (P4); its grade call is mocked in the default tier exactly as
`test_attempt.py` mocks `attempt`'s grade (P2's pattern). `cli.py` adds two
subparsers under the grade/capture pattern; exit codes ride `main`'s outer
`except SatyrnError`.

**Tech Stack:** Python ≥3.14, stdlib only.

**Spec:** `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md`
§3, §5, §6. Depends on P4.

## Global Constraints

- **No commits.** Commits are maintainer-controlled (`docs/sdd.md`).
- Default tier must not spawn (tripwire). Regrade is pure file I/O until
  the real grade, which is integration-tier (Task 3).
- Refusal tests get success siblings. Exit codes are spec §6 exactly:
  `regrade` returns `0` on PASS/FAIL **or a no-op (refusal code, with a
  stderr note)**, `2` on usage (not an attempt dir / identity mismatch /
  unknown task), `3` on operational (unreadable record / UNAVAILABLE).
- House style: `type` aliases, `match`/`case`, `:=`; real annotations.
- `docs/sdd.md` cap: this plan stays ≤400 lines.

---

### Task 1: default-tier `regrade_attempt` tests

**Files:**
- Test: `tests/test_rescore.py` (extend the P4 file)

**Interfaces:**
- Consumes: `rescore.regrade_attempt` (P4), the P4 `record()`/`write_cell()`
  helpers, `rescore.grade` import (mock target).
- Produces: each state machine leg of `regrade_attempt` is proven with a
  refusal/success sibling where one applies.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rescore.py`:

```python
import json as _json
from satyrn_evals.receipt import Receipt
from satyrn_evals.rescore import regrade_attempt
from satyrn_evals.errors import SatyrnError


def _fake_grade(verdict: Verdict, *, fail: bool = False):
    """A grade double that mirrors real grade(): writes the receipt file."""

    def fake(task_dir, patch_path, receipt_path):
        if fail:
            raise HookError("oracle exploded")
        receipt_path.write_text(
            _json.dumps({"task": task_dir.name, "verdict": verdict.value})
        )
        return Receipt(
            task=task_dir.name, patch_digest="a" * 64,
            verdict=verdict, reason="", evidence=None,
        )

    return fake


def test_regrade_turns_a_grade_failed_cell_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A GRADE_FAILED cell is the reason regrade exists (success leg)."""
    from satyrn_evals import rescore as rescore_module

    out = tmp_path / "run"
    write_cell(out, "format_number-1",
               record(code=AttemptCode.GRADE_FAILED, verdict=None,
                      receipt_path=None))
    monkeypatch.setattr(rescore_module, "grade", _fake_grade(Verdict.PASS))
    rewritten = regrade_attempt(out / "format_number-1", tasks_root=_bundled())
    assert rewritten is not None
    assert rewritten.code is AttemptCode.OK
    assert rewritten.verdict is Verdict.PASS
    assert rewritten.receipt_path == "receipt.json"
    loaded = load_attempt_record(out / "format_number-1" / "attempt.json")
    assert loaded.code is AttemptCode.OK and loaded.verdict is Verdict.PASS


def test_regrade_of_a_refusal_cell_is_a_noop(tmp_path: Path) -> None:
    """A refusal code was never graded: nothing to re-score (no-op leg)."""
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(
        code=AttemptCode.NO_PATCH, outcome=AttemptOutcome.REFUSED,
        verdict=None, receipt_path=None, patch_path=None, transcript_path=None,
        patch_digest=None, transcript_digest=None,
    ))
    assert regrade_attempt(out / "format_number-1", tasks_root=_bundled()) is None


def test_regrade_refuses_identity_mismatch(tmp_path: Path) -> None:
    """A renamed cell must not be graded (refusal leg)."""
    cell = tmp_path / "other-1"
    cell.mkdir()
    write_attempt_record(
        cell / "attempt.json",
        replace(record(code=AttemptCode.GRADE_FAILED, verdict=None,
                       receipt_path=None), attempt_dir="format_number-1"),
    )
    with pytest.raises(UsageError, match="names"):
        regrade_attempt(cell, tasks_root=_bundled())


def test_regrade_refuses_a_non_cell_directory(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="no attempt record"):
        regrade_attempt(tmp_path / "nope", tasks_root=_bundled())


def test_regrade_unavailable_verdict_raises_operational(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UNAVAILABLE after a successful regrade is exit-3 class (spec §6)."""
    from satyrn_evals import rescore as rescore_module

    out = tmp_path / "run"
    write_cell(out, "format_number-1", record())
    monkeypatch.setattr(rescore_module, "grade",
                        _fake_grade(Verdict.UNAVAILABLE))
    with pytest.raises(SatyrnError, match="unavailable"):
        regrade_attempt(out / "format_number-1", tasks_root=_bundled())
    # the record was still rewritten and consistent before the raise
    loaded = load_attempt_record(out / "format_number-1" / "attempt.json")
    assert loaded.code is AttemptCode.OK
    assert loaded.verdict is Verdict.UNAVAILABLE
```

(The refusal-cell record must satisfy the `NO_PATCH` policy — outcome
`refused`, no artifacts, command_exit present — mirror `make_record` in
`tests/test_summary.py` if the local helper needs it. The identity test
needs `write_attempt_record`, `replace`, and `load_attempt_record`
imported at the top of the test file.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_rescore.py -k regrade`
Expected: FAIL — `regrade_attempt` raises `UsageError` on the refusal cell
today (P4's pre-fix state) instead of returning `None`; adjust P4's
implementation first if the module landed before this plan (the P4 module
text already encodes the no-op return).

- [ ] **Step 3: Run to verify they pass**

Run: `uv run pytest -q tests/test_rescore.py`
Expected: PASS.

### Task 2: CLI subparsers for summarize and regrade

**Files:**
- Modify: `src/satyrn_evals/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `rescore.summarize_output`, `rescore.regrade_attempt`.
- Produces: exit codes per spec §6; `--tasks-root` on both.

- [ ] **Step 1: Write the failing tests**

```python
def test_summarize_cli_writes_summary(tmp_path: Path, monkeypatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        cli_module, "summarize_output",
        lambda output, **kw: seen.update(output=str(output), **kw),
    )
    assert cli_module.main(["summarize", str(tmp_path)]) == 0
    assert seen["output"] == str(tmp_path)


def test_summarize_cli_usage_error_exits_2(
    tmp_path: Path, monkeypatch
) -> None:
    def refuse(output, **kw):
        raise UsageError(f"no attempt cells under {output}")

    monkeypatch.setattr(cli_module, "summarize_output", refuse)
    assert cli_module.main(["summarize", str(tmp_path)]) == 2


def test_regrade_cli_dispatches(tmp_path: Path, monkeypatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        cli_module, "regrade_attempt",
        lambda attempt_dir, **kw: seen.update(
            attempt_dir=str(attempt_dir), **kw
        ),
    )
    assert cli_module.main(["regrade", str(tmp_path)]) == 0
    assert seen["attempt_dir"] == str(tmp_path)


def test_regrade_cli_noop_exits_0_with_note(
    tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "regrade_attempt",
                        lambda attempt_dir, **kw: None)
    assert cli_module.main(["regrade", str(tmp_path)]) == 0
    assert "nothing" in capsys.readouterr().err


def test_regrade_cli_usage_error_exits_2(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        cli_module, "regrade_attempt",
        lambda attempt_dir, **kw: (_ for _ in ()).throw(
            UsageError("no attempt record")
        ),
    )
    assert cli_module.main(["regrade", str(tmp_path)]) == 2


def test_regrade_cli_operational_error_exits_3(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        cli_module, "regrade_attempt",
        lambda attempt_dir, **kw: (_ for _ in ()).throw(
            SatyrnError("regrade: verdict unavailable")
        ),
    )
    assert cli_module.main(["regrade", str(tmp_path)]) == 3
```

(The generator-expression throw is the standard way to raise from a
lambda. Import `UsageError`/`SatyrnError` from `satyrn_evals.errors` at the
top of the test file; the CLI module under test is `satyrn_evals.cli`.)

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_cli.py -k "summarize or regrade"`
Expected: FAIL — unknown subcommand.

- [ ] **Step 3: Implement**

In `cli.py`:

1. Import `summarize_output`, `regrade_attempt` from
   `satyrn_evals.rescore`.
2. In `main()`, inside the existing `args.command` dispatch
   (`cli.py:129` region):

```python
        if args.command == "summarize":
            summarize_output(
                Path(args.output), tasks_root=Path(args.tasks_root)
            )
            return 0
        if args.command == "regrade":
            if regrade_attempt(
                Path(args.attempt_dir), tasks_root=Path(args.tasks_root)
            ) is None:
                print(
                    "satyrn-evals: regrade: nothing to grade "
                    "(refusal record)",
                    file=sys.stderr,
                )
            return 0
```

   Exit codes ride `main`'s outer `except SatyrnError`: `UsageError` → 2,
   operational → 3. The no-op (`None`) prints the note and exits 0.

3. Add the subparsers after the `run` subparser:

```python
summarize_p = sub.add_parser(
    "summarize", help="rebuild summary.json for a run output directory"
)
summarize_p.add_argument("output", help="run output directory")
summarize_p.add_argument(
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)

regrade_p = sub.add_parser(
    "regrade", help="re-grade a preserved attempt and rewrite its record"
)
regrade_p.add_argument(
    "attempt_dir", help="attempt directory (holds attempt.json)"
)
regrade_p.add_argument(
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_cli.py tests/test_rescore.py`
Expected: PASS. If a CLI test shows a raw `ValueError` escaping instead of
a clean exit, the module under test is not wrapping a loader error — fix
`rescore.py`, not the test.

### Task 3: integration round trip through the real fake seam

**Files:**
- Test: `tests/integration/test_rescore.py` (new)

**Interfaces:**
- Consumes: real `run` over the fake attempt command, then `regrade` and
  `summarize` on the output.

- [ ] **Step 1: Write the test**

```python
"""End-to-end: run -> regrade -> summarize over the real fake seam."""

import sys
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.rescore import regrade_attempt, summarize_output
from satyrn_evals.run import run

pytestmark = pytest.mark.integration

FAKE = Path(__file__).parent / "fake_attempt.py"
KNOWN_GOOD = (
    DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"
)


def test_run_regrade_summarize_round_trip(tmp_path: Path) -> None:
    output = tmp_path / "run"
    run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=output,
        command=[sys.executable, str(FAKE), "--patch", str(KNOWN_GOOD),
                 "--transcript", "wrote the fix"],
        n=2, timeout=123.0,
    )
    before = (output / "summary.json").read_text()
    # re-score every cell explicitly by name (refusals no-op; graded re-grade)
    for cell in sorted(p for p in output.iterdir() if p.is_dir()):
        regrade_attempt(cell, tasks_root=DEFAULT_TASKS_ROOT)
    after_regrade = summarize_output(output, tasks_root=DEFAULT_TASKS_ROOT)
    # the rebuild is byte-identical to the run's own summary
    assert (output / "summary.json").read_text() == before
    assert after_regrade.attempted == 2
```

- [ ] **Step 2: Run to verify it passes**

Run: `uv run pytest -q tests/integration/test_rescore.py -m integration`
Expected: PASS (real grade subprocesses are integration-tier).

- [ ] **Step 3: Whole default tier + gate**

Run: `uv run pytest -q` and
`uv run pytest -q -m integration tests/integration/test_rescore.py`
Expected: both PASS. Then
`uv run ruff check src/satyrn_evals tests`.
