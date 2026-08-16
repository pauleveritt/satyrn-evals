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
`c74c31f`. **That repository is evidence, not source.** Do not transplant
`harness/`. Re-earn each behavior from the named fixture and incident recorded
in the harvest index.

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
5. **Default tests use no model, no network, no subprocess**, enforced
   mechanically by a planted-spawn tripwire that fails the build. Real Git,
   environment materialization, model invocation and oracle execution live in
   a marked integration tier that does not run in CI.
6. **A refusal test has a sibling success test.** Most of this code tests
   rejection, and rejection is the default outcome of most failures.

## Two selection rules, because there are two jobs

Conflating these picks the wrong artifact for both.

**A grader fixture** proves the grading machinery discriminates. No model
runs, so headroom is irrelevant. It must grade **offline and
deterministically, with no network and no third-party dependencies.**

**A diagnostic workload** must be able to show a difference. It requires a
**baseline probe** — the baseline attempt command at n=4–6, recorded once as a
property of the task. A task at or near ceiling is smoke only. A task at the
floor is a capability wall, not something an engine change moves. Diagnosis
lives in between.

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

## Where to start

`ROADMAP.md`, phase V1. Brainstorm V1's details treating this brief and the
phase list as settled. Build the fast-tier tripwire first.
