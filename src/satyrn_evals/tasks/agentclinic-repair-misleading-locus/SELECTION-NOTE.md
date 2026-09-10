# Why this condition is in the suite

`agentclinic-repair-misleading-locus` at `R3`, selected 2026-09-08 as the one
additional task-condition proposed by the AgentClinic suite brief. The accepted
condition it is added beside is `agentclinic-repair-depth-3` at `R3`.

## The behavior it exercises

The board renders the module-level `complaints` list, and the POST handler
appends to a *copy* of it (`base/app.py`, `add_complaint`). A posted complaint
is therefore built correctly, redirected correctly, and then lost. The repair
is to make the handler write to the store the board actually reads.

This is a **state-persistence repair, implemented and then verified**, carried
out without disturbing the surrounding behavior. Its practical value is that it
is the ordinary shape of a real defect: the data path is right at both ends and
wrong in the middle, and a fix is only credible once the writer and the reader
have been shown to be the same object.

**What it does not test, stated so it is not later claimed:** at `R3` it does
not test *discovering* the misleading locus. The `R3` contract names the copy
defect and names `app.py`. The symptom-versus-defect distance is a property of
the task, and it is disclosed at this rung.

## What it adds beyond the accepted condition

`depth-3`/`R3` is three seams, each a one-line substitution — an attribute on
the `html` element, a default-factory expression, a `status_code` argument.
This condition adds three things it does not have:

1. **A control-flow repair rather than a substitution.** Two lines become one,
   and the correct edit is not a token swap at a named site.
2. **A graded seam the public suite can observe, on both arms.**
   `tests/test_app.py::test_posted_complaint_appears_on_the_board` is red at
   base and green on the known-good patch, so a solver can confirm its own
   repair before finishing. Two of `depth-3`'s three seams have no public test
   at all — its own `qualification.json` records `public_tests: []` for
   `html-language` and `timezone-aware-timestamp`.

   **The two arms reach that seam by different means, and the asymmetry is
   recorded rather than assumed away.** Baseline's surface includes a general
   `bash` (`arms/baseline.json`). Engine's surface is `read,edit`
   (`arms/engine.json`) plus a tool the engine registers itself, named `bash`
   but restricted to the contract's declared `test_command` — every other
   command is refused (`satyrn-engine packages/engine/runner.ts:221-228`, and
   the rendered R3 engine contract for this task carries a `test_command`
   field). That is not a theoretical capability: **12 of 12** retained Engine
   cells on this task in `~/satyrn-smokes/2026-09-07-v14b-133236` show a `bash`
   call in their transcript. Recompute:

   ```
   for d in ~/satyrn-smokes/2026-09-07-v14b-133236/\
   agentclinic-repair-misleading-locus/cell-*-engine; do
     grep -l '"bash"' $d/*/transcript.txt; done | wc -l
   ```
3. **A preservation-violating negative witness.** `depth-3`'s negatives are
   partial repairs; this one is a *wrong* repair that changes the visible
   symptom and breaks a behavior the task requires preserved.

## Selection reasoning, and what did not enter it

Selection is by repair behavior and observability. **Historical outcomes did
not qualify or disqualify any candidate.** This condition's task appears in
earlier batches with counts that favour Engine — Baseline 3/6 against Engine
5/6 in `archive/2026-09-07-pre-reset/docs/superpowers/specs/`
`2026-09-06-v13b-post-pin-bands.md:59-60` — and that is not why it is here.
Avoiding it for the same reason would have been the same outcome-driven error
in the other direction.

`depth-2` and `plausible-wrong-fix` were not selected: their seams are subsets
of `depth-3`'s, so they add no coverage. `framing-2` was not selected because
its repair requires creating a file, which the Engine arm's `read,edit` surface
cannot do.

`framing-2-edit` is a genuine candidate and is **not** disqualified. Its public
suite is green at base, but its contract says so plainly and names the missing
`models.complaints` compatibility requirement — that is a stated condition, not
a suite that misleads a solver into reading green as complete success. It was
not selected because this condition's observable POST → state → board path is
the more useful addition, not because green-at-base is invalid. It remains
available if the suite is extended again.

## Qualification evidence

One filing is a judgement call, recorded because it is the check the
`known-broken` witness turns on: `test_complaints_board_still_renders_seed_`
`complaint_details` sits under `preserve-page-board-and-redirect-behavior`
because it is a property of what the board renders, though its first assertion
compares a card count to the seed population and could be read as belonging to
`preserve-complaint-data-contract`.

`qualification.json` records three behaviors covering all 13 hidden checks, and
three witnesses whose rows were **derived by running the real public and hidden
suites**, not predicted:

| witness | public failing | hidden failing |
|---|---|---|
| `base` | `test_posted_complaint_appears_on_the_board` | `test_posted_complaint_appears_on_complaints_board` |
| `known-good` | none | none |
| `known-broken` | `test_posted_complaint_appears_on_the_board` | `test_complaints_board_still_renders_seed_complaint_details`, `test_posted_complaint_appears_on_complaints_board` |

The `known-broken` patch changes `templates/complaints.html` to iterate
`complaints[1:]` — a repair aimed at the symptom's location, which makes the
board look different without recording anything. The record names the **exact**
preservation check it breaks, because an overall failure would be no evidence:
the seam it leaves unrepaired fails regardless. It drops the first seed, so
`test_complaints_board_still_renders_seed_complaint_details` fails on its card
count — `assert len(cards) >= len(SEED_COMPLAINTS)` evaluates `3 >= 4` and
raises, so the per-seed loop below it never runs — while
`test_complaints_board_still_lists_seed_complaint`, which looks only for the
third seed's text (`"Scope creep never ends."`, `base/models.py:21-24`), stays
green.

**The control that makes this discriminating is `base`, not `known-good`.**
`base` and `known-broken` differ by exactly this witness's patch — the board
template and nothing else — and the details check is silent at `base`. So it
tracks the wrong repair rather than the unrepaired seam. `known-good` differs
from `known-broken` in two ways at once (the handler repaired *and* the
template unsliced), so it cannot isolate the template edit on its own; it is
recorded as the all-clear end of the range.

Recompute:

```
uv run pytest -q -m integration tests/integration/test_agentclinic_gate.py \
  -k "qualification or record_maps or record_names"
```

The structural half of the record — behaviors covering the whole oracle, and
both witness directions present — is checked in the default tier by
`tests/test_agentclinic_manifests.py`, since the gate above is an integration
row that `just gates` does not execute. Neither tier runs in GitHub CI: the
repository's only workflow, `.github/workflows/pages.yml`, builds the docs and
nothing else. `just gates` is where both fire.

## Risks recorded for the live stages

**Lock-ups on this task are a recorded pathology, and their direction is not
the one an Engine-favourable reading would assume.**
`archive/2026-09-07-pre-reset/docs/superpowers/specs/`
`2026-09-06-v16-diagnostic-suite-admission-design.md:160-162` records that on
`misleading-locus`, Baseline lock cells ran `pytest` as their *second* call and
locked anyway, Baseline locking 5/12 against Engine's 0/12 — and that the
lock's cause is untested. This is recorded as a **feasibility and
interpretation** fact for stage 4, which the brief permits, not as a selection
input, which it does not. It means a four-attempt screen on this condition can
easily produce a lock in either arm, and that a lock is not evidence about
either arm's design.

**One witness the record does not have.** No fixture demonstrates a repair that
*succeeds* at the seam while violating preservation — `known-broken` leaves the
seam unrepaired as well as breaking the board, so the two effects arrive
together. The isolating `base` contrast above shows the preservation check
tracks the template edit alone, so the property is established by composition
rather than by a single row. A fourth fixture repairing `app.py` and slicing
the template would turn that inference into a witness; it is not built, and its
absence is stated here rather than left to be discovered.

## Scope

Qualifying this condition authorizes no live spending. The live route
verification and the matched four-attempt screen are separate stages of
[the suite brief](../../../../docs/current/agentclinic-suite-brief.md), each
needing its own budget authorization.
