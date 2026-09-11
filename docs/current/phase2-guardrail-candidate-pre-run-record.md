# Pre-run record — phase-2-board guardrail candidate

Written 2026-09-10, **before any inference**. Every value below is
frozen at the moment of writing. **This record authorizes no
inference.** It needs its own separate authorization, and its
observations stay outside TE4's confirmation and outside every TE
turn-efficiency denominator, per
[the TE plan's Repair Ownership rule](engine-turn-efficiency-plan.md):
"Use a separately authorized bounded candidate screen, keep its
observations outside confirmation, then freeze the adopted behavior
and rerun only the preparation checks affected by the change."

Follows
[the phase-2-board runaway investigation](phase-2-board-runaway-investigation.md),
which found (correlation, not proven causation, across two matched
pairs) that both Engine runaways on record follow a destructive `edit`
deleting the phase-1 home route while adding the phase-2 complaints
route, converging on a file with an unimported name, never caught
because `run_self_test` is never invoked. Investigation also
established (see the same doc, "Candidate remedy") that `edit`/`write`/
`read` are `pi`'s own built-in tools — nothing in this repo can
intercept or wrap them. The only two feasible remedies are a new
advisory tool (optional; the model already had `run_self_test`
available and did not call it during either runaway, undercutting
confidence a second optional tool would fare differently) or a prompt
guardrail. This record tests the guardrail.

## What this candidate is, and what it is not

**A one-sentence addition to phase-2-board's prompt**, telling the
implementer to insert the new route alongside the existing one rather
than replacing it. Built as
`src/satyrn_evals/tasks/agentclinic-phase2-guardrail-candidate/` — a
bounded, two-phase (`phase-1-home`, `phase-2-board`) probe task, not a
permanent fixture in this family. `phase-1-home`'s prompt is
byte-identical to `agentclinic-session-phased`'s own (digest
`9238e5d3a1265a6c`, verified); `phase-2-board`'s prompt is the original
text plus the guardrail bullet, inserted before the existing "Add `GET
/complaints` route" bullet:

> - When adding the new route to `app.py`, insert it alongside the
>   existing `/` route — do not remove, replace, or rewrite the route
>   that already works

The two existing tasks (`agentclinic-session-phased`,
`agentclinic-complaint-lifecycle`) are **untouched** — this candidate
does not amend either accepted task's own frozen prompt, so no
existing pre-run record's prompt digests are invalidated.

**This is not a claim the guardrail should be adopted.** It is a
bounded test of whether it changes phase-2-board's Engine-route
outcome at all. Grading reuses `agentclinic-session-phased`'s own
phase-1/phase-2 hidden checks unchanged — the required app behavior is
identical; only the instruction on how to add the route changed.
Verified offline: `known-good` (= the original checkpoint-2 solution)
scores 10/10, `known-broken` fails the same named check
(`test_complaint_model_contract_is_preserved`) it always has, and the
bare `grade` CLI path accepts/rejects them the same way.

## Why a base rate matters here

Without any intervention, Engine has completed phase-2-board live 2 of
4 times (HP7, TE2/HP8's Engine-02) and run away 2 of 4 times (TE2/HP8's
Engine-01, TE4's Engine-01) — **a 50% base rate**. A single attempt
passing with the guardrail is weak evidence (a coin flip already gets
there half the time); a single attempt running away is still real
evidence the guardrail did not fix it. This does not, by itself, argue
for an underpowered confirmation — it argues for naming the base rate
so nobody reads one pass as proof. This screen is not designed to
reach statistical significance; TE3/TE5-style confirmation design is
not invoked here, deliberately, per its own restriction to TE3/TE5.

## The two arms

Same model, adapters and tool surfaces as every prior record in this
family:

| Field | Baseline | Engine |
|---|---|---|
| Route | `satyrn-evals session` | `engine_command_implementer`/`run_and_record_engine_chain` |
| Adapter | `satyrn-evals-session-pi` | `satyrn-evals-implementer-pi` |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` | same |
| Tools | `read,bash,edit,write` | `read,write,edit` + `run_self_test` |
| pi | `0.85.1` | same |
| Context / max tokens / compaction / temperature | 80000 / 8192 / enabled, 16384 / 1.0 | same |

## The task

| Field | Value |
|---|---|
| Task | `agentclinic-phase2-guardrail-candidate` |
| Task tree sha256 | `702f2acb0e0f31a376486daf6cd64e0960ad558afed72c9ccf9151a635a09965` |
| `phase-1-home` prompt digest | `9238e5d3a1265a6c`, 1579 bytes (verbatim match) |
| `phase-2-board` prompt digest | `362480e8681f118a`, 1774 bytes (original 1622 + the guardrail bullet) |

Recompute the task tree digest:

```
uv run python -c "
import hashlib
from pathlib import Path
t = Path('src/satyrn_evals/tasks/agentclinic-phase2-guardrail-candidate')
h = hashlib.sha256()
for p in sorted(t.rglob('*')):
    if p.is_file():
        h.update(p.relative_to(t).as_posix().encode()); h.update(p.read_bytes())
print(h.hexdigest())
"
```

## Run parameters, proposed — not final until authorized

| Field | Value |
|---|---|
| **n** | **3 Engine attempts, 1 Baseline attempt** (proposed; adjust before authorizing, not after reading a result) |
| `--step-timeout` / `--timeout` | 600s, matching every prior record |
| Engine `turn_budget` / `tool_call_budget` | 20 / 30 (declared, not enforced, unchanged) |
| `base_revision` | the task tree sha256 above |

Baseline's single attempt is a fairness check (does the added sentence
confuse a route that has never failed this phase, 9 of 9 to date), not
a comparison — its own denominator stays separate from Engine's.

## What this run retains

Same as every prior record: the real `SessionRecord` (Baseline) /
`ChainRecord` (Engine, via `scripts/hp7_live_route.py --task
agentclinic-phase2-guardrail-candidate --task-tree-sha256
<above>`), turn counts computed post-hoc via `turn_ledger.count_turns`
from the real transcripts.

## Preconditions

1. Environment materializes and imports at pinned versions —
   confirmed offline already (`fastapi==0.115.10`, `turbohtml==1.5.0`,
   `pytest==8.3.4`, same `base/` as the other two tasks in this
   family).
2. `known-good`/`known-broken` grade as stated above on the exact
   commit this runs from.
3. A live completion, never a `/v1/models` listing.
4. Model identity verified from each transcript's own field, after
   each attempt.
5. HP1–HP8 acceptance and the TE2/HP8 screen's own result accepted as
   written — both already true.

## What voids an attempt

Same rule as every prior record: a refused/unreadable retained record;
a transcript-observed `message.model` mismatch; an inference setting
changed mid-run; or, for Engine, a `check_chain` finding of
"implementer window was never observed" — reported as voided, with the
transcript's actual retention stated plainly (per TE2/HP8's own
correction, voided is not the same claim as unretained).

## What happens after

Report per attempt: whether the destructive-edit-then-runaway pattern
recurred, was avoided, or (for Baseline) whether anything about its
already-clean phase-2-board behavior changed. State plainly this
cannot reach statistical confidence at this `n` against a 50% base
rate — report the raw pattern, not a rate estimate treated as settled.
Do not propose adopting the guardrail in either accepted task's own
prompt without saying so explicitly and getting separate authorization
— that would be amending the treatment, per the TE plan's own Repair
Ownership rule, and needs its own review even if this probe looks
favorable. Do not propose or begin TE4's own screen from this result
either way.
