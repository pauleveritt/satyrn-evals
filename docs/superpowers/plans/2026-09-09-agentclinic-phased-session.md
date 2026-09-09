# Phased AgentClinic Session Workload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a three-prompt AgentClinic session task, graded cumulatively with budget as a co-equal verdict, so pathologies that only appear across successive development requests become countable.

**Architecture:** A new task `agentclinic-session-phased` whose `base/` holds only the pinned environment, whose hidden oracle is a byte-identical copy of depth-3's acceptance suite, and whose three prompts are the swiftstar roadmap's own phase sections. Three code changes precede it: declared directory source paths (so an empty skeleton has a writable `templates/`), optional per-step turn and tool budgets plus live `elapsed_seconds` capture, and an offline budget verdict reported as a 2x2 against correctness.

**Tech Stack:** Python 3.14, `uv`, pytest, `just`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-09-agentclinic-phased-session-design.md` (commit `ae15ad0`). Executors read both.

## Global Constraints

- **Python `>=3.14` house style.** Real return annotations on every function; `type` aliases for semantic types; `match`/`case` for dispatch over unions; walrus for bind-and-test. A review that rewrites these into older forms is wrong (`CLAUDE.md`).
- **Default tests use no model, no network, no subprocess.** A planted process-spawning test enforces this. Never weaken or remove it.
- **A refusal test has a sibling success test.** Never add one without the other. Rejection is the default outcome of most failures, so a broken refusal test passes silently.
- **Verify, don't assert.** Cite `file:line`. Never write down a number you did not compute; carry the command that recomputes it.
- **Commits are maintainer-controlled** in the sense that no commit is a *substitute* for review — but this plan's tasks each end in a commit, which is the maintainer's stated workflow for plan execution. Do not squash tasks together.
- **Gates:** `just gates` runs `uv run pytest -q`, `uv run ruff check`, `just lint-docs`, `just docs`, stopping on first non-zero exit. Read the exit code. **Never pipe a gate into `tail` or anything else.**
- **Task fixture pins stay exact:** `fastapi[standard]==0.115.10`, `turbohtml==1.5.0`, `pytest==8.3.4`.
- **The acceptance suite is never edited.** Not renamed, not relaxed, not reordered. If a check cannot be satisfied from the prompt, the prompt changes.
- **Do not modify `agentclinic-repair-depth-3`.** It is the byte-identity anchor.

---

### Task 1: Declared directory source paths

**Why:** `writable_paths` infers directory-ness by probing `base/`
(`src/satyrn_evals/engine_contract.py:45`). With an empty skeleton,
`templates` and `tests` do not exist in `base/`, so both render as exact
file patterns and the Engine arm cannot write `templates/home.html`. The
current behaviour is deliberate for *file* creation targets —
`agentclinic-repair-framing-2` declares `models.py` whose base deletes it
(`engine_contract.py:39-43`, `tests/test_engine_contract.py:91-96`) — so
the fix must add a way to *declare* a directory without changing what any
existing task renders.

**Design:** A `source_paths` entry with a trailing slash (`"templates/"`)
declares a directory. The manifest stores entries normalized (slash
stripped) in `source_paths`, so `within_source` and `overlay.py` are
untouched, plus a new `source_dirs: frozenset[str]` recording which were
declared. `writable_paths` consults `source_dirs` first and falls back to
the `base/` probe, so all six existing tasks render byte-identically.

**Files:**
- Modify: `src/satyrn_evals/manifest.py:33` (dataclass), `:242-247` and `:307` (parser)
- Modify: `src/satyrn_evals/engine_contract.py:32-46`
- Test: `tests/test_manifest.py`, `tests/test_engine_contract.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `TaskManifest.source_dirs: frozenset[str]`;
  `writable_paths(task_dir: Path, source_paths: Sequence[str], source_dirs: frozenset[str] = frozenset()) -> WritablePaths`.

- [ ] **Step 1: Write the failing tests — refusal and both successes**

Add to `tests/test_engine_contract.py`:

```python
def test_declared_directory_renders_as_pattern_without_base_probe() -> None:
    """A trailing-slash entry is a directory even when base/ has nothing there.

    This is the empty-skeleton case: the phased session task's base ships
    no templates/ at all, and the Engine arm must still be able to write
    templates/home.html.
    """
    task_dir = _fixture_dir("agentclinic-repair-framing-2")
    assert not (task_dir / "base" / "templates").exists()
    patterns = writable_paths(
        task_dir, ("templates",), frozenset({"templates"})
    )
    assert patterns == ("templates/*",)


def test_undeclared_missing_entry_still_stays_exact() -> None:
    """Sibling success: the framing-2 creation target is unchanged.

    Without a declaration, a path absent from base/ is still a file
    creation target, not a directory (engine_contract.py:39-43).
    """
    task_dir = _fixture_dir("agentclinic-repair-framing-2")
    assert writable_paths(task_dir, ("models.py",), frozenset()) == ("models.py",)
```

Add to `tests/test_manifest.py`:

```python
def test_trailing_slash_source_path_is_normalized_and_recorded(tmp_path) -> None:
    task_dir = _write_task(tmp_path, source_paths=["app.py", "templates/"])
    manifest = load_manifest(task_dir)
    assert manifest.source_paths == ("app.py", "templates")
    assert manifest.source_dirs == frozenset({"templates"})


def test_bare_source_path_declares_no_directory(tmp_path) -> None:
    """Sibling success: an entry without a trailing slash records nothing."""
    task_dir = _write_task(tmp_path, source_paths=["app.py"])
    manifest = load_manifest(task_dir)
    assert manifest.source_paths == ("app.py",)
    assert manifest.source_dirs == frozenset()


def test_source_path_of_only_a_slash_is_refused(tmp_path) -> None:
    """Refusal: '/' normalizes to the empty string, which would make
    within_source admit every path in the workspace."""
    task_dir = _write_task(tmp_path, source_paths=["/"])
    with pytest.raises(ManifestError, match="source_paths"):
        load_manifest(task_dir)
```

`_write_task` is the existing helper in `tests/test_manifest.py`; if it
does not accept `source_paths`, add that keyword with the current value as
its default rather than writing a second helper.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_engine_contract.py tests/test_manifest.py -q -k "declared_directory or undeclared_missing or trailing_slash or bare_source or only_a_slash"`

Expected: FAIL — `writable_paths()` takes 2 positional arguments, and `TaskManifest` has no attribute `source_dirs`.

- [ ] **Step 3: Add `source_dirs` to the manifest dataclass**

In `src/satyrn_evals/manifest.py`, after the `source_paths` field (line 33):

```python
    source_paths: tuple[str, ...]
    #: Entries that were declared with a trailing slash in ``source_paths``,
    #: normalized without it. A declaration, not an inference: the Engine
    #: contract renders these as directory patterns even when ``base/`` holds
    #: nothing at that path, which is what an empty-skeleton task needs.
    #: An entry absent from this set keeps the ``base/`` probe, so the six
    #: existing tasks render byte-identically (engine_contract.py:39-43).
    source_dirs: frozenset[str]
```

Place it immediately after `source_paths` and before `fixtures`, and give
it no default — the parser always supplies it, and a default would let a
hand-built `TaskManifest` in a test silently disagree with a loaded one.

- [ ] **Step 4: Normalize and record in the parser**

In `src/satyrn_evals/manifest.py`, replace the `sources = tuple(data["source_paths"])`
assignment and its validation with:

```python
    raw_sources = tuple(data["source_paths"])
    if not raw_sources or not all(isinstance(x, str) and x for x in raw_sources):
        raise ManifestError("source_paths must be a non-empty list of strings")
    sources = tuple(entry.rstrip("/") for entry in raw_sources)
    if not all(sources):
        raise ManifestError(
            "source_paths entries must name a path, not just a separator"
        )
    source_dirs = frozenset(
        entry.rstrip("/") for entry in raw_sources if entry.endswith("/")
    )
```

Delete the now-duplicated `if not sources or not all(...)` check further
down so the message is raised once. Add `source_dirs=source_dirs,` to the
`TaskManifest(...)` construction beside `source_paths=sources,`.

- [ ] **Step 5: Consult the declaration in `writable_paths`**

In `src/satyrn_evals/engine_contract.py`, replace the function:

```python
def writable_paths(
    task_dir: Path,
    source_paths: Sequence[str],
    source_dirs: frozenset[str] = frozenset(),
) -> WritablePaths:
    """``writable_paths`` patterns derived from a manifest's ``source_paths``.

    A **file** entry stays exact. A **directory** entry becomes an fnmatch
    pattern over its descendants (``templates`` -> ``templates/*``), which
    ``fnmatch`` matches at any depth because its ``*`` spans ``/``.

    Directory-ness is taken from ``source_dirs`` when the entry is declared
    there (a trailing slash in the manifest), and otherwise probed in
    ``base/``. The probe is kept because an entry with nothing at that path
    and no declaration is a *file* creation target
    (``agentclinic-repair-framing-2`` declares ``models.py`` and its base
    deletes the file). Declaration is what an empty-skeleton task needs:
    its ``templates/`` does not exist in ``base/`` either, and inference
    alone cannot tell the two cases apart.
    """
    base = task_dir / "base"
    return tuple(
        f"{entry}/*"
        if entry in source_dirs or (base / entry).is_dir()
        else entry
        for entry in source_paths
    )
```

- [ ] **Step 6: Pass the declaration through the renderer**

In `render_engine_contract`, change the `writable_paths` call:

```python
    lines += [
        f"  - {json.dumps(pattern)}"
        for pattern in writable_paths(
            task_dir, manifest.source_paths, manifest.source_dirs
        )
    ]
```

- [ ] **Step 7: Run the new tests, then the full suite**

Run: `uv run pytest tests/test_engine_contract.py tests/test_manifest.py -q`
Expected: PASS.

Then: `uv run pytest -q`
Expected: PASS. Any `TaskManifest(...)` constructed positionally or without
`source_dirs` in a test will fail here — fix each by adding
`source_dirs=frozenset()`, which preserves that test's existing meaning.

- [ ] **Step 8: Prove the six existing tasks render byte-identically**

This is the regression the change is most likely to cause and the reason
the probe was kept. Run:

```bash
uv run python -c "
from pathlib import Path
from satyrn_evals.manifest import load_manifest
from satyrn_evals.engine_contract import writable_paths
root = Path('src/satyrn_evals/tasks')
for d in sorted(p for p in root.iterdir() if (p / 'manifest.json').is_file()):
    m = load_manifest(d)
    print(d.name, writable_paths(d, m.source_paths, m.source_dirs))
"
```

Expected: every line matches what the same command prints on `HEAD~1`
(run it there first and diff the two outputs). No existing manifest uses a
trailing slash, so `source_dirs` is empty for all of them and the probe
alone decides — the output must be identical, not merely similar.

- [ ] **Step 9: Commit**

```bash
git add src/satyrn_evals/manifest.py src/satyrn_evals/engine_contract.py tests/test_manifest.py tests/test_engine_contract.py
git commit -m "Let a task declare a directory source path

writable_paths inferred directory-ness by probing base/, which cannot
distinguish an empty-skeleton directory from a file creation target --
framing-2 declares models.py precisely because its base deletes it. A
trailing slash now declares a directory; entries without one keep the
probe, so the six existing tasks render byte-identically.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Per-step budgets and an app-less base in `session.json`

**Why:** Two blockers in the session spec loader. `_STEP_KEYS` is an exact
set match (`src/satyrn_evals/session_manifest.py:42`), so a step carrying
budgets is refused; and `base_preservation_selectors` must be non-empty
(`:86-92`), which the phased task cannot satisfy — its base has no
application, so there is no base behaviour to preserve.

**Note for the executor:** cross-phase preservation is *not* lost by the
empty list. It is delivered by cumulative feature grading
(`session_grader.py:_cumulative_selectors`), which re-runs every earlier
phase's checks at each later checkpoint. `base_preservation_selectors`
covers only *base* public tests, of which this task has none.

**Files:**
- Modify: `src/satyrn_evals/session_manifest.py:22,23,26-37,39-64,86-92,105-107`
- Modify: `src/satyrn_evals/session_grader.py:150-160`
- Test: `tests/test_session_manifest.py`, `tests/test_session_preservation_per_checkpoint.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `SessionStep.turn_budget: int | None`, `SessionStep.tool_budget: int | None`; `SessionSpec.base_preservation_selectors` may now be an empty tuple.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_session_manifest.py`:

```python
def test_step_budgets_are_parsed(tmp_path) -> None:
    spec = _write_and_load(
        tmp_path,
        steps=[
            _step("one", turn_budget=12, tool_budget=30),
            _step("two"),
        ],
    )
    assert spec.steps[0].turn_budget == 12
    assert spec.steps[0].tool_budget == 30


def test_step_without_budgets_records_none(tmp_path) -> None:
    """Sibling success: budgets are optional, and absent is not zero.

    None means 'no ceiling declared', which the grader reports as
    unmeasured. Zero would mean 'every run is over budget'.
    """
    spec = _write_and_load(tmp_path, steps=[_step("one"), _step("two")])
    assert spec.steps[0].turn_budget is None
    assert spec.steps[0].tool_budget is None


def test_non_positive_budget_is_refused(tmp_path) -> None:
    """Refusal: a ceiling of zero or less is never a real measurement."""
    with pytest.raises(SessionSpecError, match="turn_budget"):
        _write_and_load(
            tmp_path, steps=[_step("one", turn_budget=0), _step("two")]
        )


def test_empty_base_preservation_selectors_are_allowed(tmp_path) -> None:
    """A task whose base ships no application has no base behaviour to
    preserve. Cross-phase preservation comes from cumulative feature
    grading, not from this list."""
    spec = _write_and_load(
        tmp_path, steps=[_step("one"), _step("two")], preservation=[]
    )
    assert spec.base_preservation_selectors == ()


def test_base_preservation_selectors_must_be_strings(tmp_path) -> None:
    """Refusal, narrowed: empty is now legal, but a non-string entry
    never was and still is not."""
    with pytest.raises(SessionSpecError, match="base_preservation_selectors"):
        _write_and_load(
            tmp_path, steps=[_step("one"), _step("two")], preservation=[""]
        )
```

If `tests/test_session_manifest.py` has no `_write_and_load`/`_step`
helpers with these keywords, add them there — a `_step(id, **budgets)`
returning the step dict, and `_write_and_load(tmp_path, steps, preservation=None)`
writing `session.json` and calling `load_session_spec`. Default
`preservation` to the file's existing non-empty value so every current
test keeps its meaning.

Add to `tests/test_session_preservation_per_checkpoint.py`:

```python
def test_no_preservation_selectors_leaves_verdict_unset(tmp_path) -> None:
    """With nothing declared, preservation is not graded and not inferred.

    An unset verdict is a stated absence. It must never be summarized as a
    pass -- the same rule the PRESERVATION_INVALID sentinel exists for.
    """
    record = _graded_session(tmp_path, preservation=[])
    assert all(step.preservation_verdict is None for step in record.steps)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_session_manifest.py tests/test_session_preservation_per_checkpoint.py -q -k "budget or empty_base_preservation or must_be_strings or leaves_verdict_unset"`

Expected: FAIL — "session step must hold exactly id, kind, prompt, new_feature_selectors" and "base_preservation_selectors must be a non-empty list of strings".

- [ ] **Step 3: Widen the step schema**

In `src/satyrn_evals/session_manifest.py`, replace the `_STEP_KEYS`
constant and the `SessionStep` dataclass:

```python
_STEP_KEYS = {"id", "kind", "prompt", "new_feature_selectors"}
_OPTIONAL_STEP_KEYS = {"turn_budget", "tool_budget"}


@dataclass(frozen=True, slots=True)
class SessionStep:
    """One ordered prompt; ``feature`` steps add cumulative hidden selectors.

    ``turn_budget`` and ``tool_budget`` are the declared ceilings for this
    step. ``None`` means no ceiling was declared and the budget verdict is
    reported ``unmeasured`` -- a stated gap, never an inferred pass. The
    ceilings are frozen in the pre-run record before the batch; a ceiling
    chosen after reading the counts is the shape the spike protocol forbids.
    """

    id: str
    kind: StepKind
    prompt: str
    new_feature_selectors: tuple[str, ...]
    turn_budget: int | None = None
    tool_budget: int | None = None
```

- [ ] **Step 4: Parse and validate the budgets**

In `_parse_step`, replace the key check and add budget parsing before the
`return`:

```python
def _parse_step(raw: object) -> SessionStep:
    if not isinstance(raw, dict) or not _STEP_KEYS <= set(raw):
        raise SessionSpecError(
            "session step must hold exactly id, kind, prompt, new_feature_selectors"
        )
    if extra := set(raw) - _STEP_KEYS - _OPTIONAL_STEP_KEYS:
        raise SessionSpecError(f"unknown session step keys: {sorted(extra)}")
```

and, immediately before constructing `SessionStep`:

```python
    budgets: dict[str, int | None] = {}
    for key in sorted(_OPTIONAL_STEP_KEYS):
        value = raw.get(key)
        match value:
            case None:
                budgets[key] = None
            case bool():
                # bool is an int subclass; a JSON true would otherwise
                # silently become a ceiling of 1.
                raise SessionSpecError(f"{key} must be a positive integer")
            case int() if value > 0:
                budgets[key] = value
            case _:
                raise SessionSpecError(f"{key} must be a positive integer")
    return SessionStep(
        id=id_,
        kind=kind,
        prompt=prompt,
        new_feature_selectors=sels_tuple,
        turn_budget=budgets["turn_budget"],
        tool_budget=budgets["tool_budget"],
    )
```

- [ ] **Step 5: Allow an empty preservation list**

In `load_session_spec`, replace the `pres` validation:

```python
    pres = data["base_preservation_selectors"]
    if not isinstance(pres, list) or not all(
        isinstance(s, str) and s for s in pres
    ):
        raise SessionSpecError(
            "base_preservation_selectors must be a list of non-empty strings"
        )
```

The emptiness check is dropped; the per-entry check is kept.

- [ ] **Step 6: Skip preservation grading when nothing is declared**

In `src/satyrn_evals/session_grader.py`, guard the `_grade_preservation`
call site (around line 156):

```python
                if spec.base_preservation_selectors:
                    current, step_unavailable = self._grade_preservation(
                        current, spec, protected, session_dir, receipt_dir
                    )
                    unavailable = unavailable or step_unavailable
```

Without the guard, an empty selection would hand pytest no `-k` argument
and run the whole workspace suite — the model's own tests — which is the
circularity the preservation guard exists to prevent. Leaving
`preservation_verdict` at `None` states the absence instead.

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/test_session_manifest.py tests/test_session_preservation_per_checkpoint.py -q`
Expected: PASS.

Then: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/satyrn_evals/session_manifest.py src/satyrn_evals/session_grader.py tests/test_session_manifest.py tests/test_session_preservation_per_checkpoint.py
git commit -m "Accept per-step budgets and an app-less session base

A step may declare turn_budget and tool_budget; absent means no ceiling
was declared, which is reported unmeasured rather than inferred as a pass.
base_preservation_selectors may now be empty, for a task whose base ships
no application -- cross-phase preservation comes from cumulative feature
grading, not from that list. An empty list skips preservation grading
rather than handing pytest no selection and running the model's own tests.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Capture `elapsed_seconds` per step

**Why:** Wall-clock exists only if captured live; unlike the budget
ceiling, it cannot be recovered from retained artifacts afterward. Under
the repo's stopping rule that is what makes it block the run. It is a
**diagnostic**, never a verdict component (spec §2): the arms' differing
tool surfaces mean an elapsed-time gap would measure the harness.

**Files:**
- Modify: `src/satyrn_evals/session_record.py:43-65`
- Modify: `src/satyrn_evals/session.py:131,225-227,397-398,506`
- Test: `tests/test_session_record.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `StepRecord.elapsed_seconds: float | None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_session_record.py`:

```python
def test_elapsed_seconds_round_trips(tmp_path) -> None:
    step = StepRecord(
        step_id="one",
        prompt_digest="d",
        outcome="settled",
        elapsed_seconds=12.5,
    )
    record = _record_with(steps=(step,))
    reloaded = _write_and_reload(tmp_path, record)
    assert reloaded.steps[0].elapsed_seconds == 12.5


def test_elapsed_seconds_defaults_to_none(tmp_path) -> None:
    """Sibling success: a record written before this field, or a step that
    never ran, carries None -- not 0.0, which would read as an instant
    step."""
    step = StepRecord(step_id="one", prompt_digest="d", outcome="settled")
    reloaded = _write_and_reload(tmp_path, _record_with(steps=(step,)))
    assert reloaded.steps[0].elapsed_seconds is None
```

Use whatever construction and round-trip helpers
`tests/test_session_record.py` already provides; if it writes and reloads
inline, follow that shape rather than adding helpers.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_session_record.py -q -k elapsed`
Expected: FAIL — `StepRecord.__init__() got an unexpected keyword argument 'elapsed_seconds'`.

- [ ] **Step 3: Add the field**

In `src/satyrn_evals/session_record.py`, after `context_events` (line 64):

```python
    context_events: int = 0
    #: Wall-clock seconds this step's prompt took, measured from the send
    #: to the terminal event. A DIAGNOSTIC ONLY: the arms differ in tool
    #: surface (Engine's bounded bash runner versus Baseline's full bash),
    #: so an elapsed-time gap between arms measures the harness, not the
    #: model. Summaries report it with that caveat and never rank on it.
    #: ``None`` means unmeasured, which is not the same as instant.
    elapsed_seconds: float | None = None
```

Keep it before `contamination` if that field's position matters to the
serializer; the existing round-trip test will catch it if so.

- [ ] **Step 4: Measure it in the runner**

In `src/satyrn_evals/session.py`, the step loop already sets
`step_deadline = time.monotonic() + step_timeout` right after the prompt
is sent (line 397). Capture the start on the same clock:

```python
                step_deadline = time.monotonic() + step_timeout
                step_started = step_deadline - step_timeout
                turn_count = tool_count = context_events = 0
```

Deriving `step_started` from `step_deadline` rather than calling
`time.monotonic()` a second time guarantees the elapsed figure is measured
against exactly the deadline the step was judged by, with no gap between
the two reads.

At the checkpoint-capture call (line ~506), pass the elapsed value:

```python
                        turn_count, tool_count, context_events,
                        time.monotonic() - step_started,
```

Add the matching parameter to the capture helper's signature (line 131)
and to its `StepRecord(...)` construction (lines 225-227):

```python
    turn_count: int, tool_count: int, context_events: int,
    elapsed_seconds: float,
```

```python
        turn_count=turn_count,
        tool_count=tool_count,
        context_events=context_events,
        elapsed_seconds=elapsed_seconds,
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_session_record.py tests/test_session_protocol.py tests/test_pi_session_driver.py -q`
Expected: PASS.

Then: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/session_record.py src/satyrn_evals/session.py tests/test_session_record.py
git commit -m "Capture per-step elapsed seconds as a diagnostic

Wall-clock exists only if captured live, so unlike a budget ceiling it
cannot be recovered from retained artifacts -- which is why it lands
before the run. It stays a diagnostic: the arms differ in tool surface,
so an elapsed-time gap between them would measure the harness. None means
unmeasured, not instant.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: The budget verdict and the 2x2

**Why:** Spec §2 — each step yields two verdicts, reported as a 2x2 and
never merged into a scalar, so a budget win cannot mask a correctness
regression. This is pure offline computation over a retained record, so it
is re-scorable and could in principle follow the run; it lands here because
Task 2's fields are meaningless without it.

**Files:**
- Create: `src/satyrn_evals/session_budget.py`
- Test: `tests/test_session_budget.py`

**Interfaces:**
- Consumes: `SessionStep.turn_budget`/`tool_budget` (Task 2), `StepRecord.turn_count`/`tool_count` (existing).
- Produces:
  - `type BudgetVerdict = Literal["within", "over", "unmeasured"]`
  - `type OutcomeCell = Literal["clean", "expensive_pass", "cheap_fail", "expensive_fail", "unmeasured_pass", "unmeasured_fail"]`
  - `budget_verdict(step: SessionStep, record: StepRecord) -> BudgetVerdict`
  - `outcome_cell(feature_verdict: str | None, budget: BudgetVerdict) -> OutcomeCell`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_session_budget.py`:

```python
"""The budget verdict and the 2x2 it forms with correctness.

Both directions are exercised (BRIEF rule 8): a step that fits its
ceilings and a step that breaks each of them separately, so a verdict
stuck at one value cannot pass.
"""

import pytest

from satyrn_evals.session_budget import budget_verdict, outcome_cell
from satyrn_evals.session_manifest import SessionStep
from satyrn_evals.session_record import StepRecord


def _step(**kwargs: object) -> SessionStep:
    return SessionStep(
        id="one",
        kind="feature",
        prompt="p",
        new_feature_selectors=("t::a",),
        **kwargs,
    )


def _record(turns: int, tools: int) -> StepRecord:
    return StepRecord(
        step_id="one",
        prompt_digest="d",
        outcome="settled",
        turn_count=turns,
        tool_count=tools,
    )


def test_within_both_ceilings_is_within() -> None:
    step = _step(turn_budget=10, tool_budget=20)
    assert budget_verdict(step, _record(turns=10, tools=20)) == "within"


def test_exceeding_turns_alone_is_over() -> None:
    step = _step(turn_budget=10, tool_budget=20)
    assert budget_verdict(step, _record(turns=11, tools=20)) == "over"


def test_exceeding_tools_alone_is_over() -> None:
    step = _step(turn_budget=10, tool_budget=20)
    assert budget_verdict(step, _record(turns=10, tools=21)) == "over"


def test_missing_ceiling_is_unmeasured_not_within() -> None:
    """An undeclared ceiling is a stated gap. Treating it as 'within'
    would report a pass nobody measured."""
    step = _step(turn_budget=None, tool_budget=20)
    assert budget_verdict(step, _record(turns=999, tools=1)) == "unmeasured"


@pytest.mark.parametrize(
    ("feature", "budget", "expected"),
    [
        ("pass", "within", "clean"),
        ("pass", "over", "expensive_pass"),
        ("fail", "within", "cheap_fail"),
        ("fail", "over", "expensive_fail"),
        ("pass", "unmeasured", "unmeasured_pass"),
        ("fail", "unmeasured", "unmeasured_fail"),
    ],
)
def test_outcome_cell_covers_the_grid(
    feature: str, budget: str, expected: str
) -> None:
    assert outcome_cell(feature, budget) == expected


def test_ungraded_feature_verdict_is_not_a_failure() -> None:
    """A checkpoint whose hidden grading was skipped has no correctness
    verdict. It must not fall through to a fail cell."""
    with pytest.raises(ValueError, match="feature verdict"):
        outcome_cell(None, "within")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_session_budget.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'satyrn_evals.session_budget'`.

- [ ] **Step 3: Write the module**

Create `src/satyrn_evals/session_budget.py`:

```python
"""Budget as a co-equal verdict, and the 2x2 it forms with correctness.

Design 2026-09-09 §2. Budget is measured in COUNTS, never wall-clock: the
counts come from discrete ``turn_end``/``tool_end`` events
(``session.py:454-460``), so they are immune to the streaming-duplication
defect that inflated three earlier figures by 4-10x, whereas an
elapsed-time gap between arms would measure their differing tool surfaces.

The two verdicts are never merged into a scalar. A scalar would let a
budget improvement mask a correctness regression, and the point of grading
them equally is that both stay visible -- so this module returns a CELL,
not a score.
"""

from typing import Literal

from satyrn_evals.session_manifest import SessionStep
from satyrn_evals.session_record import StepRecord

type BudgetVerdict = Literal["within", "over", "unmeasured"]
type OutcomeCell = Literal[
    "clean",
    "expensive_pass",
    "cheap_fail",
    "expensive_fail",
    "unmeasured_pass",
    "unmeasured_fail",
]


def budget_verdict(step: SessionStep, record: StepRecord) -> BudgetVerdict:
    """Whether this checkpoint stayed inside its declared ceilings.

    Both ceilings must be declared. A partially declared step is
    ``unmeasured``: reporting ``within`` on the strength of the one
    ceiling that exists would claim a measurement nobody made.
    """
    match (step.turn_budget, step.tool_budget):
        case (int() as turns, int() as tools):
            return "over" if record.turn_count > turns or record.tool_count > tools else "within"
        case _:
            return "unmeasured"


def outcome_cell(feature_verdict: str | None, budget: BudgetVerdict) -> OutcomeCell:
    """The 2x2 cell for one checkpoint.

    ``feature_verdict`` of ``None`` means hidden grading was skipped (a
    scope violation, say). That is not a correctness failure and must not
    be reported as one, so it is refused rather than bucketed.
    """
    if feature_verdict is None:
        raise ValueError("no feature verdict: this checkpoint was not graded")
    passed = feature_verdict == "pass"
    match (passed, budget):
        case (True, "within"):
            return "clean"
        case (True, "over"):
            return "expensive_pass"
        case (False, "within"):
            return "cheap_fail"
        case (False, "over"):
            return "expensive_fail"
        case (True, _):
            return "unmeasured_pass"
        case _:
            return "unmeasured_fail"
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_session_budget.py -q`
Expected: PASS.

- [ ] **Step 5: Run ruff and the full suite**

Run: `uv run pytest -q`
Expected: PASS.

Run: `uv run ruff check`
Expected: clean. The `return "over" if ...` line may exceed the line
length; wrap it across lines rather than adding a `noqa`.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/session_budget.py tests/test_session_budget.py
git commit -m "Grade budget as a co-equal verdict, reported as a 2x2

A checkpoint yields correctness and budget, combined into a cell rather
than a scalar: a scalar would let a budget improvement mask a correctness
regression. Budget is counts only -- turn_end/tool_end are discrete
events, so unlike wall-clock they compare across arms. An undeclared
ceiling is unmeasured, never inferred within, and an ungraded checkpoint
is refused rather than bucketed as a failure.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Assemble the task

**Why:** Spec §1 and §3. Everything before this was machinery; this is the
workload.

**Files:**
- Create: `src/satyrn_evals/tasks/agentclinic-session-phased/base/pyproject.toml` (copy)
- Create: `src/satyrn_evals/tasks/agentclinic-session-phased/base/uv.lock` (copy)
- Create: `src/satyrn_evals/tasks/agentclinic-session-phased/grader/overlay/tests/test_acceptance.py` (copy)
- Create: `src/satyrn_evals/tasks/agentclinic-session-phased/manifest.json`
- Create: `src/satyrn_evals/tasks/agentclinic-session-phased/session.json`
- Test: `tests/test_agentclinic_session_phased.py`

**Interfaces:**
- Consumes: `source_dirs` (Task 1), step budgets and empty preservation (Task 2).
- Produces: the task directory that Task 6's witnesses run against.

- [ ] **Step 1: Copy the three files, byte-for-byte**

```bash
T=src/satyrn_evals/tasks/agentclinic-session-phased
mkdir -p $T/base $T/grader/overlay/tests $T/fixtures
cp src/satyrn_evals/tasks/agentclinic-repair-depth-3/base/pyproject.toml $T/base/
cp src/satyrn_evals/tasks/agentclinic-repair-depth-3/base/uv.lock $T/base/
cp src/satyrn_evals/tasks/agentclinic-repair-depth-3/overlay/test_acceptance.py $T/grader/overlay/tests/
```

Do not edit any of the three. `agentclinic-repair-depth-3` is not touched.

- [ ] **Step 2: Write the failing identity and structure test**

Create `tests/test_agentclinic_session_phased.py`:

```python
"""The phased session task: identity, structure, and prompt provenance.

The acceptance suite's trustworthiness rests on byte-identity with the
swiftstar fixture it was recovered from, so identity is asserted rather
than assumed.
"""

from hashlib import sha256
from pathlib import Path

from satyrn_evals.manifest import load_manifest
from satyrn_evals.session_manifest import load_session_spec

TASK = Path("src/satyrn_evals/tasks/agentclinic-session-phased")
DEPTH3 = Path("src/satyrn_evals/tasks/agentclinic-repair-depth-3")


def test_overlay_is_byte_identical_to_depth_3() -> None:
    ours = (TASK / "grader/overlay/tests/test_acceptance.py").read_bytes()
    theirs = (DEPTH3 / "overlay/test_acceptance.py").read_bytes()
    assert sha256(ours).hexdigest() == sha256(theirs).hexdigest()


def test_base_ships_the_environment_and_no_application() -> None:
    """The empty skeleton: dependency files only. Shipping pyproject.toml
    and uv.lock is deliberate -- the spike recorded a solver writing its
    own from a skeleton, which is a scope violation."""
    present = sorted(p.name for p in (TASK / "base").rglob("*") if p.is_file())
    assert present == ["pyproject.toml", "uv.lock"]


def test_three_feature_steps_split_the_checks_four_six_three() -> None:
    spec = load_session_spec(TASK)
    assert [len(s.new_feature_selectors) for s in spec.steps] == [4, 6, 3]
    assert all(s.kind == "feature" for s in spec.steps)


def test_every_declared_selector_exists_in_the_overlay() -> None:
    """A selector naming a test the suite does not define would grade as a
    silent error rather than a failure."""
    source = (TASK / "grader/overlay/tests/test_acceptance.py").read_text()
    spec = load_session_spec(TASK)
    for step in spec.steps:
        for selector in step.new_feature_selectors:
            name = selector.split("::", 1)[1]
            assert f"def {name}(" in source, selector


def test_all_thirteen_checks_are_claimed_exactly_once() -> None:
    spec = load_session_spec(TASK)
    claimed = [s for step in spec.steps for s in step.new_feature_selectors]
    assert len(claimed) == 13
    assert len(set(claimed)) == 13


def test_no_prompt_discloses_a_later_phase() -> None:
    """Correction 7: a phase-1 prompt that disclosed later phases made a
    model build all three phases at once, leaving the later checkpoint
    patches byte-identical."""
    spec = load_session_spec(TASK)
    assert "Phase 2" not in spec.steps[0].prompt
    assert "Phase 3" not in spec.steps[0].prompt
    assert "Phase 3" not in spec.steps[1].prompt


def test_templates_and_tests_are_declared_directories() -> None:
    """Without the trailing-slash declaration the Engine arm cannot write
    templates/home.html, because base/ has no templates/ to probe."""
    manifest = load_manifest(TASK)
    assert {"templates", "tests"} <= manifest.source_dirs


def test_every_step_declares_both_budgets_or_neither() -> None:
    """A partially declared step grades unmeasured, which is a gap rather
    than a measurement -- legal, but it must be deliberate."""
    spec = load_session_spec(TASK)
    for step in spec.steps:
        declared = (step.turn_budget is None, step.tool_budget is None)
        assert declared[0] == declared[1], step.id
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/test_agentclinic_session_phased.py -q`
Expected: FAIL — no `manifest.json`, no `session.json`.

- [ ] **Step 4: Write `manifest.json`**

```json
{
  "name": "agentclinic-session-phased",
  "contract": "Build the AgentClinic application across three ordered development requests: the home page, the complaints board, then adding a complaint.",
  "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"],
  "expected_test_ids": [
    "tests/test_acceptance.py::test_home_still_returns_200_and_tagline"
  ],
  "source_paths": ["app.py", "models.py", "templates/", "tests/"],
  "fixtures": {
    "known_good": "fixtures/known-good.patch",
    "known_broken": "fixtures/known-broken.patch"
  },
  "grader_overlay": "grader/overlay",
  "oracle_visibility": "hidden",
  "provenance": {
    "repo": "https://github.com/pauleveritt/swiftstar.git",
    "base_sha": "ab1d83d06791432f031e55860961529a048d4d9c",
    "fix_sha": "ab1d83d06791432f031e55860961529a048d4d9c"
  }
}
```

`templates/` and `tests/` carry the trailing slash from Task 1: neither
exists in `base/`, so without the declaration both would render as file
patterns. `app.py` and `models.py` do not, since they are file creation
targets exactly like framing-2's.

- [ ] **Step 5: Write `session.json`**

Each prompt is the preamble followed by the roadmap's `## Phase N`
section, quoted from
`/Users/pauleveritt/projects/pauleveritt/swiftstar/fixtures/agenttest/specs/roadmap.md`
at commit `ab1d83d`. Read that file and copy the section text verbatim —
do not paraphrase, and do not include the `## Phase N` heading of any
later phase.

The preamble, identical on all three steps:

```
The project environment is already installed; do not install or reinstall
anything. You may write only app.py, models.py, files under templates/,
and files under tests/. Adding tests under tests/ is expected.
```

Apply exactly two tightenings to the quoted text, and no others:

1. In Phase 2's complaints-card bullet, after `timestamp (formatted)`, add
   `showing year, month and day`. The check requires all three
   (`overlay/tests/test_acceptance.py:127-139`); the section does not say
   so, and the sibling `roadmap-user-story.md` already uses this wording.
2. In Phase 3's form bullets, change `Text input for agent name` to
   `Text input named agent_name` and `Textarea for complaint text` to
   `Textarea named text`. The check requires both names
   (`:194-201`); the section's own route bullet already implies them.

Set `turn_budget` and `tool_budget` to `null` on all three steps for now —
Task 6's calibration pass supplies the numbers, and a ceiling guessed here
would be exactly the after-the-fact choice the protocol forbids. Set
`"base_preservation_selectors": []`.

The three steps' `new_feature_selectors`, all prefixed
`tests/test_acceptance.py::`:

- **phase-1-home** (4): `test_home_has_html5_doctype`,
  `test_home_html_element_declares_english_language`,
  `test_home_still_returns_200_and_tagline`,
  `test_home_still_has_navigation_links`
- **phase-2-board** (6): `test_complaints_board_still_has_its_heading`,
  `test_complaints_board_still_lists_seed_complaint`,
  `test_complaints_board_still_renders_seed_complaint_details`,
  `test_complaints_board_preserves_the_shared_layout`,
  `test_complaint_model_contract_is_preserved`,
  `test_seed_complaint_count_is_preserved`
- **phase-3-add** (3): `test_complaints_board_renders_add_complaint_form`,
  `test_post_complaint_redirects_to_complaints_board`,
  `test_posted_complaint_appears_on_complaints_board`

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_agentclinic_session_phased.py -q`
Expected: PASS.

If `test_every_declared_selector_exists_in_the_overlay` fails, a selector
is misspelled against the suite — fix the selector, never the suite.

- [ ] **Step 7: Run the whole suite and the manifest sweep**

Run: `uv run pytest -q`
Expected: PASS. `tests/test_agentclinic_manifests.py` sweeps task
directories; if it asserts a fixed task count or iterates only
`agentclinic-repair-*`, read what it intends before changing it — a sweep
that silently skips the new task is worse than one that fails.

- [ ] **Step 8: Commit**

```bash
git add src/satyrn_evals/tasks/agentclinic-session-phased tests/test_agentclinic_session_phased.py
git commit -m "Add the phased AgentClinic session task

Three ordered prompts over one growing checkout, from an empty skeleton
that ships only the pinned environment. The oracle is depth-3's
acceptance suite copied byte-for-byte, asserted by digest rather than
assumed; its 13 checks split 4/6/3 and each is claimed exactly once.
Prompts are the swiftstar roadmap's own phase sections, and no prompt
names a later phase -- Correction 7 made structural.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Witnesses, calibration, and the fairness gate

**Why:** Spec §5. A task with no witnesses is an assertion. This task also
produces the budget ceilings Task 5 left `null`.

**Files:**
- Create: `.../fixtures/checkpoint-{1,2,3}.patch` (known-good series)
- Create: `.../fixtures/known-good.patch`, `known-broken.patch`, `prompt-faithful.patch`
- Create: `.../QUALIFICATION-NOTE.md`
- Modify: `.../session.json` (budget ceilings)
- Test: `tests/test_agentclinic_session_phased.py` (witness assertions)

**Interfaces:**
- Consumes: the task directory (Task 5), `budget_verdict` (Task 4).
- Produces: the qualified task, and the frozen ceilings the pre-run record cites.

- [ ] **Step 1: Derive known-good from the swiftstar reference tree**

The reference application is
`/Users/pauleveritt/projects/pauleveritt/swiftstar/fixtures/agenttest/`
at `ab1d83d`. Build three cumulative patches against `base/`: after phase
1 (`app.py`, `templates/base.html`, `templates/home.html`, `tests/`), after
phase 2 (adds `models.py`, `templates/complaints.html`, the GET route),
after phase 3 (adds the POST route and the form). `known-good.patch` is
`checkpoint-3.patch`.

- [ ] **Step 2: Prove known-good passes cumulatively at every checkpoint**

Run each checkpoint patch against `base/` with the overlay and that
checkpoint's cumulative selection. Expected: checkpoint 1 passes its 4,
checkpoint 2 passes 10, checkpoint 3 passes all 13.

A failure here means the phase split is wrong, not the solver. Fix the
split; do not touch the suite.

- [ ] **Step 3: Write known-broken and prove it discriminates**

Follow depth-3's recorded broken intent: an application that satisfies the
public surface but never establishes the model contract, so
`test_complaint_model_contract_is_preserved` fails at checkpoint 2 and is
not silently repaired by checkpoint 3. Record which named check fails at
which checkpoint in the qualification note.

- [ ] **Step 4: Write prompt-faithful with the suite closed**

Write an application using **only** the preamble and the three prompt
texts. Do not open `test_acceptance.py` while writing it. This is the
gate that catches a prompt that under-specifies.

- [ ] **Step 5: Prove prompt-faithful passes AND scans clean**

Both conditions, not one:

```bash
uv run python -c "
from pathlib import Path
from satyrn_evals.contamination import scan_patch
from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
task = Path('src/satyrn_evals/tasks/agentclinic-session-phased')
overlay = load_overlay(task, load_manifest(task))
patch = (task / 'fixtures/prompt-faithful.patch').read_text()
print(scan_patch(patch, overlay))
"
```

Expected: passes all 13 checks, and scans `clean`.

If it **fails a check**: the prompt under-specifies. Fix the prompt, add
the tightening to the qualification note's map, and re-run. Never relax
the suite.

If it **flags contamination**: the prompt's test bullet is steering an
honest solver into text within four non-blank lines of the overlay's own
(`contamination.py:20`). Reword the prompt's test bullet. **Never widen
the window** — the scanner exists to catch copying and must not be tuned
to accommodate our prompt.

- [ ] **Step 6: Calibrate the budget ceilings**

Ceilings come from what the retained evidence actually supports (spec §2):

- **Phase 1 and 2 turn ceilings** may use the spike cells, which are
  uncensored: Phase 1 `8, 10, 10, 11`; Phase 2 `6, 6, 6, 8`
  (`archive/2026-09-07-pre-reset/docs/superpowers/research/2026-09-01-agentclinic-spike.md:288-292`).
- **Phase 3's turn ceiling must not use the spike cells.** Two of the four
  (24 and 22) are censored lower bounds from runs that hit the 300s cap
  (`:294-296`, `:409`). A ceiling from a censored maximum is biased low.
- **No `tool_budget` may come from the spike table at all** — it records
  tool *errors*, not tool-call totals.

So run the known-good and prompt-faithful witnesses through the session
runner to get per-phase turn and tool counts, and set each ceiling from
those. Witness runs use no model, so this costs no inference.

Record in the qualification note, per phase: the ceiling, its source
(spike cells or calibration), and — for any phase where calibration
cannot establish a defensible bound — leave the ceiling `null` and state
that its budget verdict is `unmeasured`. A stated gap, never a guess.

- [ ] **Step 7: Write `QUALIFICATION-NOTE.md`**

It must carry:

- The 13-row check-to-prompt-line map: for each check, the prompt line
  that makes it satisfiable, and whether that line is quoted roadmap text
  or one of the two tightenings.
- The sha256 of the roadmap file the prompts were quoted from, the
  `swiftstar` commit `ab1d83d`, and the command that recomputes the digest.
- The note that check names read as preservation language
  (`still_`, `_is_preserved`) for historical reasons, while phase 1 grades
  them as new features — and that renaming was rejected because it would
  forfeit byte-identity with the source.
- Each witness: what it is, what it demonstrates, and the exact named
  checks it fails at which checkpoint.
- The budget ceilings with their per-phase provenance from step 6.

- [ ] **Step 8: Add witness assertions to the test file**

```python
def test_known_good_and_known_broken_form_a_contamination_pair() -> None:
    """A new task owes its own pair; it does not inherit one."""
    manifest = load_manifest(TASK)
    for key in ("known_good", "known_broken"):
        assert (TASK / manifest.fixtures[key]).is_file()


def test_prompt_faithful_fixture_exists() -> None:
    """The fairness gate is an artifact, not a claim: it must be on disk
    for a later reader to re-run."""
    assert (TASK / "fixtures/prompt-faithful.patch").is_file()


def test_qualification_note_records_the_roadmap_digest() -> None:
    note = (TASK / "QUALIFICATION-NOTE.md").read_text()
    assert "ab1d83d" in note
    assert "sha256" in note.lower()
```

- [ ] **Step 9: Run the gates**

Run: `uv run pytest tests/test_agentclinic_session_phased.py -q`
Expected: PASS.

Run: `just gates`
Expected: exit 0. Read the exit code directly. **Do not pipe it.**

- [ ] **Step 10: Commit**

```bash
git add src/satyrn_evals/tasks/agentclinic-session-phased tests/test_agentclinic_session_phased.py
git commit -m "Qualify the phased session task with three witnesses

known-good from the swiftstar reference tree passes cumulatively at every
checkpoint; known-broken fails a named check at a named checkpoint and is
not silently repaired later; prompt-faithful was written with the suite
closed and must both pass and scan clean.

Budget ceilings are calibrated rather than guessed. Phase 1 and 2 turn
ceilings come from the spike's uncensored cells; Phase 3's and every tool
ceiling come from witness runs, because two Phase 3 cells are censored
lower bounds and the spike table records tool errors rather than totals.
A phase whose ceiling cannot be established stays unmeasured.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: The phase-leak detector (does not block the run)

**Why:** Spec §4 and §5. This reads `patch_digest`, which is already
persisted, so it can be built after the run and applied to retained
artifacts. Under the repo's stopping rule — a fix precedes an authorized
run only if it blocks that run or cannot be re-scored afterward — it
waits. **Do not execute this task before the batch runs.**

**Files:**
- Modify: `src/satyrn_evals/session_budget.py`
- Test: `tests/test_session_budget.py`

**Interfaces:**
- Consumes: `StepRecord.patch_digest` (existing).
- Produces: `phase_leak(steps: Sequence[StepRecord]) -> tuple[str, ...]` — the ids of steps whose patch is byte-identical to their predecessor's.

- [ ] **Step 1: Write the failing tests**

```python
from satyrn_evals.session_budget import phase_leak


def test_identical_successive_patches_are_a_leak() -> None:
    """Correction 7's signature: a model that built later phases early
    leaves the later checkpoints with nothing to add."""
    steps = (
        _record_with_digest("one", "aaa"),
        _record_with_digest("two", "aaa"),
        _record_with_digest("three", "bbb"),
    )
    assert phase_leak(steps) == ("two",)


def test_distinct_patches_are_not_a_leak() -> None:
    """Sibling success: ordinary progress reports nothing."""
    steps = (
        _record_with_digest("one", "aaa"),
        _record_with_digest("two", "bbb"),
    )
    assert phase_leak(steps) == ()


def test_missing_digest_is_not_reported_as_a_leak() -> None:
    """Two ungraded checkpoints both carry None. Calling that a leak would
    manufacture a finding out of missing data."""
    steps = (
        _record_with_digest("one", None),
        _record_with_digest("two", None),
    )
    assert phase_leak(steps) == ()
```

Add `_record_with_digest(step_id, digest)` beside the existing `_record`
helper, returning a `StepRecord` with `patch_digest=digest`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_session_budget.py -q -k leak`
Expected: FAIL — `ImportError: cannot import name 'phase_leak'`.

- [ ] **Step 3: Implement**

Append to `src/satyrn_evals/session_budget.py`:

```python
def phase_leak(steps: Sequence[StepRecord]) -> tuple[str, ...]:
    """Checkpoints whose patch is byte-identical to their predecessor's.

    Correction 7 (spike:378-382): a phase-1 prompt that disclosed later
    phases made a model build all three at once, leaving its phase-2 and
    phase-3 patches byte-identical. This makes that a measurement.

    A ``None`` digest is missing data, not a match: two ungraded
    checkpoints must not manufacture a finding.
    """
    return tuple(
        step.step_id
        for previous, step in zip(steps, steps[1:], strict=False)
        if previous.patch_digest is not None
        and previous.patch_digest == step.patch_digest
    )
```

Add `from collections.abc import Sequence` to the imports.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_session_budget.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/session_budget.py tests/test_session_budget.py
git commit -m "Detect a phase leak from retained checkpoint digests

Correction 7 recorded a model building all three phases during phase 1,
leaving its later patches byte-identical. This turns that from a
remembered anecdote into a count, over artifacts already persisted. A
missing digest is missing data, never a match.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Longest no-edit run (does not block the run)

**Why:** Spec §4's misdiagnosis-loop observable. The spike's reference
signature is a `follow_redirects` loop that spent roughly 17 tool calls
"fixing" a redirect that was already correct
(`archive/2026-09-07-pre-reset/docs/superpowers/research/2026-09-01-agentclinic-spike.md:303-308`),
in 2 of 4 baseline runs. The general shape is a run of tool calls with no
edit between them. Computed from a retained transcript, so it is
re-scorable and waits until after the batch, like Task 7.

**The trap this task must avoid.** `message_update` events are
**snapshots**: iterating them and counting tool calls inflates the figure —
that defect produced 4.2x, 5.5x and 9.9x overcounts on three separate
occasions (`docs/development/lessons.md`). Count from `tool_end` events,
which are discrete and emitted once per call
(`src/satyrn_evals/session.py:457`). `tool_end` carries the tool name but
no arguments (`session_repeat_limit.py:43-45`), and a name is all this
detector needs.

**Files:**
- Modify: `src/satyrn_evals/session_budget.py`
- Test: `tests/test_session_budget.py`

**Interfaces:**
- Consumes: `tool_end` event names from a step's transcript prefix.
- Produces: `longest_no_edit_run(tool_names: Sequence[str], edit_tools: frozenset[str]) -> int`.

- [ ] **Step 1: Write the failing tests**

```python
from satyrn_evals.session_budget import EDIT_TOOLS, longest_no_edit_run


def test_run_between_edits_is_measured() -> None:
    names = ["read", "bash", "bash", "edit", "read", "bash"]
    assert longest_no_edit_run(names, EDIT_TOOLS) == 3


def test_trailing_run_after_the_last_edit_counts() -> None:
    """The follow_redirects loop was a tail: the route landed early and
    the spending came after it, with nothing further written."""
    names = ["edit", "bash", "bash", "bash", "bash"]
    assert longest_no_edit_run(names, EDIT_TOOLS) == 4


def test_all_edits_is_zero() -> None:
    """Sibling success: a step that edits every turn has no idle run."""
    assert longest_no_edit_run(["edit", "write", "edit"], EDIT_TOOLS) == 0


def test_no_tool_calls_is_zero() -> None:
    """A step that called nothing did not loop. Zero, not an error."""
    assert longest_no_edit_run([], EDIT_TOOLS) == 0


def test_unknown_tool_counts_as_no_edit() -> None:
    """A tool this harness does not recognise did not write anything, so
    it belongs to the run. Guessing the other way would hide a loop."""
    assert longest_no_edit_run(["mystery", "mystery"], EDIT_TOOLS) == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_session_budget.py -q -k no_edit`
Expected: FAIL — `ImportError: cannot import name 'longest_no_edit_run'`.

- [ ] **Step 3: Implement**

Append to `src/satyrn_evals/session_budget.py`:

```python
#: Tool names that write to the workspace. Both arms are covered: Baseline
#: runs pi with ``read,bash,edit,write``, and the Engine arm registers its
#: mutator alongside a bounded ``run_tests``. A name absent here counts as
#: no-edit, which can only lengthen a reported run -- the safe direction,
#: since the alternative hides a loop.
EDIT_TOOLS = frozenset({"edit", "write", "mutator", "apply_patch"})


def longest_no_edit_run(
    tool_names: Sequence[str], edit_tools: frozenset[str]
) -> int:
    """The longest streak of consecutive tool calls that wrote nothing.

    The misdiagnosis-loop statistic (design 2026-09-09 §4). Feed the names
    from ``tool_end`` events in order -- NEVER from ``message_update``,
    whose payloads are snapshots and inflate every count taken from them.
    """
    longest = current = 0
    for name in tool_names:
        current = 0 if name in edit_tools else current + 1
        longest = max(longest, current)
    return longest
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_session_budget.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/session_budget.py tests/test_session_budget.py
git commit -m "Measure the longest no-edit run per step

The misdiagnosis-loop statistic: the spike recorded ~17 tool calls spent
fixing a redirect that was already correct, in 2 of 4 runs. Counted from
tool_end events, which are discrete -- never from message_update, whose
snapshot payloads produced 4.2x, 5.5x and 9.9x overcounts on three
earlier occasions. An unrecognised tool counts as no-edit, which can only
lengthen a run; the opposite default would hide a loop.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Execution order

Tasks 1-6 must land before the batch runs. Tasks 7 and 8 wait until after.

Tasks 1, 2 and 3 are independent of one another and may be done in any
order or in parallel. Task 4 depends on Task 2. Task 5 depends on Tasks 1
and 2. Task 6 depends on Tasks 3, 4 and 5.

## Out of scope

Named here so an executor does not add them:

- Wall-clock as a verdict component.
- Renaming any acceptance check.
- Relaxing, reordering or editing the acceptance suite.
- Vendoring `specs/` into any task's `base/`.
- A generic budget framework — two session tasks is not three.
- Any edit to `agentclinic-repair-depth-3`.
