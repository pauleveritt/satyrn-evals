# Phase V — engine gap register

**Exploratory. Not published figures.** Each row names the measure that indicates a candidate engine improvement, its population, and the observed value. No row enters a claim or denominator.

**Provenance:** read under `HEAD` 9bcda24caacf1c6ad5f2f5f4054eeb7eb4b2ac57; populations: current-prompt and phase-4-reaching Engine attempts from `/Users/pauleveritt/satyrn-smokes`, and the screen turn costs from the generated per-phase ledger.

| candidate | measure | population | observed (exploratory) | proposed change | rationale |
|---|---|---|---|---|---|
| Self-reported verification is not authoritative | verification_claim | retained Engine attempts under the final prompt | 1 of 8 attempts show a false verification claim (exploratory) | V4: grade Contract.test_command's own result on AttemptResult, independent of model text | A screen attempt fabricated a passing pytest report over a retained exit code 1; report honesty and pass/fail are separable. |
| The required self-test fails at phase 4 and is not closed | self_test_outcome | phase-4-reaching Engine attempts | 8 of 15 attempts fail their required self-test (exploratory) | V4/V6: surface the authoritative self-test outcome in the packet result so a failing required check cannot be reported as success | Redirect-trap friction recurs across the sequence and never closed via a prompt fix. |
| Phase-4 turn cost dominates the whole-attempt budget | turn_cost | screen Engine attempts versus Baseline | phase-4 turns 23, 23 (Engine) vs 8, 6 (Baseline) — per-phase ledger (exploratory) | V5: a whole-attempt turn limit and wall-clock deadline, retaining partial work | Engine uses fewer turns across phases 1-3 in total and far more on phase 4; the gap is entirely phase 4. |
| Destructive edits are frequent and restoration is not | restoration | phase-4-reaching Engine attempts | 15 destructive, 3 restoring, of 15 (exploratory) | V4: a validation boundary that makes a broken route visible before the attempt ends | The V2 classifiers measure a broader property than the published route-specific counts; the churn signal is exploratory. |
