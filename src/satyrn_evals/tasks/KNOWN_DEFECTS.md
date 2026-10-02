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

## `selfhost-preflight-quiet`

Prompt-ambiguity at R1-plan, found by the night-3 class review (2026-09-18):
the prompt (`docs/superpowers/plans/2026-09-18-preflight-quiet.md`, the
`certificate` paragraph) says `decode` is "null, or exactly
`{"tok_s", "completions", "tokens", "seconds"}`" and never states when it is
null. Three of the six night-3 cells (689196, 717272, 166645) read it as
"record decode only when it is a problem" and fail
`test_certificate_is_empty_on_a_quiet_machine_and_records_its_inputs` and the
quiet command-line test; the fourth non-pass cell (091987) fails the same
test through a different, unambiguous mistake — its `as_dict()` returns
`self.problems` (a tuple) where the prompt specifies a list. Two cells
reached a pass state, so capability stays primary on the four non-pass cells
and the ambiguity is secondary on three. The R0 §1.2 validity check did not
catch it: Sonnet read the sentence the intended way, 20 of 20, and a prompt
can be determined for Sonnet while ambiguous for a 9B model.

Maintainer's decision 2026-09-18: keep the claim two tasks wide; record the
task as authored and mixed with the ambiguity named; use it as the
development task Engine design section 7 anticipated. The recorded prompt
edit is "decode is null only when the rate is None". It is **not** applied
here: adding it and re-cutting moves `tree_digest(task_dir)`, which the
frozen night-3 record pins, and no replacement night is spent.

## `selfhost-*`: host-assumption tests (2026-09-25, Linux port)

All five self-hosted tasks carry a public suite copied from this repo at
their cut commit. Two of its tests assume the maintainer's Mac and fail on
Linux, before any cell, so `task_self_test` refused every one of them
(`launch FAILED: task self-test ...`):

- `tests/test_timing.py::test_the_residual_is_never_folded_into_the_phases_dict`
  calls `measure_timing` without `birthtime_reader`; on Linux there is no
  `st_birthtime`, so setup and command stay combined as `setup_and_command`,
  which the assertion forbids. The parent copy was made hermetic in `f6302ca`.
- `tests/test_cell_engine.py`'s `_pinned_export` (`selfhost-preflight-quiet`
  only) leaves the stand-in export group-writable under `umask 002`, so
  `verify_export` refuses it. The parent copy was fixed 2026-09-25.

Neither touches the contract, the hidden grader, the seeded bug or the
known-good patch: both are the repository's own incidental context tests.
The fix is the parent's own, applied to each base's `tests/` only, so the
revised tasks carry new `task_tree_sha256`s. They are re-qualified under R0
§2 on this host (known-good green and known-broken red, both directions).
The censuses and the release-two comparison ran on the previous revision;
their records pin those hashes and that revision is in git, so their
evidence stays theirs.

| task | before this revision | after |
|---|---|---|
| `selfhost-cell-loop` | `406487a854b78b38b615d23de3c20f18eed39b04610ce3e905ff997e542f3173` | `57d65a06c4412e5dc843d956c48c84a727916da53f4d457e0c86699c060d6370` |
| `selfhost-docs-linter` | `a8c1aaf0e2d5136be35ed6e5d2bf49cb88e06e15c7217ed0b481edfbd090b1c6` | `74ad8dc9ccb935b2d6272c531d5a593c0c1de9890f16817d08491f4d0aee3516` |
| `selfhost-run-record-gate` | `a7c74e5449d5a82e155f9e0161b793697ac9c973323818fe335297faf114ebcc` | `7ec64d916bad6e4a5a96418919c3e1a7c4d2a2800c3c0b65a5c60f4ef30f3da8` |
| `selfhost-speed-probe` | `dbb752affe8df090fa8594e8f046383c3ac57e6657fbb7c6181f31331270df28` | `a83618c5df42df0b687a532c6f2b738d08351c0bab799986c1a09ca887805a5a` |
| `selfhost-preflight-quiet` | `1edcf796591ec22e9c19187744d43706f840e4fdc05dbe790f925c06cac86aa0` | `5921477554353022e45d4fc5113c67ac1deadc77e9b8ee68ae962781905efa20` |

## Admission rule

No task named here may be reused as a ceiling candidate until its defect is
fixed and the task is re-qualified under
`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md` §2 (task
validity at qualification). depth-3 and run-record-gate were re-qualified
under R0 §2, and the five census tasks carry `validity` blocks (this commit).
