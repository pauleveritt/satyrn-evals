# Self-test evidence: the harness runs `self_test_command`

Written 2026-09-10. A precondition for HP7, not a numbered HP cycle of its
own. Design only: **it authorizes no implementation beyond itself and no
inference.** Read with
[the HP7 pre-run record](../../current/hp7-live-route-proof-pre-run-record.md),
whose "implementer cannot run its own verification" gap this closes, and
with `route.py`'s module docstring, whose "does not... decide verdicts" this
must keep true.

This closes one of HP7's two disclosed blocking gaps: `self_test_command` is
declared in every packet and never applied
(`chain_record.declaration_ledger`, `AppliedState.DECLARED_NOT_APPLIED`,
hard-coded), because nothing runs it. `adapters/pi_implementer.py` has no
`bash`, on purpose, so the model cannot run it either. The fix named in the
pre-run record is narrow: **the harness runs it, and retains what happened.**

## What this is not

**Corrected 2026-09-10.** This section originally claimed `pi_implementer.py`
lacks the turn capacity for self-correction and that closing this would need
"a multi-turn retry loop." That reasoning was wrong: `pi --print --mode json`
already runs a complete multi-generation agent interaction inside one process
invocation, not one bounded turn — see the corresponding correction in
`adapters/pi_implementer.py`'s module docstring. Pi's own tool loop already
has the turn capacity; nothing here needs a new retry loop bolted on.

This is still not implementer self-correction, but for the real reason: the
harness runs `self_test_command` **after the process has already exited**,
so there is no running invocation left for the result to reach. A design
that actually closes the loop would expose the self-test as a **tool** Pi
can call from inside its own invocation, letting Pi's existing tool loop
carry the retry — not a new external retry mechanism. This spec closes the
narrower, already-named gap only: `self_test_command` goes from *silently
never applied* to *honestly applied-and-retained*, once, after the
implementer's invocation exits. Wiring it as an in-invocation tool is
separately scoped work, not attempted here.

## Where it runs

Inside `route.command_implementer`'s `implement()` closure — the one place
in this repository that already spawns a real subprocess for a live
implementer, and the only seam `declaration_ledger` already treats specially
(`redacts` reaches `AppliedState.APPLIED` only when `executable_seam` is
true). After the implementer's own subprocess returns successfully and its
result is read, if `packet.self_test_command` is non-empty, run it as a
second bounded `subprocess.run` in the same `workspace`, output captured
rather than inherited, with its own timeout.

It runs **only** on the executable seam. `scripted_implementer` and
`fake_implementer.py` never spawn it — matching `redacts`'s precedent
exactly, and keeping every default-tier test (which drives the in-process
seam, under the planted subprocess tripwire) unaffected. No new mock is
needed anywhere self_test execution is not being tested; only
`tests/integration/test_hp2_route.py`'s marked tier exercises a real
process.

A launch failure (the command does not exist, is not executable) and a
timeout are both caught, never raised: a self-test that cannot run is
evidence — a `ran=False` finding with a reason — not a route crash. Nothing
about `run_phases`'s existing crash handling changes; this is a new,
independent failure mode local to one bounded subprocess call, not a
reason to fail the phase.

## What is captured, and where it goes

A small immutable result, one per phase where it ran:

```python
@dataclass(frozen=True, slots=True)
class SelfTestOutcome:
    command: tuple[str, ...]
    ran: bool
    exit_code: int | None      # None when ran is False
    output: str                 # combined stdout+stderr; "" when ran is False
    reason: str | None          # set only when ran is False
    duration_seconds: float
```

`command_implementer` writes this to a new harness file in the workspace —
`.satyrn-self-test-result.json`, alongside `.satyrn-packet.json` and
`.satyrn-result.json` — rather than folding it into `ImplementerResult`.
`ImplementerResult` is what the **implementer** reports; this is what the
**harness** did after the implementer returned, a different actor, and
conflating the two would put a route-level action inside a contract that
`route.py`'s tests already pin byte-for-byte against a real process. The new
filename joins `attribution.HARNESS_FILES`, so it is never misread as an
implementer mutation the way `.satyrn-packet.json` already is not.

`chain_record.run_and_record_chain`'s existing `capture_candidate` hook —
already the place per-phase workspace evidence is read before grading —
reads this file when present and attaches it to the phase's record. `None`
when the file does not exist (in-process seam, or no `self_test_command`
declared). `PhaseRecord` gains one field:

```python
self_test_outcome: SelfTestOutcome | None = None
```

`build_chain_record`, the lower-level API with no workspace to read from,
always passes `None` here — the same shape `candidate_snapshot_path` already
uses for the same reason.

## The ledger

`declaration_ledger` gains one keyword parameter, `self_test_ran: bool`,
supplied by the caller that has the outcome in hand
(`run_and_record_chain`; `build_chain_record` always passes `False`). The
`self_test_command` entry becomes:

```python
"self_test_command": (
    AppliedState.APPLIED if self_test_ran else AppliedState.DECLARED_NOT_APPLIED
),
```

Two values only, not three. Unlike `writable_paths`, there is no ambiguous
middle case here worth an `OBSERVED_COMPLIANT`-shaped state: either the
harness ran the command (`APPLIED`, regardless of whether the tests
themselves passed — running it is what was declared, not passing it) or it
did not (`DECLARED_NOT_APPLIED`). A failed self-test that ran is still
`APPLIED`; whether it *passed* lives in `SelfTestOutcome.exit_code`, not in
the ledger.

## Never gates

`SelfTestOutcome.exit_code` must never reach `accepted` or `reason` on a
`PhaseRecord`. `PhaseGrader` — the hidden per-checkpoint grader — remains the
only decider of acceptance, exactly as it is today. This is required by
`route.py`'s own module docstring ("does not... decide verdicts") and by
HP5's established "observes, never gates" rule for everything the harness
retains about a phase beyond the grader's own verdict. A failing self-test on
an otherwise-accepted phase is retained and reportable, not silently
absorbed and not a reason to reject.

## Acceptance

1. On the executable seam, with a packet declaring a `self_test_command`
   that exits 0, the retained `PhaseRecord.self_test_outcome` shows
   `ran=True`, the real exit code, and non-empty output; the ledger shows
   `self_test_command: applied`.
2. The same, with a command that exits non-zero: `ran=True`, the non-zero
   exit code retained, ledger still `applied` — a failing self-test is not
   silently reclassified as unapplied.
3. A packet with no `self_test_command` declared: no self-test file is
   written, `self_test_outcome` is `None`, ledger stays
   `declared_not_applied`.
4. The in-process seam (`scripted_implementer`/`fake_implementer.py`): no
   subprocess is spawned regardless of what the packet declares;
   `self_test_outcome` is `None`; ledger stays `declared_not_applied`. A
   default-tier test proves no subprocess call happens here, matching the
   planted tripwire's own proof obligation.
5. A self-test command that cannot launch (bad executable) or times out:
   `ran=False`, a `reason` string, no exception propagates out of
   `command_implementer`, and the phase's `accepted`/`reason` are unaffected
   — driven by a real launch failure and a real timeout, not a mock, per
   this repository's own standard for subprocess-ordering claims
   (`tests/integration/test_pi_implementer_ordering.py`'s precedent).
6. Regardless of outcome, `self_test_outcome.exit_code` never appears in, or
   changes, `PhaseRecord.accepted`/`reason` — proven by a phase whose
   self-test fails but whose grader still accepts it.
7. `chain_record_to_dict`/`chain_record_from_dict` round-trip a
   `self_test_outcome`-bearing record without loss, matching every other
   retained field's own round-trip proof.

## Out of scope

- **Feeding the result back to the implementer.** No retry, no follow-up
  turn, no multi-turn loop. That is separately authorized future work.
- **Any pass/fail threshold or gate.** Acceptance is `PhaseGrader`'s alone.
- **Truncating or redacting captured output.** Full stdout+stderr is
  retained, matching this repository's existing untruncated-transcript
  precedent (`adapters/pi_implementer.py`'s append-mode transcript). A size
  limit, if one is ever needed, is a later, separately motivated change.
- **A configurable self-test timeout surfaced as a CLI flag.** A single
  default constant is enough: `command_implementer.DEFAULT_SELF_TEST_TIMEOUT_SECONDS
  = 600`, matching `pi_implementer.DEFAULT_TIMEOUT_SECONDS` — the same
  `self_test_command` (`uv run python -m pytest tests`) HP7's own pre-run
  record already reasoned about at that figure. Nothing here is bounding a
  live run's own budget (`turn_budget` stays its own, separately unapplied,
  declaration).
