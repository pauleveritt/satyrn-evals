# V16 (revised) — the pathology census

**Status: confirmed by the maintainer 2026-09-07.** This supersedes the
deliverable in `2026-09-06-v16-diagnostic-suite-admission-design.md`; the
three-axis admission rule there stands and becomes a *consequence* of this,
not the primary work.

## 1. Why this, and not more batches

Every engine change on 2026-09-06 came from reading transcripts by hand:
the mutator's 973 schema refusals, `Tool bash not found`, an anchor loop, a
read lock. **None came from a comparison.** The comparisons produced a
null, two corrections and four instrument findings.

**499 transcripts are already on disk** across 23 batches. Each diagnosis
was an ad-hoc script over them. Those scripts are the product.

The census costs **no inference**, is re-scorable forever (`BRIEF.md`
rule 3), and a detector added later applies retroactively to every retained
cell. It answers "what is going wrong, where, how often" — which is what a
contributor asking *"did my engine fix help, and if not, why"* needs, and
is the question `BRIEF.md` puts first.

**What it does not do:** say whether a change makes the model succeed more.
Outcomes still cost cells. The census says where to spend them.

## 2. The named pathologies

Each is a **predicate over one transcript**, computed offline. Each reports
a magnitude, not a boolean, because "how bad" is the interesting part.

| name | magnitude | observed |
|---|---|---|
| `schema_refusal` | count of tool results carrying a schema validation failure | 973 across 6/12 Engine cells, V13 |
| `tool_not_found` | count of results naming an unregistered tool | every runner call, two smokes |
| `unknown_tool` | count of calls to a tool outside the known vocabulary | `uv_run`, invented twice |
| `read_lock` | longest run of identical consecutive calls **before the first edit** | 8 bare-Pi cells reached >= 5; **0 of 8 ever edited** |
| `anchor_refusal` | count of mutator refusals | 65 in one `depth-3` cell |
| `noop_edit` | count of edits reporting no change or no match | 175 in one Envelope cell |
| `stall` | longest run of calls without an **applied** edit | 158-247 on timeouts, 6-8 on passes |
| `v10_unmeasured` | whether V10 refuses the transcript, and why | compaction events; unknown tool names |

`read_lock` uses the definition frozen in the V13d protocol, unchanged.

## 3. The rule that keeps it honest

**A census never voids a cell.** V10 marks a whole transcript `unmeasured`
on one unrecognised event, which blinded it on `depth-3`'s two most
expensive cells — exactly the cells worth reading. The census scans what it
can and reports `v10_unmeasured` as *one pathology among others*, so a
transcript V10 cannot parse still yields every detector that does not
depend on the tool vocabulary.

Counts are per cell and are **never pooled across arms into one number**;
they aggregate by `(batch, task, arm, engine_commit)`, and the engine
commit comes from the batch's own `preflight.json`, so a census row always
says which product produced it.

## 4. Surface

```
satyrn-evals census RUNS_ROOT [RUNS_ROOT...] [--json PATH]
```

Walks each root, finds every `*/transcript.txt`, and prints a table of
pathology x (task, arm) with cell counts and magnitudes, plus the cells
named for any pathology present. `--json` writes the full per-cell record.
Exit 0 whatever it finds: **a census is a measurement, not a gate.**

## 5. Test layout

Default tier, no model/network/subprocess. Synthetic transcript fixtures,
one per detector, each with:

- a **firing** fixture asserting the magnitude, not merely presence; and
- a **silent sibling** — a clean transcript of the same shape — asserting
  the detector reports nothing (`BRIEF.md` rule 8).

Plus: a transcript V10 refuses still yields other detectors' findings
(the no-void rule, which is the point of section 3); an empty or
unparseable transcript is reported, never counted as zero; and aggregation
groups by all four keys.

## 6. Acceptance

- The census over the retained batches reproduces figures already published
  by hand: **973** `schema_refusal` in `2026-09-06-v13-143343`'s Engine
  arm, **0** in its Baseline and Envelope arms; `read_lock` >= 5 on
  **8** bare-Pi cells across V13/V13b/V13c with **0** of them editing; and
  **0** `schema_refusal` in every post-`b977941` batch. Reproducing a
  hand-computed number is what makes it an instrument rather than a new
  source of numbers.
- Full gates green.
