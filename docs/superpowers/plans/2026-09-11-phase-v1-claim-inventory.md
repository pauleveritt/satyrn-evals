# Phase V1 — claim inventory and the per-phase ledger implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Phase TE figure a committed home with a named population,
and re-derive the per-phase unit counts from retained evidence identically on
both arms.

**Architecture:** Two pure modules and one I/O script. `phase_ledger.py` turns
each arm's retained transcript plus its own phase declaration into a
per-phase ledger, refusing rather than guessing. `claim_inventory.py` is a
frozen registry of published claims, each with source, carriers, measure and
population. `scripts/reconcile_claims.py` reads retained artifacts, runs the
ledger, and writes the inventory table. Corrections touch the source document
and every in-repo carrier in the same commit.

**Tech Stack:** Python 3.14 stdlib only (`json`, `dataclasses`, `typing`).
Default tier is pure; the one integration test reads retained artifacts under
`~/satyrn-smokes` and is skipped loudly when they are absent.

**Spec:** [docs/current/phase-v-design.md](../../current/phase-v-design.md)
(V1 section; the whole design governs, especially Governance and Limits).

## Global Constraints

- Default tier runs without model, network, or subprocess; the planted
  subprocess tripwire stays armed.
- `phase_ledger.py` and `claim_inventory.py` are pure: no filesystem, no
  subprocess, no model. All I/O lives in `scripts/reconcile_claims.py`.
- `turn_ledger.py` is imported and **never modified**; its contract is
  whole-stream, this plan's is per-phase.
- Refuse rather than guess: an unattributable phase is `undecidable`, a
  missing record is `absent`; neither is a zero and neither is a count.
- Never originate a figure. V1 confirms or corrects *published* figures only.
- Corrections are recorded in place with dated blocks; the original text is
  not rewritten.
- Every carrier of a corrected claim **in this repository** is updated in the
  **same commit** as the source. A cross-repo carrier follows the two-way
  revision recording in the design's preamble.
- Evidence first: each Task runs the stated failing test before implementing.
- `docs/current/index.md:234` is the first carrier V1 must correct.

---

## File structure

| File | Responsibility |
| --- | --- |
| `src/satyrn_evals/phase_ledger.py` | Pure per-phase attribution and counts for both arms; refusal states. |
| `src/satyrn_evals/claim_inventory.py` | Frozen `INVENTORY` of published claims; source validation; table rendering. |
| `scripts/reconcile_claims.py` | I/O: load artifacts, run the ledger, write `docs/current/phase-v-claim-inventory.md`. |
| `tests/test_phase_ledger.py` | Default-tier synthetic success and refusal tests for both layouts. |
| `tests/test_claim_inventory.py` | Default-tier inventory integrity and rendering tests. |
| `tests/test_reconcile_claims.py` | Default-tier report-rendering and missing-source tests. |
| `tests/integration/test_phase_ledger_retained.py` | Marked integration: the retained attempts recomputed to their published values. |
| `docs/current/phase-v-claim-inventory.md` | Generated inventory table (committed output). |

---

## Task 1: `phase_ledger.py` — Engine attribution and counts

**Files:**
- Create: `src/satyrn_evals/phase_ledger.py`
- Test: `tests/test_phase_ledger.py`

**Interfaces:**
- Produces: `LedgerState = Literal["measured", "undecidable", "absent"]`,
  `SelfTestOutcome = Literal["pass", "fail", "not_run", "unrecorded"]`,
  `PhaseCounts(step_id, turns, tool_calls, self_test_calls, self_test_outcome)`,
  `PhaseLedger(state, reason, cells)` with `.step_ids` and `.cell(step_id)`,
  and `ledger_from_engine(transcript_text: str, chain: Mapping | None) -> PhaseLedger`.
- Consumes: `satyrn_evals.turn_ledger.events_from_pi_stdout`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_phase_ledger.py`:

```python
"""The per-phase ledger: one shape over two retained layouts.

Default tier throughout -- synthetic transcripts built in-process, no
filesystem, no subprocess.
"""

import json

from satyrn_evals.phase_ledger import ledger_from_engine


def _engine_text(phases: int, *, self_tests: int = 0) -> str:
    lines: list[str] = []
    for i in range(phases):
        lines.append(json.dumps({"adapter_marker": "turn_start", "index": i}))
        lines.append(json.dumps({"type": "session", "version": 3}))
        lines.append(json.dumps({"type": "turn_start"}))
        lines.append(
            json.dumps({"type": "tool_execution_start", "toolName": "read"})
        )
        for _ in range(self_tests if i == 0 else 0):
            lines.append(
                json.dumps(
                    {"type": "tool_execution_start", "toolName": "run_self_test"}
                )
            )
    return "\n".join(lines) + "\n"


def _chain(step_ids: tuple[str, ...], outcomes: dict[str, object] | None = None):
    outcomes = outcomes or {}
    return {
        "phases": [
            {"step_id": step_id, "self_test_outcome": outcomes.get(step_id)}
            for step_id in step_ids
        ]
    }


PHASES = ("phase-1-home", "phase-2-board", "phase-3-add", "phase-4-resolve-reopen")


def test_engine_splits_positional_sessions_against_declared_phases() -> None:
    ledger = ledger_from_engine(_engine_text(4, self_tests=2), _chain(PHASES))

    assert ledger.state == "measured"
    assert ledger.step_ids == PHASES
    assert [cell.turns for cell in ledger.cells] == [1, 1, 1, 1]
    assert [cell.tool_calls for cell in ledger.cells] == [3, 1, 1, 1]
    assert ledger.cell("phase-1-home").self_test_calls == 2


def test_engine_refuses_when_sessions_disagree_with_declared_phases() -> None:
    """The named refusal: a count that does not match its chain is never a
    per-phase number."""
    ledger = ledger_from_engine(_engine_text(4), _chain(PHASES[:3]))

    assert ledger.state == "undecidable"
    assert "4 session blocks against 3 declared phases" in (ledger.reason or "")
    assert ledger.cells == ()


def test_engine_is_absent_without_a_chain_record() -> None:
    ledger = ledger_from_engine(_engine_text(4), None)

    assert ledger.state == "absent"
    assert ledger.cells == ()


def test_engine_self_test_outcome_reads_the_chain_not_the_transcript() -> None:
    outcomes = {
        "phase-1-home": {"ran": True, "exit_code": 0},
        "phase-2-board": {"ran": True, "exit_code": 1},
        "phase-3-add": {"ran": False, "exit_code": None},
        "phase-4-resolve-reopen": None,
    }
    ledger = ledger_from_engine(_engine_text(4), _chain(PHASES, outcomes))

    assert [cell.self_test_outcome for cell in ledger.cells] == [
        "pass",
        "fail",
        "not_run",
        "unrecorded",
    ]


def test_engine_self_test_outcome_is_unrecorded_when_exit_code_is_missing() -> None:
    """A run without a readable exit code is unknown, never a pass."""
    outcomes = {"phase-1-home": {"ran": True}}  # no exit_code at all
    ledger = ledger_from_engine(_engine_text(4), _chain(PHASES, outcomes))

    assert ledger.cell("phase-1-home").self_test_outcome == "unrecorded"
    assert ledger.cell("phase-2-board").self_test_outcome == "unrecorded"


def test_engine_ignores_an_event_before_the_first_session() -> None:
    """A stray event outside any session block is not attributed to phase 1."""
    stray = json.dumps({"type": "tool_execution_start", "toolName": "bash"})
    text = stray + "\n" + _engine_text(4)

    ledger = ledger_from_engine(text, _chain(PHASES))

    assert ledger.state == "measured"
    assert [cell.tool_calls for cell in ledger.cells] == [1, 1, 1, 1]


def test_engine_refuses_a_chain_phase_without_a_step_id() -> None:
    chain = {"phases": [{"step_id": "phase-1-home"}, {"no_step": True}]}

    ledger = ledger_from_engine(_engine_text(2), chain)

    assert ledger.state == "undecidable"
    assert "no step_id" in (ledger.reason or "")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_phase_ledger.py`
Expected: collection error (`satyrn_evals.phase_ledger` does not exist yet).

- [ ] **Step 3: Implement `phase_ledger.py`**

Create `src/satyrn_evals/phase_ledger.py`:

```python
"""Per-phase attribution and counts over retained attempt transcripts.

Pure: text and already-parsed records in, a ledger out. No filesystem, no
subprocess, no model. ``turn_ledger.py`` is imported for the Engine
transcript's stream parsing and is never modified.

Two layouts, two attribution mechanisms, one shape:

- **Baseline** (``agentclinic-session-phased`` through ``pi_session``): every
  retained ``event`` carries its own ``step_id``, and ``session-record.json``'s
  ``steps`` list is the declared phase order.
- **Engine** (the packet route through ``pi_implementer``): the transcript is
  four positional ``session`` blocks with no phase label; the chain record's
  ``phases`` list is the only authority mapping block N to phase N, so the
  count is cross-checked against it before any per-phase number is reported.

A ledger that cannot attribute a phase is ``undecidable``; a missing record is
``absent``. Neither is a zero, and neither is a per-phase number.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from satyrn_evals.turn_ledger import events_from_pi_stdout

type LedgerState = Literal["measured", "undecidable", "absent"]
type SelfTestOutcome = Literal["pass", "fail", "not_run", "unrecorded"]


@dataclass(frozen=True, slots=True)
class PhaseCounts:
    """One phase's counts.

    ``self_test_calls``/``self_test_outcome`` are ``None`` on an arm whose
    self-test evidence this cycle cannot derive in both directions; V2 owns
    that Baseline measure and V3 records it as arm-asymmetric evidence if it
    stays undecidable.
    """

    step_id: str
    turns: int
    tool_calls: int
    self_test_calls: int | None
    self_test_outcome: SelfTestOutcome | None


@dataclass(frozen=True, slots=True)
class PhaseLedger:
    """A per-phase ledger, or the named reason it is not one."""

    state: LedgerState
    reason: str | None
    cells: tuple[PhaseCounts, ...]

    @property
    def step_ids(self) -> tuple[str, ...]:
        return tuple(cell.step_id for cell in self.cells)

    def cell(self, step_id: str) -> PhaseCounts | None:
        for cell in self.cells:
            if cell.step_id == step_id:
                return cell
        return None


def _self_test_outcome(record: object) -> SelfTestOutcome:
    """The chain's independently recorded self-test verdict.

    ``not_run`` and ``unrecorded`` are distinct on purpose: "the command was
    never run" and "the record does not say what happened" are different
    findings, and neither is a pass.
    """
    if not isinstance(record, Mapping):
        return "unrecorded"
    if record.get("ran") is not True:
        return "not_run"
    exit_code = record.get("exit_code")
    if not isinstance(exit_code, int):
        return "unrecorded"
    return "pass" if exit_code == 0 else "fail"


def _engine_session_blocks(text: str) -> list[list[dict[str, object]]]:
    """The transcript's ``session``-delimited blocks, in file order.

    ``events_from_pi_stdout`` already drops ``pi_implementer``'s own
    ``adapter_marker`` lines; a real pi ``session`` event is the boundary.
    """
    blocks: list[list[dict[str, object]]] = []
    for event in events_from_pi_stdout(text):
        if event.get("type") == "session":
            blocks.append([])
            continue
        if blocks:
            blocks[-1].append(event)
    return blocks


def ledger_from_engine(
    transcript_text: str,
    chain: Mapping[str, object] | None,
) -> PhaseLedger:
    """Attribute an Engine transcript's positional blocks to the chain's
    declared phases, then count each phase."""
    if chain is None:
        return PhaseLedger("absent", "no chain record", ())
    phases = chain.get("phases")
    if not isinstance(phases, list):
        return PhaseLedger("undecidable", "chain record has no phases list", ())
    declared: list[str] = []
    outcomes: list[SelfTestOutcome] = []
    for phase in phases:
        if not isinstance(phase, Mapping) or not isinstance(phase.get("step_id"), str):
            return PhaseLedger("undecidable", "a chain phase has no step_id", ())
        declared.append(phase["step_id"])
        outcomes.append(_self_test_outcome(phase.get("self_test_outcome")))
    blocks = _engine_session_blocks(transcript_text)
    if len(blocks) != len(declared):
        return PhaseLedger(
            "undecidable",
            f"{len(blocks)} session blocks against {len(declared)} declared phases",
            (),
        )
    cells = tuple(
        PhaseCounts(
            step_id=step_id,
            turns=sum(1 for event in block if event.get("type") == "turn_start"),
            tool_calls=sum(
                1 for event in block if event.get("type") == "tool_execution_start"
            ),
            self_test_calls=sum(
                1
                for event in block
                if event.get("type") == "tool_execution_start"
                and event.get("toolName") == "run_self_test"
            ),
            self_test_outcome=outcome,
        )
        for step_id, block, outcome in zip(declared, blocks, outcomes, strict=True)
    )
    return PhaseLedger("measured", None, cells)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_phase_ledger.py`
Expected: PASS, all 7 tests.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/satyrn_evals/phase_ledger.py tests/test_phase_ledger.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/phase_ledger.py tests/test_phase_ledger.py
git commit -m "phase_ledger: attribute Engine phases and count per phase"
```

---

## Task 2: `phase_ledger.py` — Baseline attribution and counts

**Files:**
- Modify: `src/satyrn_evals/phase_ledger.py`
- Modify: `tests/test_phase_ledger.py`

**Interfaces:**
- Produces: `ledger_from_baseline(transcript_text: str, session_record: Mapping | None) -> PhaseLedger`.
- Consumes: `PhaseCounts`, `PhaseLedger` (Task 1).

- [ ] **Step 1: Write the failing tests**

**Note:** this task's tests reference `ledger_from_baseline`, which Task 2 defines. Amend the existing import line to `from satyrn_evals.phase_ledger import (ledger_from_baseline, ledger_from_engine)` in the same edit, then append these tests. (That makes Task 2's RED a collection error — the name does not exist yet — rather than a `NameError`.)

```python
def _baseline_text(steps: tuple[str, ...], *, omit_step: str | None = None) -> str:
    lines = [json.dumps({"version": 1, "type": "session_started"})]
    for step_id in steps:
        line = {
            "version": 1,
            "type": "event",
            "step_id": step_id,
            "kind": "other",
            "payload": {"type": "turn_start"},
        }
        if step_id == omit_step:
            line.pop("step_id")
        lines.append(json.dumps(line))
        lines.append(
            json.dumps(
                {
                    "version": 1,
                    "type": "event",
                    "step_id": step_id,
                    "kind": "tool_end",
                    "payload": {"type": "tool_execution_end"},
                }
            )
        )
    return "\n".join(lines) + "\n"


def _session_record(step_ids: tuple[str, ...]) -> dict[str, object]:
    return {"steps": [{"step_id": step_id} for step_id in step_ids]}


def test_baseline_attributes_by_each_events_own_step_id() -> None:
    ledger = ledger_from_baseline(_baseline_text(PHASES), _session_record(PHASES))

    assert ledger.state == "measured"
    assert [cell.turns for cell in ledger.cells] == [1, 1, 1, 1]
    assert [cell.tool_calls for cell in ledger.cells] == [1, 1, 1, 1]
    assert all(cell.self_test_calls is None for cell in ledger.cells)


def test_baseline_refuses_an_event_missing_its_step_id() -> None:
    """The design's named refusal: a transcript that cannot be attributed is
    undecidable, never a per-phase number."""
    text = _baseline_text(PHASES, omit_step="phase-2-board")

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "step_id" in (ledger.reason or "")
    assert ledger.cells == ()


def test_baseline_refuses_an_event_outside_the_records_steps() -> None:
    text = _baseline_text(PHASES)
    text += json.dumps(
        {
            "version": 1,
            "type": "event",
            "step_id": "phase-9-ghost",
            "payload": {"type": "turn_start"},
        }
    )

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "phase-9-ghost" in (ledger.reason or "")


def test_baseline_refuses_an_unparseable_line() -> None:
    text = _baseline_text(PHASES) + "not json\n"

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "unparseable" in (ledger.reason or "")


def test_baseline_is_absent_without_a_session_record() -> None:
    ledger = ledger_from_baseline(_baseline_text(PHASES), None)

    assert ledger.state == "absent"
    assert ledger.cells == ()


def test_baseline_refuses_a_record_without_steps() -> None:
    ledger = ledger_from_baseline(_baseline_text(PHASES), {"nope": True})

    assert ledger.state == "undecidable"
    assert "steps" in (ledger.reason or "")


def test_baseline_refuses_a_record_step_without_a_step_id() -> None:
    ledger = ledger_from_baseline(
        _baseline_text(PHASES), {"steps": [{"not_step_id": 1}]}
    )

    assert ledger.state == "undecidable"
    assert "no step_id" in (ledger.reason or "")


def test_baseline_refuses_a_non_object_line() -> None:
    text = _baseline_text(PHASES) + "[1, 2]\n"

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "non-object" in (ledger.reason or "")


def test_baseline_refuses_an_event_without_a_payload() -> None:
    text = _baseline_text(PHASES).rstrip("\n") + "\n" + json.dumps(
        {"version": 1, "type": "event", "step_id": "phase-1-home"}
    ) + "\n"

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "payload" in (ledger.reason or "")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_phase_ledger.py -k baseline`
Expected: collection error (`ledger_from_baseline` does not exist yet).

- [ ] **Step 3: Implement `ledger_from_baseline`**

**Note:** add `import json` back to the module's imports (Task 1 dropped it as unused there; only this Baseline half calls `json.loads`), then append this function:

```python
def ledger_from_baseline(
    transcript_text: str,
    session_record: Mapping[str, object] | None,
) -> PhaseLedger:
    """Attribute a Baseline transcript by each retained event's own
    ``step_id``, with ``session-record.json``'s step list as the declared
    order and the bounds check."""
    if session_record is None:
        return PhaseLedger("absent", "no session record", ())
    steps = session_record.get("steps")
    if not isinstance(steps, list):
        return PhaseLedger("undecidable", "session record has no steps list", ())
    declared: list[str] = []
    for step in steps:
        if not isinstance(step, Mapping) or not isinstance(step.get("step_id"), str):
            return PhaseLedger("undecidable", "a session step has no step_id", ())
        declared.append(step["step_id"])
    turns = dict.fromkeys(declared, 0)
    tool_calls = dict.fromkeys(declared, 0)
    for line in transcript_text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return PhaseLedger("undecidable", "an unparseable transcript line", ())
        if not isinstance(event, Mapping):
            return PhaseLedger("undecidable", "a non-object transcript line", ())
        if event.get("type") != "event":
            continue
        step_id = event.get("step_id")
        if not isinstance(step_id, str) or step_id not in turns:
            return PhaseLedger(
                "undecidable",
                f"an event's step_id {step_id!r} is outside the record's steps",
                (),
            )
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            return PhaseLedger("undecidable", "an event carried no payload", ())
        if payload.get("type") == "turn_start":
            turns[step_id] += 1
        elif payload.get("type") == "tool_execution_end":
            tool_calls[step_id] += 1
    cells = tuple(
        PhaseCounts(step_id, turns[step_id], tool_calls[step_id], None, None)
        for step_id in declared
    )
    return PhaseLedger("measured", None, cells)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_phase_ledger.py`
Expected: PASS, all 16 tests across Tasks 1–2.

- [ ] **Step 5: Run the default-tier suite for regressions**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Lint**

Run: `uv run ruff check src/satyrn_evals/phase_ledger.py tests/test_phase_ledger.py`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add src/satyrn_evals/phase_ledger.py tests/test_phase_ledger.py
git commit -m "phase_ledger: attribute Baseline phases by step_id"
```

---

## Task 3: `claim_inventory.py` — the declared inventory

**Files:**
- Create: `src/satyrn_evals/claim_inventory.py`
- Test: `tests/test_claim_inventory.py`

**Interfaces:**
- Produces: `ClaimStatus`, `ClaimLevel`, `ClaimRecord(id, quote, source,
  carriers, level, measure, population, status)`, `INVENTORY: tuple[ClaimRecord, ...]`,
  `validate_sources(root: Path = Path(".")) -> tuple[str, ...]`,
  `render_table(records: Sequence[ClaimRecord] = INVENTORY) -> str`.

**Note on the inventory contents.** This is the analytical core of V1: one
record per published figure or framing a recorded phase decision rests on.
The seed below covers every figure the design itself names plus the per-phase
rows of the screen; the executor extends it by scanning the three named
carrier documents for any remaining `N of M` figure or quoted framing, adding
one record each, before running Task 4. Every `source`/`carriers` path is
asserted to exist.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_claim_inventory.py`:

```python
"""The claim inventory: frozen records, valid sources, one table.

Default tier: pure, no filesystem read beyond the repository's own paths.
"""

from pathlib import Path

from satyrn_evals.claim_inventory import (
    INVENTORY,
    ClaimRecord,
    render_table,
    validate_sources,
)

ROOT = Path(__file__).resolve().parent.parent


def test_every_cited_source_path_exists() -> None:
    assert validate_sources(ROOT) == ()


def test_ids_are_unique() -> None:
    ids = [record.id for record in INVENTORY]
    assert len(ids) == len(set(ids))


def test_a_record_defaults_to_unreconciled() -> None:
    """The default is the pre-reconciliation state; V1/V2 then settle records
    in place, so the test pins the default rather than the whole tuple."""
    record = ClaimRecord(
        id="example",
        quote="x",
        source="ROADMAP.md",
        carriers=(),
        level="unit",
        measure="turns",
        population="none",
    )
    assert record.status == "unreconciled"


def test_both_levels_are_present() -> None:
    levels = {record.level for record in INVENTORY}
    assert levels == {"unit", "claim"}


def test_the_table_names_every_record_and_its_population() -> None:
    table = render_table(
        (
            ClaimRecord(
                id="example",
                quote="6 of 18",
                source="docs/current/te6-explain-and-decide.md",
                carriers=(),
                level="claim",
                measure="completion_rate",
                population="18 Engine attempts",
            ),
        )
    )
    assert "example" in table
    assert "6 of 18" in table
    assert "18 Engine attempts" in table


def test_validate_sources_names_a_missing_path(tmp_path: Path) -> None:
    record = ClaimRecord(
        id="missing",
        quote="x",
        source="does/not/exist.md",
        carriers=("also/missing.md",),
        level="unit",
        measure="turns",
        population="none",
    )
    missing = validate_sources(tmp_path, records=(record,))
    assert "does/not/exist.md" in missing
    assert "also/missing.md" in missing
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_claim_inventory.py`
Expected: collection error (`satyrn_evals.claim_inventory` does not exist yet).

- [ ] **Step 3: Implement `claim_inventory.py`**

Create `src/satyrn_evals/claim_inventory.py`:

```python
"""The Phase TE claim inventory: what was claimed, against what, for whom.

Declared in code as a frozen tuple, the way ``scripts/rescore_seams.py``'s
``SEAM_MAP`` declares its map before it is used -- so a reviewer can diff the
claims, and every cited path is testable. The human-readable table is
generated from this tuple, never written twice.

Statuses begin ``unreconciled``. V1 settles the ``level == "unit"`` records
from the per-phase ledger; V2 settles the rest with the claim-level measures;
V3 assigns the final status to every record. A record is never deleted when a
correction lands -- the correction is a dated block at its source.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

type ClaimStatus = Literal[
    "unreconciled",
    "confirmed",
    "corrected",
    "not_derivable",
    "claim_measure_mismatch",
]
type ClaimLevel = Literal["unit", "claim"]


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    """One published figure or framing, with the population it is about.

    ``source`` is the document where the figure was first published; each
    entry of ``carriers`` is another document that repeats it. Both carry an
    optional ``:line`` suffix for a human reader; validation strips it.
    """

    id: str
    quote: str
    source: str
    carriers: tuple[str, ...]
    level: ClaimLevel
    measure: str
    population: str
    status: ClaimStatus = "unreconciled"


#: The V1 inventory. Unit-level records are re-derived by the per-phase
#: ledger; claim-level records are V2's.
INVENTORY: tuple[ClaimRecord, ...] = (
    ClaimRecord(
        id="u-baseline-01-per-phase-turns",
        quote="43 (7/22/6/8)",
        source="docs/current/te4-screen-result.md:28",
        carriers=("ROADMAP.md:289",),
        level="unit",
        measure="turns per step_id",
        population="Baseline-01, 2026-09-11-te4-screen-baseline-01",
    ),
    ClaimRecord(
        id="u-baseline-02-per-phase-turns",
        quote="32 (9/8/9/6)",
        source="docs/current/te4-screen-result.md:29",
        carriers=("ROADMAP.md:289",),
        level="unit",
        measure="turns per step_id",
        population="Baseline-02, 2026-09-11-te4-screen-baseline-02",
    ),
    ClaimRecord(
        id="u-engine-01-per-phase-turns",
        quote="47 (6/8/10/23)",
        source="docs/current/te4-screen-result.md:30",
        carriers=(),
        level="unit",
        measure="turns per session",
        population="Engine-01, 2026-09-11-te4-screen-engine-01",
    ),
    ClaimRecord(
        id="u-engine-02-per-phase-turns",
        quote="45 (6/7/9/23)",
        source="docs/current/te4-screen-result.md:31",
        carriers=(),
        level="unit",
        measure="turns per session",
        population="Engine-02, 2026-09-11-te4-screen-engine-02",
    ),
    ClaimRecord(
        id="u-completion-turn-distribution",
        quote="43, 49, 44, 36",
        source="docs/current/te4-completion-recurrence-check-result.md:181",
        carriers=(),
        level="unit",
        measure="whole-attempt turns",
        population="the 4 recorded Engine completions",
    ),
    ClaimRecord(
        id="u-recurrence-01-per-phase-turns",
        quote="44 (6/8/11/19)",
        source="docs/current/te4-completion-recurrence-check-result.md:13",
        carriers=(),
        level="unit",
        measure="turns per session",
        population="2026-09-11-recurrence-engine-01",
    ),
    ClaimRecord(
        id="u-recurrence-03-per-phase-turns",
        quote="36 (6/8/8/14)",
        source="docs/current/te4-completion-recurrence-check-result.md:15",
        carriers=(),
        level="unit",
        measure="turns per session",
        population="2026-09-11-recurrence-engine-03",
    ),
    ClaimRecord(
        id="c-engine-population",
        quote="18 Engine attempts and 3 Baseline attempts",
        source="docs/current/te6-explain-and-decide.md:38",
        carriers=("ROADMAP.md:292",),
        level="claim",
        measure="population statement",
        population="agentclinic-complaint-lifecycle, Phase TE sequence",
    ),
    ClaimRecord(
        id="c-baseline-3-of-3",
        quote="Baseline: **3 of 3 complete**",
        source="docs/current/te6-explain-and-decide.md:51",
        carriers=("ROADMAP.md:292",),
        level="claim",
        measure="completion_rate",
        population="3 Baseline attempts on agentclinic-complaint-lifecycle",
    ),
    ClaimRecord(
        id="c-contemporaneous-screen-tie-2-of-2",
        quote="2/2 vs 2/2",
        source="docs/current/te6-explain-and-decide.md:67",
        carriers=("docs/current/te6-explain-and-decide.md:251",),
        level="claim",
        measure="completion_rate",
        population="the final screen, both configurations fresh on the identical prompt",
    ),
    ClaimRecord(
        id="c-completion-6-of-18",
        quote="6 of 18",
        source="docs/current/te6-explain-and-decide.md:54",
        carriers=(
            "ROADMAP.md:292",
            "docs/current/index.md:234",
            "docs/current/te4-screen-result.md:43",
        ),
        level="claim",
        measure="completion_rate",
        population="18 Engine attempts on agentclinic-complaint-lifecycle",
    ),
    ClaimRecord(
        id="c-completion-4-of-16",
        quote="4 of 16",
        source="docs/current/te4-completion-recurrence-check-result.md:22",
        carriers=("ROADMAP.md:275", "docs/current/index.md:208"),
        level="claim",
        measure="completion_rate",
        population="16 Engine attempts before the 2026-09-11 screen",
    ),
    ClaimRecord(
        id="c-destroyed-13-of-15",
        quote="destroyed in 13 of 15",
        source="docs/current/te6-explain-and-decide.md:147",
        carriers=(),
        level="claim",
        measure="destructive_edit",
        population="15 phase-4-reaching Engine attempts",
    ),
    ClaimRecord(
        id="c-restored-9-of-15",
        quote="9 of 15",
        source="docs/current/te6-explain-and-decide.md:169",
        carriers=(),
        level="claim",
        measure="restoration",
        population="15 phase-4-reaching Engine attempts",
    ),
    ClaimRecord(
        id="c-redirect-fixed-1-of-9",
        quote="1 of 9",
        source="docs/current/te6-explain-and-decide.md:174",
        carriers=(),
        level="claim",
        measure="redirect_trap_resolution",
        population="9 attempts showing the redirect-trap signature",
    ),
    ClaimRecord(
        id="c-nonrestore-0-of-6",
        quote="0 of 6",
        source="docs/current/te4-completion-recurrence-check-result.md:178",
        carriers=("docs/current/index.md:204", "ROADMAP.md:272"),
        level="claim",
        measure="completion_rate",
        population="6 non-restoring phase-4-reaching Engine attempts",
    ),
    ClaimRecord(
        id="c-restore-4-of-7",
        quote="4 of 7",
        source="docs/current/te4-completion-recurrence-check-result.md:179",
        carriers=("docs/current/index.md:205", "ROADMAP.md:272"),
        level="claim",
        measure="completion_rate",
        population="7 restoring phase-4-reaching Engine attempts",
    ),
    ClaimRecord(
        id="c-phase4-denominator-6-of-10",
        quote="6 of 8",
        source="docs/current/te6-explain-and-decide.md:87",
        carriers=("docs/current/te6-explain-and-decide.md:93",),
        level="claim",
        measure="denominator_binding",
        population="10 attempts under the current prompt, not 8",
    ),
    ClaimRecord(
        id="c-redirect-6-of-9",
        quote="6 of 9",
        source="docs/current/te4-phase4-guardrail-reverification-result.md:30",
        carriers=("docs/current/index.md:164",),
        level="claim",
        measure="redirect_trap_occurrence",
        population="9 phase-4-reaching Engine attempts at that round",
    ),
    ClaimRecord(
        id="c-fabricated-report-n1",
        quote="fabricated a fully invented passing pytest transcript",
        source="docs/current/te6-explain-and-decide.md:110",
        carriers=("docs/current/te4-screen-result.md:20", "ROADMAP.md:282"),
        level="claim",
        measure="verification_claim",
        population="1 Engine screen attempt (screen-engine-01)",
    ),
)


def validate_sources(
    root: Path = Path("."),
    *,
    records: Sequence[ClaimRecord] = INVENTORY,
) -> tuple[str, ...]:
    """Every path a record cites that does not exist under ``root``.

    The ``:line`` suffix is for readers; only the path is checked, so a
    reflow that moves a figure within its file does not fail this test."""
    missing: list[str] = []
    for record in records:
        for cited in (record.source, *record.carriers):
            path = cited.rsplit(":", 1)[0]
            if not (root / path).exists():
                missing.append(cited)
    return tuple(missing)


def render_table(records: Sequence[ClaimRecord] = INVENTORY) -> str:
    """The inventory as a Markdown table, generated from the tuple."""
    header = (
        "| id | level | status | measure | population | quote | source | carriers |",
        "|---|---|---|---|---|---|---|---|",
    )
    rows = [
        "| {id} | {level} | {status} | {measure} | {population} | {quote} | "
        "{source} | {carriers} |".format(
            id=record.id,
            level=record.level,
            status=record.status,
            measure=record.measure,
            population=record.population,
            quote=record.quote,
            source=record.source,
            carriers=", ".join(record.carriers) or "—",
        )
        for record in records
    ]
    return "\n".join((*header, *rows))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_claim_inventory.py`
Expected: PASS, all 6 tests.

- [ ] **Step 5: Extend the seed to the full inventory**

Scan the three named carriers and the TE result documents for any remaining
`N of M` figure or quoted framing a recorded decision rests on:

```bash
rg -n 'of [0-9]+|of the|not supported|reliable' \
  docs/current/te6-explain-and-decide.md docs/current/te4-screen-result.md \
  docs/current/index.md ROADMAP.md docs/current/te4-phase4-guardrail-reverification-result.md
```

For each figure not already represented, add one `ClaimRecord` with its
`level` (`unit` if it is a single attempt/phase's own count, `claim` if it is
an aggregate rate or framing), its `measure`, and its `population`. Re-run the
tests; `validate_sources` must stay empty.

- [ ] **Step 6: Lint**

Run: `uv run ruff check src/satyrn_evals/claim_inventory.py tests/test_claim_inventory.py`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add src/satyrn_evals/claim_inventory.py tests/test_claim_inventory.py
git commit -m "claim_inventory: declare the Phase TE claim inventory"
```

---

## Task 4: `scripts/reconcile_claims.py` — the generated table

**Files:**
- Create: `scripts/reconcile_claims.py`
- Test: `tests/test_reconcile_claims.py`
- Create (generated): `docs/current/phase-v-claim-inventory.md`

**Interfaces:**
- Consumes: `phase_ledger.ledger_from_engine`, `phase_ledger.ledger_from_baseline`,
  `claim_inventory.INVENTORY`, `claim_inventory.render_table`,
  `claim_inventory.validate_sources`.
- Produces: `AttemptSpec(label, run_dir, arm)` and
  `render_report(ledgers: Sequence[tuple[AttemptSpec, PhaseLedger]]) -> str`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reconcile_claims.py`:

```python
"""The reconciliation report: rendered from the ledger, sources checked.

Default tier: `render_report` is pure; the `--check` path is exercised
against a temporary root.
"""

import sys
from pathlib import Path

from satyrn_evals.claim_inventory import ClaimRecord
from satyrn_evals.phase_ledger import PhaseCounts, PhaseLedger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from reconcile_claims import (  # noqa: E402  # scripts/ added via sys.path above
    AttemptSpec,
    render_report,
    validate_root,
)


def _spec(label: str, arm: str) -> AttemptSpec:
    return AttemptSpec(label=label, run_dir=label, arm=arm)


def test_render_report_names_every_attempt_and_its_state() -> None:
    ledger = PhaseLedger(
        "measured",
        None,
        (PhaseCounts("phase-1-home", 6, 3, 1, "fail"),),
    )
    report = render_report(((_spec("engine-01", "engine"), ledger),))
    assert "engine-01" in report
    assert "phase-1-home" in report
    assert "6" in report


def test_render_report_carries_a_refusal_as_a_word_not_a_zero() -> None:
    ledger = PhaseLedger("undecidable", "2 session blocks against 4 declared phases", ())
    report = render_report(((_spec("engine-02", "engine"), ledger),))
    assert "undecidable" in report
    assert "2 session blocks against 4 declared phases" in report


def test_render_report_records_the_revision_and_artifact_digests() -> None:
    """V1 Currency rule: the HEAD revision and each artifact's sha256 are
    recorded before measuring."""
    ledger = PhaseLedger(
        "measured", None, (PhaseCounts("phase-1-home", 6, 3, 1, "fail"),)
    )
    report = render_report(
        ((_spec("engine-01", "engine"), ledger),),
        head="a" * 40,
        digests={"x/transcript.jsonl": "b" * 64},
    )
    assert "a" * 40 in report
    assert "b" * 64 in report
    assert "x/transcript.jsonl" in report


def test_validate_root_names_a_missing_citation(tmp_path: Path) -> None:
    record = ClaimRecord(
        id="missing",
        quote="x",
        source="nope.md",
        carriers=(),
        level="unit",
        measure="turns",
        population="none",
    )
    assert "nope.md" in validate_root(tmp_path, records=(record,))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_reconcile_claims.py`
Expected: collection error (`reconcile_claims` does not exist yet).

- [ ] **Step 3: Implement `scripts/reconcile_claims.py`**

Create `scripts/reconcile_claims.py`:

```python
#!/usr/bin/env python3
"""Reconcile the Phase TE claim inventory against the per-phase ledger.

Reads retained artifacts already on disk under a runs root, runs the pure
per-phase ledger over each named attempt, and writes
``docs/current/phase-v-claim-inventory.md``. No model, no network. The
artifacts live outside the repository, so this script is run explicitly; the
default tier never needs it.

Never originates a figure. The report states each attempt's recomputed
per-phase values beside the inventory's published values and the population
each belongs to; a refusal is printed as its named state, never as a zero.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.claim_inventory import (
    INVENTORY,
    ClaimRecord,
    render_table,
    validate_sources,
)
from satyrn_evals.phase_ledger import (
    PhaseLedger,
    ledger_from_baseline,
    ledger_from_engine,
)

DEFAULT_RUNS_ROOT = Path(os.path.expanduser("~/satyrn-smokes"))
DEFAULT_OUTPUT = Path("docs/current/phase-v-claim-inventory.md")


@dataclass(frozen=True, slots=True)
class AttemptSpec:
    label: str
    run_dir: str
    arm: str


#: The attempts whose per-phase values are published. Engine transcripts are
#: `harness/.satyrn-implementer-transcript.jsonl`; Baseline transcripts are
#: nested under a session directory and carry a `session-record.json` sister.
ATTEMPTS: tuple[AttemptSpec, ...] = (
    AttemptSpec("baseline-01", "2026-09-11-te4-screen-baseline-01", "baseline"),
    AttemptSpec("baseline-02", "2026-09-11-te4-screen-baseline-02", "baseline"),
    AttemptSpec("engine-01", "2026-09-11-te4-screen-engine-01", "engine"),
    AttemptSpec("engine-02", "2026-09-11-te4-screen-engine-02", "engine"),
    AttemptSpec("round2-01", "2026-09-11-p4guardrail-round2-engine-01", "engine"),
    AttemptSpec("round2-02", "2026-09-11-p4guardrail-round2-engine-02", "engine"),
    AttemptSpec("recurrence-01", "2026-09-11-recurrence-engine-01", "engine"),
    AttemptSpec("recurrence-03", "2026-09-11-recurrence-engine-03", "engine"),
)


def _load_json(path: Path) -> Mapping[str, object] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, Mapping) else None


def ledger_for(spec: AttemptSpec, runs_root: Path) -> PhaseLedger:
    run = runs_root / spec.run_dir
    if spec.arm == "engine":
        transcript = run / "harness" / ".satyrn-implementer-transcript.jsonl"
        if not transcript.exists():
            return PhaseLedger("absent", "no implementer transcript", ())
        return ledger_from_engine(
            transcript.read_text(encoding="utf-8", errors="replace"),
            _load_json(run / "chain.json"),
        )
    transcript = next(run.rglob("transcript.jsonl"), None)
    record = next(run.rglob("session-record.json"), None)
    if transcript is None:
        return PhaseLedger("absent", "no session transcript", ())
    return ledger_from_baseline(
        transcript.read_text(encoding="utf-8", errors="replace"),
        _load_json(record) if record is not None else None,
    )


def artifacts_for(spec: AttemptSpec, runs_root: Path) -> tuple[Path, ...]:
    """Every retained artifact this attempt's ledger reads."""
    run = runs_root / spec.run_dir
    if spec.arm == "engine":
        return (
            run / "harness" / ".satyrn-implementer-transcript.jsonl",
            run / "chain.json",
        )
    transcript = next(run.rglob("transcript.jsonl"), None)
    record = next(run.rglob("session-record.json"), None)
    return tuple(path for path in (transcript, record) if path is not None)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _head_commit() -> str:
    """The revision the artifacts were read under (V1 Currency rule)."""
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() or "unrecorded"


def render_report(
    ledgers: Sequence[tuple[AttemptSpec, PhaseLedger]],
    *,
    head: str = "unrecorded",
    digests: Mapping[str, str] | None = None,
) -> str:
    digests = digests or {}
    header = ["# Phase V1 — per-phase ledger", "", f"**HEAD:** `{head}`", ""]
    lines = [
        "| attempt | arm | state | reason | phases | per-phase turns | per-phase tool calls |",
        "|---|---|---|---|---|---|---|",
    ]
    for spec, ledger in ledgers:
        phases = ", ".join(cell.step_id for cell in ledger.cells) or "—"
        turns = ", ".join(str(cell.turns) for cell in ledger.cells) or "—"
        tools = ", ".join(str(cell.tool_calls) for cell in ledger.cells) or "—"
        lines.append(
            f"| {spec.label} | {spec.arm} | {ledger.state} | "
            f"{ledger.reason or '—'} | {phases} | {turns} | {tools} |"
        )
    provenance = ["", "## Artifact digests (sha256)", "", "| artifact | sha256 |", "|---|---|"]
    provenance += [f"| {path} | {digest} |" for path, digest in digests.items()]
    return "\n".join(
        (
            *header,
            *lines,
            *provenance,
            "",
            "## Claim inventory",
            "",
            render_table(),
            "",
        )
    )


def validate_root(
    root: Path,
    *,
    records: Sequence[ClaimRecord] = INVENTORY,
) -> tuple[str, ...]:
    return validate_sources(root, records=records)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    missing = validate_root(Path("."))
    if missing:
        print("missing cited sources:", *missing, sep="\n  ", file=sys.stderr)
        return 1
    head = _head_commit()
    digests: dict[str, str] = {}
    for spec in ATTEMPTS:
        for artifact in artifacts_for(spec, args.runs_root):
            if artifact.exists():
                digests[str(artifact)] = _sha256(artifact)
    ledgers = tuple((spec, ledger_for(spec, args.runs_root)) for spec in ATTEMPTS)
    report = render_report(ledgers, head=head, digests=digests)
    if args.check:
        print(report)
        return 0
    args.output.write_text(report, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_reconcile_claims.py`
Expected: PASS, all 4 tests.

- [ ] **Step 5: Generate the table against the retained attempts**

Run:

```bash
uv run python scripts/reconcile_claims.py --runs-root ~/satyrn-smokes
```

Expected: `wrote docs/current/phase-v-claim-inventory.md`; the table shows
`measured` for all eight attempts with per-phase turns
`7, 22, 6, 8`, `9, 8, 9, 6`, `6, 8, 10, 23`, `6, 7, 9, 23`,
`6, 8, 11, 19`, `6, 8, 8, 14`, plus the two round-2 completions
`6, 8, 8, 21` and `6, 8, 7, 28` (whose whole-attempt totals 43 and 49 are two
of the four in `u-completion-turn-distribution`).

- [ ] **Step 6: Lint and the default gate**

Run: `uv run ruff check scripts/reconcile_claims.py tests/test_reconcile_claims.py`
Expected: clean.

Run: `just gates`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add scripts/reconcile_claims.py tests/test_reconcile_claims.py \
  docs/current/phase-v-claim-inventory.md
git commit -m "reconcile_claims: generate the inventory table from the ledger"
```

---

## Task 5: the retained-attempt integration proof

**Files:**
- Create: `tests/integration/test_phase_ledger_retained.py`

**Interfaces:**
- Consumes: `phase_ledger.ledger_from_engine`, `phase_ledger.ledger_from_baseline`,
  `scripts.reconcile_claims.ledger_for`, `scripts.reconcile_claims.ATTEMPTS`.
- Produces: nothing (a gate).

This is the design's own V1 test: the four screen attempts and the recurrence
batch recomputed to their published per-phase values. It is marked
integration because it reads artifacts outside the repository; it reads no
model and spawns nothing. When an artifact is absent it skips **loudly**,
naming the path, rather than passing silently.

- [ ] **Step 1: Write the test**

Create `tests/integration/test_phase_ledger_retained.py`:

```python
"""The retained attempts, recomputed to their published per-phase values.

Integration because these artifacts live under ``~/satyrn-smokes``. No model
and no subprocess; a missing artifact is a loud skip, never a silent pass.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from reconcile_claims import (  # noqa: E402  # scripts/ added via sys.path above
    ATTEMPTS,
    AttemptSpec,
    ledger_for,
)

pytestmark = pytest.mark.integration

RUNS_ROOT = Path(os.path.expanduser("~/satyrn-smokes"))

#: label -> published per-phase turns, copied from each attempt's own result
#: document (never derived here).
PUBLISHED: dict[str, tuple[int, ...]] = {
    "baseline-01": (7, 22, 6, 8),
    "baseline-02": (9, 8, 9, 6),
    "engine-01": (6, 8, 10, 23),
    "engine-02": (6, 7, 9, 23),
    "recurrence-01": (6, 8, 11, 19),
    "recurrence-03": (6, 8, 8, 14),
    "round2-01": (6, 8, 8, 21),
    "round2-02": (6, 8, 7, 28),
}


@pytest.mark.parametrize("spec", ATTEMPTS, ids=lambda spec: spec.label)
def test_retained_attempt_recomputes_to_its_published_per_phase_turns(spec) -> None:
    if not (RUNS_ROOT / spec.run_dir).exists():
        pytest.skip(f"retained attempt absent: {RUNS_ROOT / spec.run_dir}")
    ledger = ledger_for(spec, RUNS_ROOT)
    assert ledger.state == "measured", ledger.reason
    assert tuple(cell.turns for cell in ledger.cells) == PUBLISHED[spec.label]


def test_a_missing_attempt_is_a_named_absent_state_not_a_zero(tmp_path: Path) -> None:
    """Sibling to the success above: `ledger_for` on an absent artifact
    returns the named refusal state with no cells, never a zero. This
    exercises the production path, not a dataclass literal."""
    spec = AttemptSpec(label="missing", run_dir="does-not-exist", arm="engine")

    ledger = ledger_for(spec, tmp_path)

    assert ledger.state == "absent"
    assert ledger.reason
    assert ledger.cells == ()
```

- [ ] **Step 2: Run the test to verify it passes against the retained artifacts**

Run:

```bash
uv run pytest -q -m integration tests/integration/test_phase_ledger_retained.py
```

Expected: 9 passed (8 attempts + the refusal sibling; or skipped loudly if `~/satyrn-smokes` is absent).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_phase_ledger_retained.py
git commit -m "phase_ledger: prove the retained per-phase values (integration)"
```

---

## Task 6: V1 reconciliation — correct the stale carrier

**Files:**
- Modify: `docs/current/index.md:234`
- Modify: `docs/current/phase-v-claim-inventory.md` (statuses)
- Modify: `docs/current/phase-v-design.md` (record the V1 outcome)

**Interfaces:**
- Consumes: the generated table and the ledger from Tasks 4–5.
- Produces: no code; a corrected carrier and a dated record, in one commit.

The design names `docs/current/index.md:234` as the stale carrier: it still
reads "the opposite of 'Engine completes harder work more reliably'" while
`te6-explain-and-decide.md:255` reads "not that Baseline is the more reliable
configuration." V1 corrects the carrier to match its source, in place, with a
dated block.

- [ ] **Step 1: Correct the carrier in place**

In `docs/current/index.md`, replace the sentence fragment beginning
"— the opposite of 'Engine completes harder work more reliably.'" with the
source document's own corrected framing, keeping the original text visible
beneath a dated block:

```markdown
  `agentclinic-complaint-lifecycle`, Engine 6 of 18. **Corrected
  2026-09-11 (V1):** an earlier draft read "— the opposite of 'Engine
  completes harder work more reliably.'" The supported conclusion is
  narrower and is `te6-explain-and-decide.md:255`'s: Engine's proposed
  reliability advantage was not demonstrated, not that Baseline is the more
  reliable configuration.
```

- [ ] **Step 2: Mark the reconciled unit-level records**

For each `level="unit"` record in `claim_inventory.py`, set its status to
`confirmed` where the recomputed per-phase value equals the published one, or
`corrected` where it does not. Do not invent a third value; if the ledger
refused for an attempt, the record is `not_derivable` and names the missing
artifact.

- [ ] **Step 3: Regenerate the table**

Run:

```bash
uv run python scripts/reconcile_claims.py --runs-root ~/satyrn-smokes
uv run pytest -q tests/test_claim_inventory.py tests/test_reconcile_claims.py
```

Expected: the generated table carries the settled statuses; tests pass.

- [ ] **Step 4: Record the cycle outcome in the design**

Append a dated block to `docs/current/phase-v-design.md` under the V1 section:
how many inventory records now carry a status, how many `unit` records were
reconciled, the `not_derivable` count with its named artifacts, whether the
cycle published at least one status change (the findings-bearing object test),
and that the ledger records the `HEAD` revision and each read artifact's
sha256 per the design's Currency rule. If no status changed, use the design's
own zero-corrections wording.

- [ ] **Step 5: Run the full gate**

Run: `just gates`
Expected: clean.

- [ ] **Step 6: Commit (source, carrier, and generated table together)**

```bash
git add docs/current/index.md docs/current/phase-v-claim-inventory.md \
  src/satyrn_evals/claim_inventory.py docs/current/phase-v-design.md
git commit -m "V1: reconcile the per-phase ledger and correct index.md's framing"
```

---

## Self-review

**Spec coverage.** The inventory (V1 product 1) is Task 3; the shared
per-phase ledger (product 2) is Tasks 1–2; unit-level reconciliation
(product 3) is Tasks 4–6. The refusal conditions map to the `absent` and
`undecidable` states tested in Tasks 1–2. `index.md:234` and its carrier rule
are Task 6. The design's "turn_ledger imported, not changed" is honored by
importing `events_from_pi_stdout` only.

**Deliberately out of scope** (the design's own V1 exclusion): claim-level
measures, the `census.py`/`pathology.py` repair, and figures the ledger cannot
settle. Those are V2.

**Type consistency.** `PhaseLedger`/`PhaseCounts` names and fields are used
identically in Tasks 1–5; `ClaimRecord` fields are used identically in Tasks
3–4; `AttemptSpec` and `ledger_for` are defined in Task 4 and consumed by Task
5.

**Known limits.** `render_table` and `validate_sources` are pure and proven in
the default tier; the retained-attempt proof is integration-only and says so
loudly. The inventory seed is the design's named figures; Task 3 Step 5 is the
bounded completion step, with `validate_sources` as the correctness gate.

**Fixture scope.** The design's V1 Files list names `tests/data/` fixtures. This
plan instead builds the refusal/success transcripts as minimal synthetic
in-process documents (the `test_census.py` precedent), because every V1 case is
fully expressible that way, and reads the real retained attempts only in the
marked integration test. The design's trimmed-real-excerpt-with-provenance
standard belongs to V2, where the classifiers need retained counterexamples;
committing environment-specific blobs for V1 would add bytes without adding a
claim. If a reviewer wants the blobs anyway, add one trimmed excerpt per arm
under `tests/data/phase-ledger/` with a `PROVENANCE.json` recording its source
path and sha256, and keep the synthetic tests as the default tier.

---

## Post-review fixes (final whole-branch review, 2026-09-11)

The final review returned "with fixes"; one fix wave was applied and a scoped
re-review confirmed every finding addressed with no new breakage. The plan's
code blocks above remain the as-planned version; these are the shipped deltas.

| finding | disposition |
|---|---|
| F1 Tool-call boundary differed by arm (`tool_execution_start` vs `_end`) | Fixed: Baseline now counts `tool_execution_start`; truncation tests on both arms. |
| F2 No guard between `INVENTORY` and the committed generated doc | Fixed: default-tier test asserts `render_table()` is contained in the committed doc. |
| M3 `c-engine-population` cited `ROADMAP.md:292` (the rate, not the population) | Fixed: carrier removed. |
| M4 `u-recurrence-01/03` sources off by one | Fixed: `:13`→`:12`, `:15`→`:14`. |
| M5 index.md correction dropped "and efficiency" | Fixed: restores the source's wording. |
| M6 Digest table used absolute host paths | Fixed: keys are relative to `--runs-root`, with one `**Runs root:**` header line. |
| M9 Missing Baseline `step_id` reason conflated with "outside the record" | Fixed: split into two named reasons. |
| M10 Inventory size unpinned | Fixed: a test pins 20 records / 7 unit / 13 claim. |
| M11 Refusal test did not assert no zero | Fixed: asserts the empty cells render as dashes. |

Recorded as V2 prerequisites (not fixed here): duplicate declared `step_id`s
produce duplicate cells; an empty `steps` list reports measured zeros; an
ambiguous multi-`rglob` should refuse rather than pick the first; the per-phase
tool-call columns are first-time derivations and should be labelled as such;
`validate_root` is cwd-anchored.
