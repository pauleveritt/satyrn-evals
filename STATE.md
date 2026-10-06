# State of the project — 2026-10-06

The one page to read first. What exists, what is proven, what is disproven,
what is decided, and what is next. Every claim here cites the file or commit
that holds it; "the ledger" is `evidence/2026-09-15-release-one-decision-ledger.md`,
cited by entry title.

## Goal

Keep a small local model on track so a Python developer can use local AI and
stay at the wheel: the developer does domain engineering (specs and tests),
not agent engineering. Two repositories, both on branch `main`:

- **`satyrn-evals`** — the eval harness: tasks, confined cells, launcher,
  grading from retained evidence. Head: the commit that adds this line;
  `phase-c1` (Phase C, the R0 agenda, the Engine re-pin and the development
  read) is merged as `341200d` (ledger "Engine pin moved to the merge commit
  5b681b0"). The engine-budget work is merged: `worktree-engine-budget` as
  `8079874` and EB2 (`eb2-estimates`) as `631ef05`.
- **`satyrn-engine`** — the product: `/implement`, a derived contract,
  guards, symbol preservation, carried tests, `self_test`, a receipt; its
  terms are in `site/engine-glossary.md`. Pinned at
  `23a0ef649dc4764bf09ca51110434b1b34ac1c27` (`arms/engine-ornith15-9b.json`),
  engine `main` after the merge of `eb-confinement-parity` (`5b681b0`) plus a
  glossary-only commit; the seven pinned
  digests equal those at `6d30479`, so cells read at `6d30479` are the same
  Engine bytes (same ledger entry).

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

These readings ran under two-uid isolation; they are concluded and stand as
evidence for the isolated condition only (ledger "C0", "Not re-opened").

## What is proven

- **On run-record-gate the pinned Engine delivers more often than bare Pi.**
  This is the first deciding Engine outcome on the confinement harness, decided
  2026-10-06. It was pre-registered at
  `docs/superpowers/specs/2026-10-05-run-record-gate-delivery-comparison.md`
  (approved `e9b3aa9`, amended §10 `9a5e668`) and decided once by a reader
  frozen before launch. Three `campaign` records, n = 12 per arm each, engine
  `23a0ef6`, Apple M5 Max. **Engine 22 of 36 delivered a passing patch within
  48,000 output tokens and 72 turns; Baseline 10 of 36; one-sided Fisher exact
  p = 0.0043** (admitted cells only: 22/36 against 10/35, p = 0.0056). The run
  had 0 replaced and 0 infrastructure cells, and no wall-clock cut.
  Secondaries: at the 32k/48 line both arms usually hold a passing tree
  (`grade-line`: Baseline 29 of 33, Engine 28 of 34), so the difference is
  finishing. Bare Pi ran out of budget in 26 of 36 cells. Total output tokens
  per delivered pass: Baseline 143,848, Engine 60,400
  (`evidence/2026-10-05-rrg-delivery/README.md`; ledger "The run-record-gate
  comparison on delivery: holds"). The claim covers one task, one model and
  one budget; the delivery endpoint was chosen after the development reads and
  is disclosed as such (pre-registration §2).
- **Confinement replaces isolation.** Two-uid and `bwrap` isolation are
  retired at `35c298d`; both arms run as the maintainer under an eval-owned Pi
  extension that refuses file-tool paths outside the worktree and bash naming
  a protected root, plus a post-hoc reach audit and an admission tally
  (`docs/superpowers/specs/2026-09-27-unisolated-harness-design.md` §3; ledger
  "C0"). The `satyrn-cell` user and its sudoers rule were removed 2026-10-03
  (ledger "C3 frozen 60a29bc"). The claim is "no observed access", never "no
  possible access" (`src/satyrn_evals/confinement.py`).
- **The census re-ran under confinement.** C3: 36 Baseline cells, six tasks,
  Apple M5 Max; admitted 36, refused 0, flagged 0, unmeasured 0, replaced 0,
  two named wall-clock cuts that stand (ledger "C3: the census re-run under
  confinement"; `evidence/2026-10-03-c3-census/README.md`, signed). C1
  re-qualified the tasks first (re-cut `7fc679f`, ledger "C1"); C2 re-signed
  the process classes with `hunting` live (ledger "C2: census process classes
  re-read", `evidence/2026-10-03-c2-hunting-reread/`).
- **C4 read `verify`; UNCONFIRMED since 2026-10-05.** The finishing
  counterfactual on the C3 census, deciding reading run 2: run-record-gate and
  preflight-quiet qualify (net 3 and 2), floor harm 0 (decision `4bc9831`). Its
  at-line and green-turn reads came from the classifier's replay. On fresh
  cells `grade-line` read Baseline 6 of 6 at the line where C3's replay read
  0 of 6, so C4, C3's at-line column and the power figures built on them are
  marked unconfirmed (ledger "Baseline line read on run-record-gate", (b)).
  C3's harness verdicts, admission and codes are not affected.
- **The harness measures what it claims.** Budget tripwire, base-commit
  harvest, per-cell evidence, offline reconstruction, and a launcher that
  stops on infrastructure failures and resumes a capped sitting. A declared
  per-record line (`line_token_budget`/`line_turn_budget`) harvests a cell's
  `line.diff` at the crossing on both arms, and `satyrn-evals grade-line`
  grades it offline (`src/satyrn_evals/line_grade.py`; ledger "Replay
  instrument piece landed").
- **k = 3 is sound** on the earlier machine: k = 1 gives 41 tok/s per stream
  and k = 3 about 89 total, 2.2×
  (`evidence/2026-09-15-finishing-counterfactual/run-2/q3stats.md`). Not
  re-derived on the M5 Max.

## What is disproven, or undetermined

- **Floor parity: a stated negative at `23a0ef6`.** On the two floor tasks,
  the Engine costs more per delivered pass than bare Pi (total output tokens ÷
  delivered passes). On guard-prefixes it is 38,497 against 23,888, with medians
  28,463 against 5,510. On review-script it is 24,847 against 13,180, with the
  Engine delivering 6 of 12 against 11 of 12 (p = 0.034)
  (`evidence/2026-10-05-eb-cell-read/README.md`). Section 4's parity rule cannot
  certify parity on guard-prefixes at n ≤ 24, so EB3 does not run and EB closes
  on the floor secondary with this negative (ledger "EB after EB2: seven
  rulings"; result draft `evidence/2026-10-05-eb2-estimates/floor-result-draft.md`,
  not yet placed).
- **No EB remedy was estimated to work.** EB2's finding is that offline
  estimation cannot discriminate here: every candidate remedy changes the
  Engine's calls from turn 1 (`evidence/2026-10-05-eb2-estimates/README.md` §6).
  A remedy, if built, is measured Engine against Engine.
- **UNCONFIRMED (35c298d), kept:** `docs/numbers.md` (Engine 16 of 24 against
  Baseline 2 of 24), the 2026-09-17 and 2026-09-19 route proofs, and the
  red-stop replay (`evidence/2026-09-23-red-stop-gate/`). C1–C4 re-derive none
  of them; they need Engine cells under confinement (ledger "C4", KEPT).
- **SUPERSEDED for building:** census nights 1–3 and their class columns
  (ledger "C3: the census re-run"), and the 2026-09-15 finishing
  counterfactual runs 1 and 2 (ledger "C4"). They stay evidence for the
  isolated condition. The sandbox Baseline set is permanently unconfirmed
  (ledger "C0").
- **The red-stop gate's receipts and the retired redirect.** `self_test_red_stop`
  now reaches receipts and `self_test_redirected` is retired, still classified
  (ledger "Engine re-pin 6d30479"). No outcome effect of either has been
  measured on this harness.
- **EB0 and EB1** (engine `1869397`) are evidence about that pin only. EB1
  §5's remedy figures labelled "upper bounds" are category medians, not bounds
  on the decider, and are UNCONFIRMED (spec §7; ledger "EB2 executed", 4).

## Current direction, 2026-10-06

**The comparison is decided:** the run-record-gate claim above holds. The
maintainer decides what it opens: how STATE.md and a release frame the claim,
and whether a second task (preflight-quiet, unconfirmed as a ceiling task since
2026-10-05) is wanted before any release claim. The results page is drafted
for the maintainer to place (`evidence/2026-10-05-rrg-delivery/result-draft.md`).

**EB is closed on the floor secondary** with the stated negative above (ledger
"EB after EB2: seven rulings"). The decider's reading is fixed: an arm's total
output tokens ÷ its delivered passes, with delivery beside it. The scratch-path
remedy is withdrawn. The light path is a product decision. A built remedy is
measured Engine against Engine on guard-prefixes. The Engine backlog line
(review-script's discarded candidate after `git commit`) is held until the next
engine change, so engine `main` stays at the pin.

**Superseded:** the 2026-10-04 at-line endpoint and its power sizing
(0.43 / 0.72). The comparison's endpoint moved to delivery (ledger "Baseline
line read on run-record-gate", (a)).

## Rules that bind the work

- **`AGENTS.md`** in each tree: read order, the unattended/attended split, and
  **"Evidence has a harness"** — a harness fix re-opens every decision it
  could have produced, and no Engine component is designed before diagnosed
  admission plus an offline estimate. Two consecutive instrument-only pieces
  stop the loop; the replay piece (`d996351`) is the first after three
  measurement pieces (ledger "R0 sitting").
- **`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`:** order
  of work, task validity, diagnosis before building, what a claim may target;
  §4's two-uid line carries a dated pointer to the confinement design (ledger
  "C4", D10).
- **`docs/lessons.md`:** the evidence checks, and the lesson this release
  earned — "We built the remedy for the failures we saw, and the failures we
  saw were the harness's."
- No Docker, no sandbox, no second user. The launcher is the only path to a
  model. Results and reviews are written only by their tools.

## Reading order for someone new

1. This page, then `BRIEF.md` (goal and invariants) and `ROADMAP.md` (status).
2. The confinement design (`docs/superpowers/specs/2026-09-27-unisolated-harness-design.md`),
   then `docs/results/2026-10-03-c3-census.md` and
   `docs/results/2026-10-03-c4-counterfactual.md` (both partly unconfirmed
   since 2026-10-05), then the comparison's pre-registration and evidence
   (`docs/superpowers/specs/2026-10-05-run-record-gate-delivery-comparison.md`,
   `evidence/2026-10-05-rrg-delivery/README.md`).
3. `docs/superpowers/specs/2026-09-15-release-one-outcome.md` — what happened;
   then the R0 constraints and the census design
   (`docs/superpowers/specs/2026-09-15-release-two-census-design.md`).
4. The ledger — why each decision was made, dated, 2026-09-13 onward; the
   2026-10-04 to 2026-10-06 entries hold the current rulings.
5. `docs/numbers.md` is UNCONFIRMED (35c298d): read it as evidence for the
   isolated condition, not as a result.
6. `docs/lessons.md`, `docs/pathologies.md`, `docs/remediations.md` — the
   catalogue, with every entry marked re-opened or settled.
7. The release-one design and the phase plans under `docs/superpowers/plans/`:
   **evidence, not guidance.**

## Where the evidence lives

- **`records/`** — every run record and its committed result (159 files),
  including the C1 census records (`2026-10-02-c1-*`), the development reads
  (`2026-10-04-dev-engine-*`, `2026-10-05-dev-baseline-*`), the EB cell reads
  (`2026-10-04-eb-*`) and the comparison (`2026-10-05-campaign-*-{a,b,c}`).
- **`~/satyrn-runs/`** — the retained cells: transcripts, patches, receipts,
  timelines, summaries. Not in git.
- **`evidence/2026-10-02-c1-preflight/`**, **`2026-10-03-c2-hunting-reread/`**,
  **`2026-10-03-c3-census/`**, **`2026-10-03-c4-counterfactual/`** — Phase C,
  each with its README.
- **`evidence/2026-10-02-engine-budget/`**, **`2026-10-03-eb1-read/`**,
  **`2026-10-05-eb-cell-read/`**, **`2026-10-05-eb2-estimates/`** — Phase EB.
  **`2026-10-05-dev-baseline-run-record-gate/`** and
  **`2026-10-05-rrg-delivery/`** — the comparison (`decide.py` is frozen by
  `tests/test_frozen_instruments.py`).
- **`evidence/2026-09-15-release-one-outcome/`**,
  **`2026-09-15-finishing-counterfactual/`**, **`2026-09-16-census/`**,
  **`2026-09-17-census-2/`**, **`2026-09-18-census-3/`** — isolated-condition
  evidence. `evidence/2026-09-16-census/classify.py` is the frozen classifier
  C3 and C4 ran by path, pinned by `tests/test_frozen_instruments.py`.
- **`scripts/`** — preflight, settings provenance, speed probe, power,
  sequential design, and the night drivers (`c3_night.sh` for C3).

## Known defects and open items

- **Collection errors score `unavailable`, not `fail`** (`docs/lessons.md`).
  When the solver's own code fails test collection, zero tests run and the
  grader reports a mismatch. In the comparison this counted against the
  Engine (D2). Not fixed.
- **Stray files make a correct patch `unavailable`.** Examples are a model's
  own test writing `docs/reviews/…`, or a scratch file. The strip-rule
  sensitivity read answers it offline; it was not run for EB.
- **The batch cap** (`CAPS` in `src/satyrn_evals/run_record.py`: n ≤ 12 per
  arm, 720 minutes) means a larger design runs as several records decided
  together (pre-registration §10).
- **Root-search and outside-worktree gap.** The extension does not refuse,
  and the audit does not count, a bash search rooted above the worktree or a
  bash command that works outside it without naming a protected path. A
  harness build item after C4, not yet built (ledger "C3 root searches").
- **The replay skips bash writers.** `classify.py` stays frozen; the
  delete-only interpreter `src/satyrn_evals/replay_ops.py` landed for
  diagnosis columns in future work and is wired into nothing (ledger "Replay
  instrument piece landed").
- **Leftover temp directories.** The launcher left an Engine deliver worktree
  and six `satyrn-attempt-*` directories in the ambient temp dir; nothing
  cleaned by hand (ledger "Engine development read", observation 1).
- **Task defects:** speed-probe's shared hidden-test failure is signed
  `ambiguity` and it is out of the ceiling set (census page; ledger "R0
  sitting"). The R1 defects of depth-3 and run-record-gate were fixed for the
  census. `src/satyrn_evals/tasks/KNOWN_DEFECTS.md`.
- **Pathology counter blind to malformed tool-call text.** `summarize` counts
  parsed `tool_calls`, so malformed `tool_call` JSON inside a text block reads
  as a plain refusal. *2026-09-24:* the block now carries
  `tool_call_text_messages` (23 of the 115 retained probe replies); blocks
  written before it lack the key (unknown, not zero), and the cells in
  `~/satyrn-runs` are not yet rescanned
  (`evidence/2026-09-22-mellum-tool-surface/`).
- **Pathology counter blind to announce-then-stop.** A final turn that plans a
  step and ends with no tool call counts as a clean `self_stop`; it ended 4 of
  12 Mellum cells. The detector in
  `evidence/2026-09-22-mellum-tool-surface/compare_ornith.py` is a regex, not a
  harness counter; none is built.
- **Mellum vs Ornith reruns owed before any model claim**
  (`evidence/2026-09-22-mellum-tool-surface/README.md`): Ornith at n = 6 on
  both arms on a freshly started server, about 20 cells per arm per model
  before a pass-rate claim, and a k = 1 run before quoting per-request speed.
- **Arm parity:** on 2026-09-21 the Engine's `DELIVER_TIMEOUT_SECONDS` was
  1800 against a 3,000 s backstop. Not re-derived against the 4,800 s backstop
  or the `23a0ef6` pin (same engine bytes as `5b681b0`).
- **Declared, not measured:** the Pi-loop length-stop semantics come from the
  design, not from a cell.
- **`tripped_verdict` has no denominator rule yet.** It is reported beside
  `verdict`, never instead of it.
- **Integration tier (not in `just gates`):** last recorded 335 passed, 1
  skipped, 0 failed at `b624b84`; not re-derived since.
- **Local state not in git:** `~/satyrn-runs`, the oMLX and Pi config, and the
  Mellum `mellum`-class MLX conversion (the broken `qwen3_moe` conversion was
  deleted 2026-09-23, so `arms/baseline-mellum-swe-pi.json` cannot be rerun
  without rebuilding it). The engine export under `/Users/Shared/satyrn-cells/`
  is retired; the Engine arm pins a checkout (ledger "C0").
