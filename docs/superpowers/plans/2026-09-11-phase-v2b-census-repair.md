# Phase V2b — census/pathology repair and the denominator binding

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the committed census/pathology instruments read both arms — the packet route's `run_self_test`, its transcript filename, and its multi-session shape — and derive the descoped `6 of 8`→`6 of 10` denominator executably.

**Architecture:** Two seam repairs to existing pure modules (`census.py`, `pathology.py`) and one reconciliation addition to `scripts/reconcile_claims.py`. No engine behaviour changes. V2b is the design's V2 product 3 plus the product-1 binding V2a deferred.

**Tech Stack:** Python 3.14 stdlib only (`json`, `re`, `dataclasses`, `typing`).

**Spec:** [docs/current/phase-v-design.md](../../current/phase-v-design.md) — V2 products 1 and 3, Governance, Limits; the V2a block names what V2b inherits.

## Global Constraints

- Default tier runs without model, network, or subprocess; the planted subprocess tripwire stays armed.
- Refuse rather than guess: an unattributable transcript is a named state, never a zero.
- Never originate a figure or a new Engine-vs-Baseline contrast; the denominator binding reproduces a published figure or is `not_derivable`.
- Repo rule (`docs/sdd.md`): the maintainer controls commits; executors leave changes in the working tree.
- `claim_measures.py`'s classifiers are imported, never re-implemented in the census.

---

## Task 1: census — vocabulary and the rejected/no-op split

**Files:**
- Modify: `src/satyrn_evals/census.py`
- Test: `tests/test_census.py`

**Interfaces:**
- Produces: `KNOWN_TOOL_NAMES` including `run_self_test`; `PathologyName` with
  `rejected_edit`; `CellCensus.rejected_edit: int`; `detect_rejected_edit(events) -> int`.
- Consumes: nothing new.

The census's `_NOOP_EDIT_RE` buckets a *rejected* edit ("Could not find the exact
text") with a *true* no-op, so `noop_edit` is an ambiguous count (design cause 3).
Split it: `_REJECTED_EDIT_RE` (anchor mismatch and schema refusal) and a
no-op-only `_NOOP_EDIT_RE`. `_edit_applied` must treat **both** as not-applied,
or `stall` changes meaning.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_census.py`:

```python
from satyrn_evals.census import detect_rejected_edit, detect_noop_edit


def _edit_start(call_id: str) -> dict:
    return {
        "type": "tool_execution_start",
        "toolCallId": call_id,
        "toolName": "edit",
        "args": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]},
    }


def _edit_end(call_id: str, text: str, *, is_error: bool = False) -> dict:
    event = {
        "type": "tool_execution_end",
        "toolCallId": call_id,
        "toolName": "edit",
        "result": {"content": [{"type": "text", "text": text}]},
    }
    if is_error:
        event["isError"] = True
    return event


def test_a_rejected_edit_is_counted_separately_from_a_true_no_op() -> None:
    events = [
        _edit_start("c1"),
        _edit_end("c1", "Could not find the exact text in app.py.", is_error=True),
        _edit_start("c2"),
        _edit_end("c2", "No changes made to app.py; identical content.", is_error=True),
    ]

    assert detect_rejected_edit(events) == 1
    assert detect_noop_edit(events) == 1


def test_a_run_self_test_call_is_not_an_unknown_tool() -> None:
    events = [
        {"type": "tool_execution_start", "toolCallId": "c1", "toolName": "run_self_test", "args": {}},
    ]

    assert detect_unknown_tool(events) == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_census.py -k 'rejected_edit or run_self_test'`
Expected: collection error (`detect_rejected_edit` does not exist).

- [ ] **Step 3: Implement the vocabulary and split**

In `src/satyrn_evals/census.py`:

```python
KNOWN_TOOL_NAMES = frozenset(
    {"read", "bash", "edit", "write", "run_tests", "run_self_test"}
)

_REJECTED_EDIT_RE = re.compile(
    r"could not find the exact text|validation failed for tool", re.IGNORECASE
)
_NOOP_EDIT_RE = re.compile(
    r"no changes? made|no matching text|replacement produced identical content",
    re.IGNORECASE,
)
```

Add `rejected_edit` to the `PathologyName` literal and to `PATHOLOGY_NAMES`,
immediately before `noop_edit`; add `rejected_edit: int` to `CellCensus` (beside
`noop_edit`); add it to `to_record`; add the detector:

```python
def detect_rejected_edit(events: list[dict]) -> int:
    """Count of edit results refusing to apply (anchor mismatch or schema)."""
    return sum(
        1
        for event in events
        if event.get("type") == "tool_execution_end"
        and event.get("toolName") == "edit"
        and _REJECTED_EDIT_RE.search(_result_text(event.get("result")))
    )
```

Set `rejected_edit=detect_rejected_edit(events)` in `_census_one_transcript`; add
`totals[name] = sum(int(c.magnitude(name)) ...)` covers it via the generic
branch. Update `_edit_applied`:

```python
    if _REJECTED_EDIT_RE.search(text) or _NOOP_EDIT_RE.search(text):
        return False
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_census.py`
Expected: PASS, including the two new tests.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src/satyrn_evals/census.py tests/test_census.py
git add src/satyrn_evals/census.py tests/test_census.py
git commit -m "census: add run_self_test and split rejected edits from true no-ops"
```

---

## Task 2: census — discover the packet route's transcript

**Files:**
- Modify: `src/satyrn_evals/census.py`
- Test: `tests/test_census.py`

**Interfaces:**
- Consumes: `census_root` (existing).
- Produces: `census_root` also walks `.satyrn-implementer-transcript.jsonl`.

`census_root` globs only `transcript.txt`, so on the packet route — which
retains `harness/.satyrn-implementer-transcript.jsonl` (24 on disk, 0
`transcript.txt`) — it returns **0 cells** and the repaired vocabulary is
unobservable through the CLI.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_census.py`:

```python
def test_census_root_discovers_the_packet_route_transcript(tmp_path) -> None:
    harness = tmp_path / "run" / "harness"
    harness.mkdir(parents=True)
    (harness / ".satyrn-implementer-transcript.jsonl").write_text(
        json.dumps({"type": "session", "version": 3, "cwd": "/x"}) + "\n"
        + json.dumps(
            {
                "type": "tool_execution_start",
                "toolCallId": "c1",
                "toolName": "run_self_test",
                "args": {},
            }
        )
        + "\n"
    )

    cells = census_root(tmp_path)

    assert len(cells) == 1
    assert cells[0].unknown_tool == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest -q tests/test_census.py -k discovers`
Expected: FAIL (`len(cells) == 0`).

- [ ] **Step 3: Implement discovery**

In `census_root`, after the `transcript.txt` loop:

```python
    for transcript_path in sorted(root.rglob(".satyrn-implementer-transcript.jsonl")):
        cells.append(
            _census_one_transcript(transcript_path, root=root, contexts=contexts)
        )
```

`_cell_dir_for` finds no `cell-*` ancestor for a `harness/` transcript, so its
`batch`/`task`/`arm` stay `None` — a census never guesses a value it cannot
support. Do not invent an arm from the directory name.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_census.py`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src/satyrn_evals/census.py tests/test_census.py
git add src/satyrn_evals/census.py tests/test_census.py
git commit -m "census: discover the packet route's implementer transcript"
```

---

## Task 3: pathology — vocabulary, adapter header, and multi-session

**Files:**
- Modify: `src/satyrn_evals/pathology.py`
- Test: `tests/test_pathology.py`

**Interfaces:**
- Produces: `TOOL_NAMES` including `run_self_test`; `PathologyReason` including
  `multi_session`; an adapter-marker-tolerant `count_transcript`.

The packet-route transcript leads with `{"adapter_marker": "turn_start",
"index": 0}`, which trips `_header_ok` to `malformed`; behind it is a
multi-session concatenation and the `run_self_test` vocabulary gap. Specify all
three: skip marker lines, name multi-session explicitly, and admit the tool.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pathology.py`:

```python
def test_count_transcript_skips_adapter_marker_lines() -> None:
    text = (
        json.dumps({"adapter_marker": "turn_start", "index": 0}) + "\n"
        + json.dumps({"type": "session", "version": 3, "cwd": "/x"}) + "\n"
        + json.dumps({"type": "turn_start"}) + "\n"
        + json.dumps({"type": "turn_end", "message": {"stopReason": "stop"}}) + "\n"
        + json.dumps({"type": "agent_end"}) + "\n"
    )

    block = count_transcript(text, had_patch=False)

    assert block.measured is True


def test_a_multi_session_concatenation_is_named_not_malformed() -> None:
    session = json.dumps({"type": "session", "version": 3, "cwd": "/x"})
    turn = json.dumps({"type": "turn_start"}) + "\n" + json.dumps(
        {"type": "turn_end", "message": {"stopReason": "stop"}}
    )

    block = count_transcript(
        f"{session}\n{turn}\n{json.dumps({'type': 'agent_end'})}\n{session}\n{turn}\n"
        f"{json.dumps({'type': 'agent_end'})}\n",
        had_patch=False,
    )

    assert block.measured is False
    assert block.reason == "multi_session"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_pathology.py -k 'adapter or multi_session'`
Expected: FAIL (`measured is False`, reason `malformed`/`unknown_event`).

- [ ] **Step 3: Implement**

In `src/satyrn_evals/pathology.py`:

```python
TOOL_NAMES = frozenset({"read", "bash", "edit", "write", "run_self_test"})

type PathologyReason = Literal[
    "absent", "empty", "unparseable", "unsupported_version",
    "unknown_event", "malformed", "multi_session", "partial",
]
```

In `count_transcript`, drop marker lines and name multi-session before the
vocabulary/structure checks:

```python
    events = [event for event in events if "type" in event]
    if not events:
        return _unmeasured("empty")
    if (reason := _header_ok(events)) is not None:
        return _unmeasured(reason)
    if sum(1 for event in events if event.get("type") == "session") > 1:
        return _unmeasured("multi_session")
```

(Place the marker filter immediately after the JSON parse, before `_header_ok`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_pathology.py`
Expected: PASS. Also run `uv run pytest -q tests/test_census.py` — `v10_unmeasured` for the packet route is now `multi_session`, and any test pinning `malformed` for that fixture must be updated to the named reason (a correction, not a loosening).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src/satyrn_evals/pathology.py tests/test_pathology.py
git add src/satyrn_evals/pathology.py tests/test_pathology.py
git commit -m "pathology: admit run_self_test and name multi-session concatenations"
```

---

## Task 4: the denominator binding (`6 of 8` → `6 of 10`)

**Files:**
- Modify: `scripts/reconcile_claims.py`
- Modify: `src/satyrn_evals/claim_inventory.py` (`c-phase4-denominator-6-of-10`)
- Test: `tests/test_reconcile_claims.py`
- Modify: `docs/current/phase-v-claim-inventory.md` (regenerated)
- Modify: `docs/current/phase-v-design.md` (V2b block)

**Interfaces:**
- Consumes: `_phase4_reaching_engine_attempts` (V2a), `measure_inventory_for_run`.
- Produces: `denominator_binding(attempts) -> ClaimMeasure`.

The published correction is `6 of 8` → `6 of 10`: the denominator is all attempts
under the current prompt, not only those reaching phase 4. V2a enumerated the
phase-4 set but did not derive the binding.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_reconcile_claims.py` a test that `denominator_binding` over a
synthetic attempt set returns a `ClaimMeasure` whose `population` is the count of
attempts supplied and whose `evidence` names the phase-4 subset, and that an
empty set is `undecidable` (never `no`).

- [ ] **Step 2: Implement the binding**

In `scripts/reconcile_claims.py`:

```python
def denominator_binding(
    attempts: tuple[str, ...], phase4: tuple[str, ...]
) -> ClaimMeasure:
    """The `6 of 8` -> `6 of 10` correction as an executable binding.

    Names the full attempt population and the phase-4-reaching subset it was
    narrowed to. The completion count is *read*, never re-derived: a
    hidden-grader verdict is not a transcript-local fact.
    """
    if not attempts:
        return ClaimMeasure(
            claim_id="c-phase4-denominator-6-of-10",
            measure="denominator_binding",
            population="0 attempts",
            result="undecidable",
            evidence=("no attempts supplied",),
        )
    return ClaimMeasure(
        claim_id="c-phase4-denominator-6-of-10",
        measure="denominator_binding",
        population=f"{len(attempts)} attempts under the current prompt",
        result="yes",
        evidence=(f"phase-4-reaching subset: {len(phase4)} of {len(attempts)}",),
    )
```

Wire it in the claim section, passing the enumerated current-prompt attempts and
the `_phase4_reaching_engine_attempts` subset.

- [ ] **Step 3: Reconcile the record and record the outcome**

Set `c-phase4-denominator-6-of-10`'s status per the derived result (`confirmed`
if the population names 10 and the phase-4 subset 8; `not_derivable` if the
current-prompt population cannot be established from retained artifacts — name
the missing prompt-state evidence). Append a dated V2b block to
`docs/current/phase-v-design.md`; keep it at/under 400 lines.

- [ ] **Step 4: Regenerate and gate**

Run: `uv run python scripts/reconcile_claims.py --runs-root ~/satyrn-smokes`,
then `uv run pytest -q`, `uv run pytest -q -m integration`, `uv run ruff check`,
`uv run python tools/lint_docs.py`. `just docs` stays red at BASE; do not claim
it green.

- [ ] **Step 5: Commit**

```bash
git add scripts/reconcile_claims.py src/satyrn_evals/claim_inventory.py \
  tests/test_reconcile_claims.py docs/current/phase-v-claim-inventory.md \
  docs/current/phase-v-design.md
git commit -m "V2b: derive the 6-of-10 denominator binding"
```

---

## Self-review

**Spec coverage.** Product 3's three parts are Tasks 1 (vocabulary + split),
2 (discovery) and 3 (structure/multi-session), with the pathology fix carrying
the adapter-header tolerance V2a's F1 named. The product-1 denominator binding
V2a deferred is Task 4.

**Evidence standard.** Each repair is proven on the retained packet-route
transcript in the integration tier and on a synthetic excerpt at default tier;
`tests/data/` gains a trimmed `run_self_test` excerpt if the synthetic tests
cannot express a shape.

**Known limits.** The completion numerator is read from retained verdicts, never
re-derived from transcripts; if the current-prompt population is not
enumerable, the record is `not_derivable` and names the missing evidence.
