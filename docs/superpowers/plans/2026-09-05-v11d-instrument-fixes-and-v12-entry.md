# V11d — instrument fixes, then V12's entry gates

**Status: proposal, awaiting confirmation.** `CLAUDE.md` requires a confirmed
proposal before implementation. One slice is already done and is marked so.

Ordered by the maintainer's direction of 2026-09-05: the small metric fix and
the signal-interruption reproduction first, then V12 resume support and the
remaining entry gates. Inference tuning is deferred behind all of it.

## What this addresses

Six findings, all from the V11c mini-probe round. Each names its evidence.

| # | Finding | Source |
|---|---|---|
| F1 | Preflight passed while an arm's command was unresolvable | Engine smoke abort, 2026-09-05 |
| F2 | `tool_free_terminal_turns` can never fire on a pi-adapter cell | `rescore.py:214` vs `pathology.py:321` |
| F3 | A signal-killed `run` writes no `aborted.json` | `misleading-locus` interrupted batch |
| F4 | An infrastructure error scores as a model refusal | `attempt.py:102`; voided batch |
| F5 | V12's 288-cell run has no resume support | V12 entry gate, not yet built |
| F6 | pi and the server disagree about the context window | 262,144 vs 80,000 |

## Slice 0 — preflight resolves each arm's command (**done**)

`scripts/preflight_commands.py` plus `tests/test_preflight_commands.py`,
called from `preflight.sh` as check 0b. Addresses **F1**.

Verified in both directions on the real script, per `BRIEF.md` rule 8: with
`satyrn-engine` absent from PATH it names that arm and stops; with it present
both arms resolve and the run proceeds. It runs under `uv run` so it resolves
the way a cell resolves — checked with a bare `python3` it reported the
working Baseline command as missing, which is the over-firing detector this
project keeps re-learning about.

**Its stated limit:** a resolvable command is not a working one. That is what
the V5d smoke is for, and this does not replace it.

## Slice 1 — the empty-patch metric fix (**F2**)

Small and self-contained; first because it silently understates every
pi-adapter cell already collected.

`pathology.py:321` gates `tool_free_terminal_turns` on `not had_patch`, but
`rescore.py:214` passes `had_patch=record.patch_path is not None` while
`attempt_pi.py:231` writes `patch.diff` unconditionally. So `had_patch` is
always true and the counter is dead.

**Change:** `had_patch` must mean a **non-empty** patch.

**Acceptance tests, stated before implementation:**
1. Refusal sibling: a `NO_PATCH` cell whose terminal turn is tool-free text
   counts `tool_free_terminal_turns == 1`.
2. Success sibling: a cell with a real patch counts `0` for the same
   transcript shape — the gate still works in the direction it was designed
   for.
3. A cell with an existing-but-empty `patch.diff` behaves as (1), pinning the
   actual defect rather than the field name.

**Re-score, do not re-run.** Every affected cell has a retained transcript, so
`regrade`/`summarize` rebuild the corrected counts offline. The known
demonstration: `miniprobe-2/plausible-wrong-fix/…-200622-258836` publishes
`0` and recomputes to `1`.

## Slice 2 — signal-interruption reproduction (**F3**)

`run.py:123-153` writes `aborted.json` on any `BaseException`, and a
`UsageError` demonstrably does (the aborted Engine smoke recorded `completed:
0` and its cause). A SIGTERM apparently does not — the interrupted
`misleading-locus` batch left three cell directories, no `summary.json`, and
no `aborted.json`.

**Reproduce before fixing.** A test that sends SIGTERM to a live `run` and
asserts on what lands. If the reproduction fails, F3 is a misattribution and
is recorded as such rather than quietly dropped.

**Constraint:** the default tier forbids subprocesses, so this is an
**integration-tier** test, marked and excluded from CI. Do not weaken the
planted-spawn tripwire to make it convenient.

**Acceptance:** signal arrives mid-cell → an abort record exists naming the
signal, completed cells stay readable, and the incomplete cell is
distinguishable from a completed one. Sibling: a clean run still writes
`summary.json` and no abort record.

## Slice 3 — V12 resume-safe driver (**F5**)

Built **before** V12's long run, not during it. 288 cells is far past the
interruption horizon this session already crossed twice.

**Rules, written before any cell:**
- A **completed** cell is immutable evidence and is never re-run on resume.
- An **incomplete** cell (directory present, no `attempt.json`) is discarded
  and re-run; the discard is recorded.
- An **invalid** cell (an infrastructure failure per slice 4) is recorded,
  re-run, and **both** records are retained — the original is not deleted.
- Resume refuses outright if pins, contract digest, or model identity differ
  from the run's own recorded preflight. A batch resumed onto different
  conditions is two experiments in one denominator.

**Acceptance:** interrupt at cell *k*, resume, and the completed *k−1* cells
are untouched with the run reaching *n*; plus the refusal sibling, where a
changed pin stops the resume.

## Slice 4 — `MODEL_ERROR` (**F4**)

A non-scoring outcome code decided from the **preserved transcript** before
`decide_refusal` runs, mirroring `pi_session.py:60-84`, which already does
exactly this for the session adapter.

**It must classify, not pattern-match.** This round produced both shapes: a
GPU OOM with zero tokens (voids the cell) and a 285-turn context exhaustion
(genuine pathology, stays in the denominator). Three screens were tried and
two over-fired — `'"stopReason":"error"'` hit the exhaustion cell, and
`'"totalTokens":0'` matched all 12 cells including four passes. The
classifier is therefore judged on both directions before it ships.

**Constraints:** never from the exit code (`BRIEF.md` rule 4); not in V10's
counts-only layer, which would leave the cell inside `code_counts[NO_PATCH]`;
report and never drop — `n` stays intact and exclusion from a success count
is the maintainer's call under V11c §2 rule 1.

## Slice 5 — remaining V12 entry gates

Per the roadmap's V12 row: author R0 and R2, restore the four-point
monotonicity check, ship creation-capable patch capture before `framing-2`
runs, add a well-formed-tool-call canary per model, and validate the observed
transcript model.

## Deferred deliberately — inference tuning (**F6**)

pi believes this model's context window is 262,144; the server enforces
80,000, so pi's compaction can never fire first. Changing context limits,
compaction, quantization or stopping rules would shorten runs **and change
what is measured**. These are frozen until slices 1–4 are done, then decided
and recorded before a batch — never tuned mid-sequence.

Recorded now so the mismatch is not rediscovered as a novel finding.

## Sequencing and verification

Slices 1 and 2 are independent and small. Slice 3 depends on slice 2's
answer about signal handling. Slice 4 is independent but gates any budgeted
batch that must be trusted cell-by-cell. Slice 5 is V12's own gate list.

Focused tests during each slice; the full gates — `uv run pytest`,
`uv run ruff check`, `just lint-docs`, `just docs` — at integration, not
after every handoff. Development happens in a worktree separate from any
frozen checkout that is running cells.

**The V11c spike stays held** and is unaffected by this plan: its task
selection is frozen and its Engine path passed its V5d smoke.
