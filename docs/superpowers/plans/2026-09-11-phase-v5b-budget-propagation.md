# Phase V5b — propagate the engine's budget into the composed route

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans.

**Goal:** the measured packet route enforces the engine's turn/deadline budget and records exhaustion as **delivered-but-partial**, so V6 can read a phase-4 exhaustion mechanically as an ordinary failed repair.

**Why:** V5 landed in `satyrn-engine` (exit 14, partial candidate retained and validated) but the composed route does not use it. `adapters/engine_delivery.py` passes only `--timeout`/`--base`; `deliver_result_from_receipt` accepts only `OK`/`TESTS_FAILED`; `turn_budget` is still `DECLARED_NOT_APPLIED`; and no receipt budget block reaches the chain record. As wired, an exhausted phase is recorded as an implementer refusal and the retained partial work is invisible.

**Spec:** the confirmed V5 proposal and plan (`satyrn-engine`), and V4's Task 4 propagation as the precedent.

## Global constraints

- Grade from retained evidence, never stdout/exit status; a refusal test has a sibling success test.
- State denominators and missingness; never fold a missing answer into a decided one.
- Repo rule: maintainer controls commits; executors leave changes in the working tree.
- Default tier: no model, no network, no subprocess; real `deliver` runs are marked integration.

## Task 1: pass the budget through the adapter argv

**Files:** `src/satyrn_evals/adapters/engine_delivery.py`, tests

- [ ] Extend `deliver_argv` (the `--timeout`/`--base` builder) to add `--turn-limit <packet.turn_budget>` and, if the route supplies one, `--deadline-seconds <deadline>`. Decide and record whether the packet gains a `deadline_seconds` field or the route supplies a default; either way the value comes from the frozen packet, not from the model.
- [ ] TDD: a packet with `turn_budget=20` produces `--turn-limit 20`; a packet without a deadline produces no `--deadline-seconds`; a nonsensical budget is refused before the call.

## Task 2: flip the declaration ledger

**Files:** `src/satyrn_evals/chain_record.py`, tests

- [ ] `declaration_ledger` currently sets `turn_budget: DECLARED_NOT_APPLIED` (`chain_record.py:169`). When the adapter actually passes `--turn-limit` and the engine enforces it, set `turn_budget` to `APPLIED` (a code path this build can name), and the deadline field likewise. Update the golden chain record fixture.
- [ ] TDD with an `OBSERVED_COMPLIANT`-vs-`APPLIED` sibling, so "we passed the flag" never gets recorded as "the engine enforced it" unless the enforcement path is named.

## Task 3: accept BUDGET_EXHAUSTED as delivered-but-partial

**Files:** `src/satyrn_evals/adapters/engine_delivery.py`, `src/satyrn_evals/chain_record.py`, tests

- [ ] `deliver_result_from_receipt` (`~:86-102`) accepts `OK`/`TESTS_FAILED` as delivered. Add `BUDGET_EXHAUSTED` on the same terms: a retained partial candidate is **delivered-but-partial**, not a refusal. `reported_outcome` stays "were files delivered", never "did the tests pass".
- [ ] `run_and_record_engine_chain` (`~:127-203`) advances `state["base"]` to the partial candidate's commit when exhaustion is delivered-but-partial, exactly as for `OK`/`TESTS_FAILED`.
- [ ] Record the receipt's `budget` block on the phase record alongside `validation` (`PhaseRecord`), so the exhausted state survives into the chain record and an offline regrade.
- [ ] TDD: exhausted-with-partial advances the base and records `budget.state == "deadline_exhausted"`/`"turn_exhausted"`; a genuinely refused receipt does not advance; both have siblings.

## Task 4: a distinct chain stop reason for exhaustion

**Files:** `src/satyrn_evals/chain_record.py`, tests

- [ ] Give the chain a stop reason for exhaustion separate from an implementer refusal and from a `FAILED` validation, so V6's reading can be applied mechanically rather than by reading transcripts. A `FAILED` validation still stops (V4); exhaustion stops with its own reason while retaining the ref.
- [ ] TDD pinning the three distinct reasons on three synthetic chains.

## Task 5: record the readings and limits

**Files:** `ROADMAP.md` (Phase V entry), the pre-run record once written

- [ ] Add to the evaluator roadmap's Phase V entry the two confirmed readings — a phase-4 exhaustion is an ordinary failed repair (counted observation), and a passed validation on an exhausted attempt is not a completion — and the model-authored-tests limit on V4. Keep the roadmap at/under 400 lines.
- [ ] State that V6 is held until V5b lands.

## Self-review

**Scope.** V5b wires the engine's budget into the measured route and makes its record truthful. It does not change the engine, improve completion, explain phase-4 cost, or run V6.

**Ordering.** V6's pre-run record must not be written until V5b is accepted.
