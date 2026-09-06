# V13a — engine-fix verification spike, frozen before the first cell

**Status: frozen 2026-09-06, before any cell runs.** Exploratory. **Not a
preregistration and not a claim.** V13's preregistration is frozen and read
out; nothing here extends it, and **V13a cells are never pooled with V13
cells**.

## 1. The question

V13 recorded a null with the Engine arm crippled by its own edit tool: 973
schema-refused calls, five of twelve cells lost to the deadline
(`~/satyrn-smokes/2026-09-06-v13-143343/RESULT.md`). Engine `f5d1c62` fixed
that. Two things are unknown:

1. **Is the refusal loop gone?**
2. **Where does the Engine arm sit when it can actually edit?**

Not asked: which component of Engine is responsible for any difference, and
whether any task is admissible. This spike admits nothing.

## 2. Design, frozen

- **Arms:** `arms/baseline.json` and `arms/engine.json`, **interleaved**
  within each batch on a seed recorded before the first cell. Counts are
  only compared **within** a batch — never against V12's or V13's
  previously-run counts, which are a different batch at an unpinned
  temperature.
- **Envelope is not run.** It answered its question in V13 and would cost a
  third of the budget for nothing.
- **`n = 6` per arm per task.** Two tasks — `agentclinic-repair-depth-2` and
  `agentclinic-repair-misleading-locus` — at rung **R1**, model
  `omlx/gemma-4-12B-it-MLX-8bit`. **24 cells total.**
- **`--max-repeated-calls 10` on for every arm**, as in V13.
- One preflight per (task) batch into a fresh output directory; check 0c
  must see both arms with identical `inference` blocks.
- One uncounted **V5d smoke** on the fixed engine path before the first
  budgeted cell — the execution path materially changed.
- The engine pin is bumped to `b977941` for **the schema fix alone**, so any
  movement is attributable to one change. The rejected refusal breaker was
  never built.

## 3. The consequence table, predeclared

Read on **successful attempts** and on **the count of schema-refused edit
calls**, which are separate questions.

| what the cells show | what it means | what happens next |
|---|---|---|
| **A.** zero schema refusals, Engine ≥ Baseline on either task | the fix worked and Engine is competing | the arms are comparable again; suite-headroom work proceeds on real bands |
| **B.** zero schema refusals, Engine < Baseline on both tasks | the fix worked and Engine loses for some other reason | read the transcripts for the shape before changing any code; **do not fix blind** |
| **C.** schema refusals still present | the fix is incomplete | stop, re-diagnose from the transcripts; no further engine change until the cause is named |
| **D.** a failure class not seen in V11c or V13 | unknown | record it, classify verdict-counts vs diagnostic-only, and do not read the comparison until it is classified |

Outcome A is not a win for Engine and B is not a loss for it: `n=6` per arm
on two tasks carries no significance threshold, and none is computed. These
are directions, and they decide **what to look at next**, not what is true.

## 4. Stopping rule

`n` is fixed at 6 per arm per task. **No extension after reading the
result.** No task is added, dropped or swapped after the first cell. If a
batch is interrupted, completed cells stand, an incomplete cell directory is
moved aside and re-run, and the move is logged.

## 5. What voids a batch

A tally that does not accept the set; a transcript whose own
`message.model` is not `gemma-4-12B-it-MLX-8bit`; a preflight that did not
run into a fresh directory; an engine tree that is not `b977941`; or a
machine-state failure (a GPU out-of-memory is `MODEL_ERROR` after the fact,
and is voided, not scored).

## 6. Known limits, stated before the counts

- **Temperature is still unpinned** for every arm, so this batch is
  internally comparable and not reproducible across time. Same limit V13
  recorded.
- **Two tasks, one rung, one model.** All this suite's reference-arm
  headroom sits here; that is why these two, and it is also why the result
  generalizes to nothing else.
- **`misleading-locus` already recorded Engine 10/12 on the defective
  commit** (V11c), so a high Engine count there is partly a re-measurement
  of a known point, not fresh information. `depth-2` is where the loop
  occurred and is the informative task.
