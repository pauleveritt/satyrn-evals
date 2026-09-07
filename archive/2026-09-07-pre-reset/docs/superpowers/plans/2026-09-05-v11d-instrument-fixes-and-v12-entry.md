> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V11d — instrument fixes, then V12's entry gates

**Status: confirmed 2026-09-05, then stopped after slice 2 the same day.**
Slices 0, 1 and 2 are done — see the
[F2/F3 record](../research/2026-09-05-v11d-f2-f3-record.md).

**Slices 3–5 are deferred behind the held V11c spike**, by the stopping
rule this round paid for (`CLAUDE.md`, "an instrument fix round needs a
stopping rule"). Of the six findings only **F1 blocked** the spike; **F2
and F4 are re-scorable** from retained transcripts after the run, which
is what `BRIEF.md` rule 3 exists to buy; and **F5 belongs to V12's 288
cells**, not to this spike's 24. The round opened with six findings and
reached nine — the real-E5 engine failure, the drifted 100%-coverage
claim, and `regrade_attempt` no-opping on refusal cells — while the run
the fixes were for stayed held.

Slice 4 keeps a confirmed design, recorded below, for whoever picks it
up after the spike.

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

## Slice 1 — the empty-patch metric fix (**F2**, **done**)

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
demonstration: `…-200622-258836` publishes `0` and recomputes to `1`.
**Correction:** that cell is in `miniprobe` (the **voided** first
mini-probe), not `miniprobe-2` as this plan first stated — the record
carries the recompute and the two-directional discrimination.

## Slice 2 — signal-interruption reproduction (**F3**, **done**)

`run.py:123-153` writes `aborted.json` on any `BaseException`, and a
`UsageError` demonstrably does (the aborted Engine smoke recorded `completed:
0` and its cause). A SIGTERM apparently does not — the interrupted
`misleading-locus` batch left three cell directories, no `summary.json`, and
no `aborted.json`.

**Reproduce before fixing.** A test that sends SIGTERM to a live `run` and
asserts on what lands. If the reproduction fails, F3 is a misattribution and
is recorded as such rather than quietly dropped. **It reproduced**, for
SIGTERM and SIGHUP alike, with the clean-run sibling passing throughout.

**Constraint:** the default tier forbids subprocesses, so this is an
**integration-tier** test, marked and excluded from CI. Do not weaken the
planted-spawn tripwire to make it convenient.

**Acceptance:** signal arrives mid-cell → an abort record exists naming the
signal, completed cells stay readable, and the incomplete cell is
distinguishable from a completed one. Sibling: a clean run still writes
`summary.json` and no abort record.

## Slice 3 — V12 resume-safe driver (**F5**, **withdrawn 2026-09-06**)

> **Withdrawn, not deferred.** Staging made it moot: the profile ran in
> batches of at most 60 cells and 168 cells landed with no interruption
> loss, so nothing was left for a resume path to preserve. The 288-cell
> figure below is the count this slice was written against and no longer
> the plan. It reopens only if a batch is again scheduled past the
> interruption horizon in one piece. Recorded in `ROADMAP.md`'s 2026-09-06
> amendment and in
> `docs/superpowers/research/2026-09-06-next-agent-brief-v13-envelope-and-roadmap-control.md` §7.

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

## Slice 4 — `MODEL_ERROR` (**F4**, **done**)

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

### Slice 4's confirmed design (2026-09-05), for after the spike

Recorded so it is not re-derived. The decision surface, computed from the
retained transcripts of both batches:

| shape | cells | `stopReason` | tokens | `errorMessage` | treatment |
|---|---|---|---|---|---|
| healthy | 11 of 12 (of record) | `stop`/`length` | 3.9k–23.6k | none | untouched |
| context exhaustion | `misleading-locus …203854` | `error` | 0 | `400: {"message":"Prompt too long: 80036 tokens exceeds max context window of 80000 tokens", …}` | **stays in the denominator** |
| runtime fault | `plausible-wrong-fix …200818`, `…200819` (voided) | `error` | 0 | `[METAL] Command buffer execution failed: Insufficient Memory (…OutOfMemory)` | **`MODEL_ERROR`** |

`stopReason == "error"` and `totalTokens == 0` are each true of **both**
error shapes, so neither can be the rule — confirming `0ec2e34`. One
structural shortcut is dead too: `responseModel: "keepalive"` appears on
the OOM cell **and** on a healthy `OK` cell. (Beside the point here but
owed to V12's observed-transcript-model gate: `responseModel` is not the
model identity; `message.model` is.)

**The rule.** On a `stopReason: "error"` terminal turn, an
`errorMessage` that is a status response from the model server
(`^\d{3}: …`) means the server was reached and answered about its own
input limits — a model-side outcome that stays in the denominator.
Anything else is the substrate failing beneath a well-formed request →
`MODEL_ERROR`. Deliberately conservative toward `MODEL_ERROR` for unknown
faults, because report-never-drop makes that visible, whereas today's
behaviour — infrastructure silently counted as `NO_PATCH` — is not. Its
cost: a model-side failure arriving without a status code would inflate
apparent infrastructure trouble rather than hide a refusal.

**Two decisions confirmed by the maintainer:**

1. **A pure classifier over the transcript, called from both paths** —
   `attempt()` before `decide_refusal`, and the re-score path, so cells
   already collected reclassify offline.
2. **A new `AttemptCode.MODEL_ERROR` with its own policy row; outcome
   stays `REFUSED`.** It leaves `code_counts[NO_PATCH]` — this slice's
   actual complaint — and gets its own summary line. `n` stays intact.

**A gap this plan missed:** `regrade_attempt` no-ops on refusal cells
(`rescore.py:362`, "nothing was graded, so nothing re-scores"), so an
attempt-time-only decision would strand every collected cell at
`NO_PATCH` with no offline path to correct it — the failure `BRIEF.md`
rule 3 exists to prevent. Decision 1 is what closes it.

### Corrections found in review, recorded (2026-09-06)

Four, all caught by an adversarial review of the first implementation.

1. **The two call sites disagreed, and one destroyed evidence.** The
   attempt path consulted the substrate whenever no code was set — before
   looking at the patch — while the re-score path only reclassified
   `NO_PATCH`. So a cell that edited files and *then* hit a GPU fault was
   refused `MODEL_ERROR` and never graded, and `regrade` could not
   recover it (`_gradeable` admits only `OK`/`GRADE_FAILED`). The
   classifier now runs only where `decide_refusal` would have said
   `NO_PATCH`, which is exactly the population re-scoring reclassifies.
   **`MODEL_ERROR` replaces a `NO_PATCH`; it never displaces a patch.**
   No cell on disk had that shape, which is why the replay evidence did
   not catch it — the known-bad and known-good sets contained no
   patch-plus-errored-turn cell.
2. **The rule was a pattern match on punctuation.** It keyed on a literal
   `"400: "`. pi renders `"<status>: <body>"` only when the provider
   returns a structured error object and `"<status> <message>"` otherwise,
   so the same context overflow from a server returning a bare string
   would have been called infrastructure. Worse, *any* status counted as
   model-side, so a 503 — the server blaming itself, which pi's own retry
   layer treats as a transient provider error — landed in the denominator
   as a refusal. The rule now asks what HTTP already answers: **4xx the
   server blamed the request (model-side); 5xx it blamed itself
   (infrastructure); no status is a runtime fault**, except pi's own
   `Provider finish_reason:` rendering, which is model-side. A test that
   pinned `503` as model-side encoded the bug and was inverted.
3. **Re-scoring was one-way.** It promoted `NO_PATCH → MODEL_ERROR` but
   never back, so cells reclassified under a rule later found wrong —
   and the rule *was* wrong once already — could not be re-derived.
   `regrade` now derives the code from the transcript in both directions.
4. **The evidence census was wrong.** It was reported as 69 cells; the
   scope stated (excluding the running overnight batch) actually holds
   **54**. The corrected replay: fires on 5, silent on 49, of which
   **8** are context-exhaustion known-goods — the seven `400:` cells of
   the V11c spike plus the mini-probe's, a better known-good set than the
   single cell first cited.

The attempt-path wiring had no test at all; it now has three
(`tests/integration/test_model_error_attempt.py`), including the
delivered-patch regression from finding 1.

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
