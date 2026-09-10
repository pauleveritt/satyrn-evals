# Pre-run record — `run_self_test`, one bounded operability smoke

Written 2026-09-10, **before any inference and before any live run**. Every
value below is frozen at the moment of writing; a value chosen or changed
after reading a result is the shape the spike protocol forbids. **This
record authorizes no inference.** It proposes exactly one bounded `pi`
invocation and states its own budget; nothing runs until that budget is
separately, explicitly authorized.

Design: [self-test tool design](../superpowers/specs/2026-09-10-self-test-tool-design.md).
Plan: [self-test tool plan](../superpowers/plans/2026-09-10-self-test-tool.md),
whose offline tasks (the pure core, the extension wrapper, the Python
wiring) are implemented and green; this record is that plan's final task.
Sibling record: [HP7's live route proof](hp7-live-route-proof-pre-run-record.md),
whose shape this one follows and whose own "operability, not superiority"
framing this one adopts exactly.

## What this run is for, and what it is not

**The question this run asks is only: can Pi actually discover and call
`run_self_test`, and does a real failure's content reach it legibly enough
to act on?** That is operability, not usefulness or improvement. This run
cannot establish, and no reading of it may claim:

- That the tool helps the implementer produce better or more correct work.
  One call proves reachability, not benefit.
- That Pi *chooses* to call the tool without being told to. This record's
  prompt asks directly; whether an unprompted implementer would discover
  and use the tool on its own is a different, harder question this smoke
  does not attempt.
- Anything about turn counts, efficiency, or the TE comparison. This run's
  `n = 1` stays outside every TE confirmation denominator, the same rule
  HP7 and HP8 already hold themselves to.

## Precondition: the pi version mismatch, unresolved

The locally resolved `pi` is `0.85.1`; every existing pin in this
repository (`arms/*.json`, every other pre-run record, `pi_implementer.py`'s
own docstrings) names `0.84.4`. `scripts/preflight.sh:233-234` already
checks `pi --version` against the pinned value and fails loudly on
mismatch — this run is **not authorized to proceed** until that is
resolved (either `pi` is reinstalled at `0.84.4`, or the pin is
deliberately updated after checking `0.85.1`'s actual CLI behavior against
what the adapters assume, e.g. the space-form-only `--model` parsing
`attempt_pi.py`/`pi_session.py`/`pi_implementer.py` all depend on).
Named here as a precondition, not silently worked around; resolving it is
a separate decision from authorizing this smoke's budget.

## The arm

Same as [HP7's live route proof](hp7-live-route-proof-pre-run-record.md#the-arm):
`arms/baseline.json`'s inference settings (model
`omlx/gemma-4-12B-it-MLX-8bit`, context window 80000, max tokens 8192,
compaction enabled/16384, temperature 1.0), pi pinned per the precondition
above. Tool surface: `read`, `write`, `edit`, plus `run_self_test` — the
one addition this smoke exists to prove reachable.

## The task and the route

**Not `agentclinic-session-phased`.** That task's real `self_test_command`
(`uv run python -m pytest tests`) needs a real `uv`-managed virtualenv and
takes real wall-clock time to resolve — noise this operability question
does not need. Instead, a minimal, purpose-built fixture:

- A one-file workspace: `check.py`, containing a function that currently
  returns the wrong value.
- `self_test_command`: `["python3", "-m", "unittest", "check_test"]` (or
  the equivalent for whatever minimal test runner is actually used —
  fixed at implementation time, before the run, not guessed here), backed
  by a `check_test.py` asserting the correct value — engineered to fail
  once, and pass after the one obvious one-line fix.
- Packet fields beyond `self_test_command`: `objective` names the fix
  directly ("`check.py`'s function returns the wrong value; fix it"),
  `writable_paths` admits `check.py` only, `facts` states the expected
  value.

Route: `command_implementer` driving `adapters/pi_implementer.py` directly
(matching Task 2's own integration tests in `tests/integration/test_hp2_route.py`),
**not** a full three-phase chain — this smoke is about one implementer
invocation calling one tool, not chain composition, which stays HP3's own
open question, untouched here.

## Run parameters

| Field | Value |
|---|---|
| **n** | **1 invocation**, frozen, not extended after reading |
| `turn_budget` (declared, unenforced, per the packet's own honest shape) | 10 |
| `--timeout` (the whole invocation) | 120s — generous for one trivial fixture, checked against nothing longer since no representative trace exists yet for this exact fixture |
| `run_self_test`'s own internal timeout | `DEFAULT_SELF_TEST_TIMEOUT_SECONDS` (600s, `route.py`) — unreachable in practice for a fixture this small, named for completeness |

## The two questions, stated separately

**Reachability.** Does the retained transcript (`adapters/pi_implementer.py`'s
raw pi stdout, unfiltered per `turn_ledger`'s own finding) contain a
`tool_execution_start`/`tool_execution_end` pair naming `run_self_test`?
Reported plainly either way — a transcript with no such call is itself the
finding, not a voided run.

**Legibility.** If called, does the tool's returned content actually
reach a subsequent generation — read from the retained transcript's own
event sequence (a `tool_execution_end` for `run_self_test` followed by
further turns referencing its content), not inferred from the final
outcome alone. A final `check.py` fix succeeding is suggestive but not
proof the tool's content was what informed it; the event sequence is.

## What this run retains, and what closes it out

The same evidence HP2's executable seam already retains for any
`command_implementer` run: the raw pi transcript and stderr
(`adapters/pi_implementer.py`'s own append-mode files), the
`ImplementerResult`, and — separately — the harness-run
`SelfTestOutcome` from `command_implementer`'s own post-exit self-test,
which still runs regardless of whether the model called the tool itself.
Comparing the two (did the tool's mid-invocation result match the
harness's own post-exit result) is itself informative and costs nothing
extra to check, since both are already retained.

## Preconditions, all required before the run starts

1. **The pi version mismatch, above** — resolved.
2. **The fixture exists and is qualified offline** — `check.py`/`check_test.py`
   built, the failing-then-passing shape verified without any model (run
   the test command by hand against both the broken and fixed versions).
3. **A live completion, never a `/v1/models` listing** — the phased-session
   record's own precondition 2, unchanged, reused here.
4. **The machine is quiet.** Recorded, not silently assumed.
5. **Model and tool identity verified from the transcript's own fields**
   after the run — the model's `message.model`, and `run_self_test`'s
   presence in the actual `tool_execution_start` events, never assumed
   from the requested argv or `--tools` flag.

## What voids a run

A refused chain (the implementer crashes or times out before any tool
call is possible); a transcript-observed model that is not the requested
one; an inference setting that changed under the run. A voided run is
re-run in full under a new record, not patched.

## What happens after

State plainly whether `run_self_test` was called, whether its content
was legible enough to act on, and what the harness's own post-exit
`SelfTestOutcome` recorded for comparison. Do not propose extending `n`
from this result, and do not fold this smoke's cost or outcome into any
TE denominator — it answers a route-operability question, the same
category HP7 itself is scoped to, not a comparison question.
