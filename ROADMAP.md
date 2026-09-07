# Roadmap

## Current milestone

Build one dependable route from a qualified task-condition to a retained,
re-scorable result. The milestone qualifies only
`agentclinic-repair-depth-3` at `R3`, then proves a two-attempt synthetic
route before any separate model-run budget is requested.

Acceptance, design decisions, and the ordered work are in
[the first-milestone design](docs/current/first-milestone-design.md) and
[plan](docs/current/first-milestone-plan.md). The active documents are the
source of truth for this work.

## State and dependencies

The evaluation core already captures attempts, preserves evidence, grades
offline, and can re-score retained artifacts. The milestone checks that one
condition's public task feedback, hidden oracle coverage, deliberate incomplete
repair, and declared execution path agree.

The documentation reset defines the public vocabulary and command surface.
Implementation work begins only after its Astra review. Model runs have their
own budget and are not authorized by this work. The milestone does not repair
or extend telemetry, census, or reporting machinery.

The engine, model server, and any real execution environment are external
dependencies. This repository can define and test the seam, fixture
qualification, evidence retention, and offline re-scoring. A real engine
comparison waits for a frozen configuration and the separately authorized run.

## Completion

The milestone completes when depth-3/R3 has documented
public/hidden/incomplete-repair witnesses; its bounded synthetic route proves
actual edit/test/artifact/grade flow plus between-attempt resume and
mid-attempt recovery-needed preservation; and its result can be regenerated
from retained artifacts. The detailed acceptance criteria are in the design.

Historical phase labels, probes, and result narratives are archived outside
the active reading path.
