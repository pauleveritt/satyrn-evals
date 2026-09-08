# Backlog

Keep only concrete work that is not needed for the current milestone. Archive
holds the resolved and superseded record.

## Entries

**Normalize a diagnostic across arms only when a frozen experiment needs it.**
Existing arm-specific pathology detectors are evidence scoped to their own
transcript vocabulary. Reopen when a proposed comparison needs one shared
measure and can demonstrate it on examples from every compared arm.

**Constrain the interleave order so a small batch cannot draw a clumped
schedule.** `build_order` in `scripts/interleave.py` is a balanced shuffle with
no run-length constraint. That is right at `n=12`, where a clumped order is
improbable and its effect is small; at two cells per arm it is a coin flip —
two of the six possible orders put both cells of one arm first, which confounds
arm with position over the batch. The 2026-09-08 screen drew exactly that at
seed 20260908 (`engine, engine, baseline, baseline`) and was run instead under
a rule declared before any cell: the smallest seed whose order alternates. That
rule lives in the batch record, not in the tool, so the next small batch can
draw the same problem. The fix is a constraint in `build_order` with its own
tests in `tests/test_interleave.py`, including the refusal direction — a
request whose constraint cannot be satisfied must fail loudly rather than fall
back to an unconstrained shuffle. Not done on the way to the run, because
patching pinned instrument code between a preflight and a spend is how an
instrument becomes the subject. **Reopen** when a batch with fewer than about
six cells per arm is next planned, or when `interleave.py` is being changed for
another reason.

**Count an invalid tool call instead of voiding the cell.** A tool call the
agent emits and the runtime *refuses* currently makes a whole cell
`measured: false`, so every pathology count for that cell disappears. Observed
twice: two Engine cells of the V11c spike (2026-09-05) and three Baseline cells
of the R1 batch (2026-09-08), all an `edit` whose args carry `edits` with no
top-level `path`, all answered by pi with `isError: true`. Relaxing the
well-formedness rule is the **wrong** fix and was drafted and abandoned on
2026-09-08 — the calls never executed, so counting them would manufacture
`tool_calls`, `churn` and `noop_edits` from nothing. The right fix is a new
axis recording refused calls, leaving the executed-call axes untouched. A
proposal must decide the axis name, whether a refusal is keyed by `isError` or
by parsing the refusal text, and what a refusal-heavy cell means for a
comparison — an arm that emits invalid calls is telling us something real about
that arm. **Reopen** when a comparison depends on pathology counts from cells
containing refused calls.

**Establish an effective session tool boundary, and disable delegation.**
`adapters/pi_session.py:87-98` passes no `--tools`, so a session runs on
whatever pi defaults to. On 2026-09-08 the model dispatched a **detached
subagent** that wrote two files across two checkpoint boundaries with no
retained events, leaving per-step turn, tool and context figures understating
the work by an unknown amount. The attempt path does not have this problem:
each arm freezes its tools and the pre-run record carries them.

**A `--tools` flag is not sufficient, and is not what this entry asks for.**
The worker came from an **installed extension**, so the boundary that matters
is what the launched pi runtime actually exposes — ambient extensions
included — not what the adapter's argv requests. The proposal must verify the
effective surface of the launched runtime, and the next bounded run must use a
**fixed single-agent surface with delegation disabled**.

**Recording a dispatch is not an acceptable alternative.** An earlier wording
of this entry offered "refused outright or merely recorded" as a choice; that
option is withdrawn. A recorded dispatch still would not capture the worker's
usage and still would not prevent writes landing across a checkpoint boundary,
which are the two properties this prerequisite exists to guarantee.

**Reopen** before any session intended to count — this is a prerequisite, not
an improvement, because no grading change can re-score evidence that was never
retained.

**State the writable scope in session prompts.** `session.py:392` sends only
the step prompt, so a session solver is never told where code belongs or what
is writable — the information a single-prompt contract carries in
`writable_paths`. Two sessions on two different tasks (2026-09-04, 2026-09-08)
ended `SCOPE_VIOLATION`. **Reopen** with the tool-surface entry above; they are
the same proposal.

**Expand the task family after qualification.** Reopen after the first
qualified route is complete and a specific engine hypothesis needs additional
headroom or a regression case beyond the qualified initial set.
