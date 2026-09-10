# HP7 live route proof — result

Run 2026-09-10, under
[the pre-run record](hp7-live-route-proof-pre-run-record.md) as corrected
the same day (route: `engine_command_implementer`/`run_and_record_engine_chain`;
both named gaps closed). `n = 1`, not extended after reading this result.
Retained at `~/satyrn-smokes/2026-09-10-hp7-live-route-proof/chain.json`.
**Independently reviewed 2026-09-10** (Sol); this document folds in that
review's confirmed findings rather than standing beside them.

## The question, answered

**Yes.** One real implementer (`pi` 0.85.1, `gemma-4-12B-it-MLX-8bit`)
completed the three-phase packet chain end to end, through real chained
isolation (`satyrn-engine deliver --base`), judged by the real hidden
per-checkpoint oracle. All three phases accepted:

| Phase | Accepted | Implementer mutations | Hidden checks (cumulative) |
|---|---|---|---|
| `phase-1-home` | true | 4 files | 4/4 |
| `phase-2-board` | true | 6 files | 10/10 |
| `phase-3-add` | true | 3 files | 13/13 |

Reproduced independently from the retained patches and receipts
(`grading/*.patch`, `grading/receipts/0N-*.json`), not merely reread from
`chain.json`. `decisions_from_record(record)` reproduces the same three
`(step_id, accepted)` pairs from the retained document alone.
`check_chain(record)` returns **zero findings** — no unobserved
implementer window, no out-of-declared-scope mutation, no missing
evidence in the schema it checks. **Zero `check_chain` findings is not
the same as complete provenance** — see "Execution reconciliation"
below for what that check does not cover.

This establishes *operability*, not superiority, per the pre-run record's
own framing. It is one run; no rate, no comparison, no claim about Engine
versus Baseline follows from it.

## Findings from independent review

**1. An unreported pathology: public regression tests disappeared
between phase 2 and phase 3.** Phase 2's cumulative `tests/test_app.py`
carries `test_home` and `test_complaints`
(`grading/phase-2-board.patch:124-134`). Phase 3's cumulative diff shows
the same file replaced wholesale — `test_home`/`test_complaints` are
gone, overwritten rather than extended, replaced with
`test_post_complaints`/`test_complaint_added`
(`grading/phase-3-add.patch:145-171`). The hidden oracle still passed
13/13, because it grades from its own `grader_tests/`, not the model's
`tests/` — so **this does not invalidate the accepted verdict**. It does
mean "accepted" concealed a loss of public regression coverage that a
human reviewer would want surfaced. Recorded here rather than folded
silently into "implementer mutations: 3."

**2. Worker-local verification is stronger evidence than reported, not
weaker.** The initial report described only the harness-run self-test
(`command_implementer`'s post-turn check, closed 2026-09-10). The
transcript shows more: `pi_implementer.py` adds the `run_self_test` tool
whenever a packet declares `self_test_command` — true for every phase of
this task (`build_pi_argv`, `adapters/pi_implementer.py:228`) — and **Pi
called it in every phase**, receiving a passing result before finishing
that phase's turn
(transcript `tool_execution_start` events, `toolName: "run_self_test"`,
once per phase, each followed by `toolName: "write"` or `"edit"` calls
that stop rather than continue fixing). This is the model verifying its
own work mid-turn, not just the harness checking after the fact.

**What remains unexercised: failure → feedback → correction → passing
retest.** All three of this run's self-tests passed on the first try, so
the loop's *recovery* half — a failing result feeding back into a
correction — has still never been observed live. Proving tool discovery
again is not worth a second smoke; proving the recovery path needs a
task engineered to fail at least once, which this run's task was not.

## Cost, by role, never summed

**Orchestrator: null throughout, by design.** Phase HP runs no
orchestrating model. `orchestrator_mutations == ()` and `fallback ==
False` for all three phases — the expected shape, not a finding.

**Implementer, descriptive — from the retained transcript
(`harness/.satyrn-implementer-transcript.jsonl`), not from
`ChainRecord`'s own cost fields, which this route does not populate (see
"What this run did not close," below):**

| Phase | Internal turns | Tool calls | Input tokens | Output tokens |
|---|---|---|---|---|
| `phase-1-home` | 6 | 5 | 8,024 | 942 |
| `phase-2-board` | 8 | 7 | 9,991 | 1,374 |
| `phase-3-add` | 8 | 7 | 12,620 | 1,512 |

22 turns total (6/8/8), 19 tool calls total, matching independent
review's own recount from the same transcript. All well within the
declared (not enforced) `turn_budget=20`, `tool_call_budget=30`.
Monetary cost is `0` in every `usage.cost` field — a local provider,
unmeasured by design, matching the phased-session record's own rule.

## Model identity, verified from the transcript's own field

`message.model` reads `gemma-4-12B-it-MLX-8bit` on every one of 22 real
turns across all three phases (462 transcript lines total) — never the
requested argv, per precondition 6. No drift.

## Declaration ledger, every phase identical

`self_test_command: applied` (harness-run, real exit code 0). `Finding 2`
above is additional evidence beyond what this ledger field captures: it
only records the harness's own post-turn run, not Pi's own live calls.
`writable_paths: observed_compliant` (nothing observed leaving declared
scope; the adapter still does not self-enforce, so this is an honest
weaker claim, not "applied"). `redacts: applied`. `turn_budget` /
`tool_call_budget`: `declared_not_applied`, as they are everywhere on
this route.

## Execution reconciliation

Independent review found the frozen pre-run record's own "Repo commit"
field (`275f963`) stale against what actually ran, and a deeper gap
underneath it: this route's real provenance chain is not durably
retained by `ChainRecord` at all.

**What actually ran.** `HEAD` at run time was `bdfba77` (`live_grading: a
real PhaseGrader for the engine-composed route`), with
`scripts/hp7_live_route.py` present on disk but not yet committed — it
was committed afterward, in `e5c0f70`, alongside this result document's
first version. `275f963` was the commit at the time the pre-run record
was *frozen* (2026-09-09), a full day before HP3 composition, the
self-test fix, and the live grading adapter existed; it was never
updated when the route itself was corrected. That correction is
recorded, dated, in the pre-run record itself — the commit field simply
was not carried along with it.

**The gap `check_chain` cannot see.** `engine_command_implementer`'s
`receipts` — the only place each phase's real `base_commit` and
`candidate_commit` git shas exist — is an in-memory list, read
incrementally by `run_and_record_engine_chain` and then discarded when
the process exits (`chain_record.py`, `capture_candidate`, around line
655). Nothing in `PhaseRecord`/`ChainRecord` stores these shas. A
`check_chain` finding of "zero" therefore certifies the schema it
checks, not full provenance of which git commit each accepted phase
actually was.

**For this specific run, the shas are currently recoverable, by
accident, not by design:** the run's `repo` directory was never deleted,
and `deliver` left each phase's candidate reachable (not dangling) on
`main`:

| Phase | Commit |
|---|---|
| base | `8a15ce7dd3345a3c6b5088ceeadc91d6e1ddc2c6` |
| `phase-1-home` | `4bcdfa0` |
| `phase-2-board` | `0abbc70` |
| `phase-3-add` | `e5a8022` |

If that directory had been cleaned up — routine for a "smoke" — these
would be unknown. Closing this for real means threading `receipts`
through the same durable side channel `self_test_outcome` now uses, not
attempted here per "what this run did not close."

## What this run did not close

Named plainly, not left implicit:

- **`ChainRecord`'s own cost fields are still unpopulated on this
  route.** The cost table above is a manual read of the raw transcript.
  Per independent review's own guidance: this does not need a schema
  project by itself — a retained, reproducible report from the existing
  turn ledger may be enough for what TE actually needs before HP8, and
  that's a TE-scoped decision, not one made here.
- **Per-phase git provenance (`base_commit`/`candidate_commit`) is not
  durably retained** — see "Execution reconciliation" above. The two
  stale-documentation items (repo commit, tool surface) are fixed in the
  pre-run record; the underlying retention gap is not.
- **The named crash-safety gap's *sibling* concern — per-phase
  persistence — was proven separately** (a real subprocess run with an
  injected grader crash, `satyrn-evals@b8ca71a`), not by this run, which
  completed cleanly and so never exercised that path live.
- **This is not D8.** No wall-clock, no comparison to the plain-session
  route's own three prior runs, and this run's counts stay outside any
  future confirmation's denominator.

## What it proved, and what it did not

A real packet-driven Pi workflow can create the application through
chained isolation, invoke public verification live, and produce
independently regradable passing checkpoints.

It did not prove fewer turns than Baseline, recovery from a failed
verification (none failed), preservation of the model's own regression
suite (Finding 1: it eroded), or any benefit from Satyrn's own
in-conversation guards (not loaded on this route).
