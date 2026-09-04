# V8 — AgentClinic through Evals: design spec

**Status: design of record for V8 (branch `v8-agentclinic`), written
2026-09-04 after a four-decision maintainer brainstorm: scope B, the
`swiftstar` companion repository as fixture input, six hand-authored bundled
tasks with the full 13-test hidden oracle, and the task-owned base project as
the environment of record. Corrections are recorded where they land.

**Amended 2026-09-04 (maintainer review).** The first draft described the
fixtures from memory: a "recorded 12/13 signature" true for only two bugs
was generalized to all six. Corrections land where recorded — §2/§6 carry
the re-derived failing sets (§14), §7 changes the smoke target, §11 reverses
no-public-tests with its reason, §10 names the build-role path.

## Relationship to what is on main

Main's tip at writing is `2bb452b`. V7's post-merge review (Sol)
remediation is ahead of this branch's origin: attempt records carry their
own `attempt_dir`; `run` no longer infers cell identity from an
output-directory delta (`09cc041`); the 100 % coverage gate is restored
(`5e80dec`); the V7 verification record and spec close-out amendment are
committed (`1863141`), with `ROADMAP.md`'s V7 status cell citing both without
reopening the phase (`d82398e`).

## 1. Direction, and the evidence behind it

The roadmap row (`ROADMAP.md:96`):

> **V8 — AgentClinic through Evals:** reproduce the repair fixtures on this
> repository's own `capture`/`attempt`/`grade` path, replacing the spike's
> scratchpad harness. Excludes: engine changes, including a `facts` field
> (satyrn-engine `BACKLOG.md`); an orchestrator.

The maintainer-review sequence that placed V8 where it is
(`2026-09-02-phase-proposals-and-session-eval-convergence.md` §5): land PR #17
→ repair instrument semantics → containment decision → **reproduce AgentClinic
through Evals** → then test engine facts. V6 and V7 landed the first three; V8
is the reproduce step; engine `facts` is after it, never inside it.

**Why repair fixtures, and why re-derive on this path.** The overnight run
found the repair fixtures were the only workload measured whose distribution
moves (`2026-09-02-overnight-packet-and-isolation-run.md` §5), through a
scratchpad harness whose numbers "must be re-derived before they are cited
in a plan" (ibid. §7) and whose instrument carried four defects of one class
plus an environment confound — grader on reachable disk, oracle env
differing from the model's (six false passes, spike Correction 4), and the
`factonly` arm's advantage sharing one cause with its protection. V8 replaces
that instrument with this repository's own path: grader never in the attempt
workspace (V6 overlay), task owning its environment (below).

**Scope decision (B), recorded.** V8 offline-qualifies the dependency-bearing
hidden-oracle path deterministically and runs one durable, uncounted smoke.
The budgeted admission probe is **not** part of V8; it is a separately
confirmed, preregistered measurement proposal whose reopen condition is
recorded in `BACKLOG.md`.

**Input decision, recorded.** The fixture set is `swiftstar`'s
`fixtures/agenttest/` (`github.com/pauleveritt/swiftstar`; local clone at
`~/projects/pauleveritt/swiftstar`), whose `PROVENANCE.md` names its
`local-ai-pi` source commits (`8af05f8`, `191895e`), records `repair/` was
authored there (2026-08-24), and pins the dependency versions. Availability,
provenance, and publication rights were confirmed; `swiftstar` is MIT
(c) 2026 Paul Everitt, so vendoring with the notice retained is explicit.
The spike evidence archive (`~/work/satyrn/evidence/2026-09-02-agentclinic-
spike.tar.gz`) is **evidence only** — unsanitized, never a source of
publishable task contents. Re-derived equivalents would be a different input
decision, never silently substituted for the canonical six fixtures.

## 2. The six tasks: packaging and data shapes

Six bundled tasks under `src/satyrn_evals/tasks/`, one per seeded repair
state, named `agentclinic-repair-{depth-2, depth-3, framing-2,
framing-2-edit, misleading-locus, plausible-wrong-fix}`. Each directory is
self-contained:

```text
agentclinic-repair-<state>/
  manifest.json
  base/                  # the reconstructed broken app (see below)
    pyproject.toml       # authored; runtime pins + locked dev group
    uv.lock              # committed
    app.py  models.py  templates/{home,base,complaints}.html   # per state
    tests/test_app.py    # public tests, vendored from reference/tests (§11.7)
  overlay/               # grader-only: the vendored 13-test acceptance suite
    test_acceptance.py
  fixtures/
    known-good.patch     # the reference fix delta (state -> reference)
    known-broken.patch   # an authored plausible-wrong repair
  LICENSE                # the swiftstar MIT notice
  PROVENANCE             # swiftstar commit, state, reconstruction rule, pins
```

**Base reconstruction rule.** The swiftstar repair directories are sparse
deltas, not trees (verified by listing and `diff`, 2026-09-04): each holds
only files that differ from the reference solution, plus meta. Each entry is
one of three classes: a **content override** replacing the same-named
reference file (`reference/app.py`, `reference/models.py`, a
`reference/templates/` file); a **content addition** (a state-only file); a
`.delete` **marker** naming a reference file to omit; or a per-state
`README*.md` **documentation** file — a contract-authoring input (§4), never
vendored into `base/`. Each `base/` is therefore the reference app tree
(`app.py`, `models.py`, `templates/{home,base,complaints}.html`,
`tests/test_app.py`) minus each `.delete`-named file, plus the state's
overrides and additions.

**The signature is not uniform.** `PROVENANCE.md` records "12/13 each" for
the two bugs it describes; the first draft generalized it to all six and was
wrong. Re-derived on the real suite (§14), the six bases fall into three
evidence classes:

| state | delta files | base suite result (re-derived 2026-09-04) |
|---|---|---|
| `misleading-locus` | `app.py` | 12/13 — 1 failed: `test_posted_complaint_appears_on_complaints_board` |
| `plausible-wrong-fix` | `app.py` | 12/13 — 1 failed: `test_post_complaint_redirects_to_complaints_board` |
| `depth-2` | `app.py`, `templates/base.html` | 10/13 — 3 failed |
| `depth-3` | `models.py`, `app.py`, `templates/base.html` | 9/13 — 4 failed |
| `framing-2` | `app.py`, `.delete` naming `models.py` | collection abort — `ModuleNotFoundError: models` (`app.py:7`) |
| `framing-2-edit` | `models.py`, `app.py`, `README.md` (documentation) | collection abort — `AttributeError: models.complaints` |

The delta-file column is the "files to fix" — a state dir holds exactly
the files its fix touches. Each base must reproduce **its own recorded
failing set**, re-proven by the §6 gate; a reconstruction that drops a delta
(e.g. depth-2's template change) fails that gate. `framing-2` is retained
although `repair/framing-2-edit/README.md` marks it "superseded for this
purpose": it is the only author-from-scratch cell (the fix recreates
`models.py` from an implied contract), and the supersession is recorded,
never silently edited away.

**Manifest fields.** No schema change. `oracle_visibility: "hidden"`;
`grader_overlay: "overlay"`; `oracle` runs the oracle hook with all thirteen
test ids; `expected_test_ids` is the same thirteen. The `contract` is the
repair prompt (§4). `source_paths` lists the per-state repairable app files —
derived from each state's fix delta, never lockfiles, `pyproject.toml`, or
`tests/` (§11.7 makes public tests immutable under grading). `fixtures` names
`known_good`/`known_broken`; `provenance` names the swiftstar commit, the
state, the reconstruction rule, and the pins.

**Overlay duplication, decided.** The acceptance suite is byte-identical
across all six tasks, and the overlay validator is task-dir-scoped
(`manifest.py:32-58`). Six self-contained copies ship — accepted duplication,
no schema change, each task independently reproducible. The suite stays
harness-owned grader content: never named in a contract, never in an attempt
workspace, graded only from the overlay.

## 3. The environment: provenance and materialization

**The task is a real project.** Each `base/` carries an authored
`pyproject.toml` declaring the pinned runtime dependencies —
`fastapi[standard]==0.115.10`, `turbohtml==1.5.0`, `httpx` — and a committed
`uv.lock`. `pytest==8.3.4` lives in a **locked test/dev dependency group** of
the same project, so grade materializes one deterministic project environment
— no `--with` convention (maintainer clarification). A runner, a bare model,
or a human needs only `uv sync --locked` in `base/`.

**Grade-side change — the only production-code change in V8.** When the
graded tree is dependency-bearing (its `base/` carries `pyproject.toml` and
`uv.lock`), `grade` materializes the project's locked environment into a
relocated project env at a scratch path outside the graded tree
(`UV_PROJECT_ENVIRONMENT`), runs the oracle inside it, and writes the
attestation below. Stdlib/vendored tasks — every bundled task that predates
V8 — are untouched: ambient python exactly as today, no new receipt field,
byte-compatible receipts.

**The oracle hook import.** The oracle command runs `python -m pytest -p
satyrn_evals.oracle_hook …`. In the materialized env the package is not
installed, so grade prepends a controlled `PYTHONPATH` naming the evals
package source; nothing else leaks into the oracle env. Oracle runs set
`PYTHONDONTWRITEBYTECODE=1`, carrying forward the V6 session-runtime lesson
that stray bytecode pollutes captured trees.

**`resolved_versions`, attested not inferred.** The receipt field
`resolved_versions` (§9) is populated from the **materialized environment's
installed distributions** — the full `uv pip freeze` of the env grade
actually executed — not by parsing `uv.lock` (maintainer correction: the
receipt attests to what grade ran; a lock is a promise, a freeze is a
record). Omitted for ambient/stdlib grading.

## 4. Contracts: the repair prompt

Each contract is a repair work order: the task statement plus that fixture's
**verified failure output** — the seeded bug's real traceback as produced by
running the suite against the vendored `base/`. The per-state documentation
in the companion repository (`repair/README.md` sections and per-state
`README*.md` files, e.g. `framing-2-edit/README.md`) is the authoring source
for describing the seeded bug; the failure output itself is **re-derived
during implementation**, never copied unchecked from the companion
repository: BRIEF rule 7 ("cite, don't recall") requires the text a model
sees to match this repository's own grade output. The traceback names
`test_acceptance.py`, never present in the attempt workspace; the runnable
tests are `tests/test_app.py` (§11.7) — hidden suite's failure output,
public suite's local runner, deliberately split.

The confounded "ownership sentence" from the overnight run (`factonly`) is
**not** in the contract: it is a measured prompt-arm variable whose advantage
and protection shared one cause (`2026-09-02-overnight-packet-and-isolation-
run.md`, the exposure correction). On this path the grader is structurally
unreachable from the attempt workspace (V6/V7 overlay), so that isolation is
designed in; the wording belongs to the deferred probe, not the fixture.

## 5. Contamination evidence, both directions, per task

V7's rule-8 discipline (`BRIEF.md`, binding rule 8) applies to each new
overlay: a known-bad from the task's own batch must fire the detector, and a
known-good from the same batch must stay silent. Per task, following the V7
`test_contamination.py` trio's shape: a patch embedding five non-blank lines
of that task's own overlay flags with evidence naming the overlay file; the
task's `fixtures/known-good.patch` stays clean; a same-behavior,
different-bytes restatement never fires. These are integration-tier tests (a
real grade is a subprocess) reusing the overlay bytes. The vendored public
tests were checked byte-wise against the overlay (§11.7): no verbatim
overlap, so restating them introduces no overlay-content identity — the V7
sixfold-overstatement class does not apply here.

## 6. The offline qualification gate

Deterministic, no model, asserted by fixture name (BRIEF rules 2 and 8), per
task:

| row | input | expectation |
|---|---|---|
| base | broken state, no patch | verdict fails, matching the state's recorded failing set in §2 (assertion counts by id, or collection abort) |
| known-good | `fixtures/known-good.patch` (reference fix delta) | verdict passes, 13/13 |
| known-broken | `fixtures/known-broken.patch` (plausible-wrong repair) | verdict fails, failing id(s) named |

The §2 failing sets are the gate's expectations, re-proven on the vendored
task. A collection-abort base is a valid base row: the oracle hook records
collection errors as hook evidence (`oracle_hook.py:16-21, 44-50`), so the
verdict comes from the hook's record — never a pytest exit or an
`unavailable`-shaped void. The gate is integration-tier tests plus a
documented, recomputable command (the V5c precedent; §14, and the
`docs/sdd.md` verification record at close-out).

**What the six states encode (and do not encode).** The set is a designed
gradient — one-file to three-file fixes, assertion-evidence against
collection-abort bases — the first suite here built with headroom as a design
axis rather than found by accident (BRIEF.md's unsolved problem). Whether any
rung is middle-band is **unmeasured**: the only prior signal is the
confounded overnight block, whose ranking was retracted for unequal runner
exposure (`2026-09-02-overnight-packet-and-isolation-run.md`). V8 measures
nothing; the deferred probe exists to find out.

## 7. The smoke

One real-model attempt through the qualified path — a dependency-bearing
hidden-oracle single-shot attempt — on **`plausible-wrong-fix`** (a
single-file fix whose base fails exactly one assertion), after every offline
row of all six tasks is green. `framing-2` is not the target: its fix is two
files, one authored from scratch, and its successor README marks it
superseded (§2); the smoke exercises plumbing, so it uses the cleanest
single-assertion state. The V5d practice applies: uncounted, durable,
uniquely named evidence; attempt record always read, receipt only when
grading ran; `NO_PATCH`/`COMMAND_TIMEOUT` pass only on positive evidence the
model started; no admission or quality claim. Model: local only (V6
precedent). The attempt command is the product seam — the stock engine's
attempt against the base project — so the smoke exercises the path V8
qualifies, not a test double; an engine defect it surfaces is recorded, not
fixed here (engine changes excluded).

## 8. CLI surface and exit codes

Unchanged. V8 adds no commands and changes no exit code: it qualifies
bundled tasks and records evidence through the existing `grade`, `attempt`,
and `run` surfaces (stated explicitly per the CLAUDE.md design-proposal
requirement: no surface change is intended).

## 9. Data shapes

- `TaskManifest`: unchanged schema; new values only (`manifest.py:19-30`).
- `Receipt`: gains `resolved_versions: dict[str, str] | None = None`
  (`receipt.py:11-18`), written only when grading materialized an
  environment, None-popped like `contamination`. It holds the full `uv pip
  freeze` of the executed oracle env, keyed by normalized package name →
  exact version.
- No new record files; `attempt.json`, the receipt, and the run summary are
  unchanged in shape except the receipt field above.

## 10. Non-goals

- **The budgeted admission probe** (scope C): a separately confirmed,
  preregistered measurement proposal, not this phase.
- **Engine changes**, including the `facts` field (satyrn-engine `BACKLOG.md`).
- **An orchestrator** (remains unjustified).
- **Capture changes**: cumulative-suite capture is deferred to `BACKLOG.md`
  with its reopen condition (committed `2bb452b`).
- **OS-level containment** (deferred; V7 detects rather than prevents).
- Any `run`/summary change, new CLI, or new exit code.

**Expansion path, not V8.** The build role sits just past these fixtures:
swiftstar's `broken/app.py` (zero routes) plus `specs/roadmap.md` (three
phases) compose a cumulative-suite, multi-file build-from-spec task — the
next rung toward "actual development." The cumulative-capture backlog entry
(`BACKLOG.md`) is the hook when that is pursued; this spec does not design it.

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
   repairable app files derived per state and excluding `tests/`, so the
   public tests are immutable under grading.
6. The receipt field is named `resolved_versions` and is omitted for
   ambient/stdlib grading.
7. **Correction (maintainer review, same day) — public tests are vendored.**
   The earlier no-public-tests recommendation is reversed:
   `reference/tests/test_app.py` (four tests) ships in each `base/` as the
   runnable local signal — a working local runner is the overnight
   correction's requirement for a decisive experiment, and a traceback
   naming `test_acceptance.py` with no runnable file anywhere is the
   dumb-arm precondition behind the recorded `ls -R` spirals. Partial public
   coverage against a stricter hidden suite is the realism simulated; a
   model that still hunts while runnable tests sit in its workspace is a
   cleaner pathology signal. No verbatim overlap with the 13-test overlay
   (§5); `source_paths` excludes `tests/`, so read/run-only.

## 12. Reviewable slices

Proposed implementation order (the plan decomposes and sequences these):
1. Vendoring and reconstruction: the six `base/` trees + authored projects,
   licenses, provenance; reconstruction verification per state (the recorded
   failing set of §2 — assertion counts or collection abort).
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
`resolved_versions` attestations, and the smoke evidence directory with its
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
`grade`, naming each fixture; it is recorded in the verification record.
Re-derivation is mandatory wherever this spec cites a companion-repo number
(per-state failing id, failure output, base signature) — each is re-earned on
the vendored task, and the recomputing command travels with the claim.

**The §2 failing sets were produced by this command on 2026-09-04, not
copied.** Each tree was composed exactly as §2 prescribes (reference files,
state overrides applied, `.delete`-named files removed, acceptance suite
copied in):

```bash
cd ~/projects/pauleveritt/swiftstar/fixtures/agenttest
for s in misleading-locus plausible-wrong-fix depth-2 depth-3 framing-2 framing-2-edit; do
  d=$(mktemp -d)
  cp reference/app.py reference/models.py "$d"/ && cp -r reference/templates "$d"/
  cp -r "repair/$s/." "$d"/
  [ -f "repair/$s/.delete" ] && while read -r f; do rm -f "$d/$f"; done < "repair/$s/.delete"
  cp acceptance/test_acceptance.py "$d"/
  (cd "$d" && uv run --no-project --quiet \
    --with "fastapi[standard]==0.115.10" --with "turbohtml==1.5.0" --with httpx \
    --with "pytest==8.3.4" python -m pytest -q test_acceptance.py 2>&1 | tail -4)
  rm -rf "$d"
done
```

Output tails match the §2 table: `misleading-locus` and
`plausible-wrong-fix` 1 failed/12 passed; `depth-2` 3 failed/10 passed
(`test_home_html_element_declares_english_language`,
`test_complaints_board_preserves_the_shared_layout`,
`test_post_complaint_redirects_to_complaints_board`); `depth-3` 4 failed/9
passed (those three plus `test_complaint_model_contract_is_preserved`);
`framing-2` collection error, `ModuleNotFoundError: models` at `app.py:7`;
`framing-2-edit` collection error, `AttributeError: models.complaints`. The
slice-1 gate re-derives these from the bundled trees — this command is the
recomputation it must match.
