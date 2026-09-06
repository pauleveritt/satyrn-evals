# V13c — suite inventory, post-pin, on two axes. Frozen before the first cell.

**Status: frozen 2026-09-06, before any cell runs.** Exploratory. Admits
nothing and compares nothing to a pre-pin batch.

## 1. Why

The suite's headroom inventory — "four of six tasks carry no information"
— rests entirely on the V12 placement profile, which ran at **`n=6`**, the
size V13b showed is unreliable: `depth-2` Baseline read 3/6, 7/12, 2/6 and
7/12 across four batches. A `6/6` at `n=6` is consistent with a true rate
of 0.8, which reads 9–10/12 and is not a ceiling.

And V13b established a **second axis**: on the same 48 cells, the outcome
contrast was p = 0.333 while **cost-to-succeed** — tool calls on cells
that passed — separated the arms at p = 0.00009 and 0.00017. A count per
cell carries far more information than a pass/fail bit.

So this batch re-measures the three remaining runnable tasks on **both**
axes before any new task is authored.

## 2. Design, frozen

- Tasks: `agentclinic-repair-plausible-wrong-fix`,
  `agentclinic-repair-depth-3`, `agentclinic-repair-framing-2-edit`, rung
  **R1**, `omlx/gemma-4-12B-it-MLX-8bit`. `framing-2` stays excluded — its
  known-good patch creates a file and creation-capable capture is owed.
- Arms `arms/baseline.json` and `arms/engine.json`, **interleaved**,
  `n=12` per arm per task. **72 cells.**
- `--max-repeated-calls 10` on for every arm; one preflight per task into a
  fresh directory; temperature 1.0 verified on both sides.
- Engine pinned at `b977941`. No engine change since V13b.
- **No V5d smoke owed:** the execution path is byte-identical to V13b's.

## 3. What is measured, and kept separate

Three quantities, never pooled into one number (V5a rule):

1. **successful attempts** per arm;
2. **retained patches** per arm;
3. **cost-to-succeed** — tool calls per cell, **on passing cells only**,
   reported as a distribution with its median. This is *conditional on
   success* and must always be labelled so; it says what a win costs, not
   how often you win.

Tool calls are counts, not wall-clock. **No wall-clock figure is compared
between arms** (`BRIEF.md`).

## 4. The consequence table, predeclared

| what a task shows | what it means | what happens next |
|---|---|---|
| **A.** an arm strictly inside 0–12 **or** a cost separation | the task carries information | it stays in the inventory, on whichever axis it earned |
| **B.** both arms at 0/12 or both at 12/12 **and** overlapping cost distributions | it carries nothing at this rung | drop it from the inventory and record the `n=12` reading beside the old `n=6` one |
| **C.** a task the `n=6` profile called saturated that is not | the inventory was an artifact of sample size | say so plainly; the suite is wider than believed and fewer new tasks are owed |
| **D.** a failure class absent from V13/V13a/V13b | unknown | classify verdict-counts vs diagnostic-only before reading anything |

## 5. Stopping rule

`n` fixed at 12 per arm per task. No extension after reading, no task added
or dropped after the first cell. Interrupted batches resume; incomplete
cell directories are moved aside and logged.

## 6. Limits

- One rung, one model, one sampler value. Cost-to-succeed on a task with
  very few successes is a distribution over very few cells and must be
  reported with its `n`, not as a median alone.
- `depth-3` recorded 0/6 with 6/6 patches at `n=6` — a quality floor. If it
  stays at 0/12 it carries no outcome information, but its cost
  distribution may still be readable and its failure shape is already
  named.
