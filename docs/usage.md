# Usage

V3 ships three commands: `grade`, `capture`, and `attempt`. See the
[glossary](glossary.md) for the vocabulary.

## grade

Apply a {term}`patch` to a bundled {term}`task`'s base state, run the
task's {term}`oracle`, and record the {term}`verdict` in a
{term}`receipt` — offline and deterministically, with no model and no
network.

```console
satyrn-evals grade TASK PATCH [--receipt PATH] [--tasks-root DIR]
```

- `TASK` — a {term}`task` name. `format_number` is the first bundled task:
  a small pure-Python function task with known-good and known-broken
  fixture patches.
- `PATCH` — path to a unified-diff {term}`patch` file.
- `--receipt PATH` — where the {term}`receipt` is written; default `receipt.json`
  in the current directory.
- `--tasks-root DIR` — where to find tasks; default: the bundled tasks that
  ship in the wheel. Point it at a captured-task directory to grade a
  {term}`capture record`'s output.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Grading completed; the {term}`receipt` says `pass` or `fail` |
| 2 | Usage error — unknown task, unreadable {term}`patch`, bad arguments |
| 3 | Operational failure — the {term}`receipt` says `unavailable` and names the cause |

The {term}`verdict` never comes from stdout or the exit code. Read the
{term}`receipt`.

### The receipt

```json
{
  "task": "format_number",
  "patch_digest": "251a3d81e289f932d69bb1d93116fda757f47b9dcbdb11e9bc68aab7dd687ebc",
  "verdict": "pass",
  "reason": "",
  "evidence": {
    "executed_test_ids": ["test_solution.py::test_large", "test_solution.py::test_negative"],
    "outcomes": {"test_solution.py::test_large": "passed", "test_solution.py::test_negative": "passed"},
    "counts": {"passed": 2, "failed": 0, "error": 0, "skipped": 0}
  }
}
```

`patch_digest` is the sha256 of the {term}`patch` file, so a {term}`receipt`
names the exact input it graded — re-scoreable without re-running anything.
`evidence` is the {term}`hook result` verbatim.

### Example

```console
$ satyrn-evals grade format_number known-good.patch --receipt r.json
$ echo $?
0
$ python -c "import json; print(json.load(open('r.json'))['verdict'])"
pass
```

A {term}`patch` that does not apply, or an {term}`oracle` that produces no
trustworthy {term}`hook result`, records `unavailable` and exits 3 — never
a clean zero that proved nothing.

## capture

Turn a real fixing commit in a repository into a {term}`task` — manifest,
base state, and a known-good {term}`patch` — winnable by construction, in
minutes. The task's base is the fix's parent tree; the known-good patch is
the fix diff restricted to non-test source paths; the {term}`oracle`
runs only the tests that fail at base and pass with the fix (the
{term}`discriminating set`).

```console
satyrn-evals capture --revert SHA [--repo PATH] [--name NAME] [--contract TEXT] [--output DIR]
```

- `--revert SHA` — the fixing commit. Required.
- `--repo PATH` — the source repository; default: the current directory. Its
  working tree, index, branch, and `HEAD` are never touched.
- `--name NAME` — the task directory name; default: a slug of the fix
  commit's subject line.
- `--contract TEXT` — the task statement; default: the fix subject line.
- `--output DIR` — where the task directory is written; default `./tasks/`.

Four deterministic checks run during capture (source preflight, base
oracle runs, un-done at base, winnable); a failed check refuses with a
precise `code` in the {term}`capture record`. Exit codes: `0` captured,
`2` usage error, `3` refusal.

### The capture record

```json
{
  "version": 1,
  "outcome": "captured",
  "code": "OK",
  "message": "task captured",
  "repo": "/src/app",
  "base_sha": "…",
  "fix_sha": "…",
  "task_dir": "tasks/fix-off-by-one",
  "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook", "test_solution.py::test_one"],
  "expected_test_ids": ["test_solution.py::test_one"],
  "check_outcomes": {
    "source_preflight": "passed",
    "base_oracle": "passed",
    "un_done_at_base": "passed",
    "winnable": "passed"
  }
}
```

The record is the authoritative result; the exit code is coarse by design.
A refusal writes the same shape with `outcome: refused` and a precise
`code` (e.g. `REPO_DIRTY`, `NO_DISCRIMINATING_TESTS`, `CLEANUP_FAILED`).

Grade a captured task with `--tasks-root`:

```console
$ satyrn-evals capture --revert <sha> --repo /src/app --output tasks
$ satyrn-evals grade --tasks-root tasks fix-off-by-one tasks/fix-off-by-one/fixtures/known-good.patch
```

## attempt

Run an {term}`attempt command` against a {term}`task` in a disposable work
copy of the task's base, preserve the patch and transcript the command
delivers, and grade the preserved patch offline — the engine seam exercised
end to end, with no model and no network.

```console
satyrn-evals attempt TASK [--tasks-root DIR] [--output DIR] -- COMMAND...
```

- `TASK` — a {term}`task` name (bundled, or under `--tasks-root`), resolved
exactly as `grade`'s.
- `--tasks-root DIR` — where to find tasks; default: the bundled tasks that
ship in the wheel.
- `--output DIR` — the directory under which the attempt directory is
created; default `./attempts/`.
- `-- COMMAND...` — the {term}`attempt command`: an executable plus its
arguments. The `--` is required and separates evals' own flags from the
command; everything after the first `--` is the command verbatim. A missing
`--` or an empty command is a usage error.

The command runs in a disposable temporary work copy of the task's base,
with the inputs `SATYRN_TASK_NAME` and `SATYRN_TASK_CONTRACT` and the
reserved delivery paths `SATYRN_ATTEMPT_PATCH` and
`SATYRN_ATTEMPT_TRANSCRIPT` in its environment. The delivery paths sit
inside the attempt directory and are never created up front — a silent
command leaves no file, which is refused, never a clean pass. The command
writes its patch to `SATYRN_ATTEMPT_PATCH` and its transcript to
`SATYRN_ATTEMPT_TRANSCRIPT`. **The command's cwd is a temporary work copy,
so relative paths inside the command resolve there — use absolute paths.**
The example below passes `--output` absolutely too: the delivery paths
handed to the command derive from it, and the command's cwd is elsewhere.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Attempted and graded; the {term}`attempt record` says `verdict: pass` or `fail` |
| 2 | Usage error — unknown {term}`task`, missing/empty command, command cannot start |
| 3 | Refusal (`NO_PATCH`, `PATCH_INVALID`, `TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY`) or verdict `unavailable` |

The {term}`attempt record` and the {term}`receipt` — not the exit code — are
the result. The exit code is coarse by design.

### The attempt directory

`<output>/<task>-<timestamp>/`, the timestamp UTC with microsecond
resolution:

```
patch.diff        # the delivered patch, when the command wrote one
transcript.txt    # the delivered transcript, when the command wrote one
receipt.json      # written only when graded
attempt.json      # always
```

### The attempt record

```json
{
  "version": 1,
  "outcome": "attempted",
  "code": "OK",
  "message": "attempt recorded and graded",
  "task": "format_number",
  "command": ["python", "…/tests/integration/fake_attempt.py", "--patch", "…/src/satyrn_evals/tasks/format_number/fixtures/known-good.patch"],
  "command_exit": 0,
  "patch_path": "patch.diff",
  "transcript_path": "transcript.txt",
  "patch_digest": "251a3d81e289f932d69bb1d93116fda757f47b9dcbdb11e9bc68aab7dd687ebc",
  "transcript_digest": "68b680be59b044860a88a04d273ef8df0a3482539ba133c8154d2c4880a56c17",
  "verdict": "pass",
  "receipt_path": "receipt.json"
}
```

The record is authoritative; the exit code is coarse. `command_exit` is
recorded as diagnostic context and never trusted — a command that exits
nonzero with complete artifacts is still attempted and graded. `patch_digest`
is the sha256 of the persisted `patch.diff`, the same value the
{term}`receipt` records — one source, no drift. A refusal keeps the same
shape with `outcome: refused`, a precise `code`, `verdict` and
`receipt_path` null, and `patch_path`/`transcript_path` null for an artifact
that never existed; artifacts that do exist are persisted even on refusal,
so the record names exactly what was preserved.

Refusal is a preservation failure; `unavailable` is a grading failure.
Refusal = the artifacts were incomplete (no patch / invalid patch / no
transcript / empty transcript) — no {term}`receipt`, nothing complete to
grade. `unavailable` = the patch was well-formed but couldn't be graded
(doesn't apply, touches non-allowlisted paths, no trustworthy {term}`hook
result`) — the receipt names the cause.

### Example

```console
$ ROOT="$(pwd)"
$ satyrn-evals attempt format_number --output "$ROOT/attempts" \
    -- python "$ROOT/tests/integration/fake_attempt.py" \
    --patch "$ROOT/src/satyrn_evals/tasks/format_number/fixtures/known-good.patch"
$ echo $?
0
```

Verdict `pass` — read the {term}`attempt record` or the {term}`receipt` in
the attempt directory. Every path the command touches is absolute: its cwd
is a disposable work copy.
