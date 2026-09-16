# Census task-validity runs — 2026-09-16

The R0 §1.2 task-validity check
(`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`) for the five
census tasks. Each task was cut with its prompt, solved from the prompt alone,
and graded by its hidden acceptance suite. The runs previously lived only in the
scratch tree and `~/satyrn-census-grades`; they are preserved here so the check
can be audited. `selfhost-cell-loop`'s run is `selfhost-cell-loop-r3`, the
re-validated amended prompt, filed under the canonical task name.

## Per task

| task | verdict | counts | prompt read from | named leak tells | receipt `grader_content_in_patch` |
|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | pass | 13/13 | `df33336` | clean | clean |
| selfhost-run-record-gate | pass | 20/20 | `df33336` | clean | clean |
| selfhost-docs-linter | pass | 15/15 | `df33336` | clean | clean |
| selfhost-cell-loop | pass | 22/22 (amended prompt) | `fc870ba` | clean | flagged |
| selfhost-speed-probe | pass | 17/17 | `df33336` | clean | flagged |

Verdict and count are read from each task's `receipt.json`
(`verdict` and the length of `evidence.executed_test_ids`).

## Model

`deepseek-v4-flash`. The harness has one configured agent model and no per-task
selector, so the design's named Sonnet agent could not be selected. The
maintainer ratified this substitution on 2026-09-16 as the instrument for R0
§1.2, as a deliberate deviation from the design's Sonnet wording. The manifests'
`validity.by` record the same string. Read the five certifications as slightly
weaker than the design's Sonnet intended: if a task turns out easier than
expected, that is the trigger to re-check it on the named instrument before
trusting its certificate.

## Leak tells

Checked each task's `solution.diff` and `REPORT.md` for any id in the task's
`expected_test_ids`, and for the strings `overlay`, `known-good.patch`,
`known-broken.patch`, `manifest.json`, or the task directory path. All five are
clean on that named check.

The table's last column is the receipts' own separate
`contamination.grader_content_in_patch` field, which reads `flagged` for
`selfhost-cell-loop` and `selfhost-speed-probe` (the solver's own test file
shares a block with the hidden overlay at the same path). That is the receipt's
separate overlay-content check, not the named leak-tell check above.

## Source

Copied from the retained runs, not recomputed: `solution.diff`, `REPORT.md`, and
`PROMPT.txt` from the scratch validity tree; `receipt.json` from
`~/satyrn-census-grades`. No model run is reproducible offline.
