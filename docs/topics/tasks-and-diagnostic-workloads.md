# Tasks, qualification, and headroom

Evals uses tasks for two related jobs. A grader fixture demonstrates that the
oracle can distinguish a correct patch from an incorrect one. An evaluation
condition tests a specific engine hypothesis. The same task may contribute to
both jobs, but the evidence for each is different.

## A grader fixture proves the oracle

A grader fixture is a bundled task with known-good and known-broken patches.
It proves that offline grading accepts the correct change and rejects the
incorrect one. It needs no model run or headroom. `format_number` is the small
fixture used in the [first tutorial](../tutorials/see-one-verdict.md).

## Qualification makes requirements inspectable

Capture establishes that a base is un-done and a known-good patch is winnable.
Qualification goes further for an evaluation condition: it maps each required
behaviour to evidence accessible to the solver, public feedback, hidden oracle
checks, and known plausible incomplete repairs. A public-green/hidden-fail
partial repair can be useful evidence when the requirement is accessible by
another source; it is never silently treated as a complete task.

The current milestone records this mapping only for
`agentclinic-repair-depth-3` at R3. See [Current work](../current/index.md).

## Headroom belongs to a condition

Headroom belongs to the task, prompt, model, engine, tool surface, and budget
together. It is not a permanent task label. A condition near a previous high
outcome can reveal a regression or cost change. A condition at a previous low
outcome can test a targeted improvement. Changing the prompt, tool surface, or
budget creates a different condition.

To claim that one component caused a difference, compare matched conditions
that isolate that component. A product comparison may establish a product
result, but it does not attribute the result to one internal component.

Historical material remains in the archive as evidence; it does not govern
current qualification or experiment selection.

Use the [diagnostic-batch guide](../guides/run-a-diagnostic-batch.md) for the
operational command and the [glossary](../glossary.md) for format vocabulary.
