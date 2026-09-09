# HP1 design: the handoff packet

Written 2026-09-09; **revised the same day after a deep review that found
twenty-three defects, several of them load-bearing.** Corrections are marked
rather than edited away. Phase HP, cycle 1. Design only: **it authorizes no
implementation and no inference.** Read with
[the phase design](../../current/orchestrated-delivery-design.md), which
settles ownership and the one path being built.

HP1 defines the packet as a **data contract in `satyrn-evals`** and nothing
more. Executing a packet is HP2, isolation is HP3, and both are out of scope.

## A retrieved record that changes this cycle's scope

`satyrn-engine` already considered a pinned-facts field in its handoff
contract and **deferred it, with evidence and two separate reopen
conditions** (branch `research/facts-field-backlog`, commit `7b847eb`,
2026-09-02, still unmerged).

**The `facts` field's condition** is an Evals experiment that isolates
contract **content** from contract **delivery**. Phase HP changes both at
once, so HP1 **specifies** the field and does not claim that deferral closed.

**Autonomous authoring is measured, and its condition is different.** A
2026-08-15/16 spike found machine-made bounds do confine an implementer, and
packet content does move outcomes floor to ceiling, but a system authoring
and gating that content autonomously scored **3/8 against 8/8 by hand**, and
a remediated authoring prompt **collapsed to 0/8, all no-op**
(`local-ai-pi/ROADMAP.md:386-402`, verified at source). That entry reopens
"on a deterministic authoring path, or on evidence that a newer model closes
the 3/8-versus-8/8 gap".

> **Correction.** This design first attached the *facts* condition to
> autonomous authoring. It does not apply. And `build_packet` below **is** a
> deterministic authoring path, so the authoring entry's own condition is
> arguably met by this cycle. Keeping autonomous authoring out of Phase HP is
> a **scope judgment**, not a claim the condition is unmet.

**Consequence.** HP2 runs an **inspected** packet, built deterministically
and reviewed, so an HP2 failure is readable as an execution defect rather
than an authoring one.

## Fields

Mapped from `swiftstar/Sources/SwiftStarKit/HandoffPacket.swift:62-90`.

| Field | Type | Why it is here |
|---|---|---|
| `objective` | `str` | The phase's own prompt text, from `session.json` |
| `facts` | `tuple[str, ...]` | Pinned decisions the implementer must not re-derive |
| `base_revision` | `str` | The state the phase starts from. HP3 chains these |
| `writable_paths` | `tuple[str, ...]` | The **declared** scope, rendered as today's contract renderer does |
| `preserve` | `tuple[str, ...]` | Earlier behaviour to keep, as prose |
| `self_test_command` | `tuple[str, ...] \| None` | What the **implementer** may run for its own feedback loop |
| `redacts` | `tuple[str, ...]` | Strings the rendered packet must not contain |
| `turn_budget` | `int` | Bounding policy; **required**, never defaulted |
| `tool_call_budget` | `int` | Bounding policy; **required**, never defaulted |
| `role` | `PacketRole` | Which role the packet addresses |
| `version` | `int` | Schema version, so a persisted packet replays |

### No parent validation command, and why

> **Correction.** This design first carried `validation_command`, sourced
> from `manifest.oracle`. For this task that is
> `python -m pytest -p satyrn_evals.oracle_hook`
> (`src/satyrn_evals/tasks/agentclinic-session-phased/manifest.json:5`), so
> the packet would have put **the hidden oracle hook into a document the
> implementer reads**. `manifest.py:76-77` already refuses a `public_suite`
> naming that plugin for exactly this reason, and neither `redacts` nor
> `scan_texts` would have flagged it. The command is also not runnable as
> written: grading appends selectors and materializes the overlay
> (`src/satyrn_evals/grade.py:125-127,151,163-171`).

**The field is removed, not set to `None`.** Acceptance is decided by the
harness's hidden per-phase grading, which the packet never names. A field
that is always empty is a declaration the runtime does not apply, which is
the capture-integrity defect this design refuses elsewhere. It reopens when a
task offers a command a parent can run in a candidate worktree without
grader material.

### `self_test_command` comes from the session spec

Not from `manifest.public_suite`, which this task does not declare. Adding
one would also register the engine's `run_tests` tool for the task
(`engine_contract.py:89-95`), changing an unrelated surface. So it is a
spec-level key beside `facts`, and for this task it is the command the
prompts already name.

### Fields deliberately not carried

- **`sampling`.** SwiftStar records that carrying a declared sampling setting
  the runtime does not send "was itself a new capture-integrity lie"
  (`PoolOrchestrator.swift:70-78`). Nothing here applies one. Reopens when a
  runtime does.
- **`baselines`.** SwiftStar's per-file digest read at dispatch time is the
  worker's mutation guard. It needs a revision to be read against, which
  arrives with HP3's chained checkouts; reading it here would also make
  `build_packet` impure. **Deferred to HP3**, recorded rather than dropped.
- **`textContract`.** A SwiftStar rendering flag with no analogue here.

## What `render_packet` emits

Enumerated, because three gates depend on it: `objective`, `facts`,
`preserve`, `writable_paths`, `self_test_command`. **`redacts` is never
rendered** — a packet that printed its own forbidden strings would refuse
itself. `role`, `version` and the budgets are metadata and are not rendered.

**`self_test_command` renders as one shell-quoted command line, not as one
bullet per argv token.** A list of tokens is not something an implementer can
run. Found in review as a real defect rather than a formatting preference.

**Budgets carry no defaults.** Two unexplained numbers frozen into the golden
file would be a decision nobody made, so the caller states them.

## Modern Python shape

`type` aliases for `PacketRole` and the command type; a frozen slotted
dataclass; `match` for validation dispatch, in the style of
`contamination.overall` (`contamination.py:283`). *(Correction: this first
cited `session_manifest.py`, which contains no `match` statement.)* Commands
are `tuple[str, ...] | None`, where `None` means the task offers none —
distinct from `()`, which would mean an empty command. Refusals raise
`PacketError(UsageError)` beside `SessionSpecError` in `errors.py`.

## Acceptance

Every refusal ships with the sibling success that proves it can pass, and
every check is shown to work in both directions (`BRIEF.md` invariants 1 and
5). *(Correction: this design first cited "rules 3, 6 and 8", which are the
archive's numbering.)*

1. **Golden packet.** One packet from `phase-2-board`, asserted
   byte-for-byte.
2. **`facts` is load-bearing at build time.** `build_packet` refuses a step
   whose facts are empty; the real step is accepted. The loader still
   defaults facts to empty, so an older spec loads.
3. **Redaction gate.** A packet whose rendered text contains any `redacts`
   string is refused; the same packet without it is accepted. **Blank
   rendered text is refused**, because "no secret appeared" in a document
   with no content is an absence of signal reported as a pass.

   > **Correction, after implementation.** This check first said the gate
   > "reuses `scan_texts`" and refuses on its `unmeasured`. `scan_texts`
   > matches the **overlay's own relative paths**, not arbitrary strings
   > (`contamination.py:211-247`), so it cannot implement this gate. There
   > are two gates with different jobs: `assert_redactions_absent` compares
   > the packet's declared strings by substring and refuses blank text, and
   > `assert_overlay_absent_from_packet` runs `scan_texts` and refuses both
   > `flagged` and `unmeasured`.
4. **Every rendered field is actually rendered.** Each field in the list
   above appears in the output, asserted individually, and the contamination
   fixture is parametrized over all of them. Without this, a renderer that
   dropped fields would satisfy check 3.
5. **No hidden selector reaches a packet**, over the real task, with a
   planted-selector sibling.
6. **`preserve` carries no selector.** Defined as: no entry contains `::`,
   and `scan_texts` over the entries is clean.
7. **Recorded prompt digests are unchanged.** A test computes `session.py`'s
   digest over each step of both spec files and asserts the six values
   recorded at
   `docs/current/agentclinic-verification-triage-screen.md:33-35`.
8. **Version round-trip.** Version 1 loads; an unknown version is refused.
9. **No model, no network, no subprocess.**

## Two decisions, settled by the maintainer 2026-09-09

**`facts` is a per-step key in `session.json`.** The loader compares against
an exact key set (`session_manifest.py:22,44`), so the key is added there and
unknown keys stay refused. It is optional in the loader and required by the
builder.

**`preserve` carries prose, not selectors.** A selector list would put grader
node ids in a document the implementer reads, contradicting `redacts` in the
same packet.

> **Correction.** An earlier draft said `facts` is refused "only when the
> packet declares it required". No such declaration exists among the fields.
> The rule is stated once, above: optional in the loader, required by the
> builder.

## What changes when `facts` lands, and what does not

Adding the key changes **the spec file digests and the task tree hash**
recorded at
`docs/current/agentclinic-verification-triage-screen.md:32,62`. Both become
historical, and both get recorded as a correction to that record rather than
edited into it. The **prompt digests at `:33-35` do not change**, because
`facts` never reaches a prompt, and acceptance check 7 is the evidence.

> **Correction.** An earlier draft proposed a "prompt invariance" test
> comparing prompts built with and without facts. That test cannot fail:
> `session.py:396` sends `spec_step.prompt` verbatim, so no builder exists
> that could append anything. Check 7 replaces it with a claim that can fail.

## Out of scope

- Executing a packet, isolation, file creation, attribution, retention.
- The declared-versus-enforced scope mismatch, which is HP4's. The packet's
  `writable_paths` is the **declared** scope and is not what the session
  route enforces (`patch.within_source`).
- Autonomous packet authoring, per the scope judgment above.
- `sampling`; `baselines` before HP3; a second `PacketRole` member.
- Any change to `session.json`'s **existing** keys, or to the graders.
