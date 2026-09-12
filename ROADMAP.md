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

**Status 2026-09-10.** After HP, Phase TE — fewer wasted turns, more work
within budget — is now proposed and **recorded below**, with its own
[execution plan](docs/current/engine-turn-efficiency-plan.md). It confirms two
turn-efficiency claims on an easy and a harder AgentClinic roadmap once HP's
route is accepted; TE does not absorb unfinished HP requirements. Neither
phase authorizes implementation, merge, commit, or inference; each live stage
needs its own budget authorization.

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
| **HP1** Packet schema | The typed packet mapped from SwiftStar's field set: objective, pinned facts, base revision, writable scope, behaviour to preserve, worker self-test command, redactions, budgets. **No parent validation command** — sourcing one from the task's `oracle` would put the hidden oracle hook in a document the implementer reads | Executing a packet; anything engine-side; fields this path does not need | spec + plan | **accepted 2026-09-10** — acceptance detail in the per-cycle result docs |
| **HP2** Offline route | The three phases end to end against a fake implementer on the engine seam, no model | Real inference; isolation (HP3); attribution (HP5) | plan only | **accepted 2026-09-10** — acceptance detail in the per-cycle result docs |
| **HP3** Chained isolation *(engine)* | Phase N branches from phase N-1's accepted commit; a refused phase stops the chain with no candidate ref | Pools, parallel dispatch, retry | spec + plan | **engine-side accepted 2026-09-10** — acceptance detail in the per-cycle result docs |
| **HP4** File creation | Declared directory source paths, so an empty-skeleton directory is distinguishable from a creation target | A trailing slash as the settled syntax; relaxing scope enforcement | plan only | **accepted 2026-09-10** — acceptance detail in the per-cycle result docs |
| **HP5** Role attribution | Every mutation attributed to orchestrator or implementer from retained events | Judging whether delegation helped; any new pathology detector | spec + plan | **accepted 2026-09-10** — acceptance detail in the per-cycle result docs |
| **HP6** Chain retention | Instructions, packets, worker events, candidate, validation output, accept/reject with reason, cost per role, fallback labelled | Cost thresholds or a budget verdict | plan only | **accepted 2026-09-10** — acceptance detail in the per-cycle result docs |
| **HP7** Live route proof | One orchestrated delivery, `n` frozen at 1, Baseline model, the adopted verification instruction | Superiority of any kind; extending `n` after reading it | spec (pre-run record); [result](docs/current/hp7-live-route-proof-result.md) | **Run 2026-09-10, accepted with corrections, not reopened as infrastructure.** — acceptance detail in the per-cycle result docs |
| **HP8** Workflow comparison | Orchestrated route against the continuous-session route, same roadmap and prompt, triage at two attempts per configuration | Publication; mechanism attribution; wall-clock between contiguous arms | see [TE plan](docs/current/engine-turn-efficiency-plan.md), TE2–TE3; [result](docs/current/te2-hp8-screen-result.md) | **Run 2026-09-10, corrected 2026-09-10 after review.** — acceptance detail in the per-cycle result docs |

**Why plan-only, and ordering.** HP1, HP3, HP5, HP7 and HP8 move an evaluation
condition, evidence boundary, task contract or interpretation and earn a spec;
HP2, HP4 and HP6 implement decisions those specs fixed. HP1 gates HP2/HP3;
HP4/HP5/HP6 gate HP7; HP7 gates HP8. Two SwiftStar limits carry into every
cycle: its live campaign substitutes harness-defined scope and commands, so it
does not jointly validate authoring, isolation and integration, and a passing
workflow can hide a silent implementer (seed 221, **0 mutations** across all
three phases) — HP5 exists because of the second.

## Phase V — verified, bounded delivery

**Track A closed 2026-09-11; Track B (engine) proposed.** Design:
[phase-v-design.md](docs/current/phase-v-design.md). Track A made the evidence
trustworthy — a committed per-phase ledger, a 20-record claim inventory, the
claim-level measures and the [Track B gate](docs/current/phase-v-track-b-gate.md)
— and published the exploratory [engine gap register](docs/current/phase-v-engine-gap-register.md).
Track B (V4 validation, V5 budget, V6 live proof) is engine-owned and mirrored
in `satyrn-engine`'s roadmap, with cross-repo revisions recorded in both:
V4 at `satyrn-engine@0069ace`, V5 (whole-attempt turn and deadline budget)
at `satyrn-engine@1ea478c`; V6 is the remaining live proof.
Two Backlog entries carry Track A's follow-ups.

## After HP: Phase TE — fewer wasted turns, more work within budget

**Proposed 2026-09-10; closed 2026-09-11 at [TE6](docs/current/te6-explain-and-decide.md).
TE1 closed for pairing/accounting, ceiling qualified; TE2 run, both
frozen questions read against Engine; TE3 not pursued, not reopened;
TE4 qualified, screened, and closed — the harder-work claim is not
supported. No further live Phase TE spending is proposed.**
[The execution plan](docs/current/engine-turn-efficiency-plan.md) follows HP
with two independent claims: Engine uses fewer total model turns on an easy
AgentClinic roadmap both configurations reliably complete; and Engine completes
one harder roadmap more reliably within a practical shared turn ceiling.
Turns are the outcome, not a proxy for speed. Reduced unproductive looping is
the explanation to investigate, not a conclusion inferred from lower totals.

The sequence is: identify the actual pair and audit accounting; reuse HP8 or
run a necessary easy screen; confirm easy efficiency with a quality guardrail;
qualify and screen one harder roadmap; confirm harder completion; review both
claims and decide. Count every role and failed attempt. Historical screens
remain outside fresh confirmation denominators. Each confirmation freezes its
practical thresholds, statistical design and authorized budget before launch.

**TE1 closed for pairing and accounting, 2026-09-10; the ceiling
criterion qualified.** The actual pair: continuous Pi (Baseline)
against Phase HP's packet route with HP3 composed (Engine) —
`arms/engine.json` is a different, paused comparison. `turn_ledger.py`
reads both sides' real transcripts through the same code: the frozen
40-turn ceiling was Baseline-only (range 15–25) until HP7 gave a real
Engine point (22 turns) inside it. Pairing and accounting-reproducibility
hold without qualification; "40 checked, not asserted" holds only for
attempts that complete normally — TE2/HP8's voided attempt ran 65 turns
in one phase alone, unenforced, so "not contradicted" no longer
describes the ceiling unconditionally (see
[the result](docs/current/te2-hp8-screen-result.md)). **The Baseline
capture gap is closed too** (`adapters/pi_session.py` retains
`turn_start`); already-retained pre-fix transcripts still can't answer
it, named and tested, not hidden.

**HP8 folds into TE2, decided 2026-09-10** (see the HP8 row) — one
screen for both, not a duplicate experiment, deciding whether an
easy-work confirmation (TE3) is worth running, not superiority. Run
and corrected — numbers in the HP8 row and its
[result doc](docs/current/te2-hp8-screen-result.md), not repeated
here. **TE3 not pursued, not reopened without new evidence** — not
formally closed, since the runaway's cause was then undiagnosed; an
unfavorable screen is a legitimate completion, not an invitation to
re-run. **TE4 scoping started** under the plan's own rule that a
negative easy-work result does not by itself rule out the harder
claim.

**TE4 timeline** (full detail in each dated doc, not repeated here):
[design](docs/current/te4-harder-roadmap-design.md) qualified
`agentclinic-complaint-lifecycle` (phases 1–3 verbatim, phase 4 new),
8/8 checks. [Route proof](docs/current/te4-route-proof-result.md) found
a grader defect (fixed) and a phase-2-board Engine runaway, [investigated](docs/current/phase-2-board-runaway-investigation.md) and
traced to a destructive `edit` deleting the phase-1 home route.
[A guardrail sentence, candidate-tested then adopted](docs/current/phase2-guardrail-candidate-result.md)
into this task only closed it for its own final-content measure (5/5,
then 7/7 pass since — though [corrected](docs/current/te4-tightening3-reverification-result.md),
"pass" meant final content intact, not that the edit never happened;
it recurs in about half of post-guardrail attempts and self-corrects
in all but one). Two `id`-field ambiguities (position, then default)
were closed by **tightenings 3 and 4**, [re-verified](docs/current/te4-tightening4-reverification-result.md)
and validated live. The same destructive-edit mechanism then turned up
recurring at phase 4 (3 of 4 graded attempts), with no guardrail
against it there — **phase-4 guardrail applied**, see the task's own
[`QUALIFICATION-NOTE.md`](src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md).

**Phase-4-guardrail re-verification, three rounds**
([round 1](docs/current/te4-phase4-guardrail-reverification-result.md),
[round 2](docs/current/te4-phase4-guardrail-reverification-round2-result.md),
[completion-recurrence check](docs/current/te4-completion-recurrence-check-result.md),
several corrections along the way): round 1 was 0/3; round 2 gave the
first two full completions ever on this task family; the recurrence
check added 2 more. Across all 13 phase-4-reaching Engine attempts on
record, the guardrail's own destructive edit occurs regardless of the
guardrail (11 of 13); restoring it is **necessary** for completion (0
of 6 non-restorations pass) but **not sufficient** (4 of 7 pass; the
other 3 time out, none submitted-and-rejected) — the bottleneck is
turn/time budget, unexplained by anything on record. Engine had
completed the full task **4 of 16 times** before the screen below.

**[TE4 screen run and reported](docs/current/te4-screen-result.md),
corrected after review: both configurations pass the hidden grader
both times (18/18 each), but Engine's own required verification never
did.** Neither screen Engine attempt's own `uv run python -m pytest
tests` ever passed at phase 4 (the redirect-trap pattern, unfixed);
**one fabricated an invented "2 passed" pytest transcript while its
own last tool call showed two failures** — a new, distinct behavior,
surfaced only because this review checked test *outcomes* and report
honesty, not just file structure. Per-phase turns: Engine used fewer
on phases 1–3 (TE's original hypothesis) and far more on phase 4 alone
(23 vs Baseline's 6–8) — the whole-attempt gap is entirely phase 4.
Baseline's first data under the current, fully-fixed prompt is clean
both times, tests included (43, 32 turns). Per the plan's own rule for
a "both pass" screen: reported plainly, not grounds to enlarge the
screen or design TE5's confirmation. Engine's cumulative record is now
**6 of 18**; Baseline is 3 of 3, though never tested repeatedly under
the pre-fix conditions Engine failed under, so not evidence it is
immune to them. The harder-roadmap claim is not supported on current evidence.

HP remains responsible for the composed, retained, regradable route; TE does
not absorb unfinished HP requirements or reopen the paused single-task
tuning campaign below. Negative and inconclusive results are legitimate completion, not invitations to extend a batch or search for a favorable task.

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
