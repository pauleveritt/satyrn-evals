# Working in this repository

Read `STATE.md` (what exists, what is proven, what is decided), `BRIEF.md`, `ROADMAP.md`, and
`docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`. Then read
the spec for the current stage (today,
`docs/superpowers/specs/2026-09-15-release-two-finishing-counterfactual.md`,
the knowledge-stage pre-registration) and nothing else. The release-one
design (`docs/superpowers/specs/2026-09-13-release-one-design.md`) and its
phase plans are evidence for a named question, never guidance. The tag
`pre-release-one-2026-09-13` on `main` holds everything before this tree; it
too is evidence for a named question, never guidance.

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

**Evidence has a harness.** Every design decision -- an Engine target, a
ceiling task, a budget, a claim -- names the evidence it rests on and the
harness commit that produced it. When a harness defect is found (a leak, a
cutoff, a harvest or grading bug, wrong sampling, a prompt defect), list
every decision whose evidence that defect could have produced, mark each one
unconfirmed in the ledger, and build nothing on an unconfirmed decision until
it is re-derived on the fixed harness. No Engine component is designed before
admission on the comparison's own harness has classified why Baseline fails
(information, ambiguity, capability, budget, finishing), and no remedy is
built before an offline estimate on retained cells says it can clear the
threshold (`docs/lessons.md`, "We built the remedy for the failures we
saw"). **Going faster shortens building, never the order:** harness
validity, then diagnosed admission, then the counterfactual, then the build.

**The instrument is not the work.** Two consecutive instrument-only pieces stop
the loop; a token run does not restart it. If a fix is larger than the
measurement it unblocks, stop and ask. Every file here has a row in
`PROVENANCE.md`; `just gates` fails if one does not.
