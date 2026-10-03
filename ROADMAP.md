# Roadmap — release one and release two (both concluded)

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

## Release two — concluded

The claim is met, pre-registered 2026-09-19 and read once: Engine 16 of 24
against Baseline 2 of 24 on the primary task (`docs/numbers.md`).

Release two starts with a design sitting, not a build. What release one
settled, and what it leaves for that sitting:

- **Keep:** two-uid isolation, the launcher and its records, the generator
  and qualification, the budget tripwire, per-cell evidence, guard 4, the
  `self_test` output detection (which replaces the retired redirect), and the
  offline reconstruction method
  (`evidence/2026-09-15-release-one-outcome/`).
- **Hypothesis to test before building:** the lever at 9B on build tasks is
  finishing, not guarding — cells reach a passing state and keep working.
  Measure it offline first (reconstructed pass-state versus end state over
  retained cells), then decide whether a finish-on-green Engine is worth a
  claim.

| # | Phase | Mode | Done when |
|---|---|---|---|
| R0 | Design sitting under `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`: the claim, the workload, what counts as a ceiling task | attended | a spec the maintainer approves that meets those constraints. Knowledge stage: the finishing counterfactual ran `not-the-lever` and, corrected in run 2, **Verify** — a small, real finishing class (power 0.26) (evidence/2026-09-15-finishing-counterfactual/README.md and run-2/README.md). Maintainer's decision 2026-09-15, later the same day: the "ship as a product with no claim" direction is withdrawn; a Baseline-only pathology census runs first under `docs/superpowers/specs/2026-09-15-release-two-census-design.md` (five tasks, n = 6, 48k/72, per-turn cap 16k, tripped worktrees graded), and the claim shape is chosen from its classified table. Census night 1 ran 2026-09-16 (30 cells; classifier outputs evidence/2026-09-16-census/): depth-3 at R2 is floor (6/6); run-record-gate and docs-linter are finishing-bound (9 of 12 cells reached green inside the 32k line, 2 stopped); cell-loop and speed-probe reached no pass state; 9 cells wall-clock-cut on a shared machine. Night 2 ran 2026-09-17 (nine replacement cells, 4,800 s backstop, quiet machine, no timeouts; run-record-gate 3/3 reached green inside the line, none stopped; large builds unchanged; the third-candidate record was withdrawn by the section 4 amendment). No plan holds a third medium-build task; it is authored (docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md). Census page draft: evidence/2026-09-16-census/README.md. Next: class columns, R0 sitting, Engine spec. The third medium-build task is authored, not cut: selfhost-preflight-quiet (docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md, approved 2026-09-17), cut 2026-09-18, validity-checked under R0 §1.2, 20 hidden tests and a public suite measured at roughly 34.8-34.9 s wall clock (a ceiling on a contended machine), both inside the 15-20 and under-40-s targets; four ungraded-literal gaps in the hidden suite are disclosed and pre-registered for a post-hoc read in evidence/2026-09-18-census-3/postreg.md; one Baseline admission record frozen for census night 3 (n = 6, 48,000 tokens, 72 turns, 4,800 s, k = 3); wiring the check into launch --preflight is a separate later commit. |
| R1 | Measurement validity: rung fix (assertion explanations), a qualification check that the prompt determines the hidden suite's structural choices, per-turn output cap, grade tripped worktrees as a declared secondary, re-measure k | overnight | fixture tests both directions; re-probe; every candidate re-qualified |
| R2 | Engine parity and hygiene: multi-edit, prompt collapse, writable paths from `Files:`, finish-on-green nudge | overnight | replay and fixture tests; Engine and Baseline tool surfaces equivalent |
| R3 | Workload: new ceiling candidates cut and admitted under confinement | attended | a ceiling set whose Baseline failures are budget- or finish-shaped, not information-bound |
| R4 | Development measurement on a hard, build-shaped dev cut; route proof | attended | the target behaviour moves on development cells |
| R5 | Comparison and decision | batch, frozen in daylight | result pages, or a stated negative |

## Next — re-derive on the confinement harness

Design: `docs/superpowers/specs/2026-09-27-unisolated-harness-design.md`;
plan: `docs/superpowers/plans/2026-09-27-unisolated-harness.md`.

The two-uid and `bwrap` profiles are retired. A cell now runs as the
maintainer on a plain checkout on macOS or Linux, with an eval-owned Pi
extension loaded by both arms (in-worktree confinement), a post-hoc reach
audit, and a mechanical admission tally. The serving backend is a declared arm
field (`omlx` or `openai`), and cells from different backends never pool.

That is a harness change, so every deciding result produced under isolation is
unconfirmed until re-derived here (spec §5): the 39-cell census and its signed
class columns, the release-two comparison in `docs/numbers.md`, both route
proofs and the red-stop replay, and the sandbox Baseline set (historical).
Nothing is built on any of them in the meantime.

| # | Step | Mode | Done when |
|---|---|---|---|
| C0 | Mark each result above unconfirmed in `evidence/2026-09-15-release-one-decision-ledger.md`, naming this harness change | attended | every listed decision carries the mark and the commit that re-opened it  done 2026-10-02: ledger entry "C0", marks name `35c298d`; census night 3 added to the list |
| C1 | Re-qualify on the new harness: same task, model and budgets, extension loaded on both arms, no host setup | attended | a qualification record under `confinement` that passes preflight on this machine |
| C2 | Re-read the census process classes from retained transcripts; re-sign the class columns where `hunting` becomes live | attended | signed columns that state which cells reclassified and why |
| C3 | Re-run the census outcome cells under confinement | batch, frozen in daylight | a classified table on this harness, with refused and flagged cells counted |
| C4 | Re-derive the finishing counterfactual, then resume R0's order | attended | the counterfactual's verdict on the new census, before any Engine build |

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

**Parked 2026-10-02: the satyrn-engine branch `derive-new-top-level-module`.**
Two local commits, rebased 2026-10-02 onto engine `main` `1869397`: `d4abd65`
lets `derive` admit a new top-level module the request names, and `92c9282`
adds a backlog note (`/implement` defaults `SATYRN_ENGINE_REPO` and
`SATYRN_MODEL` itself). The rebase was clean and touches no digest-pinned
`packages/engine` file. But it changes Engine behaviour, so landing it means re-pinning the
Engine arms, which is a new Engine condition. It is also a remedy that no
diagnosed admission on this harness has asked for yet. Reopens at C4, only if
the re-derived counterfactual names it. Until then the Engine arms stay on
`1869397`.

Contributors bringing their own workflows in as suites; the isolation versus
guards ablation; pattern refusal of hunting commands; a filesystem sandbox
for `/implement`; the orchestrator skill; a depth-4 AgentClinic task; any
course-derived claim; an integration test that drives the real
`adapters/pi_session.py` through a full four-phase session protocol (the
tag's only such test was built on the dropped `session-mechanics` task).

**Cleanup, 2026-10-02** — findings and evidence in
`evidence/2026-10-02-cleanup-audit/README.md`; engine-side items
in satyrn-engine `BACKLOG.md`. Each item names what closes or reopens it.

- **Un-nest the task bases.** `cut_task.py` archives every other task's
  `base/` into a new base; `selfhost-preflight-quiet` carries 3,821 nested
  task files, four levels deep, and cells work in that tree. Do at C1, where
  the tasks are re-qualified anyway: one re-cut, one re-pin.
- **Propagate the C0 unconfirmed mark** to `docs/numbers.md`, the site, the
  census and red-stop evidence READMEs, and the records the ledger names.
  Prose only; do before the site next deploys.
- **Rewrite `STATE.md`; one reading order** across `AGENTS.md`, `README.md`
  and `STATE.md`; retired local state removed. Do with the mark above.
- **This file's shape:** a Status column for the release-two table, R0's
  cell reduced to a pointer, 2d closed, the list below given reopen
  conditions or moved to `TODO.md`, one backlog home chosen. Do with `STATE.md`.
- **Session route:** `packet.py`, `turn_ledger.py`, `hygiene.py`,
  `session_repeat_limit.py`, the `session_*` family, 25 test files and the
  263 KB transcript fixture have no product caller. Reopens if a plan names a
  multi-phase workload; otherwise delete at the next instrument-free window.
- **Frozen census scripts call `preflight_settings.py --cell`, a flag that no
  longer exists**; `launch_record.py` keeps the dead branch. Header or fix,
  with the engine's red-stop receipt fix, before the first re-derivation record.
- **Gates that nothing runs:** coverage and pyrefly configured in both
  repos, Node installed in CI with no Node gate, the confinement extension
  outside `just gates`. Decide once for both repos: gate it or remove it.
- **Fossil files:** `scripts/seq_design.py`, `scripts/suite_durations.json`,
  `tools/agentclinic_gate.sh`, `arms/baseline.json`, the duplicate
  `engine-mellum-class-swe-pi-redstop.json`, 92 duplicate Mellum request
  files; catalogue marks for lessons, pathologies 21-23 and the two "clean
  harness" banners; the three spec headers; the misfiled task plan. One
  provenance row and one commit each.
