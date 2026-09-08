# Brief: Satyrn Evals

## North star

Given an engine change, run meaningful development tasks, preserve every
attempt, and determine which required behaviours improved or regressed and at
what cost. Keep enough headroom to test the next hypothesis.

Satyrn Evals captures a task, invokes an attempt command, persists the patch
and transcript, and grades the saved evidence offline. The engine seam is an
executable command so the suite can be developed with a fake command and does
not import engine internals.

Headroom belongs to a task, prompt, model, engine, and budget together. It is
not a permanent task label. A task that currently passes can expose a
regression; a task that currently fails can test a targeted improvement. A
prompt change is a different evaluation condition. Do not draw a component
claim from a product comparison: use matched controls that differ only in the
component when component attribution is the question.

## Invariants

1. **Preserve before judging.** Persist the patch and transcript before
   grading or cleanup. Grade and re-score only retained evidence, so a grading
   or reporting repair does not require another model run.
2. **Use independent verdict evidence.** The verdict comes from an oracle test
   hook, never stdout or an exit status. The result path is not bound to the
   oracle process, so model code imported by that process can forge a
   shape-valid result; the current mitigation and limit are in
   [trust boundaries](docs/topics/trust-boundaries.md).
3. **State the population.** Report explicit denominators, missing cells, and
   unmeasured diagnostics. Do not silently shrink a denominator or read an
   arm-specific detector as an arm-neutral rate.
4. **Freeze execution before spending budget.** Record the task, prompt,
   model, engine revision, tool surface, budget, schedule, and stopping rules
   before a budgeted run. Keep completed cells on interruption and state the
   rule for incomplete cells.
5. **Prove checks in both directions.** A grader accepts a known-good fixture
   and rejects a known-broken fixture. A refusal test has a sibling success
   test. The default tier runs without model, network, or subprocess; real
   Git, materialization, an attempt command, and oracle execution belong to
   marked integration checks.

## Development feedback policy

Target useful development feedback within 10–15 minutes. Use the cheapest
check that can answer the current question:

| Question | Cheapest useful check |
| --- | --- |
| Did a specific software defect change? | Deterministic regression test; no model. |
| Does the complete execution path work? | One bounded attempt. |
| Is a change promising enough to investigate? | Two attempts per matched configuration on one relevant qualified task. |
| Does an improvement survive repetition or broader conditions? | A separately planned confirmation run. |

Small runs are triage, not success-rate, causal, or headroom conclusions. A
two-minute command budget answers a different question from a fifteen-minute
budget; keep their conditions and results separate. Before choosing a short
budget or repeated-call limit, check representative retained attempts to make
sure the relevant behavior occurs within it. Do not use a repeated-call limit
when recovery from repetition is the question.

Declare development budgets and stopping rules before a live run. Stop remaining
launches on an established infrastructure failure (wrong model, missing
executable, invalid task setup, or broken artifact path), retain the partial
batch, and repair it. An ordinary failed repair is a valid observation and does
not justify an improvised retry. Each expensive failure should yield a cheap
deterministic regression test for the reproducible component; that test proves
the component handles the saved request or artifact, not that a model will make
better choices.

Measure setup, command, and grading durations before optimizing infrastructure.
Short-run promises require a bound around the whole attempt, not merely a
model-command timeout. Keep task workspaces isolated; investigate cache reuse,
model reuse, or accelerator concurrency only after those measurements identify
the limiting stage.

## What comes next

The current milestone qualifies `agentclinic-repair-depth-3` at R3 and, as of
2026-09-08, `agentclinic-repair-misleading-locus` at R3 — the latter with witnesses
derived from real suite runs and a verified live route. A matched four-cell
screen put both arms at ceiling (2/2 each) and **detected no outcome
difference** — comparison evidence, but not enough to conclude anything general
about the arms. The milestone also proves
one repeatable synthetic route from a frozen execution description to retained,
re-scorable results. Its design and plan live in `docs/current/`.
`ROADMAP.md` says what is active and what remains outside this repository's
immediate control.

Historical specifications, run interpretations, and withdrawn ideas are in
`archive/`. They are evidence to retrieve for a named question, not policy to
apply by default.
