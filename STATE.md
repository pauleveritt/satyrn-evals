# State of the project — 2026-09-16

The one page to read first. What exists, what is proven, what is disproven,
what is decided, and what is next. Every claim here cites the file or commit
that holds it.

## Goal

Keep a small local model on track so a Python developer can use local AI and
stay at the wheel: the developer does domain engineering (specs and tests),
not agent engineering. Two repositories, both on branch `release-one`:

- **`satyrn-evals`** — the eval harness: tasks, isolated cells, launcher,
  grading from retained evidence. Head `ff2436c` (the census build plus its
  2026-09-16 fix wave).
- **`satyrn-engine`** — the product: `/implement`, a derived contract, four
  guards, symbol preservation, carried tests, `self_test`, a receipt. Head
  `ea49666`; the last code commit is `8049d73`, unchanged by the census.

## Where release one ended

**A stated negative, 2026-09-15**
(`docs/superpowers/specs/2026-09-15-release-one-outcome.md`). Phase 4 never
ran: the claim was `/implement` takes Ornith 1.5 9B past its ceiling within
32,000 output tokens and 48 turns, on 2 of 3 ceiling tasks, and each failed
for a reason the Engine cannot reach under identical prompts:

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
  stops on infrastructure failures and resumes a capped night. The census adds
  a per-turn 16,000 cap on both arms, a harvested-and-graded `tripped_verdict`
  (never a pass), the backstop as a gated record field, the R0 §1.2 validity
  check on all five tasks, and the classifier and night driver. Fixture tests
  both directions; no census cell has run.
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
- **Two ceiling tasks were defective, not hard**, and are addressed for the
  census: depth-3 gains rung R2 with the `tzinfo` assertion text;
  run-record-gate gets two recorded prompt edits. Both pass the R0 §1.2 check.
- **The census is frozen, not measured.** Five Baseline records exist; no cell
  has run, so no failure class is counted at a denominator yet.

## Current direction, decided 2026-09-15; census built and frozen 2026-09-16

**A pathology census before any Engine work, then the claim shape.** The
earlier "ship the Engine as a product with no outcome claim" direction was
withdrawn: a page saying the Engine does nothing good is not worth shipping.
The census is now **built and frozen**: five Baseline-only records, one per
task, at 48,000 tokens / 72 turns / 3,000 s backstop, k = 3, n = 6, per-turn
output cap 16,000, tripped worktrees harvested and graded offline as a
declared secondary that is never a pass. All five tasks passed the R0 §1.2
validity check (run on `deepseek-v4-flash`, the harness's only selectable
model; ratified by the maintainer 2026-09-16 as a deliberate deviation from the
design's Sonnet wording). **No census cell has run**; the
night is the maintainer's to launch. The release-two claim (outcome within
32k, cost at equal outcome, or a numbered ceiling at 9B) is chosen from the
classified table once it exists (census design, section 8); `ROADMAP.md`
holds the phase rows.

## Rules that bind the work

- **`AGENTS.md`** in each tree: read order, the unattended/attended split, and
  **"Evidence has a harness"** — a harness fix re-opens every decision it
  could have produced, and no Engine component is designed before diagnosed
  admission plus an offline estimate.
- **`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`:** order
  of work, task validity, diagnosis before building, what a claim may target.
- **`docs/lessons.md`:** the evidence checks, and the lesson this release
  earned — "We built the remedy for the failures we saw, and the failures we
  saw were the harness's."
- No Docker, no sandbox. The launcher is the only path to a model. Results and
  reviews are written only by their tools.

## Reading order for someone new

1. This page, then `BRIEF.md` (goal and invariants) and `ROADMAP.md` (status).
2. `docs/superpowers/specs/2026-09-15-release-one-outcome.md` — what happened;
   then `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md` and the
   census design (`docs/superpowers/specs/2026-09-15-release-two-census-design.md`)
   — the rules for what comes next.
3. `evidence/2026-09-15-release-one-decision-ledger.md` — why each decision
   was made, dated, 2026-09-13 onward.
4. `docs/lessons.md`, `docs/pathologies.md`, `docs/remediations.md` — the
   catalogue, with every entry marked re-opened or settled.
5. The release-one design
   (`docs/superpowers/specs/2026-09-13-release-one-design.md`) and the phase
   plans under `docs/superpowers/plans/`: **evidence, not guidance.**

## Where the evidence lives

- **`records/`** — every run record and its committed result (41 files):
  admission, route proof, Phase 3b development, the first isolated Pi turn,
  and five frozen census records (`2026-09-16-census-*.json`).
- **`~/satyrn-runs/`** — the retained cells: transcripts, patches, receipts,
  timelines, summaries. Not in git.
- **`evidence/2026-09-15-release-one-outcome/`** — the deep review behind the
  negative, with its scripts.
- **`evidence/2026-09-15-finishing-counterfactual/`** — the pre-registered
  counterfactual: run 1's outputs, and `run-2/` with the corrected reading.
- **`evidence/2026-09-16-census/`** — the classifier (`classify.py`); the
  classified table lands after the night.
- **`scripts/`** — preflight, settings provenance, speed probe, sequential
  design, and the frozen `census_night.sh`.

## Known defects and open items

- **Task defects:** depth-3 at R1 and run-record-gate at R1-plan were
  information- and ambiguity-bound; both are fixed for the census (R2
  assertion text; two recorded prompt edits) and pass the R0 §1.2 check.
  `selfhost-cell-loop`'s prompt-underdetermination was found and fixed by a
  recorded edit. `src/satyrn_evals/tasks/KNOWN_DEFECTS.md`.
- **Measurement defects, fixed for the census:** per-turn `max_tokens` 16,000
  on both arms; over-budget worktrees harvested and graded; the backstop a
  gated record field. **Open, for R2 parity:** the Engine's one-replacement
  edit schema, its 3–4× prompt that lists carried files as writable, and
  derive admitting paths the grader rejects.
- **Arm parity:** the Engine's `DELIVER_TIMEOUT_SECONDS` is 1800 while the
  record's backstop is 3,000, so an Engine cell stops earlier than Baseline's.
  Fix before the first Engine record of release two; not a census defect.
- **Declared, not measured:** the Pi-loop length-stop semantics (a length-cut
  turn with tool calls fails them and continues; with no tool call it ends the
  session) come from the design, not from a cell.
- **`tripped_verdict` has no denominator rule yet.** It is reported beside
  `verdict`, never instead of it, until section 8 decides.
- **The release-two claim shape is undecided** until the classified table exists.
- **Integration tier (not in `just gates`):** 335 passed, 1 skipped, 0 failed
  at `b624b84`; the census build's stale qualify expectations and launch-record
  timing were restored in that commit.
- **Local state not in git:** the `satyrn-cell` user and its sudoers rule, the
  engine export under `/Users/Shared/satyrn-cells/`, and `~/satyrn-runs`.
