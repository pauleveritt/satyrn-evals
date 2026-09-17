# Census task-validity run — 2026-09-17

The R0 §1.2 task-validity check
(`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`) for the
newly authored `selfhost-preflight-quiet` task. The task was cut with its
prompt, solved from the prompt and a copy of `base/` alone, and graded by its
hidden acceptance suite.

## Per task

| task | verdict | counts | prompt read from | named leak tells | receipt `grader_content_in_patch` |
|---|---|---|---|---|---|
| selfhost-preflight-quiet | pass | 20/20 | `d6c2691` | clean | flagged |

Verdict and count are read from `receipt.json` (`verdict` and the length of
`evidence.executed_test_ids`). `grader_content_in_patch` is not a top-level
receipt field — it lives at `receipt["contamination"]["checks"]` — and is
reported here as its own column, never conflated with the two named leak
tells below.

## Authored, not cut

Unlike the five census tasks in `evidence/2026-09-16-census/validity/`, this
task was authored rather than cut from a real commit. Its design is recorded
in `docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md`,
and its heading document is
`docs/superpowers/plans/2026-09-18-preflight-quiet.md`, written by the three
roles the design assigns: an author who wrote the heading and the acceptance
suite, a solver who worked the cut prompt blind, and a reviewer. The tree the
solver received was verified to contain no `docs/superpowers/`, no
`tests/test_preflight_quiet.py`, and no `selfhost-preflight-quiet` directory
under `src/satyrn_evals/tasks/`. The heading document is excluded from
`base/` by the generator's own `EXCLUDED_PREFIXES` in `tools/cut_task.py`,
not by an instruction given to the solver.

## Leak tells

Checked `solution.diff` and `REPORT.md` for any id in the task's
`expected_test_ids`, and for the strings `overlay`, `known-good.patch`,
`known-broken.patch`, `manifest.json`, `tasks/selfhost-preflight-quiet`, or
`2026-09-18-preflight-quiet.md`. Both named tells are clean. The harvested
diff touches exactly `PROVENANCE.md`, `scripts/preflight_quiet.py` and
`tests/test_preflight_quiet.py`.

`grader_content_in_patch` is flagged, and this is a false positive, not
contamination — record it that way rather than trusting the column. The
evidence is one `block` hit: overlay path `test_preflight_quiet.py`, in
`tests/test_preflight_quiet.py`, line 19. The matching block is the
eight-name import list — `IGNORE_PREFIXES, Process, Rate, busy_processes,
certificate, decode_rate, load_problem, main` — byte-identical in both files
because the task spec's `formats` string names exactly those eight public
symbols and ruff/isort sorts them canonically. `src/satyrn_evals/contamination.py:20`
sets `GRADER_BLOCK_LINES = 4`, so any four consecutive non-blank matching
lines flag. Any census cell that writes its own test module importing the
task's eight public names in canonical order will match this block and flag
again on the night; the column is a reported secondary, never a verdict, and
it changes nothing about this pass. The two named tells above are the actual
leak check, and both are clean.

## Model

**Sonnet ran this check.** This is the instrument the validity procedure
names as the project's intended role, not night 1's `deepseek-v4-flash`.
Night 1's procedure recorded that it could not select the intended role and
that the maintainer ratified the `deepseek-v4-flash` substitution on
2026-09-16; this harness can select the named role, so Ruling 8 ("request
the named role, use what the harness offers, record it") resolves to Sonnet
here. Two consequences follow, stated plainly rather than smoothed over:

- Night 1's standing caveat — read the certification as slightly weaker than
  the design's named instrument, and re-check on that instrument if the task
  turns out easier than expected — applies to the five cut tasks in
  `evidence/2026-09-16-census/validity/` and does **not** apply to this one.
- The six census tasks are therefore **not** certified on a single
  instrument. That is a comparability caveat the census page must carry, not
  a boast: five ran on `deepseek-v4-flash`, this one ran on Sonnet.

## Confound to watch on the night

The base tree ships functions named `decode_rate`
(`src/satyrn_evals/census_decode.py:101`, signature `(completions, *, start,
end) -> DecodeReading`) and `certificate` (`src/satyrn_evals/cell_preflight.py`),
and a `Process` class in `scripts/preflight_processes.py`, all with different
signatures from the ones this task's prompt asks for. The prompt fully
determines the new signatures, so the contract is unambiguous, but a model
that greps before it reads can produce a plausible wrong implementation.
Unrecorded, that failure mode would read as task difficulty rather than as a
naming collision. This solver did not trip it.

Also worth recording: the solver reported that the server-log path is the
one fact the prompt never states, and that it recovered
`~/.omlx/logs/server.log` from `scripts/speed_probe.py`'s docstring inside
`base/`. That is a fact the prompt leaves to the tree rather than to the
text. It did not cost the check — the hidden suite never executes the real
reader — but it belongs in the record.

## Source

Copied from the retained run, not recomputed: `solution.diff`, `REPORT.md`,
and `PROMPT.txt` from the scratch validity tree
(`$HOME/satyrn-authored-task-scratch/validity/selfhost-preflight-quiet/`);
`receipt.json` from `$HOME/satyrn-census-grades/validity/selfhost-preflight-quiet/`.
No model run is reproducible offline.

## Cross-reference

This certificate is the one `evidence/2026-09-18-census-3/` admits: the
night run for `selfhost-preflight-quiet` is valid only against this pass.
