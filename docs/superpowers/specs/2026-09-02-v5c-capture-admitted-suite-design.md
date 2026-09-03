# V5c — Capture the admitted suite: design spec

**Phase:** V5c (`ROADMAP.md`). **Date:** 2026-09-02.
**Status:** proposal confirmed by the maintainer 2026-09-02; spec written
before implementation per `docs/sdd.md`.

> **Amendment (2026-09-02, maintainer-confirmed).** Row 3's adversary is
> re-specified — the recorded N=2 type-set does not reproduce on this
> machine (`docs/superpowers/research/2026-09-02-v5c-local-pings-capture-reconstruction.md`),
> and the cross-machine investigation shows the catch is a discrete function
> of hash stride versus table geometry and allocation phase, not a
> stateable probability (see the cross-machine research record). The
> sections this amendment supersedes are marked below; the original text is
> kept, not edited away.
>
> **Row 3's adversary.** The type-set at **six** registry-only services
> (`Service`, `AnotherService` from `tests/ifaces.py`, plus four classes
> defined in the curator module), documented as a **re-specification**, not a
> reproduction. N=6 lands on the scramble face in every context measured
> (this machine's pytest gate, bare contexts on 3.14.2 and 3.14.7, and the
> reviewer's machine), unlike N=2 (preserve face here; dead on both
> machines) and N=8 (flips between machines). The object-set substitution is
> dropped: N=6 keeps the recorded defect kind — a set of service *types*,
> per the probe's prose — and only scales the fixture. Whether the probe's
> model actually wrote a type-set or an object-set is settled only by the
> evidence archive on the other machine, which this phase did not have;
> that is recorded, not resolved here.
>
> **The curator test** registers six registry services in a known order plus
> one local ping, parametrized over forward and reversed registration order
> (node ids `[order0]`/`[order1]`): a single iteration order cannot match
> both, so at least one case fails whenever the environment scrambles.
>
> **`expected_test_ids`** is the **five** ids: the three upstream
> local-ping tests plus the two curator parametrizations
> (`[order0]`, `[order1]`).
>
> **The canary.** The curator module carries a third test,
> `test_environment_scrambles_registry_type_set`, which is **not** part of
> `expected_test_ids`. It mirrors the adversary's exact mechanism — it
> compares `list(set(registry._services) - local_svc_types)` against
> `list(registry._services)`, never the raw source set, because set
> subtraction rebuilds the table — and it runs in the same process and
> context as row 3. The gate has **three outcomes, not two**: pass, fail,
> and **inconclusive**. Inconclusive is when the canary reads the preserve
> face (the type-set is then undetectable by any order comparison, and a
> silent pass is the exact silent-zero shape this repository has four
> recorded incidents of). **Inconclusive stops capture and is never a pass.**
>
> **Test-tier correction.** The V1-property grade tests (`grade` accepts the
> known-good patch and rejects the known-broken one) spawn Git and pytest
> and therefore belong to the **integration** tier, mirroring
> `tests/integration/test_bundled.py`; the default tier cannot run them (the
> audit-hook tripwire blocks spawning, `tests/conftest.py:17-23`). The
> manifest-shape test is default tier.
>
> **Environment.** Grading and capture run the oracle with the invoking
> Python, so that environment needs svcs's test dependencies (attrs, sybil,
> pytest-asyncio). The synthetic base's `pyproject.toml` gains
> `pythonpath = ["src"]` under `[tool.pytest.ini_options]` — a
> test-runner-only deviation so uninstalled tree copies can run, since the
> grade machinery copies `base/` and does not install.
>
> First-look gate results at N=6 (this machine; see the re-recorded
> qualification table in the reconstruction record for the full run):
> base 0/5; known-good 5/5; type-set 3 pass / 2 fail in 20/20 fresh
> processes; canary ok 20/20.

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

> **Superseded by the Amendment above**: the oracle is five ids — three
> upstream local-ping tests plus `[order0]`/`[order1]`. The single curator
> node id below is the pre-amendment form.

```text
tests/test_eval_preservation.py::test_local_ping_keeps_registry_ping_order
```
(`2026-08-27-local-pings-corrected-probe.md:37`)

## Test layout

**Default tier** (no model, no network, no subprocess; planted tripwire
untouched):

> **Superseded by the Amendment above**: the grade accept/reject tests are
> integration tier (they spawn Git and pytest). The default tier holds the
> manifest-shape test only.

- ~~`grade` accepts the captured known-good patch and rejects the
  known-broken one — the V1 property, now on a real task — as a refusal
  test with its sibling success test (`BRIEF.md:84-85`).~~
- A manifest-shape test asserts `expected_test_ids` matches the oracle the
  probe records.

**Integration tier** (marked `integration`, deselected from CI):

- The capture reproduction itself: real Git, fetch upstream, build the
  synthetic pair, run `capture`.
- The V1-property evidence floor on the captured task: `grade` accepts the
  known-good patch and rejects the known-broken one, asserted by name
  (mirrors `tests/integration/test_bundled.py`; requires svcs test
  dependencies in the runtime environment).

## The qualification gate

> **Superseded by the Amendment above.** The gate is re-recorded at N=6 with
> a canary verdict reported alongside each row; the gate has three outcomes
> (pass, fail, inconclusive) and inconclusive stops capture. The table below
> is the pre-amendment form (four-test oracle at the recorded N=2 fixture).

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
   order-losing set patch; the qualification table is the guard. Row 3 is
   now a re-specification (N=6 type-set), per the Amendment.
2. **Environment-dependent determinism.** The probe states that, in the
   frozen Python 3.14 environment, "controlled class hashes make the
   previously accepted set-union patch fail deterministically"
   (`2026-08-27-local-pings-corrected-probe.md:42-44`). This environment
   differed, row 3 did not reproduce at the recorded size, and the cause is
   now recorded (hash stride vs table geometry and allocation phase — the
   probe's "controlled class hashes" cannot have meant hash seeding, which
   does not move `id()`-based residues). The canary converts any residual
   preserve-face environment into an **inconclusive** stop rather than a
   silent pass.

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
- The three-row qualification table is re-recorded at the N=6 fixture
  across ≥20 fresh processes with the canary verdict reported alongside,
  recorded with the command that recomputes it; no row is inconclusive
  (the canary must read the scramble face in every run).
- The integration tier proves `grade` accepts known-good and rejects
  known-broken, with the sibling pair, and the default tier proves the
  manifest shape (five ids).
- `satyrn-evals run local-pings --n 8 -- COMMAND...` is *executable*
  (execution itself is the next step, not this phase's done-when).
