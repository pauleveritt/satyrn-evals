> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# Brief: satyrn-evals

**Read this first. Do not re-brainstorm the project.** The design in this file
and in `ROADMAP.md` is the output of a long, twice-reviewed design session.
Brainstorm *within* a phase; do not reopen the phase list or the architecture.

## What we are building

**satyrn-evals** lets a contributor capture a Python development task, invoke
an attempt command, preserve what happened, and grade the result offline — so
they can find problems and work on engine fixes.

It owns: task capture and task manifests; known-good and known-broken
fixtures; patch application, oracle execution and grading; transcript, patch,
receipt and conditions recording; summaries of failure reasons and thrashing
behavior.

It does **not** import engine internals. **Its engine seam is an executable
command.** A fake command must satisfy the same seam, so eval development
never waits for the real engine.

## Diagnosis first, claims much later

This is the decision that governs everything else.

A contributor asking *"did my engine fix help, and if not, why"* needs to know
what broke and where. They do not need a confidence interval. The prior
project conflated these and produced a 6,065-line harness measuring a 340-line
engine, whose durable output was about five sentences.

**In scope now:** capture, attempt, offline grading, n=8, a diagnostic summary.

**Deferred to a claims layer, with a later consumer:** pre-registration,
confidence intervals, condition enforcement, cells and digest pinning, void
and retry accounting, the pilot/confirmatory distinction, model canaries, A/B
publication machinery.

Record drift; do not abort a diagnostic batch because conditions changed.
**Never compare wall-clock time between contiguous arms** — two figures in the
prior repository were retracted for exactly that. Summaries use counts.

## Provenance

Seeded from research at `github.com/pauleveritt/local-ai-pi`, commit
`8588ba4`, specifically
`docs/superpowers/research/2026-08-16-two-repo-rewrite-and-python-engine.md`
and `docs/superpowers/handoff/HARVEST-INDEX.md`. **That repository is
evidence, not source.** Do not transplant `harness/`. Re-earn each behavior
from the named fixture and incident recorded in the harvest index.

## The trap we are avoiding

The prior harness grew two systems under one name — with two different
`run_suite` functions and two different `_out_of_scope` helpers — three
results formats, eight grading-rule versions, and a conditions record with 13
fields and 5 back-compatibility sentinels because every added field
invalidated every stored checkpoint. Its measurement apparatus became the
subject: seven instrument defects found in one external review, four
silent-zero incidents, and a checker framework cut from 862 lines to 380 and
then mostly deleted.

Consequences: one phase at a time; no machinery ahead of the contract it
serves; a concept budget and a repository-weight budget from phase one.

## Binding rules

1. **Verify, don't assert.** Carry the command that recomputes a number, not
   the number alone.
2. **The evidence floor.** No grader is done until it has accepted a
   known-good input and rejected a known-broken one, each asserted by naming
   the fixture.
3. **Capture is separate from grading.** Every attempt persists its patch and
   transcript *before* cleanup, and grading reads those artifacts. Every
   grading defect in the prior project was re-scored without re-running a
   model. **This property matters more than any capture shape.**
4. **The verdict never comes from stdout or an exit code.** Predecessor
   graders were defeated by `addopts = --collect-only` and an import-time
   `os._exit(0)`. Results are written by a test hook, outside model-controlled
   output.

   > **Recorded amendment (V9, 2026-09-04).** A stated limit beside this rule:
   > the result file's path is in the oracle's environment, and the loader
   > checks shape, internal consistency, and freshness only. Model code
   > imported at collection time — which runs in the oracle's process — can
   > write a shape-valid, fresh result file and exit 0 without running the
   > tests, forging a pass. Standing mitigations: the path is reserved and
   > unlinked before the run, the graded tree is grading's private copy, and
   > the oracle's stdout/exit code are never read. There is no binding of the
   > result to the process that produced it; that is the seam's stated limit,
   > not a fixed property. See the V9 design spec §9 and the trust-boundaries
   > topic.
5. **Default tests use no model, no network, no subprocess**, enforced
   mechanically by a planted-spawn tripwire that fails the build. Real Git,
   environment materialization, model invocation and oracle execution live in
   a marked integration tier that does not run in CI.
6. **A refusal test has a sibling success test.** Most of this code tests
   rejection, and rejection is the default outcome of most failures.
7. **Cite, don't recall.** No claim about a prior result enters a plan, a spec,
   or a roadmap without a `file:line` citation checked at the time of writing.
   Earned the hard way: one false claim — "the Engine arm has never been run
   against a floored task" — was corrected in a research document and then
   restated three more times in later documents, including once four paragraphs
   above the `ROADMAP.md` text that already refuted it. Restating a conclusion
   is not the same as re-deriving it, and the failure mode is invisible from
   inside the sentence that repeats it.
8. **A detector must discriminate, in both directions.** Every check must be
   shown to fire on a known-bad drawn from the *current* batch and stay silent
   on a known-good from the same batch. Five instrument defects in one spike
   shared one shape: an absence of signal reported as a finding — a void hiding
   a fail, a preflight that could not fail, a verdict computed over zero cells,
   a detector that fired on 104 of 128 cells, and an arm protected from a
   harness defect its rivals were exposed to.

## Two selection rules, because there are two jobs

Conflating these picks the wrong artifact for both.

**A grader fixture** proves the grading machinery discriminates. No model
runs, so headroom is irrelevant. It must grade **offline and
deterministically, with no network and no third-party dependencies.**

**A diagnostic workload** must be able to show a difference between the arms
under comparison. It requires a **baseline probe** — the baseline attempt
command at n=4–6, recorded once as a property of the task. The middle-band
bar applies to the arms under comparison, not to the reference arm alone: a
task is admissible when its probe records at least one pair of those arms
in different successful-attempt bands, with the metric and stopping rule
fixed before the run and successful-attempt outcome, retained-patch production, and
conditional retained-patch quality kept separate. A task is smoke only when
its reference arm sits at or near ceiling. A task at the floor is a
capability wall only when no arm under comparison is recorded above it and no
retained patch passes a preservation-safe oracle; a completion floor whose
retained patches pass is what an engine change exists to move.

> **Recorded amendment (V5a, 2026-09-02).** The paragraph above supersedes
> the prior wording: "A task at or near ceiling is smoke only. A task at the
> floor is a capability wall, not something an engine change moves. Diagnosis
> lives in between." The corrected probes falsified the floor sentence: bare
> Pi recorded 0/4 successful attempts on `local-pings` while retained patches
> passed a fresh preservation suite, and the Engine composite then recorded
> 2/4; the pilot recorded Engine 6/6 against a 0/6 Baseline on
> `stringified-annotations`. Decision and per-arm index:
> `docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md`.

The four deterministic capture checks prove a task is **valid** — un-done at
base, and winnable. They say nothing about **discriminating power**. The prior
project spent 64 attempts to learn that three of its four tasks carried no
comparative information.

## The unsolved problem

Nothing in the prior repository reliably produced tasks in the middle band.
Every suite it built saturated, and the two tasks that discriminated were
found by running batches, not by design. **A suite with headroom is design
work that this project still owes**, and the diagnostic summary is only
informative on tasks whose baseline can move. See `ROADMAP.md`.

> **Recorded amendment (V5a, 2026-09-02).** "Middle band" is read on the
> arms under comparison, not on the bare-Pi reference alone — see the
> diagnostic-workload amendment above and the V5a design spec. Two probed
> tasks (`local-pings`, `stringified-annotations`) are admissible under that
> reading; suite-headroom design work remains owed for the rest.

## Where to start

`ROADMAP.md`, phase V1. Brainstorm V1's details treating this brief and the
phase list as settled. Build the fast-tier tripwire first.
