# Brief for the next agent — correct the screen's claims, then put Engine on the phased workload

Written 2026-09-09 at `b78fa13`. Read `CLAUDE.md`, `BRIEF.md` and
`ROADMAP.md` first, as every session must. This brief does not replace them.

## Where things stand

The phased AgentClinic session workload exists, is qualified, and has run.

- Task `src/satyrn_evals/tasks/agentclinic-session-phased/`: an empty
  skeleton carried through three ordered development requests, graded
  cumulatively against 13 hidden checks split 4/6/3. The depth-3 acceptance
  assertions are extracted into three independently collectable modules
  under `grader/overlay/grader_tests/`, verbatim, enforced by an AST
  comparison — the unchanged source module imports `models` at load, and
  collection precedes selection, so it cannot grade a phase-1 workspace.
- Two prompt conditions differ by exactly one sentence: `session.json`
  (verification) and `session-control.json` (control). A test pins the
  character-exact equivalence and is proven to fail when one condition is
  weakened alone.
- `--session-spec` selects between them. Its guard is **lexical**: it
  refuses separators, `..`, absolute paths and non-`.json` names, and does
  **not** establish containment — a bare filename that is a symlink out of
  the task still resolves. That limit is stated in the docstring; do not
  restate it as containment.

Three runs are retained, all under `~/satyrn-smokes/`:

| Run | What it was |
|---|---|
| `2026-09-09-session-phased-112550` | Discovery, n=1, no verification instruction. Found a genuine cross-phase regression. |
| `2026-09-09-session-phased-verify-114708` | n=1 with the instruction. Exposed two environment defects, since fixed. |
| `2026-09-09-verify-triage-132612` | The four-session matched screen: 2 control, 2 verification. |

## Part 1 — corrections to make first. No new run is required for any of them.

These correct overclaims in records that are otherwise sound. A correction is
recorded, not edited away.

**C1. The control refutes necessity, not causation.** Session 04 shows
verification can occur without the instruction. It does **not** show the
instruction cannot raise its likelihood, and two instructed sessions do not
establish that the instruction "made verification consistent". The
defensible statement is: *both instructed sessions verified after their final
edits; one control did and one did not.* Phases are **nested within
sessions**, so "6 of 6 phases" is not six independent trials and must not be
counted as though it were. Fix in both
`~/satyrn-smokes/2026-09-09-verify-triage-132612/RESULT.md` (the Q1 section)
and `docs/development/lessons.md` (the "The control produced the behaviour we
were about to attribute to the instruction" entry).

**C2. One factual error in the recovery trace.** The sequence after the
failing run was **failed edit → read → failed edit → rewrite**, not two
failed edits followed by a read. The finding itself holds: failing tests,
application-only repair, passing tests, test file untouched throughout
recovery — a concrete example of the desired behaviour, and not evidence the
instruction caused it. Correct the order in `RESULT.md`.

**C3. Cost is observed, not causally explained.** The turn totals reproduce,
but "cost tracks verifying, not being instructed" cannot be separated here
from trajectory differences, command-discovery effort, and the repair work in
session 02. Say what was observed and stop. In the same section, call the
outcome an **all-pass sample**, not an established correctness ceiling.

**C4. Keep the cheap-screen lesson; drop the statistical folklore.** The
standing lesson currently implies that reaching for a power calculation was
itself the tell. That is wrong: a larger controlled study would not
inherently make the attribution mistake, and power calculations are not the
problem. The lesson is **choosing an expensive experiment before knowing
which decision it serves**. Rewrite the "The experiment grew until it
answered a question nobody had asked" entry accordingly.

**C5. `ROADMAP.md` is stale.** Around line 75 it still reads "Tasks 1-2
landed, Task 3 pending authorization" and "Task 3 ... has not started". Task
3 ran, twice, plus the four-session screen. `CLAUDE.md`'s one-current-status
rule requires the opening paragraph and the phase table to agree — update
both in the same edit or neither.

**C6. Close the prompt experiment.** Adopt the verification sentence as a
practical operating policy: it states a desirable behaviour and supplies a
command that works. Record the adoption explicitly as **a judgment, not a
demonstrated correctness or reliability improvement**. No confirmation
campaign. Fold C1-C6 into one small documentation change.

## Part 2 — the direction: make Engine usable on this workload

This is the main gap and the next substantial work. The frozen screen says
so plainly (`docs/current/agentclinic-verification-triage-screen.md`, the
Conditions section): **no Engine session arm exists**, so nothing produced so
far speaks to Engine versus Baseline in either direction, and no report may
imply otherwise.

**This is an Engine capability decision, not adapter plumbing.** The recorded
obstacle (`docs/current/agentclinic-phase-session-proposal.md:118-121`) is
that the mutator and runner assume one frozen contract carrying a
`test_command`, and a session has no per-prompt equivalent. Scope the work to
four properties and no more:

1. sequential requests against one checkout that persists between them;
2. legitimate **file creation**, since the workload starts from an empty
   skeleton — not only anchored replacement in existing files;
3. explicit tool and contract behaviour per request, stated rather than
   inferred;
4. retained evidence per checkpoint, on the same terms as Baseline.

**Do not build a general session platform.** Three concrete implementations
must need the same shape before a framework is justified, and there are not
three.

Note that `writable_paths` currently infers directory-ness by probing
`base/`, which cannot distinguish an empty-skeleton directory from a file
creation target; the deferred entry in
`docs/superpowers/plans/2026-09-09-agentclinic-phased-session.md` describes
the trailing-slash declaration and reopens exactly when an Engine session arm
exists. That is now.

## Part 3 — prove the route cheaply

**Offline lifecycle checks first**, then **one bounded Engine session**. Use
the adopted verification instruction for **both** Engine and Baseline, so the
arms differ in engine, not in prompt.

That run establishes **operability, not superiority**. Write its pre-run
record before it, freeze `n`, and say in the record what it cannot show.

## Part 4 — then one named Engine behaviour

Use this existing workload and the retained traces to identify **one**
concrete obstruction and a proposed remedy. Compare matched configurations
with the required behaviour and the cost declared **separately**. Start with
triage — two attempts per configuration, per `BRIEF.md`'s development
feedback policy — and require a development reason before any confirmation
run.

**Do not build a "recovery under pressure" task yet.** Retain the existing
recovery trace (`2026-09-09-verify-triage-132612`, session 02, phase 3). If a
specific Engine remedy later needs a controlled failing state, reuse that
session's broken checkpoint as an explicitly separate diagnostic condition
rather than authoring a new task.

## Guardrails that were paid for today

Each of these cost a correction in this session. They are in
`docs/development/lessons.md` in full.

- **A test that cannot fail.** Four were written today; three were caught by
  review, one by an implementer's own negative control. Before trusting a new
  test, break the thing it guards and watch it fail. A pass is not evidence.
- **Verify the proposition you actually need.** A precondition "the
  environment is installed" was checked by installing it, which is a
  different claim; the workspace does not arrive installed.
- **A wrapper's exit code is not the wrapped command's.** An RTK-filtered
  `uv run ... pytest` reported non-zero on a passing tree. Verify any command
  you put in a prompt unfiltered.
- **Byte identity proves provenance, not fitness.** The acceptance suite was
  identical to its source and still could not grade phase 1.
- **Run the full gates, not one of them.** `just gates`, exit code read
  directly, never piped.
- **Use a separate worktree** for anything that checks out another commit.

## What is deliberately not queued

- Any confirmation campaign on the verification instruction.
- A budget-verdict subsystem, and any pass/fail cost threshold. Cost is
  reported raw. The drafted classifier bucketed `unavailable` as failure and
  would have produced a `within` verdict from counts defaulting to zero.
- The phase-leak and no-edit-run detectors, which were named beyond their
  evidence and specified against the wrong event shape (`tool_end` carries
  `payload.toolName`; the plan's entry has the correction).
- A second task directory for any purpose. Duplicating the overlay and
  fixtures caused two drift corrections today; `--session-spec` exists so it
  is not needed.

## One open instrument question, unresolved

A solver application that cannot import grades **`unavailable`**, not
`fail`: the grader requires executed ids to match expected, a collection
error executes zero, and the mismatch reads as *we could not measure* when
the truth is *the model shipped code that does not import*. The narrow fix
must preserve both facts — the candidate could not load, and the expected
checks did not execute — must not invent failed assertions, must keep the
original receipt unchanged, and must not turn every collection error or every
traceback containing application code into a failure verdict, since missing
dependencies and broken grader imports produce similar symptoms and are
genuinely infrastructure. `src/satyrn_evals/verdict.py:114`'s exact-execution
requirement stays. It is re-scorable offline from retained receipts, so it
does not block a run.
