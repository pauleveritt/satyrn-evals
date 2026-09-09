# Roadmap

## Proposed next work: one AgentClinic addition

**Status 2026-09-08.** The suite sequence completed at `R3` (four cells,
Baseline 2/2 and Engine 2/2, no outcome difference detected;
`~/satyrn-smokes/2026-09-08-misleading-locus-r3-174721/RESULT.md`). A fresh
**R1 comparison then ran to its declared design** — 36 cells per arm, tally
accepted 72/72, model identity verified in all 72 transcripts:

- **Primary: Baseline 33/36, Engine 36/36, one-sided Fisher p = 0.1197**
  against a predeclared `alpha = 0.05`. The criterion is **not met**: the
  earlier large outcome advantage did not replicate at the specified
  threshold. Given Baseline's realized 33/36, the best possible Engine result
  would also have been p = 0.1197.
- **Secondary, declared in advance: Engine reached the same outcomes for
  less.** On successful cells, medians of 10 turns / 9 tool calls / 11,222
  input / 500 output against Baseline's 13 / 12 / 15,934 / 674. Descriptive;
  monetary cost is unmeasured on a local provider.
- Every Baseline non-success in the batch is `REPEAT_LIMIT`.

Counts, recompute and the decision:
`~/satyrn-smokes/2026-09-08-misleading-locus-r1-201314/RESULT.md`.

**Sessions: started, and blocked on one prerequisite.** The instrument measures
one request per cell against a fresh workspace, so it cannot exercise a
*sequence of new user requests* — where a later request regresses earlier work,
or acts on state formed several requests ago. That gap is independent of the R1
outcome. Three things landed against it on 2026-09-08:

- Base preservation is now graded at **every** checkpoint, not only the last,
  so a regression is visible at the checkpoint that caused it.
- `session-ordering-regression` is a task built around a real cross-prompt
  dependency, with three checkpoint patches witnessing pass → break → restore
  on both the feature and preservation axes, verified through the real grader.
- One bounded Baseline session ran
  (`~/satyrn-smokes/2026-09-08-session-ordering-baseline-220737/RESULT.md`).
  All three prompts settled on one conversation; the route and the
  per-checkpoint grading both work.

That first run found a prerequisite that blocked any session intended to count:
the adapter passed no `--tools`, so the model reached an installed extension and
dispatched a **detached subagent** that wrote two files across two checkpoint
boundaries with **no retained events**. **Both repairs have since landed** — an
effective tool boundary (allowlist plus `--no-extensions`, since the worker came
from an extension) and a writable-scope statement in every prompt — and a
**second session verified them**
(`~/satyrn-smokes/2026-09-08-session-ordering-baseline2-230325/RESULT.md`):
`COMPLETE`, no tool outside the allowlist, no detached dispatch, zero scope
violations, and three real per-checkpoint preservation verdicts.

A second run then exposed a fairness defect — the hidden checks demanded the
ellipsis character and punctuation handling that the prompt never stated, so no
solver could finish step 1. The task had been authored as a **grader fixture**
and run as a **workload** without qualification, which `BRIEF.md`'s two
selection rules forbid. **It is now qualified**: the prompts state what the
checks require, `QUALIFICATION-NOTE.md` maps every hidden check to the
accessible text, and `fixtures/prompt-faithful.patch` plus a fairness gate hold
it there — an implementation written only from the prompts must pass, verified
by mutation.

**A third session then ran clean**
(`~/satyrn-smokes/2026-09-08-session-ordering-baseline3-231223/RESULT.md`):
`COMPLETE`, surface held, zero scope violations, and **every checkpoint passing
both axes** — the first time any session reached step 1's feature.

**The cross-prompt regression still did not occur, and now we know why.** The
solver satisfied step 2 with `name.split()` rather than by refactoring
`normalize` into a shared helper, so nothing could break. The task **offers**
the hazard; it does not force it. At `n=1` that is an observation, not a rate.
Making it reliable would mean forcing contact with the shared code, which
trades away the accident the task is modelling — a design choice belonging in
its own proposal. **No session runs are queued.**

**The phased AgentClinic session task: Tasks 1-2 landed, Task 3 pending
authorization.** [The plan](docs/superpowers/plans/2026-09-09-agentclinic-phased-session.md)
adds a second, independent session workload: one growing checkout carried
through three ordered development requests (home page, then the complaints
board, then adding a complaint), with the depth-3 acceptance assertions
extracted into three independently collectable modules so each phase grades
on its own. Task 1 (sampling `elapsed_seconds` live instead of deriving it,
and allowing an app-less `base/` so a session task can ship no application)
and Task 2 (the `agentclinic-session-phased` task itself, its per-phase
graders, and its witnesses — `known-good`, `known-broken`,
`regression`, `contaminated`, and `prompt-faithful`, all qualified through
the real grader) are both committed. Task 3 — the one bounded Baseline
session this exists to run — has not started and needs its own live-run
authorization, per this file's other live stages.

[The suite brief](docs/current/agentclinic-suite-brief.md) proposes finishing
the existing engine repairs, qualifying one additional useful task-condition,
verifying its live route, and then running a matched four-attempt Engine and
Baseline screen — two interleaved attempts per arm — before deciding what the
evidence warrants. Selection is driven by distinct repair behavior, not a
favorable historical score and not by which task separates the arms. The screen
is a planned stage rather than an afterthought, and four attempts observe
without establishing superiority. This is bounded suite development, not a
restart of the paused comparison or a pathology audit. The brief authorizes no
implementation, merge, commit, or inference; each live stage needs its own
budget authorization.

## Paused: the engine comparison

**The comparison is paused. Do not restart it.** Stages 1 and 2 are complete —
the live route works and its evidence regrades — and stage 3 was stopped after
naming a candidate, because the candidate was chosen for being measurable in
retained traces rather than for addressing a problem that matters in use. That
is too weak a reason to spend.

No evaluation is queued, and none should be manufactured. The next one is
pulled by a real development need: a concrete engine problem whose relevance is
established first, then evaluated with the cheapest existing condition. A
negative result closes a question rather than prompting a search for another
lever.

The ordered work, if a need reopens it, is in
[the first engine comparison plan](docs/current/first-engine-comparison-plan.md),
and the candidate record in `docs/current/triage-candidate.md` says what was
closed and why. Each live stage would carry its own frozen, explicitly
authorized budget. This roadmap authorizes no spending and no model inference.

What the pause produced instead: two engine defects found by inspecting
model-facing messages and fixed without any model run — a post-edit region that
could report truncation while showing none of the change, and a loop breaker
that refused to let a model inspect or test a file it had just edited.

## Accepted baseline

The offline milestone is accepted. `agentclinic-repair-depth-3` is qualified at
`R3`, with base, known-good, and declared-incomplete witnesses.
`agentclinic-repair-misleading-locus` is qualified at `R3` as of 2026-09-08,
with base, known-good, and a preservation-violating known-broken witness, all
three derived from real public and hidden suite runs. Its live route is
verified, and a matched four-cell screen ran at that rung: **Baseline 2/2,
Engine 2/2**. The screen **detected no outcome difference** and cannot
support a general comparison conclusion. Four observations also say nothing
about whether `R3` is a ceiling; retained as a regression and route condition,
and its discriminating power at that rung is simply unmeasured. Why it was selected, and what it adds that `depth-3` does
not, is in the task's own `SELECTION-NOTE.md`. Its synthetic
route proves the edit, test, artifact, and grade flow and re-scores retained
artifacts offline. The whole-attempt deadline then bounded setup, command,
preservation, grading, and cleanup without discarding evidence. Their
[design](docs/current/first-milestone-design.md),
[plan](docs/current/first-milestone-plan.md),
[deadline design](docs/current/whole-attempt-deadline-design.md), and
[deadline plan](docs/current/whole-attempt-deadline-plan.md) remain the
contracts the next sequence preserves rather than reopens.

The first-milestone fixture launcher has a synthetic identity. Its output is
not live evidence and is never relabelled as such.

## State and dependencies

The evaluation core captures attempts, preserves evidence, grades from hook
results, and re-scores retained patches without a new model run. It records no
per-attempt duration on a normal completion and no token usage of its own;
timing needs external measurement and usage survives only inside a retained
transcript.

What the comparison needs from outside this repository is a concrete
engine/model combination, a reachable model server, and an authorized budget
for each live stage. The engine is an external dependency: a recommendation
from this work does not authorize editing or merging it.

Evaluating a different engine checkout needs only its own arm file, a synced
virtual environment on `PATH`, and preflight's `--engine-repo`; that checkout
must be committed and clean, because preflight verifies its revision against
the arm's pin. Comparing two engine revisions inside one batch needs more:
`ArmName` is a closed vocabulary and the tally groups its counts by that name,
so two engine configurations would pool into one denominator. This need not
mean extending the vocabulary: separate configuration-specific schedules and
output roots, sharing one frozen interleaving order, keep the denominators
apart without new platform work. The triage stage picks an approach before it
freezes a matched pair.

Retained live evidence for `depth-3` is reported by condition rather than
pooled. At `R3`, 6 of 6 baseline attempts pass with `gemma-4-12B`, 6 of 6 pass
with `gemma-4-26b`, and the one engine-arm attempt — the 2026-09-08 smoke —
passes. At `R1`, no baseline attempt passes in any recorded batch, and 1 of 24
engine attempts passes at the pinned engine. At `R0`, no baseline attempt
passes at either model. Refusals are counted separately from fail verdicts, and
the earlier batches ran under limits and an evals revision that differ from the
smoke's condition.

Both arms now pass at `R3`, on 12 baseline attempts and 1 engine attempt.
Whether `R3` can distinguish engine configurations is **not** settled by that:
one engine attempt beside baseline runs under different limits cannot decide
it. The triage stage names the engine change and the behavior it predicts
first, and only then judges whether `R3` exercises that behavior. `depth-2` at
`R1` is an exploratory lead, not on its own a reason to change conditions.

## Completion

The sequence completes when one bounded live route has worked, the selected
engine question has been addressed by the declared confirmation analysis, the
decision is reproducible from retained evidence, and the final review accepts
the conclusion and its stated limits. A negative or inconclusive decision
satisfies it. A blocked smoke or an abandoned triage screen is reported as
partial progress, not completion.

Historical phase labels, probes, and result narratives are archived outside the
active reading path.
