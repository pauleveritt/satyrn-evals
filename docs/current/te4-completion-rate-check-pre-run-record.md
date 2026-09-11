# Pre-run record — TE4 completion-rate check

**Superseded, 2026-09-10, before its second and third attempts ran.**
This record's premise — no prompt change needed, the remaining
failures are ordinary variance — rested on a mischaracterization an
independent review caught: 3 of 4 graded phase-4 attempts on record
destroy the phase-3 route via phase 2's own former destructive-edit
mechanism, not "variance." See
[the tightening-4 result](te4-tightening4-reverification-result.md)'s
correction and resolution, and the task's own
[`QUALIFICATION-NOTE.md`](../../src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md),
"The phase-4 guardrail." Attempt 1 of this record's own 3 (launched
before the reopening) completed and is retained as the third
confirming occurrence; attempts 2 and 3 were not run against this
now-superseded prompt state. A fresh pre-run record covers the
guardrail's own re-verification.

Written 2026-09-10, **before any inference**. Every value below is
frozen at the moment of writing. **This record authorizes no TE4
screen.** Live inference for this record falls under the maintainer's
standing overnight authorization ("free use of the GPU... keep working
through TE... don't ask me questions"), unchanged from the two prior
records in this sequence.

Follows
[the tightening-4 re-verification](te4-tightening4-reverification-result.md):
both id-field ambiguities (position, then default) are closed and
validated live. The two most recent failures — a misplaced
`__post_init__`; a dropped phase-3 route on a whole-file rewrite — were
judged genuine implementation variance, not prompt gaps, and no fifth
tightening was applied.

## What this run is for, and what it is not

**No prompt change this time.** This run asks a different question
than every prior record in this sequence: not "what specific mistake
is Engine making," but "at what rate, if any, does Engine complete
this task now that the diagnosed prompt gaps are closed." Six prior
attempts (across the guardrail and both tightening rounds) are 0 for 6
on full completion — but each failed for a different, increasingly
ordinary reason, not a repeated structural block. This batch is sized
to see whether a nonzero completion rate is reachable at all, not to
establish what that rate is with any statistical confidence.

**This still cannot establish:**

- Completion reliability or turn efficiency in the sense TE4's own
  two-per-configuration screen would need — that screen, if warranted
  after this, needs its own frozen design and remains a separate
  decision.
- That implementation-variance failures (a misplaced method, a dropped
  route) are "solved" — they are not prompt gaps to close, and this
  run does not attempt to prevent them; it only checks how often they
  occur at all across attempts free of the two closed gaps.
- A turn ceiling from fewer completions than TE1's own six-transcript
  check for the 3-phase task.

## The arm

**Engine only** — Baseline has never needed any of this task's
tightenings and has already completed phase 4 cleanly (the original
route proof's Baseline-01, before the kw_only grader fix even landed).

| Field | Value |
|---|---|
| Route | `engine_command_implementer`/`run_and_record_engine_chain` |
| Adapter | `satyrn-evals-implementer-pi` |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` |
| Tools | `read,write,edit` + `run_self_test` |
| pi | `0.85.1` |
| Context / max tokens / compaction / temperature | 80000 / 8192 / enabled, 16384 / 1.0 |

## The task

| Field | Value |
|---|---|
| Task | `agentclinic-complaint-lifecycle` |
| Commit this record is written against | `001e6d6` |
| Task tree sha256 | `a0a90054934b9bc520ad387f8ad0cc4f979abeb10f9446fdfb764c218fa25ac3` (unchanged since tightening 4 — no prompt edit this round) |
| `phase-2-board` / `phase-4-resolve-reopen` digests | `362480e8681f118a` / `ef0452709399edba`, both unchanged |

## Run parameters

| Field | Value |
|---|---|
| **n** | **3 Engine attempts** — larger than the prior two-attempt rounds, since the question this time is a rate, not a single mechanism |
| `--timeout` | 600s, unchanged |
| `turn_budget` / `tool_call_budget` | 20 / 30 (declared, not enforced) |
| `base_revision` | the task tree sha256 above |

## Preconditions

1. Environment materializes at pinned versions — unchanged `base/`.
2. Offline qualification suite (8 tests) passes on the exact commit —
   reconfirmed at time of writing.
3. A live completion, never a `/v1/models` listing.
4. Model identity verified from each transcript's own field.
5. HP1–HP8, TE2/HP8, the guardrail, and tightenings 1–4 all accepted
   as written.

## What voids an attempt

Unchanged: refused/unreadable record; model-identity mismatch; a
changed inference setting mid-run; a `check_chain` "implementer window
was never observed" finding — reported as voided, transcript retention
stated plainly.

## What happens after

Report per attempt: completion or the specific mechanism it failed by
(classified against the four now-named mechanisms — runaway;
id-before-agent_name; id-no-default; misplaced-`__post_init__`/dropped-route-style
implementation variance — or named as new if it matches none). If one
or more attempts complete cleanly, propose a practical turn ceiling
from what's now on record and say plainly this is a screen-sized
sample, not a confirmation. If none complete, report the completion
rate honestly as still zero across nine attempts and say what that
means for whether TE4's own screen is worth proposing next, rather
than running further batches hoping for a different outcome. Get
Fable's review of this result before deciding what comes next, per the
standing instruction.
