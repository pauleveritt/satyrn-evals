> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V5c close-out — branch reconciliation and the post-V5c re-probe record: design spec

**Phase:** V5c close-out (`ROADMAP.md`). **Date:** 2026-09-03.
**Status:** design approved by the maintainer 2026-09-03; execution
proceeding per the sequence below. No implementation plan follows — this
cycle produces no new feature code: git operations, executing an
already-pre-registered protocol, and recording results. This is the V5a
precedent (documentation only, no code).

## Decisions of record

Recorded here because they were made in this session and every later reader
needs them with their evidence.

1. **Branch as record.** `research/local-pings-reprobe` is the V5c record of
   record; its design spec
   (`docs/superpowers/specs/2026-09-02-v5c-capture-admitted-suite-design.md`)
   is ratified as-is — proposal confirmed by the maintainer 2026-09-02
   (spec `:4-5`, commit `09fbf3d`), amendment maintainer-confirmed (spec
   `:7-9`, commit `60aea7a`).
2. **The missing implementation plan stays missing.** The deviation recorded
   in the spec (`:237-253`) and commit `36d7974` is ratified: no
   retrospective plan is written. A retrospective document cannot restore
   the pre-code review checkpoints it skipped, and would document history
   inaccurately.
3. **The re-probe is post-V5c reconciliation work**, not unfinished V5c
   implementation. V5c's capture work is closed (V5c spec Out of scope:
   "Running the loop. The step after this phase, not part of it"). The
   re-probe exists to re-earn or revise the admission evidence under the
   captured task's five-id oracle; its record is the re-probe protocol
   document and the V5a caveat — never a V5c artifact.
4. **Publication scope is V5c only.** Main is published to `36d7974` (the
   `research/local-pings-reprobe` tip). V5d remains a separate, unconfirmed
   proposal on branch `v5d-realmodel-smoke-check`; that dedicated proposal
   branch is the appropriate record, and no V5d row or doc reaches main
   before its own confirmation. "One direction at a time" applies to
   proposals, not only to code.
5. **Mechanics: fast-forward.** `git merge --ff-only 36d7974` — verified
   ancestry (`git merge-base --is-ancestor main 36d7974` exit 0; merge-base
   `5a809d2`, exactly main's tip). Rebase and cherry-pick would rewrite or
   duplicate 18 committed commits for no gain. The uncommitted
   `docs/glossary.md` edit is unaffected: the branch's diff does not touch
   that file.
6. **Provenance corrections to record** (in the results section — never by
   editing pre-registered text):
   - the re-probe protocol's Conditions line (`:75-76`) names branch
     `v5c-capture-admitted-suite`; execution actually used the worktree
     `.worktrees/v5c-capture-admitted-suite`, branch
     `research/local-pings-reprobe` @ `36d7974`, clean tree at run time
     (the attempt records' command lines name that path; `git status` in
     the worktree is clean);
   - commit `96a1282`'s message says "record smoke outcomes — baseline
     pass" but its sole diff changes the baseline wrapper's model flag to
     the space form; the baseline smoke outcome is unrecorded in the
     repository until this cycle's results section (scratch
     `runs/baseline-smoke/`: n=1, `OK`, verdict pass 1/1);
   - the baseline arm's eight attempts (2026-09-03, 12:14–13:12) postdate
     the branch tip and are likewise unrecorded until the results section.

## What ships

Docs and git operations only — no new feature code, no CLI, no schema
change. The captured task, its two-tier tests, and the integration
dependency group arrive on main exactly as committed on the branch. New
writing: this spec; a dated results section appended to
`docs/superpowers/research/2026-09-03-local-pings-reprobe-protocol.md`; a
dated update to the V5a admission caveat
(`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md`).

## Execution sequence

1. **Pre-flight** (re-verified at execution time): the local server's
   `/v1/models` serves `gemma-4-12B-it-MLX-8bit`; shim `arms/pi` and the
   engine binary are present; the worktree is clean;
   `git merge-base --is-ancestor main 36d7974` exits 0; `git status`
   shows only `docs/glossary.md`.
2. **Reconcile:** on main, `git merge --ff-only 36d7974`; verify
   `git merge-base --is-ancestor 36d7974 main`; run the default suite
   (`.venv/bin/pytest -q`) — the captured task's manifest-shape test is
   default tier; confirm `docs/glossary.md` is still modified and
   otherwise untouched.
3. **Environment:** `uv sync --group integration` — the oracle needs
   svcs's sybil/attrs/pytest-asyncio, declared by the arrived
   `pyproject.toml`.
4. **Commit this spec** on main — record before execution.
5. **Run the engine arm** per the pre-registered protocol, unchanged:
   n=8, `--timeout 900`, the compat shim on `PATH` (`arms/` first),
   `SATYRN_MODEL=omlx/gemma-4-12B-it-MLX-8bit`,
   `SATYRN_ENGINE_REPO=~/projects/pauleveritt/satyrn-engine`, output to
   durable scratch `runs/engine/`. Executed from main's tree at
   `36d7974` — the same commit content the baseline arm ran (worktree
   @ `36d7974`, clean); the path difference is recorded in the results
   section.
6. **Record results** (section below); one commit.
7. **Update the V5a caveat** strictly from the recorded numbers; a second,
   separate commit.

## The results section

Appended to the re-probe protocol document per its own recording plan:

- a dated provenance-corrections block (decision 6);
- smoke outcomes: the baseline smoke (n=1, `OK`, verdict pass 1/1 —
  recorded here for the first time, with its scratch pointer); the engine
  smoke is already recorded in the Smoke findings section and is
  referenced, not restated;
- both arms' counts-only summaries (`attempted`/`refused`, `code_counts`,
  `verdict_counts`, `timeouts`), each with its scratch pointer and the
  command that recomputes it; no wall-clock comparisons between arms;
- the exact tree per arm: baseline — worktree
  `.worktrees/v5c-capture-admitted-suite` @ `36d7974` (clean); engine —
  main working tree @ `36d7974` post-ff (clean at run time);
- engine-arm defects, if any: a new plumbing defect is a stop-and-record
  condition (the protocol's own rule); the run stops, the section records
  what actually ran, and nothing is presented as an arm result.

The protocol's pre-registered body is not edited. The stale Conditions
line gains a one-line dated pointer note to the results section, matching
the spec amendment's "superseded-by" pattern.

## The V5a caveat update

Strictly from the recorded numbers, counts only. Band re-reading follows
the V5a band definitions (floor / middle / ceiling on successful-attempt
outcome). **If the band picture changed** — the baseline arm's recorded
3 `OK` of 8 already reads as something other than unambiguous floor — the
caveat records the numbers and the band reading, and any consequence for
the V5a admission decision is flagged to the maintainer as a decision,
never silently applied in either direction.

## Out of scope

- Any retrospective V5c plan (ratified missing, decision 2).
- V5d: no row, no doc, no confirmation on main (decision 4).
  **Superseded 2026-09-03:** the maintainer confirmed V5d and it landed
  — `2026-09-03-v5d-preflight-smoke-check-design.md` (status line) and
  the `ROADMAP.md` phase row.
- Editing the protocol's pre-registered body (corrections live in the
  dated results section).
- Any diagnostic batches beyond the pre-registered arms — n=8 per arm, no
  re-runs, no extensions.
- Worktree/branch cleanup (`research/local-pings-reprobe`,
  `v5d-realmodel-smoke-check`, their worktrees) — a separate decision
  after close-out.
- `docs/glossary.md` — the uncommitted edit is preserved untouched.

## Done-when

- main contains `36d7974`
  (`git merge-base --is-ancestor 36d7974 main` exit 0).
- The engine arm ran n=8; eight attempt directories plus `summary.json`
  exist under scratch `runs/engine/`.
- The results section exists with both arms' counts-only summaries, the
  provenance corrections, and recomputation commands; the protocol's body
  carries only the pointer note.
- The V5a caveat cites the results section; any band-picture change is
  flagged, not absorbed.
- `just lint-docs` passes; the default suite is green;
  `docs/glossary.md` still carries the uncommitted edit.

## Risks

1. **Engine-arm plumbing.** The smoke step already caught the three known
   defects (contract YAML, pi child argv, shim name). A new defect
   mid-run is a stop-and-record condition, never tune-until-green.
2. **Admission picture shifts.** Handled by the caveat rule above:
   numbers recorded, consequence flagged to the maintainer.
3. **Environment drift.** Pre-flight re-verifies server, shim, engine,
   and ancestry; a failed pre-flight stops before any attempt is spent.
