# Pre-registration: the run-record-gate comparison, on delivery

**Status: draft for the maintainer's approval, 2026-10-05.** Drafted by an agent (Opus) at the maintainer's request ("Yes to all three, draft the pre-registration"). The rulings it rests on are in the ledger:
- "2026-10-05 — EB after EB2: seven rulings", items 2, 4 and 5
- "2026-10-05 — Baseline line read on run-record-gate…", rulings (a)–(c)
- "R0 sitting: rulings on the agenda", §8.3 (a): the Engine as pinned, no finish-on-green build

No record is issued, and no cell runs, until the maintainer approves this text and answers §9's decisions. Once approved, it changes only through a dated, superseding entry in the ledger.

## 1. Question

On `selfhost-run-record-gate` (R1-plan), under confinement, does the pinned Engine deliver a passing patch within the run budget more often than bare Pi?

**Smallest honest claim, if the rule rejects:** on one medium self-hosted task under confinement, the pinned Engine (`satyrn-engine` `23a0ef6`) driving Ornith 1.5 9B delivers a passing patch within 48,000 output tokens and 72 turns more often than bare Pi with the same model. One task, one model, one budget. Nothing pools with any other read.

**If it does not reject:** a stated negative at this n. No difference is shown; the power in §6 says how much that negative is worth.

## 2. Why this endpoint (disclosed)

The deciding endpoint was pass at the 32k/48 line until 2026-10-05. On that endpoint neither arm has headroom on this task: Baseline 6 of 6 at the line (`evidence/2026-10-05-dev-baseline-run-record-gate/`), and the Engine 5 of 5 with 1 excluded (ledger, "Replay instrument piece landed"). The arms differ in delivery. Every Baseline cell reaches a passing tree before the line and keeps working to the budget edge. Today 0 of 6 delivered and C3 delivered 4 of 6; in both nights the cells ran 60–72 turns. The Engine delivered 4 of 6. The endpoint was chosen after these readings were seen. That is an informed selection, legitimate when disclosed (`BRIEF.md`, "An informed selection is legitimate"), and the readings are all in committed files. The readings the R0 sitting used for an at-line Baseline rate came from the classifier's replay and are marked unconfirmed (ledger, ruling (b) of the entry above).

## 3. Arms, task and conditions (fixed)

| item | value |
|---|---|
| task | `selfhost-run-record-gate`, rung R1-plan, `task_tree_sha256` `068f216e08ef0abee4d3f2b1042ed38d68aaac5a638004c06a1052e03f52be05` |
| Baseline arm | `arms/baseline-ornith15-9b.json` (Pi 0.85.1, no product extensions, plus the confinement extension) |
| Engine arm | `arms/engine-ornith15-9b.json`, engine `23a0ef649dc4764bf09ca51110434b1b34ac1c27` with its seven pinned digests; checkout `../satyrn-engine` with HEAD at the pin, and `SATYRN_ENGINE_REPO` unset |
| model, backend | `omlx/Ornith-1.5-9B-MLX-8bit` on oMLX, Apple M5 Max 128 GiB |
| condition | `confinement: extension`, cold |
| budget | 48,000 output tokens and 72 turns per cell; command backstop 4,800 s |
| declared line | 32,000 tokens and 48 turns, for the secondary in §5 only |
| concurrency | k = 3, arms interleaved by the launcher (`arm: baseline+engine`) |
| record | one `campaign` record, n per arm per §9 D1, purpose `campaign` (a deciding purpose: no `--no-hunt`, `--no-settings`, `--timeout`, `--attempt-timeout` or path-prefix seam) |
| stop rule | established infrastructure failure only. An infrastructure stop is not relaunched unattended. A capped sitting may be resumed under the same record by the maintainer's word. A wall-clock cut is named, never re-measured. |

The Engine's backlog line from the 2026-10-05 rulings (item 7) is held until after this run, so engine `main` stays at the pin (ledger item 7, held 2026-10-05).

## 4. Counting (fixed)

Each finished, unreplaced cell of the record gets exactly one class. Classes are read from the hook-written `attempt.json` and `receipt.json`, never from stdout or exit status.

| class | definition |
|---|---|
| **delivered** | harness verdict `pass` (attempt code `OK`) |
| **not delivered** | any model-side outcome without a `pass` verdict: `fail`, `BUDGET_EXCEEDED`, `NO_PATCH`, `COMMAND_TIMEOUT` in the command phase, or the Engine's `discarded` |
| **unavailable** | harness verdict `unavailable` (a stray non-source file, a collection error with 0 tests executed, a test-ID mismatch). Counted per §9 D2. |
| **infrastructure** | a code the launcher classifies as infrastructure. The launcher replaces or stops by its own rules; never counted. |

**Admission (fixed, per §9 D3).** A cell whose `attempt.json` records any confinement *reach* outside the worktree is excluded from both arms' denominators and listed by name. A cell with only *refusals* (access the extension prevented) stays in. A second count, admitted cells only (no refusals and no reaches), is reported beside it, and the claim stands only if the rule rejects on both counts.

Denominators are stated per arm, with every excluded or reclassified cell named.

## 5. The decision rule (fixed)

- **Test:** one-sided Fisher exact test on delivered counts, H1: the Engine's delivery rate exceeds Baseline's, α = 0.05.
- **Reject** on the primary count and on the admitted-only count: the claim in §1 holds.
- **Reject on one count only:** reported as not holding, with both p values.
- **Not reject:** the stated negative in §1.

**Secondaries, reported and never deciding:**
1. Pass at the 32k/48 line, both arms, by `satyrn-evals grade-line`, `unavailable` excluded and listed.
2. Total output tokens ÷ delivered passes per arm (the EB decider's reading, ruled 2026-10-05), with the median over delivered passes beside it.
3. Turns and output tokens at stop, per arm.
4. Wall clock per arm. It is shared under k = 3 interleaving, so it is descriptive only.
5. Confinement refusals and reaches, per arm.
6. The Engine's guard firings from its receipts, notably `finish_nudged`.

Nothing is pooled with the development reads (2026-10-04 Engine, 2026-10-05 Baseline), with C3, or with any release-one or release-two cell.

## 6. Power (exact, one-sided Fisher at α = 0.05)

Planning inputs, not results:
- **Baseline delivery:** 4 of 6 in C3 (no line declared) and 0 of 6 on 2026-10-05, on the same task tree. Together that is about 1 in 3, but the two are not pooled for any decision.
- **Engine delivery:** 4 of 6 in the 2026-10-04 development read.

| stipulated Engine | Baseline | n = 12 | n = 24 | n = 36 |
|---|---|---|---|---|
| 0.75 | 0 | 1.00 | 1.00 | 1.00 |
| 0.75 | 1/6 | 0.89 | 0.99 | 1.00 |
| 0.75 | 1/3 | 0.60 | 0.87 | 0.97 |
| 0.75 | 1/2 | 0.26 | 0.45 | 0.65 |
| 0.75 | 2/3 | 0.06 | 0.09 | 0.13 |
| 0.67 | 0 | 1.00 | 1.00 | 1.00 |
| 0.67 | 1/6 | 0.77 | 0.97 | 1.00 |
| 0.67 | 1/3 | 0.42 | 0.68 | 0.87 |
| 0.67 | 1/2 | 0.15 | 0.23 | 0.36 |
| 0.67 | 2/3 | 0.03 | 0.03 | 0.03 |

The figures come from exact enumeration over both arms' binomial outcomes, rejecting where the one-sided Fisher p ≤ 0.05.

Ruling 5 of 2026-10-05 set the stipulated Engine rate at 0.75, below the Engine's observed rate *at the line* (5 of 6). On the delivery endpoint the Engine's observed rate is 4 of 6 (0.67). At 0.75 the stipulation would sit *above* what was observed, the optimistic error that ruling warns against (§9 D4).

**GPU time** (six cells per arm took about 1.5 h on either arm at k = 3): n = 12 is about 5.9 h, n = 24 about 11.7 h, n = 36 about 17.6 h, all for both arms. A run longer than one night is split into sittings under the same record.

## 7. What is not read

- Nothing about preflight-quiet or any other task.
- No offline counterfactual and no replay class column decides anything.
- No Engine change. The Engine is measured as pinned.

## 8. Deliverables, after approval

1. The ledger records the approval and §9's answers.
2. One frozen record, `records/<date>-campaign-selfhost-run-record-gate.json`, carrying this file's path and commit in its decision rule, issued by `satyrn-evals record new` and committed after green gates.
3. Preflight. Then the run, launched only with the maintainer's word.
4. The result file, written by the launcher, committed after green gates.
5. One reader, offline, applying §4 and §5 exactly. It is built and tested on synthetic cells *before* the record is launched, its digest is frozen, and it is run once on the result.
6. An evidence page and a results-page draft for the maintainer to place.

## 9. Decisions for the maintainer (each with a recommendation)

- **D1, n per arm.** Recommended: **n = 36** (about 17.6 GPU h, two or three sittings). At the conservative planning point (Engine 0.67, Baseline 1/3) its power is 0.87. n = 24 (11.7 h) gives 0.68 there, and 0.87 only if the Engine is truly at 0.75. If wrong: n = 36 spends about 6 GPU h more than needed if Baseline is near 1/6; n = 24 leaves a one-in-three chance of an uninterpretable negative at the conservative point.
- **D2, `unavailable` cells.** Recommended: **Baseline-favouring.** An Engine `unavailable` counts as not delivered and a Baseline `unavailable` counts as delivered, as the 2026-10-04 ruling's text has it. The alternative, excluding them from both denominators, is reported beside it. If wrong: the test is slightly conservative; it cannot inflate the claim.
- **D3, admission.** Recommended: **as in §4.** Exclude cells with reaches, keep cells with refusals only, and require rejection on the admitted-only count too. If wrong: the double requirement costs some power when Baseline's `/tmp` refusals are frequent; it cannot inflate the claim.
- **D4, stipulated Engine rate for sizing.** Recommended: **0.67** (the observed 4 of 6), not ruling 5's 0.75, because on this endpoint 0.75 is optimistic. If wrong: n larger than needed by about a third.
- **D5, the reader.** Recommended: **built and frozen before launch** (§8 item 5), on synthetic cells, so the one run cannot shape it. If wrong: one small instrument piece before the run; it is the piece this decision needs.
