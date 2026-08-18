# V3 — Attempt persistence: design spec

**Phase:** V3 (`ROADMAP.md`). **Date:** 2026-08-18. **Status:** approved
design (post-brainstorm); implementation plan pending.

## Why this phase

V2 made tasks: `capture --revert SHA` turns a fixing commit into a task
winnable by construction, in minutes. V1 grades a patch offline. V3
connects them through the engine seam: `attempt TASK -- COMMAND...` runs an
attempt command against a task, preserves its patch and transcript *before*
cleanup, and grades the preserved patch offline — so a contributor can
invoke an attempt and see what happened, without waiting for the real
engine.

This is the first phase where the engine seam is exercised. The seam is an
executable command; a fake command satisfies the same seam (the real engine
arrives in V4, `satyrn-engine attempt`, in the same slot). Grading runs no
model and no network; the verdict comes from the oracle hook, never stdout
or an exit code.

Settled and not reopened: the phase list, the diagnosis-before-claims
split, the two selection rules, the capture-record and receipt shapes, and
the oracle hook. This spec only fixes how those rules apply to V3's
artifacts.

## Done-when

- `satyrn-evals attempt TASK -- COMMAND...` runs the command in a
  disposable workspace at the task's base, persists its patch and
  transcript *before* cleanup, grades the persisted patch offline, and
  writes both a receipt and an attempt record — in one invocation.
- The command reports through reserved env-var paths
  (`SATYRN_ATTEMPT_PATCH`, `SATYRN_ATTEMPT_TRANSCRIPT`); a command that
  writes no patch is refused (`NO_PATCH`), never a clean pass (the
  silent-zero defense, `BRIEF.md` rule 4's philosophy reused).
- The command's exit code is recorded but never determines the outcome
  (the artifact-driven seam).
- A fake command that writes the bundled task's known-good patch grades
  `pass` through the real path, asserting the fixture by name; a fake
  command writing the known-broken patch grades `fail` (the evidence
  floor, `BRIEF.md` rule 2).
- Refusal is the default outcome of most failures and is never silent:
  `NO_PATCH`, `PATCH_INVALID`, `TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY`
  each write an attempt record naming a precise `code`, and each refusal
  test has a sibling success test (`CLAUDE.md` rule 6).
- Default tier green with the spawn tripwire active; `ruff` and `pyrefly`
  clean; integration tier green.

## Decisions from the brainstorm

1. **The seam is reserved env-var paths** — evals reserves
   `SATYRN_ATTEMPT_PATCH` and `SATYRN_ATTEMPT_TRANSCRIPT` inside the
   freshly-created attempt directory (guaranteed absent, so a silent
   command leaves *no* file), passes `SATYRN_TASK_NAME` and
   `SATYRN_TASK_CONTRACT` as inputs, and the command writes its patch and
   transcript to those paths. This applies the same structural silence detection as the oracle hook
   (a missing file is a refusal, never a pass) and matches the glossary's
   "attempt command ... produces a patch" — the delivery is a patch, not a
   working-tree diff (decision 6).
2. **Auto-grade in the same invocation** — `attempt` runs the command,
   persists patch + transcript, then immediately grades the persisted
   patch through `grade()` (apply → oracle → hook result → verdict →
   receipt). Re-grading stays possible because the receipt's
   `patch_digest` names the exact input.
3. **The attempt record** — the new durable artifact, parallel to the
   capture record: the exit code stays coarse, the record is precise. It
   references the receipt by path and repeats the verdict at top level.
4. **Artifact-driven outcome** — the command's exit code never determines
   the outcome; it is recorded as diagnostic context only. A command that
   cannot *start* (any `OSError` from `subprocess.run`) is a usage error
   (exit 2, no record): the command is user input, like `--repo not a git
   repository` in capture.
5. **Refusal is preservation failure; unavailable is grading failure** — a
   missing/empty/invalid patch or a missing/empty transcript is a refusal
   (no receipt; nothing complete to grade). A well-formed patch that
   doesn't apply, touches non-allowlisted paths, or yields no trustworthy
   hook result is `attempted` with verdict `unavailable`, the receipt
   naming the cause — `BRIEF.md` rule 3's "capture is separate from
   grading."
6. **The delivery model** — evals grades the patch the command *delivered*
   (the file it wrote to `SATYRN_ATTEMPT_PATCH`), not a diff of the
   workspace. The workspace is scratch; only the delivered artifacts are
   preserved and graded.

## CLI surface

```
satyrn-evals attempt TASK [--tasks-root DIR] [--output DIR] -- COMMAND...
```

- `TASK` — a task name (bundled, or under `--tasks-root`), resolved exactly
  as `grade`'s.
- `--tasks-root DIR` — default: the bundled tasks root.
- `--output DIR` — the directory under which the attempt directory is
  created; default `./attempts/`.
- `-- COMMAND...` — the attempt command (executable + args). The `--` is
  required and separates evals' own flags from the command; everything
  after the first `--` is the command verbatim.

The CLI splits `argv` at the first `--` itself rather than relying on
`argparse.REMAINDER`, which greedily swallows options appearing after
`TASK` (verified: `attempt t --tasks-root R -- fake.py` would leave
`tasks_root` at its default and hand `--tasks-root R` to the command). A
missing `--` or an empty command is a usage error (exit 2).

Attempt is silent over the CLI: artifacts, not stdout. The attempt record
and receipt are the output.

## Exit codes

| Code | Meaning | Artifact |
|------|---------|----------|
| 0 | attempted and graded; verdict `pass` or `fail` | attempt record + receipt |
| 2 | usage error — unknown task, missing/empty command, command cannot start | none |
| 3 | refusal (`NO_PATCH`, `PATCH_INVALID`, `TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY`) or verdict `unavailable` | attempt record (+ receipt only when graded) |

The attempt record's `outcome`/`code` and the receipt's `verdict` are
authoritative; the exit code is coarse, matching `grade` and `capture`.

## Data shapes

**Attempt directory** — `<output>/<task>-<timestamp>/`, the timestamp UTC
with microsecond resolution. A same-microsecond collision is practically impossible given single-user,
human-invoked attempts; V5's loop revisits layout:

```
patch.diff        # the delivered patch, when the command wrote one
transcript.txt    # the delivered transcript, when the command wrote one
receipt.json      # written only when graded
attempt.json      # always
```

**Attempt record** (`attempt.json`) — attempted:

```json
{
  "version": 1,
  "outcome": "attempted",
  "code": "OK",
  "message": "attempt recorded and graded",
  "task": "format_number",
  "command": ["fake_attempt.py", "--good"],
  "command_exit": 0,
  "patch_path": "patch.diff",
  "transcript_path": "transcript.txt",
  "patch_digest": "…",
  "transcript_digest": "…",
  "verdict": "pass",
  "receipt_path": "receipt.json"
}
```

Refused keeps the same shape with `outcome: "refused"`, a precise `code`,
`verdict` and `receipt_path` null, and `patch_path`/`transcript_path` null
for an artifact that never existed. `command_exit` is always present (an
integer) — a record is only written after the command ran; a command that
cannot start is a usage error with no record. **Artifacts that exist are
persisted even on refusal** (e.g. `NO_PATCH` still persists the
transcript), so the record names exactly what was preserved.

The receipt is reused unchanged (`receipt.py`); the record references it
and repeats the verdict. `patch_digest` is the sha256 of the persisted
`patch.diff` — the same value the receipt records, one source, no drift.

## Refusal codes

| code | condition |
|------|-----------|
| `NO_PATCH` | the command wrote no patch, or a patch with no non-whitespace content |
| `PATCH_INVALID` | the patch is non-empty but not a parseable unified diff |
| `TRANSCRIPT_MISSING` | the command wrote no transcript |
| `TRANSCRIPT_EMPTY` | the transcript has no non-whitespace content |

Checks run in order — patch (`NO_PATCH`, `PATCH_INVALID`), then transcript
(`TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY`) — and the first failure refuses.
Apply-failure and non-allowlisted patches are *not* refusals: they flow
through `grade()` to verdict `unavailable` (decision 5).

## Mechanics

```
resolve task → load manifest
create attempt dir <output>/<task>-<microsecond UTC timestamp>
reserve patch/transcript paths inside it (never created; a silent command leaves no file)
copytree base → disposable workspace
run COMMAND (cwd=workspace, env = os.environ + SATYRN_TASK_NAME + SATYRN_TASK_CONTRACT
              + SATYRN_ATTEMPT_PATCH + SATYRN_ATTEMPT_TRANSCRIPT;
              PATH prepended with the interpreter's dir, as grade/capture do)
  → OSError (not found, not executable, wrong format, …): usage error (exit 2);
    remove the now-empty attempt dir so a usage error writes nothing
record the command's exit code as `command_exit` (never trusted)
read patch + transcript from the reserved paths (patch as text for the parse
  check and as bytes for the digest; transcript as UTF-8 text, errors=replace,
  for the emptiness check and as bytes for the digest)
decide: NO_PATCH / PATCH_INVALID / TRANSCRIPT_MISSING / TRANSCRIPT_EMPTY →
  refuse (persist what exists, write the refused record)
remove workspace (the delivered artifacts live in the attempt dir, outside it)
grade(task_dir, patch, attempt_dir/receipt.json) → receipt (pass/fail/unavailable)
write the attempt record (after the receipt; references it)
```

The refusal decision is a pure function
(`decide_refusal(patch_text, transcript_text) -> str | None`; an input of
`None` means the file was absent, a return of `None` means no refusal —
proceed to grade), default-tier testable without subprocess. The command's
runtime exit code is recorded as `command_exit`, but no code path branches
on it.

Environment boundaries: V3 inherits the caller's environment plus the seam
variables. Repo-local routing-variable stripping (capture's `_clean_env`)
and a git worktree for the attempt are a V4 concern, when the real engine's
needs are known — not built ahead of the contract.

## Test layout

**Default tier** — no model, no network, no subprocess (tripwire):
- `decide_refusal` as a pure function, with siblings: each refusal and the
  proceed case;
- attempt-record construction (attempted and refused shapes, nulls, digest
  derivation);
- attempt-directory naming (task + timestamp, deterministic given a fixed
  `when`);
- CLI `--` splitting (command verbatim, flags-before-`--` still parsed,
  missing `--` and empty command are usage errors) and exit-code mapping.

**Integration tier** (`pytest -m integration`, real subprocess): a
committed `fake_attempt.py` fixture honoring the env seam, with a flag for
each behavior:
- success: writes the bundled `format_number` known-good patch → verdict
  `pass`, artifacts persisted, record written, exit 0 — the fixture named
  (evidence floor);
- known-broken patch → verdict `fail`; a patch that doesn't apply →
  `unavailable`; a non-allowlisted patch → `unavailable`;
- siblings: no patch (`NO_PATCH`), invalid patch (`PATCH_INVALID`), no
  transcript (`TRANSCRIPT_MISSING`), empty transcript
  (`TRANSCRIPT_EMPTY`), nonzero exit with valid artifacts → still
  attempted + graded (proves artifact-driven), command not found → exit 2.

The fake command is a test double (lives under `tests/integration/`, not in
the wheel); nothing engine-shaped ships.

## File layout

```
src/satyrn_evals/
  cli.py            attempt subcommand, -- splitting, exit codes
  attempt.py        NEW: orchestrate run/preserve/grade/record; decide_refusal
  attempt_record.py NEW: attempt record shape, write/read
  (unchanged)       grade.py, receipt.py, manifest.py, patch.py, verdict.py,
                    capture.py, capture_record.py, oracle_hook.py,
                    errors.py (attempt reuses UsageError/ManifestError;
                    refusals return records, not exceptions)
tests/
  test_attempt.py                default tier
  integration/fake_attempt.py    the fixture command
  integration/test_attempt.py    integration tier
```

## Concept budget

Defined now: **attempt record** (the durable artifact `attempt` writes —
parallel to the capture record). "Attempt command" and "preservation" were
already in the glossary marked "lands in V3" and land now. No other new
terms; the README's "disposable worktree" prose reads as "workspace" here
(a temp copy of base, not a git worktree) — noted, not renamed.

## Out of scope (deferred, with the phase that reopens each)

- the baseline probe and discriminating power — V4/V5 (needs a real engine
  and loop machinery; a fake command's baseline carries no signal)
- the real engine seam (`satyrn-engine attempt`) — V4
- the diagnostic loop (`run --n 8`) and summary — V5
- repo-local env stripping and a git worktree for the attempt — V4, when
  the engine's needs are known
- transcript *format* (structured tool-call records) — V4/V5; V3 treats the
  transcript as opaque bytes (digest only), no machinery ahead of the
  contract
- command stdout/stderr capture, retry, repair, security sandbox — outside
  V3, matching E3's scope guard
- wall-clock comparisons — never (`BRIEF.md`; summaries use counts)
