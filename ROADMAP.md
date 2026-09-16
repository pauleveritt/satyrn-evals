# Roadmap — release one (concluded) and release two (proposed)

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
| 2d | Warm prefix: a developer prefix recorded and replayed byte-identically (a declared secondary outside the win rule) | overnight, plus attended recording | a recorded prefix replays byte-identically against a fake | not run; release two if still wanted |
| 3 | Admission and route proof: Baseline admission cells; one Engine cell per ceiling task | attended | ceiling and floor sets fixed; guards fire where retained evidence says they should; receipts read | done 2026-09-15 — records/2026-09-1[45]-*; Engine n=1 BUDGET_EXCEEDED on all three ceiling tasks, `self_test` unused |
| 3b | Remediation iteration: `self_test` enforcement first; development records on tasks outside the claim | attended, one day | each change moves its target behaviour on development cells; engine commit freezes after | done 2026-09-15 — engine 8049d73: ad-hoc pytest runs redirected (24 to 3), gate 0 firings, outcomes unchanged; engine frozen |
| 4 | Comparison: campaign record, held-out cut, one batch night plus a day at k = 3 | unattended batch, frozen in daylight | one result page per task and one against the rule | not run: every ceiling task fails for a reason the Engine cannot reach (outcome page) |
| 5 | Decide and ship, or stop | attended | release one published, or a stated negative | done 2026-09-15 — stated negative: docs/superpowers/specs/2026-09-15-release-one-outcome.md |

The Ornith pathology probe answered 0/8, 1/8, 0/8 on the tagged tree; the
claim moved from pathologies to a ceiling (spec, "What the evidence
settled").

## Release two — proposed, not yet specified

Release two starts with a design sitting, not a build. What release one
settled, and what it leaves for that sitting:

- **Keep:** two-uid isolation, the launcher and its records, the generator
  and qualification, the budget tripwire, per-cell evidence, guard 4, the
  `self_test` redirect, and the offline reconstruction method
  (`evidence/2026-09-15-release-one-outcome/`).
- **Hypothesis to test before building:** the lever at 9B on build tasks is
  finishing, not guarding — cells reach a passing state and keep working.
  Measure it offline first (reconstructed pass-state versus end state over
  retained cells), then decide whether a finish-on-green Engine is worth a
  claim.

| # | Phase | Mode | Done when |
|---|---|---|---|
| R0 | Design sitting under `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`: the claim, the workload, what counts as a ceiling task | attended | a spec the maintainer approves that meets those constraints. Knowledge stage: the finishing counterfactual ran `not-the-lever` and, corrected in run 2, **Verify** — a small, real finishing class (power 0.26) (evidence/2026-09-15-finishing-counterfactual/README.md and run-2/README.md). Maintainer's decision 2026-09-15, later the same day: the "ship as a product with no claim" direction is withdrawn; a Baseline-only pathology census runs first under `docs/superpowers/specs/2026-09-15-release-two-census-design.md` (five tasks, n = 6, 48k/72, per-turn cap 16k, tripped worktrees graded), and the claim shape is chosen from its classified table. Census: five records frozen 2026-09-16 (48,000 tokens, 72 turns, 3,000 s, k = 3, n = 6, Baseline only); the claim shape is chosen from the classified table (docs/superpowers/specs/2026-09-15-release-two-census-design.md section 8). |
| R1 | Measurement validity: rung fix (assertion explanations), a qualification check that the prompt determines the hidden suite's structural choices, per-turn output cap, grade tripped worktrees as a declared secondary, re-measure k | overnight | fixture tests both directions; re-probe; every candidate re-qualified |
| R2 | Engine parity and hygiene: multi-edit, prompt collapse, writable paths from `Files:`, finish-on-green nudge | overnight | replay and fixture tests; Engine and Baseline tool surfaces equivalent |
| R3 | Workload: new ceiling candidates cut and admitted under isolation | attended | a ceiling set whose Baseline failures are budget- or finish-shaped, not information-bound |
| R4 | Development measurement on a hard, build-shaped dev cut; route proof | attended | the target behaviour moves on development cells |
| R5 | Comparison and decision | batch, frozen in daylight | result pages, or a stated negative |

## Rules that bind every phase

- Attended sittings are ≤ 60 min and n ≤ 8; a batch sitting is 720 minutes
  of wall clock with no cell-count cap, record and campaign frozen in
  daylight, on this machine.
- A result is one file under `docs/results/`, ≤ 120 lines, with a fenced
  recompute command; at most twelve before one is folded into
  `docs/pathologies.md` or `docs/lessons.md`.
- Two consecutive instrument-only pieces stop the loop.
- A harness fix re-opens every decision its defect could have produced;
  nothing is built on a re-opened decision until it is re-derived on the
  fixed harness.
- No Engine design before diagnosed admission on the comparison harness and
  an offline estimate of the remedy; speed shortens building, never the
  order.
- Nothing pools across conditions, workloads, models, or machines.

## Deferred

Contributors bringing their own workflows in as suites; the isolation versus
guards ablation; pattern refusal of hunting commands; a filesystem sandbox
for `/implement`; the orchestrator skill; a depth-4 AgentClinic task; any
course-derived claim; an integration test that drives the real
`adapters/pi_session.py` through a full four-phase session protocol (the
tag's only such test was built on the dropped `session-mechanics` task).
