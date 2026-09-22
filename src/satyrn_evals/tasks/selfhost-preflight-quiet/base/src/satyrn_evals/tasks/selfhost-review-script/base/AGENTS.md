# Working in this repository

Read `BRIEF.md`, `ROADMAP.md`, and the release-one design
(`docs/superpowers/specs/2026-09-13-release-one-design.md`). Then read the
plan for the current phase and nothing else. The tag
`pre-release-one-2026-09-13` on `main` holds everything before this tree; it
is evidence for a named question, never guidance.

**Unattended is for building; attended is for deciding and spending.** An
agent executing a plan implements its tasks, commits at task boundaries, and
stops at anything the plan did not foresee: an underspecified task, a task
that fails acceptance twice, a red gate whose fix is not in the plan, or any
step that wants inference. It never merges, never pushes, never runs a model
outside `satyrn-evals launch` with a frozen record, and never writes a result
or review file except through `satyrn-evals launch` and `tools/review.py`.

The default test tier uses no model, network, or subprocess; the tripwire in
`tests/conftest.py` enforces it. Every refusal test has a sibling success test.
Grade from hook-written evidence, never stdout or exit status. State
denominators and missingness. Count events from `tool_execution_start`, one
per call — never `grep -c`. Read a gate's exit code; never pipe a gate.

**The instrument is not the work.** Two consecutive instrument-only pieces stop
the loop; a token run does not restart it. If a fix is larger than the
measurement it unblocks, stop and ask. Every file here has a row in
`PROVENANCE.md`; `just gates` fails if one does not.
