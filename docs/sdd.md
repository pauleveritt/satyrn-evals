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
518 passed, 140 deselected

.venv/bin/pytest tests/integration -m integration -q
132 passed, 3 skipped

.venv/bin/pytest -m '' --cov=src/satyrn_evals --cov-branch \
  --cov-report=term-missing --cov-fail-under=100
655 passed, 3 skipped
2209 statements, 711 branches, 100% coverage
```

Ruff lint clean; `just lint-docs` within caps; the svcs probe import
hashes to `296a961f…` as committed (V6 delta spec, Delta 5). macOS-only
evidence; Windows is not part of this record. A worktree needs
`uv sync --group integration` — the integration group carries the svcs
runtime's third-party imports (`pyproject.toml:39-44`).

### The real-model smoke (layer (b))

The smoke is an explicit V6 done-when item and is deliberately manual
(V5d's practice; see `docs/session-smoke.md`): one uncounted real-model
session through the shipped adapter against the supported Pi executable,
with a durable evidence directory and the five session-specific
assertions evidenced individually in this section — Pi accepted the model
configuration; genuine model-stream events; one conversation across the
ordered prompts reached; parseable session/checkpoint artifacts; clean
teardown — plus the no-shim outcome. Model behavior may pass or fail; the
smoke makes no admission, difficulty, or quality claim.

**Status: pending the maintainer's manual run** — it costs real
wall-clock time and model money by design and is not automatable per the
landed V5d practice. The phase's machinery done-when is met by the tiers
above; the smoke completes V6's done-when when recorded here.
