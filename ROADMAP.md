# Roadmap

## Proposed next work: one AgentClinic addition

**Status 2026-09-09. The phased AgentClinic session workload exists, is
qualified, and has run three times; the proposed next work is Phase HP,
orchestrated delivery.** Nothing produced so far speaks to Engine versus
Baseline on a session workload in either direction, and no Engine session arm
exists. The phase and its eight cycles are below; the paragraphs before it
record how each stage got here.

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

**The phased AgentClinic session task: all three tasks landed, and Task 3 has
run.** [The plan](docs/superpowers/plans/2026-09-09-agentclinic-phased-session.md)
adds a second, independent session workload: one growing checkout carried
through three ordered development requests (home page, then the complaints
board, then adding a complaint), with the depth-3 acceptance assertions
extracted into three independently collectable modules so each phase grades
on its own. Task 1 (sampling `elapsed_seconds` live instead of deriving it,
and allowing an app-less `base/` so a session task can ship no application)
and Task 2 (the `agentclinic-session-phased` task itself, its per-phase
graders, and its witnesses — `known-good`, `known-broken`,
`regression`, `contaminated`, and `prompt-faithful`, all qualified through
the real grader) are both committed.

**Task 3 has run, three times, all Baseline and all retained under
`~/satyrn-smokes/`:** a discovery session at `n=1` without the verification
instruction (`2026-09-09-session-phased-112550`), which found a genuine
cross-phase regression; an `n=1` session with it
(`2026-09-09-session-phased-verify-114708`), which exposed two environment
defects, both since fixed; and the **four-session matched triage screen**
(`2026-09-09-verify-triage-132612`), two control and two verification,
recorded in [the frozen screen](docs/current/agentclinic-verification-triage-screen.md).

**The prompt experiment is closed.** The verification sentence is **adopted as
an operating policy** for session prompts: it states a desirable behaviour and
supplies a command that works, where an uninstructed session spent calls
discovering one. That adoption is **a judgment, not a demonstrated correctness
or reliability improvement** — the screen's own control verified unprompted in
one session of two, all four sessions passed every check, and four sessions
separate nothing. **No confirmation campaign is queued**, and the screen's
counts stay outside the denominator of any later experiment.

**The proposed next phase is orchestrated delivery**, not a longer Engine
conversation, and it is an **adaptation of SwiftStar's already-exercised
design** rather than a new one: this same phased roadmap carried through
bounded implementer handoffs, each phase branched from its predecessor's
accepted commit, with every packet, decision, role-attributed mutation and
cost retained ([the proposal](docs/current/orchestrated-delivery-design.md)),
**recorded below as Phase HP** and sequenced into eight feature cycles. It supersedes
Part 2 of [the next-agent brief](docs/current/next-agent-brief-engine-on-phased.md),
which scoped an Engine session arm; that arm survives only as a comparison
condition. Neither document authorizes implementation or inference, and each
live stage needs its own budget authorization.

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

## Phase HP — the handoff packet

**Proposed 2026-09-09, not started, authorizing nothing.** Design:
[orchestrated delivery](docs/current/orchestrated-delivery-design.md), an
adaptation of SwiftStar's exercised implementation rather than a new
orchestration design. **Ownership is settled:** `satyrn-engine` owns packet
execution, chained isolation and candidate production; `satyrn-evals` owns
the packet schema, the arm, capture, grading, attribution and comparison.
Cycles marked *engine* need mirrored entries in that repository's own
roadmap; this table does not govern it.

The one path being built, and the only one: **inspected packet → bounded
implementer → isolated candidate → explicit integration → cumulative
validation.** The packet is built deterministically and reviewed, not authored
by an orchestrator unsupervised — autonomous authoring is measured at 3/8
against 8/8 by hand and is **out of scope for the phase** (the amendment in
the design names the evidence). The workload is the existing
`agentclinic-session-phased` task. No second workload is authored, and no
agent is asked to invent a decomposition.

| Cycle | In scope | Out of scope | Artifacts | Status |
|---|---|---|---|---|
| **HP1** Packet schema | The typed packet mapped from SwiftStar's field set: objective, pinned facts, base revision, writable scope, behaviour to preserve, worker self-test command, redactions, budgets. **No parent validation command** — sourcing one from the task's `oracle` would put the hidden oracle hook in a document the implementer reads | Executing a packet; anything engine-side; fields this path does not need | spec + plan | **implemented, awaiting acceptance** — five slices, 1,559 tests green; two review rounds recorded in the spec's correction blocks |
| **HP2** Offline route | The three phases end to end against a fake implementer on the engine seam, no model | Real inference; isolation (HP3); attribution (HP5) | plan only | proposed |
| **HP3** Chained isolation *(engine)* | Phase N branches from phase N-1's accepted commit; a refused phase stops the chain with no candidate ref | Pools, parallel dispatch, retry | spec + plan | proposed |
| **HP4** File creation | Declared directory source paths, so an empty-skeleton directory is distinguishable from a creation target | A trailing slash as the settled syntax; relaxing scope enforcement | plan only | proposed |
| **HP5** Role attribution | Every mutation attributed to orchestrator or implementer from retained events | Judging whether delegation helped; any new pathology detector | spec + plan | proposed |
| **HP6** Chain retention | Instructions, packets, worker events, candidate, validation output, accept/reject with reason, cost per role, fallback labelled | Cost thresholds or a budget verdict | plan only | proposed |
| **HP7** Live route proof | One orchestrated delivery, `n` frozen at 1, Baseline model, the adopted verification instruction | Superiority of any kind; extending `n` after reading it | spec (pre-run record) | proposed, budgeted |
| **HP8** Workflow comparison | Orchestrated route against the continuous-session route, same roadmap and prompt, triage at two attempts per configuration | Publication; mechanism attribution; wall-clock between contiguous arms | spec (pre-run record) | proposed, separately authorized |

**Why some cycles are plan-only.** `docs/sdd.md` asks for designs
proportionate to the change: work that moves an evaluation condition,
evidence boundary, task contract or interpretation earns a spec, and the rest
does not. HP1, HP3, HP5, HP7 and HP8 each move one of those. HP2, HP4 and HP6
implement decisions those specs already fixed.

**Ordering.** HP1 gates HP2 and HP3. HP4, HP5 and HP6 all gate HP7 — a run
that cannot create files, cannot attribute a mutation, or cannot be re-scored
is not worth its inference. HP7 gates HP8.

**Two limits carried into every cycle, from SwiftStar's own records.** Its
live campaign substitutes harness-defined scope and commands for the model's
packet parameters, so it does not jointly validate packet authoring,
isolation and integration
(`swiftstar/Sources/swiftstar-agenttest/main.swift:1297-1305`). And a passing
workflow can hide a silent implementer: seed 221 passed with **0 mutations**
in all three dispatched phases
(`swiftstar/captures/agenttest/20260829-212715-roadmap-user-story-directive/campaign-stdout.txt:14-16`).
HP5 exists because of the second one.

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
