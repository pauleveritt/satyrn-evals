# Working in this repository

Read `AGENTS.md`, `BRIEF.md`, and `ROADMAP.md` at the start of work. Then
read the named current design and the relevant section of its plan. Do not
preload historical material.

The archive is evidence, never operating guidance. When a concrete question
needs it, search one named area with `rg --no-ignore archive/...`; ordinary
`rg` intentionally excludes it. `archive/README.md` maps original paths and
explains how to recover original line citations.

Keep the executable-command engine seam. Persist an attempt's patch and
transcript before grading or cleanup. Grade from hook-written evidence, never
stdout or exit status; the hook-path spoofing limit is stated in the current
trust-boundaries topic. State denominators and missingness. Make causal claims
only with controls that isolate the proposed cause. Re-score retained evidence
offline. Freeze execution conditions before a budgeted run.

The default test tier uses no model, network, or subprocess. Keep its planted
subprocess tripwire; run marked integration checks when a change needs real
Git, materialization, an attempt command, or an oracle. Give every refusal
test a sibling success test.

Any comparison follows `BRIEF.md`'s comparison policy: declare the outcome and
cost questions before the run, disclose an informed selection rather than hide
it, carry a power figure's test and assumptions, keep checkpoints to execution
integrity, treat outcome-shaped signals as measurements rather than stop
triggers, and never restart from zero by default.

**The instrument is not the work.** Instrument improvement is always
available, always verifiable, and always produces a green gate and a commit,
while finding a pathology is uncertain and often ends in "no change". Left
alone that gradient runs one way, so three rules bind it.

**Currency.** Do not open an investigation on a pathology whose only evidence
predates the shipping revision of the component it targets. Compare the
evidence's recorded digest against `HEAD` **before** measuring — one command.
On 2026-09-09 three consecutive cycles characterised a loop breaker that a
landed commit had already fixed, because nobody ran that command.

**Declare what each piece of work produced**, and cap one of the answers:
*remedy tested live*, *remedy proposed and refused*, or **instrument only**.
**Two consecutive instrument-only pieces stop the loop** and require a live run
before another opens. The overnight run of 2026-09-08/09 was four in a row and
ended with no remedy enabled and none tested.

**Instrument work is a tax, not a product.** It is permitted when it blocks the
measurement in hand, it is recorded as debt rather than as the work's result,
and **if the fix is larger than the measurement it unblocks, stop and ask**.
Each such fix is individually justified; the failure is cumulative, and only a
count catches it.

Optimize development for useful feedback within 10–15 minutes. Start with a
deterministic reproducer, then one bounded attempt, then two attempts per
matched configuration on one relevant qualified task; a broader confirmation
run needs its own plan. Treat small runs as triage, never success-rate or
causal evidence. Declare budgets and stop rules before spending: infrastructure
failure stops remaining launches, while an ordinary failed repair remains a
counted observation. Turn each expensive failure's deterministic component into
a cheap regression test, and measure setup, command, and grading durations
before proposing infrastructure optimization.

Make normal, reviewable changes directly. Do not run model inference or create
commits unless requested. Do not invent a spec or plan for a trivial change;
use a current design and plan when the work needs one. An authorization remains
in force for its stated scope.

Use Sol for iterative implementation reviews and recommendations. Reserve Astra
for a final acceptance review after the focused checks pass, unless the user
explicitly asks for an earlier Astra gate.
