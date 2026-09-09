# Evidence checks

Use these checks when interpreting a task or result:

- Identify the actual required behaviour, the public feedback, and the hidden
  oracle separately.
- Test known-good, known-broken, and plausible incomplete repairs before
  treating a task as qualified.
- Keep prompt, model, engine, tools, budget, and schedule explicit; changing
  one changes the condition.
- Use a detector across arms only if it can fire meaningfully for every arm.
- Read stopping behaviour from retained transcript evidence, not an attempt
  exit code.

## Indexed by symptom

**"The count looked plausible and was a whole multiple of the truth."**
A transcript is a *streaming* record: the same call and the same usage block
appear in several representations. Counting by matching a field name across
the whole file therefore multiplies. Tool calls first reported for the
2026-09-08 screen were inflated exactly 4x this way, and the same walk inflates
output tokens 5.5x — which is why `scripts/usage_totals.py` exists, with the
trap in its own docstring. **Count tool calls from `tool_execution_start`, one
per call, and read usage with `usage_totals.py`.** A plausible-looking count is
the dangerous case: nothing about 12 reads looks wrong until it is 3.

**"The file was not modified, so the tool did not write it."**
Equal content is not evidence a file was left alone. A `cmp` over a regraded
cell found `receipt.json` byte-equal and it was reported as untouched; its
mtime showed it had been rewritten with identical bytes. **Compare timestamps,
or snapshot before the operation and keep the hashes.** State only what the
retained artifacts prove — an empty log and no retained hashes support no
claim about what a command did or did not write.

**"I replayed the change over the old recordings and got a number."**
An intervention that changes *which events occur* cannot be evaluated by
replaying events recorded under a different intervention. A loop breaker
decides which tool calls execute, so a transcript's call sequence is endogenous
to the breaker that produced it; feeding it to another breaker measures a
counterfactual. The tell, when it happened on 2026-09-09: replaying the
*shipping* breaker — built to refuse less — over transcripts from the older one
produced **1,373 refusals against 532 recorded**. **Compare in lockstep and
stop at the first divergence**, so every decision counted is one both versions
actually faced, and report the result as a prefix agreement rate rather than a
run-level rate.

**"The count looked plausible and was a whole multiple of the truth" — the
rule, not the two fields.** The earlier entry named `tool_execution_start` and
`usage_totals.py`, and a third occurrence followed anyway on 2026-09-08
(`grep -o NO_CHANGE_REQUESTED` gave 466 against 47 real refusals, 9.9x; the
loop-breaker string runs 4.2x). The rule: **count engine messages only from
top-level `tool_execution_end` events, and never `grep -c`/`-o` a string**,
because a tool result is re-streamed in the following message and quoted in
model thinking. Carry the recompute command beside every count.

For a specific past incident or original line citation, retrieve its record
from [the archive](https://github.com/pauleveritt/satyrn-evals/tree/main/archive/2026-09-07-pre-reset).
