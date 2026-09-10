# HP2 implementation plan: one inspected packet, executed offline

**Design:** [orchestrated delivery](../../current/orchestrated-delivery-design.md),
deliverable D2. Phase HP, cycle 2. **Plan only, no spec**, per the phase
table. Revised 2026-09-09 after a ruling on its tier split; the ruling
upheld the split and found three assignments that could not execute as
written. Authorizes no inference.

**Goal.** Carry the phased task's three requests end to end against a **fake
implementer**, and show the route accepts a known-good result and rejects a
known-broken one.

## The tier split, ruled on and corrected

`BRIEF.md` keeps the default tier free of model, network **and subprocess**;
the engine seam is an executable command, and real Git lives in the marked
integration tier. The split:

- **The route takes the implementer as a callable**,
  `type Implementer = Callable[[HandoffPacket], ImplementerResult]`. This is
  the house pattern, not a new one: the attempt path, the session executor,
  the Pi adapter and the grader each keep an executable as the public
  parameter and an in-process double at an internal boundary
  (`adapters/pi_session.py:159-171` is the closest analogue, and its driver
  test says so in its own docstring).
- **The executable-to-callable adapter ships in `src/`**, as
  `command_implementer(argv) -> Implementer`. It is what HP2.5 and later HP7
  call. *(Ruled: if that adapter existed only inside the integration test,
  the callable would be a different contract from the live one and the test
  would prove only its own fixture.)*
- **The result crosses the process boundary as a document**, written by the
  executable to an env-var path, mirroring the attempt seam's
  `SATYRN_ATTEMPT_PATCH`/`SATYRN_ATTEMPT_TRANSCRIPT`
  (`attempt.py:5-7`). One parser, `implementer_result_from_dict`, is the
  only path from that document to an `ImplementerResult`, so the default
  tier tests the **wire contract** on the same bytes the real process writes.

## Two things the default tier cannot do, and where they go instead

**It cannot apply a patch.** There is no pure-Python applier here; every path
is `git apply` (`grade.py:306`, `capture.py:545`), and the planted tripwire
blocks subprocesses in the default tier. **No second applier is written.** The
default-tier fake writes files directly; the checkpoint patches are
integration-tier inputs.

**It cannot tell known-good from known-broken.** Verified: the two fixtures
differ by one line, `datetime.now(timezone.utc)` against a naive
`datetime.now`. Only the oracle distinguishes them, and the oracle spawns. A
fixture-named verdict is therefore an **integration** check; asserting one in
the default tier would make "names the fixture" a label on a scripted verdict,
which is the fabricated-clean-number family the harvest index records.

*(`known-good.patch` is byte-identical to `checkpoint-3.patch`, confirmed with
`cmp`, so one fixture set serves both witnesses.)*

## What is reused rather than rebuilt

`fixtures/checkpoint-1..3.patch` as the per-phase progression;
`known-good.patch` and `known-broken.patch` as the accept and reject
witnesses; `SessionGrader` for verdicts; `patch.check_allowlist`
(`patch.py:181`, pure, so it works in both tiers) for scope. **No new grader,
no new scope rule, no new patch applier.**

## Slices

**HP2.1 — the result, and its wire form.**
`ImplementerResult` plus `implementer_result_from_dict`, with a golden
fixture in the HP1 style.
*Acceptance:* a result claiming success while reporting no changed files is
**refused**; a result with changes is accepted. A malformed persisted result
fails as itself, shape-checked before conversion, as HP1's loader does. The
implementer's own claim is never the verdict.

**HP2.2 — the fake implementer.**
Writes files directly, from a scripted table of per-phase contents.
*Acceptance:* it refuses to write outside the packet's declared
`writable_paths`, so a route defect cannot be masked by an obliging fake.

**HP2.3 — the route.**
`run_phases(task_dir, spec, implementer, workspace, grader)` builds a packet
per step, calls the implementer, grades the checkpoint, and records an
accept-or-reject decision **with its reason**.
*Acceptance:* three phases in order; phase N starts from phase N-1's accepted
state; a rejected phase **stops the route** rather than continuing.

**HP2.4 — the witnesses, split by tier.**
*Default tier:* the route's decision logic against a scripted grader —
accept on pass, stop-with-reason on fail, carry-forward from the accepted
predecessor. The precedent is
`tests/test_session_preservation_per_checkpoint.py:55-83`.
*Integration tier:* the real `SessionGrader` over the checkpoint patches,
`known-good` **accepted** and `known-broken` **rejected**, each named in the
assertion per `BRIEF.md`'s evidence floor. The shape exists already at
`tests/integration/test_session_ordering_regression_witness.py:38-75`.

**HP2.5 — the executable seam.**
One marked test driving `run_phases` through `command_implementer` and a real
checkout.
*Acceptance:* it asserts its accept-or-reject sequence against a **scenario
constant shared with the default-tier route test**, so the two seams cannot
drift apart while both stay green. Excluded from the default run, and its
exclusion asserted rather than assumed.

## Explicitly not in HP2

Chained worktrees (HP3), the declared-versus-enforced scope gap (HP4), role
attribution (HP5), retention shape (HP6), any real model (HP7). No
orchestrator: the route is driven by the test, because an inspected packet
needs no author. No second patch applier.

## Verification

`just gates`, exit code read directly, never piped.

**`just gates` will never reach HP2.4's or HP2.5's integration halves** — it
runs `pytest -q` with `addopts = -m "not integration"`, and there is no
integration recipe. So this cycle is not done until the following has been
run by hand and its exit code read:

```
uv run pytest -q -m integration tests/integration/test_hp2_route.py
```
