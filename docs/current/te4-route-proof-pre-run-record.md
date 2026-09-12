# Pre-run record — TE4 route proof

Written 2026-09-10, **before any inference**. Every value below is frozen
at the moment of writing. **This record authorizes no inference, no
commit beyond what is already merged, and no screen.** It needs its own
separate budget authorization, apart from
[the TE4 design](te4-harder-roadmap-design.md) and apart from any future
authorization for TE4's own two-per-configuration screen.

**Note, added after this record's own run.** The task's phase-2-board
prompt was amended the same day, after this record's attempts, adopting
[the guardrail candidate](phase2-guardrail-candidate-result.md) — see
the task's own
[`QUALIFICATION-NOTE.md`](https://github.com/pauleveritt/satyrn-evals/blob/main/src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md).
The task tree sha256 and phase-2-board digest below are frozen values
for *this* record's own run and are correct for it; recomputing them
against the current task will not match, by design.

Sibling records this one narrows rather than repeats:
[HP7's live route proof](hp7-live-route-proof-pre-run-record.md) proved
the Engine route itself works, on the 3-phase task;
[the TE2/HP8 screen](te2-hp8-screen-pre-run-record.md) proved both routes
work end to end, also on the 3-phase task. Neither has ever run against
`agentclinic-complaint-lifecycle` — this record is not re-proving the
routes; it is proving this **task** resolves and grades correctly when
driven live through routes already proven, and it is gathering the one
thing the TE plan requires before any ceiling is declared: a real
transcript.

## What this run is for, and what it is not

**Two questions, both narrow:**

1. Does `agentclinic-complaint-lifecycle` materialize, run and grade
   correctly through the real Baseline and Engine adapters — not just
   through `satyrn_evals.grade` called directly, which is all that has
   verified it so far
   ([`QUALIFICATION-NOTE.md`](https://github.com/pauleveritt/satyrn-evals/blob/main/src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md))?
2. What do real per-phase and whole-attempt turn counts look like on
   this 4-phase task, so a practical shared ceiling can be **checked,
   not asserted** — the same standard TE1 held itself to for the
   3-phase task (`engine-turn-efficiency-plan.md`, "The shared
   whole-attempt turn ceiling... checked against every real
   `agentclinic-session-phased` Baseline transcript on record").

**This run cannot establish, and no reading of it may claim:**

- That either configuration reliably completes this roadmap. `n = 1`
  per configuration distinguishes nothing from a fluke; that is TE4's
  own two-per-configuration screen, separately authorized, and this
  run's counts stay outside its denominator.
- Anything about turn *efficiency* — one point per configuration is a
  ceiling input, not a comparison. No sentence from this run may say
  one configuration used fewer turns than the other.
- That the task is a fair **workload**, only that it is a fair
  **fixture** with at least one real transcript behind it. The
  `QUALIFICATION-NOTE.md`'s own "still not established" section names
  this distinction; this run narrows it, does not close it, at `n = 1`.

## The two arms

Identical to [the TE2/HP8 screen's arms](te2-hp8-screen-pre-run-record.md#the-two-arms) —
same model, same routes, same tool surfaces, same confound (Baseline has
`bash`; Engine never does). Restated here so this record is
self-contained:

| Field | Baseline | Engine |
|---|---|---|
| Route | `satyrn-evals session`, continuous conversation | `engine_command_implementer`/`run_and_record_engine_chain`, HP3-composed packet route |
| Adapter | `satyrn-evals-session-pi` | `satyrn-evals-implementer-pi` (via `pi_implementer.py`) |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` | same |
| Server model | `gemma-4-12B-it-MLX-8bit` | same |
| Tools | `read,bash,edit,write` (`arms/baseline.json`) | `read,write,edit` + `run_self_test` (added automatically — this task declares `self_test_command`) |
| pi | `0.85.1` | same |
| Context window / max tokens | 80000 / 8192 | same |
| Compaction | enabled, reserve 16384 | same |
| Temperature | 1.0 | same |

## The task and route

| Field | Value |
|---|---|
| Task | `agentclinic-complaint-lifecycle` |
| Task tree sha256 | `aa19f92e27ecf3c65701bfa2edb1c6a4ad88b316e7a8a9f1d14b618e8cb66480` |
| Session spec | `session.json` — phases 1–3 byte-identical to `agentclinic-session-phased`, phase 4 new |

Recompute the task tree digest:

```
uv run python -c "
import hashlib
from pathlib import Path
t = Path('src/satyrn_evals/tasks/agentclinic-complaint-lifecycle')
h = hashlib.sha256()
for p in sorted(t.rglob('*')):
    if p.is_file():
        h.update(p.relative_to(t).as_posix().encode()); h.update(p.read_bytes())
print(h.hexdigest())
"
```

Phase prompt digests (sha256, first 16 hex, of the exact `objective`/prompt
string), confirming phases 1–3 are unchanged and phase 4 is the only new
one:

| Step | Digest | Bytes |
|---|---|---|
| `phase-1-home` | `9238e5d3a1265a6c` | 1579 |
| `phase-2-board` | `8bc6457681df6448` | 1622 |
| `phase-3-add` | `6fcfd29df448f013` | 1190 |
| `phase-4-resolve-reopen` | `9ae6b35208360017` | 1619 |

The first three digests are byte-identical to HP7's and TE2/HP8's own
records for `agentclinic-session-phased` — recomputing them against that
task confirms it, not just this file's claim.

## Run parameters

| Field | Value |
|---|---|
| **n** | **1 attempt per configuration** (2 total), frozen, not extendable after reading |
| `--step-timeout` (Baseline) / `--timeout` (Engine `deliver`, `pi_implementer`) | 600s, matching every prior record's reasoning |
| Engine `turn_budget` / `tool_call_budget` | 20 / 30 (declared in the packet, not enforced — same figures as HP7 and TE2/HP8, unchanged; this run is part of what would ground a revised number, not assumed to validate the current one) |
| `base_revision` | the task tree sha256 above |

## What this run retains, and what it does not

Baseline: the real `SessionRecord` (`satyrn-evals session`'s own
output). Engine: the real `ChainRecord`
(`run_and_record_engine_chain`), via `scripts/hp7_live_route.py` with
`--output-dir` pointed at this task and `--task agentclinic-complaint-lifecycle`
(the script currently hardcodes `agentclinic-session-phased`'s task name
and digest as frozen constants — **making it accept a task argument
is implementation work this record does not authorize**; either that
change lands first, under its own small review, or a one-off driver
script is written for this run alone and retained alongside its
output).

Same named gap as every prior Engine-route record: `ChainRecord`'s own
cost fields remain unpopulated. Turn totals are computed post-hoc from
each attempt's real retained transcript via `turn_ledger.count_turns`,
the same reconciliation every prior record used, not from a cost field
neither route populates.

## Preconditions, all required before either attempt starts

1. **Environment materializes and imports at pinned versions** —
   `fastapi==0.115.10`, `turbohtml==1.5.0`, `pytest==8.3.4`. Unverified
   live (only verified through `satyrn_evals.grade`'s own scratch
   workspaces so far); confirm before any inference under this record.
2. **The offline qualification suite passes on the exact commit this
   run starts from** —
   `tests/integration/test_complaint_lifecycle_qualification.py`, 8
   tests. A task whose fixtures regressed between writing and running
   this record is not the task this record qualifies.
3. **A live completion, never a `/v1/models` listing**, at the pinned
   server model.
4. **The machine is quiet.** Recorded, not silently assumed; two real
   attempts take real wall-clock, and no cross-attempt or
   cross-configuration wall-clock comparison is claimed regardless.
5. **Model identity from each transcript's own field**, after each
   attempt, never from the requested argv.
6. **HP1–HP8 acceptance, and the TE2/HP8 screen's own result accepted
   as written** — both already true (`ROADMAP.md`).

## What voids an attempt

A refused/unreadable retained record; a transcript-observed
`message.model` that is not the requested model; an inference setting
that changed mid-run; or, for Engine, a `check_chain` finding of
"implementer window was never observed" — the same instrument-gap
condition named in every prior Engine-route record, and the same
caveat TE2/HP8's corrected result applied: the raw transcript may still
be fully retained even when this fires, in which case say so plainly
rather than treating "voided" and "no evidence exists" as the same
claim. A voided attempt is reported as voided, not silently excluded or
replaced.

## What happens after

Report per configuration: whether the attempt completed all four
phases, and the whole-attempt and per-phase turn counts via
`turn_ledger` (both roles). State plainly whether the task materialized
and graded correctly live, or whether anything about it (dependency
resolution, self-test execution, the harness's handling of a fourth
phase) behaved differently from the offline qualification suite's own
proof. **Do not declare TE4's shared turn ceiling from this alone if
either attempt's completion status makes the resulting number look
arbitrary** — say so, and propose the number as a separate, explicit
step the maintainer can accept or adjust, the same way TE1 froze 40
only after stating the evidence it rested on. Do not propose or begin
TE4's two-per-configuration screen without saying so explicitly and
getting separate authorization.
