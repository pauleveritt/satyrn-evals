> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V5c cross-machine finding: the set-order qualification gate is environment-discrete, not portable-in-principle

**Date:** 2026-09-02. **Status:** recorded; drove the V5c adversary
decision (spec amendment). Scratch evidence lives in the durable scratch
`~/projects/pauleveritt/satyrn-v5c-scratch/` (`exp/RESULTS.md`, harnesses);
this file is the repository-side record.

## Symptom

Row 3 of the V5c qualification table — the recorded adversary, a
`get_pings` that combines service types in a `set` — did not reproduce on
this machine at the recorded fixture size
([`2026-09-02-v5c-local-pings-capture-reconstruction.md`](2026-09-02-v5c-local-pings-capture-reconstruction.md),
commit `548e019`). An independent reviewer then measured the *opposite* of
the first N=8 measurement on their machine. Both tables were faithful; the
quantities genuinely differ between machines and between harness shapes on
the same machine.

## The two measurements, both faithful

This machine (Python 3.14.2, macOS): the type-set preserves insertion order
20/20 in the real pytest gate context at N=8 (raw per-run order verified),
and scrambles 20/20 at N=5 and N=6. Bare `python -c` harnesses on the same
interpreter scramble N=8 20/20 — same code, same classes, different
allocation context. The reviewer's machine (3.14.7): N=8 scrambles 20/20
and is robust to 0/100/5000 pre-allocated objects; N=2–4 are partial. Both
sides' N=5 and N=6 scramble 20/20 in every context measured (this machine's
pytest gate, bare contexts on 3.14.2 and 3.14.7, and the reviewer's
machine).

## Geometry and mechanism (corrected)

- `hash(cls) == id >> 4` for classes (no per-object hash randomization).
  Sequential classes allocate at a ~1024-byte id stride, so hash stride is
  64 and every measured class shares one residue class mod the set-table
  size (e.g. 1 mod 32).
- Set table sizing: `sys.getsizeof` is 216 bytes (embedded 8-slot
  smalltable) for N=2–4 and 728 bytes (32 slots) for N=5–10. **CPython 3.14
  resizes 8 → 32 at N=5.** An earlier draft of this finding claimed a
  16-slot table at N=8; that was an unmeasured inference and is wrong — no
  16-slot table exists at these sizes.
- With all first-probe residues equal, iteration order is decided by
  CPython's perturbed probing, which depends on the classes' **absolute
  addresses** — their allocation phase inside the process (import graph,
  build, arena layout). Each harness context has a fixed phase and is
  internally deterministic (20/20 either way, robust to object churn), but
  the same N can deterministically preserve order in one context and
  deterministically scramble it in another. N=8 sits on that knife edge;
  N=5 and N=6 land on the scramble face in every context observed.
- The outcome is therefore a **discrete function** of hash stride versus
  table geometry and allocation phase — not a residual probability that
  shrinks smoothly with N. No stateable residual exists.
- **Hash seeding is irrelevant.** `PYTHONHASHSEED` 0/1/42/random leaves
  class hash residues unchanged (verified). The corrected probe's phrase
  "controlled class hashes"
  ([`2026-08-27-local-pings-corrected-probe.md`](2026-08-27-local-pings-corrected-probe.md):42-44)
  therefore cannot have meant hash seeding; the frozen environment must
  have controlled allocation layout. A later reader should not chase
  `PYTHONHASHSEED`.

## The canary and its trap

The gate gained a canary that must run in the same process and context as
row 3 and must mirror the adversary's exact mechanism. Prototyping exposed
a false-instrument shape: a canary that compared the raw source set
(`set(registry._services)`) against registry order read "preserve face" at
N=6 while the curator test was catching the adversary 20/20 — because the
defective `get_pings` iterates `set(registry._services) - local_svc_types`,
and **set subtraction rebuilds the table**, so the subtraction result's
iteration order can differ from the raw source set's. The canary must
compare `list(set(registry._services) - local_svc_types)` against
`list(registry._services)`. (Lessons entry: "the canary read the wrong
set".)

## Decision recorded

Row 3's adversary is re-specified as the type-set at six registry-only
services, with the two-order parametrization and the canary
(`docs/superpowers/specs/2026-09-02-v5c-capture-admitted-suite-design.md`,
amendment). The object-set substitution was dropped — N=6 keeps the
recorded defect kind and only scales the fixture. Whether the probe's model
actually wrote a type-set or an object-set is settled only by the evidence
archive on the other machine, which this phase did not have. The recorded
N=2 fixture does not survive on either machine's evidence.

**Admission caveat.** The `local-pings` arm numbers recorded by the probes
and the V5a admission index (Baseline 0/4, Envelope 0/4, Engine 2/4;
retained-patch 2/2) were graded under the superseded four-test oracle at
the N=2 fixture. The captured task's oracle is now five ids at N=6, so
those numbers are **unearned pending a re-probe** against the captured
task. The V5a structural decision (which arms separate) is not reopened by
this note; the numbers are.
