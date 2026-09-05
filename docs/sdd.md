# How we work

This repository runs on **spec-driven development**: every feature cycle
produces a design spec (what we're building and why) and an implementation
plan (the task-by-task decomposition), both prepared before the code. Commit
timing is maintainer-controlled; implementation tasks are not automatic
commit checkpoints.

The cycle shape, from the superpowers workflow:

1. **Brainstorm** — clarify the idea into a design, present it, get
   approval.
2. **Spec** — write the validated design to
   `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`.
3. **Plan** — write the implementation plan to
   `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`.
4. **Implement** — work the plan in reviewable cycles, each ending with a
   command a contributor can run and evidence that names a success fixture
   and a failure fixture.
5. **Record** — completed phases, and the withdrawn framings and retracted
   figures found along the way, move to the archive section of
   `ROADMAP.md` rather than being edited away.

The maintainer decides when to commit. Agents may leave the worktree dirty
across plan tasks and must not create checkpoint commits unless explicitly
asked. The maintainer may request a commit at any point, and a phase may be
landed as one consolidated implementation commit plus a separate close-out
commit when that is useful.

The disciplines review holds you to:

- **Concept budget** — new jargon is a cost against a 5–10 h/wk
  contributor's ability to hold the design in mind.
- **Non-vacuity** — a refusal test has a sibling success test.
- **Verify, don't assert** — demonstrate a claim, don't state it.
- **Diagrams** — contrast holds on the diagram's own card background (never
  on the page theme), card labels match the page's vocabulary, no orphaned
  asset files, and every figure is verified in the strict build with alt
  text present.

## Document caps

Two predecessor projects recorded the same failure: machinery, and the
documents describing it, outgrowing anyone's ability to hold them in mind. One
of them let `ROADMAP.md` reach roughly 1,000 lines, about 800 of them Backlog,
one defensible paragraph at a time. Its rules capped *cells* and *plans* but
never the *file*, so nothing bounded the thing that actually grew.

So: caps, and a checker. Neither works alone — a convention nothing checks is
one this lineage has already watched fail.

| Document | Cap | Over cap means |
|---|---|---|
| `ROADMAP.md` **whole file** | 400 lines | Something owes a move to `docs/superpowers/research/` or deletion |
| `BACKLOG.md` **whole file** | 400 lines | Prune resolved entries, or a research doc is owed |
| Phase-table **Direction** cell | 900 chars | A verdict or research doc is owed |
| Phase-table **Status** cell | 1,000 chars | A verdict or research doc is owed |
| Phase-table **Excludes** cell | uncapped | Deliberate — see below |
| **Backlog entry** | 1,200 chars | A research doc is owed; the entry keeps a summary, a link, and the reopen condition |
| **Spec** | 400 lines | Split the design |
| **Plan** | 400 lines | Split the phase |

**The Excludes column is uncapped, and the checker is header-aware.** A phase
row states what it ships *and what it does not*, so a reader can tell scope
creep from progress. The cell is uncapped because it is a list, not an
argument. The checker keys columns by header name rather than position: the
sibling project added this column to a positional checker and its Status cap
silently began measuring Excludes, caught only at phase close-out. Two
regression tests pin the mapping, with a third asserting Excludes stays
uncapped.

**Excludes for a phase with no spec is provisional.** Where a spec exists, the
cell condenses that spec's own non-goals section. Where one does not, it is
derived from `ROADMAP.md` and `BACKLOG.md` and is superseded by the spec when
the phase gains one.

**Caps apply at every update, not only at phase close.** A cell growing
mid-phase is the signal that a document is owed *now*, not later.

**The numbers are inherited, not calibrated here.** They come from a sibling
project's post-cleanup calibration. An earlier attempt in that lineage used a
uniform 300-character cap chosen in the abstract and failed immediately against
real content. If a cap here proves wrong against this project's own writing,
change it deliberately and record why — do not quietly exceed it.

Enforcement is `just lint-docs`.

## Backlog discipline

1. **Every entry states what reopens it.** An entry that cannot say what would
   make it relevant again is deleted, not kept "just in case".
2. **An entry over its cap owes a research doc.** The entry keeps a summary, a
   link, and the reopen condition — not the argument.
3. **Entries are pruned, not archived in place.** Resolved, retired and
   superseded entries are removed once their outcome is recorded in a phase row
   or a research doc that the row links.


## V4 verification record

V4 was verified on macOS against satyrn-engine E5 commit
`82a62f50a1d716fae4c12d9fc68e25a2b0bc70bc`. The Engine was invoked only
through its CLI; evals production code imports no Engine module.

```text
.venv/bin/pytest -q
421 passed, 106 deselected

SATYRN_V4_ENGINE_REPO=/private/tmp/satyrn-engine-v4-e5 \
  .venv/bin/pytest -m integration -q
105 passed, 1 skipped, 421 deselected

SATYRN_V4_ENGINE_REPO=/private/tmp/satyrn-engine-v4-e5 \
  .venv/bin/pytest -m '' --cov=src/satyrn_evals --cov-branch \
  --cov-report=term-missing \
  --cov-fail-under=100
526 passed, 1 skipped
1922 statements, 622 branches, 100% coverage
```

These counts are a macOS evidence snapshot; pass and skip totals can vary by
filesystem. Here, the single capability skip is the existing non-UTF-8
filename fixture on a macOS filesystem that refuses such a name. On a
case-sensitive Linux filesystem, the case-alias capability test skips instead;
an OS-independent sibling still covers the identity branch. The real E5
success test exercises the full Evals → installed `uv` project runner →
Engine CLI → Pi adapter →
Node mutator → Python protocol → patch → offline grade path and names the
bundled `format_number` fixture. Only Pi is replaced by a deterministic
fixture. Its failure sibling preserves the transcript and its digest plus the
Engine exit while refusing the missing patch. Both prove that the allocated
workspace is gone before return. Real Git siblings cover exact detached HEAD,
ignored persisted files, real clean/smudge filters, disabled hooks/fsmonitor,
hostile `TMPDIR` inside a registered sibling worktree, an outer enclosing
repository, or a bare repository, timeout descendant teardown, registration
uncertainty, complete enum policy maps, strict legacy/V4 record shapes, and
retained-parent evidence even when the linked worktree path has disappeared.
Cleanup and unexpected-exception siblings preserve the same recovery evidence.

The timeout, locked-cleanup, and post-registration interrupt group passed
three consecutive real-process runs with:

```text
for run in 1 2 3; do
  .venv/bin/pytest -q -m integration tests/integration/test_workspace.py \
    -k 'timeout or locked or registration'
done
```

Ruff lint (`ruff check .`), Pyrefly, strict Sphinx, and `git diff --check` also
passed on the same tree. Windows is not part of this evidence.

## V6 verification record

V6's default tier is model-, network-, and subprocess-free; the session
executor, the shipped Pi adapter's process behavior, and the oracle floor
tests are marked integration and excluded from CI. The deterministic
four-prompt proof replaces Pi with a scripted RPC fixture (the V4
substitution pattern) and is called adapter integration — it makes no
real-model claim.

```text
.venv/bin/pytest -q
574 passed, 190 deselected

.venv/bin/pytest tests/integration -m integration -q
182 passed, 3 skipped

.venv/bin/pytest -m '' --cov=src/satyrn_evals --cov-branch \
  --cov-report=term-missing --cov-fail-under=100
761 passed, 3 skipped
2961 statements, 958 branches, 100% coverage
```

The statement count is recomputed by the gate command on this tree
(coverage 7.15.4 in the worktree venv); a later coverage version can
report a slightly different statement count (the branch count and the
100% verdict are the invariant).

Correction (2026-09-03, review-fix cycle): the earlier "655 passed / 100%"
line was asserted without reading the gate's full output — the coverage
gate had been failing under the tail-of-output habit. The numbers above
are from a run whose full output was read; the 100% gate is now held by
730+ passing tests including the review-fix failure paths.

Ruff lint clean; `just lint-docs` within caps; the svcs probe import
hashes to `296a961f…` as committed (V6 delta spec, Delta 5). macOS-only
evidence; Windows is not part of this record. A worktree needs
`uv sync --group integration` — the integration group carries the svcs
runtime's third-party imports (`pyproject.toml:39-44`).

### The real-model smoke (layer (b))

**Status: completed 2026-09-04, plumbing pass.**

One uncounted real-model session through the shipped adapter against the
stock Pi executable (`pi` 0.84.4), local model only (no shim, no new
network/auth variables): the omlx server was already running and served
the probe-era `gemma-4-12B-it-MLX-8bit`, so the run preserved continuity
with the V5a-era environment.

Evidence directory (durable, uniquely named):
`~/projects/satyrn-v6-scratch/sessions/smoke-session-mechanics-20260904-043457/`
(record `session-mechanics-session-20260904-083458-191705/`).

```
satyrn-evals session session-mechanics --output $SMOKE_OUTPUT -- \
  satyrn-evals-session-pi --provider omlx --model gemma-4-12B-it-MLX-8bit
```

The five assertions, evidenced individually from the retained artifacts:

1. **Pi accepted the model configuration** — the session started, one
   conversation id (`pi-dbc8defb6b40`), a 1,554,904-byte transcript.
2. **Genuine model-stream events** — 243+ `message_update` events with
   streamed content in the first ~500 transcript lines alone, plus
   thinking deltas; the mapped events carry the original Pi payload.
3. **One conversation across the ordered prompts reached** — one stable
   conversation identity; the terminal came on the first prompt.
4. **Parseable session/checkpoint artifacts** — the record, checkpoint
   patch (3,298 bytes), snapshot, and the preservation receipt
   (`preservation-add-slugify.json`, verdict `pass`) all parse; the
   session exited 0 and `retained_path` is null.
5. **Teardown clean** — exit 0, record written, workspace released.

**No compatibility shim** — the shipped adapter passed against the
supported Pi executable itself (stock `pi --mode rpc --no-session`).

**Terminal state.** `agent-error` on `add-slugify` after 298 turns / 297
bash executions, with Pi's own final `stopReason: "error"` — the adapter
correctly derived the agent-error terminal from Pi's declaration (review
finding 3 works end to end on a real model). Model behavior may pass or
fail; the smoke makes no admission, difficulty, or quality claim. (The
model never edited `src/textkit/__init__.py` across those 298 turns — its
only tree changes were bytecode files; that is recorded as model
behavior, not plumbing.)

**Harness finding surfaced by the smoke (the purpose of the run).**
Running the public tests writes `__pycache__/*.pyc` under `src/` and
`tests/`; those land in the cumulative patch and become scope violations,
so hidden feature grading is skipped for the checkpoint. A model that
self-verifies — which any real diagnostic run requires — would have its
checkpoints marked out-of-scope.

**Resolution (maintainer decision 2026-09-04): the session runtime
policy.** `PYTHONDONTWRITEBYTECODE=1` is set on the pi child's environment
by the shipped adapter (`_SESSION_RUNTIME_ENV` in
`src/satyrn_evals/adapters/pi_session.py`), so the model's python
subprocesses inherit it. Deliberately no fixture `.gitignore`: a
gitignore would change the evidence boundary and could hide unrelated
mutations under ignored paths; the environment policy leaves
`source_paths` enforcement intact. Tested in three directions: a real
pytest run inside the workspace leaves no `__pycache__` in the captured
tree; a genuine out-of-scope edit still produces `SCOPE_VIOLATION` while
bytecode stays suppressed; and the adapter's pi child is shown to
inherit the setting.

### Second real-model smoke (2026-09-04, corrected adapter — revised execution path)

One more uncounted smoke on the corrected stock adapter (the policy
changed the shipped adapter's effective execution environment), same
model and rule as the first (local `omlx/gemma-4-12B-it-MLX-8bit`,
stock pi 0.84.4, no shim, durable evidence):

Evidence directory:
`~/projects/satyrn-v6-scratch/sessions/smoke2-session-mechanics-20260904-052924/`
(record `session-mechanics-session-20260904-092640-*`).

Plumbing pass, and the `__pycache__` finding is gone: all four prompts
settled (turns 20/6/7/5), review reached, one conversation
(`pi-d60db938bdef`), 508 `message_update` events across the full
386,383-byte transcript (step 1's checkpoint transcript-prefix length is
169,752 bytes — the prefix, not the whole file), parseable artifacts,
clean teardown, exit 0. No
`__pycache__` anywhere in the captured patches.

Model behavior (no admission/quality claim, but recorded): the model
produced a competent alternate structure — new sibling modules
`slugify.py`/`truncate.py`/`pluralize.py` with re-exports added to
`__init__.py`, plus its own test files, and edits to the public
`tests/test_textkit.py`. Under the fixture's narrow `source_paths`
(`src/textkit/__init__.py` only) every one of those is out-of-scope, so
the record ends `SCOPE_VIOLATION` and feature grading is skipped
(`feature_verdict: None`) even though the re-export structure would
satisfy the hidden tests. Preservation at the last checkpoint reports
`pass` — graded against the model's own edited public test, which is
circular.

**Resolution (maintainer decision 2026-09-04) — fixture/grader
correction, recorded with tests.** Two changes, neither requiring an
adapter smoke (the adapter/runtime path is unchanged):

1. **`source_paths` widened to `src/textkit`** (the package directory,
   directory-prefix matching — not a `**` glob). This admits the normal
   sibling-module implementation (`slugify.py`/`truncate.py`/
   `pluralize.py` with re-exports) while keeping the task's code
   boundary clear. `tests/` stays immutable and out of scope: public-test
   edits are never an accepted way to satisfy preservation. Making the
   widening work required unifying two matching rules that had drifted:
   the session scope classifier already matched directory prefixes but
   the grader's `check_allowlist` was exact-only — both now share one
   `within_source` rule in `src/satyrn_evals/patch.py` (a directory
   entry admits everything under it; the slash guard keeps a file entry
   from admitting prefix look-alikes).

2. **Circular-preservation fix.** When the captured patch changes a
   protected public test (the module file of a
   `base_preservation_selectors` id), the grader records
   `preservation_verdict: "invalid"` — explicitly not meaningful for
   that checkpoint — with no preservation receipt, instead of presenting
   a circular passing receipt as evidence of preserved behavior. The
   scope violation stays recorded, and the session still ends
   `SCOPE_VIOLATION`. A scope violation that is *not* a protected
   public test (e.g. a stray file) still grades preservation normally.

The svcs proposal inherits both rules: its `source_paths` shape admits
the package directory, its protected public tests are immutable, and a
patch editing them yields preservation `invalid`, never a circular pass.

### Third real-model smoke (2026-09-04, corrected runtime — final remediation smoke)

One more uncounted smoke after the integrity and evidence fixes — the
sanitized Git environment, prompt-wide deadline, per-checkpoint durable
record, and the preservation-invalid rule are a materially revised
execution path, so V5d requires a fresh smoke before any budgeted use.
Same model and rule as the prior smokes (local
`omlx/gemma-4-12B-it-MLX-8bit`, stock pi 0.84.4, no shim, durable
evidence):

Evidence directory:
`~/projects/satyrn-v6-scratch/sessions/smoke3-session-mechanics-20260904-063108/`
(record `session-mechanics-session-20260904-103108-289426/`).

Plumbing pass. The five assertions:

1. **Pi accepted the model configuration** — one conversation
   (`pi-59b6f5f6a72a`), a 335,874-byte transcript.
2. **Genuine model-stream events** — 528 `message_update` events in the
   full transcript.
3. **One conversation across the ordered prompts reached** — all four
   prompts settled (turns 15/5/5/2), review reached, one identity.
4. **Parseable session/checkpoint artifacts** — record, four checkpoint
   patches, four snapshots (each `{"tree", "status"}`, the status now
   load-bearing), transcript; exit 0, `retained_path` null.
5. **Teardown clean.**

**No compatibility shim.** **Preservation-invalid rule proven on a real
model:** the model edited the protected public test
(`tests/test_textkit.py`), so the record ends `SCOPE_VIOLATION` and the
last checkpoint's `preservation_verdict` is `invalid` with no receipt —
not a circular pass. Its source work (in-scope `src/textkit/__init__.py`
and a new `src/textkit/utils.py`) is visible in the snapshot status.
Model behavior may pass or fail; the smoke makes no admission or quality
claim.

Exit condition for remediation track 3 is met: the durable record
proves the five smoke assertions on the corrected path. V6 may then be
considered for merge/completion, subject to the maintainer.

## V7 verification record

V7's default tier stays model-, network-, and subprocess-free. The
detection machinery is pure; the grading and session paths that spawn git,
pytest, and the fake adapters are marked integration. The bundled
`local-pings` fixture pair (`tests/integration/test_local_pings_bundled.py`)
needs an external ping receiver that is absent on this machine and fails
identically on the baseline commit — it is excluded below, and the
exclusion is the only deviation from the V6 record's shape.

```text
.venv/bin/pytest -q
630 passed, 207 deselected

.venv/bin/pytest -m integration -q \
  --ignore=tests/integration/test_local_pings_bundled.py
204 passed, 1 skipped, 630 deselected

.venv/bin/pytest -m '' --cov=src/satyrn_evals --cov-branch \
  --cov-report=term-missing --cov-fail-under=100 \
  --ignore=tests/integration/test_local_pings_bundled.py
834 passed, 1 skipped
3208 statements, 1094 branches, 100% coverage
```

The 100% gate is the invariant; the statement count is recomputed by the
gate command on this tree. The coverage recovery is recorded, not edited
away: Sol's post-merge review found V7 merged without a committed
verification record, and running the gate then exposed three uncovered
branches in `session.py` (the transcript-delta fix's defensive edges) —
closed by `tests/integration/test_session_capture_delta.py`, which drives
`_capture_checkpoint` directly against a real prepared workspace.

**Fixture discrimination, both directions (BRIEF rule 8), asserted by
name** — `tests/test_contamination.py`:

- `test_detector_fires_on_contaminated_patch_built_from_bundled_overlay`
  — a patch embedding five non-blank lines of the bundled
  `session-mechanics` overlay flags with evidence naming the overlay file;
- `test_detector_silent_on_bundled_known_good` — the task's own
  `fixtures/known-good.patch` stays clean;
- `test_detector_silent_on_model_authored_restatement` — a same-behavior,
  different-bytes test never fires (the sixfold-overstatement lesson).

**Workspace absence, not merely read-only** —
`tests/integration/test_session_workspace.py`:
`test_hidden_overlay_absent_from_executor_worktree` scans the real
executor worktree and finds no overlay path or overlay-digest file;
`test_overlay_content_in_base_refuses_the_build` proves a copied overlay
file inside base refuses the build. `run_workspace`'s refusal branch is
covered by `test_run_workspace_refuses_overlay_content_in_base`
(`tests/integration/test_workspace.py`).

Ruff lint clean and `just lint-docs` within caps on the recorded tree.
macOS-only evidence; Windows is not part of this record.

## V8 verification record

V8's default tier stays model-, network-, and subprocess-free. The six
`agentclinic-repair-*` tasks' qualification rows, contamination pairs, and
materialized-env grades are integration tier (uv + network on first sync).
The bundled `local-pings` integration tests remain excluded from the coverage
gate for the pre-existing external-receiver reason recorded in the V7 record.

```text
.venv/bin/pytest -q
691 passed, 247 deselected

uv run pytest tests/integration/test_agentclinic_gate.py -q -m integration
24 passed   # 6 base rows (hook records), 6 known-good 13/13, 6 known-broken
            # fail, 6 contamination pairs — asserted by fixture name

uv run pytest -m '' --ignore=tests/integration/test_local_pings_bundled.py \
  --cov=src/satyrn_evals --cov-branch --cov-fail-under=100
933 passed, 3 skipped; 100% statement and branch coverage
```

The 100 % gate is the invariant; the statement count is recomputed by the
gate command. Two production-code changes shipped: (1) grade materializes a
dependency-bearing task's own locked project environment
(`uv sync --locked`, relocated outside the graded tree) and attests the
executed distributions as `resolved_versions` from `uv pip freeze` on the
receipt; (2) the contamination detector subtracts base-visible overlay
windows from its needles (additive — pre-V8 behavior byte-identical).

**Fixture discrimination, both directions, by name** —
`tests/integration/test_agentclinic_gate.py`: six known-good patches pass
13/13 through the real CLI; six known-broken patches fail; base rows
reproduce the recorded per-state failing sets (four assertion states, two
collection aborts) from hook records; six contamination pairs fire on
overlay-only content and stay silent on the shared public-test idiom
(`tests/test_contamination.py` holds the pure fire/silent unit pair).

**Resolved-version attestation:** the `plausible-wrong-fix` known-good
receipt carries `resolved_versions` naming 47 installed distributions
(`fastapi==0.115.10`, `pytest==8.3.4`); stdlib receipts carry no such key.

**The smoke (uncounted, V5d):** one real-model single-shot attempt through
the stock engine on `agentclinic-repair-plausible-wrong-fix` —
`omlx/gemma-4-12B-it-MLX-8bit`, pi 0.84.4. Record:
`docs/superpowers/research/2026-09-04-v8-agentclinic-smoke.md`. The first
attempt failed on a recorded engine-side pi-argv incompatibility (equals-form
`--model=` rejected by pi 0.84.4) and on evals' 30 s attempt default; the
maintainer fixed the engine (separate-token `--model`, engine commit
`d5d5d37`) and the re-run **passed**: verdict pass 13/13, contamination
clean, 92,801-byte transcript of genuine model turns, patch preserved,
`resolved_versions` attested. Evidence:
`~/projects/satyrn-v8-scratch/smoke2-pwf-20260904-160143/`.
## V9 verification record

V9's default tier stays model-, network-, and subprocess-free; the loop-
integrity fixes are proven default-tier with doubles, and every real
subprocess proof (T5's preservation pair, T7's shim, T8's hostile git,
the regrade/summarize round trip, the wheel demonstration) is integration
tier, excluded from CI. Evidence collected 2026-09-04 on macOS.

```text
uv run pytest -q
742 passed, 253 deselected

uv run pytest -q -m integration tests/integration \
  --ignore=tests/integration/test_local_pings_bundled.py
245 passed, 1 skipped        # bundled local-pings excluded (V7 precedent)

uv run pytest -q -m '' --ignore=tests/integration/test_local_pings_bundled.py \
  --cov=src/satyrn_evals --cov-branch --cov-report=term-missing --cov-fail-under=100
992 passed, 1 skipped
3415 statements, 1168 branches, 100% coverage
```

The 100% gate is the invariant; the statement count is recomputed by the
gate command. Ruff lint clean, `just lint-docs` within caps, strict Sphinx
(`sphinx-build -W -b html`) clean, and `git diff --check` clean on the
recorded tree.

**Fixture discrimination, both directions, by name** — the V9 evidence
floor:

- **T5** (`tests/integration/test_grade_preservation_auto_overlay.py`,
  3 passed, names `mini-session-divergent`): the preservation grade under
  the *old* call shape (auto-overlay default) returns `UNAVAILABLE` — the
  hazard pin; under `auto_overlay=False` it returns `PASS` with no
  contamination key; a bare grade on the same fixture still auto-overlays
  and annotates `visibility: hidden`.
- **T6**: an overlay tree chmod'd `0o664`/`0o666` (umask-002 checkouts)
  loads and materializes copies `0o444`
  (`tests/test_overlay.py`), while the genuine stored-file refusals —
  symlink, non-regular, non-UTF-8, source-path overlap, digest mismatch —
  still fire.
- **T8**: hostile ambient `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` leave
  grading correct and never materialize the redirected work tree
  (`tests/integration/test_grade_git_env.py`).
- **Record-before-grade**: the `GRADE_FAILED`/`OK` pair in
  `tests/test_attempt.py` proves a grading `SatyrnError` leaves a durable,
  loadable `GRADE_FAILED` record (no receipt) and a successful grade
  rewrites `OK` with verdict + receipt.
- **The re-score round trip**: real fake-seam `run`, then
  `regrade_attempt` per cell, then `summarize_output` — the rebuilt
  `summary.json` is byte-identical to the run's own
  (`tests/integration/test_rescore.py`, 1 passed).

**The T7 wheel demonstration (recorded verification, run once):** built a
real wheel (`uv build`) into a scratch venv that also carries
`fastapi==0.116.0` (a version that conflicts with the task lock), then
graded the bundled `agentclinic-repair-plausible-wrong-fix` known-good
from that venv:

```bash
SCRATCH=$(mktemp -d)
uv build --out-dir "$SCRATCH/dist"
uv venv "$SCRATCH/venv" --python 3.14
uv pip install --python "$SCRATCH/venv/bin/python" "$SCRATCH"/dist/*.whl \
    "fastapi==0.116.0"
"$SCRATCH/venv/bin/satyrn-evals" grade \
    --tasks-root src/satyrn_evals/tasks \
    agentclinic-repair-plausible-wrong-fix \
    src/satyrn_evals/tasks/agentclinic-repair-plausible-wrong-fix/fixtures/known-good.patch \
    --receipt "$SCRATCH/receipt.json"
python -c "import json;r=json.load(open('$SCRATCH/receipt.json'));print(r['verdict']);print(r['resolved_versions'].get('fastapi'))"
```

Output: verdict `pass`, evidence `{"passed": 13, "failed": 0, "error": 0,
"skipped": 0}`, and `resolved_versions["fastapi"] == "0.115.10"` — the
task lock's version. What this demo proves is scoped: a wheel install
grades end to end (the oracle hook resolves through the shim symlink to
the wheel-installed `satyrn_evals`), and the receipt's attestation is
consistent with the locked environment the oracle ran against
(`resolved_versions` is `uv pip freeze` of the materialized env, so it
reports the lock regardless of `PYTHONPATH`). Import-provenance
discrimination — a dependency shadowed beside evals losing to the locked
env — is not this demo's claim; that is the `python -S` two-env test's
job (`tests/integration/test_grade_shim.py`).

### Post-implementation review corrections (2026-09-04)

A maintainer review of the V9 worktree found three blockers; each was
fixed and is recorded here:

- **B1 — an aborted batch is never presented as complete.** `run` writes
  `summary.json` only when all n attempts complete. On an abort (an
  exception or Ctrl-C) it writes `aborted.json` instead —
  requested/completed counts, the error, and the tallies over the
  completed cells — then re-raises; a later completed run in the same
  directory replaces the marker. Tests:
  `test_run_writes_an_aborted_marker_and_reraises`,
  `test_run_aborts_before_any_cell_writes_a_zero_completed_marker`, and
  `test_run_completion_replaces_a_stale_aborted_marker`.
- **B2 — summarize is anchored on the run's own cells.** `summarize
  OUTPUT_DIR` rebuilds exactly the cells the run's `summary.json` names —
  never a directory scan — so a stray sibling or an un-appended crash cell
  cannot change the rebuilt artifact, and a directory whose run aborted is
  refused (exit 3, message pointing at `aborted.json`). A named cell
  missing from disk is an operational error, never a silent shrink.
  Byte-identity now holds by construction for any completed run.
- **B3 — a git-environment probe failure is one UNAVAILABLE cell, not a
  batch abort.** `clean_git_environment` wraps its routing-variable probe
  and raises `OracleError`, which `grade`'s exception handling turns into a
  single `UNAVAILABLE` receipt; the batch continues.
- **T5 wiring test** added: the preservation opt-out is proven through the
  production `SessionGrader` path on the divergent session fixture, not
  only through direct `grade()` calls.

Re-run gates after the fixes:

```text
uv run pytest -q
748 passed, 255 deselected

uv run pytest -q -m integration tests/integration/test_rescore.py
1 passed

uv run pytest -q -m '' --ignore=tests/integration/test_local_pings_bundled.py \
  --cov=src/satyrn_evals --cov-branch --cov-report=term-missing \
  --cov-fail-under=100
1000 passed, 1 skipped; TOTAL 3454 statements, 1182 branches, 100%
```

Ruff and `git diff --check` clean; `just lint-docs` within caps.

## V10 verification record

V10 ships the transcript-derived pathology counts as an offline reader of
the preserved attempt transcript — the same relationship `grade` has to
`patch.diff`. `pathology.py` enforces the documented well-formedness rules
R1–R6 over the preserved Pi stream-JSON and counts the seven
transcript-local axes (`tool_calls` by name, `repeats`, `churn`,
`noop_edits`, `test_runner_commands`, `tool_free_terminal_turns`,
`workspace_escapes`) plus `overlay_windows` for hidden-oracle measured
cells via decoded-payload scanning. A malformed/partial/unknown
transcript makes the whole cell `{"measured": false, "reason": …}` —
never partial counts beside a clean-looking zero (S1). `summary.json`
carries a per-cell `pathology` block through one shared computation on
`run`'s own summary, the abort marker, and `summarize_output`, so a
rebuilt summary is byte-identical to the run's own under the same code
and artifacts and a pre-V10 run re-summarized under V10 gains the block
(retroactive enrichment). No new CLI surface, no exit-code change, and
`regrade` recomputes no pathology (spec §8). Everything is default-tier pure file/text
processing; no model, no network, no subprocess.

Gate evidence collected on macOS:

```text
uv run pytest -q
842 passed, 255 deselected          # tripwire green (post close-out fixes)

uv run pytest -q -m '' --cov=src/satyrn_evals --cov-branch \
  --cov-report=term-missing --cov-fail-under=100
1096 passed, 1 skipped            # post close-out fixes (R4/R5/toolName + recovery tests)
TOTAL 100% coverage (statement count recomputed by the gate)
```

Recorded correction (2026-09-05, close-out): the gate command drops the
`--ignore=tests/integration/test_local_pings_bundled.py` exclusion carried
since the V7 record — the two bundled local-pings integration tests now
pass (2 passed, 0.65 s), so the count rises by two over V9's shape. The
exclusion's documented reason ("needs an external ping receiver that is
absent on this machine") does not describe these tests: they grade the
bundled known-good/known-broken fixture pair through the task's own
materialized locked environment, made reliable by V8's
environment-materialization work. They remain integration-tier and depend
on the integration dependency group plus first-time locked-env
materialization (uv cache or network on a fresh clone) — the standard
dependency-bearing-task condition, not the receiver failure the exclusion
recorded.

The 100% gate is the invariant; the statement count is recomputed by the
gate command. Ruff lint clean, `just lint-docs` within caps, and
`git diff --check` clean on the recorded tree. Pyrefly: V10's five
changed modules add zero new errors (module-scoped pyrefly reports three
errors, all on pre-existing lines — the `del dict[key]` unsupported-delete
family and the regrade `Path | None` union); the full tree carries ~110
pre-existing pyrefly errors on committed, untouched files — a toolchain
drift since V9's verification, recorded here as a known pre-existing
condition, not a V10 regression.

**Fixture discrimination, both directions, by name** — the V10 evidence
floor:

- **The validation row** (`tests/test_pathology.py::test_validation_row_reproduces_the_spec_table`,
  1 passed): the faithful-good fixture `tests/data/v10/good-repair.jsonl`
  reproduces the spec's §3 row exactly — `tool_calls {read: 6, edit: 2}`,
  `repeats: 4` (`read tests/test_app.py` ×3, `read app.py` ×2, identical
  `edit app.py` ×2), `churn`/`noop_edits`/`test_runner_commands`/
  `tool_free_terminal_turns`/`workspace_escapes`/`overlay_windows` all 0 —
  matching the spec-time count over the preserved V8 smoke transcript.
- **Whole-cell unmeasured (S1)** (`test_measured_false_never_carries_counts`
  plus one fixture per R1–R6 violation, each with its success sibling):
  an empty, unparseable, unknown-vocabulary, wrong-version,
  structurally-malformed, or partial transcript publishes only
  `{"measured": false, "reason": …}`; no count key ever coexists with
  `measured: false`.
- **The overlay detector discriminates** (P3a amendment,
  `tests/test_rescore.py`): a hidden-oracle cell whose decoded tool-result
  payload carries a verbatim overlay window fires (`overlay_windows: 1`);
  the same window present only in a model-visible `base/` text stays
  clean (visible subtraction); an unmeasured cell never carries the key.
- **Retroactive enrichment** (`tests/test_run.py::test_summarize_enriches_a_pre_v10_summary`
  and `test_run_then_summarize_is_byte_identical_with_pathology`, 2
  passed): a run dir whose `summary.json` had its `pathology` key deleted
  re-summarizes to regain the block with every other field unchanged, and
  `summarize_output` over a V10 run reproduces the run's own bytes.
- **The abort marker never lies** (`tests/test_run.py`): a batch that
  aborts writes `aborted.json` — never `summary.json` — carrying the
  pathology block when the binder succeeded, and a binder failure on the
  abort path is folded into the marker's `error` so the primary exception
  always surfaces; an overlay failure on a completed run's summary is
  operational (exit 3).

**Corrections recorded along the way** — cited, not restated; full
records in the V10 spec §13 and
`docs/superpowers/research/2026-09-04-v10-spec-evidence-and-reviews.md`:
the spec self-review corrected the validation row's `repeats` (1 → 4 by
recomputation); the GLM 5.3 review's five Important and four Minor
findings were accepted; the R4 turn-alternation rule and the decoded-payload
`overlay_windows` amendment are recorded in the spec §13 companion (this
file's sibling research record) beside the rules they amended (§2 R4,
§3.8). The BACKLOG.md
"Transcript-derived summary metrics" entry was removed on resolution per
the backlog's rule 3. A maintainer close-out review of the V10 worktree
may produce further corrections, recorded the same way.
