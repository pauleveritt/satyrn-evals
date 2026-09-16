# Census task-validity runs — 2026-09-16

The R0 §1.2 task-validity check
(`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`) for the five
census tasks. Each task was cut with its prompt, solved from the prompt alone,
and graded by its hidden acceptance suite. The runs previously lived only in the
scratch tree and `~/satyrn-census-grades`; they are preserved here so the check
can be audited. `selfhost-cell-loop`'s run is `selfhost-cell-loop-r3`, the
re-validated amended prompt, filed under the canonical task name.

## Per task

| task | verdict | counts | prompt read from | leak tells |
|---|---|---|---|---|
| agentclinic-repair-depth-3 | pass | 13/13 | `df33336` | clean |
| selfhost-run-record-gate | pass | 20/20 | `df33336` | clean |
| selfhost-docs-linter | pass | 15/15 | `df33336` | clean |
| selfhost-cell-loop | pass | 22/22 (amended prompt) | `fc870ba` | clean |
| selfhost-speed-probe | pass | 17/17 | `df33336` | clean |

Verdict and count are read from each task's `receipt.json`
(`verdict` and the length of `evidence.executed_test_ids`).

## Model

`deepseek-v4-flash`. The harness has one configured agent model and no per-task
selector, so the design's named Sonnet agent could not be selected. This check
therefore awaits ratification by the named instrument. The manifests' `validity.by`
record the same string.

## Leak tells

Checked each task's `solution.diff` and `REPORT.md` for any id in the task's
`expected_test_ids`, and for the strings `overlay`, `known-good.patch`,
`known-broken.patch`, `manifest.json`, or the task directory path. All five are
clean.

For completeness: the receipts' own `contamination.grader_content_in_patch` field
reads `flagged` for `selfhost-cell-loop` and `selfhost-speed-probe`. That is the
receipt's separate overlay-content check, not the named leak-tell check above.

## Source

Copied from the retained runs, not recomputed: `solution.diff`, `REPORT.md`, and
`PROMPT.txt` from the scratch validity tree; `receipt.json` from
`~/satyrn-census-grades`. No model run is reproducible offline.
