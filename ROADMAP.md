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
| **HP1** Packet schema | The typed packet mapped from SwiftStar's field set: objective, pinned facts, base revision, writable scope, behaviour to preserve, worker self-test command, redactions, budgets. **No parent validation command** — sourcing one from the task's `oracle` would put the hidden oracle hook in a document the implementer reads | Executing a packet; anything engine-side; fields this path does not need | spec + plan | **accepted 2026-09-10** — five slices; three review rounds recorded in the spec's correction blocks, the third closing an oracle-hook leak through `self_test_command`. Independent acceptance review verified the full field set, confirmed the no-parent-validation-command boundary holds through two separate code paths, and confirmed the golden packet fixture is exercised by a real round-trip test; 171 tests run and spot-checked non-vacuous |
| **HP2** Offline route | The three phases end to end against a fake implementer on the engine seam, no model | Real inference; isolation (HP3); attribution (HP5) | plan only | **accepted 2026-09-10** — five slices split across the tier line; a review round added the worker projection and joined the executable seam to the real grader. Independent review confirmed the tier split is real (no subprocess in any default-tier test, tripwire enforced) and drove the executable route through the real grader against `known-good`/`known-broken` fixtures; 153 default-tier plus 9 integration tests pass, `just gates` clean |
| **HP3** Chained isolation *(engine)* | Phase N branches from phase N-1's accepted commit; a refused phase stops the chain with no candidate ref | Pools, parallel dispatch, retry | spec + plan | **engine-side accepted 2026-09-10** (`satyrn-engine`) — three slices; a review round made a candidate-less success a refusal and proved retention by resolving refs; that repo's own independent review confirmed fold-forward in-process and via real `deliver --base` subprocess calls, no-partial-chain offline and against real Git. **Composed into this repo's packet route and independently accepted 2026-09-10** (`9115608`…`141f3bb`): `engine_command_implementer`/`run_and_record_engine_chain` drive real `deliver --base` chains per phase. Review confirmed no engine-internal imports, fold-forward via a real two-subprocess/real-git test, `orchestrator_mutations` structurally `()` (never `None`), and the disclosed crash-safety gap — no per-phase persistence, unlike `run_and_record_chain` — named accurately, not hidden. **Closed the same day** (`b8ca71a`): now persists per phase and in a `finally`, proven by a real run where phase 2's grader raises and phase 1's decision survives on disk |
| **HP4** File creation | Declared directory source paths, so an empty-skeleton directory is distinguishable from a creation target | A trailing slash as the settled syntax; relaxing scope enforcement | plan only | **accepted 2026-09-10** — four slices; the declaration surfaced two fakes checking scope by the prefix rule against fnmatch patterns, since fixed. Independent review confirmed both fakes now use `admits`/fnmatch, confirmed the one-directional `within_source`-vs-`admits` asymmetry is proven by a dedicated test rather than asserted away, and confirmed no scope enforcement or trailing-slash syntax was relaxed; 1780 default-tier tests pass, the five marked-tier failures traced to the pre-recorded unrelated worktree issue in `BACKLOG.md` |
| **HP5** Role attribution | Every mutation attributed to orchestrator or implementer from retained events | Judging whether delegation helped; any new pathology detector | spec + plan | **accepted 2026-09-10** — five slices; attribution observes and never gates, and an unobserved window is reported unobserved rather than zero. Independent review proved never-gates with a byte-identical-decision test, confirmed zero-vs-unobserved is a real distinct code path rather than conflated, and confirmed a mixed-delivery chain splits attribution correctly; 100% statement and branch coverage on `attribution.py`/`route.py` |
| **HP6** Chain retention | Instructions, packets, worker events, candidate, validation output, accept/reject with reason, cost per role, fallback labelled | Cost thresholds or a budget verdict | plan only | **accepted 2026-09-10** — seven slices; the widened `BoundaryEvent` replaced HP5's two-argument observer rather than adding a second injected callable, and the chain check keeps an unobserved implementer window and an observed zero on different verdicts. Two Astra/Sol review rounds (2026-09-10) found and closed: a whole-chain-then-write design that lost already-graded phases on a grader crash, candidate content retained as paths/kinds only with no offline regrade proof, and `writable_paths` reported `applied` on mere observed compliance. `run_and_record_chain` now persists per phase before grading and captures real candidate bytes; `AppliedState.OBSERVED_COMPLIANT` separates compliance from proven enforcement. A third, independent review confirmed all three fixes: crash survival via a mid-chain grader-crash test, offline regrading from retained bytes against a content-sensitive grader, and `OBSERVED_COMPLIANT` never remapped to `APPLIED` |
| **HP7** Live route proof | One orchestrated delivery, `n` frozen at 1, Baseline model, the adopted verification instruction | Superiority of any kind; extending `n` after reading it | spec (pre-run record); [result](docs/current/hp7-live-route-proof-result.md) | **Run 2026-09-10, accepted with corrections, not reopened as infrastructure.** All three phases accepted (4/4, 10/10, 13/13 hidden checks), `check_chain` zero findings, model identity verified on all 22 turns, Pi called `run_self_test` live every phase (stronger than the harness-only report). Independent review found and this repo fixed: two stale `build_pi_argv` test mocks, a stale pre-run-record commit/tool-surface field, and named two real gaps — public regression tests eroded phase 2→3 (hidden oracle unaffected), and per-phase git provenance (`base_commit`/`candidate_commit`) is not durably retained, only in-memory. Full reconciliation in the result doc. Next: HP8, folded into TE2 below |
| **HP8** Workflow comparison | Orchestrated route against the continuous-session route, same roadmap and prompt, triage at two attempts per configuration | Publication; mechanism attribution; wall-clock between contiguous arms | see [TE plan](docs/current/engine-turn-efficiency-plan.md), TE2–TE3; [result](docs/current/te2-hp8-screen-result.md) | **Run 2026-09-10, corrected 2026-09-10 after review.** Baseline completed 2/2 (3/3 phases each). Engine completed 1/2 — the other voided (phase-2-board timeout, `check_chain`: "implementer window never observed"; transcript fully retained — 65 turns, a genuine runaway loop, 58 byte-identical `write app.py` calls, 25 over the ceiling, unenforced). Completed-work turns: Engine-02's 31 is not fewer than Baseline's average 30.5. All-launched-attempts expenditure (ordinary-failure reading, per the plan's own rule): Engine averages 51 vs 30.5. Engine-02's public-test-quality finding (tests renamed phase to phase) shows no assertion loss, unlike HP7's; carried separately from that same attempt's first live self-test failure-recovery (app.py was correct throughout; the test lacked `follow_redirects=False`). TE3 not pursued, not reopened without new evidence; TE4 scoping started; the runaway loop [investigated](docs/current/phase-2-board-runaway-investigation.md) before either |

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

## After HP: Phase TE — fewer wasted turns, more work within budget

**Proposed 2026-09-10; TE1 closed for pairing/accounting, ceiling
qualified; TE2 run, both frozen questions read against Engine; TE3 not
pursued, not reopened without new evidence; TE4 scoping under way, its
phase-2-board guardrail adopted into `agentclinic-complaint-lifecycle`.**
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
8/8 checks. [Route proof](docs/current/te4-route-proof-result.md)
found a grader defect (fixed) and a phase-2-board Engine runaway,
[investigated](docs/current/phase-2-board-runaway-investigation.md)
and traced to a destructive `edit` deleting the phase-1 home route.
[A guardrail sentence, candidate-tested then adopted](docs/current/phase2-guardrail-candidate-result.md)
into this task only closed it for its own final-content measure (5/5,
then 7/7 pass since — though [corrected](docs/current/te4-tightening3-reverification-result.md)
after review, "pass" always meant final content intact, not that the
edit never happened; it recurs in about half of post-guardrail
attempts and self-corrects in all but one). Two `id`-field ambiguities
(position, then default) were closed by **tightenings 3 and 4**,
[re-verified](docs/current/te4-tightening4-reverification-result.md)
and validated live. The same destructive-edit mechanism then turned up
recurring at phase 4 (3 of 4 graded attempts), with no guardrail
against it there — **phase-4 guardrail applied**, see the task's own
[`QUALIFICATION-NOTE.md`](src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md).

**[Phase-4-guardrail round 1](docs/current/te4-phase4-guardrail-reverification-result.md),
corrected twice: 0/3 complete.** The guardrail's own edit still
recurred (7 of 9 phase-4-reaching attempts overall, 4 of 9 not
self-correcting) at the same rate as phase 2's. The `303` redirect-trap
pattern recurs in 6 of 9, resolved correctly in only 1.

**[Round 2, corrected after review](docs/current/te4-phase4-guardrail-reverification-round2-result.md):
the first two full completions ever on this task family, 18/18 each.**
Both still made the destructive edit and both restored it — restoring
was not new (2 earlier attempts did the same and still timed out).

**[Completion-recurrence check, corrected after review](docs/current/te4-completion-recurrence-check-result.md):
2 more full completions, 1 phase-2-board runaway recurrence (the
*original* import-bug pathology, unrelated to phase 4).** A first draft
claimed a clean 4-of-4-vs-2-of-2 split by restricting to the
guardrail-era attempts only, missing 3 attempts on record that also
restored the route and still failed. Restated against all 13
phase-4-reaching Engine attempts: restoring the route is **necessary**
(0 of 6 non-restorations passed) but **not sufficient** (4 of 7
restorations passed; the other 3 all timed out, none was
submitted-and-rejected) — the real bottleneck for a restoring attempt
is turn/time budget, unexplained by anything on record. Engine has
completed the full task **4 of 16 times**.

**[TE4 screen](docs/current/te4-screen-pre-run-record.md) proposed and
frozen**: 2 attempts per configuration, per the plan's own TE4 step —
Baseline's only data point on this task predates every tightening and
guardrail, so this is its first fresh attempt under current
conditions. Declared shared ceiling: 75 turns (≈1.5x Engine's observed
completion max), stated as thin. A screen, not a confirmation.

HP remains responsible for the composed, retained, regradable route; TE does
not absorb unfinished HP requirements or reopen the paused single-task tuning
campaign below. Negative and inconclusive results are legitimate completion,
not invitations to extend a batch or search for a favorable task.

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
