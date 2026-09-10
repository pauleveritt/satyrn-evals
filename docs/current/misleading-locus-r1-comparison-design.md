# A fresh misleading-locus / R1 product comparison

Design of record, written 2026-09-08. **No spending is authorized by this
document.** Each live stage needs its own budget authorization.

## The question

Does the previously observed Engine advantage in **completing repairs** on
`agentclinic-repair-misleading-locus` at `R1` survive under matched conditions
with the current engine?

Two questions are declared, and they are declared now rather than chosen later:

**Primary — outcome.** The probability that an attempt is a **successful
attempt** (verdict `pass` from hook-written evidence). One contrast, one test,
decided before the data.

**Secondary — cost, descriptive.** Turns, tool calls, and terminal-response
token usage. These are reported **whatever the primary shows**. Equal pass
counts do not erase a possible efficiency difference, and an arm that succeeds
as often for materially less is a real result about the product.

**If cost is to drive adoption, its decision rule belongs here, before the
run.** This design does not set one, because no adoption decision currently
hangs on cost. That is a deliberate gap, not an oversight: adding a cost
threshold after seeing cost figures would be choosing a rule from the data.

## Disclosure: the selection is informed, and that is legitimate

`R1` on this task was chosen **because** an earlier interleaved batch recorded
Engine 11/12 against Baseline 4/12 there. Using earlier observations to choose
the next experiment is how investigation proceeds. What the protocol forbids is
concealing that the choice was informed, pooling exploratory results into a
confirmatory denominator, or changing an experiment after seeing its outcome.

Accordingly: this is labelled a **replication of a disclosed prior
observation**; the earlier counts stay **outside** this comparison's
denominator and are never pooled with it; and nothing below changes after any
count is read.

## Design

| | |
|---|---|
| task / rung | `agentclinic-repair-misleading-locus` / `R1` |
| arms | Baseline and Engine, product surfaces, each frozen and recorded separately |
| `n` | **36 per arm**, 72 scored cells, fixed |
| schedule | interleaved, seeded, order written before the first cell |
| primary test | **one-sided Fisher exact**, `alpha = 0.05`, one contrast |

**Assumptions the power figures rest on**, stated because a number without its
assumptions is not a number: attempts are independent within and across arms;
each arm holds a fixed underlying success probability for the batch's duration;
the analysis is the single pre-declared one-sided Fisher exact test above; and
the alternatives below are *stipulated effects worth detecting*, not estimates
carried over from the earlier batch. That last point matters — powering against
a previously observed effect overstates power, because an underpowered batch's
observed effect is biased upward.

At `n = 36` per arm:

| alternative | power |
|---|---|
| 0.50 → 0.75 (+25 points) | **0.651** |
| 0.50 → 0.80 (+30 points) | **0.809** |
| 0.50 → 0.85 (+35 points) | 0.921 |

Recompute:

```
uv run scripts/power.py --n 36 --p-reference 0.50 --p-alternative 0.80
```

So this design is powered for a **+30-point** improvement in completed repairs
and is **underpowered for +25**. A null at this `n` does not show the arms are
equivalent.

**Both arms need not sit below a ceiling.** An engine that succeeds reliably
where Baseline succeeds only sometimes is exactly the advantage worth having,
and this design tests that directly.

**Runtime, extrapolated and not a guarantee.** Retained `R1` cells on this task
ran 30–75 s. 72 scored cells therefore imply **36–90 minutes**, and with the two
route checks **37–92.5 minutes** — before preflight, materialization, grading
and any other overhead, and before any cell that runs long.

## The ladder

Each rung is the cheapest check that answers its own question, per
`BRIEF.md`'s development feedback policy.

**0. Offline, no model.** Qualify `R1` — its accessible evidence differs from
`R3`, which names the defect and the file. Extend the qualification gate to
`(task, rung)` pairs. All gates green.

**1. Route check — 1 cell per arm.** Answers "does the complete execution path
work at `R1`". **Retained, reported, and outside the primary denominator.**

**2. Scored batch — 72 cells**, staged in blocks, with execution-integrity
checkpoints after cells **6, 24 and 48**.

**3. Analysis once, at the end**, over all 72. `n` is frozen; no extension
after reading anything.

## The checkpoint rule

Checkpoints are **operational**. They exist so a broken instrument is caught
early, not so the experiment can be retuned.

> Verify identity, artifact integrity, and execution health. Stop remaining
> launches only when evidence **establishes** an infrastructure failure.
> Preserve ordinary unsuccessful attempts in their assigned denominator. If the
> cause is uncertain, **pause for diagnosis without replacing the attempt.**

What a checkpoint verifies: observed `message.model` against the arm record;
engine revision and pinned digests; the cell directory set well-formed against
the schedule; artifacts present and readable; the tally accepting what exists
so far.

**What is *not* an automatic stop trigger, and why.** Refusals, command
timeouts, deadline expiries, and schema or tool refusals **are outcomes we are
here to measure** — they can be produced by an arm's own behaviour. Stopping
whenever they appear would selectively truncate whichever arm is struggling,
which is a mechanism for manufacturing a favourable result. `MODEL_ERROR` and
contamination flags require **diagnosis**, not automatic classification as
infrastructure failure: a GPU out-of-memory and a model that fails on hard
inputs are different events wearing the same code.

Checkpoints do not read pass or fail counts. Blindness to counts is necessary
and **not sufficient** — the trigger list above is what makes the rule sound,
because a trigger correlated with an arm's difficulty is an outcome-dependent
stop whether or not anyone looked at the tally.

**No sequential stopping.** Pre-declared sequential designs are statistically
legitimate; this one does not use them, and the checkpoints are not an
opportunity to extend, shrink, or retune.

## When something goes wrong

**Do not restart from zero by default.** First establish which attempts are
affected, and whether the repair changes the comparison's conditions.

- An **interrupted but healthy** run resumes. A cell with `summary.json` is
  complete; an incomplete cell directory is moved aside and never reused.
- A **materially changed condition** means a separately authorized replacement
  experiment, with the original partial batch reported separately and on its
  own terms.

Neither case licenses silently replacing unfavourable observations. An ordinary
failed repair stays in its denominator.

## What this will and will not answer

It answers a narrow, valuable question: whether this advantage replicates on
this task, at this rung, with this engine, at a stated power against a stated
effect.

It does **not** establish that Engine is better generally. That needs task
coverage the suite does not have, and this slice should stop being asked to
earn it.

## Out of scope

Additional tasks or rungs; mechanism attribution to any single engine
component; an adoption rule for cost; a confirmation campaign that follows
automatically from any outcome here.
