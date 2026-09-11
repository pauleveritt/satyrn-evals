# Pre-run record — TE4 phase-4-guardrail re-verification, round 2

Written 2026-09-11, **before any inference**. Every value below is
frozen at the moment of writing. **This record authorizes no TE4
screen.** Live inference for this record falls under the maintainer's
standing overnight authorization, unchanged from every prior record in
this sequence.

## What this run is for, and what it is not

[The first round](te4-phase4-guardrail-reverification-result.md),
corrected twice after review, found the phase-4 guardrail's specific
mechanism recurred once in its first live post-guardrail test
(Engine-03) and held once (Engine-01, additive edits, no deletion).
**n=1 each way is not enough to say whether the guardrail changed the
destructive-edit rate at phase 4 at all** — pre-guardrail, the edit
occurred in 3 of 4 graded attempts (75%); this round's own single data
point is 1 of 1. This run adds 2 more attempts specifically to widen
that comparison, not to test anything new.

**Not proposing a fifth prompt change.** The first round's corrected
result also found the `assert response.status_code == 303` redirect
trap (a self-test that doesn't pass `follow_redirects=False`) in 6 of
9 phase-4-reaching attempts, resolved correctly in only 1 — now the
single most frequent recurring phase-4 mechanism on record, more
frequent than the destructive edit ever was. **This is not being
proposed as a sixth tightening.** Every tightening and guardrail so
far closed a *design* ambiguity — what field goes where, what must be
preserved — using only the prompt's own existing vocabulary. Telling
the model how to correctly test a redirect with `TestClient` would be
telling it how to write its own verification, not clarifying what to
build; that crosses the line this sequence has held since tightening 1
between "closing a real, exploited ambiguity" and "writing the
solution for the model." It stays classified as genuine
implementation/testing friction, consistent with how it was classified
the first time it appeared
([the guardrail re-verification result](te4-guardrail-reverification-result.md)).

**Still cannot establish:** completion reliability, turn efficiency,
or a turn ceiling — no attempt on this task family has ever completed.
TE4's own two-per-configuration screen remains a separate, unauthorized
decision.

## The arm

**Engine only**, same reasoning as every phase-4-focused round in this
sequence — Baseline completed this task cleanly once, before the
kw_only grader fix even landed, and has never needed any tightening or
guardrail here.

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
| Commit this record is written against | `2196428` |
| Task tree sha256 | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` (unchanged since the phase-4 guardrail was applied — no prompt edit this round) |
| `phase-2-board` digest | `362480e8681f118a` (guardrail, unchanged) |
| `phase-4-resolve-reopen` digest | `6c264957e8cdd793` (phase-4 guardrail, unchanged) |

## Run parameters

| Field | Value |
|---|---|
| **n** | **2 Engine attempts** — brings the phase-4-guardrail-era total to 5, the same size as the tightening-3 and tightening-4 re-verification rounds, enough to move past a single data point without proposing a new confirmation-sized batch |
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
   phase-4 guardrail all accepted as written, with round 1's
   corrections folded in.

## What voids an attempt

Unchanged: refused/unreadable record; model-identity mismatch; a
changed inference setting mid-run; a `check_chain` "implementer window
was never observed" finding.

## What happens after

Report per attempt: completion, or the specific mechanism it failed
by, checked directly against raw tool calls (not a truthy-`args`
filter — round 1's own bug) — the destructive-route-deletion pattern,
the redirect-trap pattern, or named as new if it matches neither.
Combine with round 1's two phase-4-reaching attempts for a
phase-4-guardrail-era tally out of 4 (destructive edit) and out of 4
(redirect trap), stated as a small sample, not a rate. If the
destructive edit now occurs in most of these 4, the guardrail is not
meaningfully changing phase 4's rate relative to its pre-guardrail 3-
of-4; if it occurs rarely, that is a real, if still thin, signal the
guardrail helps here too, the way it clearly did at phase 2. If any
attempt completes the full task for the first time ever on this task
family, say so plainly and propose a turn ceiling from it, stating the
evidence as thin. Get an independent review of this result before
deciding what comes next.
