# Release two, R0 — the authored third task (design)

**Status:** draft for the maintainer's review, 2026-09-17, by Fable at the
maintainer's request. Bound by `2026-09-15-release-two-r0-constraints.md`,
the census design and the night-2 design. Nothing here is built until the
maintainer approves it.

## 1. Why an authored task

The night-2 plan's Task 1 surveyed every plan on `release-one`, 50 task
headings across eleven documents, for a build-shaped task in the
run-record-gate size class not already cut. None survived
(`.superpowers/sdd/2026-09-17-release-two-census-night-2/task-1-report.md`
and `task-1-extended-report.md`). The finishing tier night 1 found is two
tasks wide, and the claim table needs three.

The product's premise is a developer who writes the spec and the tests and
lets the model build. A task written that way, for a piece of work the
maintainer actually wants, is that premise made into a census task, and it
is the one source a survey cannot exhaust. It is disclosed on the census
page as **authored, not cut**, beside the cut tasks, and never pooled with
them.

## 2. The task

**Name:** `selfhost-preflight-quiet`. **Shape:** build, one new module.

**What it builds:** the machine-quiet check the night-1 contention showed
was missing. A standalone script, `scripts/preflight_quiet.py`, with a pure
API and a CLI, that a launcher preflight can call before a night:

- `load_problem(loadavg: tuple[float, float, float], cores: int, *, ceiling: float) -> str | None`
  — the one-minute load against `ceiling × cores`.
- `busy_processes(ps_stdout: str, *, cpu_floor: float, ignore_prefixes: Sequence[str]) -> list[Process]`
  — parses `ps -axo pid,pcpu,comm` output; a process is busy above
  `cpu_floor` percent unless its executable starts with an ignored prefix
  (system agents, the model server itself).
- `decode_rate(log_lines: Iterable[str], *, model: str, last: int) -> Rate | None`
  — the token-weighted decode rate over the last `last` chat completions of
  `model` in oMLX's server log, parsed from its `Chat completion:` lines;
  `None` when there are fewer than `last`.
- `certificate(load, busy, rate, *, floor_tok_s: float) -> Certificate`
  — the problems list and a JSON-serialisable record of every input.
- CLI: `python scripts/preflight_quiet.py --model ID [--ceiling F] [--cpu-floor F] [--floor-tok-s F] [--last N]`
  prints the certificate as JSON and exits 0 when `problems` is empty, 1
  otherwise.

**Message formats the hidden suite asserts**, fixed in the spec text so the
prompt determines them: `load <one-minute> > <ceiling × cores> (<cores> cores)`;
`busy: <comm> pid <pid> at <pcpu>% cpu`; `decode <rate> tok/s < <floor> over
last <n> completions`; `decode: fewer than <n> completions for <model>`.

**Hidden suite:** `tests/test_preflight_quiet.py`, 15 to 20 tests, written
from the spec before the implementation exists: each parser on a known-good
and a known-bad input, each threshold at and across its edge, the ignore
list, the token weighting (two completions of unequal length), the
fewer-than-N case, certificate JSON shape, CLI exit codes both ways. No
network, no subprocess, no real `ps`: inputs are strings.

**Public suite:** the repository's existing tests, as for every self-hosted
task. **`source_paths`:** `scripts/preflight_quiet.py`, `tests`.
`ignored_paths`: `PROVENANCE.md`. **Size targets, measured before
admission:** hidden tests 15–20; public suite under 40 s; the good commit's
diff touches one new module and one new test module only. A task that
misses a target is re-scoped before it is admitted, never after.

Wiring the check into `launch --preflight` is a separate later commit
outside the task, so the task stays one module.

## 3. How it is authored, and who sees what

Roles are separated so no party holds both the answer and the prompt:

1. **The plan heading.** Opus writes `docs/superpowers/plans/2026-09-18-preflight-quiet.md`
   with one `### Task 1: The machine-quiet preflight` heading in the shape
   `cut_task.py` cuts: `Files:`, `Interfaces:` with `Produces:`, the steps
   as prose with fenced code, and the message-formats paragraph above as
   the spec's `formats`. It contains the hidden test module's contents in a
   fenced block, as the phase plans did, so the R1-plan rung strips it.
2. **The good commit.** Sonnet implements the heading in a worktree under
   the ordinary loop (Opus review, gates green) and commits; that commit is
   `good`, its parent is `base`. The hidden tests are the developer's
   tests: they are not edited to fit the implementation; an implementation
   that cannot pass them is fixed, or the spec is, before `good` exists.
3. **The cut.** `tools/cut_task.py` cuts the task from the plan heading at
   its commit, exactly as the six self-hosted tasks were cut; `check` exit
   0; `satyrn-evals qualify` ok; `qualify.CENSUS_TASKS` extended.
4. **Validity.** The R0 §1.2 check as night 1 ran it, by a model that neither
   wrote the heading nor the implementation, from the cut prompt and the
   base tree only, artefacts preserved under
   `evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/`. A
   validity failure that traces to a fact the spec states only in stripped
   code gets a recorded prompt edit; any other failure re-scopes the task.
5. **Disclosure.** The manifest's `generator` block records
   `authored: true`, the spec path and the authoring roles; the census page
   carries the same line.

## 4. Admission

One record, Baseline, `--purpose admission`, batch, n = 6, k = 3, 48,000
tokens, 72 turns, backstop 4,800 s, isolated, quiet machine, chained from
the last committed census result, the night-1 decision rule. Classified the
day after with the fixed classifier into `evidence/2026-09-17-census-2/`.

## 5. What it decides

If its cells show the finishing shape, the tier is three tasks wide and the
R0 sitting sizes an outcome claim on it. If they pass comfortably, it is a
floor task and the tier stays two wide. If they reach no pass state, the
size class was misjudged and the task is re-scoped, not claimed against.
Either way the census page reports it as authored.

## 6. Rules carried

Two-uid isolation; the launcher is the only path to a model; records frozen
in daylight; no Docker or sandbox; results and reviews written only by their
tools; Opus steers and reviews, Sonnet implements, no haiku; a whole-path
reviewer before launch; commits with explicit paths; never push, merge or
amend.
