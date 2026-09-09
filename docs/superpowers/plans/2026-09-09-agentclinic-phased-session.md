# Phased AgentClinic Session Workload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one bounded Baseline session of three ordered development requests against a growing checkout, and report correctness beside raw cost, so cross-prompt pathologies become observable.

**Architecture:** A new task `agentclinic-session-phased` whose `base/` holds only the pinned environment, whose hidden checks are the depth-3 acceptance assertions extracted into three independently collectable modules, and whose three prompts are the swiftstar roadmap's own phase sections. Two runtime changes precede it. Everything else waits for evidence from the first run.

**Tech Stack:** Python 3.14, `uv`, pytest, `just`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-09-agentclinic-phased-session-design.md`, **including its 2026-09-09 correction section**, which refutes parts of §1-§5. Read the correction first: where the body and the correction disagree, the correction governs.

## Global Constraints

- **Python `>=3.14` house style.** Real return annotations; `type` aliases; `match`/`case` for dispatch; walrus for bind-and-test. A review that rewrites these into older forms is wrong (`CLAUDE.md`).
- **Default tests use no model, no network, no subprocess.** A planted process-spawning test enforces this. Never weaken or remove it. Tests needing the real thing are marked `@pytest.mark.integration`, which `addopts` excludes (`pyproject.toml:57-61`).
- **A refusal test has a sibling success test.** Rejection is the default outcome of most failures, so a broken refusal test passes silently.
- **Verify, don't assert.** Cite `file:line`. Never write down a number you did not compute; carry the command that recomputes it.
- **Gates:** `just gates`. Read the exit code. **Never pipe a gate into `tail` or anything else.**
- **Fixture pins stay exact:** `fastapi[standard]==0.115.10`, `turbohtml==1.5.0`, `pytest==8.3.4`.
- **Do not modify `agentclinic-repair-depth-3`.** It is the assertion source.
- **Assertion bodies are copied verbatim.** The extraction changes module structure only. If an assertion needs editing to work, stop and report — that is a finding, not a step.
- **No budget verdict, no pass/fail cost threshold.** The first run reports raw counts and elapsed time beside correctness. A threshold, if wanted later, is declared as an operational allowance and labelled a judgment.

---

### Task 1: Two runtime corrections

**Why:** Both block the run and neither is recoverable afterward. An
app-less base cannot load its session spec; elapsed time exists only if
captured live.

**Files:**
- Modify: `src/satyrn_evals/session_manifest.py:86-92`
- Modify: `src/satyrn_evals/session_grader.py:150-160`
- Modify: `src/satyrn_evals/session_record.py:43-65` and its loader at `:186-194`
- Modify: `src/satyrn_evals/session.py:131,225-227,397,506`
- Test: `tests/test_session_manifest.py`, `tests/test_session_preservation_per_checkpoint.py`, `tests/test_session_record.py`, `tests/integration/test_session_grading.py`

**Interfaces:**
- Produces: `SessionSpec.base_preservation_selectors` may be `()`; `StepRecord.elapsed_seconds: float | None`.

- [x] **Step 1: Write the failing tests for the empty preservation list**

Add to `tests/test_session_manifest.py`:

```python
def test_empty_base_preservation_selectors_are_allowed(tmp_path) -> None:
    """A base that ships no application has no base behaviour to preserve.
    Cross-phase preservation comes from cumulative feature grading."""
    spec = _write_and_load(
        tmp_path, steps=[_step("one"), _step("two")], preservation=[]
    )
    assert spec.base_preservation_selectors == ()


def test_base_preservation_selectors_must_be_non_empty_strings(tmp_path) -> None:
    """Refusal, narrowed: an empty list is now legal, an empty entry is not."""
    with pytest.raises(SessionSpecError, match="base_preservation_selectors"):
        _write_and_load(
            tmp_path, steps=[_step("one"), _step("two")], preservation=[""]
        )
```

If `_write_and_load` / `_step` do not exist with these keywords, add them,
defaulting `preservation` to the file's current non-empty value so every
existing test keeps its meaning.

Add to `tests/test_session_preservation_per_checkpoint.py`:

```python
def test_no_preservation_selectors_leaves_verdict_unset(tmp_path) -> None:
    """Not graded and not inferred. An unset verdict is a stated absence
    and must never be summarized as a pass -- the rule the
    PRESERVATION_INVALID sentinel already exists for."""
    record = _graded_session(tmp_path, preservation=[])
    assert all(step.preservation_verdict is None for step in record.steps)
```

- [x] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_session_manifest.py tests/test_session_preservation_per_checkpoint.py -q -k "empty_base_preservation or non_empty_strings or leaves_verdict_unset"`
Expected: FAIL — "base_preservation_selectors must be a non-empty list of strings".

- [x] **Step 3: Allow the empty list**

In `src/satyrn_evals/session_manifest.py`, replace the `pres` validation:

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

- [x] **Step 4: Skip preservation grading when nothing is declared**

In `src/satyrn_evals/session_grader.py`, guard the `_grade_preservation`
call site (around line 156):

```python
                if spec.base_preservation_selectors:
                    current, step_unavailable = self._grade_preservation(
                        current, spec, protected, session_dir, receipt_dir
                    )
                    unavailable = unavailable or step_unavailable
```

Without the guard an empty selection hands pytest no selection and runs
the whole workspace suite — the model's own tests — which is exactly the
circularity the preservation guard exists to prevent.

- [x] **Step 5: Write the failing tests for elapsed capture**

Add to `tests/test_session_record.py`:

```python
def test_elapsed_seconds_round_trips_through_the_loader(tmp_path) -> None:
    """The loader is explicit field-by-field (session_record.py:186-194),
    so a new field is dropped silently unless it is added there too."""
    step = StepRecord(
        step_id="one", prompt_digest="d", outcome="settled", elapsed_seconds=12.5
    )
    reloaded = _write_and_reload(tmp_path, _record_with(steps=(step,)))
    assert reloaded.steps[0].elapsed_seconds == 12.5


def test_elapsed_seconds_absent_from_json_loads_as_none(tmp_path) -> None:
    """Sibling success, and the missingness rule: a record written before
    this field carries None, not 0.0, which would read as an instant step."""
    step = StepRecord(step_id="one", prompt_digest="d", outcome="settled")
    reloaded = _write_and_reload(tmp_path, _record_with(steps=(step,)))
    assert reloaded.steps[0].elapsed_seconds is None
```

Add to `tests/integration/test_session_grading.py`:

```python
def test_elapsed_seconds_is_recorded_for_a_clean_session(tmp_path: Path) -> None:
    """Dataclass round-tripping is not evidence the runner measures anything."""
    record = _graded(tmp_path, "clean")
    assert all(
        step.elapsed_seconds is not None and step.elapsed_seconds >= 0.0
        for step in record.steps
    )


def test_elapsed_seconds_excludes_teardown_on_a_timeout(tmp_path: Path) -> None:
    """The figure must bound the prompt, not the reaping that follows it.
    A step killed at its deadline reports about the deadline, not the
    deadline plus however long terminate_and_reap took."""
    record = _graded(tmp_path, "timeout", step_timeout=1.0)
    slow = record.steps[-1]
    assert slow.elapsed_seconds is not None
    assert slow.elapsed_seconds < 5.0
```

The `"timeout"` scenario may not exist in
`tests/integration/fake_session_adapter.py`. If not, add one that accepts
a prompt and then emits nothing, so the step hits its deadline. Follow the
existing scenario dispatch rather than inventing a second mechanism.

- [x] **Step 6: Run them to verify they fail**

Run: `uv run pytest tests/test_session_record.py -q -k elapsed`
Expected: FAIL — unexpected keyword argument `elapsed_seconds`.

Run: `uv run pytest tests/integration/test_session_grading.py -q -m integration -k elapsed`
Expected: FAIL for the same reason.

- [x] **Step 7: Add the field and load it**

In `src/satyrn_evals/session_record.py`, after `context_events`:

```python
    context_events: int = 0
    #: Wall-clock seconds this step's prompt took, sampled when the step
    #: settles and BEFORE teardown -- a reaped adapter's cleanup is not the
    #: model's spending. A DIAGNOSTIC ONLY: the arms differ in tool surface,
    #: so an elapsed-time gap between them measures the harness, not the
    #: model. ``None`` means unmeasured, which is not the same as instant.
    elapsed_seconds: float | None = None
```

In the loader (line ~192), beside the other counts:

```python
            elapsed_seconds=step.get("elapsed_seconds"),
```

No default of `0.0`: absent must load as `None`.

- [x] **Step 8: Sample it where the step settles**

In `src/satyrn_evals/session.py`, capture the start on the same clock the
deadline uses (line ~397):

```python
                step_deadline = time.monotonic() + step_timeout
                step_started = step_deadline - step_timeout
```

Deriving the start from the deadline rather than reading the clock twice
guarantees the figure is measured against exactly the deadline the step
was judged by.

Then sample **once, at the point the step's event loop exits and before
any `terminate_and_reap`**, into a local:

```python
                step_elapsed = time.monotonic() - step_started
```

Pass `step_elapsed` to the checkpoint capture (line ~506) rather than
reading the clock there. Every `stop` path — settled, timeout, protocol
error — must pass through this one sample; if the control flow makes that
awkward, restructure so it does rather than adding a second sample. Add
the parameter to the capture helper's signature (line 131) and to its
`StepRecord(...)` construction (lines 225-227).

- [x] **Step 9: Run the tests**

Run: `uv run pytest -q`
Expected: PASS.

Run: `uv run pytest -q -m integration`
Expected: PASS.

- [x] **Step 10: Commit**

```bash
git add src/satyrn_evals tests
git commit -m "Allow an app-less session base, and measure per-step elapsed time

base_preservation_selectors may be empty, for a task whose base ships no
application; an empty list skips preservation grading rather than handing
pytest no selection and running the model's own tests. Cross-phase
preservation comes from cumulative feature grading, not that list.

elapsed_seconds is sampled once where the step settles, before teardown,
so a reaped adapter's cleanup is not counted as the model's spending. It
is added to the explicit record loader too, where a new field is
otherwise dropped silently, and absent loads as None rather than zero.
It stays a diagnostic: the arms differ in tool surface.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: The task, its phase-compatible checks, and its witnesses

**Why:** These cannot be separated. `load_manifest` requires the fixture
files to exist (`src/satyrn_evals/manifest.py:275-281`), so the task does
not load until its witnesses exist; and the witnesses are what prove the
extracted checks grade the phases they claim to.

**The extraction, and why it is required.** The depth-3 acceptance module
runs `from app import app`, `import models`, `from models import
Complaint` and `SEED_COMPLAINTS = tuple(models.complaints)` in its body
(`agentclinic-repair-depth-3/overlay/test_acceptance.py:14-29`).
Collection imports the module before any selector applies, so a phase-1
workspace — which has no `models.py` — fails at import for every
selector. Whole-file byte identity is therefore impossible here.
**Assertion bodies are copied verbatim**; only the module structure
changes, and provenance is claimed per check.

**Files:**
- Create: `.../base/{pyproject.toml,uv.lock}` (copies)
- Create: `.../grader/overlay/grader_tests/{_contract.py,_seed.py,test_phase1_home.py,test_phase2_board.py,test_phase3_add.py}`
- Create: `.../{manifest.json,session.json,QUALIFICATION-NOTE.md}`
- Create: `.../fixtures/{checkpoint-1,checkpoint-2,checkpoint-3,known-good,known-broken,prompt-faithful,contaminated}.patch`
- Test: `tests/test_agentclinic_session_phased.py`, `tests/integration/test_session_phased_qualification.py`

- [x] **Step 1: Copy the environment; do not copy the suite**

```bash
T=src/satyrn_evals/tasks/agentclinic-session-phased
mkdir -p $T/base $T/grader/overlay/grader_tests $T/fixtures
cp src/satyrn_evals/tasks/agentclinic-repair-depth-3/base/pyproject.toml $T/base/
cp src/satyrn_evals/tasks/agentclinic-repair-depth-3/base/uv.lock $T/base/
```

The overlay goes under `grader_tests/`, **not** `tests/`. `tests/` is a
declared source path, and `load_overlay` refuses an overlay path that
falls inside `source_paths` (`src/satyrn_evals/overlay.py:80`). The guard
stays; the location moves.

- [x] **Step 2: Write `grader_tests/_contract.py`**

The shared preamble, with **no models import**:

```python
"""Shared fixtures for the phased acceptance checks.

Extracted from agentclinic-repair-depth-3/overlay/test_acceptance.py so
that phase 1 is independently collectable: that module imports `models`
at load, and collection imports before selection, so a phase-1 workspace
with no models.py fails at import for every selector.

Nothing here touches models. Assertion bodies in the sibling test modules
are copied verbatim from the source; only the module structure differs.
"""

from starlette.testclient import TestClient
from turbohtml import Doctype, parse

from app import app

client = TestClient(app)
client.__enter__()  # run FastAPI lifespan/startup before any snapshot

TAGLINE = "Come in. Sit down. Tell us about your human."
SEED_COMPLAINT = "Scope creep never ends."


def _normalized_text(element) -> str:
    return " ".join(element.text.split())


def _has_html5_doctype(document) -> bool:
    return any(
        isinstance(node, Doctype) and node.name.casefold() == "html"
        for node in document.children
    )
```

- [x] **Step 3: Write `grader_tests/_seed.py`**

```python
"""The seed snapshot, imported only by phases that need models.

`_contract` is imported FIRST and for effect: the snapshot must be taken
after `client.__enter__()` has run the FastAPI lifespan, or seeding via a
startup hook -- a valid reading of the roadmap's "module-level list" --
looks identical to an empty store. This ordering is load-bearing; it is
the reason the source module interleaved these two statements.

pytest imports every selected module during collection, before any test
runs, so this snapshot is still taken before phase 3's POST tests mutate
`models.complaints`.
"""

from dataclasses import MISSING, fields

import models
from models import Complaint

from grader_tests import _contract  # noqa: F401  -- imported for lifespan order

SEED_COMPLAINTS = tuple(models.complaints)

__all__ = ["Complaint", "MISSING", "SEED_COMPLAINTS", "fields"]
```

If a bare `grader_tests` package import does not resolve in the graded
workspace, add an empty `grader_tests/__init__.py` and keep the import
absolute. Do not switch to a `sys.path` manipulation.

- [x] **Step 4: Write the three test modules, copying assertion bodies verbatim**

`test_phase1_home.py` imports from `_contract` only and carries these four
bodies unchanged from the source: `test_home_still_returns_200_and_tagline`
(`:47-50`), `test_home_has_html5_doctype` (`:53-56`),
`test_home_html_element_declares_english_language` (`:59-63`),
`test_home_still_has_navigation_links` (`:66-79`).

`test_phase2_board.py` imports from `_contract` and `_seed` and carries
six: `test_complaints_board_still_lists_seed_complaint` (`:82-85`),
`test_complaints_board_preserves_the_shared_layout` (`:88-104`),
`test_complaints_board_still_has_its_heading` (`:107-108`),
`test_complaints_board_still_renders_seed_complaint_details` (`:111-139`),
`test_complaint_model_contract_is_preserved` (`:142-151`),
`test_seed_complaint_count_is_preserved` (`:154-155`).

`test_phase3_add.py` imports from `_contract` only — none of its three
checks touch models — and carries
`test_post_complaint_redirects_to_complaints_board` (`:158-168`),
`test_posted_complaint_appears_on_complaints_board` (`:171-183`),
`test_complaints_board_renders_add_complaint_form` (`:186-206`).

Preserve the source module's `follow_redirects=False` note as a comment in
`test_phase3_add.py`. It records the trap this suite exists not to fall
into (`overlay/test_acceptance.py:6-11`).

- [x] **Step 5: Write the verbatim-assertion test**

Create `tests/test_agentclinic_session_phased.py`:

```python
"""The phased session task: provenance, structure, and prompt discipline."""

import ast
from pathlib import Path

from satyrn_evals.manifest import load_manifest
from satyrn_evals.session_manifest import load_session_spec

TASK = Path("src/satyrn_evals/tasks/agentclinic-session-phased")
SOURCE = Path(
    "src/satyrn_evals/tasks/agentclinic-repair-depth-3/overlay/test_acceptance.py"
)
GRADER = TASK / "grader/overlay/grader_tests"


def _functions(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text())
    return {
        node.name: ast.unparse(node)
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def test_every_extracted_check_is_verbatim() -> None:
    """Whole-file identity is impossible (the source imports models at
    load). Per-assertion identity is not, and it is what the provenance
    claim now rests on."""
    source = _functions(SOURCE)
    extracted: dict[str, str] = {}
    for module in sorted(GRADER.glob("test_phase*.py")):
        extracted |= _functions(module)
    assert len(extracted) == 13
    for name, body in extracted.items():
        assert name in source, f"{name} is not in the source suite"
        assert body == source[name], f"{name} was edited during extraction"


def test_phase_one_module_does_not_reach_models() -> None:
    """The whole reason for the extraction. If this fails, phase 1 cannot
    be graded at all -- collection imports before selection applies."""
    text = (GRADER / "test_phase1_home.py").read_text()
    assert "models" not in text
    assert "_seed" not in text


def test_base_ships_the_environment_and_no_application() -> None:
    present = sorted(p.name for p in (TASK / "base").rglob("*") if p.is_file())
    assert present == ["pyproject.toml", "uv.lock"]


def test_overlay_does_not_fall_inside_the_writable_scope() -> None:
    """load_overlay refuses this overlap (overlay.py:80); asserting it here
    names the reason rather than leaving a load error to explain it."""
    manifest = load_manifest(TASK)
    assert not any(
        source in {"grader_tests"} or "grader_tests".startswith(f"{source}/")
        for source in manifest.source_paths
    )


def test_three_feature_steps_split_the_checks_four_six_three() -> None:
    spec = load_session_spec(TASK)
    assert [len(s.new_feature_selectors) for s in spec.steps] == [4, 6, 3]
    assert all(s.kind == "feature" for s in spec.steps)


def test_all_thirteen_checks_are_claimed_exactly_once() -> None:
    spec = load_session_spec(TASK)
    claimed = [s for step in spec.steps for s in step.new_feature_selectors]
    assert len(claimed) == 13 == len(set(claimed))


def test_no_prompt_discloses_a_later_phase() -> None:
    """Correction 7: a phase-1 prompt disclosing later phases made a model
    build all three at once."""
    spec = load_session_spec(TASK)
    assert "Phase 2" not in spec.steps[0].prompt
    assert "Phase 3" not in spec.steps[0].prompt
    assert "Phase 3" not in spec.steps[1].prompt


def test_no_step_declares_a_budget_ceiling() -> None:
    """The first run reports raw counts. A ceiling here would be a
    judgment wearing a measurement's clothes."""
    spec = load_session_spec(TASK)
    assert all(
        getattr(step, "turn_budget", None) is None for step in spec.steps
    )
```

- [x] **Step 6: Write `manifest.json`**

```json
{
  "name": "agentclinic-session-phased",
  "contract": "Build the AgentClinic application across three ordered development requests: the home page, the complaints board, then adding a complaint.",
  "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"],
  "expected_test_ids": [
    "grader_tests/test_phase1_home.py::test_home_still_returns_200_and_tagline"
  ],
  "source_paths": ["app.py", "models.py", "templates", "tests"],
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

`templates` and `tests` are bare. The session scope check uses
`within_source`, where a bare directory entry already admits its
descendants (`src/satyrn_evals/patch.py:176-178`, used at
`session.py:218`). Declared directory paths matter only to the Engine
contract, and no Engine session arm exists — see Deferred.

- [x] **Step 7: Write `session.json`**

Each prompt is the preamble followed by the roadmap's `## Phase N`
section, quoted from
`/Users/pauleveritt/projects/pauleveritt/swiftstar/fixtures/agenttest/specs/roadmap.md`
at `ab1d83d`. Read that file and copy the section verbatim. Include no
later phase's heading or text.

Preamble, identical on all three steps:

```
The project environment is already installed; do not install or reinstall
anything. You may write only app.py, models.py, files under templates/,
and files under tests/. Adding tests under tests/ is expected.
```

Exactly two tightenings, and no others:

1. Phase 2's card bullet: after `timestamp (formatted)`, add
   `showing year, month and day`. The check requires all three
   (source `:126-138`); the section does not say so, and the sibling
   `roadmap-user-story.md` already uses this wording.
2. Phase 3's form bullets: `Text input for agent name` becomes
   `Text input named agent_name`, and `Textarea for complaint text`
   becomes `Textarea named text`. The check requires both names
   (source `:194-201`); the section's own route bullet already implies them.

Set `"base_preservation_selectors": []`. Declare **no** budget fields.

Selectors, all prefixed with their module path:

- **phase-1-home** (4), `grader_tests/test_phase1_home.py::` —
  `test_home_has_html5_doctype`,
  `test_home_html_element_declares_english_language`,
  `test_home_still_returns_200_and_tagline`,
  `test_home_still_has_navigation_links`
- **phase-2-board** (6), `grader_tests/test_phase2_board.py::` —
  `test_complaints_board_still_has_its_heading`,
  `test_complaints_board_still_lists_seed_complaint`,
  `test_complaints_board_still_renders_seed_complaint_details`,
  `test_complaints_board_preserves_the_shared_layout`,
  `test_complaint_model_contract_is_preserved`,
  `test_seed_complaint_count_is_preserved`
- **phase-3-add** (3), `grader_tests/test_phase3_add.py::` —
  `test_complaints_board_renders_add_complaint_form`,
  `test_post_complaint_redirects_to_complaints_board`,
  `test_posted_complaint_appears_on_complaints_board`

- [x] **Step 8: Build the witnesses**

From the swiftstar reference tree at
`/Users/pauleveritt/projects/pauleveritt/swiftstar/fixtures/agenttest/`:

- `checkpoint-1.patch` — phase 1 only: `app.py`, `templates/base.html`,
  `templates/home.html`, `tests/`. **No `models.py`.** This patch is the
  one that proves the extraction worked.
- `checkpoint-2.patch` — cumulative through phase 2.
- `checkpoint-3.patch` — cumulative through phase 3; `known-good.patch` is
  a copy of it.
- `known-broken.patch` — satisfies the public surface but never
  establishes the model contract, so
  `test_complaint_model_contract_is_preserved` fails at checkpoint 2 **and
  is still failing at checkpoint 3**.
- `regression.patch` — a checkpoint-3 tree in which a phase-1 behaviour
  genuinely broke (drop `lang="en"` from `base.html`), so a check that
  passed at checkpoint 1 fails at checkpoint 3. Without this the
  cross-phase claim is untested.
- `contaminated.patch` — a checkpoint-3 tree containing four or more
  consecutive non-blank lines lifted from a grader module. The positive
  half of the contamination pair: without it, a scanner that never fires
  looks identical to a clean workspace.
- `prompt-faithful.patch` — written using **only** the preamble and the
  three prompt texts, with the grader modules closed.

- [x] **Step 9: Write the qualification gate that actually grades**

Create `tests/integration/test_session_phased_qualification.py`. Follow
the construction in `tests/integration/test_session_grading.py`; mark the
module `pytestmark = pytest.mark.integration`.

```python
def test_known_good_passes_cumulatively_at_every_checkpoint(tmp_path) -> None:
    """4 at checkpoint 1, 10 at checkpoint 2, 13 at checkpoint 3.

    Checkpoint 1 is the load-bearing one: it has no models.py, so it also
    proves the phase-1 module is independently collectable.
    """
    assert _graded_counts(tmp_path, "checkpoint-1") == (4, 4)
    assert _graded_counts(tmp_path, "checkpoint-2") == (10, 10)
    assert _graded_counts(tmp_path, "checkpoint-3") == (13, 13)


def test_known_broken_fails_a_named_check_and_stays_failing(tmp_path) -> None:
    """A witness that fails *something* is not a witness. Name it, and
    check it is not silently repaired by a later checkpoint."""
    failures = _failed_check_names(tmp_path, "known-broken", checkpoint=3)
    assert "test_complaint_model_contract_is_preserved" in failures


def test_a_later_checkpoint_can_regress_an_earlier_phase(tmp_path) -> None:
    """The cross-phase claim, tested rather than assumed: a phase-1 check
    that passed at checkpoint 1 fails on a checkpoint-3 tree."""
    assert "test_home_html_element_declares_english_language" in _failed_check_names(
        tmp_path, "regression", checkpoint=3
    )


def test_prompt_faithful_passes_every_check(tmp_path) -> None:
    """The fairness gate. A failure means the prompt under-specifies --
    fix the prompt, never the checks."""
    assert _graded_counts(tmp_path, "prompt-faithful") == (13, 13)


def test_prompt_faithful_scans_clean(tmp_path) -> None:
    assert _contamination(tmp_path, "prompt-faithful") == "clean"


def test_the_contaminated_witness_is_flagged(tmp_path) -> None:
    """The positive half. A scanner that never fires would pass the
    clean-side test on its own."""
    assert _contamination(tmp_path, "contaminated") == "flagged"
```

Write `_graded_counts` (returns passed, total) and `_failed_check_names`
by applying the named patch over `base/`, overlaying the grader modules,
and running the cumulative selection through the real grader — not by
reading a fixture's contents. `_contamination` calls `scan_patch` with the
loaded overlay.

- [x] **Step 10: Run everything**

Run: `uv run pytest tests/test_agentclinic_session_phased.py -q`
Expected: PASS.

Run: `uv run pytest tests/integration/test_session_phased_qualification.py -q -m integration`
Expected: PASS.

If `test_prompt_faithful_passes_every_check` fails, the prompt
under-specifies: fix the prompt, add the tightening to the qualification
note, re-run. If `test_prompt_faithful_scans_clean` fails, reword the
prompt's test bullet — **never widen the contamination window**
(`src/satyrn_evals/contamination.py:20`).

Run: `just gates`
Expected: exit 0.

- [x] **Step 11: Write `QUALIFICATION-NOTE.md`, then commit**

It must carry: the 13-row check-to-prompt-line map, marking each line as
quoted roadmap text or one of the two tightenings; the `swiftstar` commit
and the roadmap file's sha256 with the command that recomputes it; **the
extraction record** — that whole-file identity was impossible because the
source imports `models` at load, that assertion bodies are verbatim, and
that `test_every_extracted_check_is_verbatim` is what enforces it; the
note that check names read as preservation language for historical
reasons while phase 1 grades them as new features; and each witness with
the exact named checks it fails at which checkpoint.

```bash
git add src/satyrn_evals/tasks/agentclinic-session-phased tests
git commit -m "Add the phased AgentClinic session task, with witnesses that grade

Three ordered prompts over one growing checkout from an empty skeleton.
The hidden checks are the depth-3 assertions extracted into three
independently collectable modules: the source imports models at load and
collection precedes selection, so the unchanged file cannot grade a
phase-1 workspace at all. Assertion bodies are copied verbatim and a test
compares their ASTs against the source, so provenance is claimed per
check rather than per file.

The overlay lives under grader_tests/, not tests/, because tests/ is
writable and load_overlay refuses an overlay inside source_paths.

Qualification grades rather than asserting existence: cumulative
correctness at all three checkpoints, a named persistent failure in the
broken witness, a phase-1 check genuinely regressing on a checkpoint-3
tree, and both halves of the contamination pair.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: One bounded Baseline session

**Why:** The point of the exercise. Everything above exists to make this
run interpretable.

- [ ] **Step 1: Verify the environment the preamble promises**

The preamble tells the solver the environment is installed. Prove it
before saying so: materialize `base/`, run the pinned install, and confirm
`fastapi`, `turbohtml` and `pytest` import at the pinned versions. If they
do not, the preamble is a false statement to the model and the run is
void. The spike's largest phase-1 tool-error class came from exactly this
gap being real (`archive/2026-09-07-pre-reset/.../2026-09-01-agentclinic-spike.md:298-301`).

- [ ] **Step 2: Write the pre-run record**

Before any inference. It states: the arm (**Baseline only** — no Engine
session arm exists), the model and full sampling recipe, `n` frozen, the
step timeout, the three prompt digests, the task digest, and the
questions. The cost question is **descriptive**: what did each phase cost
in turns, tool calls and seconds. No threshold, no budget verdict.

Declare the observables as **candidate findings requiring trace
inspection**, not verdicts: checkpoint patches with no net change,
stretches with no successful write, scope violations, compaction events,
and any earlier-phase check failing at a later checkpoint.

- [ ] **Step 3: Quiet the machine and run**

An unattended batch needs a quiet machine; that precondition is
operational, and `MODEL_ERROR` classifies an out-of-memory after the fact
rather than preventing one.

- [ ] **Step 4: Report correctness and raw cost side by side**

Per phase, per session: feature verdict, preservation verdict (unset for
this task, and reported as unset — never inferred), turns, tool calls,
compaction events, elapsed seconds with the harness caveat stated.

- [ ] **Step 5: Inspect the trajectory and pick one obstruction**

Read the transcripts. Select **one** concrete obstruction to pursue. Build
further classification only if it serves that investigation — a detector
written before a trace has demanded it is instrument work, and
`AGENTS.md` caps consecutive instrument-only pieces at two.

---

## Deferred, with the condition that would reopen each

- **Declared directory source paths.** Needed only by the Engine contract
  renderer; the session path uses `within_source`, where a bare directory
  entry already admits descendants. Reopens when an Engine session arm
  exists.
- **An Engine session arm.** Does not exist, and building one is engine
  design rather than adapter glue: the mutator and runner assume one
  frozen contract carrying a `test_command`, and a session has no
  per-prompt equivalent
  (`docs/current/agentclinic-phase-session-proposal.md:118-121`). Until it
  exists, this workload says nothing about Engine versus Baseline, and no
  report may imply otherwise.
- **A budget verdict subsystem.** Deferred on its own merits, not merely
  reordered: the drafted classifier bucketed every non-`pass` string —
  `unavailable` included — as a failure, and `turn_count`/`tool_count`
  load with a default of `0` (`src/satyrn_evals/session_record.py:190-192`),
  so a record missing counts would have produced a `within` verdict out of
  absent data. Reopens when a run has produced counts worth thresholding,
  and then only with explicit measured-count provenance and explicit
  correctness missingness.
- **Cost thresholds of any kind.** A patch witness cannot calibrate model
  effort: it carries the resulting code, not the investigation that
  produced it, so applying it measures the script that applies it.
  Reopens as a declared operational allowance, labelled a judgment.
- **Phase-leak and no-edit-run detectors.** Both were named beyond their
  evidence. Identical successive patches mean *no net change*; leakage
  would have to be established by checking whether a later phase's
  requirements were already satisfied. Tool names cannot establish that
  nothing was written — `bash` writes files, and a refused `edit` does
  not — nor does an edit-free stretch establish misdiagnosis. Reopen as
  candidate-finding observations feeding trace inspection, if a trace asks
  for them.

## Out of scope

- Editing, relaxing, reordering or renaming any acceptance assertion.
- Vendoring `specs/` into any task's `base/`.
- Any edit to `agentclinic-repair-depth-3`.
- Wall-clock as anything but a caveated diagnostic.
