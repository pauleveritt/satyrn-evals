# Qualifying agentclinic-session-phased

Three ordered development requests over one growing checkout, starting from
a base that carries the locked environment and no application at all. The
hidden checks are the depth-3 acceptance assertions, extracted into three
independently collectable modules.

`BRIEF.md`'s two selection rules apply: this note qualifies the task as a
**grader fixture** — its witnesses are graded and its prompts are shown to
be sufficient. Nothing here establishes it as a diagnostic workload; no
session has been run against it.

## The prompt source

Each prompt is a fixed preamble followed by the roadmap's own `## Phase N`
section, quoted from
`github.com/pauleveritt/swiftstar` at `ab1d83d06791432f031e55860961529a048d4d9c`,
file `fixtures/agenttest/specs/roadmap.md`:

    d470ba450101c669a3475cc388bd753f174bc749f6ed7cf2d3e114853453ff0c

Recompute it with:

```bash
git -C <swiftstar> show ab1d83d:fixtures/agenttest/specs/roadmap.md | shasum -a 256
```

The preamble, identical on all three steps, states the writable scope. It is
the information a single-prompt contract carries in `writable_paths`, and it
is not in the roadmap:

> Dependencies are pinned in pyproject.toml and uv.lock, and `uv run` provisions them from the lock; do not install packages yourself or add new dependencies. You may write only app.py, models.py, files under templates/,
> and files under tests/. Adding tests under tests/ is expected. Before finishing, run `uv run python -m pytest tests`. Address failures caused by your changes without weakening tests, and report the command and result.

**Exactly two tightenings** were applied to the quoted sections. Both are
recorded in the map below and nowhere else in the prompts:

1. *Phase 2, card bullet.* `timestamp (formatted)` became
   `timestamp (formatted) showing year, month and day`. The check requires
   all three tokens; the section did not say so. The sibling
   `roadmap-user-story.md` in the same directory already uses this wording.
2. *Phase 3, form bullets.* `Text input for agent name` became
   `Text input named agent_name`, and `Textarea for complaint text` became
   `Textarea named text`. The check requires both control names; the
   section's own route bullet (`Read agent_name and text from form data`)
   already implies them.

No later phase's heading or text appears in an earlier prompt
(`test_no_prompt_discloses_a_later_phase`). No step declares a budget
ceiling: the first run reports raw counts.

## The map: every check, and the prompt line that establishes it

| # | check | prompt line | source |
|---|---|---|---|
| 1 | `test_home_still_returns_200_and_tagline` | "A hero/jumbotron section with the tagline: *\"Come in. Sit down. Tell us about your human.\"*"; "Add the `/` route in `app.py` returning the home template" | quoted roadmap, phase 1 |
| 2 | `test_home_has_html5_doctype` | "HTML5 doctype and `<html lang=\"en\">`" | quoted roadmap, phase 1 |
| 3 | `test_home_html_element_declares_english_language` | "HTML5 doctype and `<html lang=\"en\">`" | quoted roadmap, phase 1 |
| 4 | `test_home_still_has_navigation_links` | "A simple navbar with \"AgentClinic\" brand and links to Home (`/`) and Complaints (`/complaints`)" | quoted roadmap, phase 1 |
| 5 | `test_complaints_board_still_lists_seed_complaint` | "Add `GET /complaints` route in `app.py`"; "including the exact text `Scope creep never ends.`" | quoted roadmap, phase 2 |
| 6 | `test_complaints_board_preserves_the_shared_layout` | "Create `templates/complaints.html` that extends `base.html`", against phase 1's doctype, `lang`, and navbar bullets | quoted roadmap, phases 1 and 2 |
| 7 | `test_complaints_board_still_has_its_heading` | "A heading: \"Complaints Board\"" | quoted roadmap, phase 2 |
| 8 | `test_complaints_board_still_renders_seed_complaint_details` | "render each as a Bootstrap card showing agent name, timestamp (formatted) **showing year, month and day**, and complaint text" | **tightening 1** |
| 9 | `test_complaint_model_contract_is_preserved` | "Fields: `agent_name: str`, `text: str`, `timestamp: datetime`"; "Set `timestamp` with `field(default_factory=lambda: datetime.now(timezone.utc))` so each new complaint receives its own UTC creation timestamp" | quoted roadmap, phase 2 |
| 10 | `test_seed_complaint_count_is_preserved` | "Populate `complaints` with 3-5 seed complaints" | quoted roadmap, phase 2 |
| 11 | `test_post_complaint_redirects_to_complaints_board` | "Redirect to `GET /complaints` (use `RedirectResponse` with status 303)" | quoted roadmap, phase 3 |
| 12 | `test_posted_complaint_appears_on_complaints_board` | "Create a new `Complaint` and append to the `complaints` list", with phase 2's card loop | quoted roadmap, phases 2 and 3 |
| 13 | `test_complaints_board_renders_add_complaint_form` | "`POST` method to `/complaints`"; "**Text input named agent_name**"; "**Textarea named text**"; "Submit button" | **tightening 2** (two of four bullets) |

Tightening 1 was verified load-bearing by mutation on 2026-09-09: replacing
`prompt-faithful.patch`'s `strftime("%d %B %Y")` with `strftime("%B")` turned
check 8 red (12/13), and reverting turned it green.

## The extraction record

The depth-3 acceptance module runs `from app import app`, `import models`,
`from models import Complaint` and `SEED_COMPLAINTS = tuple(models.complaints)`
in its body (`agentclinic-repair-depth-3/overlay/test_acceptance.py:13-29`).
pytest imports a test module during collection, before any selector applies,
so that file cannot grade a phase-1 workspace at all — that workspace has no
`models.py`, and every selector would fail at import.

**Whole-file byte identity is therefore impossible here.** What is claimed
instead is per-assertion identity:

- The 13 assertion bodies are copied verbatim; only the module structure
  changed. `_contract.py` carries the client, the lifespan entry and the two
  helpers, with no `models` import; `_seed.py` carries the seed snapshot and
  is imported only by phase 2.
- `tests/test_agentclinic_session_phased.py::test_every_extracted_check_is_verbatim`
  is what enforces it. It parses both the source module and the three
  extracted modules and compares each function's AST, so an edit made during
  or after extraction fails the build.
- `test_phase_one_module_does_not_reach_models` is the other half: the
  phase-1 module must mention neither `models` nor `_seed`. Verified
  load-bearing by mutation on 2026-09-09 — adding
  `from grader_tests._seed import SEED_COMPLAINTS` to the phase-1 module
  turned checkpoint-1 grading from 4/4 into 0/0, and reverting restored it.

`_seed.py`'s import order is load-bearing and is commented as such: the
snapshot must be taken after `client.__enter__()` has run the FastAPI
lifespan, or an application that seeds from a startup hook — a valid reading
of the roadmap's "module-level list" — is indistinguishable from an empty
store. That is why the source module interleaved those two statements.

The overlay lives under `grader_tests/`, not `tests/`. `tests/` is a declared
source path, and `load_overlay` refuses an overlay path that falls inside
`source_paths` (`src/satyrn_evals/overlay.py:80`). The guard stays; only the
location moved.

**The check names read as preservation language** — `still_returns`,
`is_preserved`, `still_has` — because they were written for a repair task,
where every check guarded behaviour that already existed. Here phase 1
*builds* the home page, so the same four checks grade a new feature. The
names were not rewritten, because the assertion bodies are copied verbatim
and renaming them would break the provenance claim above.

## The witnesses

Graded by `tests/integration/test_session_phased_qualification.py`, which
applies each patch over `base/`, materializes the grader modules, and runs
the real oracle over the cumulative selection. No row reads a fixture's
contents.

| witness | checkpoint | result |
|---|---|---|
| `checkpoint-1` | 1 (4 checks) | 4/4 pass. No `models.py` in the tree — this is the row that proves the phase-1 module is independently collectable |
| `checkpoint-2` | 2 (10 checks) | 10/10 pass |
| `checkpoint-3` | 3 (13 checks) | 13/13 pass |
| `known-good` | 3 | copy of `checkpoint-3`; 13/13 pass |
| `known-broken` | 2 | fails exactly `test_complaint_model_contract_is_preserved` (naive `datetime.now` default factory) |
| `known-broken` | 3 | still fails `test_complaint_model_contract_is_preserved` — not silently repaired by a later checkpoint |
| `regression` | 3 | a checkpoint-3 tree with `lang="en"` dropped from `base.html`: fails `test_home_html_element_declares_english_language` (a phase-1 check, and the cross-phase witness — it passes at checkpoint 1) and `test_complaints_board_preserves_the_shared_layout` (a phase-2 check that does not run at checkpoint 1 at all) |
| `prompt-faithful` | 3 | 13/13 pass, written from the preamble and the three prompt texts |
| `contaminated` | 3 | grades 13/13 pass, and the contamination scan flags it |

Contamination is a pair, both halves asserted: `prompt-faithful` scans
`clean`, `contaminated` scans `flagged` (evidence: `grader_tests/_contract.py`
lifted into `tests/test_layout.py`). A scanner that never fired would satisfy
the clean side alone. The other six witnesses also scan clean, though no test
asserts that.

## Known limitation: a false positive the detector can produce here

`GRADER_BLOCK_LINES` is 4 (`src/satyrn_evals/contamination.py:20`) and the
window was **not** widened. Measured on 2026-09-09: a solver whose own POST
test ends

```
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/complaints"
```

matches `grader_tests/test_phase3_add.py` verbatim on four consecutive
non-blank lines and is flagged, despite having copied nothing. The phase-3
prompt says `Location: /complaints` with a capital L, and httpx header lookup
is case-insensitive, so the spelling the prompt suggests does not collide —
which is why every witness here scans clean. This is a property of a
four-line verbatim window over idiomatic test code, not of the prompt; the
correct response to a flag is to read the evidence, not to widen the window.

## What is still not established

That the task is a **workload**. It is fair and its scope is stated, but no
session has been run against it, so nothing here shows that the three
requests discriminate between engines or that a model can finish them.
Admission would need a probe — a separate job, and one no fixture can
substitute for.

## Known limitation: `prompt-faithful` does not establish check-blindness

The `prompt-faithful` gate establishes that a prompt-derivable implementation
scoring 13/13 *exists*, which rules out "no prompt-conformant solution can
pass." It does **not** establish that a check-blind solver lands in the
passing region, because its author had read the checks — the extraction
required it (see "Caveat" in the extraction record above).

Two ambiguities in the prompt text, found by review and still unprobed,
would each fail a reading the prompt permits:

1. `test_complaint_model_contract_is_preserved` requires positional
   construction, `Complaint("first", "First complaint")`. A solver that adds
   an `id` field ahead of `agent_name` — a reading the "Fields:" bullet does
   not exclude — fails this check even though the field list it names is
   present.
2. `test_home_still_has_navigation_links` requires link text that normalizes
   to exactly `home` and `complaints`. A solver that writes "Home Page" for
   the link label — a reading the "links to Home (`/`)" bullet does not
   exclude — fails this check.

Closing this needs a fresh-author probe (someone who has not read the
checks) or a model probe (a session run against this task with no access to
the grader), not another fixture.

## Correction, 2026-09-09 — the preamble's environment claim was false

The preamble quoted above previously opened "The project environment is
already installed; do not install or reinstall anything." The first live
session's own verification call disproved it: the attempt workspace does not
arrive installed, and `uv run` printed `Creating virtual environment at:
.venv / Installed 47 packages in 80ms`. The sentence was also
self-contradictory once the verification instruction was added, since
`uv run python -m pytest tests` provisions.

Replaced with a true statement of the same intent — dependencies are pinned
and `uv run` provisions them from the lock, and the model still must not
install packages or add dependencies. The original sentence existed to prevent
a recorded failure class (a model spending turns on `pip install` for
already-present packages, 7 of 10 phase-1 tool errors in the 2026-09-01
spike); the replacement keeps that prohibition.

Evidence: `~/satyrn-smokes/2026-09-09-session-phased-verify-114708/RESULT.md`.
