# Pre-run record — TE4 tightening-3 re-verification

Written 2026-09-10, **before any inference**. Every value below is
frozen at the moment of writing. **This record authorizes no
inference and no TE4 screen.** It needs its own separate
authorization.

Follows
[tightening 3](../../src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md)
(commit `c494297`), which closed the `id`-field-ordering ambiguity
[the prior re-verification](te4-guardrail-reverification-result.md)'s
Engine-01 fell into. That tightening has been verified only offline —
re-graded against the existing fixtures and against Baseline-01's own
already-retained solution. **It has never been tried live.**

## What this run is for, and what it is not

**Does the tightened phase-4 prompt actually change Engine's outcome,
and can Engine complete the full four-phase task at all?** Across
every Engine attempt on this task family to date (route proof,
guardrail candidate's 2-phase probe, prior re-verification), Engine
has completed the full task **zero times**. This run is not designed
to raise that to a confident rate — it is designed to find out whether
one clean completion is even reachable now that both known frictions
(the phase-2-board runaway, the phase-4 field-ordering ambiguity) have
been addressed.

**This run cannot establish, and no reading of it may claim:**

- Completion reliability or turn efficiency — TE4's own
  two-per-configuration screen, separately authorized, is what would
  answer that, and this run's counts stay outside its denominator.
- That Engine-02's redirect-trap misdiagnosis (the prior
  re-verification's other phase-4 failure) is fixed. Nothing was
  changed for it — it was named as legitimate harder-roadmap friction,
  not a defect, and this run may or may not reproduce something like
  it. A recurrence is not a "tightening 3 failed" finding; a recurrence
  of the *id-ordering* failure specifically would be.
- A turn ceiling from fewer than the completions TE1 held its own 40
  to — checked against multiple real transcripts, not asserted from
  one or two.

## The arm

**Engine only**, same reasoning as the prior re-verification: Baseline
has never shown either friction (its own phase-4 solution already
placed `id` correctly, unprompted, and its redirect-aware tests have
never needed the fix Engine-02 missed). A fresh Baseline run would
confirm, not discover.

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
| Commit this record is written against | `c494297` |
| Task tree sha256 | `ccca3262a999b8aae5f9d8ca31935c700fe06ba3b08c2239e644004ef00d0e3a` |
| `phase-2-board` prompt digest | `362480e8681f118a`, 1774 bytes (guardrail, unchanged since adoption) |
| `phase-4-resolve-reopen` prompt digest | `1fc4d9d0e3ed4586`, 1753 bytes (tightening 3, unchanged since applied) |

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

As before, this sweeps `QUALIFICATION-NOTE.md` too, so it will differ
the next time that file is edited — the two prompt digests above are
the ones that actually reach the model and are stable across doc edits.

## Run parameters

| Field | Value |
|---|---|
| **n** | **2 Engine attempts** (proposed; adjust before authorizing) |
| `--timeout` (`deliver`, `pi_implementer`) | 600s, matching every prior record |
| `turn_budget` / `tool_call_budget` | 20 / 30 (declared, not enforced, unchanged) |
| `base_revision` | the task tree sha256 above |

## What this run retains

The real `ChainRecord` per attempt, via `scripts/hp7_live_route.py
--task agentclinic-complaint-lifecycle --task-tree-sha256 <above>`.
Turn counts computed post-hoc via `turn_ledger.count_turns`, per phase
and whole-attempt, the same reconciliation every prior record used.

## Preconditions

1. Environment materializes and imports at pinned versions — confirmed
   unchanged for this `base/`.
2. The offline qualification suite (8 tests) passes on the exact
   commit this run starts from — reconfirmed at the time of writing
   this record.
3. A live completion, never a `/v1/models` listing.
4. Model identity verified from each transcript's own field, after
   each attempt.
5. HP1–HP8 acceptance, the TE2/HP8 screen's result, the guardrail's
   adoption, and tightening 3 all accepted as written — already true.

## What voids an attempt

Same rule as every prior record: a refused/unreadable retained record;
a transcript-observed `message.model` mismatch; an inference setting
changed mid-run; or a `check_chain` finding of "implementer window was
never observed" — reported as voided, with the transcript's actual
retention stated plainly.

## What happens after

Report per attempt: completion (all four phases, or where it stopped
and why), and whole-attempt plus per-phase turn counts via
`turn_ledger`. Explicitly classify any phase-4 failure against the two
already-named mechanisms (id-ordering; redirect-trap misdiagnosis) or
name it as a third, distinct mechanism if it's neither. If at least one
attempt completes all four phases cleanly, propose (not declare) a
practical shared turn ceiling, stating exactly what evidence it rests
on. If neither completes, say so plainly rather than treating two more
data points as if they settled the question — this is still a small
sample, and the honest report may be "still don't know, here is what
changed." Do not propose or begin TE4's own two-per-configuration
screen from this result without saying so explicitly and getting
separate authorization.
