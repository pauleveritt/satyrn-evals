# Roadmap — release one

The design is `docs/superpowers/specs/2026-09-13-release-one-design.md`. One
claim: an Engine that beats bare Pi at three mechanical pathologies
(repeat/read-lock loops, never running its own tests, writing outside the
declared scope), and an Eval that proves it, cold and warm. Nothing else is
claimed.

## Phases

| # | Phase | Mode | Done when | Status |
|---|---|---|---|---|
| 0 | Restart: tags, orphan trees, the import with provenance, gates green, launcher gate, docs caps, review script, hooks | overnight | both trees build; default tiers green; `just gates` enforces the caps; `PROVENANCE.md` names every file's source | done 2026-09-13 — 7fb9949, 4a4c2bb |
| 1 | Engine `/implement` v1: derived contract, guards on the dispatch route, carried tests, compact results, receipt | overnight, fake-first | every component has a replay or fixture test in both directions; a fake model completes `/implement` end to end with no inference | not started |
| 2 | Eval core: two workloads re-qualified, `census` for the three counts, the warm prefix as a fixture, cold/warm launcher profiles | overnight, except one attended prefix recording | the eval runs both arms and both conditions against a fake and produces the per-cell table | not started |
| 3 | Route proof: one cell per arm per condition | attended | guards fire where retained evidence says they should; receipts read; the model probe has fixed the model | not started |
| 4 | Comparison: n=12 per cell on the M1 Pro | unattended batch, frozen in daylight | one result page against the decision rule | not started |
| 5 | Decide and ship, or stop | attended | release one published, or a stated negative | not started |

The Ornith 1.5 9B pathology probe runs alongside 0–2 on the tagged tree
(`git show pre-release-one-2026-09-13:docs/current/ornith-9b-pathology-probe-brief.md`)
and fixes the model before Phase 3.

## Rules that bind every phase

- Attended cycles are ≤ 1 GPU-hour and n ≤ 8; the weekly batch is n = 12 per
  cell, record and grant frozen in daylight, run on the M1 Pro.
- A result is one file under `docs/results/`, ≤ 120 lines, with a fenced
  recompute command; at most twelve before one is folded into
  `docs/pathologies.md` or `docs/lessons.md`.
- Two consecutive instrument-only pieces stop the loop.
- Nothing pools across conditions, workloads, models, or machines.

## Deferred

Contributor-authored suites; a fifth roadmap phase; the isolation-vs-guards
ablation; the 16 GB target if the probe is negative; the orchestrator skill;
the `session-ordering-regression` hazard question; any course-derived claim.
