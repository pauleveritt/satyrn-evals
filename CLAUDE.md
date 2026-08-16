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
recorded condition that would reopen it, in `BRIEF.md`'s Backlog section.

## Rules that govern every edit, not just phase kickoff

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
