# Census task-validity run — 2026-09-17

The R0 §1.2 task-validity check
(`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`) for the
newly authored `selfhost-preflight-quiet` task. The task was cut with its
prompt, solved from the prompt and a copy of `base/` alone, and graded by its
hidden acceptance suite.

This task has been solved and graded **twice**. Round 1's certificate
certified a prompt that has since changed (the `cores` interface line and
the two CLI tests — findings F1 and F2, see Runs below), so it is
superseded as a certificate and kept as history, not overwritten. Round 2 is
the certificate in force for `evidence/2026-09-18-census-3/`.

## Per run

| run | task | verdict | counts | prompt read from | named leak tells | receipt `grader_content_in_patch` |
|---|---|---|---|---|---|---|
| run-1 (superseded) | selfhost-preflight-quiet | pass | 20/20 | `d6c2691` | clean | flagged |
| run-2 (in force) | selfhost-preflight-quiet | pass | 20/20 | `f7a10d7` | clean | flagged |

Verdict and count are read from each run's `receipt.json` (`verdict` and the
length of `evidence.executed_test_ids`). `grader_content_in_patch` is not a
top-level receipt field — it lives at `receipt["contamination"]["checks"]`
— and is reported here as its own column, never conflated with the two
named leak tells below.

## Runs

**run-1 (superseded).** Solved and graded against the round-1 heading, before
the maintainer's 2026-09-18 re-cut ruling. The whole-path review surfaced two
tree-touching findings against that heading: **F1**, the hidden suite no
longer graded two CLI defaults after an earlier fix-round test edit, and
**F2**, the prompt's `Interfaces:` line for `main`'s injected `cores` reader
rendered ambiguously as either a value or a callable. The maintainer ruled
"proceed": fix both in the heading document and re-cut. Round 1's certificate
therefore certifies a prompt tree that no longer exists in the committed
task; its artefacts are kept at `run-1/` for the record, not deleted, and are
not the certificate this task presents to the night.

**run-2 (in force).** Solved and graded against the re-cut heading (F1 and
F2 fixed) and, further, against a `base` that the controller moved back to
`3f7a561931e4c4fabb79991756359d6d6c9c9aac` after finding R2-F1 below. This is
the certificate `evidence/2026-09-18-census-3/` admits.

### A superseded interim run (not committed)

Before `base` moved to `3f7a561931e4c4fabb79991756359d6d6c9c9aac`, a first
round-2 solve was already run and graded against an interim base
(`3cd88a6ce1e6987293dfa638337d8594535bffd3`), and it also returned
`verdict: pass`, 20 of 20, `patch_digest` beginning `773b53b49f826b81…`. That
run is superseded, not voided — it correctly certified a base tree that the
night will not use. Its artefacts are outside git and may be cleaned up:
the solve tree and diff at
`/Users/pauleveritt/satyrn-authored-task-scratch/validity-r2/selfhost-preflight-quiet/`
(`PROMPT.txt`, `solution.diff`, `tree/`), and the receipt at
`/Users/pauleveritt/satyrn-census-grades/validity-r2/selfhost-preflight-quiet/receipt.json`.
No `run-2a/` directory was created for them. If a reader later finds a
passing receipt for this task with no home in this tree, this paragraph is
its home.

### Why `base` moved (finding R2-F1)

At the interim base (`3cd88a6`), the repository's own `qualify.CENSUS_TASKS`
already named `selfhost-preflight-quiet` — `tests/test_agentclinic_manifests.py`
reaches it not by naming it textually but by iterating `CENSUS_TASKS`
(`assert len(CENSUS_TASKS) == 6`, then a per-task loop) — and three golden
tables named it textually: `tests/test_census_records_frozen.py`
(`AUTHORED = {"selfhost-preflight-quiet"}`), `tests/test_cut_task.py`
(a literal in its task-name list), and
`tests/test_writable_paths_declaration.py` (a literal key in its path
table). Meanwhile the generator's own exclusions correctly
removed the task's own cut tree and cut spec from `base/` — so the cell's
public suite inside `base/` named a task whose files did not exist there.
Measured: **5 failed, 2487 passed**, and the failures named this task's own
cell. That is a confound on the class the census measures (nights 1 and 2
gave every cell a green suite at `base`), not something to disclose and move
past, so the controller fixed it: `base` was moved back to
`3f7a561931e4c4fabb79991756359d6d6c9c9aac`, the last commit before anything
about this task existed in code, while `plan.commit` stayed pinned at
`3cd88a6ce1e6987293dfa638337d8594535bffd3` — the heading document's own
commit, which does not need to equal `base`. Every commit carrying the
revised heading also carries round 1's own cut tree and validity artefacts,
so only the pre-task commit keeps the cell's public suite green. Measured
inside the moved `base/`: **2462 passed, 0 failed, 336 deselected, 33.2 s**.
`good` was re-cut as `f7459ef5a4ccece490c8a7cb48a8e0dfea713d6b`, parent
exactly `base`.

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

Both the heading document (`docs/superpowers/plans/`) and the authored-task
design spec (`docs/superpowers/specs/`) are excluded from `base/` by the
same tuple, the generator's own `EXCLUDED_PREFIXES = ("docs/superpowers/plans/",
"docs/superpowers/specs/", ".claude/", ".github/")` at `tools/cut_task.py:67`,
not by an instruction given to the solver.

**The third maintainer-ordered heading edit (undisclosed until now).** Beyond
F1 and F2 above, the maintainer's re-cut also dropped one declared symbol,
`Certificate.as_dict`, from the heading's `Interfaces: Produces:` line, so
the task is not at exactly 10 produced symbols -- the Engine's medium-class
predicate being at most 10. `Produces:` is now 9. This is deliberate, not an
omission: `as_dict()` remains fully determined without a `Produces:` line of
its own, by the Step 6 prose (which names the method and what it returns)
and by the `formats` string the spec carries (which fixes its JSON shape).
A night-3 reader who counts 9 rather than 10 and wonders whether a symbol
went undocumented should read this paragraph as the answer.

**Where this note must travel.** The `grader_content_in_patch` known-false-
positive note above (the `block` hit on the canonical eight-name import
list) is recorded under this task's `evidence/2026-09-17-census-2/`
directory, but the census night this task will actually run in is night 3.
This note must travel with the task to whoever reads night 3's receipts:
the false positive will recur there too, under
`evidence/2026-09-18-census-3/`, and that directory's own reader should be
pointed back here rather than re-discovering the same "flagged, not
contamination" finding from scratch. The record's own text above is fixed
by the plan and is not being changed; this paragraph is the pointer.

## Disclosed, not fixed: I2 and three parked literals

A whole-path review of the hidden suite found four places where the
suite is more lenient than the prompt's own prose — most notably I2, the
`ps`-line "at most three fields" rule, which the suite cannot distinguish
from a bare `split()`, with the consequence that a mutant built that way
reports a 93.1%-cpu process as not busy. Closing any of these means
editing the frozen heading, which would move `base` and orphan `good`, so
the maintainer's ruling is to disclose and instrument them rather than fix
them. The full writeup, including the re-measured 20-passed/20-passed
comparison and the `busy_processes(...) -> []` consequence, is at
`evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/README.md`.
The pre-registered night-3 read that counts all four is
`evidence/2026-09-18-census-3/postreg.md`.

## Leak tells

**Which form of the id tell was checked.** The procedure's own tell (Ruling
5) is "any id from the manifest's `expected_test_ids` appearing" in the
run's `solution.diff` or `REPORT.md`, and an id has the full form
`test_preflight_quiet.py::test_load_problem_names_the_one_minute_load_over_the_ceiling`
-- module, `::`, function name. In that strict form both runs are **clean**
against both the round-1 and round-2 id lists (which are in fact identical
lists), confirmed below and pinned by `tests/test_validity_leak_forms.py`.

A **looser** reading some readers might apply -- the bare test *function*
name, without the `::` -- is not what the procedure defines as the tell,
and disclosing it here rather than leaving a reader to find it unassisted:
under that looser comparison, `run-1/solution.diff` has exactly **one**
hit, `test_decode_rate_is_none_with_fewer_than_last_completions`; `run-2`
has none, and neither `REPORT.md` has any. That one hit is convergent
naming, not a leak -- the solver could not read the overlay, the strict
tell (the actual procedure) is clean on it, and none of run-1's other test
names collide. It is disclosed here, with the run and the name, so a reader
who applies the looser reading is not left thinking a tell fired silently.

Checked each run's `solution.diff` and `REPORT.md` for any id in the task's
`expected_test_ids`, and for the strings `overlay`, `known-good.patch`,
`known-broken.patch`, `manifest.json`, `tasks/selfhost-preflight-quiet`, or
`2026-09-18-preflight-quiet.md`:

```bash
D=evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet
grep -no -E 'overlay|known-good\.patch|known-broken\.patch|manifest\.json|tasks/selfhost-preflight-quiet|2026-09-18-preflight-quiet\.md' \
  "$D/run-2/solution.diff" "$D/run-1/solution.diff" "$D/run-1/REPORT.md"
# (no output from any of the three -- clean)
tail -n +10 "$D/run-2/REPORT.md" | grep -no -E 'overlay|known-good\.patch|known-broken\.patch|manifest\.json|tasks/selfhost-preflight-quiet|2026-09-18-preflight-quiet\.md'
# (no output -- clean)
```

Both `solution.diff` files and `run-1/REPORT.md` are clean outright. For
`run-2/REPORT.md`, the check is scoped to the solver's verbatim text —
lines 11-57, everything after the `---` separator at line 10 — which is
clean, as the command above shows (`tail -n +10` includes the separator
line itself, which matches nothing). Lines 1-8 of `run-2/REPORT.md` are the
**controller's own preamble**, not the solver's words: it records the run
metadata and, in doing so, recites the off-limits list the solver was
given, which itself names `overlay`, `manifest.json` and
`2026-09-18-preflight-quiet.md`. Run against the whole file rather than the
scoped range, the same grep does hit those three strings at lines 5-7 of
the preamble:

```bash
grep -no -E 'overlay|known-good\.patch|known-broken\.patch|manifest\.json|tasks/selfhost-preflight-quiet|2026-09-18-preflight-quiet\.md' \
  "$D/run-2/REPORT.md"
# 5:overlay
# 6:manifest.json
# 7:2026-09-18-preflight-quiet.md
```

Disclosed here so a reader who greps the whole file is not left thinking a
tell fired: it did not — the hits are the controller's recitation of the
off-limits list, not the solver naming anything it was told not to touch.
Both named tells are clean on both runs' actual solver output. Run-2's
harvested diff (451 lines) touches `PROVENANCE.md`,
`scripts/preflight_quiet.py` and `tests/test_preflight_quiet.py`; run-1's
touched the same three paths against its own (since-superseded) heading.

`grader_content_in_patch` is flagged on both runs, and this is a **known
false positive on this task**, not contamination — record it that way
rather than trusting the column, and it is reported here as its own column,
never conflated with the two named tells above. Run-2's evidence is one
`block` hit: overlay path `test_preflight_quiet.py`, in
`tests/test_preflight_quiet.py`, line 16 (run-1's equivalent hit was at line
19, against the pre-fix heading). The matching block is the eight-name
canonical import list that the task spec's `formats` string itself
dictates — `IGNORE_PREFIXES, Process, Rate, busy_processes, certificate,
decode_rate, load_problem, main` — byte-identical in both files because
`formats` names exactly those eight public symbols and ruff/isort sorts them
canonically. `src/satyrn_evals/contamination.py:20` sets
`GRADER_BLOCK_LINES = 4`, so any four consecutive non-blank matching lines
flag. **It will fire again on the night for any cell that writes its own
test module** importing the task's eight public names in canonical order;
the column is a reported secondary, never a verdict, and it changes nothing
about either pass. The two named tells above are the actual leak check, and
both are clean on both runs.

## Model

**Sonnet ran run 2.** This is the instrument the validity procedure names as
the project's intended role, not night 1's `deepseek-v4-flash`. Night 1's
procedure recorded that it could not select the intended role and that the
maintainer ratified the `deepseek-v4-flash` substitution on 2026-09-16; this
harness can select the named role, so Ruling 8 ("request the named role, use
what the harness offers, record it") resolves to Sonnet here, confirmed
selectable and recorded by the controller as `validity.by`. Two consequences
follow, stated plainly rather than smoothed over:

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
the ones this task's prompt asks for. `certificate` is **not** a third
collision — there is no `certificate` function, class or variable anywhere
in `base/`; the occurrences in this task's own source and tests are the
prose words "would report a clean certificate" and "read as a silent,
clean certificate" at `src/satyrn_evals/cell_preflight.py:45,177`, plus a
third prose occurrence, the same phrasing, at
`tests/test_cell_preflight.py:186`. (The identical three lines also recur,
unchanged, inside `base/src/satyrn_evals/tasks/selfhost-cell-loop/base/`
— that task's own nested committed tree, itself part of this task's
`base/` — which is why a naive recursive `grep -r certificate base/`
returns six hits rather than three; none of the six is a symbol.) That is
why a combined leak-tell grep hits it and why that grep has to be read per
name rather than trusted as a symbol match. The prompt fully determines the new signatures for all
three names, so the contract is unambiguous, but a model that greps before
it reads can still produce a plausible wrong implementation against the two
real collisions. Unrecorded, that failure mode would read as task difficulty
rather than as a naming collision. Neither solver tripped it.

## Answer-leak channel into future base trees — now closed by construction

Round 1's README disclosed that `tools/cut_task.py`'s `EXCLUDED_PREFIXES`
did not exclude `evidence/`, so a validity `solution.diff` would ship inside
`base/` of any task cut at or after the commit that added it, and escalated
it as a finding (F3). **That escalation is now closed by construction.**
Controller Ruling R2-8, implemented and committed in Task 3 round 2, added a
global exclusion to `tools/cut_task.py`'s `excluded()`: any path matching
`path.startswith("evidence/") and "validity" in path.split("/")` is dropped
from every task's `base/`, alongside two further task-scoped exclusions (a
task's own cut tree and its own cut spec). This was measured against the
other six committed task specs (`cut_task.py check` on all of them) and
found to move no existing task tree's digest — the new exclusion was vacuous
everywhere except this task's own re-cut, where it correctly stopped this
task's `base/` from carrying the other five census tasks' `validity/`
records (previously present under
`base/evidence/2026-09-16-census/validity/`).

## Source

Round-2 artefacts copied from the retained run, not recomputed:
`run-2/solution.diff`, `run-2/REPORT.md`, and `run-2/PROMPT.txt` from
`$SCRATCH/validity-final/selfhost-preflight-quiet/`; `run-2/receipt.json`
from `$HOME/satyrn-census-grades/validity-final/selfhost-preflight-quiet/`.
Run-1's four files are `git mv`d from this same directory's previous flat
layout, unchanged in content. No model run is reproducible offline, but
either grade can be re-verified from the artefacts preserved here, run from
a directory with no `pyproject.toml`, `pytest.ini`, `.pytest.ini`,
`tox.ini`, `setup.cfg` or `conftest.py` in it or above it:

```bash
UV_OFFLINE=1 uv run --project <evals> satyrn-evals grade selfhost-preflight-quiet \
  run-2/solution.diff --receipt receipt.json
```

Run-2's preserved `receipt.json`'s `patch_digest` is
`1c6acea067a6283a9d14a233dc9f5cde2713d9aa58330a040c71ab828b0c8b3b`, which is
also the sha256 of the preserved `run-2/solution.diff` — the preserved diff
is the graded diff. Run-1's preserved `receipt.json`'s `patch_digest` begins
`700a2481465f060b…`.

## Cross-reference

Run 2 is the certificate `evidence/2026-09-18-census-3/` admits: the night
run for `selfhost-preflight-quiet` is valid only against this pass (Ruling
15).
