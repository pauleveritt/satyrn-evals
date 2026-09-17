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
roles the design assigns and the task's own manifest records under
`generator.authoring.roles`: `heading` (Opus, from the design spec, before
any implementation existed — the heading is what carried the hidden test
module in a fenced block), `implementation` (Sonnet, in a worktree under the
ordinary loop, without editing the acceptance suite), and `validity`
(recorded in the manifest's `validity` block — this check). The README and
the manifest agree on who did what.

The tree the solver received was verified to contain no
`docs/superpowers/`, no `tests/test_preflight_quiet.py`, and no
`selfhost-preflight-quiet` directory under `src/satyrn_evals/tasks/`. A
reader can check the same three facts against the committed task tree
(the solver's tree was a copy of
`src/satyrn_evals/tasks/selfhost-preflight-quiet/base/`):

```bash
T=src/satyrn_evals/tasks/selfhost-preflight-quiet/base
test -d "$T/docs/superpowers" && echo FOUND || echo absent
test -f "$T/tests/test_preflight_quiet.py" && echo FOUND || echo absent
test -d "$T/src/satyrn_evals/tasks/selfhost-preflight-quiet" && echo FOUND || echo absent
```

The heading document is excluded from `base/` by the generator's own
`EXCLUDED_PREFIXES` in `tools/cut_task.py`, not by an instruction given to
the solver.

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

The base tree carries two real symbol collisions a model could import and
imitate: `decode_rate` (`src/satyrn_evals/census_decode.py:101`, signature
`(completions, *, start, end) -> DecodeReading`) and a `Process` class
(`scripts/preflight_processes.py:11`), both with different signatures from
the ones this task's prompt asks for. `certificate` is not a third
collision — there is no `certificate` function, class or variable anywhere
in `base/`; the only occurrences, in `src/satyrn_evals/cell_preflight.py`
at lines 45 and 177, are the prose words "would report a clean certificate"
and "read as a silent, clean certificate", not a symbol. That is why the
combined leak-tell grep hit it and why that grep has to be read per name
rather than trusted as a symbol match. The prompt fully determines the new
signatures for all three names, so the contract is unambiguous, but a model
that greps before it reads can still produce a plausible wrong
implementation against the two real collisions. Unrecorded, that failure
mode would read as task difficulty rather than as a naming collision. This
solver did not trip it.

Also worth recording: the solver reported that the server-log path is the
one fact the prompt never states, and that it recovered
`~/.omlx/logs/server.log` from `scripts/speed_probe.py`'s docstring inside
`base/`. That is a fact the prompt leaves to the tree rather than to the
text. It did not cost the check — the hidden suite never executes the real
reader — but it belongs in the record.

## Answer-leak channel into future base trees

`tools/cut_task.py`'s `EXCLUDED_PREFIXES` (`docs/superpowers/plans/`,
`docs/superpowers/specs/`, `.claude/`, `.github/`) does not exclude
`evidence/`. The `solution.diff` this README commits — a full working
solution — will therefore ship inside `base/` of any task cut at a commit at
or after `083e5dd`. This does not affect this check: this task's `base/` is
cut at `3f7a561`, which predates that commit, and it does not affect a
night-3 cell for the same reason. The channel is also not new here — this
task's own `base/` already carries all five night-1 `solution.diff` files,
under `base/evidence/2026-09-16-census/validity/`. It will affect any future
re-cut of this task at a later base, and any future authored task whose
solver reads `base/evidence/`. The fix is the maintainer's: widening
`EXCLUDED_PREFIXES` moves every existing task tree's digest and would
re-issue every record that pins one.

## Source

Copied from the retained run, not recomputed: `solution.diff`, `REPORT.md`,
and `PROMPT.txt` from the scratch validity tree
(`$HOME/satyrn-authored-task-scratch/validity/selfhost-preflight-quiet/`);
`receipt.json` from `$HOME/satyrn-census-grades/validity/selfhost-preflight-quiet/`.
No model run is reproducible offline, but the grade itself can be
re-verified from the artefacts preserved here, run from a directory with no
`pyproject.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini`, `setup.cfg` or
`conftest.py` in it or above it:

```bash
UV_OFFLINE=1 uv run --project <evals> satyrn-evals grade selfhost-preflight-quiet \
  solution.diff --receipt receipt.json
```

The preserved `receipt.json`'s `patch_digest` begins `700a2481465f060b…`; a
reader can confirm the preserved `solution.diff` is the one that was graded
by checking that a re-run reproduces that same digest.

## Cross-reference

This certificate is the one `evidence/2026-09-18-census-3/` admits: the
night run for `selfhost-preflight-quiet` is valid only against this pass.
