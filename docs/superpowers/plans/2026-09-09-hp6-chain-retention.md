# HP6 implementation plan: the chain retained and re-scorable

**Design:** [orchestrated delivery](../../current/orchestrated-delivery-design.md),
deliverable D6. Phase HP, cycle 6. **Plan only, no spec**, per the phase
table: nothing here moves an evaluation condition, an evidence boundary, a
task contract or an interpretation. Authorizes no inference and no run.

**Goal.** Make one route execution leave behind a document from which every
acceptance decision recomputes, and from which the two things a chain can
hide — an unobserved implementer step, and a declaration the runtime never
applied — are readable rather than absent.

## What is missing, stated exactly

`run_phases` returns `list[PhaseDecision]` and keeps nothing
(`src/satyrn_evals/route.py:216-279`). The packets it builds are discarded
after the call. HP5's observer sees boundaries and no content
(`route.py:44-55`), so attribution can say *how many* mutations a role made
and never *against which packet*. Once the list of decisions goes out of
scope there is no artifact at all, so `BRIEF.md` invariant 1 — every decision
recomputes from retained artifacts — holds only for as long as the process
that made the decision is alive. That is not retention.

Two specific gaps follow, and they are the ones D6 names.

**An unobserved step is indistinguishable from a clean one.** HP5 already
refuses to report an unobserved window as zero
(`src/satyrn_evals/attribution.py:129-145`), which is the 2026-09-08
detached-worker gap held at the ledger. Nothing yet **fails** on it. A chain
whose middle phase retained no events is presently a chain with a shorter
ledger, and a shorter ledger reads as a quieter run.

**Every packet budget is declared and never applied.** `turn_budget` and
`tool_call_budget` are built into each packet and appear nowhere else in
`src/satyrn_evals/` outside `packet.py` and the `build_packet` call in
`route.py` — no code counts a turn or a tool call. `self_test_command` is
carried and never run. `base_revision` names a revision the offline route
does not check out; HP3 does that engine-side. `redacts` is enforced by
`assert_projection_is_clean`, which runs **only** inside
`command_implementer` (`route.py:294-319`) — so on the in-process seam the
redaction list is declared and unapplied too. `writable_paths` is enforced by
the implementer against itself, never by the route.

SwiftStar names this exact defect family against itself for `sampling`
(`PoolOrchestrator.swift:70-78`), and HP1 already dropped two fields rather
than record a declaration nothing applies (`packet.py:8-19`). HP6 is where
the remaining ones stop being silent: they are kept, because a live engine
does apply several of them, and each is recorded **declared and not
applied** rather than dropped or implied.

## The seam, decided once

The recorder needs the packet, the result and the decision. HP5's observer
carries `(step_id, boundary)` and nothing more.

**The seam is widened, not duplicated.** `BoundaryObserver` becomes
`Callable[[BoundaryEvent], None]` over a frozen `BoundaryEvent` carrying the
step id, the boundary, and the content available at that edge: the packet at
`before_handoff`, the result at `after_handoff`, the decision at
`chain_end`. Attribution ignores every field but two.

The alternative — leaving HP5's observer alone and adding a recorder
parameter beside it — is the second plugin system `BRIEF.md` invariant 6
refuses. The cost of widening is that HP5's tests move with the signature,
which is a rename and not a rewrite, and it is paid once.

Rebuilding the packets after the fact from `build_packet` was considered and
refused. `build_packet` is pure, so a rebuild would agree with the run by
construction, and a record that agrees with the run by construction proves
nothing about the run. Retention means capturing what crossed.

## Slices

**HP6.1 — the widened event, and HP5 adapted to it.**
`BoundaryEvent` in `route.py`; `run_phases` emits one per edge. HP5's
attribution grows a small adapter and loses nothing.
*Acceptance:* the HP2 route scenario produces the identical decision
sequence with an observer and with none, as it did before HP6 — the same
assertion that proved HP5 moved no verdict. Every HP5 mutation still dies.

**HP6.2 — the chain record data contract.**
`ChainRecord` and `PhaseRecord`, frozen and slotted, versioned, following
`session_record.py`'s durable shape exactly: `asdict`, fsync, atomic
replace, and a loader that shape-checks **before** conversion. A phase holds
its packet, the implementer's reported result, the decision with its reason,
the validation output the grader returned, and the observed mutations from
both sides of the hand-off.
*Acceptance:* a golden chain record from the HP2 scenario, asserted
byte-for-byte, the way HP1's golden packet is. A record written and reloaded
is equal to the original. A truncated document and a document with a future
version are each refused, and the well-formed sibling loads
(`BRIEF.md` invariant 5).

**HP6.3 — the declared-and-not-applied ledger.**
Each packet declaration is recorded with what the runtime did with it: a
per-field `applied` state whose three values are *applied*, *declared and
not applied*, and *unknown*. Absent is never spelled as applied, and
unapplied is never spelled as absent.
*Acceptance:* on the offline route, `turn_budget`, `tool_call_budget`,
`self_test_command` and `base_revision` are recorded declared-not-applied,
and `writable_paths` is recorded applied by the implementer rather than by
the route. `redacts` is declared-not-applied on the in-process seam and
applied on the executable seam, which is one field taking both values from
the same task — the sibling that proves the ledger is reading the runtime
and not a constant.

**HP6.4 — cost per role, null when unmeasured.**
A per-role cost field on each phase, `None` when nothing measured it. The
offline route measures no model cost, so offline the honest record is null
throughout.
*Acceptance:* an offline chain reports null orchestrator cost and null
implementer cost, and a chain fed measured costs reports them separately and
never summed. A zero is refused as a stand-in for unmeasured, which is
HP5's unobserved-is-not-zero rule in a second place.

**HP6.5 — orchestrator fallback, labelled from observation.**
A phase whose orchestrator window holds mutations is labelled as carrying
fallback work, beside the implementer's own reported outcome for that phase.
The label states what was observed; it does not judge whether the fallback
was warranted.
*Acceptance:* HP5's mixed chain — deliver, under-deliver-and-repair, deliver
— labels exactly the middle phase, and the all-delivered chain labels none.

**HP6.6 — the chain check, which is the detached-worker gap as a test.**
`check_chain(record)` returns findings. A phase with no retained events for
the implementer window is a finding. A phase whose recomputed decision
disagrees with the retained one is a finding. A clean chain returns none.
*Acceptance:* the HP2 chain returns no findings; the same chain with one
phase's implementer window removed returns exactly that finding, naming the
step; and a chain reporting **zero observed** implementer mutations returns
**no** finding, because a real observation of zero is the seed-221 shape HP5
exists to report and not a retention failure. That pair is the whole point
of the slice: absent and observed-zero must not land on the same verdict.

**HP6.7 — recomputation, end to end.**
`decisions_from_record(record)` re-derives the accept-or-reject sequence
from the retained document alone, with no task directory, no manifest and no
grader.
*Acceptance:* the sequence equals what `run_phases` returned, for the
delivered chain, for a chain stopped by an implementer refusal, and for a
chain stopped by a grader rejection — all three exit paths, since a
recomputation that only handles the happy path retains nothing about the
runs that matter.

## Explicitly not in HP6

Cost thresholds, a budget verdict, or any use of a recorded cost to decide
anything. **Applying** any declaration the ledger records as unapplied —
enforcing a turn budget is a change to what the route does, not to what it
retains. Any new pathology detector. Any real model (HP7). Any comparison
(HP8).

## Verification

`just gates`, exit code read directly, never piped — the recorded lesson is
that a piped gate reports `tail`'s status. `just lint-docs` for this file and
its toctree entry.

Every slice is default tier except the `redacts` half of HP6.3, which needs
the executable seam, so the marked tier is re-run once by hand:

```
uv run pytest -q -m integration
```

The five unrelated marked-tier failures recorded in `BACKLOG.md` are
expected to still be present and are still not this cycle's.

Mutation sweep, on a quiet tree, one mutation at a time: report an
unobserved window as an empty one; make `check_chain` always return no
findings; make the applied-state constant; sum the two role costs; label
every phase a fallback; and drop the packet from the retained record.
