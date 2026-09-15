# Known defects (task corpus)

Dated 2026-09-15. Sits beside the task directories, not inside them: adding
a file inside `agentclinic-repair-depth-3/` or `selfhost-run-record-gate/`
changes the committed directory's `task_tree_sha256` (`task_tree.py`'s
`tree_digest`, which walks every file under the task root) and would make
`cut_task.py check` report drift against a freshly cut tree, so the notes
live here instead. Citing
`docs/superpowers/specs/2026-09-15-release-one-outcome.md` and
`evidence/2026-09-15-release-one-outcome/fable-review.md`.

## `agentclinic-repair-depth-3`

Information-bound at R1, not capability-bound: R1 gives only "assert None
is not None" and strips pytest's explanation line naming `tzinfo`, the one
line that names the third seeded defect. 0 of 7 cells (4 Baseline
admission, 3 Engine route proof) found the seam under identical prompts. Two cells
reached 12 of 13 and reported `models.py` untouched.

## `selfhost-run-record-gate`

Prompt-ambiguity-bound at R1-plan, not capability-bound: the prompt's
wording invites `RunRecordError` into `errors.py`, which sits outside
`source_paths`, so that patch is rejected (5 of 9 cells). With `errors.py`
allowed, 8 of 9 reach 15 of 20 and fail the same five tests — the prompt's
"gate rules" read as `gate()`'s job, while the hidden suite expects
`load_run_record` to refuse.

## Admission rule

Neither task may be reused as a ceiling candidate until its defect is
fixed and the task is re-qualified under
`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md` §2 (task
validity at qualification).
