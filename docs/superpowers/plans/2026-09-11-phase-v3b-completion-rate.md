# Phase V3b — derive the completion-rate claims from retained verdicts

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans.

**Goal:** Replace V3's wrong `absent_artifact` label on the completion claims with a committed `completion_rate` measure that reads the retained grader verdicts and binds the population membership rule.

**Why:** every retained Engine `chain.json` carries `final_decision` with the real grader's per-phase `accepted` flag, and Baseline `session-record.json` carries the verdict too. The published `6 of 18` is computable; the gap is that no committed measure binds the population (18 vs the 21 retained chains). This is a correction to V3, not a fourth Track A cycle.

**Spec:** `docs/current/phase-v-design.md` — the V3b paragraph; Governance's object test.

## Global constraints

- Default tier: no model, no network, no subprocess; the tripwire stays armed.
- Never originate a figure: derive, or record `not_derivable` naming the missing thing.
- A refusal test has a sibling success test.
- Repo rule: maintainer controls commits; executors leave changes in the working tree.

## Task 1: the `completion_rate` measure

**Files:** `src/satyrn_evals/claim_measures.py`, `tests/test_claim_measures.py`

`completion_rate(chain, *, declared_phases: int) -> MeasureResult` reads
`chain["final_decision"]["accepted"]`:

- `yes` when the chain declares `declared_phases` and the final decision was accepted,
- `no` when it declares `declared_phases` and was not,
- `undecidable` when `final_decision` is missing/unreadable **or** the chain's
  `phases` count is shorter than `declared_phases` (this is the rule that
  separates the full-task population from the phase-2 guardrail-candidate runs).

Also `baseline_completion_rate(session_record, *, declared_phases)` reading the
Baseline verdict (its `code`/final-step `feature_verdict`).

TDD: refusal siblings for short-chain, missing-decision, unreadable-decision,
against the accepted and not-accepted success siblings.

## Task 2: bind the population and wire the claims

**Files:** `scripts/reconcile_claims.py`, `src/satyrn_evals/claim_inventory.py`

- Add a committed membership rule for the Engine attempt population (which
  retained chains are "on `agentclinic-complaint-lifecycle`", and the
  `declared_phases == 4` gate), and derive `c-engine-population`'s count from it
  rather than copying `18`.
- Wire `completion_rate` to `c-completion-6-of-18`, `c-completion-4-of-16`,
  `c-nonrestore-0-of-6`, `c-restore-4-of-7`, and the Baseline
  `c-baseline-3-of-3`, each over the population its record names.
- `c-baseline-3-of-3` reads the Baseline records; the Engine completion records
  read the Engine chains. Keep the denominators explicit.

## Task 3: reconcile and correct the labels

**Files:** `docs/current/phase-v-claim-inventory.md` (regenerated),
`src/satyrn_evals/claim_closeout.py`, `docs/current/phase-v-design.md`

- Re-run `uv run python scripts/reconcile_claims.py --runs-root ~/satyrn-smokes`.
- For the rows now derived, set the record status (`confirmed` or `corrected`)
  from the derived value; where the derived value differs from the published
  figure, that is a `corrected` finding, not a silent edit.
- Move the affected rows' `gap_kind` from `absent_artifact` to the appropriate
  kind in the audit map, dated as a correction.
- Append a dated V3b block to the design naming the derived counts, the
  membership rule, and the status changes.

**Do not reopen:** the redirect-trap classifiers, the `6 of 10` prompt-state
denominator, or the `9 of 15` reopen decision.
