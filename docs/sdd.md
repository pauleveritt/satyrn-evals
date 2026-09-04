# How we work

This repository runs on **spec-driven development**: every feature cycle
produces a design spec (what we're building and why) and an implementation
plan (the task-by-task decomposition), both committed before the code.

The cycle shape, from the superpowers workflow:

1. **Brainstorm** — clarify the idea into a design, present it, get
   approval.
2. **Spec** — write the validated design to
   `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, commit it.
3. **Plan** — write the implementation plan to
   `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`, commit it.
4. **Implement** — work the plan in reviewable cycles, each ending with a
   command a contributor can run and evidence that names a success fixture
   and a failure fixture.
5. **Record** — completed phases, and the withdrawn framings and retracted
   figures found along the way, move to the archive section of
   `ROADMAP.md` rather than being edited away.

The disciplines review holds you to:

- **Concept budget** — new jargon is a cost against a 5–10 h/wk
  contributor's ability to hold the design in mind.
- **Non-vacuity** — a refusal test has a sibling success test.
- **Verify, don't assert** — demonstrate a claim, don't state it.

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
561 passed, 178 deselected

.venv/bin/pytest tests/integration -m integration -q
170 passed, 3 skipped

.venv/bin/pytest -m '' --cov=src/satyrn_evals --cov-branch \
  --cov-report=term-missing --cov-fail-under=100
736 passed, 3 skipped
2918 statements, 940 branches, 100% coverage
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
(`pi-d60db938bdef`), 508 `message_update` events across a 169,752-byte
transcript, parseable artifacts, clean teardown, exit 0. No
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
