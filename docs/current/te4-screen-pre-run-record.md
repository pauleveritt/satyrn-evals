# Pre-run record — TE4 harder-roadmap screen

Written 2026-09-11, **before any inference**. Every value below is
frozen at the moment of writing. Live inference for this record falls
under the maintainer's standing overnight authorization ("free use of
the GPU... keep working through TE").

## What this run is for, and what it is not

Per [the TE plan](engine-turn-efficiency-plan.md)'s TE4 step: "Declare
the practical shared ceiling and run a two-per-configuration screen,
with only necessary route checks for changed execution paths." Every
named blocking ambiguity on this task family is now closed and
verified live: the phase-2 route-preservation guardrail, both
`id`-field tightenings (position, then default), and the phase-4
route-preservation guardrail. Engine has completed the full task
[4 of 16 times](te4-completion-recurrence-check-result.md), with a
characterized (if unresolved) bottleneck: restoring a
destructively-edited route is necessary but not sufficient, and the
remaining failure mode among restorations is running out of time, not
a wrong answer.

**Baseline has never been run against the current prompt state.** Its
only data point on this task
([the route proof](te4-route-proof-result.md)'s Baseline-01) predates
every tightening and both guardrails — a different, now-superseded
task-tree digest. This screen gives Baseline a first fresh attempt
under the conditions Engine has now been tested under repeatedly, not
a re-read of that old result.

**This is a screen, not a confirmation.** Per the plan: "If both pass,
both fail, or no useful contrast appears, report that finding; do not
automatically make the task harder, enlarge the budget, or shop among
variants." Two attempts per configuration cannot establish a
completion rate or turn efficiency for either side — TE1's own
Baseline ceiling needed six transcripts, and Engine's own 4
completions are already thinner than that. This screen's outcome
informs whether TE4's own confirmation (TE5) is worth designing next;
it is not pooled into that confirmation if one follows.

## The arms

| Field | Baseline | Engine |
|---|---|---|
| Route | `satyrn-evals session`, continuous conversation | `engine_command_implementer`/`run_and_record_engine_chain` |
| Adapter | `satyrn-evals-session-pi` | `satyrn-evals-implementer-pi` |
| Tools | `read,bash,edit,write` | `read,write,edit` + `run_self_test` |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` | same |
| pi | `0.85.1` | same |
| Context / max tokens / compaction / temperature | 80000 / 8192 / enabled, 16384 / 1.0 | same |

Same task, same digest, same model, same sampling settings on both
sides — the only declared workflow difference is context continuity
(one continuous session vs. bounded per-phase packets with isolated
worktrees), per the TE plan's own framing of what this comparison
tests.

## The task

| Field | Value |
|---|---|
| Task | `agentclinic-complaint-lifecycle` |
| Commit this record is written against | `d691a92` |
| Task tree sha256 | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` (unchanged since the phase-4 guardrail) |
| `phase-2-board` digest | `362480e8681f118a` |
| `phase-4-resolve-reopen` digest | `6c264957e8cdd793` |

## Run parameters

| Field | Value |
|---|---|
| **n** | **2 attempts per configuration** (4 total), per the plan's own screen size, frozen and not extendable after reading |
| `--step-timeout` (Baseline) / `--timeout` (Engine) | 600s, unchanged from every prior record on this task |
| Engine `turn_budget` / `tool_call_budget` | 20 / 30 (declared in the packet, not enforced) |
| `base_revision` | the task tree sha256 above |

**Declared shared turn ceiling for this screen: 75 whole-attempt
turns.** Grounded in Engine's 4 completions on record (36, 43, 44, 49;
mean ≈43, max 49) — 75 is ≈1.5x the observed max, the same rule TE1
used to set the original 40-turn ceiling from Baseline-only data. This
is explicitly thinner evidence than TE1 had (4 points, not six, and
zero fresh Baseline points to check it against yet) — stated as thin,
not asserted with confidence. A completion beyond 75 turns is reported
as such, not silently folded into "succeeded."

## The commands

```
uv run satyrn-evals session agentclinic-complaint-lifecycle \
  --output ~/satyrn-smokes/2026-09-11-te4-screen-baseline-<NN> \
  --step-timeout 600 \
  -- satyrn-evals-session-pi --provider omlx \
     --model gemma-4-12B-it-MLX-8bit \
     --tools read,bash,edit,write
```

```
uv run python scripts/hp7_live_route.py \
  --output-dir ~/satyrn-smokes/2026-09-11-te4-screen-engine-<NN> \
  --task agentclinic-complaint-lifecycle \
  --task-tree-sha256 773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c
```

## Preconditions

1. Environment materializes at pinned versions — unchanged `base/`.
2. Offline qualification suite (8 tests) passes on the exact commit —
   reconfirm at run time.
3. A live completion, never a `/v1/models` listing.
4. Model identity verified from each transcript's own field.
5. HP1–HP8, TE2/HP8, both guardrails, and all four tightenings all
   accepted as written, with every correction in this sequence folded
   in.

## What voids an attempt

Unchanged: refused/unreadable record; model-identity mismatch; a
changed inference setting mid-run; a `check_chain`/session-record
"window was never observed" finding. A voided attempt is reported and
retained, not silently excluded or replaced.

## What happens after

Report per attempt: completion (with hidden-check counts and turns) or
the specific mechanism it failed by, checked directly against raw tool
calls (never a truthy-`args` filter — a real bug already found twice
in this sequence). Diff public test files phase to phase for both
arms, per HP7's Finding 1 — replacing rather than extending prior
tests is a finding even when the hidden oracle accepts it. State
plainly: did a useful contrast appear, did both configurations
complete, did both fail, or is the result mixed — and whether that
finding, on its own, motivates designing TE5's confirmation next, per
the plan's explicit instruction not to enlarge the budget or shop for
a more favorable task if this screen is inconclusive. Get an
independent review of this result before drawing conclusions.
