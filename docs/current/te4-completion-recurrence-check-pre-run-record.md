# Pre-run record — TE4 completion-recurrence check

Written 2026-09-11, **before any inference**. Every value below is
frozen at the moment of writing. **This record authorizes no TE4
screen.** Live inference for this record falls under the maintainer's
standing overnight authorization, unchanged from every prior record in
this sequence.

## What this run is for, and what it is not

[Round 2 of the phase-4-guardrail re-verification](te4-phase4-guardrail-reverification-round2-result.md),
corrected after review, produced the first two full completions ever
on this task family (18/18 hidden checks each), after 0 of 11 prior
attempts. Review found the corrected account has no explanation for
*why* these two finished within budget when three earlier attempts
made the identical destructive-edit-then-restore repair and still
timed out — restoring the route is not new, finishing in time is.

**This run asks only whether completion recurs at all, at the current
prompt state, with no further prompt change.** It is not a fifth
tightening, not a new guardrail, and not a claim that whatever caused
these two completions is now understood. Three more Engine attempts,
unchanged configuration, to see whether 2 of 2 was a fluke or the
leading edge of a real, if still low, completion rate.

**Still cannot establish:** a completion rate with any confidence (5
total post-fix phase-4-reaching attempts is not a distribution), a
turn ceiling (2 completions, 43 and 49 turns, is too few to set one
against), or that TE4's own two-per-configuration screen is warranted
— that remains a separate decision, made after this batch, not before
it.

## The arm

**Engine only**, consistent with every phase-4-focused round in this
sequence.

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
| Commit this record is written against | `d57007c` |
| Task tree sha256 | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` (unchanged — no prompt edit since the phase-4 guardrail) |
| `phase-2-board` digest | `362480e8681f118a` (guardrail, unchanged) |
| `phase-4-resolve-reopen` digest | `6c264957e8cdd793` (phase-4 guardrail, unchanged) |

## Run parameters

| Field | Value |
|---|---|
| **n** | **3 Engine attempts** — brings the phase-4-guardrail-era total to 7 phase-4-reaching attempts, the same order of magnitude as the original completion-rate check this replaces the spirit of |
| `--timeout` | 600s, unchanged |
| `turn_budget` / `tool_call_budget` | 20 / 30 (declared, not enforced) |
| `base_revision` | the task tree sha256 above |

## Preconditions

1. Environment materializes at pinned versions — unchanged `base/`.
2. Offline qualification suite (8 tests) passes on the exact commit —
   reconfirm at run time.
3. A live completion, never a `/v1/models` listing.
4. Model identity verified from each transcript's own field.
5. HP1–HP8, TE2/HP8, both guardrails, all four tightenings, and round
   2's corrected result all accepted as written.

## What voids an attempt

Unchanged: refused/unreadable record; model-identity mismatch; a
changed inference setting mid-run; a `check_chain` "implementer window
was never observed" finding.

## What happens after

Report per attempt: completion (with hidden-check counts) or the
specific mechanism it failed by, checked directly against raw tool
calls, never a truthy-`args` filter. For any destructive-edit
occurrence, report explicitly whether it was restored and, if so,
whether self-test ran before or after the restoration — round 2's own
correction showed this distinction matters and is easy to get backwards
without checking. State the completion tally honestly (out of the
cumulative 13 + this batch's 3 = 16), and say plainly whether 2 of 2
looks like it was a fluke, a low but real rate, or something in
between — this batch is still too small to settle that, and the
document should say so rather than reaching past what 3 more attempts
can support. If a turn ceiling is now defensible from the completions
on record, propose one, stating the evidence plainly as thin (2–5
transcripts, not TE1's own six). Get an independent review of this
result before deciding whether TE4's own two-per-configuration screen
is now warranted.
