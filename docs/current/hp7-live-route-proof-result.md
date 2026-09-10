# HP7 live route proof — result

Run 2026-09-10, under
[the pre-run record](hp7-live-route-proof-pre-run-record.md) as corrected
the same day (route: `engine_command_implementer`/`run_and_record_engine_chain`;
both named gaps closed). `n = 1`, not extended after reading this result.
Retained at `~/satyrn-smokes/2026-09-10-hp7-live-route-proof/chain.json`.

## The question, answered

**Yes.** One real implementer (`pi` 0.85.1, `gemma-4-12B-it-MLX-8bit`)
completed the three-phase packet chain end to end, through real chained
isolation (`satyrn-engine deliver --base`), judged by the real hidden
per-checkpoint oracle. All three phases accepted:

| Phase | Accepted | Implementer mutations | Self-test |
|---|---|---|---|
| `phase-1-home` | true | 4 files | ran, exit 0 |
| `phase-2-board` | true | 6 files | ran, exit 0 |
| `phase-3-add` | true | 3 files | ran, exit 0 |

`decisions_from_record(record)` reproduces the same three `(step_id,
accepted)` pairs from the retained document alone. `check_chain(record)`
returns **zero findings** — no unobserved implementer window, no
out-of-declared-scope mutation, no missing evidence.

This establishes *operability*, not superiority, per the pre-run record's
own framing. It is one run; no rate, no comparison, no claim about Engine
versus Baseline follows from it.

## Cost, by role, never summed

**Orchestrator: null throughout, by design.** Phase HP runs no
orchestrating model. `orchestrator_mutations == ()` and `fallback ==
False` for all three phases — the expected shape, not a finding.

**Implementer, descriptive — from the retained transcript
(`harness/.satyrn-implementer-transcript.jsonl`), not from
`ChainRecord`'s own cost fields, which this route does not populate (a
real gap from `run_and_record_chain`'s `costs` parameter, not fixed
here — see "What this run did not close," below):**

| Phase | Internal turns | Tool calls | Input tokens | Output tokens |
|---|---|---|---|---|
| `phase-1-home` | 6 | 5 | 8,024 | 942 |
| `phase-2-board` | 8 | 7 | 9,991 | 1,374 |
| `phase-3-add` | 8 | 7 | 12,620 | 1,512 |

All well within the declared (not enforced) `turn_budget=20`,
`tool_call_budget=30`. Monetary cost is `0` in every `usage.cost` field —
a local provider, unmeasured by design, matching the phased-session
record's own rule.

## Model identity, verified from the transcript's own field

`message.model` reads `gemma-4-12B-it-MLX-8bit` on every one of 22 real
turns across all three phases (462 transcript lines total) — never the
requested argv, per precondition 6. No drift.

## Declaration ledger, every phase identical

`self_test_command: applied` (harness-run, real exit code 0 — the fix
closed the same day this run happened). `writable_paths:
observed_compliant` (nothing observed leaving declared scope; the
adapter still does not self-enforce, so this is an honest weaker claim,
not "applied"). `redacts: applied`. `turn_budget` / `tool_call_budget`:
`declared_not_applied`, as they are everywhere on this route.

## What this run did not close

Named plainly, not left implicit:

- **`ChainRecord`'s own cost fields are still unpopulated on this
  route.** The table above is a manual read of the raw transcript, not
  what `run_and_record_engine_chain` retains. Closing this means
  threading real per-phase cost through the same receipt-based side
  channel `self_test_outcome` now uses, or a `costs` parameter matching
  `run_and_record_chain`'s. Not attempted here.
- **The named crash-safety gap's *sibling* concern — per-phase
  persistence — was proven separately** (a real subprocess run with an
  injected grader crash, `satyrn-evals@b8ca71a`), not by this run, which
  completed cleanly and so never exercised that path live.
- **This is not D8.** No wall-clock, no comparison to the plain-session
  route's own three prior runs, and this run's counts stay outside any
  future confirmation's denominator.
