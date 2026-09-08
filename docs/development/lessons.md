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

For a specific past incident or original line citation, retrieve its record
from [the archive](https://github.com/pauleveritt/satyrn-evals/tree/main/archive/2026-09-07-pre-reset).
