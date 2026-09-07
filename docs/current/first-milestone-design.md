# First milestone: one qualified condition and synthetic batch

## Outcome and boundary

Deliver one dependable offline vertical slice for
`agentclinic-repair-depth-3` at `R3`:

1. a concise, reviewed record maps its accessible R3 requirements to public
   feedback, hidden checks, and three deliberate witnesses; and
2. a small synthetic batch uses the existing execution, preservation, grading,
   tally, and re-scoring paths to retain and recover two planned attempts.

This proves an instrument route, not task headroom, model capability, cost, an
engine mechanism, or comparative performance. It authorizes neither model
inference nor a live run. A future live smoke needs a separately frozen
condition, budget, and authorization.

The development feedback policy in `BRIEF.md` applies to later live work: use
deterministic reproduction before a bounded attempt, use two-attempt matched
screens only for triage, and plan a separate confirmation run for broader
claims. This offline slice does not change a live default or authorize model
spending, but its thin route must make a future whole-attempt deadline and
explicit stop state possible without losing retained evidence.

The milestone qualifies no other task and no other rung. It adds no general
qualification platform, task matrix, fixture/live mode system, source-copy
framework, telemetry program, reporting product, or causal comparison.

## R3 qualification record

The task-local, human-authored record belongs beside the task data. It is an
input to the integration gate, not a generated conclusion or a general schema.
It must:

- identify every required R3 behavior semantically, never by a patch or file
  name;
- cite the accessible R3 contract text, public suite, supplied specification,
  or observable base behavior for each behavior;
- link each behavior to its public feedback and hidden checks; and
- state the expected public and hidden outcome for each witness.

The public command is derived from `manifest.json`'s `public_suite`; the
record must not store another copy. The durable conclusion vocabulary is
reviewer-neutral: `pending`, `justified`, and `gap`. A gap names the missing
accessible evidence and the affected hidden check IDs. It is never converted
into a pass because a generated fixture happened to pass.

Qualification executes the declared public suite unchanged in a fresh
workspace. `PYTEST_PLUGINS=satyrn_evals.oracle_hook` and a reserved
`SATYRN_ORACLE_RESULT` path inject hook evidence without changing the command
argv. The existing hook-path shim keeps the task environment from borrowing
Evals dependencies. Public outcomes come from fresh, nonempty executed IDs and
no collection errors, never stdout or process status. The hook does not record
collected IDs, so the record makes no collection claim.

The current hook-result path is supplied to the oracle process. Model-controlled
code imported there can forge shape-valid output; this authorship limit remains
documented in [trust boundaries](../topics/trust-boundaries.md). It does not
relax the requirement that the verdict be derived from hook-written evidence.

### Witnesses

Exactly three offline witnesses are required:

| Witness | Required evidence |
| --- | --- |
| Base | The exact known hidden failures for the unchanged base task and its public outcome. |
| Known-good repair | The declared public suite and every hidden check pass. |
| Declared incomplete repair | At least one omitted required behavior fails its mapped hidden check or checks; record the public outcome even when it is green. |

The incomplete repair should be a leave-one-required-repair-out patch whenever
one exists. It can reuse known-broken material only if that patch identifies an
omitted behavior. Every witness records exact expected executed IDs, hidden
non-passing IDs, and collection-error status. A known failure path has a
sibling successful witness, so a refusal cannot pass vacuously. Results use
`pass`, `fail`, `gap`, and `unavailable`; unavailable evidence is not success.

The existing `tests/integration/test_agentclinic_gate.py` is the qualification
seam. Extend it first, preserving its real public/hidden paths and grade path.
Do not introduce a qualification command, general validator, or platform unless
this direct extension demonstrably cannot represent the record and its checks.

An Astra review decides semantic adequacy after the record and its three fresh
witnesses exist. A required behavior without accessible R3 evidence, ambiguous
witness, missing expected executed ID, or collection error is a stop: retain the
evidence, report the gap, and do not begin the synthetic route.

## Thin synthetic batch

Only after qualification passes, first try to express the route through
`scripts/interleave.py`, `satyrn-evals run --n 1`, and `scripts/tally.py`. If
their existing interfaces suffice, add only a checked-in fixture input and a
focused integration test. A necessary wrapper is a thin launcher over those
three paths, never a scheduler, recipe language, source freezer, or reporting
product.

The batch has two planned synthetic attempts against the qualified task and R3.
Before invocation it writes a schedule with the task, rung, fixture-executor
identity, exact command/configuration digest, fixed limits, and explicit
denominator. Its synthetic identity visibly says it is neither a model nor an
engine result.

The committed `recipes/first-milestone-depth3-r3.fixture.json` is the sole
fixture input. `scripts/run_first_milestone.py` is its narrow launcher: it uses
`build_order` and `materialize` from `scripts/interleave.py`, invokes
`satyrn-evals run --n 1` for each scheduled cell, and calls `scripts/tally.py`
over the retained cell summaries. It does not load arm files or create a new
execution mode. Its fixture executor records `fixture/agentclinic-executor-v1`
as both scheduled and observed identity.

Each attempt preserves its patch and transcript before grading or cleanup, then
stores hook-derived receipts. Regrading works only from those retained
artifacts; it must not launch an executor. A result reads those artifacts and
the prewritten schedule, not stdout, exit status, an earlier report, a cost
estimate, or a causal interpretation.

The route preserves these boundaries:

- On between-attempt resume, a validated completed scheduled attempt is skipped,
  never rerun or replaced.
- An interruption during an attempt leaves retained paths and an explicit
  recovery-needed or blocked state. Resume stops for review; it invents no retry
  policy.
- Tally retains the planned denominator. Missing, aborted, or mismatched
  attempts prevent a complete tally; a completed `unavailable` grade remains a
  counted observation.

Prove three focused integration cases: clean two-attempt completion;
interruption between attempts followed by a resume that skips the validated
first attempt; and mid-attempt interruption that preserves evidence and blocks
automatic continuation. Every refusal path has a sibling successful run.

## Acceptance and live-run boundary

Accept the offline milestone only when:

- active documentation uses the small vocabulary and truthfully exposes the
  available command surface;
- the R3 record has no requirement gap and has passed Astra semantic review;
- all three witnesses have fresh hook evidence matching their recorded public
  and hidden outcomes;
- the synthetic batch writes its schedule before execution, retains artifacts,
  states its denominator, regrades offline, and proves both resume boundaries;
  and
- the default and marked integration tests pass, including the default-tier
  subprocess tripwire.

No live or model run starts automatically. A separate request must freeze the
complete condition, name the question and any causal controls, declare the
schedule, stopping rule, budget, and evidence-review plan.
