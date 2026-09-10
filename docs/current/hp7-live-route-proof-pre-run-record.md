# Pre-run record — HP7, one bounded live route proof

Written 2026-09-09, **before any inference and before any live run**. Every
value below is frozen at the moment of writing; a value chosen or changed
after reading a result is the shape the spike protocol forbids. **This
record authorizes no implementation, no merge, no commit and no inference.**
HP7 needs its own budget authorization, separate from this document
(`ROADMAP.md`, HP7 row: "proposed, budgeted").

Design: [orchestrated delivery](orchestrated-delivery-design.md), D7.
Plans: `docs/superpowers/plans/2026-09-09-hp1-handoff-packet.md` through
`docs/superpowers/plans/2026-09-09-hp6-chain-retention.md` — HP1–HP6, all
**implemented, awaiting acceptance** as of this writing, and unaccepted work
is not a foundation to spend a budgeted run on. Sibling record:
[pre-run record — the phased session, Baseline](agentclinic-session-phased-pre-run-record.md),
which this one narrows rather than repeats: same task, same model family,
now routed through the packet contract instead of a plain session.

## What this run is for, and what it is not

**The question this run asks is only: does one real implementer complete the
three-phase packet chain end to end, with every packet, mutation, decision
and cost retained exactly as HP6 requires?** That is operability, not
superiority — D7's acceptance names it exactly:
*establishes operability and not superiority*.

**This run cannot establish, and no reading of it may claim:**

- That the packet route produces better, worse, or even different outcomes
  than the plain session route already run three times on this task
  (`docs/current/agentclinic-session-phased-pre-run-record.md`,
  `docs/current/agentclinic-verification-triage-screen.md`). That comparison
  is D8/HP8, separately authorized, and this run's counts stay outside its
  denominator.
- That an orchestrator adds value. **Phase HP runs no orchestrating model.**
  Packets are built deterministically by `build_packet` and reviewed before
  dispatch — autonomous packet authoring is explicitly out of scope for the
  whole phase (`orchestrated-delivery-design.md`, "Amended 2026-09-09"). The
  window HP5/HP6 label "orchestrator" is therefore expected to hold **no**
  mutation and **null** cost throughout this run: nothing acts between one
  phase's `after_handoff` and the next `before_handoff` except the route's
  own bookkeeping. A non-empty orchestrator window here would itself be a
  finding, not the expected shape.
- Anything from `n = 1`. One run distinguishes a pathology from a fluke not
  at all. `n` is frozen and **not extended after reading the result**; a
  second cell is a new proposal and a new pre-run record.

## The arm

**Baseline only**, matching the existing phased-session record exactly —
same model family for the same reason given there: the per-phase turn
figures this workload's design reasons about come from the Gemma-family
baseline arm.

| Field | Value |
|---|---|
| Arm record | `arms/baseline.json` |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` |
| Server model | `gemma-4-12B-it-MLX-8bit` |
| pi | `0.84.4` |
| Context window | 80000 |
| Max tokens | 8192 |
| Compaction | enabled, reserve 16384 |
| Temperature | 1.0 |

**Tool surface is the adapter's, not `command_implementer`'s.** `route.py`'s
executable seam is only an argv and two env vars —
`command_implementer` itself enforces nothing about what a worker may touch,
a correction to this record's own earlier wording, caught by the Astra-style
review (`route.py` module docstring: "What this module does **not** do:
apply patches ... or decide verdicts" is a statement about the *route*, not a
guarantee about any implementer behind it). The tool surface for this run is
`adapters/pi_implementer.py`'s own choice: `read`, `write`, `edit`, and
**no** `bash`, passed to Pi's `--tools` flag. This is **not** the
`read,bash,edit,write` surface the phased-session pre-run record used, and no
sentence from this run may be read against that one as if the surface were
held constant — the confound `orchestrated-delivery-design.md` names for D8
applies here too, one run early. Nothing enforces `writable_paths` on this
seam either (see precondition 1); that is HP6's `check_chain` to report, not
this adapter's to prevent.

## The task and the route

| Field | Value |
|---|---|
| Task | `agentclinic-session-phased` |
| Task tree sha256 | `1af60a147bcf6459fab39f2f94f75ba96968ae0dbfe1312ee52858d6b1053951` |
| Repo commit | `275f963` (`HP6: retain the chain, so a decision survives the process that made it`), clean tree |
| Route | `satyrn_evals.route.run_phases`, the executable seam (`command_implementer`), observed by an HP6 recorder |

Recompute the task tree digest:

```
uv run python -c "
import hashlib
from pathlib import Path
t = Path('src/satyrn_evals/tasks/agentclinic-session-phased')
h = hashlib.sha256()
for p in sorted(t.rglob('*')):
    if p.is_file():
        h.update(p.relative_to(t).as_posix().encode()); h.update(p.read_bytes())
print(h.hexdigest())
"
```

Prompt digests (sha256, first 16 hex, of the prompt string `build_packet`
renders as `objective` — preamble and the adopted verification sentence
included, since both are already part of `session.json`, not added for this
run):

| Step | Digest | Bytes |
|---|---|---|
| `phase-1-home` | `9238e5d3a1265a6c` | 1579 |
| `phase-2-board` | `8bc6457681df6448` | 1622 |
| `phase-3-add` | `6fcfd29df448f013` | 1190 |

Recompute:

```
uv run python -c "
import hashlib, json
from pathlib import Path
spec = json.loads(Path('src/satyrn_evals/tasks/agentclinic-session-phased/session.json').read_text())
for s in spec['steps']:
    print(s['id'], hashlib.sha256(s['prompt'].encode()).hexdigest()[:16], len(s['prompt'].encode()))
"
```

**The adopted verification instruction is already in these prompts and in
`self_test_command`** (`["uv", "run", "python", "-m", "pytest", "tests"]`) —
it is the policy `ROADMAP.md` names as adopted 2026-09-09, not something
authored for this run. HP7 does not re-run the verification-instruction
question; it inherits the answer.

## Run parameters

| Field | Value |
|---|---|
| **n** | **1 chain** (three phases), frozen, not extendable after reading |
| `base_revision` | the task tree sha256 above |
| `turn_budget` | 20 |
| `tool_call_budget` | 30 |
| `--step-timeout` | 600s, matching the phased-session record's reasoning: the 2026-09-01 spike censored two of four Phase-3 runs at 300s |

**`turn_budget`/`tool_call_budget` are declared, not enforced, on this
route.** HP6.3's declaration ledger records both `declared_not_applied` for
the offline route — no code counts a turn or a tool call
(`src/satyrn_evals/chain_record.py`, `declaration_ledger`). The numbers above
only shape what the packet's rendered text tells the implementer; they cap
nothing. They are set at roughly 3x the largest per-phase figure retained
from the two real phased sessions already run on this task (max observed: 7
turns, 6 tool calls per phase —
`~/satyrn-smokes/2026-09-09-session-phased-verify-114708/*/session-record.json`)
rather than invented, per `BRIEF.md`'s rule to check representative retained
attempts before choosing a budget figure — even an inert one, since an
implausible number in a rendered packet is itself a defect class this
project has already named (SwiftStar's declared-versus-sent `sampling`
field, `orchestrated-delivery-design.md` §"A related trap").

## The two questions, stated separately

**Outcome.** Does the chain reach `phase-3-add` accepted, judged by the
existing hidden per-checkpoint grading (4/10/13 cumulative checks)? Reported
**even when the chain fails early** — an implementer refusal or a grader
rejection is a result, not a voided run (`BRIEF.md` comparison policy,
"outcome-shaped signals are not stop triggers").

**Cost — descriptive, not graded.** Implementer and orchestrator cost,
reported **separately, never summed** (HP6.4). No pass/fail cost threshold
exists, matching the phased-session record's rule for the plain session.
Implementer mutation counts are reported **even when every phase is
accepted** — HP5/HP6's whole reason for existing is that a passing chain can
still hide a silent implementer (the seed-221 shape), so a clean pass with
zero implementer mutations is exactly the finding this run must be able to
show, not a result this record predicts.

## What this run retains, and what closes it out

The full `ChainRecord` (HP6.2), written durably before any grading or
cleanup (`BRIEF.md` invariant 1). Specifically:

- `check_chain(record)` is read and reported **as returned**, findings and
  all — not summarized as "clean" unless it returns `()`.
- `decisions_from_record(record)` is checked to equal the route's own
  returned decision sequence, proving the retained document is sufficient on
  its own, per HP6.7's acceptance.
- The declaration ledger for every phase, so the run's own record states
  which packet fields were declared-and-unapplied rather than leaving that
  to be assumed from the offline-route default.
- Per-phase `fallback` labels — expected `False` throughout per the
  no-orchestrator-model note above; a `True` anywhere is reported as a
  finding to investigate, not summarized away.

## Preconditions, all required before the run starts

1. **Resolved 2026-09-09.** A real implementer executable for the packet seam
   now exists: `adapters/pi_implementer.py`
   (`satyrn-evals-implementer-pi`), one bounded `pi --print --mode json`
   turn on a `read,write,edit` surface — no `bash`, which is *why*
   `self_test_command` stays declared-and-unapplied on this seam rather than
   something to reconcile — with changed files found by content digest
   (`attribution.snapshot`) rather than `git diff`, since a route workspace
   is a plain directory, not a git checkout. **It deliberately does not
   enforce `writable_paths` on itself**, unlike the test fixtures: a real
   adapter policing its own declared scope would make
   `declaration_ledger`'s `writable_paths` state true by construction, which
   is exactly the capture-integrity gap HP6.3 exists to catch. Proven only
   at the adapter's pure surface (`tests/test_pi_implementer.py`,
   `subprocess.run` replaced) — **no run against a real Pi process has
   happened**, which is precondition 4 below, unchanged.
2. **Acceptance for HP1–HP6.** The ordering rule in `ROADMAP.md` — "HP4, HP5
   and HP6 all gate HP7" — is stated against implementation, and all three
   (plus HP1/HP2) are implemented; **none has been through its Astra
   acceptance review yet.** Spending a budgeted live run on unaccepted
   machinery risks re-doing the run after a review finding changes retained
   behavior.
3. **The environment the preamble promises must exist**, exactly as the
   phased-session record's precondition 1 required: materialize `base/`, run
   the pinned install, confirm `fastapi`, `turbohtml`, `pytest` import at the
   pinned versions, before any inference.
4. **A live completion, never a `/v1/models` listing**, at the pinned model
   name — the phased-session record's precondition 2 names the exact reason
   this is checked live rather than assumed from a listing.
5. **The machine is quiet.** Recorded, not silently assumed; no wall-clock
   comparison is possible or claimed from a single-arm run regardless.
6. **Model identity verified from the transcript's own field** after the run,
   never from the requested argv.

## What voids a run

A refused chain record (fails `ChainRecord`'s own version or shape checks); a
transcript-observed `message.model` that is not the requested model; an
inference setting that changed under the run; or a `check_chain` finding of
"implementer window was never observed" for any phase — that specific
finding means the harness, not the model, failed to retain what it exists to
retain, and the harness defect is fixed before any re-run rather than the
run being reported around it. A voided run is re-run in full under a new
record, not patched.

## What happens after

Read the retained `ChainRecord` and `check_chain`'s output. State plainly
whether the chain completed, what it cost by role, and whether any fallback
or unobserved-window finding appeared. Do not propose D8 (the workflow
comparison) from this run's counts — that needs its own separate
authorization and its own frozen design, and this run's `n = 1` stays
outside its denominator either way.
