# Why Satyrn Evals

An engine can make a plausible code change without actually solving the task.
It can edit the wrong file, lose track of the requested behavior, or finish a
run that never produced a trustworthy test result. Looking only at a command's
exit code—or only at a patch—does not tell an engine developer what to fix.

Satyrn Evals turns one real Python change into a small task with a known base
state and an oracle: the tests that decide whether the change is correct. It
runs an attempt, saves the patch and transcript it produced, and grades that
saved patch offline. The durable receipt says `pass`, `fail`, or
`unavailable`, with the test evidence used to decide.

That evidence is actionable because it answers different next questions:

- A `pass` says the saved patch met the task's oracle.
- A `fail` identifies a completed, gradeable change that did not meet it.
- An `unavailable` result identifies a grading problem rather than pretending
  that a clean process exit proved success.
- A repeated run gives counts of those outcomes, so a contributor can see a
  failure pattern before changing the engine again.

## What Evals deliberately does not do

Evals is not the engine. It invokes an executable attempt command and does not
import engine internals, so a fake command and a real engine occupy the same
slot. It is also not yet a statistical claims system: it records diagnostic
counts rather than claiming a confidence interval or publishing an A/B result.

Those boundaries keep the current work focused on the question an engine
developer has first: *what happened, and what should I inspect next?*

Next: [see one verdict](tutorials/see-one-verdict.md), then learn [why the
result comes from evidence rather than an exit code](topics/trust-boundaries.md).
