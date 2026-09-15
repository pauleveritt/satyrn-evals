# Roadmap — release one

The design is `docs/superpowers/specs/2026-09-13-release-one-design.md`. One
claim: on the ceiling workload, the Engine delivers a passing candidate within
budget (tokens and turns) more often than bare Pi, on Ornith 1.5 9B. A
declared secondary: on the floor workload, where both pass, the Engine costs no
more. Nothing else is claimed.

## Phases

| # | Phase | Mode | Done when | Status |
|---|---|---|---|---|
| 0 | Restart: tags, orphan trees, the import with provenance, gates green, launcher gate, docs caps, review script, hooks | overnight | both trees build; default tiers green; `just gates` enforces the caps; `PROVENANCE.md` names every file's source | done 2026-09-14 |
| 1 | Engine `/implement` v1: derived contract, guards 1–4 and symbol preservation, carried tests, compact results, receipt | overnight, fake-first | every component has replay or fixture tests both directions; a fake model completes `/implement` end to end; 120/300 frozen against measured suite durations | done 2026-09-14 — evals e0f25df, engine 46d4514 |
| 2a | Eval core: harvest, token and turn tripwire, census extensions, hygiene | overnight | harness items 1, 3, 4, 5 have fixture tests both directions; the Engine arm runs against a fake | done 2026-09-14 — docs/superpowers/plans/2026-09-14-phase-2a-eval-core.md |
| 2b | Isolation and tasks: two-uid isolation, generator and R1-plan, candidates qualified, context-speed and concurrency probe | overnight, plus attended isolation setup and probe | the eval runs both arms against a fake under isolation with the budget tripwire; every candidate passes offline qualification; k measured; settings provenance verified by preflight | built 2026-09-15 — docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md; k and the first isolated Pi turn are the attended checklist in its Task 6 |
| 2c | Launcher loop: `launch RECORD` runs n cells per arm at k with arms interleaved under the record's profile, stops on infrastructure, resumes a stopped night; `record new` | overnight | a fake completes a k = 2 interleaved record under isolation through the launcher; a resumed night and an infrastructure stop | built 2026-09-15 — docs/superpowers/plans/2026-09-14-phase-2c-launcher-loop.md |
| 2d | Warm prefix: a developer prefix recorded and replayed byte-identically (a declared secondary outside the win rule) | overnight, plus attended recording | a recorded prefix replays byte-identically against a fake | not started; lands before Phase 4 |
| 3 | Admission and route proof: Baseline admission cells; one Engine cell per ceiling task | attended | ceiling and floor sets fixed; guards fire where retained evidence says they should; receipts read | not started |
| 4 | Comparison: campaign record, held-out cut, one batch night plus a day at k = 3 | unattended batch, frozen in daylight | one result page per task and one against the rule | not started |
| 5 | Decide and ship, or stop | attended | release one published, or a stated negative | not started |

The Ornith pathology probe answered 0/8, 1/8, 0/8 on the tagged tree; the
claim moved from pathologies to a ceiling (spec, "What the evidence
settled").

## Rules that bind every phase

- Attended sittings are ≤ 60 min and n ≤ 8; a batch sitting is 720 minutes
  of wall clock with no cell-count cap, record and campaign frozen in
  daylight, on this machine.
- A result is one file under `docs/results/`, ≤ 120 lines, with a fenced
  recompute command; at most twelve before one is folded into
  `docs/pathologies.md` or `docs/lessons.md`.
- Two consecutive instrument-only pieces stop the loop.
- Nothing pools across conditions, workloads, models, or machines.

## Deferred

Contributors bringing their own workflows in as suites; the isolation versus
guards ablation; pattern refusal of hunting commands; a filesystem sandbox
for `/implement`; the orchestrator skill; a depth-4 AgentClinic task; any
course-derived claim; an integration test that drives the real
`adapters/pi_session.py` through a full four-phase session protocol (the
tag's only such test was built on the dropped `session-mechanics` task).
