# Working in this repository

**Before writing any code for a new phase: stop.** Post a short design
proposal for the phase (CLI surface, exit codes, data shapes, test layout)
and wait for explicit confirmation before implementing anything. This
instruction is self-contained and does not depend on any skill, plugin, or
tool being available — if you were invoked as a subagent and are inclined
to skip an interactive step for that reason, this one still applies; a
one-way task dispatch is the wrong mode for starting a new phase in this
repository. If there is no way to ask and wait, stop and say so instead of
proceeding.

Read `BRIEF.md` and `ROADMAP.md` in full before any work, every session.
**Do not re-brainstorm the project.** The design in those two files is the
output of a long, twice-reviewed session recorded in
`docs/superpowers/research/2026-08-16-harvest-index.md`. Brainstorm only
*within* the current phase — do not reopen the phase list, the
diagnosis-before-claims split, or the two selection rules for a grader
fixture versus a diagnostic workload. Each has a recorded reason and a
recorded condition that would reopen it, in `BACKLOG.md`.

## Rules that govern every edit, not just phase kickoff

- **Commits are maintainer-controlled.** Do not create a commit after each
  plan task or implementation slice. Leave the worktree available for manual
  review and commit when the maintainer requests it. The spec and plan must
  exist before implementation, but their creation is not itself an automatic
  commit checkpoint.

- **Verify, don't assert.** Claims get demonstrated, not argued. Cite
  `file:line`. Do not write down a number you did not compute yourself;
  carry the command that recomputes it.
- **Default tests use no model, no network, no subprocess.** This is
  enforced mechanically by a planted process-spawning test that fails the
  build — do not weaken or remove it. Real Git, environment
  materialization, model invocation, and oracle execution are a small,
  explicitly marked integration tier that does not run in CI.
- **A refusal test has a sibling success test.** Most of this code tests
  rejection, and rejection is the default outcome of most failures, so a
  broken test passes silently. Never add one without the other.
- **The verdict never comes from stdout or an exit code.** Predecessor
  graders were defeated by `addopts = --collect-only` and an import-time
  `os._exit(0)`. A result must come from a hook writing outside
  model-controlled output.
- **Capture is separate from grading, always.** Every attempt persists its
  patch and transcript before cleanup, and grading reads only those
  artifacts. This property matters more than any capture shape — a
  grading defect must be fixable and re-scored without re-running a model.
- **Never compare wall-clock time between contiguous arms.** Two published
  figures were retracted for exactly that. Summaries use counts.
- **A grader fixture and a diagnostic workload are different jobs.** Do
  not pick one artifact for both — see `BRIEF.md`'s "Two selection rules."
- **No framework before three concrete implementations need the same
  shape.**
- **A correction is recorded, not edited away.**
- **Modern Python 3.14 idioms.** This project targets Python `>=3.14`. Use
  them, don't fight them: real return type annotations on every function
  (no bare `-> None` where a richer type applies, and never an untyped
  signature); **semantic type aliases via `type` statements**
  (`type Outcome = Literal[...]`, `type CheckState = Literal[...]`) rather
  than complicated inline generics repeated at each call site; **structural
  pattern matching** (`match`/`case`) for dispatch over unions and for the
  kind of truth tables the oracle hook already uses, in preference to
  ladders of `if`/`elif`/`isinstance` chains; and the **walrus operator
  `:=`** for bind-and-test (capturing a computed value into a name while
  branching on it), as `patch.py` and the hook result write already do.
  These are the house style, not a preference — a review that rewrites
  them into older forms is wrong.

## How work is paced (confirmed 2026-09-05)

These are working agreements, not design. They exist to stop repeated
investigation and repeated spending.

- **One current status record.** `ROADMAP.md`'s opening paragraph and its
  phase table must agree. They drifted once — the opening said "awaiting
  landing" while the table recorded completion — and the cost was a later
  session re-investigating settled work. When a phase moves, update both in
  the same edit or neither.

- **Reuse evidence before spending inference.** A grading or metric change is
  re-scored from retained transcripts (`regrade`, `summarize`), never re-run.
  A V5d smoke repeats only when the **execution path** materially changes —
  a new adapter, argv, runtime, contract shape, or arm. A
  documentation-only commit changes no path and earns no re-smoke.

- **Inference runs from a frozen checkout; development happens in a separate
  worktree.** A batch's reproducibility claim is pinned to the commit
  preflight recorded, and preflight refuses a dirty tree — so editing the
  tree that is running cells either blocks the batch or invalidates it. V12
  preparation proceeds in its own worktree, independent of Engine work.
  Create worktrees with `git worktree add` / `git checkout`, or `rsync -a` —
  **never** a `cp` loop over `git status`, which once silently skipped
  `arms/` and `scripts/` and produced spurious failures.

- **Test at the right grain.** Focused tests during implementation; the full
  gates at integration — **`just gates`**, which runs `uv run pytest -q`,
  `uv run ruff check`, `just lint-docs` and `just docs` and stops on the
  first non-zero exit. Read that exit code; never pipe a gate into `tail` or
  anything else, which is how a check that cannot fail gets written. Do not
  re-run unchanged gates after every handoff.

- **Delegation.** Give Luna bounded changes with explicit acceptance tests
  stated up front. Use Terra for runtime boundaries, failure classification,
  and final review. After a change lands, re-review **the change and the
  findings it affects** — do not restart a broad review each time.

- **Inference settings are frozen between batches.** Context limits,
  compaction, quantization and stopping rules change what is measured, not
  just how long a run takes. They are decided and **recorded** before a
  batch, never tuned mid-sequence, and tuning waits until the instrument is
  reliable.

- **When an exploratory comparison may be published.** Four conditions,
  all four required, checked before the counts leave the runs directory:
  (a) the strict tally accepts the set — no missing cell, no stray
  directory, no wrong rung; (b) model identity is verified from each
  transcript's own `message.model`, not from the requested argv;
  (c) every open finding is classified as touching **verdict counts** or
  **diagnostic counts only**, and none touches verdict counts; (d) every
  inference setting the arm's behaviour depends on is recorded in the arm
  record, and preflight checked it against the live configuration.
  Written down 2026-09-05 because that day's outcome-1-versus-outcome-3
  call was *argued* rather than decided — and an argued call after seeing
  the counts is the shape the spike protocol forbids. On the V11c spike
  (a)–(c) held and (d) failed; (d) is now check 0c. Without this test,
  "one more re-run" has no end.

- **An instrument fix round needs a stopping rule, the way an experiment
  does.** A batch has one — `n` frozen, no extension after reading the
  result. A fix round had none, so each round found more than it closed:
  V11d opened with six findings and reached nine, while the run those
  fixes were for stayed held. So, before a fix is allowed ahead of an
  authorized run, it must **block that run** or be **impossible to
  re-score afterwards**. Everything else waits until after. This is not a
  quality standard being lowered — it is what capture-separate-from-
  grading was built to buy (`BRIEF.md` rule 3: a grading defect is
  "fixable and re-scored without re-running a model"). Applied to V11d on
  2026-09-05: only F1 blocked the V11c spike; F2 and F4 are re-scorable
  from retained transcripts and F5 belongs to V12, so the round stopped
  after slice 2 and the spike went next.

- **Some failures are machine state, and no code fix reaches them.** The
  voided first mini-probe was a GPU out-of-memory. Nothing in V11d
  prevents another — `MODEL_ERROR` classifies one after the fact, it does
  not stop one. Before an unattended batch, quiet the machine; that
  precondition is operational and belongs in the pre-batch check, not in
  a slice.

- **A long run is resumable before it is long.** Any batch big enough to be
  interrupted ships resume support first: completed cells survive
  interruption, and incomplete or invalid cells have explicit, written rules
  rather than being silently re-run or silently counted.

## When something looks like a known failure mode

Check `docs/superpowers/research/2026-08-16-harvest-index.md` before
re-deriving an explanation. It is indexed by symptom (e.g. "the number
looked clean and was fabricated", "the grader accepted a broken
solution") because a prior cycle spent a full spec, build, and pilot on a
premise two committed documents already refuted — the record existed and
was never retrieved. Four silent-zero incidents are recorded there in
detail; read them before trusting a suspiciously clean result. If you find
a new failure mode worth keeping, add it to this repository's own lessons
file the same way, indexed by symptom.

## Provenance

Seeded from `github.com/pauleveritt/local-ai-pi` at commit `c74c31f`.
**That repository is evidence, not source.** Do not transplant its
`harness/` package. Re-earn each behavior from the fixture and incident
named in the harvest index.
