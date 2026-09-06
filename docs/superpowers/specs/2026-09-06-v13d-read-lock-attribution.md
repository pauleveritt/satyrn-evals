# V13d — what causes the read lock: surface, or engine. Frozen before the first cell.

**Status: frozen 2026-09-06, before any cell runs.** Exploratory,
diagnostic, admits nothing. Post-pin; never pooled with any pre-pin batch.

## 1. The question

V13c recorded Engine producing **no patch in 6 of 12** cells on
`plausible-wrong-fix`, where Baseline scored 12/12. All six surveyed the
tree and then repeated `read app.py` until a terminator fired.

**The cause is unknown.** Two explanations offered for it were refuted by
cells in the same batches, and both refutations are recorded
(`~/satyrn-smokes/2026-09-06-v13c-200158/RESULT.md`, correction block): the
breaker does not cost the patch — **0 of 8** bare-Pi cells reaching a read
run of >=5 before any edit ever edited — and the missing test runner is not
the trigger, since Baseline's lock cells run `pytest` as their *second*
call and lock anyway, while locking 5/12 on `misleading-locus` against
Engine's 0/12.

What remains are three candidates that differ between the arms: the **tool
surface** (`read,edit` versus four tools), the engine's **wrapper prompt**
(`satyrn-engine/src/satyrn_engine/attempt.py:260-270`), and the breaker's
**injected message**. This batch separates the first from the other two.

**Envelope is the control.** It is bare Pi on Engine's exact tool surface,
with no engine code, no wrapper prompt and no breaker. If the surface
causes the lock, Envelope locks like Engine. If it does not, Envelope locks
like Baseline and the cause is engine-side.

## 2. Design, frozen

- Arms `arms/baseline.json`, `arms/envelope.json`, `arms/engine.json`,
  **interleaved** on a seed recorded before the first cell.
- Task `agentclinic-repair-plausible-wrong-fix`, rung **R1**,
  `omlx/gemma-4-12B-it-MLX-8bit`, **`n=12` per arm — 36 cells.**
- `--max-repeated-calls 10` on for every arm; temperature 1.0 verified on
  both sides; engine pinned at `b977941`; one preflight into a fresh
  directory. No V5d smoke owed — every arm's execution path has run today.

## 3. The primary measure, defined before the cells

**A cell is *locked* when its longest run of identical consecutive tool
calls, counted before its first `edit` call, reaches 5 or more.**

This is deliberately **arm-neutral** and independent of which terminator
fires: the pi arms end at evals' `--max-repeated-calls 10`, the Engine arm
at `CONSECUTIVE_BLOCK_LIMIT = 3`, and a cell that locks and is cut at 3 is
still locked. Counting terminators instead of locks would measure the
terminator, not the pathology. Computable from any retained transcript.

Reported beside it, kept separate and never pooled: successful attempts,
retained patches, and cost-to-succeed **in both units** — tool calls and
turn-level `usage` tokens — with the unconditional cost per success.

## 4. The consequence table, predeclared

Reference points: on `plausible-wrong-fix` at `n=12`, V13c locked Engine
6/12 and Baseline 0/12.

| what Envelope's lock rate shows | what it means | what happens next |
|---|---|---|
| **A.** Envelope locks like Engine (>=4/12) | the **tool surface** drives the lock; engine machinery is not implicated | the engine lever is the surface — a runner or a wider surface — and the wrapper prompt and breaker message are exonerated |
| **B.** Envelope locks like Baseline (<=1/12) | the cause is **engine-side**: the wrapper prompt or the breaker's message | the next probe varies one of those two, and no runner work is justified by this evidence |
| **C.** Envelope lands between (2–3/12) | underpowered or mixed | say so; `n=12` distinguishes 0 from 6, not 2 from 4. No mechanism claim either way |
| **D.** Engine does not reproduce 6/12 | V13c's rate was itself a sampling artifact | the finding that started this line is weaker than recorded; say so first, before anything else is read |

**Outcome D is checked before A–C.** If Engine's lock rate does not
reproduce, nothing else in this table means anything.

## 5. Stopping rule

`n` fixed at 12 per arm. No extension after reading, no arm added or
dropped, no change to the lock definition after the first cell. Interrupted
batches resume; incomplete cells are moved aside and logged.

## 6. Limits

- One task, one rung, one model, one sampler value.
- Separates the **surface** from *(wrapper prompt + breaker message)*
  jointly. It cannot tell those two apart; that needs a further probe.
- Envelope carries no engine code at all, so outcome B localises the cause
  to the engine but not to a line of it.
