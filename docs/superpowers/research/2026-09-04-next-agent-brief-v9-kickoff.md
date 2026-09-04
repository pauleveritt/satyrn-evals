# Brief for the next agent: start V9

**Read first, in this order:** `CLAUDE.md`, `BRIEF.md`, `ROADMAP.md`, then
the two documents this brief accompanies:
`2026-09-04-v5-v8-deep-review-and-agentclinic-ladder.md` (the findings) and
`2026-09-04-roadmap-to-a-reliable-instrument-and-a-first-engine-result.md`
(the plan). Both are committed research records, not approved phases.

## Where things stand

The maintainer confirmed six decisions against the roadmap draft
(reopen the transcript-metrics backlog entry; contract rungs as a manifest
field; model ladder = Gemma 12B + Gemma 26B-A4B, Mellum excluded; vendor
`specs/` into `base/`; amend V5a's band note; W1 keeps the 100% coverage
gate as invariant) and asked two follow-up questions, both resolved:

- Swapping the 26B point from 4-bit to **`mlx-community/gemma-4-26b-a4b-it-8bit`**
  (matches the 12B's quantization) — download was in progress as of
  2026-09-04. **Before V12 runs a single cell, verify this model with a
  live one-word chat completion** (not `/v1/models` — this repo's harvest
  index specifically warns that endpoint enumerates from configuration and
  can advertise absent weights). The 12B was already verified this way.
- Whether swiftstar gives direct evidence that Engine beats Envelope: no —
  swiftstar never runs an Envelope arm. The real precedent is from this
  repo's own prior pilots (`stringified-annotations` Engine 6/6 vs
  Envelope/Baseline 0/6; `local-pings` Engine 2/4 vs 0/4), which is exactly
  why V13 re-derives rather than cites.

**Nothing past this brief has been implemented.** `ROADMAP.md`'s phase
table is untouched — V9 through V15 are proposals in the research doc, not
rows yet.

## What "start" means here

Per `CLAUDE.md`: **do not write code.** Post a short design proposal for
V9 (CLI surface, exit codes, data shapes, test layout) and wait for
explicit maintainer confirmation before implementing anything. If you were
dispatched as a subagent with no way to wait for a reply, stop and say so
instead of proceeding — this instruction is explicit that a one-way
dispatch is the wrong mode for starting a phase here.

## V9 — Loop integrity and re-scoring (start here)

This is the first phase because everything downstream (V11's ladder, V12's
288-cell profile, V13's 3-arm probe) runs through `run`/`grade`, and today
that loop cannot survive a batch. It needs no model and no new task — it
is entirely inside `src/satyrn_evals/{run,attempt,attempt_record,grade,
overlay,contamination,taskenv,patch}.py`.

**Read before proposing:** the deep-review doc's §3 (table T1–T14) and §6
(V9's row). The defects, each already `file:line`-cited there:

- **T1** `run.py:35-46` has no per-cell failure boundary — one exception
  from cell k discards the whole summary; cells 1..k-1 sit unsummarized.
- **T2** `attempt.py:229,247` writes `attempt.json` only *after* `grade()`
  returns — a grading exception makes a cell invisible.
- **T3** No production caller of `load_attempt_record`/
  `load_session_record`; nothing rebuilds a summary from disk. BRIEF rule 3
  ("re-scored without re-running a model") has no executable form.
- **T4** `summary.json` names cells but not task/command/timeout.
- **T5** V7's auto-overlay hijacks V6 session preservation grading when a
  task's `base_preservation_selectors` differs from `expected_test_ids`
  (`session_grader.py:122-128`, `grade.py:67-70,87-90`) — masked today
  because the one bundled session fixture's lists happen to coincide.
- **T6** `overlay.py:74-79`'s `mode & 0o022` check refuses every hidden
  task (including all six agentclinic tasks) on a umask-002 system
  (Debian/Ubuntu default) — verified as a real portability hole, not
  exercised on this maintainer's machine.
- **T7** `grade.py:211-213`'s `PYTHONPATH` for the oracle is the evals
  *install location*; correct in an editable checkout, wrong (precedes the
  locked env) in a wheel install — `resolved_versions` would then attest
  an environment the oracle didn't use.
- **T8** `grade.py:184-198` runs `git init`/`git apply` with the ambient
  environment — the one place V4's env-cleaning discipline was skipped.
- **T9** Not a bug to fix — a limit to *document* beside BRIEF rule 4:
  model code imported at collection time can forge the oracle result file
  (`SATYRN_ORACLE_RESULT` is in the oracle's env, `grade.py:208`; the
  loader checks shape/consistency/freshness only, `verdict.py:37-79`).
- **T14** Default attempt timeout is 30s (`workspace.py:28`) — cost one
  V8 smoke run already; raise it.

**Proposed shape (from the roadmap doc, not yet confirmed):** a per-cell
try/except in `run()` that records a cell's own exception as a cell
outcome and continues to n; reorder `attempt()` to write the record before
grading; add `task`/`command`/`timeout` to `Summary`; ship
`regrade ATTEMPT_DIR` and `summarize OUTPUT_DIR` CLI subcommands built on
the now-load-bearing `load_attempt_record`; fix T5–T8 each with a
refusal-then-success test pair, per this repo's non-vacuity rule; state T9
in the docs; bump the default timeout. All of this is a *proposal*, not a
spec — the design brainstorm may land somewhere different once the
maintainer has weighed in, especially on how a mid-batch cell failure
should be *represented* in the summary (a new outcome code? folded into
existing verdict counts?).

## Guardrails specific to this phase

- **Default tests stay model/network/subprocess-free.** T5's fix touches
  `session_grader.py`/`grade.py` and needs an integration-tier test (real
  grade is a subprocess); its refusal/success pair belongs there, not in
  the fast tier.
- **A refusal test needs a sibling success test** — every one of T5–T8.
- **Verify, don't assert.** T6 (umask) and T7 (wheel install) are
  portability claims about environments this machine doesn't naturally
  exercise — the plan must say how they'll be demonstrated (a `chmod`
  fixture forcing `0o664`; a built-wheel install in a scratch venv), not
  just asserted from reading the code.
- **Don't touch `ROADMAP.md`'s phase table** until V9 has a confirmed
  design spec — add the row then, following the V6/V7/V8 pattern already
  there.
- **Don't start V10, V11, or the model ladder work.** V9 is scoped
  narrowly on purpose; W1 (weight) is a separate confirmed phase that
  lands after V9 touches the same files, not concurrently.

## One open question worth raising with the maintainer during V9's brainstorm

The roadmap doc's §8 lists four still-open decisions (Envelope's
definition, V12's n, whether V12 includes rung R2, where arm definitions
live) — none block V9, but the first one (Envelope) is on the critical
path to goal (c) and has no owner yet. Surfacing it early, even before
V9 is done, avoids discovering it's undecided when V13 is being scoped.
