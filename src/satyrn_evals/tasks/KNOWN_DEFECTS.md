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

The defect is addressed by rung `R2` (commit `626169d`): the prompt now names
`first.timestamp.tzinfo` as the failing value, so the third seeded defect is
determinate. The R0 §1.2 validity check passed (13 of 13 hidden tests) at
commit `df33336`, recorded in this task's manifest as its `validity` block.

## `selfhost-run-record-gate`

Prompt-ambiguity-bound at R1-plan, not capability-bound: the prompt's
wording invites `RunRecordError` into `errors.py`, which sits outside
`source_paths`, so that patch is rejected (5 of 9 cells). With `errors.py`
allowed, 8 of 9 reach 15 of 20 and fail the same five tests — the prompt's
"gate rules" read as `gate()`'s job, while the hidden suite expects
`load_run_record` to refuse.

The defect is addressed by the two recorded prompt edits (commit `ffcd5e1`):
`RunRecordError` is now defined in `run_record.py`, and the validation rules
are split from the gate's cadence rules. The R0 §1.2 validity check passed
(20 of 20 hidden tests) at commit `df33336`, recorded in this task's manifest
as its `validity` block.

## `selfhost-docs-linter`

Branch C of the R0 §1.2 `pyproject.toml` decision, and no defect. The validity
solution passed and its diff touched only `tools/lint_docs.py` and
`tests/test_doc_caps.py`, nothing outside `source_paths`, so the check found
the prompt determines the choice without `pyproject.toml`. Cell 147562's
allowlist trip was its own detour, not something the prompt requires. No
change.

## `selfhost-cell-loop`

Prompt-underdetermination at R1-plan, found by the R0 §1.2 validity check: the
R1-plan prompt did not determine that `launch_cells` creates `<night>/slots/`,
so the first validity solution failed 17 of 22 hidden tests. The maintainer
authorized a recorded prompt edit stating the launcher creates the directory
(`tools/task_specs/selfhost-cell-loop.json`, applied and re-cut here); the
re-check passed 22 of 22.

## `selfhost-speed-probe`

Prompt-ambiguity at R1-plan, found by the census class review (2026-09-17):
the cut prompt includes the plan's Steps 4 and 6 (the maintainer's attended
checklist and an isolated preflight a cell cannot run), and 6 of 9 cells
committed turns to executing them. No cell reached a pass state on the build
alone, so the primary class is capability; the ambiguity is secondary.
Maintainer's decision 2026-09-17: dropped from the ceiling set; its cells
stay in the census evidence as capability with the defect named.

## Admission rule

Neither task may be reused as a ceiling candidate until its defect is
fixed and the task is re-qualified under
`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md` §2 (task
validity at qualification). Both named tasks were re-qualified under R0 §2,
and the five census tasks carry `validity` blocks (this commit).
