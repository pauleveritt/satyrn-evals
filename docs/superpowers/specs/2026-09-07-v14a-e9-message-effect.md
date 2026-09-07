# V14a — does telling the model the edit already landed stop it re-sending? Frozen before the first cell.

**Status: frozen 2026-09-07, before any cell runs.** Exploratory,
diagnostic, admits nothing.

## 1. The question

Engine `c6054ee` (E9) added `ANCHOR_ALREADY_APPLIED`: when an anchor is
missing but `new_text` is already in the file, the refusal says so and
names the line. 182 of 208 `ANCHOR_MISSING` events in the retained corpus
were exactly that case. **Does the message stop the re-send?**

The harvest index records that guidance did not move this attractor. This
is not guidance — it is a fact about file state, the category that worked
for `TEST_COMMAND_NOT_ALLOWED`. Whether that distinction holds is the
question.

## 2. The measure, defined before the cells

**Primary, and within-cell so it needs no control arm:** of all
`ANCHOR_ALREADY_APPLIED` events, the fraction followed later **in the same
cell** by the *same* `(path, old_text, new_text)` being sent again.

**Pre-change reference, computed before this batch and recorded here:**
over every retained Engine transcript, 208 `ANCHOR_MISSING` events across
73 cells, of which **111 (53%)** were followed by the same edit being sent
again. Recompute by walking each transcript's edit start/end pairs and
matching the triple.

That reference is **cross-batch and weak** — different engine, different
batches, and the tripwire did not apply to the Engine arm then (E10). It
sets the scale; it is not a control.

## 3. Design

Engine arm only, `n=12`, `agentclinic-repair-depth-3` R1,
`gemma-4-12B-it-MLX-8bit` — the task whose Engine cells carried anchor
loops (65 refusals in one V13c cell). Engine `8b52de9` (E9 + E10),
temperature 1.0, `--max-repeated-calls 10`. One preflight, fresh
directory. 12 cells.

`depth-3` is a quality floor — 0/12 both arms — so **outcomes are not the
measure here** and no success claim is available from this batch. That is
deliberate: it is the task where the pathology lives.

## 4. The consequence table, predeclared

| re-send fraction | meaning | next |
|---|---|---|
| **D.** fewer than 10 events | underpowered | no conclusion; say so first and stop |
| **A.** <= 20% | the message breaks the loop | keep it; try the same shape on the no-op case |
| **B.** 21–40% | partial | keep it, and look at what the re-senders did differently |
| **C.** > 40% | it does not break the loop | the corrective half of E9 is ineffective; the post-edit region (preventive) may still be, and needs its own test. Do not build more corrective messages on this evidence |

**D is checked first.** 53% is the pre-change scale; C is set at 40% so
"no change" lands in C rather than being read as partial.

## 5. Stopping rule

`n` fixed at 12. No extension after reading, no change to the measure
after the first cell. Interrupted batches resume.

## 6. Limits

One task, one rung, one model, one arm. E10 landed with E9, so the
tripwire now applies to this arm and did not before — a cell that would
have looped to the deadline may now be cut at ten repeats, which
**reduces** the event count and is a further reason D is checked first.
