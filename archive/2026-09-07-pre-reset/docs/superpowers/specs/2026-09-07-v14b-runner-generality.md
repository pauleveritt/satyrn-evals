> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V14b — does the runner help where the work is hard? Frozen before the first cell.

**Status: frozen 2026-09-07, before any cell runs.** Exploratory, admits
nothing, never pooled with a pre-E10 batch.

## 1. The question

The best-measured engine change of 2026-09-06 is the model-invocable test
runner: on `plausible-wrong-fix` the Engine arm went 6/12 to **12/12**,
matching Baseline, replicated on a fresh seed (V13e, V13f). **It was
enabled on exactly one task — the easiest in the suite**, where Baseline
already scored 12/12.

`public_suite` now exists on the four other runnable tasks. **Does the
runner help where the work is hard, or only where it was already easy?**

`depth-3` is the sharpest case: a quality floor at **0/12 for both arms**,
patches produced but none passing. If a runner moves that, it is a
capability change rather than a convenience.

## 2. Design

- Arms `arms/baseline.json` and `arms/engine.json`, **interleaved**, `n=12`
  per arm per task. Baseline is the contemporaneous control and is
  unaffected by the runner — it always had `bash`.
- Tasks: `agentclinic-repair-depth-2`, `agentclinic-repair-depth-3`,
  `agentclinic-repair-misleading-locus`, rung **R1**,
  `gemma-4-12B-it-MLX-8bit`. **72 cells.**
  `framing-2-edit` is excluded from this batch: at 11/12 and 12/12 it is at
  ceiling for both arms and carries the least of the five.
- Engine `8b52de9`, temperature 1.0 verified both sides,
  `--max-repeated-calls 10` — **which now reaches the Engine arm for the
  first time** (E10).
- One preflight per task into a fresh directory; one uncounted V5d smoke
  cell per newly-enabled task before its batch, read for a `bash` call that
  actually ran the suite.

## 3. What is measured

Kept separate, never pooled: successful attempts; retained patches;
cost-to-succeed in **both** units with the unconditional figure beside
them; and, from the census, whether the runner was used at all per cell.

**No cross-batch comparison is drawn.** Every earlier number for these
tasks predates both the runner and E10's tripwire fix, so the Baseline arm
in *this* batch is the only reference.

## 4. The consequence table, predeclared

| what the Engine arm shows | meaning | next |
|---|---|---|
| **D.** the runner is unused in most cells of a task | nothing is learned for that task | report per task before reading its counts |
| **A.** Engine >= Baseline on two or more tasks | the runner generalizes | build around it; re-inventory the bands, which will have moved |
| **B.** Engine >= Baseline only on `plausible-wrong-fix`-like tasks (near-ceiling Baseline) | it is a convenience, not a capability | stop expanding it; the hard tasks need something else |
| **C.** `depth-3` moves off 0/12 for the Engine arm | a floor moved | the strongest single result available here; verify by replication before any claim |

**D is checked per task, first.** A tool the model does not invoke makes
that task's rows meaningless, which the 2026-09-06 smoke already
demonstrated once.

## 5. Stopping rule

`n` fixed at 12 per arm per task. No extension after reading, no task added
or dropped, no engine change during the batch. Interrupted batches resume;
incomplete cells are moved aside and logged.

## 6. Limits

One rung, one model, one sampler value. `depth-3`'s floor is a *quality*
floor — patches are produced and fail — so a runner could plausibly move it
without any capability change, simply by letting the model see its patch
fail. That would still be worth having, and it is not the same claim.
