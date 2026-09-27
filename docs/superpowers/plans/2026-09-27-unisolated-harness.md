# The unisolated harness — implementation plan

**Status:** in execution, updated 2026-09-27. Implements
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

## Progress

| # | Task | State |
|---|---|---|
| 1 | The confinement extension | done, `f309d2d` |
| 2 | The audit core | done, `11ff95f` |
| 3 | Both arms load the extension | done (eval `e31c3da`; engine seam below) |
| 4 | Retire OS isolation and the export; pin via the checkout | open — replaces old 4 + old 6 |
| 5 | The `confinement` record field | open |
| 6 | Refusal counts, and the stated limit | open |

Task 3's engine half lives on the engine branch `harness-extension-seam` at
`54d814d98f69fdf399884276c7d00cd5052e3ca1`, based on `release-one` `803df2d`,
author Nicola Jordan. It adds `build_pi_command(..., extra_extensions=())` and
reads `$SATYRN_EXTRA_EXTENSIONS` in `attempt`. The eval pins it only once the
PR merges (Task 4 re-pins for development in the meantime).

## Task 4 — retire OS isolation and the export; pin via the checkout

**Why this is one task, not two.** The old plan ordered "retire the export"
(4) before "remove the OS surfaces" (6). That order cannot work: the export
exists *because* of two-uid isolation — under `satyrn-cell` the cell user
cannot read the maintainer's engine checkout, so the engine is exported to a
shared cells root. Retiring the export while the profiles exist leaves the
profiles unusable, and four integration modules fail to import:

- `tests/integration/test_isolated_arms.py` (tests two-uid and the export),
- `tests/integration/test_cell_preflight.py` (cell/sandbox preflight),
- `tests/integration/test_launch_record.py` (imports `_cell_pi` from the first),
- `tests/integration/test_engine_selftest.py` (`arm_export`).

Those modules *are* the isolation test surface; they are deleted or rewritten
here, not left broken. `Task 6` and `Task 4` are therefore merged.

**Findings carried from the attempted Task 4.**

- The scoped source change is small and clean: `cell_engine.py` becomes
  `checkout_root` + `engine_checkout_problems` (absent tree, `HEAD != pin`,
  or a pinned `packages/engine` byte differing, each refused by name);
  `attempt_engine.isolated()` returns `False` for `local` and refuses an
  isolating profile by name; `cli.py`/`launch_record.py` rename the call
  (`arm_export_problems` → `engine_checkout_problems`, `arm_export` →
  `checkout_root`); the arms drop `--engine-repo` and name their commit.
- **Re-pinning moves a digest.** `runner.ts` is `c5c9f431…` at `78ab87d` but
  `d042fdd1bae9127467d82ce2225b37b17c2f463a40c51e6801b7b77d7ad99fcb` at
  `54d814d`. All three Engine arms must set the new `engine_commit` **and** the
  new `runner.ts` digest; the other six `ENGINE_SOURCES` are unchanged between
  the two commits.
- `attempt_engine.parse_args` must default `--engine-repo` (the arms no longer
  name it): `$SATYRN_ENGINE_REPO`, else the sibling `../satyrn-engine`, via
  `cell_engine.default_checkout`.

**Sub-steps, each green at its boundary.**

**4a — the export retires; the pin is the checkout.** Land the scoped source
change above and re-pin the three Engine arms to `54d814d` (updating the
`runner.ts` digest). The `isolated`/`sandbox` profiles still exist, but the
Engine arm now refuses them by name; the isolation-only test modules are
deleted here or in 4b, whichever keeps `just gates` and the integration tier
green at the boundary.

**4b — the OS surfaces retire.** Delete the `Isolation` triad's `isolated` and
`sandbox` behaviour (`cell.py`'s layout, `cell_environment`, `cell_command`,
`grant_maintainer`, `share_with_cell`, `sandbox_*`), `cell_preflight.py`,
`workspace.py`'s cell sharing and cell-side kill, `attempt.py`'s and
`attempt_pi.py`'s isolation branches, and every test that exists only for them.
A grep proving no source imports a removed symbol is part of acceptance.

**4c — the portable preflight.** Replace the cell/sandbox preflight with: the
confinement extension is loadable, and the run tree holds no grader material
(spec C2). No host user, no `bwrap`, no cells root.

**Acceptance.** A record runs both arms end to end with no `satyrn-cell` user
and no `bwrap`; a checkout at the wrong commit is refused with both shas named
(the failure this session hit); the per-arm `--engine-repo` still lets two
Engine arms at two commits run in one record; `just gates` and the integration
tier green.

## Task 5 — the `confinement` record field

**Files:** `src/satyrn_evals/run_record.py`, `src/satyrn_evals/launch_record.py`,
`src/satyrn_evals/cli.py`, record fixtures and tests.

**Behaviour.** `isolation` becomes `confinement`; committed records keep
`isolation` and are read under it. `DECIDING_PURPOSES` no longer require an
isolating profile — a deciding record's condition is a clean confinement audit,
enforced at grading, not a profile gate. The `local`/`isolated`/`sandbox`
values retire.

**Acceptance.** A deciding record with `confinement` writes and launches; an
old record with `isolation` still loads; the schema test proves both keys.

## Task 6 — count refusals, and state the limit

**Files:** `src/satyrn_evals/pathology.py`, `src/satyrn_evals/cell_evidence.py`,
`src/satyrn_evals/summary.py`, tests.

**Behaviour.** `confinement_refusals` joins `workspace_escapes`; the summary
and result page carry the audit outcome and the spec C4 limit ("no observed
access", not "could not access").

**Acceptance.** A transcript with a recorded refusal counts it; a clean one
counts zero; the result page renders the limit from a fixture.

## Out of scope

Re-qualifying the tasks, re-reading the census from retained transcripts,
re-deriving the comparison, and marking the ledger are the next plan; this one
stops when the harness is green and the suite runs with no host setup.
