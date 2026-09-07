> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V10 P1 — The pathology parser: vocabulary, well-formedness, seven counts

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `src/satyrn_evals/pathology.py` — a pure, offline parser over a
preserved Pi stream-JSON attempt transcript that enforces the documented
well-formedness rules (spec §2 R1–R6) and counts the seven
transcript-local pathology axes (spec §3.1–3.7), with the whole-cell
`measured: false` discipline (spec §2, S1) and a faithful-good fixture
reproducing the spec's §3 validation row.

**Architecture:** Pure text-in/result-out — no I/O, no subprocess.
`count_transcript(text, *, had_patch)` returns a `CellPathology`
(measured with counts, or unmeasured with one `reason`). Parsing is two
phases: document well-formedness (R1–R6) over the event list, then
counting over the validated document. `to_block()` emits count keys only
for measured cells.

**Tech Stack:** Python ≥3.14, stdlib only, house style (`type` aliases,
`match`/`case`, walrus, real return annotations).

**Spec:** `docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md`
§1–§3, §6, §9.1–9.3, §12. (Trimmed to the 400-line cap 2026-09-04; the
spec is the binding authority and the plan argues from it.)

## Global Constraints

- **No commits** — maintainer-controlled (`docs/sdd.md`, `CLAUDE.md`);
  leave the worktree dirty.
- Default tier must not spawn (planted tripwire). Run `uv run pytest -q`;
  the module gate is `uv run pytest -q tests/test_pathology.py` plus
  `uv run ruff check src/satyrn_evals/pathology.py tests/test_pathology.py`
  and `uv run pyrefly` — every task ends green and lint-clean.
- Refusal tests get success siblings; a detector fires on a known-bad from
  the same fixture batch and stays silent on the known-good (`BRIEF.md`
  rules 6, 8). 100% statement-and-branch gate applies.
- Fixtures live under `tests/data/v10/` (excluded from collection by
  `norecursedirs`, `pyproject.toml:52`).

---

### Task 1: The module skeleton, wire shape, and unmeasured helpers

**Status: implemented (2026-09-04, review clean).** Full walkthrough
history is in the SDD workspace (brief/report/review under
`.superpowers/sdd/2026-09-04-v10-p1-pathology-parser/`); this note is the
durable record.

**Files:** `src/satyrn_evals/pathology.py` (constants, `CellPathology`,
`to_block`), `tests/test_pathology.py` (two skeleton tests).

**What shipped:** `SESSION_VERSION == 3`; `EVENT_TYPES` (the 11 verified
top-level types — spec §1); `TOOL_NAMES = {read, bash, edit, write}`;
`FILE_TOOLS`/`WRITE_TOOLS`/`SHELL_TOOLS`/`RUNNER_NAMES = {"pytest"}`;
`type PathologyReason` with the closed seven-value set (spec §2);
`@dataclass(frozen=True, slots=True) CellPathology` with `measured`,
`reason`, and the seven count fields (default `0`/`{}`);
`to_block()` — unmeasured emits only `{"measured": false, "reason": …}`
(never a count key beside `measured: false`, S1); measured emits the full
count set and never a `reason` key. Imports are only what this task uses
(ruling: `json`/`posixpath`/`Counter`/`PurePosixPath` join Tasks 2–3).
`tests/data/v10/` README + the `GOOD` faithful fixture are written in
Task 4.

**Rulings (controller, recorded):** a brief test asserting Task 3
behavior was moved to Task 3's batch (it duplicated Task 3's
`test_tool_calls_counted_by_name_first_seen`); unused future imports were
trimmed (ruff gate).

- [ ] **(done)** Module skeleton + two tests; 2 passed, ruff clean.

---

### Task 2: Document well-formedness (R1–R6)

**Status: implemented (2026-09-04).** Walkthrough history in the SDD
workspace; this note is the durable record.

**Files:** `src/satyrn_evals/pathology.py`, `tests/test_pathology.py`.

**What shipped:** `import json`; `_unmeasured(reason)` helper;
`count_transcript(text, *, had_patch)`; `_header_ok` (R2),
`_vocabulary_ok` (R3: event types **and** the tool-name set),
`_structure_ok` (R4/R5/R6), `_count` (a Task-3 stub returning
`CellPathology(measured=True)` — enough for the good-document test). The
reason mapping is exact per spec §2: unparseable line ⇒ `unparseable`;
wrong version ⇒ `unsupported_version`; missing/malformed header ⇒
`malformed`; unknown event type or tool name ⇒ `unknown_event`; turn or
execution-structure violations ⇒ `malformed`; no terminal ⇒ `partial`;
empty input ⇒ `empty`. R6 (ruled): after the single `agent_end` the
remainder is `[]` or exactly one `agent_settled`; a duplicate `agent_end`
**or** a second `agent_settled` ⇒ `malformed`.

**Tests:** 16 passed (refusal tests per the brief, each with success
siblings where the brief requires; `GOOD` document measured). SIM102
single-`if`-with-`and` accepted (ruff-mandated).

- [ ] **(done)** Well-formedness + `count_transcript`; 16 passed, ruff clean.

---

### Task 3: The seven count axes

**Files:**
- Modify: `src/satyrn_evals/pathology.py`
- Test: `tests/test_pathology.py`

**Interfaces:**
- Consumes: validated `events` (Task 2); `CellPathology` (Task 1).
- Produces: `_count(events, *, had_patch) -> CellPathology` replacing the
  stub, implementing spec §3.1–3.7 exactly.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pathology.py`. Fixtures: `REPEAT_TEXT` (two
identical `read`s of one file in one turn), `NOOP_TEXT` (an `edit` whose
block has `oldText == newText`), `CHURN_TEXT` (two differing payloads on
one path), `RUNNER_TEXT` (a `bash` execution running `uv run pytest
tests/`), `ESCAPE_TEXT` (a `read` of `../etc/passwd`), `FLOOR_TEXT` (a
single text-only final turn, `had_patch=False`), `SUCCESS_TEXT` (a
text-only final turn after an edit, `had_patch=True`). All satisfy R1–R6.
Also add the test moved from Task 1 by ruling:

```python
def test_tool_calls_counted_by_name_first_seen() -> None:
    block = count_transcript(GOOD, had_patch=True)
    assert list(block.tool_calls) == ["read", "edit"]  # first-seen order
    assert block.tool_calls == {"read": 2, "edit": 2}


def test_repeats_count_identical_executions_beyond_the_first() -> None:
    assert count_transcript(REPEAT_TEXT, had_patch=True).repeats == 1


def test_noop_edit_fires_on_byte_identical_block() -> None:
    assert count_transcript(NOOP_TEXT, had_patch=True).noop_edits == 1


def test_churn_counts_differing_payload_on_same_path() -> None:
    assert count_transcript(CHURN_TEXT, had_patch=True).churn == 1


def test_test_runner_matches_pytest_token() -> None:
    assert count_transcript(RUNNER_TEXT, had_patch=True).test_runner_commands == 1


def test_test_runner_ignores_aliases_and_wrappers() -> None:
    text = RUNNER_TEXT.replace("uv run pytest tests/", "pt")
    assert count_transcript(text, had_patch=True).test_runner_commands == 0


def test_workspace_escape_is_lexical() -> None:
    assert count_transcript(ESCAPE_TEXT, had_patch=True).workspace_escapes == 1
    assert count_transcript(GOOD, had_patch=True).workspace_escapes == 0


def test_tool_free_terminal_turn_counts_only_without_patch() -> None:
    assert count_transcript(FLOOR_TEXT, had_patch=False).tool_free_terminal_turns == 1
    assert count_transcript(SUCCESS_TEXT, had_patch=True).tool_free_terminal_turns == 0
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_pathology.py -k "counted or repeat or noop or churn or runner or escape or terminal"`
Expected: FAIL (stub returns measured-empty).

- [ ] **Step 3: Implement `_count`** (replace the stub)

Add the module imports `import posixpath`, `from collections import
Counter`, `from pathlib import PurePosixPath`, then implement, per spec §3:

```python
def _count(events: list[dict], *, had_patch: bool) -> CellPathology:
    starts = [e for e in events if e.get("type") == "tool_execution_start"]
    tool_calls: dict[str, int] = {}
    for event in starts:
        name = event["toolName"]
        tool_calls[name] = tool_calls.get(name, 0) + 1
    identity = Counter(
        (event["toolName"], json.dumps(event.get("args"), sort_keys=True))
        for event in starts
    )
    repeats = sum(count - 1 for count in identity.values())
    last_payload: dict[str, str] = {}
    churn = 0
    for event in starts:
        if event["toolName"] not in WRITE_TOOLS:
            continue
        args = event.get("args") or {}
        if not isinstance(args.get("path"), str):
            continue
        payload = json.dumps(
            args.get("edits") if event["toolName"] == "edit" else args.get("content"),
            sort_keys=True,
        )
        path = args["path"]
        if path in last_payload and payload != last_payload[path]:
            churn += 1
        last_payload[path] = payload
    noop_edits = 0
    for event in starts:
        if event["toolName"] != "edit":
            continue
        edits = (event.get("args") or {}).get("edits")
        if isinstance(edits, list) and any(
            isinstance(block, dict)
            and block.get("oldText") is not None
            and block.get("oldText") == block.get("newText")
            for block in edits
        ):
            noop_edits += 1
    test_runner_commands = 0
    for event in starts:
        if event["toolName"] not in SHELL_TOOLS:
            continue
        command = (event.get("args") or {}).get("command")
        if isinstance(command, str) and RUNNER_NAMES & set(command.split()):
            test_runner_commands += 1
    terminal = _terminal_turn(events)
    tool_free = (
        1
        if terminal is not None and not had_patch and _turn_tool_free(events, terminal)
        else 0
    )
    escapes = sum(
        1
        for event in starts
        if event["toolName"] in FILE_TOOLS and _escapes(events, event)
    )
    return CellPathology(
        measured=True,
        tool_calls=tool_calls,
        repeats=repeats,
        churn=churn,
        noop_edits=noop_edits,
        test_runner_commands=test_runner_commands,
        tool_free_terminal_turns=tool_free,
        workspace_escapes=escapes,
    )


def _terminal_turn(events: list[dict]) -> tuple[int, int] | None:
    """(turn_start index, turn_end index) of the final turn."""
    end_idx = max(i for i, e in enumerate(events) if e.get("type") == "turn_end")
    start_idx = max(
        i for i, e in enumerate(events[:end_idx]) if e.get("type") == "turn_start"
    )
    return start_idx, end_idx


def _turn_tool_free(events: list[dict], turn: tuple[int, int]) -> bool:
    start_idx, end_idx = turn
    parts = events[end_idx].get("message", {}).get("content")
    if not isinstance(parts, list):
        return False
    has_text = any(
        isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
        and part["text"].strip()
        for part in parts
    )
    if not has_text:
        return False
    return not any(
        events[i].get("type") == "tool_execution_start"
        for i in range(start_idx + 1, end_idx)
    )


def _escapes(events: list[dict], event: dict) -> bool:
    cwd = events[0]["cwd"]
    path = (event.get("args") or {}).get("path")
    if not isinstance(path, str):
        return False  # R5 guarantees file-tools carry a path; defensive
    candidate = path if posixpath.isabs(path) else posixpath.join(cwd, path)
    normalized = PurePosixPath(posixpath.normpath(candidate))
    return not normalized.is_relative_to(PurePosixPath(cwd))
```

Semantics pinned by spec §3 (the authority): `tool_calls` = starts by
toolName, first-seen order (§3.1); `repeats` = identical (toolName, args)
beyond the first (§3.2); `churn` = 2nd+ edit/write execution on a path
whose payload differs from the previous, cross-tool, never for identical
payloads (§3.3); `noop_edits` = edit executions with ≥1 byte-identical
`oldText`/`newText` block, orthogonal to churn (§3.4); `test_runner_commands`
= shell executions whose command contains a whole-token runner name
(§3.5); `tool_free_terminal_turns` = final turn with assistant text, no
execution in it, and `had_patch` false (§3.6); `workspace_escapes` =
lexical file-tool path resolution against `cwd` (§3.7).

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_pathology.py`
Expected: PASS. Then `uv run ruff check …`, `uv run pyrefly`, and the
module-coverage gate: `uv run pytest -q --cov=satyrn_evals --cov-report=term-missing`
(100% statement and branch).

---

### Task 4: The validation-row fixture and S1 discipline

**Files:**
- Create: `tests/data/v10/good-repair.jsonl`
- Create: `tests/data/v10/README.md`
- Modify: `tests/test_pathology.py`

**Interfaces:**
- Consumes: `count_transcript` (Tasks 2–3).
- Produces: `good-repair.jsonl` reproducing spec §3's validation row; a
  `README.md` naming the spec §3/§12 source and stating the fixture is
  synthesized, not byte-copied from the scratch transcript.

- [ ] **Step 1: Write the failing test + fixture**

```python
def test_validation_row_reproduces_the_spec_table() -> None:
    text = Path("tests/data/v10/good-repair.jsonl").read_text(encoding="utf-8")
    block = count_transcript(text, had_patch=True)
    assert block.to_block() == {
        "measured": True,
        "tool_calls": {"read": 6, "edit": 2},
        "repeats": 4,
        "churn": 0,
        "noop_edits": 0,
        "test_runner_commands": 0,
        "tool_free_terminal_turns": 0,
        "workspace_escapes": 0,
    }
```

The fixture: six `read` executions (`app.py`, `tests/test_app.py`,
`models.py`, `tests/test_app.py`, `app.py`, `tests/test_app.py` — so
`tests/test_app.py` ×3 and `app.py` ×2 are repeats) plus two identical
`edit app.py` executions (spec §12: `repeats` = 3 re-reads + 1 re-edit =
4), inside balanced turns, then a final text-only turn and the terminal
`agent_end`/`agent_settled`.

- [ ] **Step 2: Run to verify it fails** (fixture absent) — then create it.
- [ ] **Step 3: Add the S1 discipline test**

```python
def test_measured_false_never_carries_counts() -> None:
    reasons: list[PathologyReason] = [
        "absent", "empty", "unparseable", "unsupported_version",
        "unknown_event", "malformed", "partial",
    ]
    for reason in reasons:
        wire = CellPathology(measured=False, reason=reason).to_block()
        assert set(wire) == {"measured", "reason"}
```

- [ ] **Step 4: Full module + tree gate**

Run: `uv run pytest -q tests/test_pathology.py`; `uv run pytest -q`
(whole default tier — tripwire green); coverage at 100% branch;
`uv run ruff check …`; `uv run pyrefly`.

---

## Self-review note for the executor

The spec is the binding authority; where this plan and the spec disagree,
the spec wins and the discrepancy is a plan defect to report. P1
deliberately excludes `overlay_windows` (spec §10: P2's scan produces the
eighth axis; P3's binder joins it). `absent` is decided by P3's binder (a
record naming no transcript, or one unreadable); `count_transcript` never
returns `absent`. This plan was trimmed to the 400-line cap 2026-09-04
(tasks already implemented are record notes; the SDD workspace holds
their full walkthroughs).
