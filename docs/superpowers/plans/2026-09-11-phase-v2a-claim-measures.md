# Phase V2a — claim-level measures and the denominator binding

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every claim-level record a claim→measure→population binding backed by four pure classifiers that return `undecidable` where evidence is absent.

**Architecture:** A new pure module `src/satyrn_evals/claim_measures.py` holds one normalizer and four classifiers over already-parsed transcript events. `scripts/reconcile_claims.py` consumes them to settle the thirteen claim-level inventory records and regenerate the table. No model, no network, no subprocess in any module.

**Tech Stack:** Python 3.14 stdlib only (`json`, `dataclasses`, `typing`, `re`).

**Spec:** [docs/current/phase-v-design.md](../../current/phase-v-design.md) — the V2 section, plus Governance ("never originate a figure") and Limits.

## Global Constraints

- Repo rule (`docs/sdd.md`): the maintainer controls commits. An executor
  leaves changes in the working tree; the per-task `git commit` steps below
  are run by the maintainer, not the executor.
- Default tier runs without model, network, or subprocess; the planted subprocess tripwire stays armed.
- Every classifier is pure and returns `undecidable` — never `False`, never a zero — where evidence is absent.
- Never originate a figure or a new Engine-vs-Baseline contrast. V2 confirms or corrects *published* figures only.
- `turn_ledger.py` and `phase_ledger.py` are imported, never modified.
- A classifier's fixture is a trimmed real excerpt with its source attempt path and a recorded sha256; the integration check runs the same measures over the full retained artifacts and says so loudly when they are absent.
- Corrections are recorded in place with dated blocks, and every in-repo carrier is updated in the same commit.

---

## File structure

| File | Responsibility |
| --- | --- |
| `src/satyrn_evals/claim_measures.py` | Pure normalizer + four classifiers; the claim→measure→population binding datum. |
| `scripts/reconcile_claims.py` | Add the claim-level section; regenerate the table. |
| `tests/test_claim_measures.py` | Default-tier classifier success/refusal tests over trimmed excerpts. |
| `tests/data/claim-measures/` | Trimmed real excerpts + `PROVENANCE.json`. |
| `tests/integration/test_claim_measures_retained.py` | Marked integration: full retained artifacts. |
| `docs/current/phase-v-claim-inventory.md` | Regenerated table with claim-level statuses. |

---

## Task 1: `claim_measures.py` — events, edit classification, `destructive_edit`

**Files:**
- Create: `src/satyrn_evals/claim_measures.py`
- Test: `tests/test_claim_measures.py`

**Interfaces:**
- Produces: `MeasureResult = Literal["yes", "no", "undecidable"]`,
  `EditClass = Literal["replacement", "rejected", "no_op", "undecidable"]`,
  `EditCall(turn, tool_name, path, classification, removed, added)` (each of
  `removed`/`added` a `tuple[str, ...]` of text blocks, `()` when unreadable),
  `edit_calls(events) -> tuple[EditCall, ...]`,
  `destructive_edit(events) -> MeasureResult`.
- Consumes: nothing new (operates on the normalized event shape both adapters already produce).

**Event shapes (verified against the retained attempts).** Engine
(`.satyrn-implementer-transcript.jsonl`, one JSON object per line): a call is a
`tool_execution_start` with `toolName` and `args`; its result is the matching
`tool_execution_end` with `result.content[].text`. Baseline (`transcript.jsonl`,
a wrapped `{"type": "event", "step_id", "kind", "payload"}` line): the same
pi events sit under `payload`. `run_self_test` results begin `exit code 0\n` or
`exit code 1\n`. A rejected edit's result contains `Could not find the exact
text`; a true no-op's contains `No changes made` / `replacement produced
identical content`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_claim_measures.py`:

```python
"""The claim-level measures: pure classifiers over retained event shapes.

Default tier throughout -- synthetic events built in-process from the
shapes recorded in the retained fixtures.
"""

from satyrn_evals.claim_measures import destructive_edit, edit_calls

PHASES = ("phase-1-home", "phase-2-board", "phase-3-add", "phase-4-resolve-reopen")


def _start(call_id: str, tool: str, args: dict) -> dict:
    return {
        "type": "tool_execution_start",
        "toolCallId": call_id,
        "toolName": tool,
        "args": args,
    }


def _end(call_id: str, tool: str, text: str, *, is_error: bool = False) -> dict:
    return {
        "type": "tool_execution_end",
        "toolCallId": call_id,
        "toolName": tool,
        "isError": is_error,
        "result": {"content": [{"type": "text", "text": text}]},
    }


def _edit(call_id: str, old: str, new: str) -> tuple[dict, dict]:
    args = {
        "path": "app.py",
        "edits": [{"oldText": old, "newText": new}],
    }
    return _start(call_id, "edit", args), args


def test_a_replacement_is_a_destructive_edit() -> None:
    start, _ = _edit("c1", "old line\n", "new line\n")
    events = [start, _end("c1", "edit", "applied")]

    assert edit_calls(events)[0].classification == "replacement"
    assert destructive_edit(events) == "yes"


def test_a_rejected_edit_is_not_a_destructive_edit() -> None:
    """`oldText` did not match: a refused edit is not a content change."""
    start, _ = _edit("c1", "old line\n", "new line\n")
    events = [
        start,
        _end(
            "c1",
            "edit",
            "Could not find the exact text in app.py. The old text must match "
            "exactly including all whitespace and newlines.",
        ),
    ]

    assert edit_calls(events)[0].classification == "rejected"
    assert destructive_edit(events) == "no"


def test_a_true_no_op_is_not_a_destructive_edit() -> None:
    start, _ = _edit("c1", "same\n", "same\n")
    events = [
        start,
        _end(
            "c1",
            "edit",
            "No changes made to app.py. The replacement produced identical content.",
        ),
    ]

    assert edit_calls(events)[0].classification == "no_op"
    assert destructive_edit(events) == "no"


def test_a_read_is_not_an_edit() -> None:
    events = [_start("c1", "read", {"path": "app.py"}), _end("c1", "read", "contents")]

    assert edit_calls(events) == ()
    assert destructive_edit(events) == "undecidable"


def test_removed_and_added_blocks_are_recorded_for_restoration() -> None:
    start, _ = _edit("c1", "route A\nroute B\n", "")
    events = [start, _end("c1", "edit", "applied")]

    call = edit_calls(events)[0]
    assert call.removed == ("route A\nroute B\n",)
    assert call.added == ()


def test_an_unpaired_edit_call_is_undecidable() -> None:
    start, _ = _edit("c1", "old\n", "new\n")

    call = edit_calls([start])[0]
    assert call.classification == "undecidable"
    assert destructive_edit([start]) == "undecidable"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_claim_measures.py`
Expected: collection error (`satyrn_evals.claim_measures` does not exist yet).

- [ ] **Step 3: Implement the normalizer and `destructive_edit`**

Create `src/satyrn_evals/claim_measures.py`:

```python
"""The claim-level measures: pure classifiers over retained transcript events.

Every function here answers one published question and returns a tri-state:
`yes`, `no`, or `undecidable`. `undecidable` is for absent or unreadable
evidence — never a silent `no`, which would turn "never kept" into "never
happened" (the failure `phase_ledger` exists to prevent).

Scope: V2 confirms or corrects published figures. Nothing here originates a
figure, and nothing here makes a causal claim; the binding datum
(`ClaimMeasure`) names the population each result is about.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

type MeasureResult = Literal["yes", "no", "undecidable"]
type EditClass = Literal["replacement", "rejected", "no_op", "undecidable"]

_REJECTED_EDIT_RE = re.compile(r"could not find the exact text", re.IGNORECASE)
_NOOP_EDIT_RE = re.compile(
    r"no changes? made|replacement produced identical content", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class EditCall:
    """One `edit` execution, classified from its own start/end pair.

    `removed`/`added` are the text blocks the edit deleted and introduced,
    kept for the `restoration` measure; both are `()` when the call carried
    no readable `edits` list.
    """

    tool_name: str
    path: str | None
    classification: EditClass
    removed: tuple[str, ...]
    added: tuple[str, ...]


def _iter_events(
    events: Sequence[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    """Flatten either layout to the raw pi event shape.

    Engine events are already raw. A Baseline line wraps the raw event in
    `{"type": "event", "payload": {...}}`; its payload is the event.
    """
    flattened: list[Mapping[str, object]] = []
    for event in events:
        if event.get("type") == "event" and isinstance(event.get("payload"), Mapping):
            flattened.append(event["payload"])
        else:
            flattened.append(event)
    return flattened


def _result_text(event: Mapping[str, object]) -> str:
    result = event.get("result")
    if not isinstance(result, Mapping):
        return ""
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        part["text"]
        for part in content
        if isinstance(part, Mapping)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
    )


def _blocks(args: Mapping[str, object], key: str) -> tuple[str, ...]:
    edits = args.get("edits")
    if not isinstance(edits, list):
        return ()
    values = []
    for block in edits:
        if (
            isinstance(block, Mapping)
            and isinstance(block.get(key), str)
            and block[key]
        ):
            values.append(block[key])
    return tuple(values)


def _classify_edit(text: str) -> EditClass:
    if _REJECTED_EDIT_RE.search(text):
        return "rejected"
    if _NOOP_EDIT_RE.search(text):
        return "no_op"
    return "replacement"


def edit_calls(
    events: Sequence[Mapping[str, object]],
) -> tuple[EditCall, ...]:
    """Every `edit` execution in order, paired with its result.

    An `edit` start with no matching end is `undecidable`: the call was made,
    but whether it changed content is not decidable from the retained stream.
    """
    flat = _iter_events(events)
    starts: dict[str, Mapping[str, object]] = {}
    results: dict[str, str] = {}
    order: list[str] = []
    for event in flat:
        if event.get("type") == "tool_execution_start":
            call_id = event.get("toolCallId")
            if isinstance(call_id, str):
                starts.setdefault(call_id, event)
                if call_id not in order:
                    order.append(call_id)
            continue
        if event.get("type") == "tool_execution_end":
            call_id = event.get("toolCallId")
            if isinstance(call_id, str):
                results[call_id] = _result_text(event)
    calls: list[EditCall] = []
    for call_id in order:
        start = starts[call_id]
        if start.get("toolName") != "edit":
            continue
        args = start.get("args")
        args = args if isinstance(args, Mapping) else {}
        removed = _blocks(args, "oldText")
        added = _blocks(args, "newText")
        text = results.get(call_id)
        classification: EditClass = (
            "undecidable" if text is None else _classify_edit(text)
        )
        path = args.get("path")
        calls.append(
            EditCall(
                tool_name="edit",
                path=path if isinstance(path, str) else None,
                classification=classification,
                removed=removed,
                added=added,
            )
        )
    return tuple(calls)


def destructive_edit(
    events: Sequence[Mapping[str, object]],
) -> MeasureResult:
    """Did the attempt apply at least one content-changing edit?

    `yes` for a replacement, `no` for a transcript whose edits were all
    rejected or true no-ops, and `undecidable` when no edit was retained or
    an edit's result is unreadable.
    """
    calls = edit_calls(events)
    if not calls:
        return "undecidable"
    if any(call.classification == "undecidable" for call in calls):
        return "undecidable"
    return "yes" if any(call.classification == "replacement" for call in calls) else "no"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_claim_measures.py`
Expected: PASS, all 6 tests.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/satyrn_evals/claim_measures.py tests/test_claim_measures.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/claim_measures.py tests/test_claim_measures.py
git commit -m "claim_measures: classify edits and the destructive_edit measure"
```

---

## Task 2: `restoration`

**Files:**
- Modify: `src/satyrn_evals/claim_measures.py`
- Modify: `tests/test_claim_measures.py`

**Interfaces:**
- Consumes: `EditCall`, `edit_calls` (Task 1).
- Produces: `restoration(events) -> MeasureResult`.

- [ ] **Step 1: Write the failing tests**

Amend the top import to `from satyrn_evals.claim_measures import destructive_edit, edit_calls, restoration`, then append these tests:

```python
def test_a_later_edit_returning_removed_text_is_a_restoration() -> None:
    remove, _ = _edit("c1", "route\n", "")
    restore, _ = _edit("c2", "", "route\n")
    events = [
        remove, _end("c1", "edit", "applied"),
        restore, _end("c2", "edit", "applied"),
    ]

    assert restoration(events) == "yes"


def test_edits_that_only_add_new_text_are_not_a_restoration() -> None:
    first, _ = _edit("c1", "", "alpha\n")
    second, _ = _edit("c2", "", "beta\n")
    events = [
        first, _end("c1", "edit", "applied"),
        second, _end("c2", "edit", "applied"),
    ]

    assert restoration(events) == "no"


def test_a_rejected_restore_edit_does_not_count() -> None:
    remove, _ = _edit("c1", "route\n", "")
    restore, _ = _edit("c2", "", "route\n")
    events = [
        remove, _end("c1", "edit", "applied"),
        restore, _end("c2", "edit", "Could not find the exact text in app.py."),
    ]

    assert restoration(events) == "no"


def test_restoration_is_undecidable_without_any_edit() -> None:
    assert restoration([]) == "undecidable"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_claim_measures.py -k restoration`
Expected: collection error (`restoration` does not exist yet).

- [ ] **Step 3: Implement `restoration`**

Append to `src/satyrn_evals/claim_measures.py`:

```python
def restoration(events: Sequence[Mapping[str, object]]) -> MeasureResult:
    """Was content removed by an applied edit later re-added before the end?

    A restoration is an applied edit whose added blocks include a block that
    an earlier applied edit removed. This is a transcript-level shape, not a
    semantic repair: it does not claim the restored content fixed anything.
    """
    calls = edit_calls(events)
    applied = [call for call in calls if call.classification == "replacement"]
    if not calls:
        return "undecidable"
    removed_since_start: set[str] = set()
    for call in applied:
        if any(block in removed_since_start for block in call.added):
            return "yes"
        removed_since_start.update(block for block in call.removed if block)
    return "no"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_claim_measures.py`
Expected: PASS, all 10 tests.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src/satyrn_evals/claim_measures.py tests/test_claim_measures.py
git add src/satyrn_evals/claim_measures.py tests/test_claim_measures.py
git commit -m "claim_measures: detect restoration of removed content"
```

---

## Task 3: `self_test_outcome`

**Files:**
- Modify: `src/satyrn_evals/claim_measures.py`
- Modify: `tests/test_claim_measures.py`

**Interfaces:**
- Consumes: `edit_calls`' flattening helpers.
- Produces: `self_test_outcome(events, chain) -> MeasureResult`.

**Policy.** Engine: the last `run_self_test` result's `exit code N` line, cross-checked
against `chain["phases"][i]["self_test_outcome"]` when phases are given; a
disagreement is `undecidable`, never a silent pass. Baseline: the design says
*"specified or refused"* — Baseline has no `chain.json`, so unless a
Baseline-side self-test is provable in both directions this returns
`undecidable`, and V3 records the arm asymmetry.

- [ ] **Step 1: Write the failing tests**

Amend the top import to add `self_test_outcome`, then append these tests:

```python
def _self_test(call_id: str, code: int) -> tuple[dict, dict]:
    return (
        _start(call_id, "run_self_test", {}),
        _end(call_id, "run_self_test", f"exit code {code}\n1 passed"),
    )


def test_engine_self_test_fails_when_the_last_run_failed() -> None:
    events = [*_self_test("c1", 0), *_self_test("c2", 1)]

    assert self_test_outcome(events, chain=None) == "no"


def test_engine_self_test_passes_when_the_last_run_passed() -> None:
    events = [*_self_test("c1", 1), *_self_test("c2", 0)]

    assert self_test_outcome(events, chain=None) == "yes"


def test_engine_self_test_refuses_when_the_chain_disagrees() -> None:
    events = [*_self_test("c1", 0)]
    chain = {"phases": [{"step_id": "phase-1-home", "self_test_outcome": {"ran": True, "exit_code": 1}}]}

    assert self_test_outcome(events, chain=chain) == "undecidable"


def test_baseline_self_test_is_refused_without_a_chain() -> None:
    """A Baseline transcript runs its tests through `bash`, not
    `run_self_test`; with no chain record the measure is undecidable rather
    than an improvised detector."""
    events = [
        _start("c1", "bash", {"command": "uv run python -m pytest tests"}),
        _end("c1", "bash", "1 passed"),
    ]

    assert self_test_outcome(events, chain=None) == "undecidable"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_claim_measures.py -k self_test`
Expected: collection error (`self_test_outcome` does not exist yet).

- [ ] **Step 3: Implement `self_test_outcome`**

Append to `src/satyrn_evals/claim_measures.py`:

```python
_EXIT_CODE_RE = re.compile(r"^exit code (\d+)$", re.MULTILINE)


def _last_self_test(events: Sequence[Mapping[str, object]]) -> int | None:
    flat = _iter_events(events)
    last: int | None = None
    for event in flat:
        if event.get("type") != "tool_execution_end":
            continue
        if event.get("toolName") != "run_self_test":
            continue
        match = _EXIT_CODE_RE.search(_result_text(event))
        if match is not None:
            last = int(match.group(1))
    return last


def self_test_outcome(
    events: Sequence[Mapping[str, object]],
    chain: Mapping[str, object] | None,
) -> MeasureResult:
    """The attempt's own required self-test: did it pass?

    Engine: the last retained `run_self_test` exit code. When a chain record
    is supplied, every phase's independently recorded `self_test_outcome`
    must agree that the command passed; a disagreement or an unrecorded
    phase is `undecidable`. Baseline transcripts carry no `run_self_test`
    tool at all, so this returns `undecidable` and V3 records the arm
    asymmetry rather than improvising a detector.
    """
    exit_code = _last_self_test(events)
    if exit_code is None:
        return "undecidable"
    if chain is not None:
        phases = chain.get("phases")
        if not isinstance(phases, list):
            return "undecidable"
        for phase in phases:
            if not isinstance(phase, Mapping):
                return "undecidable"
            record = phase.get("self_test_outcome")
            if not isinstance(record, Mapping) or record.get("ran") is not True:
                return "undecidable"
            if record.get("exit_code") not in (0, exit_code):
                return "undecidable"
    return "yes" if exit_code == 0 else "no"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_claim_measures.py`
Expected: PASS, all 14 tests.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src/satyrn_evals/claim_measures.py tests/test_claim_measures.py
git add src/satyrn_evals/claim_measures.py tests/test_claim_measures.py
git commit -m "claim_measures: read the required self-test outcome"
```

---

## Task 4: `verification_claim`

**Files:**
- Modify: `src/satyrn_evals/claim_measures.py`
- Modify: `tests/test_claim_measures.py`

**Interfaces:**
- Produces: `verification_claim(events) -> MeasureResult`.

**Policy.** Compare the implementer's final assistant text against the
retained `run_self_test` results: a final message that reports a passing
pytest run while the last retained self-test failed is `no` (a fabricated
verification claim). A claim that matches the retained result is `yes`.
No readable final message, or no retained self-test, is `undecidable`.

- [ ] **Step 1: Write the failing tests**

Amend the top import to add `verification_claim`, then append these tests:

```python
def _summary(text: str) -> dict:
    return {
        "type": "turn_end",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def test_a_summary_claiming_passed_over_a_failed_self_test_is_a_false_claim() -> None:
    events = [
        *_self_test("c1", 1),
        _summary("All done: ===== 2 passed in 0.35s ====="),
    ]

    assert verification_claim(events) == "no"


def test_a_summary_matching_a_passing_self_test_is_honest() -> None:
    events = [
        *_self_test("c1", 0),
        _summary("Tests pass: ===== 4 passed in 0.4s ====="),
    ]

    assert verification_claim(events) == "yes"


def test_a_summary_that_claims_nothing_is_undecidable() -> None:
    events = [*_self_test("c1", 1), _summary("I refactored the models.")]

    assert verification_claim(events) == "undecidable"


def test_no_final_message_is_undecidable() -> None:
    assert verification_claim([*_self_test("c1", 1)]) == "undecidable"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_claim_measures.py -k verification`
Expected: collection error (`verification_claim` does not exist yet).

- [ ] **Step 3: Implement `verification_claim`**

Append to `src/satyrn_evals/claim_measures.py`:

```python
_PASSED_RE = re.compile(r"\b\d+ passed\b|\ball tests? pass", re.IGNORECASE)
_FAILED_RE = re.compile(r"\b\d+ failed\b", re.IGNORECASE)


def _final_assistant_text(events: Sequence[Mapping[str, object]]) -> str:
    flat = _iter_events(events)
    last = ""
    for event in flat:
        if event.get("type") != "turn_end":
            continue
        message = event.get("message")
        if not isinstance(message, Mapping):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if (
                isinstance(part, Mapping)
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
            ):
                last = part["text"]
    return last


def verification_claim(events: Sequence[Mapping[str, object]]) -> MeasureResult:
    """Does the implementer's own summary match its retained tool results?

    `no` when the final summary claims a passing test run while the last
    retained self-test failed (or vice versa); `yes` when they agree;
    `undecidable` when the summary makes no test claim or no self-test was
    retained. This measures report honesty, never whether the underlying
    work is correct.
    """
    text = _final_assistant_text(events)
    exit_code = _last_self_test(events)
    if not text or exit_code is None:
        return "undecidable"
    claims_pass = bool(_PASSED_RE.search(text)) and not _FAILED_RE.search(text)
    claims_fail = bool(_FAILED_RE.search(text)) and not _PASSED_RE.search(text)
    if not claims_pass and not claims_fail:
        return "undecidable"
    if claims_pass and exit_code != 0:
        return "no"
    if claims_fail and exit_code == 0:
        return "no"
    return "yes"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_claim_measures.py`
Expected: PASS, all 18 tests.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src/satyrn_evals/claim_measures.py tests/test_claim_measures.py
git add src/satyrn_evals/claim_measures.py tests/test_claim_measures.py
git commit -m "claim_measures: compare the implementer's verification claim to retained results"
```

---

## Task 5: trimmed real fixtures with provenance, and the integration check

**Files:**
- Create: `tests/data/claim-measures/PROVENANCE.json`
- Create: `tests/data/claim-measures/engine-02-edits.jsonl` (trimmed real excerpt)
- Create: `tests/data/claim-measures/engine-01-verification.jsonl` (trimmed real excerpt)
- Create: `tests/test_claim_measures_fixtures.py`
- Create: `tests/integration/test_claim_measures_retained.py`

**Interfaces:**
- Consumes: `edit_calls`, `destructive_edit`, `restoration`, `self_test_outcome`, `verification_claim`.
- Produces: nothing (gates).

The excerpts are the retained evidence:
`2026-09-11-te4-screen-engine-02` carries the rejected edit and the true
no-op; `2026-09-11-te4-screen-engine-01` carries the fabricated passing
report over a retained `exit code 1`. Each file records, in `PROVENANCE.json`,
its source attempt path and sha256.

- [ ] **Step 1: Write and run the fixture generator (scratch, not committed)**

Create and run `scripts/_make_claim_fixtures.py`:

```python
#!/usr/bin/env python3
"""Trim the retained counterexamples into committed fixtures. Scratch."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(os.path.expanduser("~/satyrn-smokes"))
OUT = Path("tests/data/claim-measures")


def keep_edit_or_self_test(event: dict) -> bool:
    return (
        event.get("type") in ("tool_execution_start", "tool_execution_end")
        and event.get("toolName") in ("edit", "run_self_test")
    )


def keep_verification(event: dict) -> bool:
    return keep_edit_or_self_test(event) or event.get("type") == "turn_end"


def trim(source: Path, destination: Path, keep) -> None:
    kept = [
        line
        for line in source.read_text().splitlines()
        if line.strip() and keep(json.loads(line))
    ]
    destination.write_text("\n".join(kept) + "\n")


SOURCES = {
    "engine-02-edits": (
        ROOT / "2026-09-11-te4-screen-engine-02/harness/.satyrn-implementer-transcript.jsonl",
        keep_edit_or_self_test,
    ),
    "engine-01-verification": (
        ROOT / "2026-09-11-te4-screen-engine-01/harness/.satyrn-implementer-transcript.jsonl",
        keep_verification,
    ),
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = {}
    for name, (source, keep) in SOURCES.items():
        trim(source, OUT / f"{name}.jsonl", keep)
        provenance[name] = {
            "source": str(source),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    (OUT / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n")
```

Run it, then delete `scripts/_make_claim_fixtures.py` before committing; the
two `.jsonl` fixtures and `PROVENANCE.json` are what commit.

- [ ] **Step 2: Write the default-tier fixture tests**

Create `tests/test_claim_measures_fixtures.py` asserting, on the committed
excerpts: `engine-02-edits.jsonl` yields one `rejected` edit and one `no_op`
edit and `destructive_edit == "no"` for that excerpt; `engine-01-verification.jsonl`
yields `verification_claim == "no"` and `self_test_outcome == "no"`. Read the
excerpts with `json.loads` per line and pass the parsed events to the
classifiers.

- [ ] **Step 3: Write the marked integration check**

Create `tests/integration/test_claim_measures_retained.py` (marked
`integration`) that reads the full retained attempts from `~/satyrn-smokes`,
runs the four classifiers, and asserts: `destructive_edit == "yes"` on every
attempt in `ATTEMPTS`; `verification_claim == "no"` on `2026-09-11-te4-screen-engine-01`;
`self_test_outcome` agrees with `chain.json` on every Engine attempt. It skips
**loudly**, naming the absent path, when `~/satyrn-smokes` is missing.

- [ ] **Step 4: Run both tiers**

Run: `uv run pytest -q tests/test_claim_measures_fixtures.py && uv run pytest -q -m integration tests/integration/test_claim_measures_retained.py`
Expected: fixture tests pass; integration skips loudly or passes.

- [ ] **Step 5: Lint and commit**

```bash
git add tests/data/claim-measures tests/test_claim_measures_fixtures.py tests/integration/test_claim_measures_retained.py
git commit -m "claim_measures: prove the classifiers on retained counterexamples"
```

---

## Task 6: the binding and claim-level reconciliation

**Files:**
- Modify: `src/satyrn_evals/claim_measures.py` (the `ClaimMeasure` datum)
- Modify: `scripts/reconcile_claims.py`
- Modify: `docs/current/phase-v-claim-inventory.md` (regenerated)
- Modify: `src/satyrn_evals/claim_inventory.py` (settle the claim records)
- Modify: `docs/current/phase-v-design.md` (V2 outcome block)

**Interfaces:**
- Produces: `ClaimMeasure(claim_id, measure, population, result, evidence)`;
  `measure_inventory(records) -> tuple[ClaimMeasure, ...]`.

- [ ] **Step 1: Write the failing test**

Amend the top imports to add `from satyrn_evals.claim_inventory import INVENTORY` and `measure_inventory`, then append these tests:

```python
def test_measure_inventory_covers_every_claim_record_with_its_population() -> None:
    claims = [record for record in INVENTORY if record.level == "claim"]
    measures = measure_inventory(INVENTORY)

    assert len(measures) == len(claims)
    assert {measure.claim_id for measure in measures} == {r.id for r in claims}
    assert all(measure.population for measure in measures)


def test_an_uncovered_measure_is_undecidable_not_no() -> None:
    measures = {measure.claim_id: measure for measure in measure_inventory(INVENTORY)}

    assert measures["c-completion-6-of-18"].result == "undecidable"
```

- [ ] **Step 2: Implement the binding**

Add to `claim_measures.py`:

```python
@dataclass(frozen=True, slots=True)
class ClaimMeasure:
    claim_id: str
    measure: str
    population: str
    result: MeasureResult
    evidence: tuple[str, ...]


def measure_inventory(records) -> tuple[ClaimMeasure, ...]:
    out = []
    for record in records:
        if record.level != "claim":
            continue
        out.append(
            ClaimMeasure(
                claim_id=record.id,
                measure=record.measure,
                population=record.population,
                result="undecidable",
                evidence=("no classifier covers this measure in V2a",),
            )
        )
    return tuple(out)
```

The three measures with classifiers (`destructive_edit`, `restoration`,
`verification_claim`) are wired to their classifiers in this task; the
completion-rate claims stay `undecidable` and are noted as V3 findings. This
is deliberate: V2 confirms only what it can derive, and an `undecidable`
completion rate is a finding about evidence, not a zero.

- [ ] **Step 3: Wire the three covered measures to their classifiers**

For each `level="claim"` record whose `measure` is one of
`destructive_edit`, `restoration`, `verification_claim`, call the matching
classifier over the relevant retained attempt(s) and set `result` and
`evidence`. The Engine attempts come from `scripts/reconcile_claims.ATTEMPTS`.

- [ ] **Step 4: Emit the claim section and regenerate**

Add a `## Claim measures` section to `render_report`, and regenerate
`docs/current/phase-v-claim-inventory.md`.

- [ ] **Step 5: Settle the inventory records**

Set `status` on each claim record per its derived result (`confirmed` where a
published figure is reproduced, `claim_measure_mismatch` where the classifier
contradicts it, `not_derivable` where `undecidable` names the missing
evidence). Update every in-repo carrier in the same commit.

- [ ] **Step 6: Record the V2 outcome**

Append a dated block to `docs/current/phase-v-design.md` under the V2 section:
how many claim records carry each status, which measures are `undecidable`
with the arm asymmetry named, and whether the cycle published a status change.

- [ ] **Step 7: Run the gates and commit**

Run: `uv run pytest -q && uv run ruff check && uv run python tools/lint_docs.py`
Expected: clean (the repo's `just docs` remains red at BASE for pre-existing
`myst.xref_missing` warnings; do not claim it green).

```bash
git add src/satyrn_evals/claim_measures.py scripts/reconcile_claims.py \
  src/satyrn_evals/claim_inventory.py docs/current/phase-v-claim-inventory.md \
  docs/current/phase-v-design.md
git commit -m "V2a: bind the claim-level inventory to its measures and reconcile"
```

---

## Self-review

**Spec coverage.** Product 1 (the binding) is Task 6; product 2 (the four
classifiers) is Tasks 1–4; product 4 (claim reconciliation) is Task 6. Product 3
(the census/pathology repair and discovery) is deliberately **V2b**, a separate
plan: it is a seam repair independent of the classifiers, and mixing them
would put two unrelated failure modes behind one review gate.

**Evidence standard.** Task 5 commits trimmed real excerpts with provenance
digests and adds a marked integration check that skips loudly.

**Known limits.** `self_test_outcome` for Baseline is refused by design (the
design's "specified or refused"); completion-rate claims have no classifier in
V2a and stay `undecidable`. Both are V3 arm-asymmetry findings, not zeros.
