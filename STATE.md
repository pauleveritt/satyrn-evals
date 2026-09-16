# State of the project — 2026-09-15

The one page to read first. What exists, what is proven, what is disproven,
what is decided, and what is next. Every claim here cites the file or commit
that holds it.

## Goal

Keep a small local model on track so a Python developer can use local AI and
stay at the wheel: the developer does domain engineering (specs and tests),
not agent engineering. Two repositories, both on branch `release-one`:

- **`satyrn-evals`** — the eval harness: tasks, isolated cells, launcher,
  grading from retained evidence. Head `d0ea79d`.
- **`satyrn-engine`** — the product: `/implement`, a derived contract, four
  guards, symbol preservation, carried tests, `self_test`, a receipt. Head
  `ea49666`; the last code commit is `8049d73`.

## Where release one ended

**A stated negative, 2026-09-15**
(`docs/superpowers/specs/2026-09-15-release-one-outcome.md`). Phase 4 never
ran. The claim was that `/implement` takes Ornith 1.5 9B past its ceiling
within 32,000 output tokens and 48 turns, on 2 of 3 ceiling tasks. Each
ceiling task failed for a reason the Engine cannot reach under identical
prompts:

| task | Baseline admission | why it fails |
|---|---|---|
| `agentclinic-repair-depth-3` R1 | 0/4 | the prompt omits the line naming `tzinfo`; no cell of 7 found the seam |
| `selfhost-run-record-gate` R1-plan | 0/4 twice | the prompt invites `errors.py` (outside the allowlist) and reads gate rules as `gate()`'s |
| `selfhost-docs-linter` R1-plan | 1/4 | budget, after a passing state; Baseline is too good for a powered win |

## What is proven

- **Isolation holds.** The model runs as `satyrn-cell`; cells hunted from `/`
  and found no grader material. Preflight caught the one leak (the engine
  export carried a hidden test's name) before any cell used it.
- **Guard 4 works live.** It bounded 6–38 bash commands per cell and cut a
  root-wide search that had cost a Baseline cell 1,800 s.
- **The `self_test` redirect works.** Ad-hoc pytest runs fell from 24 to 3 on
  development cells (engine `8049d73`).
- **The harness measures what it claims.** Budget tripwire, base-commit
  harvest, per-cell evidence, offline reconstruction, and a launcher that
  stops on infrastructure failures and resumes a capped night.
- **k = 3 is sound.** On 1,932 live completions, k = 1 gives 41 tok/s per
  stream and k = 3 about 89 total, 2.2× (`evidence/2026-09-15-finishing-counterfactual/run-2/q3stats.md`).

## What is disproven, or undetermined

- **No outcome improvement from the Engine has been shown.** Three route-proof
  cells, one per ceiling task, all exhausted the budget.
- **Finishing is a real but small class.** Stopping at the first
  Engine-observable green rescues one retained cell of twelve budget-shaped
  ones (run 2; run 1's stricter rules counted none). Power at n = 12 would be
  0.26. `evidence/2026-09-15-finishing-counterfactual/` and its `run-2/`.
- **`self_test` enforcement did not move outcomes.** The completion gate
  cannot fire in cells that end at the budget.
- **Two ceiling tasks are defective**, not hard:
  `src/satyrn_evals/tasks/KNOWN_DEFECTS.md`.

## Current direction, decided 2026-09-15

**A pathology census before any Engine work, then the claim shape.** The
earlier same-day direction (ship the Engine as a product with no outcome
claim) was withdrawn by the maintainer: a page saying the Engine does nothing
good is not worth shipping. The census is one Baseline-only night on the
fixed harness, five medium tasks at n = 6, 48,000 tokens and 72 turns, every
cell classified by binding constraint the day after; the release-two claim
(outcome within 32k, cost at equal outcome, or a numbered ceiling at 9B) is
chosen from that table. Design:
`docs/superpowers/specs/2026-09-15-release-two-census-design.md`.
`ROADMAP.md` holds the phase rows.

## Rules that bind the work

- **`AGENTS.md`** in each tree: read order, the unattended/attended split,
  and **"Evidence has a harness"** — a harness fix re-opens every decision its
  defect could have produced, and no Engine component is designed before
  diagnosed admission plus an offline estimate.
- **`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`:** order
  of work, task validity, diagnosis before building, what a claim may target.
- **`docs/lessons.md`:** the evidence checks, and the lesson this release
  earned — "We built the remedy for the failures we saw, and the failures we
  saw were the harness's."
- No Docker, no sandbox. The launcher is the only path to a model. Results and
  reviews are written only by their tools.

## Reading order for someone new

1. This page, then `BRIEF.md` (goal and invariants) and `ROADMAP.md` (status).
2. `docs/superpowers/specs/2026-09-15-release-one-outcome.md` — what happened.
3. `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md` — the
   rules for what comes next.
4. `evidence/2026-09-15-release-one-decision-ledger.md` — why each decision
   was made, dated, 2026-09-13 onward.
5. `docs/lessons.md`, `docs/pathologies.md`, `docs/remediations.md` — the
   catalogue, with every entry marked re-opened or settled.
6. The release-one design
   (`docs/superpowers/specs/2026-09-13-release-one-design.md`) and the phase
   plans under `docs/superpowers/plans/`: **evidence, not guidance.**

## Where the evidence lives

- **`records/`** — every run record and its committed result (36 files):
  admission, route proof, Phase 3b development, the first isolated Pi turn.
- **`~/satyrn-runs/`** — the retained cells: transcripts, patches, receipts,
  timelines, summaries. Not in git.
- **`evidence/2026-09-15-release-one-outcome/`** — the deep review behind the
  negative, with its scripts.
- **`evidence/2026-09-15-finishing-counterfactual/`** — the pre-registered
  counterfactual: run 1's outputs, and `run-2/` with the corrected reading.
- **`scripts/`** — preflight, settings provenance, the speed probe, sequential
  design. Two carry dated "evidence, not a design input" notes.

## Known defects and open items

- **Task defects:** depth-3 at R1 and run-record-gate at R1-plan
  (`src/satyrn_evals/tasks/KNOWN_DEFECTS.md`).
- **Measurement defects, unfixed:** per-turn `max_tokens` equals the whole
  budget; over-budget worktrees are discarded ungraded; the Engine's edit
  schema allows one replacement where Baseline's allows many; the Engine
  prompt is 3–4× Baseline's and lists carried files as writable; derive admits
  paths the grader rejects. Outcome page, section "What is wrong".
- **Environment:** `/usr/bin/git` needs `sudo xcodebuild -license accept`; 4
  integration tests fail until then.
- **Local state not in git:** the `satyrn-cell` user and its sudoers rule, the
  engine export under `/Users/Shared/satyrn-cells/`, and `~/satyrn-runs`.
