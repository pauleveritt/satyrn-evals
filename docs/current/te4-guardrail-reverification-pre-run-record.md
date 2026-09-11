# Pre-run record — TE4 guardrail re-verification

Written 2026-09-10, **before any inference**. Every value below is
frozen at the moment of writing. **This record authorizes no
inference and no TE4 screen.** It needs its own separate
authorization.

Follows
[the guardrail's adoption](../../src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md)
into `agentclinic-complaint-lifecycle`'s own phase-2-board prompt
(commit `3e6ad02`). Two gaps remain that the candidate probe did not
close, because it was a bounded two-phase task built only to test the
phase-2-board mechanism:

1. **No Engine attempt has ever reached phase 4 on this task.** The
   [route proof](te4-route-proof-result.md) voided at phase-2-board
   before the guardrail existed; the
   [candidate probe](phase2-guardrail-candidate-result.md) only ran
   phases 1–2 on a separate task. Phase 4 (resolve/reopen) is entirely
   unproven live, on either route.
2. **No practical shared turn ceiling exists for this task.** The
   route proof explicitly declined to propose one — Engine had
   completed the task zero times. That is still true until an Engine
   attempt completes all four phases.

## What this run is for, and what it is not

**Does Engine now complete the full, guardrail-amended task, and what
do real phase-3/phase-4 turn counts look like?** Narrow questions,
answered by attempts, not a designed comparison.

**This run cannot establish, and no reading of it may claim:**

- Anything about completion reliability or turn efficiency — that is
  TE4's own two-per-configuration screen, separately authorized, and
  this run's counts stay outside its denominator.
- That the guardrail is proven in general. The candidate probe already
  gave phase-2-board evidence (3 of 3 clean, mechanism confirmed); this
  run extends that to phases 3–4 and the full chain, it does not
  re-litigate phase 2.
- A turn ceiling from `n < 2` completions, the same standard TE1 held
  its own 40 to (checked against multiple real transcripts, not
  asserted from one).

## The arm

**Engine only.** Baseline already has two relevant, clean data points
under this exact prompt text: the original [route
proof](te4-route-proof-result.md)'s Baseline-01 (all 4 phases, 28
turns, pre-amendment prompt — the guardrail sentence is generic
instruction-following text, not an Engine-specific tool constraint,
and Baseline was already exposed to it with no effect) and the
candidate probe's own Baseline-01 (phases 1–2, 17 turns,
post-amendment, clean). A third Baseline run would confirm rather than
discover; skipped for cost, not because it's unimportant — a fresh
Baseline reference stays available if this record's own author wants
one before TE4's screen.

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
| Commit this record is written against | uncommitted fix to `QUALIFICATION-NOTE.md`'s own self-referential digest claim, on top of `3e6ad02` |
| Task tree sha256 (post-guardrail, post doc-fix) | `e4791eca47b231e2d54e39cedb9312d14c054088402e5b43b871887c7768de3b` |
| `phase-2-board` prompt digest | `362480e8681f118a`, 1774 bytes (the adopted guardrail, unchanged since the candidate) |

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

Note: this digest sweeps the whole task directory, including
`QUALIFICATION-NOTE.md` — it will differ from every earlier record's
figure for this task each time that file is edited, by design (nothing
in the directory should drift invisibly). The `phase-2-board` prompt
digest above is the one that actually reaches the model and is the one
to check against prior records.

## Run parameters

| Field | Value |
|---|---|
| **n** | **2 Engine attempts** (proposed; adjust before authorizing) |
| `--timeout` (`deliver`, `pi_implementer`) | 600s, matching every prior record |
| `turn_budget` / `tool_call_budget` | 20 / 30 (declared, not enforced, unchanged) |
| `base_revision` | the task tree sha256 above |

## What this run retains

The real `ChainRecord` per attempt
(`run_and_record_engine_chain`), via `scripts/hp7_live_route.py --task
agentclinic-complaint-lifecycle --task-tree-sha256 <above>`. Turn
counts computed post-hoc via `turn_ledger.count_turns` from the real
retained transcripts, per phase and whole-attempt, the same
reconciliation every prior record in this family used.

## Preconditions

1. Environment materializes and imports at pinned versions — already
   confirmed for this `base/` (unchanged since the route proof).
2. The offline qualification suite (8 tests) passes on the exact
   commit this run starts from.
3. A live completion, never a `/v1/models` listing.
4. Model identity verified from each transcript's own field, after
   each attempt.
5. HP1–HP8 acceptance, the TE2/HP8 screen's result, and the guardrail's
   adoption all accepted as written — already true.

## What voids an attempt

Same rule as every prior record: a refused/unreadable retained record;
a transcript-observed `message.model` mismatch; an inference setting
changed mid-run; or a `check_chain` finding of "implementer window was
never observed" — reported as voided, with the transcript's actual
retention stated plainly, not conflated with "no evidence exists."

## What happens after

Report per attempt: completion (all four phases, or where it stopped
and why), and whole-attempt plus per-phase turn counts via
`turn_ledger`, with particular attention to phases 3 and 4 since
neither has any prior Engine data point on this task. If both attempts
complete, propose (not declare) a practical shared turn ceiling for
TE4, stating exactly what evidence it rests on — the same discipline
TE1 held itself to. If completion is mixed or the sample still looks
arbitrary to build a ceiling from, say so rather than picking a number
anyway. Do not propose or begin TE4's own two-per-configuration screen
from this result without saying so explicitly and getting separate
authorization.
