# V13 — preregistration

**Status: draft, awaiting confirmation.** Everything here except
[§7](#7-the-one-open-decision-envelope) is frozen by being written down
before any non-reference arm runs. Nothing in it reads a non-reference
outcome.

## 1. The question

On one predeclared cell, does the Engine product produce more successful
attempts than bare Pi, and than Envelope?

Not asked, and excluded: **which part** of Engine is responsible. The
arms are whole products with different tool surfaces; an advantage
attributes to none of their components.

## 2. The firewall

Two algorithms are frozen here, both computed from **reference-arm data
only** — the 2026-09-06 staged profile and R0 profile, 168 cells of bare
Pi at two capability points:

1. the ordered primary-cell selection (§3), and
2. the rule mapping reference-arm evidence to Envelope's cap (§7, open).

Neither reads V11c spike outcomes. **Spike cells are never pooled with
V13 cells.**

## 3. Primary-cell selection, frozen

**Eligible** = a pure-edit repair cell the reference arm places below
ceiling and above a capability wall: `0 < successful attempts < n`, with
at least one retained patch. Seven of 29 profiled cells qualify.

**Ordered rule.** Rank ascending by:

1. `|successful attempts / n − 0.5|` — a cell at even odds carries the
   most information about a difference;
2. task name, ascending;
3. rung, ascending;
4. model identifier, ascending.

The first is the criterion; 2–4 break ties and are **not invented here** —
they are the tie-break already recorded in the V11c spike protocol §3,
reused rather than chosen with knowledge of where they land.

**Result: `agentclinic-repair-depth-2`, rung R1, `gemma-4-12B-it-MLX-8bit`**
(3/6 successful attempts, 4/6 patches produced). `misleading-locus` R1 at
the 12B ties on the criterion and loses on task name.

**Disclosure.** The rule selects a cell the V11c spike did *not* use, so
this is a fresh comparison rather than a replication. Had it selected
`misleading-locus` R1, V13 would have disclosed the prior peek and
labelled itself a replication. That it did not is recorded as convenient,
not as evidence of anything.

Recompute the ranking:

```
uv run python - <<'PY'
import json, glob, os
rows = []
for t in glob.glob(os.path.expanduser("~/satyrn-smokes/2026-09-06-*/*/tally.json")):
    d = json.load(open(t)); a = d["per_arm"]["baseline"]
    rows.append((d["task"], d["rung"], d["model"],
                 a["verdict_counts"]["pass"], a["code_counts"]["OK"], a["cells"]))
elig = [r for r in rows if 0 < r[3] < r[5] and r[4] > 0]
print(sorted(elig, key=lambda r: (abs(r[3]/r[5]-0.5), r[0], r[1], r[2]))[0])
PY
```

## 4. Arms

| arm | definition |
|---|---|
| Baseline | bare Pi as shipped, `arms/baseline.json` |
| Envelope | **open — see §7.** Cannot run until frozen |
| Engine | the shipped Engine, `arms/engine.json`, pinned `25ca0be` |

## 5. Design

- **`n = 12` per arm**, 36 cells, interleaved on a seed recorded before
  the first cell.
- One preflight per batch into a fresh output directory, including the
  live completion and the inference-settings check.
- **`--max-repeated-calls 10` on for every arm.** Stated limit: it bites
  only arms that produce identical-run loops, and the Engine arm
  self-limits below the threshold, so the rule fires asymmetrically in
  practice. It is kept because it is a *spending* rule — it terminates
  and sends the model nothing — and because it cannot change the primary
  metric: across 231 retained cells, **no cell that produced a patch ever
  reached an identical run of 10** (max 2). It changes cost and the
  recorded code, not who succeeds.
- The tally must accept the set, or there is no result.

## 6. Analysis, frozen

- **Primary:** two one-sided contrasts, Engine > Envelope and
  Engine > Baseline, each at Bonferroni-adjusted `α = 0.025`.
- Published beside them: per-arm counts, bands, and V10 pathology counts.
- **Power is low.** At `n = 12` per arm this design detects only a large
  difference; a null is therefore weak evidence of no effect, and is
  reported as such rather than as "no difference".
- **Null handling:** if the primary contrasts do not meet the criterion,
  the result is a null **at that cell**, recorded as prominently as a
  positive would be. `n` does not increase and the cell does not change.
  Another rung or task is a new proposal and a new preregistration.
- Any other eligible cell run afterwards is a descriptive replication,
  never an independent chance at a positive.

## 7. The one open decision: Envelope

**V13 cannot run until this is frozen**, because the schedule interleaves
all three arms.

What is known: the 900 s / 8192 tokens / 80 k context in the de-admission
record are pi and model settings, **not** what `envelope-cap.ts` capped.
The historical configuration is unrecoverable, so this is a fresh choice
that must be argued from a per-cell floor measured inside a materialized
workspace. That floor is on record: **1,546 input tokens**
(`~/satyrn-smokes/2026-09-05-v11-trim/token-floor.json`).

**A trap to avoid when choosing.** Defining Envelope as "Baseline plus a
stall cap" is appealing and wrong twice over: an arm that only terminates
stalled cells can never record *more* successful attempts than Baseline,
so it is a pointless outcome arm; and it converges mechanistically with
Engine's loop breaker, weakening the three-way contrast V13 exists for.

This is Engine-side design and belongs in `satyrn-engine`'s backlog. It
is recorded here because that repository is pinned at `25ca0be` and must
stay byte-identical for the Engine arm — editing it would make V13's own
preflight refuse. **Transfer it when the pin next moves.**

## 8. What voids a run

A refused tally; a red preflight; a cell whose transcript-observed
`message.model` is not the requested model; or an inference setting that
changed under the batch. A voided run is re-run in full, not patched.
