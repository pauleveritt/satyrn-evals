# V5c — Capture the admitted suite: design spec

**Phase:** V5c (`ROADMAP.md`). **Date:** 2026-09-02.
**Status:** proposal confirmed by the maintainer 2026-09-02; spec written
before implementation per `docs/sdd.md`.

## What V5c ships

V5c reconstructs and captures one task, `local-pings`, so V5b's diagnostic
loop has a real admitted target on this machine. It adds no CLI, no exit
codes, and no schema: the deliverable is a captured task directory matching
the bundled `format_number` shape, gated on re-recording the corrected
probe's three-row qualification table exactly. No model runs; the loop
itself is the next step, not this phase.

## The problem

V5a admitted `local-pings` and `stringified-annotations` on probe records
made on another machine
(`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md:119-120`),
but neither task is captured here. The authoring area holds only `repo/` +
`brief.md` per task — no `manifest.json`, no `base/`, no `fixtures/`. The
only `manifest.json` on this machine is the bundled `format_number`. V5b's
`run` therefore has no admitted target — the same evidence gap V5a used to
refuse `magicmock-factory`
(`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md:206`, `:210`).

## Why this is not "just run V2 capture"

`capture --revert SHA` needs a Git repository containing a fixing commit.
The packet's `repo/` is a flat 85-file snapshot with no `.git`, and its
recorded `base_sha` (`31bc6dfd`) is the *upstream* base, not the corrected
synthetic pair the probe actually used:

```text
upstream base:        31bc6dfd5d1a570b3b96cfefd878ccc686bde980
upstream target:      52c6689d34ce80c0f5a754f95d2aad54837402df
corrected task base:  9261f41efc99732204919cad5432de9085d6a70c
corrected task fix:   0055ea7b3fbee0fd0438be6cf7d0e561c230652e
```
(`2026-08-27-local-pings-corrected-probe.md:56-59`)

The corrected pair must be rebuilt: the base carries the upstream target's
test changes plus the curator-authored preservation test; the fix applies
the upstream target's source change. Upstream is the public `hynek/svcs`,
so both upstream SHAs are fetchable.

## Scope

Reconstruct and capture `local-pings` only. `stringified-annotations` is
deferred — its Engine arm is pinned at ceiling (6/6,
`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md:78`), which
is regression detection, not headroom; it reopens once the loop has run on
a task that can move.

## CLI surface

None added. V5c uses V2's
`capture --revert SHA [--repo DIR] [--name NAME] [--contract TEXT] [--output DIR]`
as it stands. A discovered need for a new flag is a stop-and-re-propose
signal, not a mid-phase addition — no machinery ahead of the contract it
serves (`BRIEF.md:62`).

## Exit codes

None added. `capture`'s existing codes stand unchanged.

## Data shapes

No schema change. One new captured task directory matching the bundled
`format_number` shape exactly (`src/satyrn_evals/tasks/format_number/`):

```text
manifest.json   name, contract, oracle, expected_test_ids,
                source_paths, engine_contract, fixtures{known_good, known_broken}
base/           the task's starting tree
fixtures/       known-good.patch, known-broken.patch
engine-contract.yaml
```

`expected_test_ids` carries the corrected four-test oracle, including the
curator preservation test:

```text
tests/test_eval_preservation.py::test_local_ping_keeps_registry_ping_order
```
(`2026-08-27-local-pings-corrected-probe.md:37`)

## Test layout

**Default tier** (no model, no network, no subprocess; planted tripwire
untouched):

- `grade` accepts the captured known-good patch and rejects the
  known-broken one — the V1 property, now on a real task — as a refusal
  test with its sibling success test (`BRIEF.md:84-85`).
- A manifest-shape test asserts `expected_test_ids` matches the oracle the
  probe records.

**Integration tier** (marked `integration`, deselected from CI):

- The capture reproduction itself: real Git, fetch upstream, build the
  synthetic pair, run `capture`.

## The qualification gate

Re-record the corrected probe's qualification table against the newly
captured task (`2026-08-27-local-pings-corrected-probe.md:62-68`):

| Input | Corrected oracle |
| --- | ---: |
| base | 0 pass, 4 fail |
| upstream known-good patch | 4 pass |
| previously accepted set-union patch | 3 pass, 1 fail |

**If all three rows do not reproduce, the capture is wrong and the phase
stops.** This is the mechanical guard against silently recapturing a weaker
oracle — the exact defect that invalidated the first probe
(`2026-08-27-local-pings-corrected-probe.md:32-34`): the prior three-test
oracle accepted a patch that combined registry and local service types in a
`set`, losing insertion order. Row 3 is the row that catches it.

## Risks

1. **Reconstruction, not transcription.** The recorded failure mode is the
   order-losing set patch; the qualification table is the guard.
2. **Environment-dependent determinism.** The probe states that, in the
   frozen Python 3.14 environment, "controlled class hashes make the
   previously accepted set-union patch fail deterministically"
   (`2026-08-27-local-pings-corrected-probe.md:42-44`). If this environment
   differs, row 3 may not reproduce. That is a stop-and-record condition —
   **not** something to tune until it passes.

## Out of scope (deferred, with what reopens each)

- **`stringified-annotations` capture.** *Reopens once the loop has run on
  `local-pings`.*
- **`magicmock-factory`.** Unadmitted per V5a; needs an arm under
  comparison. *Reopens with an Envelope/Engine probe.*
- **Any oracle improvement.** The test couples to the private `_svc_type`
  field; a future candidate should observe public names or callable
  execution order instead (`2026-08-27-local-pings-corrected-probe.md:46-49`).
  Changing it changes what is measured and voids comparison with the
  recorded probes. *Reopens as its own proposal.*
- **Running the loop.** The step after this phase, not part of it.
- **Suite-with-headroom capture** (`BRIEF.md`'s unsolved problem).
  *Reopens with the suite search.*

## Done-when

- `local-pings` exists as a captured task with the `format_number` shape.
- The three-row qualification table reproduces exactly, recorded with the
  command that recomputes it.
- The default tier proves `grade` accepts known-good and rejects
  known-broken, with the sibling pair.
- `satyrn-evals run local-pings --n 8 -- COMMAND...` is *executable*
  (execution itself is the next step, not this phase's done-when).
