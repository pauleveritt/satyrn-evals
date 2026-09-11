# Phase V3 — close-out plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every inventory record exactly one final status, prove no carrier lags its source, apply the reopen bound once, and publish the Track B gate.

**Architecture:** One pure audit module (`claim_closeout.py`), a carrier-lag check over cited files, a generated gate document, and the deferred classifier fixes. No engine behaviour changes; Track A is offline.

**Tech Stack:** Python 3.14 stdlib only.

**Spec:** [docs/current/phase-v-design.md](../../current/phase-v-design.md) — V3, Governance (reopen bound), Limits. V2b declared itself instrument-only, so **V3 must be findings-bearing**: it publishes at least one status change, or the explicit zero-corrections pass.

## Global Constraints

- Default tier runs without model, network, or subprocess; the tripwire stays armed.
- Every record has exactly one status from `confirmed | corrected | not_derivable | claim_measure_mismatch`; every `not_derivable` names the missing artifact.
- A carrier that lags its source is a failure, not a warning.
- Never originate a figure or a new contrast.
- Repo rule (`docs/sdd.md`): maintainer controls commits; executors leave changes in the working tree.

---

## Task 1: the deferred V3 fixes

**Files:**
- Modify: `src/satyrn_evals/claim_measures.py`
- Modify: `src/satyrn_evals/census.py`
- Modify: `tests/test_claim_measures.py`, `tests/test_census.py`

**Interfaces:** none new; correctness fixes only.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_claim_measures.py`:

```python
def _summary_of(text: str) -> dict:
    return {
        "type": "turn_end",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def test_a_zero_failed_summary_is_a_pass_claim_not_a_failure_claim() -> None:
    events = [*_self_test("c1", 0), _summary_of("All green: 4 passed, 0 failed")]
    assert verification_claim(events) == "yes"


def test_a_zero_passed_summary_is_a_failure_claim_not_a_pass_claim() -> None:
    events = [*_self_test("c1", 1), _summary_of("Result: 0 passed, 3 failed")]
    assert verification_claim(events) == "no"


def test_a_non_assistant_turn_end_is_not_read_as_the_summary() -> None:
    events = [
        *_self_test("c1", 1),
        {
            "type": "turn_end",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "===== 9 passed ====="}],
            },
        },
    ]
    assert verification_claim(events) == "undecidable"
```

Append to `tests/test_census.py`:

```python
def test_a_rejected_edit_does_not_reset_the_stall_run() -> None:
    events = [
        _edit_start("c1"),
        _edit_end("c1", "Could not find the exact text in app.py.", is_error=True),
        _start("c2", "read", {"path": "app.py"}),
        _end("c2", "read", "contents"),
    ]
    assert detect_stall(events) >= 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_claim_measures.py tests/test_census.py -k 'zero or non_assistant or stall_run'`
Expected: FAIL on the zero-count and role cases.

- [ ] **Step 3: Implement**

In `claim_measures.py`, make the count regexes non-zero and guard the role:

```python
_PASSED_RE = re.compile(r"\b[1-9]\d* passed\b|\ball tests? pass", re.IGNORECASE)
_FAILED_RE = re.compile(r"\b[1-9]\d* failed\b", re.IGNORECASE)
```

In `_final_assistant_text`, `continue` unless `message.get("role") == "assistant"`.

In `census.py`, correct the module docstring's stale citation to the V16
census design to the path that exists in the tree (find it; it is under
`docs/superpowers/`).

- [ ] **Step 4: Run, lint, commit**

Run: `uv run pytest -q tests/test_claim_measures.py tests/test_census.py` and `uv run ruff check` on the four files.

```bash
git add src/satyrn_evals/claim_measures.py src/satyrn_evals/census.py \
  tests/test_claim_measures.py tests/test_census.py
git commit -m "V3: close the verification regressions deferred from V2"
```

---

## Task 2: the close-out audit and carrier-lag check

**Files:**
- Create: `src/satyrn_evals/claim_closeout.py`
- Test: `tests/test_claim_closeout.py`

**Interfaces:**
- Produces: `FinalStatus`, `CloseoutRow(claim_id, level, status, source, carriers,
  missing)`, `closeout_rows(records=INVENTORY) -> tuple[CloseoutRow, ...]`,
  `carrier_lag(records, root=Path(".")) -> tuple[str, ...]`.

`missing` is the named artifact for a `not_derivable` record and `None`
otherwise; a `not_derivable` row with `missing is None` is a close-out failure.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_claim_closeout.py`:

```python
"""The V3 close-out audit: one status per record, no lagging carrier.

Default tier: pure over the frozen inventory and repository paths.
"""

from pathlib import Path

from satyrn_evals.claim_closeout import carrier_lag, closeout_rows, quote_drift
from satyrn_evals.claim_inventory import ClaimRecord

ROOT = Path(__file__).resolve().parent.parent
FINAL = {"confirmed", "corrected", "not_derivable", "claim_measure_mismatch"}


def test_every_record_carries_exactly_one_final_status() -> None:
    rows = closeout_rows()
    assert len(rows) == 20
    assert all(row.status in FINAL for row in rows)


def test_every_not_derivable_row_names_the_missing_artifact() -> None:
    rows = closeout_rows()
    for row in rows:
        if row.status == "not_derivable":
            assert row.missing, f"{row.claim_id} is not_derivable with no missing artifact"


def test_every_carrier_path_exists() -> None:
    assert carrier_lag(root=ROOT) == ()


def test_a_missing_carrier_path_is_reported(tmp_path) -> None:
    record = ClaimRecord(
        id="x",
        quote="6 of 18",
        source="claim_inventory.py",
        carriers=("carrier.md",),
        level="claim",
        measure="completion_rate",
        population="18 Engine attempts",
    )

    assert "carrier.md" in carrier_lag(records=(record,), root=tmp_path)


def test_quote_drift_lists_a_carrier_that_dropped_the_figure(tmp_path) -> None:
    record = ClaimRecord(
        id="x",
        quote="6 of 18",
        source="claim_inventory.py",
        carriers=("carrier.md",),
        level="claim",
        measure="completion_rate",
        population="18 Engine attempts",
    )
    (tmp_path / "carrier.md").write_text("this carrier paraphrased and dropped it")

    assert "carrier.md" in quote_drift(records=(record,), root=tmp_path)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_claim_closeout.py`
Expected: collection error (`satyrn_evals.claim_closeout` does not exist).

- [ ] **Step 3: Implement, run, lint, commit**

Create `src/satyrn_evals/claim_closeout.py`:

```python
"""The V3 close-out audit: every claim one status, no carrier lagging source.

Pure. The audit reads the frozen inventory and the repository's own files;
it originates no figure and changes no record.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from satyrn_evals.claim_inventory import ClaimRecord, INVENTORY

type FinalStatus = Literal[
    "confirmed", "corrected", "not_derivable", "claim_measure_mismatch"
]

#: The artifact each `not_derivable` record names as missing. V3's rule is
#: that a `not_derivable` status without a named artifact is a close-out
#: failure, so this map is the record of what each refusal is waiting on.
MISSING_ARTIFACT: dict[str, str] = {
    "c-completion-6-of-18": "hidden-grader verdicts across all 18 Engine attempts",
    "c-completion-4-of-16": "hidden-grader verdicts for the 16 pre-screen attempts",
    "c-baseline-3-of-3": "matched-repeat Baseline attempts under the final prompt",
    "c-contemporaneous-screen-tie-2-of-2": "an outcome measure executable from transcripts",
    "c-nonrestore-0-of-6": "a completion verdict per non-restoring attempt",
    "c-restore-4-of-7": "a completion verdict per restoring attempt",
    "c-redirect-fixed-1-of-9": "a redirect-trap resolution classifier",
    "c-redirect-6-of-9": "a redirect-trap occurrence classifier",
    "c-phase4-denominator-6-of-10": "prompt-state membership for the pre-phase-4 chains",
    "c-engine-population": "a measure that binds the population statement to an attempt set",
}


@dataclass(frozen=True, slots=True)
class CloseoutRow:
    claim_id: str
    level: str
    status: str
    source: str
    carriers: tuple[str, ...]
    missing: str | None


def _record_missing(record: ClaimRecord) -> str | None:
    if record.status != "not_derivable":
        return None
    return MISSING_ARTIFACT.get(record.id)


def closeout_rows(
    records: Sequence[ClaimRecord] = INVENTORY,
) -> tuple[CloseoutRow, ...]:
    return tuple(
        CloseoutRow(
            claim_id=record.id,
            level=record.level,
            status=record.status,
            source=record.source,
            carriers=record.carriers,
            missing=_record_missing(record),
        )
        for record in records
    )


def carrier_lag(
    records: Sequence[ClaimRecord] = INVENTORY,
    root: Path = Path("."),
) -> tuple[str, ...]:
    """Carrier paths that no longer exist. A hard failure.

    Path existence is the check V3 can make mechanically; textual drift is
    `quote_drift`, a review list rather than a failure, because a legitimate
    carrier may paraphrase.
    """
    return tuple(
        cited
        for record in records
        for cited in record.carriers
        if not (root / cited.rsplit(":", 1)[0]).exists()
    )


def quote_drift(
    records: Sequence[ClaimRecord] = INVENTORY,
    root: Path = Path("."),
) -> tuple[str, ...]:
    """Carriers whose text no longer contains the record's fixed quote.

    A review list, not a failure: the V1 correction preserved the original
    wording inside a dated block, so a carrier that quotes still matches,
    while one that paraphrases is flagged for a human to read.
    """
    drifted: list[str] = []
    for record in records:
        for cited in record.carriers:
            path = root / cited.rsplit(":", 1)[0]
            if path.exists() and record.quote not in path.read_text(
                encoding="utf-8", errors="replace"
            ):
                drifted.append(cited)
    return tuple(drifted)
```

Run the tests; fix the `MISSING_ARTIFACT` map so every `not_derivable` record
is covered (the test is the gate). Commit as `V3: audit the close-out and carrier lags`.

---

## Task 3: publish the Track B gate

**Files:**
- Create: `scripts/publish_gate.py`
- Test: `tests/test_publish_gate.py`
- Create (generated): `docs/current/phase-v-track-b-gate.md`
- Modify: `docs/current/index.md` (toctree line)

**Interfaces:**
- Consumes: `closeout_rows`, `carrier_lag`.
- Produces: `render_gate(rows) -> str`.

- [ ] **Step 1: Write the failing test**

A default-tier test that `render_gate(closeout_rows())` contains every
`claim_id` and each row's status, and that a `not_derivable` row renders its
`missing` artifact.

- [ ] **Step 2: Implement and generate**

`render_gate` emits a Markdown table with `claim_id | level | status | missing`
plus a summary line carrying the status counts. `main` writes
`docs/current/phase-v-track-b-gate.md` and adds `phase-v-track-b-gate` to the
hidden toctree in `docs/current/index.md`.

- [ ] **Step 3: Gate and commit**

Run the generator, `uv run pytest -q`, `uv run ruff check`, `uv run python tools/lint_docs.py`.

```bash
git add scripts/publish_gate.py tests/test_publish_gate.py \
  docs/current/phase-v-track-b-gate.md docs/current/index.md
git commit -m "V3: publish the Track B gate"
```

---

## Task 4: the reopen bound and the cycle outcome

**Files:**
- Modify: `docs/current/phase-v-design.md` (V3 block)
- Modify: `docs/current/phase-v-track-b-gate.md` (reopen record)

- [ ] **Step 1: Apply the reopen bound**

For each record whose status is `corrected` or `claim_measure_mismatch`, record
one reopen decision on the gate page under `## Reopen decisions`: the claim, the
recorded phase decision it supported, and whether that decision is reopened
(never more than once per claim per reconciliation). A `confirmed` record
reopens nothing.

- [ ] **Step 2: Declare the cycle findings-bearing**

Append the dated V3 block to `docs/current/phase-v-design.md` (≤400 lines):
the final status counts, every `not_derivable` with its named missing artifact,
the reopen decisions, and the findings-bearing declaration. If every record
confirms, use the design's zero-corrections wording ("the published numbers hold
under committed derivation") — that is also findings-bearing. State that Track
B's gate is published and the Track B cycles may start.

- [ ] **Step 3: Gate and commit**

Run the full default tier, `ruff`, `lint-docs`; regenerate the gate page.

```bash
git add docs/current/phase-v-design.md docs/current/phase-v-track-b-gate.md
git commit -m "V3: close Phase V Track A and open the Track B gate"
```

---

## Self-review

**Spec coverage.** V3's products: one status per record (Task 2), each
`not_derivable` names its artifact (Task 2's `MISSING_ARTIFACT` + test), no
carrier lags (Task 2's `carrier_lag`), the reopen bound applied once (Task 4),
and the Track B gate published (Task 3). Task 1 clears the V2-deferred
regressions so the audit is built on a correct instrument.

**Findings-bearing.** V2b was instrument-only; V3 must publish a status change
or the zero-corrections pass. The V3 block states which.

**Known limits.** `carrier_lag` is a hard path-existence check; `quote_drift` is
its textual sibling and returns a review list, because a legitimate carrier may
paraphrase (the V1 correction preserved the original wording inside a dated
block). The V3 block reports both and sends `quote_drift` items to human review
rather than silently passing them.
