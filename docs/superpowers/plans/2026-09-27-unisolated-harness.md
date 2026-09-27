# The unisolated harness — implementation plan

**Status:** for execution, 2026-09-27. Implements
`docs/superpowers/specs/2026-09-27-unisolated-harness-design.md`, approved with
the maintainer's rulings: the stronger contamination package (absence +
in-worktree confinement + audit), policy-level confinement only (no user,
`sudo`, `bwrap`, docker or container), a lexical `bash` screen accepted, the
record field named `confinement`, and the Engine arm pinned via the checkout
(§7 B) with an optional per-arm `--engine-repo`.

**Done when** the suite runs both arms end to end on a plain contributor
machine with no host setup, a deciding cell is admitted only when confinement
recorded no refusal and the audit is clean, the Engine arm refuses by name when
its checkout's HEAD is not the pin, and `just gates` plus the integration tier
are green. Re-deriving the census and the comparison is a separate plan.

**Order.** Tasks 1–7 below, in order; each commits at its boundary. No task
starts before its predecessor's acceptance is green.

## Task 1 — the confinement extension

**Files:** `packages/confinement/confinement.ts` (new), a package manifest pi
can load.

**Behaviour.** On each tool call: resolve a `read`/`edit`/`write` path against
the session cwd and refuse when it is outside; refuse a `bash` command whose
text names a protected root or a grader filename. Record every refusal as an
event the harness can count. The screen is lexical and is not a boundary; the
audit is the backstop (spec C1, C3).

**Acceptance.** A replay harness (Node, integration tier) drives the shipped
extension with: an in-worktree read (allowed), an out-of-worktree read
(refused), an in-worktree write (allowed), a `bash` naming a protected root
(refused), a `bash` naming nothing protected (allowed). Both directions, one
process.

## Task 2 — the audit core

**Files:** `src/satyrn_evals/confinement.py` (new), `tests/test_confinement.py`.

**Behaviour.** Pure functions over a transcript plus the corpus roots: enumerate
every file-tool path and every `bash` argument, resolve each against the
recorded cwd (reusing `pathology._escapes`), and flag any that reaches the
corpus root, a task directory, a hidden basename or a fixture. Return the
evidence in the shape `contamination.py` already uses.

**Acceptance.** Default tier, no model/network/subprocess. A clean transcript
flags nothing; a transcript reading a hidden file flags it with the path and
line; a transcript that copies a fixture is caught by the existing verbatim
scan. Every flag has a sibling that must not flag.

## Task 3 — both arms load the extension

**Files:** `src/satyrn_evals/attempt_pi.py`, `src/satyrn_evals/attempt_engine.py`,
`src/satyrn_evals/args.py`-adjacent tests.

**Behaviour.** `build_pi_argv` gains the explicit `--extension` under the
existing `--no-extensions`. Baseline and Engine load the same confinement
extension; the Engine keeps its own `engine.ts`/`mutator.ts`/`scope.ts`/`bounds.ts`.
The arm's documented tool surface is unchanged.

**Acceptance.** An argv test pins the extension on both arms; a parity test pins
that the two arms differ only by the Engine's own extensions and `/implement`.
Baseline's refusal is stated in the spec, not hidden.

## Task 4 — the Engine arm pins its commit via the checkout

**Files:** `src/satyrn_evals/cell_engine.py` (delete the export;
`engine_checkout_problems` replaces `verify_export`/`arm_export_problems`),
`src/satyrn_evals/attempt_engine.py`, `src/satyrn_evals/cli.py`,
`src/satyrn_evals/launch_record.py`, `tools/engine_sync.py` (unchanged),
`tests/test_cell_engine.py`, `tests/integration/test_engine_arm_pins.py`,
`arms/engine-*.json`.

**Behaviour.** The arm names `pins.engine_commit`, not a path. The engine comes
from `--engine-repo` when present, else `$SATYRN_ENGINE_REPO`, else a sibling
default. A preflight refuses by name when the checkout is absent, its HEAD is
not the pin, or its `packages/engine/*` do not match `pins.digests`. The
`cell-engine` subcommand, `CELLS_ROOT` and the export marker retire.

**Acceptance.** A checkout on the wrong commit is refused with the two shas
named (the failure this session hit); a checkout at the pin passes; the
per-arm `--engine-repo` lets two Engine arms at two commits run in one record.

## Task 5 — the record field

**Files:** `src/satyrn_evals/run_record.py`, `src/satyrn_evals/launch_record.py`,
`src/satyrn_evals/cli.py`, record fixtures and tests.

**Behaviour.** `isolation` becomes `confinement`; committed records keep
`isolation` and are read under it. `DECIDING_PURPOSES` no longer require an
isolating profile — a deciding record's condition is a clean confinement audit,
enforced at grading, not a profile gate. The `local`/`isolated`/`sandbox`
values retire.

**Acceptance.** A deciding record with `confinement` writes and launches; an
old record with `isolation` still loads; the schema test proves both keys.

## Task 6 — the portable preflight, and removing the OS surfaces

**Files:** `src/satyrn_evals/cell.py`, `src/satyrn_evals/cell_preflight.py`,
`src/satyrn_evals/workspace.py`, `src/satyrn_evals/attempt_pi.py`,
`src/satyrn_evals/attempt_engine.py`, and their tests.

**Behaviour.** The cell/sandbox preflight becomes: the confinement extension is
loadable, and the run tree holds no grader material (spec C2). The two-uid
layout, `cell_environment`, `cell_command`, `grant_maintainer`,
`share_with_cell`, `sandbox_command` and the cell-side kill retire. The
detached worktree stays.

**Acceptance.** `just gates` green; the integration tier green with no
`satyrn-cell` user and no `bwrap`; a grep proves no source imports the removed
symbols.

## Task 7 — count refusals, and state the limit

**Files:** `src/satyrn_evals/pathology.py`, `src/satyrn_evals/cell_evidence.py`,
`src/satyrn_evals/summary.py`, tests.

**Behaviour.** `confinement_refusals` joins `workspace_escapes`; the summary and
result page carry the audit outcome and the spec C4 limit ("no observed
access", not "could not access").

**Acceptance.** A transcript with a recorded refusal counts it; a clean one
counts zero; the result page renders the limit from a fixture.

## Out of scope

Re-qualifying the tasks, re-reading the census from retained transcripts,
re-deriving the comparison, and marking the ledger are the next plan; this one
stops when the harness is green and the suite runs with no host setup.
