# HP5 implementation plan: role attribution from retained events

**Design:** [HP5](../specs/2026-09-09-hp5-role-attribution-design.md), and
[orchestrated delivery](../../current/orchestrated-delivery-design.md)
deliverable D5. Phase HP, cycle 5. Authorizes no inference.

**Goal.** Report, for a completed chain, which role changed each file —
from harness observation, never from the implementer's claim.

## Where attribution lives, and where it does not

**Not in the route's decision path.** The spec is explicit that attribution
observes and never gates: a chain that passes with zero implementer
mutations still passes, and the record says both things. So `run_phases`
keeps its signature, its return type and its accept-or-reject rules, and
gains exactly one optional keyword.

**Not a second plugin system.** The route already takes its implementer and
its grader as callables, and `BRIEF.md` invariant 6 says a test seam is the
extension seam. The observer is one more callable of the same kind, injected
the same way, and it is what a live run will drive too.

**Snapshotting is the caller's job.** The route says *when* a window opens
and closes; what to record at that moment is the observer's business. That
keeps the route free of a tree walk it has no other use for, and it keeps the
default tier honest: the fixtures snapshot a real temporary directory, and
nothing spawns.

## The windows

Per phase, the route calls the observer twice, and once more when the chain
ends:

| boundary | when |
|---|---|
| `before_handoff` | immediately before the packet goes to the implementer |
| `after_handoff` | immediately after the implementer returns, before grading |
| `chain_end` | once, after the last phase, on every exit path |

From those, two windows per phase:

- **implementer window** — `before_handoff` to `after_handoff` of the same
  phase;
- **orchestrator window** — `after_handoff` of phase N to `before_handoff` of
  phase N+1, and for the last phase to `chain_end`.

Anything the orchestrator does — integration, a fix-up, a fallback that does
the phase's work outright — falls in the second. That is the seed-221 shape's
only hiding place, and it is now a named window rather than a gap between
log lines.

## Slices

**HP5.1 — the snapshot and the mutation.**
`snapshot(workspace) -> Mapping[str, str]`, path to content digest, skipping
the harness's own bookkeeping files. `diff_snapshots(before, after) ->
tuple[Mutation, ...]`, each carrying its path and one of `created`,
`deleted`, `modified`.
*Acceptance:* the three kinds are distinguished; an unchanged tree yields
none; a same-length content change is still a mutation, which is why this
compares digests and not sizes or timestamps. A file the harness wrote for
its own use never appears, and that exclusion is asserted by name rather
than left to a glob nobody reads.

**HP5.2 — the boundary observer on the route.**
`run_phases(..., observer=None)`, called with `(step_id, boundary)`.
*Acceptance:* **with no observer the route is unchanged** — the same
decisions on `ROUTE_SCENARIO` as HP2 asserts, so this slice cannot alter a
verdict. With one, the boundary sequence is exactly the expected list. An
implementer refusal and a grader rejection each still close their phase's
window and still emit `chain_end`, because a chain that stops early is
precisely when attribution matters most and is the easiest path to leave
unclosed.

**HP5.3 — the ledger.**
`attribute(...) -> ChainLedger`: per phase, the implementer's mutations, the
orchestrator's, and the files the implementer *reported*. Totals are
computed, never accumulated as the phases run.
*Acceptance:* a window whose snapshots were never taken is reported
**unobserved**, not zero — the spec's fifth acceptance, and the 2026-09-08
detached-worker gap in a new place. A test recomputes one total from the
retained ledger rather than transcribing it (`BRIEF.md` invariant 1).

**HP5.4 — three fixtures, and the direction that separates them.**
*Acceptance:* a delivered chain attributes every mutation to the implementer
and **zero** to the orchestrator. A seed-221 chain — the implementer returns
having written nothing, the orchestrator writes the files between phases —
reports **zero implementer mutations**, reported rather than passed over. A
**mixed** chain, one phase delivered and one repaired by the orchestrator
after an under-delivery, splits per phase. The third is the case a report
that always names one role cannot satisfy, and it is why the first two are
not enough (`BRIEF.md` invariant 5).

**HP5.5 — the claim against the observation.**
Both are retained per phase and the difference is stated, never reconciled.
*Acceptance:* an implementer reporting a file it did not write is recorded as
claimed and not made; a truthful sibling records no discrepancy. The report
states the discrepancy and **does not classify it** — deciding what it means
is a pathology detector, which this cycle excludes.

## Explicitly not in HP5

Judging whether delegation helped (HP8, separately authorized). Any pathology
detector or classification of a run. Thresholds of any kind, including "too
few mutations" — `BACKLOG.md` defers budget verdicts with a recorded reason.
Line-level or hunk-level attribution. Attributing a mutation to a model turn,
which needs turn-keyed worker events and is D6's shape. Any change to the
route's accept-or-reject rules.

## Verification

`just gates`, exit code read directly, never piped.

Every slice here is default tier: the fixtures write files into a temporary
directory and nothing spawns. The marked tier is re-run once by hand anyway,
because HP5.2 touches `run_phases`, which the executable seam drives:

```
uv run pytest -q -m integration tests/integration/test_hp2_route.py
```

Five marked-tier failures in this worktree are unrelated and recorded in
`BACKLOG.md`; they must not be read as this cycle's.

## What the implementation found, recorded rather than edited away

**The seed-221 implementer could not be written as first imagined.**
`ImplementerResult` refuses `delivered` with no changed files, so a fake that
delivers nothing and says so is impossible. The fixture therefore reports a
file it never writes — which is the more dangerous shape anyway, and the one
HP5.5 exists to record: a claim with no work behind it.

**A repeated window is refused rather than resolved.** A second
`before_handoff` for a step used to overwrite the first snapshot silently.
Keeping the later half of an ambiguous recording would report a number
computed from an arbitrary part of the evidence, so `attribute` now refuses
both a doubly-opened and a doubly-closed window.

**Five mutations, each killed.** Turning an unobserved window into an
observed zero: 3 failures. Always attributing to the implementer: 6. Always
attributing to the orchestrator: 9. Making `claimed_not_made` always empty: 1
— that gate has a single test holding it by design, since its sibling is
meant to pass unchanged. Dropping the `after_handoff` boundary from the
route: 9.

**Verification.** `just gates` exit 0; 1,695 default-tier tests;
`satyrn_evals/attribution.py` and `satyrn_evals/route.py` both at 100%
statement and branch coverage; `tests/integration/test_hp2_route.py` 7 passed
in the marked tier. The five unrelated marked-tier failures recorded in
`BACKLOG.md` are still present and are still not this cycle's.
