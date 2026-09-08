# Roadmap

## Proposed next work: one AgentClinic addition

**Status 2026-09-08:** stage 1 is confirmed landed and stage 2 is complete —
`agentclinic-repair-misleading-locus` is qualified at `R3`, offline. Stages 3
and 4 are authorized and have not yet run.

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
three derived from real public and hidden suite runs. That qualification is
**offline only**: its live route is not yet verified and it carries no
comparison evidence. Why it was selected, and what it adds that `depth-3` does
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
