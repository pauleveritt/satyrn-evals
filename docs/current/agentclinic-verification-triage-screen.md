# Triage screen — the verification instruction, four sessions

Written 2026-09-09, **before any inference**. Frozen at writing.

## What this is, and what it deliberately is not

A **matched triage screen**: two attempts per configuration, per this repo's
development feedback policy, which calls for exactly that before any
separately planned confirmation run (`BRIEF.md`, "Development feedback
policy"). Four sessions total.

An earlier draft of this proposal was a 48-session, ~3¼-hour powered screen
at n=24/arm. That was **the wrong experiment**: it had quietly become a
success-rate confirmation study, which is a different question from the one
in front of us and one this screen has not yet earned. The power arithmetic
was correct and its use was not. Recorded because the drift was the error,
not the numbers.

**No power calculation applies here, and none is claimed.** Four sessions
cannot estimate a rate. This screen exists to decide whether the instruction
is *operationally useful* and whether further investigation is warranted —
not to announce an improvement.

## Conditions

Two prompt conditions. **Not** Engine versus Baseline: no Engine session arm
exists, and nothing here can speak to that comparison in either direction.

| | Control | Verification |
|---|---|---|
| Spec | `session-control.json` | `session.json` |
| Spec sha256 | `16c72870b9732e22…` | `1b0139140b357138…` |
| phase-1-home prompt | `4b143eed93f721d6` | `9238e5d3a1265a6c` |
| phase-2-board prompt | `2bbeb2c9d882bf99` | `8bc6457681df6448` |
| phase-3-add prompt | `882ed2b11e6b66da` | `6fcfd29df448f013` |

The conditions differ by exactly one sentence, appended to the shared
preamble in the Verification condition:

> Before finishing, run `uv run python -m pytest tests`. Address failures
> caused by your changes without weakening tests, and report the command and
> result.

Character-exact equivalence otherwise is enforced by
`test_the_two_prompt_conditions_differ_only_by_the_verification_sentence`,
proven to fail when a tightening is weakened in one condition alone. Both
conditions use the **repaired adapter** (the harness `VIRTUAL_ENV` no longer
reaches the model's shell) and the **corrected preamble** (which no longer
claims a pre-installed environment while forbidding installation), so the
screen varies the instruction rather than a mixture of the instruction and
this week's repairs.

## Frozen run parameters

| Field | Value |
|---|---|
| Model | `omlx/gemma-4-12B-it-MLX-8bit`, provider `omlx` |
| Tools | `read,bash,edit,write` |
| Arm record | `arms/baseline.json` |
| Sessions | **4 total: 2 control, 2 verification** |
| `--step-timeout` | 600s |
| Task tree sha256 | `3e6607e533792ab0b6b77a695a2bd13966922378a79139899356a9474fbdbfca` |
| Repo commit | recorded per session in the run manifest |

**Predeclared order**, fixed before any session runs, alternating so that
machine drift cannot align with condition:

1. control
2. verification
3. verification
4. control

**No extension after reading.** Four sessions, and the screen ends. If the
result argues for a confirmation run, that is a separately planned and
separately frozen experiment, and these four sessions stay outside its
denominator.

## Per-session provenance, recorded because the record does not carry it

`SessionRecord` stores `adapter_command` but **not** the selected spec
filename or its digest (`src/satyrn_evals/session.py:329`). For this screen
that gap is closed by hand, not by new machinery: the run manifest
`RUN-MANIFEST.json`, written in the output directory before each session,
records for every session its ordinal, assigned condition, spec filename,
spec sha256, the three expected prompt digests, the exact command, and the
repo commit.

**Afterwards each session's retained transcript prompt digests are verified
against the manifest's expected digests.** A session whose prompts do not
match its assigned condition is void and reported as void — never
reassigned, and never quietly counted under whichever condition it turns out
to match.

## What is inspected

Not a success rate. Four named questions, decided before the data:

1. **Does the model execute verification after its final edits?** In which
   phases, how many times, and — the point of "after" — whether the run
   comes *last*, or before further edits that then go unverified.
2. **If tests fail, does it repair the application without weakening
   tests?** Checked against the retained checkpoint patches: a removed or
   loosened assertion is the failure mode this clause exists to guard.
3. **Cumulative correctness** per checkpoint: 4 / 10 / 13.
4. **Cost**: turns, tool calls, compaction events, elapsed seconds per phase.

## What this screen cannot establish, stated before the data

- **A session in which nothing fails does not exercise recovery.** If no test
  fails in any verification session, question 2 is unanswered, and the
  "without weakening tests" clause remains untested rather than validated.
- **A successful instructed session does not show the instruction improved
  correctness.** Two sessions per condition cannot separate an effect from
  the pair of trajectories that happened to occur.
- A non-significant or mixed result **does not establish equivalence** — and
  is not therefore uninformative. The observations and their uncertainty are
  the output; no significance claim is available at this size, and none will
  be made.

## Duration

The two retained sessions summed to roughly 2.34 and 2.83 minutes of phase
execution. Four comparable sessions imply about 10 minutes of phase time;
with materialization, grading and variability, **15–25 minutes** is the
planning estimate. That is not a cap: three 600s phase limits permit up to 30
minutes per session before overhead, and a session that hits them is an
outcome to report, not an overrun to trim.

## Preconditions

As in the prior records: environment verified at the pins; a clean tree with
the commit recorded; a **live completion** rather than a `/v1/models`
listing; and model identity read from each transcript's own `message.model`
field after the run.
