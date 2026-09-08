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

**Expand the task family after qualification.** Reopen after the first
qualified route is complete and a specific engine hypothesis needs additional
headroom or a regression case beyond the qualified initial set.
