# Self-test harness implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The harness runs a packet's declared `self_test_command` once, on
the executable seam, after the implementer's own turn, and retains what
happened — closing HP7's "implementer cannot run its own verification" gap
without adding implementer self-correction.

**Architecture:** A new `SelfTestOutcome` value type and its JSON
round-trip live in `route.py`, next to `ImplementerResult`. `command_implementer`
runs the self-test as a second bounded subprocess after its own implementer
subprocess returns, on the executable seam only, and writes the outcome to a
new harness file in the workspace. `chain_record.py`'s existing
`run_and_record_chain`/`capture_candidate` hook reads that file per phase and
attaches it to `PhaseRecord`; `declaration_ledger` reports `self_test_command`
as `applied` only when it did.

**Tech Stack:** Python 3.14, stdlib `subprocess`/`dataclasses`/`json`, pytest
(default tier: no subprocess; `@pytest.mark.integration`: real subprocess).

**Spec:** [docs/superpowers/specs/2026-09-10-self-test-harness-design.md](../specs/2026-09-10-self-test-harness-design.md)

## Global Constraints

- Never gates: `SelfTestOutcome.exit_code` never reaches `PhaseRecord.accepted`/`reason`.
- Runs only on the executable seam (`route.is_executable_seam`); never on
  `scripted_implementer`/`fake_implementer.py`.
- Never raises out of `command_implementer.implement()`: a launch failure or
  timeout is retained evidence (`ran=False`, a `reason`), not a route crash.
- `self_test_command` ledger state is two-valued: `applied` when the harness
  ran it, `declared_not_applied` otherwise — no `observed_compliant`.
- Default tier stays subprocess-free (`tests/conftest.py`'s tripwire); any
  test that actually runs a self-test command is `@pytest.mark.integration`.
- `DEFAULT_SELF_TEST_TIMEOUT_SECONDS = 600`, matching
  `adapters.pi_implementer.DEFAULT_TIMEOUT_SECONDS`.

---

## Task 1: `SelfTestOutcome` and its wire form

**Files:**
- Modify: `src/satyrn_evals/route.py` (imports, constants, new dataclass + functions)
- Create: `tests/data/self-test-outcome-golden.json`
- Modify: `tests/test_route.py` (new test section)

**Interfaces:**
- Produces: `route.SelfTestOutcome` (frozen dataclass: `command: tuple[str, ...]`,
  `ran: bool`, `exit_code: int | None`, `output: str`, `reason: str | None`,
  `duration_seconds: float`), `route.self_test_outcome_to_dict(outcome) -> dict`,
  `route.self_test_outcome_from_dict(data) -> SelfTestOutcome`,
  `route.SELF_TEST_RESULT_NAME = ".satyrn-self-test-result.json"`,
  `route.DEFAULT_SELF_TEST_TIMEOUT_SECONDS = 600`. Task 2 and Task 3 both
  import these.

- [ ] **Step 1: Write the failing tests**

In `tests/test_route.py`, add `import json` if not already present (it is —
check the existing import block), and extend the `from satyrn_evals.route
import (...)` block to add `SelfTestOutcome, self_test_outcome_from_dict,
self_test_outcome_to_dict`. Then append this section after the existing
`# --- HP2.1 the result, and its wire form ---` block's tests (after
`test_a_persisted_result_missing_a_key_fails_as_itself`, before `# --- HP2.2
the fake implementer ---`):

```python
# --- Self-test evidence: the harness runs self_test_command -----------------

SELF_TEST_GOLDEN = Path(__file__).parent / "data" / "self-test-outcome-golden.json"


def test_a_ran_self_test_records_its_exit_code() -> None:
    outcome = SelfTestOutcome(
        command=("uv", "run", "pytest"),
        ran=True,
        exit_code=0,
        output="1 passed\n",
        reason=None,
        duration_seconds=1.5,
    )
    assert outcome.exit_code == 0


def test_a_ran_self_test_must_not_carry_a_reason() -> None:
    with pytest.raises(RouteError, match="reason"):
        SelfTestOutcome(
            command=("true",), ran=True, exit_code=0, output="",
            reason="should not be set", duration_seconds=0.1,
        )


def test_an_unrun_self_test_must_carry_a_reason() -> None:
    with pytest.raises(RouteError, match="reason"):
        SelfTestOutcome(
            command=("true",), ran=False, exit_code=None, output="",
            reason=None, duration_seconds=0.1,
        )


def test_an_unrun_self_test_must_not_carry_an_exit_code() -> None:
    with pytest.raises(RouteError, match="exit_code"):
        SelfTestOutcome(
            command=("true",), ran=False, exit_code=1, output="",
            reason="launch failed", duration_seconds=0.1,
        )


def test_an_unrun_self_test_must_not_carry_output() -> None:
    with pytest.raises(RouteError, match="output"):
        SelfTestOutcome(
            command=("true",), ran=False, exit_code=None, output="stray",
            reason="launch failed", duration_seconds=0.1,
        )


def test_self_test_command_must_be_a_non_empty_tuple() -> None:
    with pytest.raises(RouteError, match="command"):
        SelfTestOutcome(
            command=(), ran=True, exit_code=0, output="", reason=None,
            duration_seconds=0.1,
        )


def test_duration_seconds_must_be_non_negative_and_finite() -> None:
    with pytest.raises(RouteError, match="duration_seconds"):
        SelfTestOutcome(
            command=("true",), ran=True, exit_code=0, output="", reason=None,
            duration_seconds=-1.0,
        )


def test_the_golden_self_test_outcome_round_trips() -> None:
    data = json.loads(SELF_TEST_GOLDEN.read_text())
    assert self_test_outcome_to_dict(self_test_outcome_from_dict(data)) == data


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("command", "true"),
        ("ran", "yes"),
        ("exit_code", "0"),
        ("output", 3),
        ("reason", 3),
        ("duration_seconds", "1.5"),
    ],
)
def test_a_persisted_self_test_outcome_of_the_wrong_shape_is_refused(
    field: str, value: object
) -> None:
    data = json.loads(SELF_TEST_GOLDEN.read_text())
    data[field] = value
    with pytest.raises(RouteError, match=field):
        self_test_outcome_from_dict(data)


def test_a_persisted_self_test_outcome_missing_a_key_fails_as_itself() -> None:
    data = json.loads(SELF_TEST_GOLDEN.read_text())
    del data["exit_code"]
    with pytest.raises(RouteError, match="missing exit_code"):
        self_test_outcome_from_dict(data)
```

Create `tests/data/self-test-outcome-golden.json`:

```json
{
  "command": ["uv", "run", "python", "-m", "pytest", "tests"],
  "ran": true,
  "exit_code": 0,
  "output": "1 passed in 0.01s\n",
  "reason": null,
  "duration_seconds": 1.23
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_route.py -k self_test`
Expected: collection error (`SelfTestOutcome` etc. do not exist yet in `route.py`).

- [ ] **Step 3: Implement `route.py`**

Modify the import block at the top of `src/satyrn_evals/route.py`:

```python
import json
import math
import os
import subprocess
import time
```

(`math` and `time` are new; keep the rest of the import block — `collections.abc`,
`dataclasses`, `pathlib`, `typing` — unchanged.)

After `_RESULT_KEYS = frozenset(...)` (currently the last line before
`@dataclass(frozen=True, slots=True)\nclass ImplementerResult:`), add:

```python
SELF_TEST_RESULT_NAME = ".satyrn-self-test-result.json"
"""Written by ``command_implementer`` after a packet's declared
``self_test_command`` runs on the executable seam -- never on the in-process
seam, and never when a packet declares no command. Listed in
``attribution.HARNESS_FILES`` so it is retained evidence, never a mutation
attributed to either role."""

DEFAULT_SELF_TEST_TIMEOUT_SECONDS = 600
"""Matches ``adapters.pi_implementer.DEFAULT_TIMEOUT_SECONDS`` -- the same
``self_test_command`` (``uv run python -m pytest tests``) HP7's pre-run
record already reasoned about at that figure."""

_SELF_TEST_KEYS = frozenset(
    {"command", "ran", "exit_code", "output", "reason", "duration_seconds"}
)
```

After `implementer_result_from_dict` (before `type PhaseFiles = ...`), add:

```python
@dataclass(frozen=True, slots=True)
class SelfTestOutcome:
    """What the harness saw when it ran a packet's declared
    ``self_test_command`` once, after the implementer's own turn. Never a
    verdict: ``ran``/``exit_code`` are retained evidence, and nothing here
    feeds ``PhaseDecision.accepted`` -- that stays ``PhaseGrader``'s alone.
    """

    command: tuple[str, ...]
    ran: bool
    exit_code: int | None
    output: str
    reason: str | None
    duration_seconds: float

    def __post_init__(self) -> None:
        if not self.command or any(
            not isinstance(c, str) or not c for c in self.command
        ):
            raise RouteError(
                "self_test outcome command must be a non-empty tuple of "
                "non-blank strings"
            )
        if self.ran:
            if (
                self.exit_code is None
                or isinstance(self.exit_code, bool)
                or not isinstance(self.exit_code, int)
            ):
                raise RouteError(
                    "a ran self-test must record an integer exit_code"
                )
            if self.reason is not None:
                raise RouteError("a ran self-test must not carry a reason")
        else:
            if self.exit_code is not None:
                raise RouteError(
                    "a self-test that did not run must not carry an exit_code"
                )
            if not self.reason:
                raise RouteError(
                    "a self-test that did not run must carry a reason"
                )
            if self.output:
                raise RouteError(
                    "a self-test that did not run must not carry output"
                )
        if (
            isinstance(self.duration_seconds, bool)
            or not isinstance(self.duration_seconds, (int, float))
            or not math.isfinite(self.duration_seconds)
            or self.duration_seconds < 0
        ):
            raise RouteError(
                "self_test duration_seconds must be a non-negative finite "
                "number"
            )


def self_test_outcome_to_dict(outcome: SelfTestOutcome) -> dict[str, object]:
    return {
        "command": list(outcome.command),
        "ran": outcome.ran,
        "exit_code": outcome.exit_code,
        "output": outcome.output,
        "reason": outcome.reason,
        "duration_seconds": outcome.duration_seconds,
    }


def self_test_outcome_from_dict(data: Mapping[str, object]) -> SelfTestOutcome:
    if missing := sorted(_SELF_TEST_KEYS - set(data)):
        raise RouteError(
            f"persisted self_test outcome is missing {', '.join(missing)}"
        )
    command = data["command"]
    if not isinstance(command, list) or not all(
        isinstance(c, str) for c in command
    ):
        raise RouteError("persisted self_test command must be a list of strings")
    ran = data["ran"]
    if not isinstance(ran, bool):
        raise RouteError("persisted self_test ran must be a bool")
    exit_code = data["exit_code"]
    if exit_code is not None and (
        isinstance(exit_code, bool) or not isinstance(exit_code, int)
    ):
        raise RouteError(
            "persisted self_test exit_code must be an integer or null"
        )
    output = data["output"]
    if not isinstance(output, str):
        raise RouteError("persisted self_test output must be a string")
    reason = data["reason"]
    if reason is not None and not isinstance(reason, str):
        raise RouteError("persisted self_test reason must be a string or null")
    duration = data["duration_seconds"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise RouteError("persisted self_test duration_seconds must be a number")
    return SelfTestOutcome(
        command=tuple(command),
        ran=ran,
        exit_code=exit_code,
        output=output,
        reason=reason,
        duration_seconds=float(duration),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_route.py`
Expected: PASS (all of `test_route.py`, not only the new tests — confirms no
regression on `ImplementerResult`'s own tests).

- [ ] **Step 5: Typecheck and lint**

Run: `uv run ruff check src/satyrn_evals/route.py tests/test_route.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/route.py tests/test_route.py tests/data/self-test-outcome-golden.json
git commit -m "route: add SelfTestOutcome and its JSON round trip"
```

---

## Task 2: `command_implementer` runs `self_test_command`

**Files:**
- Modify: `src/satyrn_evals/route.py` (`command_implementer`, new `_run_self_test`)
- Modify: `src/satyrn_evals/attribution.py` (`HARNESS_FILES`)
- Modify: `tests/test_attribution_snapshot.py` (`test_every_harness_file_is_excluded_by_name`)
- Modify: `tests/test_route.py` (one default-tier regression guard)
- Modify: `tests/integration/test_hp2_route.py` (real subprocess behavior)

**Interfaces:**
- Consumes: `SelfTestOutcome`, `self_test_outcome_to_dict`,
  `SELF_TEST_RESULT_NAME`, `DEFAULT_SELF_TEST_TIMEOUT_SECONDS` (Task 1).
- Produces: `command_implementer(argv, workspace, *, self_test_timeout=DEFAULT_SELF_TEST_TIMEOUT_SECONDS)`
  now writes `workspace / SELF_TEST_RESULT_NAME` when the packet declares a
  `self_test_command`. Task 4 reads this file.

- [ ] **Step 1: Write the failing default-tier tests**

In `tests/test_attribution_snapshot.py`, update `test_every_harness_file_is_excluded_by_name`:

```python
def test_every_harness_file_is_excluded_by_name(tmp_path: Path) -> None:
    """Asserted per name rather than through a pattern, so that adding a
    bookkeeping file to the seam is a visible decision here."""
    assert {
        ".satyrn-packet.json",
        ".satyrn-result.json",
        ".phase-counter",
        ".satyrn-implementer-transcript.jsonl",
        ".satyrn-implementer-stderr.log",
        ".satyrn-implementer-call-counter",
        ".satyrn-self-test-result.json",
    } == HARNESS_FILES
    before = snapshot(tmp_path)
    for name in HARNESS_FILES:
        _write(tmp_path, name, "bookkeeping\n")
    assert diff_snapshots(before, snapshot(tmp_path)) == ()
```

In `tests/test_route.py`, add to the `# --- HP2.2 the fake implementer ---`
section (after `test_the_fake_writes_nothing_before_refusing`, the exact
insertion point does not matter within that section):

```python
def test_the_in_process_seam_never_writes_a_self_test_outcome(
    tmp_path: Path,
) -> None:
    """The in-process seam is not `command_implementer` at all, so nothing
    here can spawn a self-test regardless of what the packet declares --
    the default-tier half of the executable-seam-only invariant; the
    subprocess half is proven in `tests/integration/test_hp2_route.py`."""
    implementer = scripted_implementer(ROUTE_SCENARIO, tmp_path)
    implementer(_packet("phase-1-home"))
    assert not (tmp_path / ".satyrn-self-test-result.json").is_file()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_attribution_snapshot.py tests/test_route.py -k "harness_file or self_test_outcome"`
Expected: FAIL — `test_every_harness_file_is_excluded_by_name` fails on the
set comparison (new name missing from `HARNESS_FILES`); the new
`test_the_in_process_seam_never_writes_a_self_test_outcome` currently PASSES
already (nothing writes that file yet) — that is expected and fine; it
becomes a real regression guard once Step 3 adds the writer.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/attribution.py`, update the `HARNESS_FILES` docstring
comment and set:

```python
#: Files the harness itself writes into a worker's workspace. They are the
#: seam's own bookkeeping, not anybody's mutation, and they are listed by
#: name rather than matched by a pattern so that adding one is a visible
#: decision. ``.satyrn-packet.json``, ``.satyrn-result.json`` and
#: ``.satyrn-self-test-result.json`` are written by
#: ``route.command_implementer``; ``.phase-counter`` by the executable fake,
#: which stands in for a worker that tracks its own position. The remaining
#: three are the real Pi implementer adapter's own
#: (``adapters/pi_implementer.py``) -- ``.satyrn-implementer-transcript.jsonl``
#: and ``.satyrn-implementer-stderr.log``, each appended to once per phase
#: rather than named per phase, since this set matches exact relative paths
#: and not a pattern; and ``.satyrn-implementer-call-counter``, its own
#: position-tracker, the same shape as ``.phase-counter``. All seven are
#: retained evidence, never a mutation to attribute to either role.
HARNESS_FILES: frozenset[str] = frozenset(
    {
        ".satyrn-packet.json",
        ".satyrn-result.json",
        ".phase-counter",
        ".satyrn-implementer-transcript.jsonl",
        ".satyrn-implementer-stderr.log",
        ".satyrn-implementer-call-counter",
        ".satyrn-self-test-result.json",
    }
)
```

In `src/satyrn_evals/route.py`, replace `command_implementer` in full:

```python
def command_implementer(
    argv: list[str],
    workspace: Path,
    *,
    self_test_timeout: int = DEFAULT_SELF_TEST_TIMEOUT_SECONDS,
) -> Implementer:
    """Adapt an implementer **executable** to the callable seam.

    Shipped here rather than in a test: if this adapter lived only in the
    integration test, the callable would be a different contract from the one
    a live run drives, and that test would prove only its own fixture.

    The packet is handed over as a file and the result read back from one, so
    neither crosses on stdout -- the same reason a verdict never comes from
    stdout anywhere else in this repository.

    **After the implementer returns, the harness runs the packet's own
    ``self_test_command`` once**, in the same workspace, if one is declared --
    closing the gap HP7's pre-run record names: nothing else on this seam can
    run it, since the real Pi adapter has no ``bash``. The outcome is
    retained evidence only (``SELF_TEST_RESULT_NAME``, excluded from
    mutation attribution via ``attribution.HARNESS_FILES``) and never
    changes this function's return value -- ``command_implementer`` still
    does not decide verdicts.
    """

    def implement(packet: HandoffPacket) -> ImplementerResult:  # pragma: no cover
        # Integration tier only: this body spawns, which the default tier's
        # planted tripwire forbids. `tests/integration/test_hp2_route.py`
        # drives it through a real executable and asserts the same decision
        # sequence the in-process seam produces, which is the drift guard.
        packet_path = workspace / ".satyrn-packet.json"
        result_path = workspace / ".satyrn-result.json"
        self_test_path = workspace / SELF_TEST_RESULT_NAME
        # Only the worker projection crosses. The full packet -- `redacts`
        # included -- stays host-side; writing it here put every hidden
        # selector in a file the worker could read.
        projection = worker_projection(packet)
        assert_projection_is_clean(packet, projection)
        packet_path.write_text(json.dumps(projection, indent=2))
        result_path.unlink(missing_ok=True)
        # A stale outcome from an earlier phase in this same workspace must
        # not survive into a phase that declares no self_test_command --
        # this is one plain workspace across the whole chain (HP3 is not
        # composed here), so "absent" must mean this phase, not a leftover.
        self_test_path.unlink(missing_ok=True)
        env = {
            **os.environ,
            PACKET_ENV: str(packet_path),
            RESULT_ENV: str(result_path),
        }
        subprocess.run(argv, cwd=workspace, env=env, check=True)
        if not result_path.is_file():
            raise RouteError(
                f"implementer wrote no result to {RESULT_ENV}; an absent "
                "result is not a refusal"
            )
        result = implementer_result_from_dict(json.loads(result_path.read_text()))
        if packet.self_test_command:
            outcome = _run_self_test(
                packet.self_test_command, workspace, self_test_timeout
            )
            self_test_path.write_text(json.dumps(self_test_outcome_to_dict(outcome)))
        return result

    # HP6: a marker on the closure itself, read by `is_executable_seam`
    # below, so a caller retaining a chain does not have to separately
    # assert which seam produced it -- the one fact that assertion cannot
    # get wrong is whether this is the object it is looking at.
    implement.executable_seam = True  # type: ignore[attr-defined]
    return implement  # pragma: no cover


def _run_self_test(
    command: tuple[str, ...], workspace: Path, timeout: int
) -> SelfTestOutcome:  # pragma: no cover
    """Runs one declared ``self_test_command`` in ``workspace`` and reports
    what happened. Never raises: a self-test that cannot launch or that
    times out is evidence for the retained record, not a route crash -- the
    implementer's own result, already read by the caller, is unaffected
    either way. Integration tier only, for the same reason `implement`
    above is: this spawns.
    """
    start = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return SelfTestOutcome(
            command=command,
            ran=False,
            exit_code=None,
            output="",
            reason=str(exc),
            duration_seconds=time.monotonic() - start,
        )
    return SelfTestOutcome(
        command=command,
        ran=True,
        exit_code=completed.returncode,
        output=completed.stdout + completed.stderr,
        reason=None,
        duration_seconds=time.monotonic() - start,
    )
```

- [ ] **Step 4: Run the default-tier tests to verify they pass**

Run: `uv run pytest -q tests/test_attribution_snapshot.py tests/test_route.py`
Expected: PASS.

- [ ] **Step 5: Write the failing integration tests**

In `tests/integration/test_hp2_route.py`, add `import dataclasses` and
`import json` right after the existing `import shutil` import, and add a new
import line `from satyrn_evals.packet import build_packet` alongside the
existing `from satyrn_evals.manifest import load_manifest, resolve_task`
line (the file currently imports nothing from `satyrn_evals.packet`).
`SelfTestOutcome` is **not** needed here — these tests read the persisted
JSON directly, the same way the file's existing tests already do. Append:

```python
def _packet(step_id: str = "phase-1-home"):
    task_dir = resolve_task(TASK_NAME)
    return build_packet(
        task_dir, load_manifest(task_dir), load_session_spec(task_dir),
        step_id, base_revision="3e6607e533792ab0", **BUDGETS,
    )


def test_a_passing_self_test_command_is_run_and_retained(tmp_path: Path) -> None:
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    implementer(dataclasses.replace(_packet(), self_test_command=("true",)))
    data = json.loads((tmp_path / ".satyrn-self-test-result.json").read_text())
    assert data["ran"] is True
    assert data["exit_code"] == 0
    assert data["command"] == ["true"]


def test_a_failing_self_test_command_is_retained_with_its_exit_code(
    tmp_path: Path,
) -> None:
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    implementer(dataclasses.replace(_packet(), self_test_command=("false",)))
    data = json.loads((tmp_path / ".satyrn-self-test-result.json").read_text())
    assert data["ran"] is True
    assert data["exit_code"] != 0


def test_a_self_test_command_that_cannot_launch_is_retained_as_not_ran(
    tmp_path: Path,
) -> None:
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    implementer(
        dataclasses.replace(
            _packet(), self_test_command=("satyrn-evals-nonexistent-binary-xyz",)
        )
    )
    data = json.loads((tmp_path / ".satyrn-self-test-result.json").read_text())
    assert data["ran"] is False
    assert data["exit_code"] is None
    assert data["reason"]


def test_a_self_test_command_that_times_out_is_retained_as_not_ran(
    tmp_path: Path,
) -> None:
    implementer = command_implementer(
        [sys.executable, str(FAKE)], tmp_path, self_test_timeout=1
    )
    implementer(
        dataclasses.replace(
            _packet(),
            self_test_command=(sys.executable, "-c", "import time; time.sleep(5)"),
        )
    )
    data = json.loads((tmp_path / ".satyrn-self-test-result.json").read_text())
    assert data["ran"] is False
    assert data["reason"]


def test_no_self_test_command_writes_no_outcome_file(tmp_path: Path) -> None:
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    implementer(dataclasses.replace(_packet(), self_test_command=None))
    assert not (tmp_path / ".satyrn-self-test-result.json").is_file()


def test_a_stale_outcome_does_not_survive_a_phase_with_no_command(
    tmp_path: Path,
) -> None:
    """The two-call sibling: a workspace this seam reuses across phases must
    not let phase 1's outcome file read as phase 2's absence-of-a-command."""
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    implementer(dataclasses.replace(_packet(), self_test_command=("true",)))
    assert (tmp_path / ".satyrn-self-test-result.json").is_file()
    implementer(dataclasses.replace(_packet(), self_test_command=None))
    assert not (tmp_path / ".satyrn-self-test-result.json").is_file()
```

- [ ] **Step 6: Run the integration tests to verify they pass**

`command_implementer` was already implemented in Step 3, so these new tests
exercise real behavior on the first run rather than failing first — that is
fine; Steps 1-2 already did the fail-first half of TDD for this task, over
the default-tier regression guard.

Run: `uv run pytest -q -m integration tests/integration/test_hp2_route.py -k self_test`
Expected: PASS.

- [ ] **Step 7: Run the full integration suite for regressions**

Run: `uv run pytest -q -m integration tests/integration/test_hp2_route.py`
Expected: PASS (no regression on the existing executable-seam tests, which
now also produce a `.satyrn-self-test-result.json` per phase for the real
task's own `self_test_command` as a side effect — none of those tests
enumerate workspace files exhaustively, so this is harmless).

- [ ] **Step 8: Lint**

Run: `uv run ruff check src/satyrn_evals/route.py src/satyrn_evals/attribution.py tests/test_attribution_snapshot.py tests/test_route.py tests/integration/test_hp2_route.py`
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add src/satyrn_evals/route.py src/satyrn_evals/attribution.py \
  tests/test_attribution_snapshot.py tests/test_route.py \
  tests/integration/test_hp2_route.py
git commit -m "route: run self_test_command on the executable seam, retain the outcome"
```

---

## Task 3: `chain_record.py` retains the outcome and reports it in the ledger

**Files:**
- Modify: `src/satyrn_evals/chain_record.py` (`declaration_ledger`, `PhaseRecord`,
  `_PHASE_KEYS`, `_phase_record_to_dict`, `_phase_record_from_dict`,
  `build_chain_record`)
- Modify: `tests/test_chain_record.py`
- Modify (regenerate): `tests/data/hp6-golden-chain-record.json`

**Interfaces:**
- Consumes: `SelfTestOutcome`, `self_test_outcome_to_dict`,
  `self_test_outcome_from_dict` (Task 1).
- Produces: `PhaseRecord.self_test_outcome: SelfTestOutcome | None`;
  `declaration_ledger(..., self_test_ran: bool = False)`. Task 4 supplies
  `self_test_ran` and `self_test_outcome` from a real run.

- [ ] **Step 1: Write the failing tests**

In `tests/test_chain_record.py`, add `PhaseRecord` to the
`from satyrn_evals.chain_record import (...)` block and `SelfTestOutcome` to
the `from satyrn_evals.route import (...)` block. Replace
`test_offline_declares_four_fields_regardless_of_observation` (it currently
also covers `self_test_command`, which is no longer unconditional) with:

```python
def test_offline_declares_three_fields_regardless_of_observation() -> None:
    packet = _packet("phase-1-home")
    ledger = declaration_ledger(
        executable_seam=False, packet=packet, implementer_mutations=()
    )
    for name in ("turn_budget", "tool_call_budget", "base_revision"):
        assert ledger[name] is AppliedState.DECLARED_NOT_APPLIED


def test_self_test_command_is_declared_not_applied_unless_the_harness_ran_it() -> None:
    """The sibling of `redacts`'s seam-derived value: this one is driven by
    whether the harness reports it actually ran the command, not by which
    seam a chain used."""
    packet = _packet("phase-1-home")
    assert (
        declaration_ledger(
            executable_seam=False, packet=packet, implementer_mutations=()
        )["self_test_command"]
        is AppliedState.DECLARED_NOT_APPLIED
    )
    assert (
        declaration_ledger(
            executable_seam=False,
            packet=packet,
            implementer_mutations=(),
            self_test_ran=True,
        )["self_test_command"]
        is AppliedState.APPLIED
    )
```

Append a new section at the end of the `# --- HP6.3 ---` block (after
`test_an_out_of_scope_mutation_is_a_check_chain_finding`, before
`# --- HP6.4 ---`):

```python
# --- self-test evidence: the harness runs self_test_command -----------------


def test_a_built_record_carries_no_self_test_outcome(tmp_path: Path) -> None:
    """`build_chain_record` has no workspace to read one from -- the same
    shape `candidate_snapshot_path` already uses for the same reason."""
    record = _delivered_record(tmp_path)
    for phase in record.phases:
        assert phase.self_test_outcome is None


def test_a_phase_record_with_a_self_test_outcome_round_trips() -> None:
    outcome = SelfTestOutcome(
        command=("uv", "run", "pytest"),
        ran=True,
        exit_code=1,
        output="1 failed\n",
        reason=None,
        duration_seconds=2.0,
    )
    packet = _packet("phase-1-home")
    record = ChainRecord(
        version=CHAIN_RECORD_VERSION,
        phases=(
            PhaseRecord(
                step_id="phase-1-home",
                packet=packet,
                result=ImplementerResult(
                    changed_files=("app.py",),
                    reported_outcome="delivered",
                    message=None,
                ),
                accepted=True,
                reason="scripted pass",
                implementer_mutations=(Mutation("app.py", "created"),),
                orchestrator_mutations=(),
                declaration_ledger=declaration_ledger(
                    executable_seam=True,
                    packet=packet,
                    implementer_mutations=(Mutation("app.py", "created"),),
                    self_test_ran=True,
                ),
                self_test_outcome=outcome,
            ),
        ),
        final_decision=None,
    )
    data = chain_record_to_dict(record)
    assert data["phases"][0]["self_test_outcome"]["exit_code"] == 1
    assert chain_record_from_dict(data) == record
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_chain_record.py -k "self_test or offline_declares_three"`
Expected: FAIL (`PhaseRecord` has no `self_test_outcome` parameter yet;
`declaration_ledger` has no `self_test_ran` parameter yet).

- [ ] **Step 3: Implement**

In `src/satyrn_evals/chain_record.py`, extend the `from satyrn_evals.route
import (...)` block to add `SELF_TEST_RESULT_NAME`, `SelfTestOutcome`,
`self_test_outcome_from_dict`, `self_test_outcome_to_dict`.

Modify `declaration_ledger`'s signature and return, and extend its
docstring:

```python
def declaration_ledger(
    *,
    executable_seam: bool,
    packet: HandoffPacket,
    implementer_mutations: tuple[Mutation, ...] | None,
    self_test_ran: bool = False,
) -> dict[str, AppliedState]:
    """What this run's own evidence says about each tracked declaration.

    ``turn_budget``, ``tool_call_budget`` and ``base_revision`` are built
    into every packet and read nowhere outside ``packet.py`` and the
    ``build_packet`` call (``route.py``) -- no code counts a turn or checks
    out the named revision, so both are always declared and unapplied on
    this route. ``redacts`` is the one field that takes both values from the
    same task: ``assert_projection_is_clean`` runs only inside
    ``command_implementer``, so it is applied on the executable seam and
    declared-and-unapplied on the in-process one. ``self_test_command``
    reaches ``applied`` only when the caller reports the harness actually
    ran it this phase (``route.command_implementer``, after the
    implementer's own turn) -- ``self_test_ran``, supplied by
    ``run_and_record_chain`` from the retained
    ``.satyrn-self-test-result.json``, never asserted by a caller that has
    not observed one. ``build_chain_record``, which has no workspace to
    observe from, always passes the default ``False``.

    ``writable_paths`` is **derived from observation, not asserted,** and
    never reaches ``applied``: nothing this build observes can name a code
    path that actively enforces scope on an implementer's behalf --
    ``scripted_implementer`` happens to enforce its own, but that is a
    property of one fixture policing itself, not something the route or this
    ledger can see or take credit for, and the real adapter deliberately
    does not self-enforce at all (``adapters/pi_implementer.py``). So:
    ``unknown`` when the implementer window was never observed (nothing to
    check); ``declared_not_applied`` when an observed mutation lands outside
    the packet's own ``writable_paths`` (unambiguous: the scope was not
    honoured); ``observed_compliant`` when every observed mutation admits
    within it -- **compliance, not enforcement.** An implementer that never
    tried to leave scope looks identical to one a restriction actually
    stopped, and this ledger does not have the evidence to tell them apart,
    so it does not claim to.
    """
    if implementer_mutations is None:
        writable_state = AppliedState.UNKNOWN
    elif any(
        not admits(packet.writable_paths, mutation.path)
        for mutation in implementer_mutations
    ):
        writable_state = AppliedState.DECLARED_NOT_APPLIED
    else:
        writable_state = AppliedState.OBSERVED_COMPLIANT
    return {
        "turn_budget": AppliedState.DECLARED_NOT_APPLIED,
        "tool_call_budget": AppliedState.DECLARED_NOT_APPLIED,
        "self_test_command": (
            AppliedState.APPLIED
            if self_test_ran
            else AppliedState.DECLARED_NOT_APPLIED
        ),
        "base_revision": AppliedState.DECLARED_NOT_APPLIED,
        "writable_paths": writable_state,
        "redacts": (
            AppliedState.APPLIED
            if executable_seam
            else AppliedState.DECLARED_NOT_APPLIED
        ),
    }
```

In `PhaseRecord`, add the field after `orchestrator_cost: float | None = None`:

```python
    self_test_outcome: SelfTestOutcome | None = None
```

And extend the class docstring with one more sentence after the
`candidate_snapshot_path`/`_digest` explanation:

```
    ``self_test_outcome`` is the harness's own record of running the
    packet's declared ``self_test_command`` once, on the executable seam
    only -- ``None`` when the seam never ran one (the in-process seam, or a
    packet declaring none), the same absence shape
    ``candidate_snapshot_path`` already uses.
```

In `_PHASE_KEYS`, add `"self_test_outcome"` to the frozenset.

In `_phase_record_to_dict`, add after `"orchestrator_cost": phase.orchestrator_cost,`:

```python
        "self_test_outcome": (
            None if phase.self_test_outcome is None
            else self_test_outcome_to_dict(phase.self_test_outcome)
        ),
```

In `_phase_record_from_dict`, add validation before the final `return
PhaseRecord(...)`:

```python
    raw_outcome = data["self_test_outcome"]
    if raw_outcome is not None and not isinstance(raw_outcome, dict):
        raise ChainRecordError(
            "persisted self_test_outcome must be an object or null"
        )
```

and add to the `PhaseRecord(...)` construction:

```python
        self_test_outcome=(
            None if raw_outcome is None else self_test_outcome_from_dict(raw_outcome)
        ),
```

In `build_chain_record`'s `PhaseRecord(...)` construction, add
`self_test_outcome=None,` and pass `self_test_ran=False` explicitly to its
`declaration_ledger(...)` call:

```python
                declaration_ledger(
                    executable_seam=executable_seam,
                    packet=packet,
                    implementer_mutations=implementer_mutations,
                    self_test_ran=False,
                ),
```

- [ ] **Step 4: Run the tests to verify the new ones pass and the golden ones now fail**

Run: `uv run pytest -q tests/test_chain_record.py`
Expected: the new tests PASS; `test_the_golden_chain_record_is_byte_identical`
and `test_the_golden_chain_record_round_trips` now FAIL (the golden fixture
predates `self_test_outcome`).

- [ ] **Step 5: Regenerate the golden fixture**

Run:

```bash
uv run python -c "
import sys
sys.path.insert(0, 'tests')
from pathlib import Path
import tempfile
from test_chain_record import _serialize, _delivered_record
with tempfile.TemporaryDirectory() as d:
    text = _serialize(_delivered_record(Path(d)))
Path('tests/data/hp6-golden-chain-record.json').write_text(text)
"
git diff tests/data/hp6-golden-chain-record.json
```

Expected diff: exactly one new line per phase, `"self_test_outcome": null,`
in its correct alphabetically-sorted position — nothing else changes. If
the diff shows anything else changing (a different `packet` field, a
different `declaration_ledger` value), stop and investigate before
proceeding; that would mean this task changed behavior the golden was
already pinning.

- [ ] **Step 6: Run the full default tier to verify everything passes**

Run: `uv run pytest -q tests/test_chain_record.py`
Expected: PASS, including the two golden tests.

Run: `uv run pytest -q`
Expected: PASS (full default-tier suite, confirming no cross-file regression).

- [ ] **Step 7: Lint**

Run: `uv run ruff check src/satyrn_evals/chain_record.py tests/test_chain_record.py`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add src/satyrn_evals/chain_record.py tests/test_chain_record.py \
  tests/data/hp6-golden-chain-record.json
git commit -m "chain_record: retain self_test_outcome, report it in the ledger"
```

---

## Task 4: `run_and_record_chain` reads the outcome off a real workspace

**Files:**
- Modify: `src/satyrn_evals/chain_record.py` (`run_and_record_chain`)
- Modify: `tests/integration/test_hp6_chain_record.py`

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces: a `ChainRecord` built by `run_and_record_chain` over the real
  executable seam now carries a real `self_test_outcome` per phase when the
  packet declares a command, with `declaration_ledger["self_test_command"]`
  matching.

- [ ] **Step 1: Write the failing integration tests**

In `tests/integration/test_hp6_chain_record.py`, add `import dataclasses` to
the imports, add `run_and_record_chain` to the `from satyrn_evals.chain_record
import (...)` line, and append:

```python
def test_a_run_and_recorded_chain_retains_a_passing_self_test(
    tmp_path: Path,
) -> None:
    """`run_and_record_chain` is the only place that reads
    `.satyrn-self-test-result.json` back off the workspace --
    `build_chain_record` has no workspace to read one from. Controls
    `self_test_command` directly rather than trusting the real task's own
    (`uv run python -m pytest tests`, not deterministic against an empty
    fixture workspace)."""
    spec = dataclasses.replace(
        load_session_spec(TASK), self_test_command=("true",)
    )
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    record = run_and_record_chain(
        TASK, load_manifest(TASK), spec, implementer, tmp_path, _grade_pass,
        tmp_path / "chain.json", base_revision="3e6607e533792ab0", **BUDGETS,
    )
    for phase in record.phases:
        assert phase.self_test_outcome is not None
        assert phase.self_test_outcome.ran is True
        assert phase.self_test_outcome.exit_code == 0
        assert phase.declaration_ledger["self_test_command"] is AppliedState.APPLIED


def test_a_run_and_recorded_chain_retains_a_failing_self_test_without_gating(
    tmp_path: Path,
) -> None:
    """The never-gates proof, end to end: a failing self-test on every
    phase does not stop the chain or flip the grader's own accept
    decision."""
    spec = dataclasses.replace(
        load_session_spec(TASK), self_test_command=("false",)
    )
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    record = run_and_record_chain(
        TASK, load_manifest(TASK), spec, implementer, tmp_path, _grade_pass,
        tmp_path / "chain.json", base_revision="3e6607e533792ab0", **BUDGETS,
    )
    for phase in record.phases:
        assert phase.self_test_outcome.ran is True
        assert phase.self_test_outcome.exit_code != 0
        assert phase.accepted is True
        assert phase.declaration_ledger["self_test_command"] is AppliedState.APPLIED
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q -m integration tests/integration/test_hp6_chain_record.py -k self_test`
Expected: FAIL — every phase's `self_test_outcome` is `None` and the ledger
reads `declared_not_applied` (nothing reads the harness file yet).

- [ ] **Step 3: Implement**

In `src/satyrn_evals/chain_record.py`'s `run_and_record_chain`, add a new
per-step dict next to the others near the top of the function body:

```python
    self_test_by_step: dict[str, SelfTestOutcome] = {}
```

In `capture_candidate(step_id)`, after the existing
`snapshots_by_step[step_id] = (str(path), digest)` line, add:

```python
        self_test_path = workspace / SELF_TEST_RESULT_NAME
        if self_test_path.is_file():
            self_test_by_step[step_id] = self_test_outcome_from_dict(
                json.loads(self_test_path.read_text(encoding="utf-8"))
            )
```

In `persist_partial()`'s per-phase loop, before the `phases.append(...)`
call, add:

```python
            self_test_outcome = self_test_by_step.get(step_id)
```

and update the `PhaseRecord(...)` construction inside that same call to add
`self_test_ran=self_test_outcome is not None,` to the `declaration_ledger(...)`
call and `self_test_outcome=self_test_outcome,` as a new keyword argument:

```python
            phases.append(
                PhaseRecord(
                    step_id=step_id,
                    packet=packets_by_step[step_id],
                    result=results_by_step[step_id],
                    accepted=accepted,
                    reason=reason,
                    implementer_mutations=implementer_mutations,
                    orchestrator_mutations=(
                        None if attribution is None else attribution.orchestrator
                    ),
                    declaration_ledger=declaration_ledger(
                        executable_seam=seam,
                        packet=packets_by_step[step_id],
                        implementer_mutations=implementer_mutations,
                        self_test_ran=self_test_outcome is not None,
                    ),
                    candidate_snapshot_path=snap_path,
                    candidate_snapshot_digest=snap_digest,
                    self_test_outcome=self_test_outcome,
                    implementer_cost=implementer_cost,
                    orchestrator_cost=orchestrator_cost,
                )
            )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q -m integration tests/integration/test_hp6_chain_record.py`
Expected: PASS, including the two existing `redacts`-focused tests in that
file (no regression).

- [ ] **Step 5: Run the full integration and default tiers**

Run: `uv run pytest -q -m integration`
Expected: PASS.

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Lint and the full gate**

Run: `just gates`
Expected: clean (pytest, ruff, lint-docs, strict Sphinx build all pass).

- [ ] **Step 7: Commit**

```bash
git add src/satyrn_evals/chain_record.py tests/integration/test_hp6_chain_record.py
git commit -m "chain_record: run_and_record_chain retains a real self_test_outcome"
```
