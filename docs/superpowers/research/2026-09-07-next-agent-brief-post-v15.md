# Brief for the next agent — after V15 was refuted

**Read first:** `BRIEF.md`, `ROADMAP.md`, `CLAUDE.md`,
`docs/superpowers/research/2026-08-16-harvest-index.md`, and
[the V15 premise correction](2026-09-07-v15-premise-correction.md). Then
this. Every number below carries the command that recomputes it.

## Why you exist

V15 — "a second application with graded tasks that express coordination" —
was proposed on 2026-09-07 and **refuted the same day, before a single cell
was spent.** Its premise was that the suite is five single-anchor repairs
with nothing to coordinate. The fixtures say otherwise, and so does a
re-score of 96 cells that already existed.

What replaced the premise is better than the premise was. On `depth-3`,
both arms stop with two of three seams unfixed — **because the only test
suite they can run cannot see those seams.** They finish on `4 passed`, and
one Engine cell says so in its own words:

> "`test_complaint_model_contract_is_preserved`: Verified by running the
> test suite. The `Complaint` model in `models.py` remains intact. […] All
> tests passed successfully."

That is not a coordination failure. It is an agent stopping correctly
against an instrument that cannot see the target.

**Your job: find out whether seam visibility is the mechanism.** If it is,
it reframes a task the project has called a quality floor since V11c, and
it points at an engine change (what an agent verifies against) rather than
a content change (build a bigger app).

## What is established, and what is not

**Established, verified at source this session.**

- `depth-2` ⊂ `depth-3`: their `app.py` and `templates/base.html` hunks are
  byte-identical, and `depth-3`'s `known-broken.patch` equals `depth-2`'s
  `known-good.patch`. A 1/2/3-seam nested ladder already ships.
- `plausible-wrong-fix` **is** the missing rung-1: `diff -r` over its
  `base/` and `depth-3`'s differs only in the two un-seeded defects and the
  package name.
- `depth-3`'s public suite has four tests and **none** matches
  `lang|tzinfo|timezone`. Two of its three graded seams are unobservable
  from inside the workspace.
- In V14b, **0 of 23** retained patches touch `models.py`, in both arms,
  while **24 of 24** transcripts mention it and the R1 contract names its
  failing check.
- `seams_closed` re-score (`scripts/rescore_seams.py`): degenerate at 1
  seam (reads 1.000 for an arm that passed 4/12), identical to the verdict
  at 2 seams, and **0.515 vs 0.500** at 3.

**Not established. Do not write these down as findings.**

- **That visibility causes the stop.** It is a hypothesis fitted to four
  tasks with everything confounded. It is the reason this brief exists, not
  a result.
- **That `depth-3` is easy.** The withdrawn label was "quality floor". The
  replacement is "we do not know", not "trivial".
- **Anything about coordination.** No task has ever isolated it, V15 did
  not build one, and the retained data cannot answer it.

## Traps, from eight wrong calls in three days

The first six are recorded in the V15 brief this one supersedes. Two are
new, both made on 2026-09-07 by the agent that wrote this file:

7. **"More seams means more to read, so Engine's read-lock resistance pays
   off more."** Refuted by the very batch cited for it: `read_lock` is
   Baseline 8 / Engine 1 on the one-file task and **0/0** on both
   multi-file tasks. A finding from one task, stated generally.
8. **Proposing to author `depth-1`.** It already ships as
   `plausible-wrong-fix`. Nobody had run `diff -r` over the two `base/`
   trees.

Every one of the eight has the same shape: **a real number with an untested
causal story attached.** Both new ones were caught by an adversary told to
attack and given the evidence directly — not by the context that formed the
belief. Budget for that reviewer; it has now caught more than any
implementation step.

A third near-miss worth recording: `seams_closed` was proposed as a power
gain and is worthless on two of three rungs. It cost nothing because it was
computed over retained cells **before** anything was authored. That is the
discipline `BRIEF.md` rule 3 was built to buy — use it.

## Rules that bind you

Everything in `CLAUDE.md` still binds. The ones this cycle nearly broke:

- **Cross-batch counts are not comparable.** Demonstrated again here:
  Baseline touched all three `depth-3` seams in 2/12 cells in V13c and
  0/11 in V14b, same task, same rung, identical arm configuration.
- **Read the gate's exit code, unpiped.** `just gates | tail` swallowed a
  gate's status this session. The `lint-docs` cap gate also refused an
  over-long phase row — let it.
- **A detector must discriminate in both directions.** `scripts/rescore_seams.py`'s
  seam-map validator reported no violations over 96 cells; that is only
  evidence because it was shown to fire on a hand-built known-bad.
- **`n=12` is the working size, `n=6` cannot carry a band**, and outcome
  differences of the size seen here need ~100/arm. Prefer within-batch
  contrasts and the cost axis.
- **Never edit the tree while a batch runs.** Use a worktree.

## What not to build

- **No second application.** V15's case for one is refuted; the V16 §6
  stopping rule that would call for one has not fired.
- **Do not author `depth-1`.** It exists.
- **No new instrument.** The census exists and its limits are recorded.
  `scripts/rescore_seams.py` is a one-off with no test and is a W1 deletion
  candidate.
- **No admission machinery** until a task needs it.

Weight, recomputed 2026-09-07: `src` (excluding vendored tasks) **9,660**,
`scripts`+`arms` **2,096**, `tests` **22,953** — all grown since
`ROADMAP.md` recorded them, and W1 has still never run.

## First moves

1. **Spend nothing first.** Before proposing a batch, grep the retained
   transcripts for cells that justify stopping by citing the test suite.
   If failing cells routinely say "all tests pass", the hypothesis
   strengthens for free; if they do not, it weakens and the batch is not
   worth running.
2. **Then the one experiment worth cells.** Author
   `agentclinic-repair-depth-3-visible`: identical to `depth-3` in base
   defects, overlay, `expected_test_ids` and every contract rung, differing
   **only** in that its `base/tests/test_app.py` covers the `lang` and
   `tzinfo` seams. Run `depth-3` and `depth-3-visible` in **one interleaved
   batch**, both arms, `n=12` — 48 cells, roughly an hour.
   - **Freeze this before the batch:** if visibility is the mechanism,
     `depth-3-visible` moves off 0/12 in **both** arms. If it stays at
     0/12, visibility is not the mechanism and `depth-3` is genuinely hard.
     Both outcomes are publishable; the null is the more interesting one.
   - **State the caveat in the protocol, not after:** the variant also
     changes how much text is in the workspace. The R1 contract is held
     identical, so *information* is held and only *verifiability* moves,
     but the workspace is not byte-identical and the write-up must say so.
3. **Post the design proposal and wait** (`CLAUDE.md`). This is a new
   phase; that instruction is self-contained and applies even to a
   subagent.

## The Opus / Sonnet / Fable split

The V15 brief's finding held again, more sharply: **roughly two-thirds of
the hours were delegatable and none of the errors were.** Both new wrong
calls were reasoning about evidence. Both catches were adversarial review.
Zero implementation defects occurred, because no implementation happened.

| work | who | why |
|---|---|---|
| Read the evidence, choose the measure, freeze the criterion | **Opus** | All eight recorded errors live here |
| Write the spec with acceptance stated up front | **Opus** | Sonnet's output quality tracks spec precision almost exactly |
| Author `depth-3-visible` | **Sonnet** | Bounded and mechanical — see the spec sketch below |
| Fix the census cross-arm columns (§4 of the correction) | **Sonnet**, shape decided by **Opus** | The code is small; *what the columns should mean* is a measurement call |
| Review the diff | **Opus** | Cheap, and verify at source rather than accepting a report |
| Attack the protocol **before** cells are spent | **Fable** | It killed two plans this session at a fraction of a batch's cost |
| Attack the reading **after** the result | **Fable** | Must not be the context that formed the belief |
| Run the batch | **maintainer** | Budgeted inference, frozen checkout, quiet machine |

**The Sonnet spec sketch, stated now so its boundedness is visible.** Copy
`agentclinic-repair-depth-3` to `agentclinic-repair-depth-3-visible`;
change **only** `base/tests/test_app.py` (add one test asserting
`<html lang="en">` and one asserting `Complaint().timestamp.tzinfo is not
None`), plus the package name in `base/pyproject.toml` and `base/uv.lock`.
Every other file must be byte-identical to `depth-3`'s.

Acceptance, given to Sonnet up front:

- `diff -r` between the two task directories reports **only** the four
  expected files.
- `just gates` exits 0, read unpiped.
- `tests/test_agentclinic_manifests.py` and `tests/test_rung_ladder.py`
  pass for the new task.
- The new public tests are **red** against the new task's own `base/` and
  **green** after its `known-good.patch` applies — a refusal test and its
  sibling success test (`BRIEF.md` rule 6).
- V5d smoke before any budgeted batch.
- *If the spec is wrong, stop and report rather than improvise.*

**Two rules that made delegation work, unchanged.** Give Sonnet the
acceptance criteria before it writes anything, and it will tell you the
spec is wrong instead of improvising. And never let a subagent's report
substitute for your own verification — every load-bearing claim in the
correction document was re-derived by hand before it was written down, and
one review claim that could not be checked locally is recorded as
unverified rather than repeated.

**The role you cannot collapse is the adversary.** Told to attack, handed
the evidence, and kept out of the context that formed the belief, it found
in two passes: that the ladder already existed, that the pathology was
symmetric, that the proposed new task already shipped, and — while trying
to break a claim that in fact held — the seam-visibility mechanism that is
now the whole of the next phase. Not one of those came from reading a
record. All of them came from opening a file.

## Open items this cycle did not close

- **`BACKLOG.md` owes V15 a reopen condition.** Its old trigger is gone and
  no new one was written. The V16 spec §7 already flagged that the
  selection rules owe one too.
- **The census cross-arm defect** (correction §4) is unfixed. Re-scorable,
  so it blocks nothing.
- **`scripts/rescore_seams.py` has no committed test.** It owes one or it
  should be deleted.
- **Nothing is committed.** `ROADMAP.md` is modified; the correction and
  the script are untracked. Commits are maintainer-controlled.
