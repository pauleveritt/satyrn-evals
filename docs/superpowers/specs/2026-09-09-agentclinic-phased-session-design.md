# Phased AgentClinic session workload — design

Date: 2026-09-09
Status: design approved in chat, section by section; not yet planned or built.

## Purpose

Observe pathologies that appear across successive development requests in
one accumulating conversation — the class of failure that a single-prompt
repair task cannot show. The workload sends three ordered prompts to one
session against one growing checkout, snapshots a cumulative patch at each
checkpoint, and grades offline.

Correctness is not the primary output. The 2026-09-01 spike ceilinged
(`deepest_pass` 3, 3, 3, 3 —
`archive/2026-09-07-pre-reset/docs/superpowers/research/2026-09-01-agentclinic-spike.md:24`)
and still produced named, countable pathologies. This design states up
front that **a correctness ceiling is not a workload failure**, and makes
budget a co-equal verdict so a ceilinged run still discriminates.

## 1. Task shape and phase mapping

New task `agentclinic-session-phased`, alongside the six repair tasks. It
borrows nothing from them at runtime; it copies two files.

`base/` ships the environment and nothing else: `pyproject.toml` and
`uv.lock` copied from `agentclinic-repair-depth-3/base/`, preserving the
pins `fastapi[standard]==0.115.10 turbohtml==1.5.0 pytest==8.3.4`. No
`app.py`, no `models.py`, no `templates/`, no `tests/`. That is the empty
skeleton. Shipping the two dependency files is deliberate: the spike
recorded a solver writing its own `pyproject.toml` from a skeleton
(`spike:332-336`), and any write outside `source_paths` blocks that
checkpoint's feature grade (`src/satyrn_evals/session_grader.py:65-88`).

`grader/overlay/tests/test_acceptance.py` is
`agentclinic-repair-depth-3/overlay/test_acceptance.py`, copied
byte-for-byte. `agentclinic-repair-depth-3` is not modified. That overlay
is byte-identical to `swiftstar` `ab1d83d`'s
`fixtures/agenttest/acceptance/test_acceptance.py`, verified by `diff`;
`ab1d83d` is the `source commit` recorded in the task's `PROVENANCE`.

The 13 checks split by phase:

| Phase | Count | Checks |
|---|---|---|
| 1 | 4 | doctype, `html lang="en"`, tagline, nav links |
| 2 | 6 | seed complaint listed, shared layout, heading, seed details rendered, model contract, seed count |
| 3 | 3 | 303 redirect, posted complaint appears, add form present |

`session.json` declares three `kind: "feature"` steps. Step N's
`new_feature_selectors` are phase N's checks; steps 2 and 3 additionally
carry every earlier phase's checks as preservation.
`base_preservation_selectors` is empty — base has no application, so there
is no prior behaviour to preserve.

### Two things named rather than papered over

**The check names read backwards.** They say
`test_home_still_returns_200_and_tagline` and
`test_seed_complaint_count_is_preserved` because they were written for a
repair task. Here, phase 1's step grades them as new-feature checks. The
assertions are correct; only the names are odd. They are **not** renamed:
renaming forfeits byte-identity with the swiftstar source and with
depth-3's overlay, which is the reason this oracle is trustworthy. The
mismatch is recorded in `QUALIFICATION-NOTE.md`.

**`source_paths` has a real gap for an empty skeleton.**
`src/satyrn_evals/engine_contract.py:45` derives the Engine arm's writable
patterns as `f"{entry}/*" if (base / entry).is_dir() else entry` —
directory-ness inferred by looking in `base/`. With `templates` and
`tests` absent from base, both become file patterns rather than directory
globs, and the Engine arm could not write `templates/home.html`.
`src/satyrn_evals/overlay.py:80` already handles this correctly with an
explicit prefix test, so the two disagree. See §5, prerequisite 1.

## 2. Outcome model: budget as a co-equal verdict

Today a step's outcome is correctness alone; `turn_count`, `tool_count`
and `context_events` ride along on `StepRecord`
(`src/satyrn_evals/session_record.py:62-64`) as diagnostics.

Each step instead produces **two verdicts, reported as a 2x2 and never
merged into a scalar**:

|  | within budget | over budget |
|---|---|---|
| **correct** | clean | expensive pass |
| **incorrect** | cheap fail | expensive fail |

A weighted scalar is rejected: it would let a budget improvement mask a
correctness regression, and the point of grading them equally is that both
stay visible.

### Budget is counts, and the ceiling is declared before the run

Each step in `session.json` gains `turn_budget` and `tool_budget`.
Exceeding either is `over`. Ceilings are frozen in the pre-run record
alongside `n`; a ceiling chosen after seeing this batch's counts is the
shape the spike protocol forbids.

**Where the numbers come from, and where they cannot.** The retained
spike telemetry is thinner than it first appears, and the spec states the
limit rather than papering over it. `spike:288-296` records turns per
phase across four passing baseline runs — Phase 1: 8, 10, 10, 11; Phase
2: 6, 6, 6, 8; Phase 3: 22, 7, 24, 11 — but:

- **Two Phase 3 cells are censored.** The 24 and 22 runs hit the 300 s
  per-prompt cap, so both are lower bounds, not completed counts
  (`spike:294-296`, `spike:409`). **No ceiling may be derived from a
  censored cell.** A ceiling set from a censored maximum is biased low and
  would mark as "over budget" runs that no uncensored observation ever
  bounded.
- **The table records tool _errors_, not tool-call totals.** `tool_budget`
  therefore cannot be derived from it.

So ceilings are set as follows, and each phase's ceiling records its own
provenance in the pre-run record:

1. **Phase 1 and Phase 2 turn ceilings** may be derived from the spike
   cells, all of which are uncensored.
2. **Phase 3's turn ceiling and every `tool_budget`** come from a
   calibration pass over the known-good and prompt-faithful witnesses,
   run before the batch and recorded. Witness runs are not model runs;
   this costs no inference against the batch.
3. If calibration cannot establish a defensible ceiling for some phase,
   that phase's budget verdict is recorded as `unmeasured` rather than
   guessed. An `unmeasured` budget is a stated gap, never an inferred
   pass.

These counts are safe to carry a verdict because they come from discrete
terminal events, not from snapshot text: `src/satyrn_evals/session.py:454-460`
increments on `turn_end` and `tool_end`. They are therefore immune to the
streaming-duplication defect that inflated three earlier figures by 4-10x
(`docs/development/lessons.md`).

### Wall-clock is recorded and kept out of the verdict

`CLAUDE.md` forbids comparing wall-clock between arms; two published
figures were retracted for exactly that. The hazard is worse here, because
the arms differ in tool surface: Engine's bounded bash runner and
Baseline's full bash have different per-call latencies for reasons
unrelated to model behaviour, so a wall-clock gap would measure the
harness. `StepRecord` gains `elapsed_seconds`, reported as a diagnostic
with that caveat stated in every summary.

If elapsed time is later wanted as a verdict component it needs its own
protocol — quiet machine, interleaved alternation, reported as a
distribution rather than a mean — and its own slice. It is out of scope
here.

Turn and tool counts do capture "how long" in the sense that survives
across machines, and they are what a phase leak or a misdiagnosis loop
inflates. The spike's `follow_redirects` loop spent roughly 17 tool calls
"fixing" a redirect that was already correct (`spike:280-308`) — an
*expensive pass*, which today's instrument scores identically to a clean
one.

`context_events` remains a third reported axis, not a verdict. A model
that compacts once and finishes cheaply is not worse than one that never
compacts and burns twice the turns; folding compaction into the budget
verdict would assert an exchange rate that has not been measured.

## 3. Prompts and the fairness gate

**Prompt N is the roadmap's `## Phase N` section, quoted verbatim** from
`swiftstar` `ab1d83d`, `fixtures/agenttest/specs/roadmap.md` (56 lines,
three phases) — the commit this fixture's `PROVENANCE` names as its
source. The section text is stored in `session.json` as a string. Nothing
is vendored into the workspace. The source file's sha256 is recorded in
`QUALIFICATION-NOTE.md` so a later reader can prove the prompts were
quoted rather than drafted.

Phase 1's prompt never mentions phases 2 or 3. This is Correction 7 made
structural: a phase-1 prompt that disclosed later phases caused DeepSeek
Flash to build all three phases during phase 1, leaving its phase-2 and
phase-3 patches byte-identical (`spike:378-382`). Per-step revelation is
free — `src/satyrn_evals/session.py:392` sends only the current step's
prompt — which is why vendoring the whole roadmap file is unnecessary as
well as harmful.

**One fixed preamble** prepends every step, identical across all three,
stating three things:

1. The environment is already installed and must not be reinstalled. The
   spike's largest phase-1 tool-error class was `pip: command not found` —
   the model installing what was already installed — 7 of 10 phase-1 tool
   errors (`spike:298-301`). The spike attributes this to the roadmap
   carrying no Environment section; the `swiftstar` revision quoted here
   likewise has none, so the preamble supplies what the spec omits.
2. The writable scope, named explicitly.
3. That adding tests under `tests/` is expected, since the roadmap asks
   for them.

### Two tightenings, in the prompt, not the suite

Walking all 13 checks against the roadmap text found exactly two places
where a check demands more than its section states:

- **Phase 2** says "timestamp (formatted)"; the check requires year, month
  and day all present. The prompt adds "showing year, month and day" —
  wording the sibling `roadmap-user-story.md` already uses, so it is not
  an invention.
- **Phase 3**'s form bullet says "Text input for agent name"; the check
  requires `name="agent_name"` and a textarea named `text`. The section's
  own route bullet already implies both ("Read `agent_name` and `text`
  from form data"). The prompt states them at the form.

Everything else the checks demand is already in the section text: the
tagline, the `.card` class implied by "Bootstrap card", the literal
`/complaints`, 3-5 seeds, and the per-instance `default_factory`
timestamp.

The suite is not relaxed. Twelve of the thirteen checks are also the
carried-forward preservation signal
(`overlay/test_acceptance.py:44, 208-249`); loosening a check to fit a
prompt would weaken regression detection at the same time.

### The fairness gate: `fixtures/prompt-faithful.patch`

The pattern that rescued `session-ordering-regression` after every session
failed its step 1 (`QUALIFICATION-NOTE.md:21-23`: "The fix is in the
prompt, not the checks"). Written strictly from preamble plus section
text, with the hidden suite closed. It must satisfy **two** conditions:

1. It passes every cumulative check at every checkpoint. A failure means
   the prompt under-specifies, and the prompt is fixed — never the suite.
2. **It scans clean for contamination.** The session path calls
   `scan_patch(capture.patch_text, overlay)` with no `visible_texts`
   subtraction (`src/satyrn_evals/session.py:160`), and the block window is
   four non-blank lines (`src/satyrn_evals/contamination.py:20`). The
   roadmap's phase-3 test bullets describe a `follow_redirects=False`
   assertion closely enough that an honest solver's test could land within
   four lines of the overlay's own. If prompt-faithful flags, the prompt's
   test bullet is reworded; the window is never widened. The scanner exists
   to catch copying and must not be tuned to accommodate our prompt.

### On the V11a reversal

V11a deliberately reversed the decision to vendor `specs/` into `base/`
(`archive/2026-09-07-pre-reset/docs/superpowers/research/2026-09-05-roadmap-amendment-v11-trim.md:23-32`).
Its stated reason was mechanical: `grade.py` builds `visible_texts` from
every file under `base/`, and the contamination scanner subtracts any
overlay window that also appears there, so vendoring "could silence the
known-broken half of the contamination pair test." Its reopen condition
concerns the existing six repair tasks' placement, not a new session task.

That objection does not reach this design, for two independent reasons:
this design vendors nothing, and the session path passes no
`visible_texts` at all (`session.py:160`). A new task owes its own
contamination pair regardless; see §5.

## 4. Observables and the pre-run declaration

Declared before the run, with `n` frozen and no extension after reading
the result:

- **Budget overruns per phase** — the 2x2 of §2, per step, per arm.
- **Phase leak** — successive checkpoint patches that are byte-identical,
  or a phase-N patch that already satisfies phase N+1's checks. This makes
  Correction 7 a measurement rather than a hope. `patch_digest` is already
  persisted on `StepRecord`, so the detector is a comparison over retained
  artifacts, not new capture.
- **Misdiagnosis loops** — repeated tool calls against behaviour that
  already passes. The spike's `follow_redirects` loop is the reference
  signature; the general shape is a run of tool calls with no edit between
  them, so the recorded statistic is the longest no-edit run per step.
- **Scope violations** — writes outside `source_paths`, and specifically
  root-level config files, which is how a skeleton start goes wrong.
- **Preservation flips** — a phase-1 or phase-2 check that passed at its
  own checkpoint and fails at a later one, attributed to the checkpoint
  that broke it. This is the cross-prompt pathology the workload exists to
  observe.
- **Compaction events** — reported, not scored.

Two questions are stated separately in the pre-run record: the **outcome**
question (does either arm reach more phases correctly) and the **cost**
question (does either arm reach them within budget). They may answer
differently, and the record must let them.

### Consequence: counting moves inside publishability condition (c)

Until now a defect in turn or tool counting was diagnostic-only and could
be re-scored at leisure. Promoting budget to a verdict means a counting
defect touches **verdict counts** and blocks publication exactly as a
grading defect does. This is affordable because the counts come from
discrete `turn_end`/`tool_end` events rather than snapshot text (§2), but
the classification changes and the pre-run record says so explicitly.

## 5. Witnesses, qualification, and build order

### Witnesses

Three, all derived by running real suites, none asserted. Following
`session-ordering-regression`'s layout, each is a per-checkpoint patch
series rather than a single diff, because grading happens at every
checkpoint:

- **known-good** — the swiftstar reference tree, split into three
  checkpoint patches. Every cumulative check passes at every checkpoint. If
  it does not, the phase split is wrong, not the solver.
- **known-broken** — fails discriminatingly at a *named* checkpoint, and
  fails in a way a later checkpoint does not silently repair. Depth-3's
  recorded broken intent (fixes the redirect and `lang`, never touches
  `models.py`) is the model: a defect the public suite cannot see.
- **prompt-faithful** — §3, gated on both passing and scanning clean.

known-good and known-broken together form this task's own contamination
pair. It is not inherited from another task.

### `QUALIFICATION-NOTE.md`

Carries the artifacts that make fairness checkable by someone who was not
present:

- the 13-row check-to-prompt-line map;
- the sha256 of the roadmap file the prompts were quoted from, and the
  `swiftstar` commit;
- the two tightenings, each with the check it serves;
- the note that check names read as preservation language for historical
  reasons while phase 1 grades them as new features.

### Build order, and what blocks the run

The repo's rule: a fix may precede an authorized run only if it **blocks
that run** or **cannot be re-scored afterward**. Applying it:

1. **`writable_paths` directory-ness — blocks.**
   `engine_contract.py:45` infers directory-ness from `base/`, so with an
   empty skeleton the Engine arm cannot write `templates/`. Fix: declared
   rather than inferred. A refusal test and its sibling success test, per
   house rule.
2. **Budget fields and `elapsed_seconds` — blocks, partly.** Turn and tool
   counts are already captured, so a *ceiling* is applied offline; freezing
   it beforehand is a discipline requirement, not a capture one.
   `elapsed_seconds` is different: it exists only if captured live, so it
   must land before the run or it is lost permanently.
3. **Task assembly — blocks.** `base/`, overlay copy, `session.json`,
   witnesses, qualification note.
4. **Phase-leak detector — does not block.** It reads `patch_digest`,
   already persisted, so it can be built after the run and applied to
   retained artifacts. Under the stopping rule it waits.

The run needs items 1-3. Item 4 follows.

## Out of scope

- Wall-clock as a verdict component (§2).
- Renaming the acceptance checks (§1).
- Relaxing the acceptance suite (§3).
- Vendoring `specs/` into any task's `base/` (§3).
- A generic budget framework. Two session tasks is not three; the design
  adds fields, not an abstraction.

## Correction, 2026-09-09 — the premise of §1 and §3 is refuted

Recorded, not edited away. Five blocking findings from external review,
all confirmed against the code. The first is fatal to this design's spine.

**1. The unchanged acceptance suite cannot grade Phase 1.** §1 asserts
that phase N's step grades phase N's checks from the copied file
unchanged. It cannot. The module body runs `from app import app`,
`import models`, `from models import Complaint`, and
`SEED_COMPLAINTS = tuple(models.complaints)` at import time
(`agentclinic-repair-depth-3/overlay/test_acceptance.py:14-29`).
Collection imports the module before any selection applies, so a phase-1
workspace — which has no `models.py` — fails at import for every
selector. The 4/6/3 split is not achievable from this file as it stands.

What survives: the assertions. What does not: whole-file byte identity as
a design constraint. Phase-1 checks must become independently collectable
— a separate module carrying the phase-1 assertions verbatim, importing
only `app` — and provenance is then claimed per assertion (digest of each
check body against the swiftstar source) rather than per file. Byte
identity proves the artifact; it does not prove the fit.

**2. The hidden oracle's location collides with the writable scope.** §1
places the overlay at `tests/test_acceptance.py` while `tests/` is a
declared source path. `load_overlay` refuses exactly that overlap
(`src/satyrn_evals/overlay.py:80`), so the task cannot load. The hidden
tests move to a grader-only namespace (`grader_tests/`); the overlap
guard stays.

**3. Patch witnesses cannot calibrate a model budget.** §2 and §5 send
Phase 3's turn ceiling and every tool ceiling to a "calibration pass over
the known-good and prompt-faithful witnesses." A witness is a patch: it
carries the resulting code, not the investigation, tool calls or mistakes
that would produce it. Applying a patch measures the script that applies
it. The calibration step is withdrawn. The first run reports **raw counts
and elapsed time**; any later threshold is declared as an operational
allowance and labelled a judgment, never presented as a measurement.

**4. §5's "six tasks block the run" overstates what the path requires.**
The session scope check uses `within_source` (`session.py:218`), where a
bare `templates` entry already admits its descendants. Declared directory
source paths matter only to the **Engine contract** — and no Engine
session arm exists (`docs/current/agentclinic-phase-session-proposal.md:118-121`).
The first slice is explicitly **one Baseline session**, and the
directory-declaration work is deferred with it.

**5. The qualification gates verify existence, not qualification.** The
tests assert that fixture files are on disk; the advertised
"passes and scans clean" command only prints `scan_patch`. Qualification
needs an integration gate that applies the checkpoint witnesses and
verifies cumulative correctness, a *named* persistent failure in the
broken witness, an earlier behaviour genuinely regressing at a later
checkpoint, and a positive contamination witness alongside the clean one.

### Consequences for §2 and §4

The budget verdict subsystem is **deferred, not merely reordered**. Two
defects made it unsafe as specified — `outcome_cell` buckets every
non-`pass` string, `unavailable` included, as a failure; and
`turn_count`/`tool_count` load with a default of `0`
(`src/satyrn_evals/session_record.py:190-192`), so a record missing counts
would produce a `within` verdict out of absent data. Cost stays co-equal
with correctness **in the report**, which needs no verdict subsystem to
achieve.

The two deferred detectors are renamed to what their evidence supports.
Identical successive patches mean *no net change*, which is a candidate
finding to inspect, not established phase leakage; leakage is established
by checking whether a later phase's requirements were already satisfied.
Tool names cannot establish "no edit" — `bash` writes files and a refused
`edit` does not — nor does an edit-free stretch establish misdiagnosis.
Both become candidate-finding observations followed by trace inspection.

### What §1-§5 keep

Progressive per-step prompt revelation and the Correction 7 guard; the
prompts as quoted roadmap sections with the two tightenings; the
prompt-faithful fairness gate; solver-owned tests; per-checkpoint
evidence; the empty `base_preservation_selectors` correction and its
skipped grading call with the verdict left unset.
