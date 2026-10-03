# Phase EB — engine budget (design)

**Status:** draft for the maintainer's approval, 2026-10-02, drafted at his
request by Fable from three Opus research reports and one earlier Opus
session. Bound by `2026-09-15-release-two-r0-constraints.md` and by the order
in `ROADMAP.md`, "Next — re-derive on the confinement harness" (C1–C4).
Nothing here is built before C4 except what section 3 names.

**Rulings, 2026-10-02 (maintainer, in session).**

- The **decider** is output tokens per delivered pass, per task, never
  pooled. Peak context (`usage.input + usage.cacheRead`, max over the cell)
  and wall-clock span are **declared secondaries**, reported whatever the
  outcome. Wall clock is re-baselined under confinement on the M5 Max and is
  never compared to a release-two number.
- **Parity is not a remedy.** A change that gives the Engine what bare Pi
  already has (tool definitions, argument tolerance, anchor matching) is
  harness parity under R2 and may land in the same re-pin as the fixes
  confinement itself requires, before the first post-C4 Engine measurement.
  A change that adds behaviour aimed at a diagnosed class is a remedy and
  waits for C4 and an offline estimate (R0 §1.4).
- Every estimate carried into this phase from the 2026-09-21 comparison
  cells is **UNCONFIRMED** (isolation harness, engine `78ab87d`, M1 Pro;
  ledger entry C0). They are hypotheses to re-count on confinement cells,
  never findings to build on.

## 1. The question

Release two's declared floor-parity secondary failed: on tasks both arms
pass, the Engine delivered the same and cost more (`docs/numbers.md`, "Where
it did not help, and what it costs"; guard-prefixes 18,740 against 8,042
output tokens per delivered pass). Phase EB asks what the Engine spends that
bare Pi does not, on the confinement harness, and removes what the diagnosis
says binds — in R0's order: harness validity, diagnosed admission, offline
estimate, build, measure.

## 2. What this chat found (unconfirmed; `evidence/2026-10-02-engine-budget/`)

Ranked by output tokens on the floor tasks, with the cells that show it:

1. **The contract's test lines.** Only the Engine prompt says
   `tests/test_guard.py (new file)` and "Tests carried from the accepted
   base … 97 files". On guard-prefixes the model then surveys `tests/` (9.5
   calls before the first edit against 1) and writes a test file (4 of 4
   passes against 0 of 4). Most of the +10.7k gap; Engine higher in 15 of 16
   cell pairs. No guard fired on any floor pass.
2. **`edit` rejections.** 95 Engine calls against 3 Baseline calls fail Pi's
   schema validation across 108 cells (40 of 54 Engine cells); 82 of 95 are
   shapes Pi's own `edit` accepts or repairs. The Engine's override drops
   Pi's parameter descriptions, its four `promptGuidelines`, its argument
   normalizer and its fuzzy anchor fallback (`mutator.ts:127-159, 396-407`
   against Pi 0.85.1 `edit.js:11-92`). 0.7–2.3 retry turns per cell.
3. **The automatic self-test.** Each detected model test run triggers a
   full-suite `self_test` (~65 s on the self-hosted base; 1–3 min per pass).
   In 87 of 87 red triggered runs the failure was in a file the model had
   just run itself. The runner also runs the declared command, then declared
   + `preserve`, where `preserve` holds every tracked test file — a suspected
   double suite run, to verify.
4. **Context echo.** Every landed edit returns the post-edit region (up to
   40 lines / 4,000 B) where Pi returns one line; ~700–900 tokens per cell.
   Green self-test notes keep pytest's progress-dot lines (`COLUMNS=500`)
   and a `VIRTUAL_ENV … will be ignored` warning from `uv run --project`;
   ~1,000–1,500 tokens per selfhost cell. No pytest flag removes the dots;
   a formatter filter does (4,819 → 1,447 B, all `E` lines kept).
5. **Peak context is mostly the model's own output** staying in context
   (+10.5k on guard) rather than injection (~1.5k). The fixed per-request
   cost is *smaller* under the Engine (−125 tokens), because of item 2.
6. **Depth-3 shows no robust difference** (Engine higher in 21 of 36 pairs;
   ranges overlap). Review-script's Baseline is 2 survivors of 6.

## 3. Order

| step | when | what | done when |
|---|---|---|---|
| EB0 | after C3, same night | Development record, both arms, floor tasks, `confinement: extension`, engine at the pin, no Engine change | three records under `records/2026-10-02-eb0-*`, cells retained whole, k recorded |
| EB1 | after EB0, offline, no model | Re-derive section 2 on EB0 cells with `evidence/2026-10-02-engine-budget/cells.py`; choose the floor set by robust pairwise difference — a task is in it when both arms deliver at least 4 of 6 and one arm's output tokens per pass are higher in at least 3 of every 4 cross-arm pass pairs (27 of 36 at 6 and 6), stated before the cells are read; state the power of section 4's rule from the observed spread | a README under `evidence/` with denominators, missingness and the floor set |
| confinement fixes | before the first post-C4 Engine read | Re-export `SATYRN_CONFINEMENT_ROOT` as the Engine's own worktree for the inner Pi (`attempt.py` passes the harness's root through, which names the eval worktree; absolute paths inside the Engine worktree are refused and the cell is never admitted); make `self_test_red_stop` reach receipts (`budget.py` `GUARD_KINDS` still counts the retired `self_test_redirected`) | refusal and sibling success tests; one admitted Engine smoke cell |
| R2 parity | same re-pin | Pi's `edit` parameter descriptions and guidelines; an open item schema or a normalizer for the unambiguous shapes (single agreed per-item `path`, nested one-file, `edits` as a string); Pi's fuzzy anchor fallback; multi-file calls still refused by name | replay fixtures both directions; `tests/` on both repos green |
| EB2 | after C4, R0's order | Remedies, each with an offline estimate on EB0 cells that names its class and says whether replay can score it (a change to earlier calls cannot): the contract's test lines; edit-result echo trimming; self-test dedup after a red model run, dot filter, `VIRTUAL_ENV` strip; a light path for small requests (no created file, at most one produced symbol — separates depth-3 and guard-prefixes from every medium build on the current prompts) | an approved spec per remedy; fixture tests both directions |
| EB3 | after EB2 | Floor read under section 4, pre-registered; the primary task re-measured because the arm changed | result files under `docs/results/`; the ledger updated |

The parked engine branch `derive-new-top-level-module` stays parked; EB
cites it only if EB1 names derive.

## 4. The floor-parity rule (to pre-register at EB3)

Per floor task, n = 6 per arm, delivered passes only, denominators stated:
parity holds when the Engine's median output tokens per delivered pass is
**at most 1.25 × Baseline's** and a one-sided Mann-Whitney test of "Engine ≤
Baseline" **does not reject at 0.05**. The pairwise sign count over all
cross-arm cell pairs is reported beside it. The 1.25 margin has no evidence
behind it; EB1 replaces it with one that does, or keeps it and says so.
Power at n = 6 is low and is stated before the rule is frozen.

## 5. EB0, tonight

Three records, one per task, mirroring `records/2026-09-21-comparison-*`
with `confinement: extension` in place of `isolation`:
`agentclinic-repair-depth-3` (R2), `selfhost-guard-prefixes` (R1-plan),
`selfhost-review-script` (R1-plan); `baseline+engine`; Ornith 1.5 9B on
oMLX; n = 6; k = 3; 48,000 tokens; 72 turns; 4,800 s backstop; line 32,000 /
48; `purpose: development`; no decision rule. Run after C3 so the census
does not share the GPU. One attended Engine smoke cell on depth-3 first,
reading `confinement_refused` in its transcript.

**Pre-registered counts** (no threshold; EB1 reads them): calls before the
first edit, and how many touch `tests/`; test files written, by arm;
rejected `edit`/`write` calls by error shape; automatic self-tests per cell,
their durations, and whether the suite runs twice; edit-result bytes; note
bytes; turns from the finish steer to stop; `confinement_refused` events;
pairwise sign counts per task.

**Caveat written in advance:** until the confinement-root fix lands, Engine
cells may carry `confinement_refused` events on absolute paths; those cells
are usable for cost and for nothing else, and EB1 subtracts the retry turns
they cost.

## 6. What EB does not do

No new tasks; no change to the claim; no pooling across arms, tasks,
machines or backends; no Engine behaviour change before the first post-C4
read except section 3's confinement fixes and R2 parity; no instrument-only
piece — the context and wall-clock secondaries are computed from retained
`transcript.txt` and `timeline.jsonl`, which already carry them.

## 7. Amendments after EB1 (2026-10-03)

Recorded from `evidence/2026-10-03-eb1-read/README.md`; nothing above is rewritten.

- **Floor set.** Guard-prefixes (Engine higher in 20 of 20 pass pairs) and review-script (25 of 25). Depth-3 is out (22 of 36; 27 needed).
- **Section 2, item 3, is corrected.** The second suite run in a self-test is the declared + `preserve` run over the carried tests only; it is a distinct check, not a duplicate, and dropping it is not proposed. In section 3's EB2 row, "self-test dedup" means only skipping the automatic run after the model's own red targeted run: in 0 of 7 such runs did the Engine's run report a failure outside the files the model had just run.
- **Section 3, EB0 row.** EB0 ran before C3 (2026-10-02 21:50 to 2026-10-03 00:27), not after it. No census cell existed then, so nothing shared the GPU and nothing is contaminated.
- **Section 4's rule is weak at n = 6.** An Engine truly at 1.25 x Baseline is declared at parity 27-47% of the time; the rule separates 1.0 x from 1.5 x and above. The Baseline spread alone supports a margin of about 1.35 on guard-prefixes and 1.2-1.25 on review-script. To rule at EB3's pre-registration: a larger n, or a wider margin stated as a coarse screen.
- **A cost the remedy list does not cover.** On guard-prefixes about half the mean gap is inline `python3 -c` probing after the first edit, in 2 of 5 passes; in one the Engine's scope guard refused the model's scratch files (`/tmp/t.py`, `tests/test_scratch.py`) first. Named here, not proposed: adding a scratch path to the contract is a new remedy and needs a ruling before EB2 estimates it.
- **Admission is arm-asymmetric.** The same `/tmp` scratch write un-admits a Baseline cell (the confinement extension refuses it) and leaves an Engine cell admitted (the Engine's scope guard refuses it first). To rule before any cross-arm floor read.
- **Remedy ranking** (output tokens per delivered pass, upper bounds where replay cannot score them): the light path, up to 14,722 on guard-prefixes; the contract's test lines, up to 11,690 on guard-prefixes and 3,618 on review-script, overlapping the light path; the `edit` normalizer, median 536 on guard-prefixes and mean 1,176 on review-script. Echo trimming and self-test hygiene save context and wall clock, not output tokens.
