> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V13 — preregistration

**Status: confirmed by the maintainer, 2026-09-06.**
[§7](#7-envelope-decided-2026-09-06) — the one section left open — was
decided that day, so **every section is frozen by being written down
before any non-reference arm runs**, and nothing in it reads a
non-reference outcome. This commit is the timestamp: it precedes the
Envelope smoke and every budgeted cell.

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
2. Envelope's definition (§7) — **decided 2026-09-06 as a tool
   surface, not a cap**, so no reference-arm budget evidence is
   mapped to it and nothing in it reads an outcome.

Neither reads V11c spike outcomes. **Spike cells are never pooled with
V13 cells.**

## 3. Primary-cell selection, frozen

**Eligible** = a pure-edit repair cell the reference arm places below
ceiling and above a capability wall: `0 < successful attempts < n`, with
at least one retained patch. Seven of **28 distinct** profiled cells
qualify. (Corrected 2026-09-06: an earlier draft read "29 profiled
cells." There are 29 tallies and 28 distinct `(task, rung, model)`
cells — `misleading-locus` R1 on the 26B was tallied twice as a
calibration duplicate, 6/6 both times, so it is at ceiling and
ineligible under either count. The recompute below globs both tallies;
selection is unaffected.)

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
| Envelope | bare Pi on Engine's tool surface, `arms/envelope.json` — `read,edit`, every other setting identical to Baseline. Prospective, not a reproduction. See §7 |
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

## 7. Envelope, decided 2026-09-06

**Envelope = `satyrn-evals-attempt-pi` with tools `read,edit`** — bare Pi
on Engine's own tool surface, every other setting identical to
`arms/baseline.json`: same model, same pins, same `inference` block, no
engine code, **no budget cap**. It is `arms/envelope.json`.

**Why a surface and not a cap.** The canonical product Envelope was itself
a restricted tool surface — "the canonical product Envelope, which used
only `read,write`"
(`docs/superpowers/research/2026-08-27-local-pings-envelope-engine-followup.md:24-27`).
Engine exposes `read,edit` (`arms/engine.json`, `"tools"`). Putting bare Pi
on exactly that surface gives three whole-product arms — Baseline's four
tools, Engine's two tools without Engine, and Engine — and an Envelope that
*can* out-score Baseline. It needs no argument from the 1,546-token floor,
no engine edit (the engine stays byte-identical at `25ca0be`, which this
preregistration's own preflight requires), and no new mechanism.

**It is prospective, not a reproduction.** `edit` is not `write`, and the
era's pi, prompt and adapter are unrecoverable (`BACKLOG.md`, "Historical
Envelope artifact recovery"). No sentence about this arm may claim to
reproduce the historical Envelope.

**The trap this avoids.** Defining Envelope as "Baseline plus a stall cap"
is appealing and wrong twice over: an arm that only terminates stalled
cells can never record *more* successful attempts than Baseline, so it is a
pointless outcome arm; and it converges mechanistically with Engine's loop
breaker, weakening the three-way contrast V13 exists for.

**Superseded, and kept visible.** The prior text of this section said the
cap "must be argued from a per-cell floor measured inside a materialized
workspace," and named that floor — **1,546 input tokens**
(`~/satyrn-smokes/2026-09-05-v11-trim/token-floor.json`). There is no cap,
so no floor argument is owed. `ROADMAP.md` carries the matching dated
amendment; the decision and its rationale are in
`docs/superpowers/research/2026-09-06-next-agent-brief-v13-envelope-and-roadmap-control.md` §2.

**Owed before the first budgeted cell.** The Envelope path is a materially
new execution path, so it takes one uncounted V5d smoke cell whose
transcript is read for *positive* evidence — `edit` present in
`tool_execution_*` events, `bash` and `write` absent — not merely for the
absence of an error.

## 8. What voids a run

A refused tally; a red preflight; a cell whose transcript-observed
`message.model` is not the requested model; or an inference setting that
changed under the batch. A voided run is re-run in full, not patched.
