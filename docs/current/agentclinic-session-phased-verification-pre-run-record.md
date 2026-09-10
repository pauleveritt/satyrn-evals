# Pre-run record — verification instruction, session 2

Written 2026-09-09, **before any inference**. Values frozen at writing.

Prior run: `~/satyrn-smokes/2026-09-09-session-phased-112550/RESULT.md`.
This run is **not** a repeat of it, and that run is **not** a control for it.

## The hypothesis, and the narrow question this run asks

**Hypothesis (not tested here):** explicit verification before completing each
phase reduces undetected regressions, at an acceptable added cost.

**The question this run asks is only: is the instruction usable?** Does the
model issue the named command, does the command work in the materialized
workspace, and what does compliance cost in turns, tool calls and seconds.

**This run cannot answer whether the instruction improves behaviour**, and no
reading of it may claim so. `n = 1` on each side, one of which was a
discovery run not designed as a control. If the improvement question is worth
answering, it needs a separately frozen matched screen with fresh controls on
both arms, and **this run and the 112550 run both stay outside its
denominator**.

## Why this rather than another unchanged session

The prior session's entire failure was one hallucinated import path:
`from fastapi.form import Form`. Correcting only that line, offline, takes
the hidden checks from 0 executed to **13 passed** and the model's own tests
from a collection error to **3 passed**. The implementation was otherwise
complete. The model had already written the tests that would have caught it,
and never ran them — and **no prompt asked it to**. Every phase's final bullet
says "Write tests in `tests/test_app.py`"; the only "run" in any prompt was
`uvicorn.run`. That is a scaffold gap with a cheap intervention, not a
mystery needing more observation.

## The intervention

One sentence, added to the shared preamble of all three prompts, identical in
each:

> Before finishing, run `uv run python -m pytest tests`. Address failures
> caused by your changes without weakening tests, and report the command and
> result.

The command is **named**, not implied. It is verified to work in a
materialized workspace: against the prior run's checkpoint-3 tree with only
the import corrected, `uv run python -m pytest tests` passes 3/3. Against the
uncorrected tree it exits non-zero at collection with
`ModuleNotFoundError: No module named 'fastapi.form'` — so the command does
expose the defect it is meant to expose.

"without weakening tests" is deliberate: the failure mode of a
verification instruction is a model that deletes or loosens the failing
assertion. Whether it holds is one of the things this run observes.

The execution bound is unchanged at 600s per step.

## Frozen values

| Field | Value |
|---|---|
| Arm | Baseline only (`arms/baseline.json`) — no Engine session arm exists |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` |
| Tools | `read,bash,edit,write` |
| **n** | **1 session**, frozen, not extendable after reading |
| `--step-timeout` | 600s |
| Task tree sha256 | `d70b728ea41e107015a08f12362e227afd48f636aa109517c5b0e8c46ed17116` |
| Prior task digest | `bd9ac2fe0c4aeee280802d4c15c00e152728b0c6a48064996009dd4ec9daab10` (the 112550 condition) |

Prompt digests, all three changed by the preamble edit:

| Step | Digest | Bytes |
|---|---|---|
| `phase-1-home` | `ca0e6305594aa674` | 1502 |
| `phase-2-board` | `b9d0dea8ae021b3c` | 1547 |
| `phase-3-add` | `0f459d2e0b072505` | 1115 |

The two digests distinguish the conditions: any later analysis can tell which
prompt set produced which record without trusting a label.

## What is observed

Reported raw, no ceilings, no thresholds:

- **Did the model run the named command**, in which phases, and how many times.
- **Did the command succeed**, and did the model act on a failure.
- **Did it weaken any test** to make the command pass — checked against the
  retained patch, not inferred from the verdict.
- Turns, tool calls, compaction events, elapsed seconds per phase — the
  compliance cost.
- Correctness per checkpoint, cumulative: 4 / 10 / 13.

## Preconditions

Same four as the prior record, plus one: the named command must work in a
freshly materialized workspace before the run, not only in the prior run's
tree. A prompt naming a command that fails is the same defect class as a
preamble promising an environment that is not installed.

## Precondition results, 2026-09-09

**Named command, in a freshly materialized workspace — PASS with one recorded
caveat.**

- On the **bare skeleton** (base/ only, before the model writes anything),
  `uv run python -m pytest tests` errors: `file or directory not found: tests`.
  The base ships no `tests/` directory by design, and a test asserts it ships
  only `pyproject.toml` and `uv.lock`.
- On a tree where the model has written `tests/test_app.py` — the prior run's
  checkpoint-3 with only the import corrected — the same command **passes
  3/3**.
- On the same tree uncorrected, it exits non-zero at collection with
  `ModuleNotFoundError: No module named 'fastapi.form'`.

So the command works exactly when the instruction says to run it ("before
finishing", by which point the phase's own bullet has asked for tests), and
errors confusingly if run first. That is **not** fixed here — the base
deliberately ships no `tests/`, and inventing one to smooth a prompt would
change the empty-skeleton premise. It is recorded as an **observable**: if the
model runs the command before creating tests and is derailed by the error,
that is a finding about this instruction's wording, not a harness fault.

**A measurement artifact worth recording**, since it nearly entered this
record as a fact: `uv run python -m pytest tests` first appeared to exit 2 on
a passing tree. That was the RTK command wrapper's filtered output reporting
"No tests collected" and returning non-zero, not the command. Unfiltered via
`rtk proxy`, the same invocation reports `3 passed`. **A wrapper's exit code
is not the wrapped command's exit code**, and every command quoted in a prompt
must be verified unfiltered.

The other four preconditions are as in the prior record: the environment
verified at the pins, a clean tree, a live completion rather than a
`/v1/models` listing, and model identity read from the transcript's own field
after the run.
