# The unisolated harness — in-worktree confinement and contamination control (design)

**Status:** draft for the maintainer's approval, 2026-09-27, drafted at his
request. This spec changes the isolation condition of
`2026-09-13-release-one-design.md` ("Isolation, both arms") and R0 §4's
"two-uid isolation for every deciding record". Neither change is made until
this is approved.

**Rulings, 2026-09-27.**

- The contamination control is the **stronger** package (absence + in-worktree
  confinement + audit).
- Confinement is required, and is **in-worktree and policy-level** — never a
  second user, `sudo`, `bwrap`, Docker, a container, or any other OS facility.
- A **lexical `bash` screen plus the C3 audit is accepted**; no OS isolation is
  required to close the bypass gap.
- The record field is named **`confinement`**; `isolation` retires and the
  committed records keep their old key.
- The five sandbox2 records stay **historical**; they are removed later only if
  they break something.

The trigger is portability: the two-uid profile needs root and a persistent
sudoers grant, `bwrap` is Linux-only, and both refused or complicated
contributors on other machines.

## 1. What this decides

How a cell is kept from reading the material that grades it, when the harness
may not change the host. It replaces a structural guarantee ("the model runs as
another user and `find /` finds nothing that grades") with a policed and
audited one ("the harness refuses in-worktree escapes, and no run was observed
reading grader material").

It decides no Engine component and no task. It is a harness-validity change and
lands before admission, per R0 §1.

## 2. What isolation bought, and what is lost

Under `satyrn-cell` the model could run `find /` and find nothing, because the
harness, grader, task roots and retained cells were mode 700 under the
maintainer's uid (`cell.py`; `STATE.md`, "Isolation holds"). That is a
**prevention** guarantee.

Without it, a cell runs as the maintainer with the whole machine readable.
`src/satyrn_evals/tasks/<task>/overlay/` (the hidden suite) and
`fixtures/known-good.patch` are ordinary files. A cell can copy the answer, and
the Engine and Baseline arms would be contaminated unequally. `contamination.py`
already declares the limit of what it can catch: it is verbatim-only and
"explicitly NOT a proof of ignorance".

## 3. The condition that replaces isolation

**Confinement and contamination control, both arms.** The same condition
applies to both arms; the product difference stays `/implement`.

**C1 — In-worktree confinement (policy).** The cell's working directory is its
attempt worktree. An eval-owned Pi extension, loaded by **both** arms, refuses
a `read`/`edit`/`write` whose path resolves outside the worktree, and refuses a
`bash` command whose text names a protected root or grader material. Every
refusal is recorded as an event and counted (a new `pathology` field). The
Engine arm keeps its own guards; this extension is the shared condition, not
the product. Consequence to declare: Baseline is no longer "bare Pi with no
extensions" — it is "bare Pi with no product extensions, plus the eval's
confinement extension". The condition is symmetric, and the two arms still
differ only by `/implement`.

**C2 — Absence, best effort.** A cell's run tree holds only `base/` and the
contract; the hidden overlay and the fixtures are not materialized inside it,
and grading loads them itself. This is a reduction, not a boundary: on one
machine with one uid a shell can still read the eval checkout, so C1 and C3
carry the weight. The spec states this rather than implying more.

**C3 — Audit, and the admission rule.** After a cell's command, the harness
enumerates from the transcript every file-tool path and every `bash` argument,
and flags any that resolves to the corpus root, a task directory, a hidden
basename or a fixture; the existing verbatim `scan_patch`/`scan_transcript`
runs beside it. A **deciding** cell is admitted only when C1 recorded no
refusal *and* C3 is clean. A flagged cell is reported and is not a pass. This
makes the census's prose admission rule ("no passing cell read material outside
its worktree") mechanical.

**C4 — The claim.** From "the model could not read the grader" to "the harness
refused in-worktree escapes, and no run was observed reaching or copying
grader material". Paraphrased or indirect reads are not excluded, exactly as
`contamination.py` already says. A claim that rests on a pass rests on the
audit, and the audit's limit is written in the result page.

**No OS confinement.** No second user, `sudo`, `bwrap`, Docker or container, in
this release or as a planned path — the maintainer's ruling. A best-effort OS
wrapper is deliberately *not* specified, so no record's validity depends on
which machine happened to have one.

## 4. What changes in the harness

- `src/satyrn_evals/confinement.py` (new): the shared extension source and the
  audit's path rules. Pure audit functions in the default tier; the extension
  is exercised in the integration tier.
- `src/satyrn_evals/cell.py`: the `Isolation` triad (`isolated`, `sandbox`,
  `local`) shrinks to one run mode. The cell layout, `cell_environment`,
  `cell_command`, `grant_maintainer`, `share_with_cell` and `sandbox_command`
  retire.
- `src/satyrn_evals/attempt_pi.py`: both arms load the confinement extension;
  `build_pi_argv` gains the explicit `--extension` (still under
  `--no-extensions`, as the Engine arm already does).
- `src/satyrn_evals/attempt_engine.py`: the sandbox-profile refusal and the
  export-path requirement retire; `--engine-repo` may be any readable checkout.
- `src/satyrn_evals/cell_engine.py`: the `cell-engine` export is no longer the
  only way to point at a pinned engine. Decide whether the export survives as a
  convenience or retires.
- `src/satyrn_evals/cell_preflight.py`: the cell/sandbox hunt is replaced by a
  portable preflight — the confinement extension is loaded, and the run tree
  holds no grader material.
- `src/satyrn_evals/run_record.py`: `DECIDING_PURPOSES` no longer require an
  isolating profile; the `isolation` field becomes `confinement` (or retires).
- `src/satyrn_evals/workspace.py`: the cell-uid sharing and cell-side kill
  retire; the detached worktree stays.
- `src/satyrn_evals/pathology.py`: a `confinement_refusals` count beside
  `workspace_escapes`.
- Tests: each refusal gets a success sibling; the audit is proved both ways
  against a clean cell and a cell that reads a hidden file.

## 5. What this re-opens

Per `AGENTS.md` ("a harness fix re-opens every decision it could have
produced"), every deciding result produced under isolation is unconfirmed until
re-derived on this harness:

- the 39-cell census (`evidence/2026-09-16-census/`, both nights) and its
  signed class columns;
- the release-two comparison (`docs/numbers.md`): Engine 16 of 24 against
  Baseline 2 of 24;
- both route proofs and the red-stop replay;
- the sandbox Baseline set (`records/2026-09-25-sandbox*-baseline-*`), kept as
  historical evidence per the 2026-09-27 ruling.

The census's *process* classes can be re-read from the retained transcripts,
but `hunting` (defined as `root_searches > 0`, `census_classify.py`) becomes
live where isolation had suppressed it, so some cells reclassify and the class
columns must be re-signed. The *outcome* claims cannot be re-read from
recordings; they need a re-run. Until then they are marked unconfirmed in the
ledger and nothing is built on them.

## 6. Order of work

1. Approve this spec and the two rulings it records.
2. Implement C1–C3 with both-directions tests; delete the two-uid and sandbox
   surfaces; keep the default tier model-, network- and subprocess-free.
3. Re-qualify: the confinement extension is loaded on both arms, the same task,
   model and budgets as before, with no host setup.
4. Re-derive the census, then the counterfactual, then any build — R0 §1's
   order, unchanged.

## 7. Open question: how the Engine arm pins its commit under C1

`cell_engine.py` does three jobs at once: it **materializes** the pinned engine
(`git archive <commit>` of `src`, `packages`, `pyproject.toml`, `uv.lock`,
`README.md`, `LICENSE`, then `uv sync --offline`), it **shares** it with the
cell user, and it **verifies** it (marker, no grader material, and the
`packages/engine/*.ts` bytes against `pins.digests`). Only the sharing is a
child of isolation. Under C1 the model reads the maintainer's checkout
directly, so the question is where materialization and verification live.

**(A) Keep the export, drop only the sharing.** The arm still points at
`CELLS_ROOT/engine-<commit>`, still created and verified by `cell-engine`. The
smallest diff and it keeps `arm_export_problems` and `test_engine_arm_pins` as
they are, and it allows two Engine arms at two commits. But it keeps a
cells-root concept and an absolute, per-machine path in the arm file, and it is
a second mechanism beside `just fetch-engine`.

**(B) Retire the export; pin via the checkout.** `tools/engine_sync.py` already
clones into a sibling (`../satyrn-engine`, or `$SATYRN_ENGINE_REPO`), checks
out the pinned commit detached and refuses a checkout at another commit; it is
what `just fetch-engine` runs. Under B it becomes the only materializer, and a
preflight replaces `verify_export` with `engine_checkout_problems`: the
checkout exists, its `HEAD` is the arm's `engine_commit` (HEAD is what
`uv run --project` builds), and its `packages/engine/*` match `pins.digests`.
`cell_engine.py`, the `cell-engine` subcommand and `CELLS_ROOT` retire;
`test_engine_arm_pins.py` stays (it reads `git show <commit>:…`). The arm file
then names the commit, not a path, and one arm file works on a mac, a Linux box
and a contributor's checkout.

**Recommendation: B**, with one check to settle first — a single sibling
checkout can be at only one commit, so a record that ran two Engine arms at two
commits (as `78ab87d` and `803df2d` are) would need two checkouts. If that case
matters, B keeps an optional per-arm `--engine-repo` pointing at a second
checkout, and the preflight verifies whichever it names. If it does not, one
sibling and one pin is enough.

The failure B must make loud is the one this session hit: the arm pins
`78ab87d` while the checkout sits on `main`. `engine_checkout_problems` must
compare the running checkout's HEAD with the pin and refuse by name, or an
Engine cell silently runs the wrong engine.
