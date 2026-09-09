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
loop-breaker string runs 4.2x). The rule: **never `grep -c`/`-o` a string to count events** — a tool result is
re-streamed in the following message and quoted in model thinking. Count from
the authoritative event for the thing being counted, which is **not one event
type for everything**: a tool's *result* is a top-level `tool_execution_end`,
while the breaker's own firings are `entry_appended` with
`entry.customType == "loop_broken"`, and usage is a settled `message_end`.
Name the event you counted, and carry the recompute command beside the number.

Two neighbouring failures share the symptom and need separate checks: an
**invalid counterfactual replay** (see the entry above) and **uncertain token
semantics** — `usage.output` is the server's `completion_tokens`, and what it
includes is a property of that server, not something a character count can
settle.

**"The night produced commits, green gates, and no tested remedy."**
Every instrument fix was individually justified — each blocked the next
measurement — and the failure was cumulative, so nothing local caught it. Four
consecutive cycles produced parser, preflight, grading and protocol changes and
**zero enabled or tested remedies**. Two contributing causes, both specific:
mining retained evidence can only find pathologies of the code that produced
it, and that code was retired; and a deterministic-reproducer entry gate turns
most candidates into instrument corrections, because building the reproducer
means first proving the instrument reads the evidence correctly. `AGENTS.md`
now carries the currency check, the instrument-only cap, and the tax rule.

**"The waiter never returned and the work had already finished."**
`while pgrep -f "run-batch.sh"; do sleep 30; done` matches the **waiter's own
command line**, which contains the pattern as its argument, so the loop can
never exit. Three such waiters spun for 10–12 hours after their batches
finished, on a machine whose quietness is a stated precondition for unattended
batches. The mirror-image error is guessing a process name that matches
nothing, which returns instantly and looks like success. **Wait on a condition
the work itself produces** — a file appearing, a marker line in a log, a count
of completed cells — not on a process name; `pgrep -f "[r]un-batch.sh"` guards
the self-match but the file check is the right instrument for this job.

For a specific past incident or original line citation, retrieve its record
from [the archive](https://github.com/pauleveritt/satyrn-evals/tree/main/archive/2026-09-07-pre-reset).
