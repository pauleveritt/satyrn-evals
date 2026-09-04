# V8 — AgentClinic through Evals: design spec

**Status: design of record for V8 (branch `v8-agentclinic`).** Written
2026-09-04 after a four-decision brainstorm (maintainer, same day): scope B
(offline qualification plus one uncounted smoke), the `swiftstar` companion
repository as the fixture input, six hand-authored bundled tasks with the full
13-test hidden oracle, and the task's own base project as the environment of
record. Each decision and its correction is recorded in the section that uses
it.

## Relationship to what is on main

Main's tip at writing is `2bb452b` (docs: backlog the deferred cumulative-suite
capture decision). V7's post-merge review (Sol) remediation is on main ahead of
this branch's point of origin: attempt records carry their own `attempt_dir`
and `run` no longer infers cell identity from an output-directory delta
(`09cc041`), the 100 % coverage gate is restored (`5e80dec`), and the V7
verification record plus spec close-out amendment are committed (`1863141`;
`ROADMAP.md`'s V7 status cell cites both without reopening the phase,
`d82398e`). V8 builds on that tree.

## 1. Direction, and the evidence behind it

The roadmap row (`ROADMAP.md:96`):

> **V8 — AgentClinic through Evals:** reproduce the repair fixtures on this
> repository's own `capture`/`attempt`/`grade` path, replacing the spike's
> scratchpad harness. Excludes: engine changes, including a `facts` field
> (satyrn-engine `BACKLOG.md`); an orchestrator.

The maintainer-review sequence that placed V8 where it is
(`2026-09-02-phase-proposals-and-session-eval-convergence.md` §5): land PR #17
→ repair instrument semantics → containment decision → **reproduce AgentClinic
through Evals** → then test engine facts. V6 (session eval) and V7 (task
visibility and leak detection) landed the first three; V8 is the reproduce
step, and engine `facts` is explicitly after it, never inside it.

**Why repair fixtures, and why re-derive on this path.** The overnight run
found the AgentClinic repair fixtures were the only workload measured whose
distribution moves, while everything else floored or ceilinged
(`2026-09-02-overnight-packet-and-isolation-run.md` §5). That claim was earned
through a purpose-built scratchpad harness whose numbers "must be re-derived
before they are cited in a plan" (ibid. §7), and whose instrument carried four
recorded defects of one class plus an environment confound — the grader lived
on reachable disk (models read it), the oracle ran in an environment different
from the model's (six false passes, spike Correction 4), and the `factonly`
arm's advantage shared a single cause with its protection (unequal exposure to
a broken test runner). V8 replaces that instrument with this repository's own
path, where the grader is never in the attempt workspace (V6 overlay) and the
task owns its environment (below).

**Scope decision (B), recorded.** V8 offline-qualifies the dependency-bearing
hidden-oracle path deterministically and runs one durable, uncounted smoke.
The budgeted admission probe is **not** part of V8; it is a separately
confirmed, preregistered measurement proposal whose reopen condition is
recorded in `BACKLOG.md` (the "AgentClinic repair admission probe" entry,
committed 2026-09-04).

**Input decision, recorded.** The fixture set is `swiftstar`'s
`fixtures/agenttest/` (`github.com/pauleveritt/swiftstar`, local clone at
`~/projects/pauleveritt/swiftstar`), whose `PROVENANCE.md` names its
`local-ai-pi` source commits (`8af05f8`, `191895e`), records that `repair/`
was authored there (2026-08-24), and pins the dependency versions. Availability,
provenance, and publication rights were confirmed before use; `swiftstar` is
MIT (c) 2026 Paul Everitt, so vendoring with the notice retained is explicit.
The spike evidence archive
(`~/work/satyrn/evidence/2026-09-02-agentclinic-spike.tar.gz`) is **evidence
only** — unsanitized, never a source of publishable task contents. Re-derived
or relicensed equivalents would be a different input decision and are not
silently substituted for the canonical six fixtures.

## 2. The six tasks: packaging and data shapes

Six bundled tasks under `src/satyrn_evals/tasks/`, one per seeded repair
state, named `agentclinic-repair-{depth-2, depth-3, framing-2,
framing-2-edit, misleading-locus, plausible-wrong-fix}`. Each task directory
is self-contained:

```text
agentclinic-repair-<state>/
  manifest.json
  base/                  # the reconstructed broken app (see below)
    pyproject.toml       # authored; runtime pins + locked dev group
    uv.lock              # committed
    app.py  models.py  templates/{home,base,complaints}.html   # per state
  overlay/               # grader-only: the vendored 13-test acceptance suite
    test_acceptance.py
  fixtures/
    known-good.patch     # the reference fix delta (state -> reference)
    known-broken.patch   # an authored plausible-wrong repair
  LICENSE                # the swiftstar MIT notice
  PROVENANCE             # swiftstar commit, state, reconstruction rule, pins
```

**Base reconstruction rule.** The swiftstar repair directories are sparse
deltas, not trees: `repair/framing-2/` holds `app.py` plus a `.delete` marker
naming `models.py` (a vendoring representation of deletion); `depth-3/` holds
`models.py`, `app.py`, `templates/base.html`; other states hold only `app.py`
(verified by directory listing at writing). Each `base/` is therefore the
reference app tree (`reference/app.py`, `reference/models.py`,
`reference/templates/{home,base,complaints}.html`) with the state's deltas
applied: file overrides replace the reference file, state-only files are
added, and each `.delete`-named reference file is omitted. The reconstruction
is deterministic and documented per task in that task's `PROVENANCE`, then
**verified, not asserted**: each base must reproduce its recorded 12/13
signature on the suite, with the one seeded failing test id named per state
(§6). `reference/tests/` (a four-test solution artifact) is **not** vendored:
no public tests ship in `base/` (decision, §11).

**Manifest fields.** No schema change. `oracle_visibility: "hidden"`;
`grader_overlay: "overlay"`; `oracle` is the pytest invocation running the
oracle hook with all thirteen test ids; `expected_test_ids` is the same
thirteen ids. The `contract` is the repair prompt (§4). `source_paths` lists
the per-state repairable app files — derived from each state's fix delta
during reconstruction, never lockfiles or `pyproject.toml` (decision, §11).
`fixtures` names `known_good`/`known_broken`. `provenance` names the swiftstar
commit, the state, the reconstruction rule, and the pins.

**Overlay duplication, decided.** The acceptance suite is byte-identical
across all six tasks, and the overlay validator is task-dir-scoped
(`src/satyrn_evals/manifest.py:32-57`). Six self-contained copies ship —
accepted duplication, no schema change, each task independently reproducible.
The suite stays harness-owned grader content: it is never named in a contract,
never present in an attempt workspace, and graded only from the overlay.

## 3. The environment: provenance and materialization

**The task is a real project.** Each `base/` carries an authored
`pyproject.toml` declaring the app's pinned runtime dependencies —
`fastapi[standard]==0.115.10`, `turbohtml==1.5.0`, `httpx` (the `PROVENANCE.md`
pins) — and a committed `uv.lock`. `pytest==8.3.4` lives in a **locked
test/dev dependency group** of that same project, so grade materializes one
deterministic project environment; there is no `--with` convention
(maintainer clarification, approved). Each task is independently reproducible
and usable by the engine's runner, a bare model, or a human: `uv sync --locked`
in `base/` is the whole environment story.

**Grade-side change — the only production-code change in V8.** When the
graded tree is dependency-bearing (its `base/` carries `pyproject.toml` and
`uv.lock`), `grade` materializes that project's locked environment into a
relocated project env at a scratch path outside the graded tree
(`UV_PROJECT_ENVIRONMENT`), runs the oracle inside it, and writes the
attestation below. Stdlib/vendored tasks — every bundled task that predates
V8 — are untouched: no project files, ambient python exactly as today, no new
receipt field, byte-compatible receipts.

**The oracle hook import.** The oracle command runs `python -m pytest -p
satyrn_evals.oracle_hook …`. In the materialized env the package is not
installed, so grade prepends a controlled `PYTHONPATH` naming the evals
package source; nothing else from the evals environment leaks into the oracle
env. Oracle runs also set `PYTHONDONTWRITEBYTECODE=1`, carrying forward the V6
session-runtime lesson that stray bytecode pollutes captured trees.

**`resolved_versions`, attested not inferred.** The receipt field
`resolved_versions: dict[str, str] | None` (see §9) is populated from the
**materialized environment's installed distributions** — the full `uv pip
freeze` of the env grade actually executed, every installed distribution —
not by parsing `uv.lock` (maintainer correction, approved: the receipt
attests to what grade ran, and a lock is a promise while a freeze is a
record). It is omitted for ambient/stdlib grading.

## 4. Contracts: the repair prompt

Each contract is a repair work order: the task statement plus that fixture's
**verified failure output** — the seeded bug's real traceback as produced by
running the suite against the vendored `base/`. The failure output is
**re-derived during implementation**, never copied unchecked from the
companion repository: BRIEF rule 7 ("cite, don't recall") requires the text a
model sees to match the text this repository's own grade produces.

The confounded "ownership sentence" from the overnight run (`factonly`) is
**not** in the contract. It is a measured prompt-arm variable whose advantage
and protection shared one cause (`2026-09-02-overnight-packet-and-isolation-
run.md`, the exposure correction); on this path the grader is structurally
unreachable from the attempt workspace (V6/V7 overlay), so the isolation that
sentence once bought is designed in, and the wording belongs to the deferred
probe, not to the qualified fixture.

## 5. Contamination evidence, both directions, per task

V7's rule-8 discipline (`BRIEF.md`, binding rule 8) applies to each new
overlay: a known-bad drawn from the task's own batch must fire the detector,
and a known-good from the same batch must stay silent. Per task, following the
V7 `test_contamination.py` trio's shape: a patch embedding five non-blank
lines of that task's own overlay flags with evidence naming the overlay file;
the task's `fixtures/known-good.patch` stays clean; a same-behavior,
different-bytes restatement never fires. These are integration-tier tests (a
real grade is a subprocess), and they reuse the overlay bytes, so the detector
is exercised against the actual shipped content of each of the six tasks.

## 6. The offline qualification gate

Deterministic, no model, asserted by fixture name (BRIEF rule 2 and rule 8),
per task:

| row | input | expectation |
|---|---|---|
| base | broken state, no patch | verdict fails; the state's recorded 12/13 signature with the one seeded failing test id named |
| known-good | `fixtures/known-good.patch` (reference fix delta) | verdict passes, 13/13 |
| known-broken | `fixtures/known-broken.patch` (plausible-wrong repair) | verdict fails, failing id(s) named |

The seeded failing id and the base signature are re-derived on the vendored
task (§4's rule applies to the gate too). The gate runs as integration-tier
tests plus a documented, recomputable gate command (the V5c three-row-gate
precedent; the command is recorded in §14 and, at close-out, in the `docs/sdd.md`
verification record).

## 7. The smoke

One real-model attempt through the qualified path — a dependency-bearing
hidden-oracle single-shot attempt — on **`framing-2`** (the smallest repair
surface: a single-file fix), after every offline row of all six tasks is
green. It is the V5d practice applied to this materially distinct path:
uncounted, durable, uniquely named evidence; the attempt record read always
and the receipt only when grading ran; `NO_PATCH`/`COMMAND_TIMEOUT` pass only
on positive evidence the model started; no admission, difficulty, or quality
claim. Model: local only, per the V6 smoke precedent. The attempt command is
the product seam — the stock engine's attempt against the base project — so
the smoke exercises the path V8 qualifies rather than a test double; an engine
defect surfaced by the smoke is recorded, not fixed here (engine changes are
excluded).

## 8. CLI surface and exit codes

Unchanged. V8 adds no commands and changes no exit code: the phase qualifies
bundled tasks and records evidence through the existing `grade`, `attempt`,
and `run` surfaces. (This section states the CLAUDE.md design-proposal
requirement explicitly: no surface change is intended.)

## 9. Data shapes

- `TaskManifest`: unchanged schema; new values only (`manifest.py:19-30`).
- `Receipt`: gains `resolved_versions: dict[str, str] | None = None`
  (`receipt.py:11-18`), written only when grading materialized an environment,
  None-popped exactly like `contamination`. Field name fixed by the
  maintainer: it names the contents.
- No new record files; `attempt.json`, the receipt, and the run summary are
  unchanged in shape except the receipt field above. `resolved_versions` is
  the full `uv pip freeze` of the materialized oracle env — every installed
  distribution, keyed by normalized package name → exact version — so the
  attestation is complete and needs no judgment about "relevance".

## 10. Non-goals

- **The budgeted admission probe** (scope C): a separately confirmed,
  preregistered measurement proposal, not this phase.
- **Engine changes**, including the `facts` field (satyrn-engine `BACKLOG.md`).
- **An orchestrator** (remains unjustified).
- **Capture changes**: cumulative-suite capture is deferred to `BACKLOG.md`
  with its reopen condition (committed `2bb452b`).
- **OS-level containment** (deferred; V7 detects rather than prevents).
- **Public tests in `base/`**, or any `run`/summary change, new CLI, or new
  exit code.

## 11. Recorded decisions (maintainer, 2026-09-04)

1. Scope **B**: offline qualification of the dependency-bearing hidden-oracle
   path; one durable uncounted smoke after qualification. The probe (C) is a
   separate preregistered proposal.
2. Input: the `swiftstar` companion repository, after availability,
   provenance, and license were confirmed; the evidence archive is not a
   content source; no silent substitution of re-derived equivalents.
3. **A**: hand-authored bundled tasks with the full 13-test hidden oracle;
   capture is not exercised; the cumulative-capture decision is backlogged
   with its reopen condition.
4. Environment **A**: the definition lives with the task's base project
   (`pyproject.toml` + committed `uv.lock`, `pytest==8.3.4` in a locked dev
   group); grading materializes that locked environment; `resolved_versions`
   is attested from the materialized environment's installed distributions;
   the oracle subprocess imports `satyrn_evals.oracle_hook` via a controlled
   `PYTHONPATH`.
5. Six self-contained copies of the hidden overlay; `source_paths` limited to
   repairable app files derived per state; no public tests in `base/`.
6. The receipt field is named `resolved_versions` and is omitted for
   ambient/stdlib grading.

## 12. Reviewable slices

Proposed implementation order (the plan decomposes and sequences these):
1. Vendoring and reconstruction: the six `base/` trees + authored projects,
   licenses, provenance; reconstruction verification per state (12/13
   signature, seeded id named).
2. Environment materialization in `grade` + the `resolved_versions` receipt
   field, with refusal/sibling and omission/presence tests; existing-task
   byte-compatibility pinned.
3. The three-row qualification gate and the contamination pairs per task.
4. Documentation: spec amendment if needed, plan, and close-out records
   (the probe's `BACKLOG.md` entry already exists).
5. The smoke (§7), last, uncounted.

## 13. Verification record shape

At close-out, `docs/sdd.md` gains a V8 verification record following the
V4/V6/V7 pattern: default-tier counts, the 100 % coverage gate, the named
discrimination fixtures (six known-good 13/13 passes, six known-broken
failures, six contamination pairs), the workspace-absence and
`resolved_versions` attestations, and the smoke evidence directory with the
V5d checklist outcomes.

## 14. Evidence and recomputation

Companion fixtures (read-only inputs, MIT, not committed here verbatim except
as vendored task contents with notice):

```text
~/projects/pauleveritt/swiftstar/fixtures/agenttest/
  acceptance/test_acceptance.py     # 13 tests, the hidden oracle
  reference/app.py models.py templates/ tests/
  broken/app.py                     # bare app, zero routes
  repair/<state>/                   # sparse deltas + .delete markers
  PROVENANCE.md                     # source commits 8af05f8/191895e, pins
```

The gate command recomputed at close-out runs the three rows per task through
`grade` and names each fixture; it is recorded in the verification record.
Re-derivation is mandatory wherever this spec cites a companion-repo number
(per-state failing id, failure output, 12/13 signature): each is re-earned on
the vendored task by running this repository's own suite, and the recomputing
command travels with the claim.
