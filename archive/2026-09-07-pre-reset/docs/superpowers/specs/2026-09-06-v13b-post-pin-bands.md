> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V13b — post-pin bands, frozen before the first cell

**Status: frozen 2026-09-06, before any cell runs.** Exploratory. **Not a
preregistration and not an admission.** Never pooled with V13, V13a, V11c
or the V12 profile — all of those are **pre-pin** and ran at the server's
own unrecorded default sampler.

## 1. What this buys

`temperature` is now pinned at **1.0**, recorded in every arm file, sent
through pi's `models.json` `samplingParams`, and checked by preflight 0c
(`b015c11`). Two things follow:

1. **Primary — establish the post-pin bands** for the two tasks that carry
   this suite's entire reference-arm headroom, at `n=12` per arm, both arms
   interleaved. These become the reference measurement going forward; every
   earlier number is pre-pin.
2. **Secondary, and deliberately weak — a continuity flag.** Whether the
   post-pin counts look consistent with the pre-pin ones. This **cannot
   confirm** continuity: it is a cross-pin comparison, and the pre-pin
   numbers are themselves noisy — Baseline on `depth-2` R1 read 7/12 in the
   V13 batch and 2/6 in V13a with *no* setting changed. It can only raise a
   flag.

Not asked: which Engine component is responsible for anything; whether any
task is admissible; any claim that Engine is better.

## 2. Design, frozen

- **Arms:** `arms/baseline.json` and `arms/engine.json`, **interleaved**
  within each batch on a seed recorded before the first cell. Counts are
  compared **within** a batch only.
- **`n = 12` per arm per task.** Tasks `agentclinic-repair-depth-2` and
  `agentclinic-repair-misleading-locus`, rung **R1**, model
  `omlx/gemma-4-12B-it-MLX-8bit`. **48 cells.**
- `--max-repeated-calls 10` on for every arm.
- One preflight per task into a fresh output directory. Check 0c must see
  both arms recording `temperature: 1.0` **and** pi's config sending it —
  which is now a refusal, not a note.
- Engine pinned at `b977941`, digests verified. No engine change since
  V13a, so nothing here is attributable to new engine code.
- **No V5d smoke is owed.** The execution path is byte-identical to V13a's;
  only a sampler setting changed, and preflight checks that one directly.

## 3. The consequence table, predeclared

| what the cells show | what it means | what happens next |
|---|---|---|
| **A.** at least one task keeps a spread — some arm strictly between 0 and 12 | headroom survives the pin | these are the working cells; suite design proceeds from the post-pin bands |
| **B.** a task saturates — both arms at 0/12 or both at 12/12 | that task stopped carrying information under the pin | drop it from the headroom inventory and say so; do not re-tune the rung to recover it |
| **C.** any arm/task differs from its pre-pin proportion by more than **3/12** | 1.0 is probably not what the server was running | record it; every pre-pin batch is then a *different operating point*, not a continuous prefix. No pre-pin count may be quoted beside a post-pin one afterwards |
| **D.** a failure class absent from V13 and V13a | unknown | classify verdict-counts vs diagnostic-only before reading the comparison |

Pre-pin reference points for **C**, written down now: `depth-2` Baseline
2/6 and Engine 4/6; `misleading-locus` Baseline 3/6 and Engine 5/6. At
`n=12` the continuous expectations are 4, 8, 6 and 10; the flag fires
outside ±3.

**No significance threshold is declared and none will be computed as a
test.** Fisher values, if reported, are descriptive beside the counts.

## 4. Stopping rule

`n` is fixed at 12 per arm per task. **No extension after reading.** No
task added, dropped or swapped after the first cell. An interrupted batch
resumes: completed cells stand, an incomplete cell directory is moved
aside and re-run, and the move is logged.

## 5. What voids a batch

A tally that does not accept the set; a transcript whose own
`message.model` is not `gemma-4-12B-it-MLX-8bit`; a preflight that did not
run into a fresh directory; an engine tree that is not `b977941`; a
`temperature` that preflight does not see pinned at 1.0 on both sides; or
a machine-state failure such as a GPU out-of-memory, which is voided
rather than scored.

## 6. Limits, stated before the counts

- Two tasks, one rung, one model, one sampler value. Nothing here
  generalizes past that.
- **1.0 was chosen for continuity, not measured.** The server's prior
  default is unknown and unreadable from outside; this batch's outcome C is
  the only evidence about it that will exist, and it is a flag, not a test.
- `misleading-locus` remains partly a re-measurement: Engine recorded 10/12
  there in V11c on the defective commit.
