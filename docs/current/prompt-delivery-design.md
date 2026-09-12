# Phase PD — prompt delivery: what the overnight numbers are evidence about

**Proposed 2026-09-12. Authorizes no implementation beyond PD1, no merge,
no inference, and no spending.** PD1 is the clean-up recorded in this
document's own commit. PD2–PD5 are proposal: each is scoped here so it can
be authorized later on its own terms, and each live step needs its own
pre-run record and budget authorization under `BRIEF.md`'s comparison
policy. This is a proposal to make the next Baseline/Engine numbers mean
something, not a plan to produce more of the numbers we have.

## Goal

Deliver the AgentClinic roadmap to both arms the way a developer using
spec-driven development actually delivers it — reference files plus a
pointer prompt — in an easy and a harder variant that share one hidden
grader, so that a later matched comparison measures the architectures and
not the prompt. Then run one cheap screen to verify the route and take an
initial observation.

## Starting point: the overnight comparison, and what it measured

**The figures.** The 2026-09-12 overnight phase-4 context screen ran 36
cells, 12 per arm, on `agentclinic-complaint-lifecycle`: Baseline 12 of 12,
plain Engine 6 of 12, `engine-basefiles` 4 of 12; Baseline over plain
Engine, one-sided Fisher exact **p=0.0069**; phase-4 turns, Engine over
Baseline, one-sided Mann-Whitney p=0.0028. A second night's edit-guard
screen ran 24 more cells: plain Engine 4 of 12, guarded 7 of 12, p=0.207.
Both runs are retained under `~/satyrn-smokes/2026-09-12-overnight-phase4/`
and `~/satyrn-smokes/2026-09-12-overnight-editguard/`, and their result
documents, grading reports, independent review and committed per-attempt
dataset live in the closed worktree named below.

**The mechanism, from the retained transcripts.** All five plain-Engine
hidden-grader failures at phase 4 share one tool sequence — `read(app.py)`,
one `edit(app.py)`, `write(tests/test_app.py)`, self-test, deliver
(`overnight-phase4-context-result.md`, "The Engine failure has one
signature") — and in each the one `edit` replaced the accepted phase-3
`POST /complaints` route with the new resolve/reopen routes. The model read
the correct file immediately before the edit and still dropped the route
while constructing the call: a copy-fidelity failure inside the edit, not
blindness to the file. The independent review's correction is carried with
it: Baseline attempted the same deletion too (9 destructive edits across 7
of 12 cells, every one self-repaired before the checkpoint; 0 of 12
delivered without the route), and the supported contrast is attempt rate —
Engine 19 of 23 phase-4 attempts against Baseline 3 of 12, p=0.0014.

**The self-tests.** Derived here from each cell's retained
`chain-evidence/phase-4-resolve-reopen-candidate.json` and the last
`collected N items` line in its `harness/.satyrn-implementer-transcript.jsonl`:
the five failing cells (001, 005, 018, 019, 027) each delivered a
`tests/test_app.py` with exactly 2 `def test_` and a last self-test of
`collected 2 items`, and none of the five POSTs to `/complaints`; the six
completions collected 3, 5, 5, 3, 3 and 2 (004, 025, 028, 029, 030, 033).
The Engine grading report finds cumulative test counts shrinking between
phases in 12 of 12 plain-Engine cells that reached phase 2, against 0 of 12
Baseline. The phase-4 prompt's own test bullet names only the new
behaviour to test (`session.json`, `phase-4-resolve-reopen`); nothing in
the packet asks the implementer to re-verify what it is told not to break,
and a suite rewritten each phase discards whatever earlier coverage there
was regardless.

**The prompt's history.** Since qualification, this task's `session.json`
has changed four times — `3e6ad02` (phase-2 guardrail adopted), `c494297`
(tightening 3), `001e6d6` (tightening 4), `c12dd05` (phase-4 guardrail) —
and the task's `QUALIFICATION-NOTE.md` records an observed Engine attempt
as the trigger for each. The two earlier tightenings inherited from
`agentclinic-session-phased` were offline qualification mapping on
2026-09-09, not run-triggered. Before the overnight run Baseline had 3
attempts on this task family (1 pre-fix route proof, 2 post-fix screen) to
Engine's 18; [the TE4 screen result](te4-screen-result.md) already says
that framing Baseline as "never needing" those fixes "overstates the
evidence."

**The delivery style is not one a developer uses.** Every phase's prompt
inlines the full implementation detail — exact route paths, field order,
badge text — as the turn message. The reference project this content
descends from keeps it in files:
`/Users/pauleveritt/PycharmProjects/dlai-local-ai-course/specs/` holds
`mission.md`, `tech-stack.md` and `roadmap.md`, and that `roadmap.md` is
the same text this repository inlines for phases 1–2 (the lineage is
recorded: phases 1–3 were quoted from `swiftstar@ab1d83d`
`fixtures/agenttest/specs/roadmap.md`, whose `PROVENANCE.md` traces them to
`local-ai-pi@8af05f8` and the prior ds4-control project). SwiftStar's
harness reads `specs/mission.md` and `specs/tech-stack.md` as shared context
whichever roadmap variant runs (`Sources/swiftstar-agenttest/main.swift:75-76`).
No task under `src/satyrn_evals/tasks/` delivers a prompt this way.

**A harder variant already exists, with run evidence.** `local-ai-pi`'s
worktree `user-story-batch` (`.worktrees/user-story-batch`, HEAD `0f149bc`)
carries `examples/agentclinic/specs/roadmap-user-story.md` (introduced at
`191895e`, last touched `1d33d0f`) and `domain.md` (`6fb0006`): the same
three phases as user-facing outcomes, "targeting the identical app: same
routes, same redirect contract, same seed content." SwiftStar ran it live
(`docs/superpowers/research/`): `experiment-results-orchestrate-userstory.tsv`,
seeds 201–204, 0 pass / 3 fail / 1 harness-void; `-fixed.tsv`, seeds
211–215, 5 harness-void; `-221.tsv`, seeds 221–230, 6 pass / 3 fail / 1
harness-void. Those are SwiftStar's orchestrator and harness, not this
instrument, and are cited as existence and feasibility evidence only. No
phase-4 (resolve/reopen) user story exists anywhere.

**What this makes the overnight numbers.** Evidence about one condition:
one task, one model, one budget, and one prompt that inlines implementation
detail no developer inlines, amended four times in response to one arm's
failures. Under that condition the packet route completes less often and
spends more turns on phase 4, and that stands. It is not a verdict on
either architecture, because the condition is not representative of the
work either was built for — which is why what follows is authorized to
propose and not to spend.

## Sequence

### PD1 — Clean-up (done in this commit; authorizes nothing further)

Two commits on `main`: the pathology entry found in `cell-003-baseline`
during the same investigation (`docs/pathologies.md` entry 7,
`docs/remediations.md` entry 7, with the renumbering they required), and
this design with its roadmap entry.

The worktree `.claude/worktrees/overnight-phase4-context` (branch
`worktree-overnight-phase4-context`, HEAD `fbb23f4`, one commit past this
repository's `3e25954`) is **closed and retained as evidence**: it holds
both nights' pre-run records, results, grading reports, the independent
review, `docs/current/data/overnight-2026-09-12-attempts.jsonl`, and the
launcher, readout and edit-guard code. It is not merged, not deleted, not
superseded, and not to be edited. Cite it by path; do not rerun it.

### PD2 — A worktree and branch for this investigation (not yet authorized)

Once PD3 is authorized, open a fresh worktree and branch for it, per
`superpowers:using-git-worktrees`. Nothing below happens on `main`.

### PD3 — SDD delivery in the task-authoring path (proposal; heaviest scrutiny)

A task's `base/` may carry `specs/mission.md`, `specs/tech-stack.md` and
`specs/roadmap.md`, materialized into the workspace like any other base
file, and a step's prompt becomes a pointer sentence — "Implement Phase 1;
see `specs/` for details" — rather than the phase's inlined text. The
standing preamble (writable scope, no new dependencies, the adopted
verification sentence) stays, because `ROADMAP.md` adopted it as operating
policy for session prompts. Both arms must receive the same files: the
Baseline session sees them in its workspace; the packet route's builder
(evals-owned, HP1) must carry them without re-inlining the roadmap into
`objective` or `preserve`, or the change is cosmetic.

**This step decides whether either arm's future numbers mean anything, so
it is checked against how a developer actually works, not accepted because
it compiles.** The standard to match is the reference layout in
`dlai-local-ai-course/specs/` and SwiftStar's convention of always
supplying `mission.md` and `tech-stack.md` as shared context: three files,
one pointer, the agent reads the specs itself. Review asks whether a
developer would recognise the workspace and the prompt; a delivery a
developer would not use is a failed step, not a passed test.

Qualification is unchanged in kind: a `prompt-faithful` witness written
from the pointer prompt plus the specs alone must pass the hidden grader,
and `QUALIFICATION-NOTE.md` must map every hidden check to text the
solver can reach. A delivery change is a prompt change, and `BRIEF.md`
makes that a different evaluation condition: no figure from it pools with
any figure above.

### PD4 — An easy and a hard variant on one grader (proposal)

Two tasks, or two conditions of one task, sharing the existing
`grader/overlay` and fixtures byte for byte, so the prompt style is the
only difference between them:

- **Easy.** The current `session.json` phase text, tightenings and both
  guardrail sentences included verbatim, moved into `specs/roadmap.md` and
  delivered by pointer. Against the current task it changes delivery only.
- **Hard.** `roadmap-user-story.md` and `domain.md` from `local-ai-pi`'s
  `user-story-batch` worktree for phases 1–3, near-verbatim, plus a newly
  authored phase-4 user story for stable identity and resolve/reopen in
  the same voice — outcomes an agent experiences, not files to edit. It
  carries none of the Engine-triggered guardrails, because a user story
  does not say how to edit a file; that asymmetry is declared here, not
  hidden.

The hard variant must earn qualification on its own: if a hidden check
(the keyword-only `id` contract, check 14, is the obvious case) cannot be
reached from story-level wording, the story states the outcome or the
check is reconsidered — recorded as a qualification finding, never as a
silent tightening after a run.

### PD5 — An n=2 screen across the new conditions (proposal, no budget)

Two interleaved attempts per arm on each variant — eight cells — preceded
by one route-verification attempt per arm per variant that stays outside
the denominator, under the qualify → verify → screen → decide discipline
of [the suite brief](agentclinic-suite-brief.md) and
`agentclinic-repair-misleading-locus`. A pre-run record freezes the
outcome question (hidden-grader completion) and the cost question
(per-phase `turn_count`, `tool_count`, `elapsed_seconds` from
`session-record.json`; `implementer_cost` and `orchestrator_cost` from
`chain.json`; `turn_ledger.py` across both) before the first cell. Eight
attempts verify the route and give an initial observation; they support
no superiority claim, no rate, and no mechanism attribution, and nothing
in their result authorizes extending `n`.

## Quality beyond pass/fail — named, and out of scope

The hidden grader is binary and the cost counters above are the only other
measurement. The overnight review showed what that misses: a fabricated
"passed" report, a suite rewritten each phase, a route destroyed and
restored twice inside one phase. A transcript-level quality read — the
Phase V classifiers `destructive_edit`, `restoration`, `self_test_outcome`
and `verification_claim` in `claim_measures.py` applied per attempt, or a
model-assisted judgement of the delivered application and tests — would
turn those from review findings into measurements. **It is out of scope
for this phase.** PD5's result may earn it as a separately proposed step;
nothing here builds it.

## Done and out of scope

PD1 is complete when both commits are on `main` and the retained worktree
is untouched. The phase is complete when PD5's screen is reported with its
denominators and a decision on whether either variant is retained; a
negative, inconclusive or blocked result is a legitimate completion.

Excluded: merging or rerunning the retained worktree; any change to
`satyrn-engine`; a confirmation campaign; a fresh-context Baseline control;
adopting the edit guard or `base_files`; the test-carry-forward remedy the
edit-guard result names; and any claim, from any step here, that Baseline
or Engine is the more reliable architecture.
