# Pre-run record — TE2/HP8 screen

Written 2026-09-10, **before any inference under this record**. Values
frozen at writing. Instantiates the frozen design in
[the TE plan](engine-turn-efficiency-plan.md), TE2–TE3 section ("Decided
2026-09-10: HP8 is this screen"): this is that screen, not a second one.
Budget authorized 2026-09-10, separate from TE1's closure.

## What this screen is for, and what it is not

Decides whether an easy-work *confirmation* (TE3) is worth running. It
does **not** establish superiority — four attempts distinguish a pattern
from a fluke barely better than `n=1` does. No claim about Engine versus
Baseline in general follows from this run regardless of outcome.

**The frozen questions:**

1. Do both configurations complete `agentclinic-session-phased` — every
   phase accepted, cumulative checkpoint preservation intact — at two
   attempts each?
2. Does the packet workflow use fewer total started model turns
   (whole-attempt, TE1's unit) than the continuous session, without
   sacrificing required behavior?

**Required behavior is read from the hidden cumulative checks *and* a
public-quality review** — not the hidden pass count alone. HP7's own
result named a real gap: an accepted chain that quietly dropped public
regression tests between phases
([result](hp7-live-route-proof-result.md), Finding 1). Each attempt's
public test file is diffed phase to phase; a checkpoint that replaces
rather than extends the prior phase's public tests is reported as a
finding regardless of hidden-oracle or completion outcome.

## The two arms

| Field | Baseline | Engine |
|---|---|---|
| Route | `satyrn-evals session`, continuous conversation | `engine_command_implementer`/`run_and_record_engine_chain`, HP3-composed packet route |
| Adapter | `satyrn-evals-session-pi` | `satyrn-evals-implementer-pi` (via `pi_implementer.py`) |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` | same |
| Server model | `gemma-4-12B-it-MLX-8bit` | same |
| Tools | `read,bash,edit,write` (`arms/baseline.json`) | `read,write,edit` + `run_self_test` (added automatically when `self_test_command` is declared, true for this task) |
| pi | `0.85.1` | same |
| Context window / max tokens | 80000 / 8192 | same (pi's own per-model config, not passed as flags — matches HP7's precedent) |
| Compaction | enabled, reserve 16384 | same |
| Temperature | 1.0 | same |

**Not the same tool surface.** Baseline has `bash`; Engine does not, ever
(HP7's own precondition 1). No sentence from this run may compare the two
as if the surface were held constant — the same confound named in both
prior records.

## The task

| Field | Value |
|---|---|
| Task | `agentclinic-session-phased` |
| Task tree sha256 | `1af60a147bcf6459fab39f2f94f75ba96968ae0dbfe1312ee52858d6b1053951` (recomputed 2026-09-10, matches HP7's record, unchanged since) |
| Session spec | `session.json` (default) — the adopted verification instruction, `self_test_command: uv run python -m pytest tests` |

## Run parameters

| Field | Value |
|---|---|
| **n** | **2 attempts per configuration** (4 total), frozen, not extendable after reading |
| `--step-timeout` (Baseline) / `--timeout` (Engine `deliver`, `pi_implementer`) | 600s, matching every prior record's reasoning |
| Engine `turn_budget` / `tool_call_budget` | 20 / 30 (declared in the packet, not enforced — HP7's frozen figures, unchanged) |
| `base_revision` | task tree sha256 above |

## What this run retains, and what it does not

Baseline: the real `SessionRecord` per attempt (`satyrn-evals session`'s
own output). Engine: the real `ChainRecord` per attempt
(`run_and_record_engine_chain`), via `scripts/hp7_live_route.py` invoked
once per attempt with a distinct `--output-dir`.

**Named, not silently carried as parity: `ChainRecord`'s own cost fields
remain unpopulated on the Engine route** ([result doc](hp7-live-route-proof-result.md),
"What this run did not close"). Turn totals for both sides are computed
post-hoc from each attempt's real retained transcript via
`turn_ledger.count_turns`, the same reconciliation TE1 closed with, not
from a cost field neither route populates identically.

## Preconditions, all required before any attempt starts

1. **Environment materializes and imports at pinned versions** —
   `fastapi==0.115.10`, `turbohtml==1.5.0`, `pytest==8.3.4` (HP7 already
   confirmed this against the same unchanged task; reconfirmed here since
   a fresh screen, not a rerun).
2. **A live completion, never a `/v1/models` listing**, at the pinned
   server model.
3. **The machine is acceptable, not asserted silent** — recorded, since
   four real attempts take real wall-clock and no cross-attempt
   wall-clock comparison is claimed regardless.
4. **Model identity from each transcript's own field**, after each
   attempt, never from the requested argv.
5. **HP1–HP7 acceptance** — all accepted 2026-09-10 (`ROADMAP.md`).

## What voids an attempt

A refused/unreadable retained record; a transcript-observed
`message.model` that is not the requested model; an inference setting
that changed mid-screen; or, for Engine, a `check_chain` finding of
"implementer window was never observed." A voided attempt is reported as
voided, not silently excluded or replaced — the screen's own `n=2`
denominator per configuration stays what was frozen above unless a
replacement attempt is itself separately authorized.

## What happens after

Report per configuration: completion (both attempts, one attempt, or
neither), total started turns per attempt (`turn_ledger`, both roles),
and the public-test-quality finding for every attempt regardless of
outcome. State plainly whether the two frozen questions are answered,
contradicted, or inconclusive at `n=2` — this is a screen, not a
confirmation, and no joint statistical decision is computed here. Do not
propose TE3 from a favorable result without saying so is what's being
proposed; do not treat an unfavorable result as license to re-run.
