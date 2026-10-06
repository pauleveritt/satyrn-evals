# TODO

## Now

- Investigate non-macOS initial setup and workspace isolation

## Next

- Improve onboarding with configuration and a `satyrn-setup` skill

## Soon

## Freezer

- **EB cost work: postponed 2026-10-06 until large blocks of GPU time.**
  At `23a0ef6` the Engine costs more than bare Pi on floor tasks: guard-prefixes
  5.2× by total ÷ delivered; review-script delivers 6/12 against 11/12. None
  of the candidates below was refuted; none could be scored offline (each
  changes calls from turn 1, EB2 README §6). Each needs its own
  Engine-against-Engine measurement on guard-prefixes (about 2 GPU h: 12
  remedied cells against the 12 retained `23a0ef6` cells, one-sided rank-sum),
  and certifying parity needs about 200 cells per arm. Required cut: 21,576
  tokens per delivered pass at 1.25. Design: `docs/superpowers/plans/2026-10-06-eb-replan.md`.
  - **Light path** (decision L: no): a derive-only light class (no created
    file, ≤ 1 produced symbol → no `test_command`; no digest moves). The only
    lever the size of the gap. Expect delivery near Baseline's 8/12. If
    revived, `d4abd65` lands first (decision A).
  - **Contract test lines** (survey of `tests/` plus the test file): central
    16,120. The largest partial cut; never measured.
  - **Edit-shape hoisting** (schema and `ANCHOR_MISSING` retries): 2,679.
  - **Self-test and echo trimming:** saves 34–77 s per pass and some context,
    no output tokens. It changes `runner.ts`, so it rides the next runtime
    re-pin as a wall-clock secondary.
  - **Withdrawn, do not revive:** the scratch path (bare Pi probes the same
    way). **Delivery, not cost:** the completion gate (at most +10/36 on
    run-record-gate; release one withdrew it).
  - **Any new cells** run at `9aecfb5` or later, so they also carry head
    tolerance; a pre-registration must say it can move delivery but not the
    token decider.

## Done
