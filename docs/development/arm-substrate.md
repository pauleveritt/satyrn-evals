# Arm substrate

The arm substrate is the repository-owned description and validation of an
attempt command. It is execution infrastructure, not a result or an engine
comparison.

## Components

- `arms/*.json` are executable arm records loaded by `satyrn_evals.arms`.
  They declare command argv, model and server model names, tool surface,
  inference settings, and pins. The Baseline record declares `read`, `bash`,
  `edit`, and `write`; the Engine record currently declares `read` and `edit`.
- `satyrn_evals.attempt_pi` is the Baseline adapter. It supplies the selected
  contract and tool surface to Pi, preserves its stream transcript, and writes
  a patch derived from the workspace after the command exits.
- `scripts/preflight.sh` checks the supplied arm records and their model,
  inference, and pinning prerequisites, then uses `scripts/interleave.py` to
  write a seeded schedule before cells run.
- `scripts/interleave.py` creates one directory per scheduled cell.
  `scripts/tally.py` validates that the retained cells match that schedule and
  refuses a missing, extra, incomplete, or mismatched cell rather than changing
  a denominator.

The current runner described in [the first-milestone plan](../current/first-milestone-plan.md)
is not implemented yet. It will freeze the exact executable and imported
source identities used for a route, retain recovery state, and share the tally
validation for resume decisions.

## Current limits

An arm record declares a tool surface, but it does not independently prove the
tools actually exposed by every runtime path. Treat that record as frozen input
to validate, not as transcript evidence. The planned route will record the
resolved executable and imported source identities alongside retained attempt
artifacts.

The Baseline adapter obtains its patch after Pi exits with `git diff HEAD`; it
does not capture untracked file creation. The tally reports counts from
retained records. It does not provide a controlled performance measurement;
any performance claim needs a matched, frozen execution condition.

`preflight.sh` still requires an obsolete token-floor record. The current
milestone removes that prerequisite while preserving the relevant arm and
execution checks; until then it is a known runtime gap, not a satisfied
precondition.
