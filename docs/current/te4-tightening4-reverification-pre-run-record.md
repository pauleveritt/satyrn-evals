# Pre-run record — TE4 tightening-4 re-verification

Written 2026-09-10, **before any inference**. Every value below is
frozen at the moment of writing. **This record authorizes no TE4
screen.** Live inference for this record is separately authorized —
the maintainer's own instruction: "Time for an overnight to finish TE
without me. You have authorization and free use of the GPU... Keep
working through TE... Don't ask me questions." This is the standing
authorization for every live step this record and its successors take
overnight; each still gets its own frozen pre-run record and result,
per house convention, but does not wait for a fresh go-ahead.

Follows
[tightening 4](../../src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md),
which closed the missing-default gap
[the tightening-3 re-verification](te4-tightening3-reverification-result.md)'s
two Engine attempts both fell into. Verified only offline so far.

## What this run is for, and what it is not

**Does Engine now complete the full four-phase task?** Engine has
completed it zero times across five prior attempts, each failing for a
narrower reason than the last (destructive-edit runaway; `id` before
`agent_name`; `id` with no default). This run checks whether that
narrowing has actually closed the gap or only moved it again.

**Still true, unchanged from every prior record in this sequence:**
this cannot establish completion reliability or turn efficiency (TE4's
own screen, separately authorized, does that); a clean pass here does
not itself justify running that screen — it justifies grounding a turn
ceiling and considering the screen, a separate decision this record
does not make in advance.

## The arm

**Engine only**, unchanged reasoning: Baseline's own phase-4 solution
has never needed any of these three tightenings.

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
| Task tree sha256 | `a0a90054934b9bc520ad387f8ad0cc4f979abeb10f9446fdfb764c218fa25ac3` |
| `phase-2-board` digest | `362480e8681f118a` (guardrail, unchanged) |
| `phase-4-resolve-reopen` digest | `ef0452709399edba`, 1841 bytes (tightening 4; was `1fc4d9d0e3ed4586`, 1753) |

## Run parameters

| Field | Value |
|---|---|
| **n** | **2 Engine attempts** |
| `--timeout` | 600s, unchanged |
| `turn_budget` / `tool_call_budget` | 20 / 30 (declared, not enforced) |
| `base_revision` | the task tree sha256 above |

## Preconditions

1. Environment materializes and imports at pinned versions — unchanged
   `base/`.
2. Offline qualification suite (8 tests) passes on the exact commit
   this run starts from — reconfirmed at time of writing.
3. A live completion, never a `/v1/models` listing.
4. Model identity verified from each transcript's own field.
5. HP1–HP8, TE2/HP8, the guardrail, and tightenings 1–3 all accepted
   as written.

## What voids an attempt

Unchanged: a refused/unreadable record; a model-identity mismatch; a
changed inference setting mid-run; a `check_chain` "implementer window
was never observed" finding — reported as voided, transcript retention
stated plainly regardless.

## What happens after

Report per attempt: completion or where/why it stopped, classified
against the four now-named mechanisms (runaway; id-before-agent_name;
id-no-default; redirect-trap misdiagnosis) or named as a fifth,
distinct one if it matches none. If at least one attempt completes all
four phases, propose a practical shared turn ceiling from what's now
on record. If neither completes, name the mechanism precisely and
propose the next narrowest fix, the same discipline as every step in
this sequence — not a broader rewrite of the phase-4 prompt in one
pass. Get Fable's independent review of this result before proceeding
to whatever comes next, per the standing overnight instruction.
