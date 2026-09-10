# HP1 implementation plan: the handoff packet

**Spec:** `docs/superpowers/specs/2026-09-09-hp1-handoff-packet-design.md`,
**including its correction blocks**, which govern where the body and they
disagree. Phase HP, cycle 1. Revised 2026-09-09 after review.

Default tier throughout: **no model, no network, no subprocess.** Every slice
is test-first, and every refusal lands with the sibling success that proves
it can pass, each check working in both directions (`BRIEF.md` invariants 1
and 5). Commits are the maintainer's; this plan creates none.

## Slice order, and why

1. **The packet type** — the data contract, standalone.
2. **`facts` and `self_test_command` in the session spec** — the only
   task-contract change.
3. **Building a packet from a step** — the deterministic builder.
4. **Rendering, and the gates over it** — the refusals that matter.
5. **The golden packet** — byte-for-byte, once the shape is settled.

Slice 2 is deliberately not first. Adding a key to a task file before
anything consumes it is how a field gets declared and never applied, which is
the defect the spec refuses in the `sampling` case.

## Slice 1 — the packet type

**Files:** new `src/satyrn_evals/packet.py`; `src/satyrn_evals/errors.py`;
new `tests/test_packet.py`.

`HandoffPacket` as a frozen slotted dataclass carrying the spec's eleven
fields. **No `validation_command`** — see the spec's correction. `type
PacketRole = Literal["implement"]`, one member, because that is how many
roles this path has.

`type PacketCommand = tuple[str, ...] | None`, where `None` means *the task
offers none* and `()` is refused as malformed. The manifest uses `()` for
absence (`manifest.py:31,50`); this type deliberately differs because the
packet must distinguish "no command exists" from "an empty command", and the
plan says so rather than claiming to match a convention it does not.

`PacketError(UsageError)` joins `errors.py` beside `SessionSpecError`.

**Tests, each refusal with its sibling.** Empty objective refused, non-empty
accepted. Unknown version refused, version 1 accepted. A command as a bare
string refused, a tuple accepted. An empty-tuple command refused, `None`
accepted. Empty `facts` is **not** refused here — that rule belongs to the
builder, and stating it in one place is what keeps the two from drifting.

**Done when** the type refuses each malformed shape by its own error and
accepts the well-formed sibling, with no I/O in the module.

## Slice 2 — `facts` and `self_test_command` in the session spec

**Files:** `src/satyrn_evals/session_manifest.py`; the phased task's
`session.json` and `session-control.json`;
`tests/test_session_manifest.py`; `tests/test_agentclinic_session_phased.py`.

Add `facts` to `_STEP_KEYS` (`session_manifest.py:22`) and to `SessionStep`,
as `tuple[str, ...]` defaulting to empty. Add `self_test_command` to `_KEYS`
as a spec-level optional list of tokens. The exact-key comparison at
`session_manifest.py:44` stays exact, so a misspelled `fact` is still
refused.

Author the facts for the three steps: pinned decisions drawn from text
already in the prompts — the framework, the template engine, the dependency
policy. **They introduce no new requirement.**

**The divergence test must cover the new key.**
`tests/test_agentclinic_session_phased.py:292-297` compares `kind`,
`new_feature_selectors` and `prompt` only. After this slice the two
conditions could carry different facts with that test still green, and the
screen's validity rests on it. Add `assert c["facts"] == r["facts"]`, plus
the spec-level `self_test_command`.

**The digest test.** Compute `session.py`'s digest over each step of both
spec files and assert the six values recorded at
`docs/current/agentclinic-verification-triage-screen.md:33-35`. This is the
check that can fail if `facts` ever reaches a prompt.

> **Removed after review.** An earlier version of this slice proposed a
> "prompt invariance" test comparing prompts built with and without facts.
> `session.py:396` sends `spec_step.prompt` verbatim, so no such builder
> exists and the test was a tautology. The digest test replaces it.

**Also tested:** a spec with neither new key still loads.

**Done when** the existing character-exact condition test still passes
untouched, the divergence test covers facts, the digest test passes, and the
task's steps carry facts.

**Recorded on landing:** the spec file digests **and the task tree hash** at
`docs/current/agentclinic-verification-triage-screen.md:32,62` become
historical. Write that into the screen record as a correction; do not edit
the digests.

## Slice 3 — building a packet from a step

**Files:** `src/satyrn_evals/packet.py`; `tests/test_packet_build.py`.

`build_packet(task_dir, manifest, spec, step_id, base_revision, *, budgets)`
returns one `HandoffPacket`. **Deterministic, not pure**: no clock, no
randomness, no environment read, so slice 5's golden packet is reproducible —
but `writable_paths` probes `base/` on disk, so the result depends on the task
tree too. *(Corrected after review; "pure function of its inputs" was wrong.)*

Mapping:

- `objective` from the step's prompt; `facts` from slice 2, **refused when
  empty**.
- `writable_paths` from `engine_contract.writable_paths(task_dir,
  manifest.source_paths)` (`engine_contract.py:32-46`), reused rather than
  reimplemented. Its fnmatch semantics differ from the session route's
  prefix matching (`patch.within_source`, `patch.py:166-178`); that gap is
  HP4's, and this slice inherits it unchanged rather than half-fixing it. A
  test **records** the disagreement rather than asserting it away.
- `self_test_command` from slice 2's spec key.
- `preserve` as prose: the objectives of every earlier step, restated.
- `redacts` seeded from **every** step's `new_feature_selectors` and the
  grader overlay directory name. *(Widened during implementation from "the
  step's". A packet for phase 1 must not leak phase 3's hidden checks either,
  and a later phase's selectors are what a forward-looking implementer might
  guess at.)*
- `base_revision`, budgets and `role` from explicit arguments. `base_revision`
  is refused when empty; for a materialized `base/` with no commit it carries
  the task tree hash, which is what the screen record already pins.

**Tests.** The same call twice gives an identical packet. Phase 2's packet
carries phase 1's objective in `preserve`; phase 1's carries none. `preserve`
holds no `::` and is clean under `scan_texts`, with a planted-selector
sibling. A step with empty facts is refused; the real step builds. An unknown
`step_id` is refused.

**Done when** the builder is deterministic and every mapping is asserted from
the real phased task, not a synthetic fixture.

## Slice 4 — rendering, and the gates over it

**Files:** `src/satyrn_evals/packet.py`; `tests/test_packet_render.py`.

`render_packet(packet) -> str` emits exactly the five fields the spec
enumerates and **never `redacts`**.
`assert_redactions_absent(packet)` refuses when any `redacts` string appears
in that text, **and refuses blank text**, since a renderer returning nothing
would otherwise pass silently.

> **Corrected during implementation.** This slice was written believing
> `scan_texts` matched arbitrary strings, and said the gate would reuse it
> "rather than a second matcher". It matches the overlay's own relative paths
> only (`contamination.py:211-247`). There are two gates with different jobs:
> the redaction gate compares the packet's declared strings, and
> `assert_overlay_absent_from_packet` runs `scan_texts` and refuses `flagged`
> and `unmeasured` alike.

**Tests, both directions.**

- **Positive rendering, per field.** Each of the five rendered fields has its
  **section** present in the output, asserted individually. *(Review found a
  first version that could not fail for `writable_paths` or
  `self_test_command`: every token of both already appears inside the
  objective prompt, so bare substring containment was satisfied by the wrong
  field. The check is on `## <field>` plus each entry's own rendered line.)*
- **Contamination, parametrized over every rendered field.** A selector
  planted into each in turn is refused; the same packet without it is
  accepted. *(Review finding: the first version planted only into
  `preserve`, so a renderer omitting the other four passed.)*
- **The planted string is really there.** The fixture is asserted to contain
  what it plants, so the gate cannot pass by finding nothing.
- **Empty render refused**, exercising the `unmeasured` path directly.
- `redacts` values do not appear in the rendered text even though they are
  packet fields.

**Done when** no gate can pass on a no-op renderer, demonstrated by a test
that a stub returning `""` fails at least one check in each direction.

## Slice 5 — the golden packet

**Files:** `tests/data/hp1-golden-packet.json`;
`tests/test_packet_golden.py`.

One packet from `phase-2-board`, serialized with sorted keys, asserted
byte-for-byte. Regenerating it is a visible diff in review.

**Done when** the golden file round-trips and refuses an unknown version.

## Out of scope for HP1

Executing a packet, isolation, file creation, attribution, retention. The
declared-versus-enforced scope mismatch, which is HP4's. Autonomous packet
authoring. `sampling`; `baselines` before HP3; a second `PacketRole` member.
Any change to `session.json`'s existing keys, or to the graders.

## Verification

`just gates`, exit code read directly and never piped. Focused tests during
each slice; the full gates once at the end of the cycle.
