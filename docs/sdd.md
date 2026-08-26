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
