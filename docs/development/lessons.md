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

For a specific past incident or original line citation, retrieve its record
from [the archive](https://github.com/pauleveritt/satyrn-evals/tree/main/archive/2026-09-07-pre-reset).
