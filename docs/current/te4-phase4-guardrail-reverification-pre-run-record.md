# Pre-run record — TE4 phase-4-guardrail re-verification

Written 2026-09-10, **before any inference**. Every value below is
frozen at the moment of writing. **This record authorizes no TE4
screen.** Live inference for this record falls under the maintainer's
standing overnight authorization, unchanged from every prior record in
this sequence.

Follows
[the phase-4 guardrail](https://github.com/pauleveritt/satyrn-evals/blob/main/src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md),
applied after independent review found 3 of 4 graded phase-4 attempts
on record destroyed the phase-3 `POST /complaints` route via the same
destructive-edit mechanism phase 2 already carries a guardrail
against. Verified only offline so far.

## What this run is for, and what it is not

**Does the phase-4 guardrail actually stop the route deletion, the
way the phase-2 guardrail stopped the phase-2 runaway?** Both
tightenings 3 and 4 (the `id`-field design) are already validated live
and are not under test here. This run isolates the one remaining named
mechanism with an applied fix not yet tried live.

**Still true, unchanged from every prior record in this sequence:**
this cannot establish completion reliability or turn efficiency; a
clean pass here does not itself authorize TE4's own screen, which
remains a separate decision; a turn ceiling needs more than one or two
clean completions to check against, the same standard TE1 held its own
40 to.

## The arm

**Engine only.** Baseline has never destroyed a route in this task
family across any attempt.

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
| Commit this record is written against | `c12dd05` |
| Task tree sha256 | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` |
| `phase-2-board` digest | `362480e8681f118a` (guardrail, unchanged) |
| `phase-4-resolve-reopen` digest | `6c264957e8cdd793`, 1993 bytes (phase-4 guardrail; was `ef0452709399edba`, 1841) |

## Run parameters

| Field | Value |
|---|---|
| **n** | **3 Engine attempts** — sized like the completion-rate check this replaces, since the question (does the fix hold, and at what rate) is the same shape |
| `--timeout` | 600s, unchanged |
| `turn_budget` / `tool_call_budget` | 20 / 30 (declared, not enforced) |
| `base_revision` | the task tree sha256 above |

## Preconditions

1. Environment materializes at pinned versions — unchanged `base/`.
2. Offline qualification suite (8 tests) passes on the exact commit —
   reconfirm at run time.
3. A live completion, never a `/v1/models` listing.
4. Model identity verified from each transcript's own field.
5. HP1–HP8, TE2/HP8, the phase-2 guardrail, tightenings 1–4, and the
   phase-4 guardrail all accepted as written.

## What voids an attempt

Unchanged: refused/unreadable record; model-identity mismatch; a
changed inference setting mid-run; a `check_chain` "implementer window
was never observed" finding. **Also named, not yet a formal voiding
rule**: a `stopReason: "length"` termination that still produces
gradable output (observed once, tightening-4's Engine-02) is reported
as its own outcome, not silently folded into "rejected" or "voided" —
this record does not decide whether it should void an attempt, only
that it must be named if it recurs.

## What happens after

Report per attempt: completion, or the specific mechanism it failed
by — classified against every named mechanism to date (destructive
route deletion; `id`-before-`agent_name`; `id`-no-default; misplaced
`__post_init__`-style implementation bug; redirect-trap misdiagnosis;
length-capped degenerate repetition) or named as new if it matches
none. If the destructive-edit-on-an-existing-route pattern recurs even
once at this `n`, say so plainly — the guardrail's phase-2 analog
needed adoption once and has held 9 of 9 since; a phase-4 recurrence
after this fix would be a materially different, worse signal than
phase 2's own clean record. If one or more attempts complete cleanly,
propose a practical turn ceiling from what's now on record, stating
its evidence plainly as thin. Get Fable's review of this result before
deciding what comes next, per the standing instruction.
