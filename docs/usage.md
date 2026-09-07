# CLI reference

The CLI ships eight commands: `grade`, `capture`, `attempt`, `run`,
`summarize`, `regrade`, `session`, and `census`. This page is the complete
interface reference. For outcome-oriented instructions, use the
[guides](guides/index.md); for a first successful result, use the
[tutorial](tutorials/see-one-verdict.md). The [glossary](glossary.md) is
optional lookup material.

## grade

Apply a patch to a bundled {term}`task`'s base state, run the
task's oracle, and record the {term}`verdict` in a
{term}`receipt` — offline and deterministically, with no model and no
network.

```console
satyrn-evals grade TASK PATCH [--receipt PATH] [--tasks-root DIR]
```

- `TASK` — a {term}`task` name. `format_number` is the first bundled task:
  a small pure-Python function task with known-good and known-broken
  fixture patches.
- `PATCH` — path to a unified-diff patch file.
- `--receipt PATH` — where the {term}`receipt` is written; default `receipt.json`
  in the current directory.
- `--tasks-root DIR` — where to find tasks; default: the bundled tasks that
  ship in the wheel. Point it at a captured-task directory to grade a
  capture record's output.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Grading completed; the {term}`receipt` says `pass` or `fail` |
| 2 | Usage error — unknown task, unreadable patch, bad arguments |
| 3 | Operational failure — the {term}`receipt` says `unavailable` and names the cause |

The {term}`verdict` never comes from stdout or the exit code. Read the
{term}`receipt`.

The {term}`receipt`'s fields — and the {term}`hook result` embedded as
`evidence` — are documented in [task and artifact
formats](reference/formats.md#receipt).

### Example

```console
$ satyrn-evals grade format_number known-good.patch --receipt r.json
$ echo $?
0
$ python -c "import json; print(json.load(open('r.json'))['verdict'])"
pass
```

A patch that does not apply, or an oracle that produces no
trustworthy {term}`hook result`, records `unavailable` and exits 3 — never
a clean zero that proved nothing.

## capture

Turn a real fixing commit in a repository into a {term}`task` — manifest,
base state, and a known-good patch — winnable by construction, in
minutes. The task's base is the fix's parent tree; the known-good patch is
the fix diff restricted to non-test source paths; the oracle
runs only the tests that fail at base and pass with the fix (the
discriminating set).

```console
satyrn-evals capture --revert SHA [--repo PATH] [--name NAME] [--contract TEXT] [--output DIR]
```

- `--revert SHA` — the fixing commit. Required.
- `--repo PATH` — the source repository; default: the current directory. Its
  pre-existing files, index, branch, and `HEAD` are never changed.
- `--name NAME` — the task directory name; default: a slug of the fix
  commit's subject line.
- `--contract TEXT` — the task statement; default: the fix subject line.
- `--output DIR` — where the task directory and capture record are written;
  default `./tasks/`. These declared artifacts are the sole permitted writes
  when the output directory is inside the source repository. A source-local
  output must contain no tracked path; the repository root and Git metadata
  directories are rejected.

Four deterministic checks run during capture (source preflight, base
oracle runs, un-done at base, winnable); a failed check refuses with a
precise `code` in the capture record. Exit codes: `0` captured,
`2` usage error, `3` refusal.

The capture record — `<output>/<name>.capture.json`, its fields, and
its refusal codes — is documented in [task and artifact
formats](reference/formats.md#capture-record); the exit code stays coarse by
design.

Grade a captured task with `--tasks-root`:

```console
$ satyrn-evals capture --revert <sha> --repo /src/app --output tasks
$ satyrn-evals grade --tasks-root tasks fix-off-by-one tasks/fix-off-by-one/fixtures/known-good.patch
```

## attempt

Run an {term}`attempt command` against a {term}`task` in a clean detached
worktree reconstructed from the task base, preserve the patch and transcript
the command delivers, and grade the preserved patch offline.

```console
satyrn-evals attempt TASK [--tasks-root DIR] [--output DIR] [--rung KEY] [--timeout SECONDS]
    [--max-repeated-calls N] -- COMMAND...
```

- `TASK` — a {term}`task` name (bundled, or under `--tasks-root`), resolved
exactly as `grade`'s.
- `--tasks-root DIR` — where to find tasks; default: the bundled tasks that
ship in the wheel.
- `--output DIR` — the directory under which the attempt directory is
created; default `./attempts/`.
- `--rung KEY` — which contract rung from the manifest's `contracts`
map to export as `SATYRN_TASK_CONTRACT`; default: the manifest's `contract`.
An unknown key, or `--rung` against a task with no `contracts`, is a usage
error naming the available keys. **The command never sees `--rung`** — the
rung reaches it only as the exported contract text.
- `--timeout SECONDS` — a positive finite command deadline; default `900`.
- `--max-repeated-calls N` — stop the command after `N` identical
consecutive tool calls; **off by default**. A spending rule, not a nudge:
the command is torn down exactly as the timeout tears it down and is sent
nothing, so a bare arm stays bare. The cell records
`REPEAT_LIMIT` — deliberately not `NO_PATCH`, because a cell that was
stopped is not the same event as one that refused on its own. The limit a
batch used is recorded on every attempt record. It reads the transcript as
the command writes it, so it applies to any adapter that writes one.
- **`MODEL_ERROR`** is recorded when the preserved transcript shows the
inference substrate failed underneath a well-formed request — a 5xx from
the model server, or a runtime fault such as a GPU out-of-memory — and the
attempt delivered no patch. It is its own outcome code rather than
`NO_PATCH` because an infrastructure failure counted as a refusal
understates the arm; that defect voided a whole probe. **`n` stays
intact** and the cell is reported, never dropped: excluding it from a
success count is the maintainer's call. A 4xx is *not* a model error — the
server answered and rejected the input on its own terms (a context
overflow is the case on record), which is genuine pathology and stays in
the denominator. A cell that *did* deliver a patch is graded normally even
if its final turn errored.
- `-- COMMAND...` — the {term}`attempt command`: an executable plus its
arguments. The `--` is required and separates evals' own flags from the
command; everything after the first `--` is the command verbatim. A missing
`--` or an empty command is a usage error.

The command runs once in a clean detached Git worktree at the exact synthetic
base commit. Evals owns and removes the private repository and linked worktree.
The command receives the inputs `SATYRN_TASK_NAME` and
`SATYRN_TASK_CONTRACT` and the
reserved delivery paths `SATYRN_ATTEMPT_PATCH` and
`SATYRN_ATTEMPT_TRANSCRIPT` in its environment. The delivery paths sit
inside the attempt directory and are never created up front — a silent
command leaves no file, which is refused, never a clean pass. The command
writes its patch to `SATYRN_ATTEMPT_PATCH` and its transcript to
`SATYRN_ATTEMPT_TRANSCRIPT`. **The command's cwd is a temporary detached worktree,
so the command's own paths — its script, its `--patch` argument — must be
absolute; relative paths inside the command resolve there.**
`--output` is different: evals resolves it itself, so a relative
`--output` is fine. The delivery paths handed to the command derive from
it and are always absolute — the command's cwd being elsewhere does not
matter for them.

If the task manifest declares `engine_contract`, evals validates its safe
task-relative path without parsing the file, then appends its absolute path to
the command. A task **without** the field gets a contract generated from its
own manifest plus the selected rung, written once under the output root at
`engine-contracts/<sha256 of the rendered bytes>.yaml`, whose absolute path is
appended the same way. Either way an Engine command prefix ends with its own
literal `--`; evals supplies the final contract argument.

The generated path is keyed by content, not by attempt, on purpose: a fresh
path per attempt would change each cell's recorded command, and a summary
refuses mixed commands, so the batch would not summarize. Two cells at the
same rung therefore record the same command; two cells at different rungs
record different ones and are correctly refused as one batch. The rendered
shape and the `writable_paths` derivation are in
[task and artifact formats](reference/formats.md#the-generated-engine-contract).

The record names what the model was shown: `rung` (null for the default
contract) and `contract_digest`, the sha256 of the exact exported text. A
`run` carries the same two fields on its summary and refuses a batch whose
cells disagree.

On POSIX, timeout handling terminates and reaps the command process group
before removing the worktree. Cleanup that cannot be confirmed becomes
`CLEANUP_FAILED`, and `attempt.json` names the retained path. The command is
trusted and runs with the user's permissions; the worktree is not a security
sandbox. Windows is outside the V4 proof.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Attempted and graded; the attempt record says `verdict: pass` or `fail` |
| 2 | Usage error — unknown {term}`task`, missing/empty command, command cannot start |
| 3 | Artifact, workspace, timeout, or cleanup refusal; or verdict `unavailable` |

The attempt record and the {term}`receipt` — not the exit code — are
the result. The exit code is coarse by design.

The attempt directory and the attempt record — its fields, the
refusal codes, and the refusal/`unavailable` distinction — are documented in
[task and artifact formats](reference/formats.md#attempt-directory-and-record).

### Example

```console
$ ROOT="$(pwd)"
$ satyrn-evals attempt format_number --output "$ROOT/attempts" \
    -- python "$ROOT/tests/integration/fake_attempt.py" \
    --patch "$ROOT/src/satyrn_evals/tasks/format_number/fixtures/known-good.patch"
$ echo $?
0
```

Verdict `pass` — read the attempt record or the {term}`receipt` in
the attempt directory. Every path the command touches is absolute: its cwd
is a disposable worktree.

For the bundled Engine-capable task:

```console
$ satyrn-evals attempt format_number --timeout 30 -- \
    uv run --project /src/satyrn-engine satyrn-engine attempt \
    --model=MODEL --
```

Evals appends `engine-contract.yaml`; Engine writes the patch and transcript
through the same reserved artifact paths used by the fake command. For a task
with no `engine_contract` field, evals appends the contract it generated for
the selected rung instead:

```console
$ satyrn-evals attempt agentclinic-repair-plausible-wrong-fix --rung R1 \
    --output "$ROOT/attempts" -- uv run --project /src/satyrn-engine \
    satyrn-engine attempt --model=MODEL --
```

## run

Repeat an {term}`attempt command` for one {term}`task`, preserving each
attempt and writing a counts-only diagnostic summary. `run` uses the
same command seam, worktree isolation, artifact preservation, and offline
grading as `attempt`; it adds repetition and aggregation, not another engine
integration.

```console
satyrn-evals run TASK --n N [--rung KEY] [--tasks-root DIR] [--output DIR] [--timeout SECONDS]
    [--max-repeated-calls N] -- COMMAND...
```

- `TASK`, `--tasks-root`, `--timeout`, `--max-repeated-calls`, and
  `-- COMMAND...` have the same
  meaning as for `attempt`.
- `--n N` — required positive number of planned attempts. State it explicitly
  so the recorded denominator is deliberate rather than inherited from a
  command default.
- `--rung KEY` — as for `attempt`, applied to every cell. An unknown rung is
  refused **before the first attempt**, so the refusal preserves nothing and
  is fixed by repairing the flag and re-running.
- `--output DIR` — directory containing the individual attempt directories
  and the run's `summary.json`; default `./runs/`.

`run` completes all `n` attempts, including refusals, then writes
`<output>/summary.json` — its fields are documented in [task and artifact
formats](reference/formats.md#run-summary). The summary is the authoritative
result: exit code `0` means the loop and summary write completed, regardless
of individual verdicts or refusals; `2` is a usage error and `3` means the
loop could not complete.

`summary.json` is written only by a completed run. If the loop stops early
— an exception or Ctrl-C — `run` writes `<output>/aborted.json` instead
(requested/completed counts, the error, and the partial tallies) and never
writes `summary.json`, so a partial batch cannot be mistaken for a
completed short run.

For example:

```console
$ satyrn-evals run local-pings --n 1 --timeout 900 --output runs/engine -- \
    /src/satyrn-engine/.venv/bin/satyrn-engine attempt
```

The example uses `local-pings`, a bundled fixture task suitable for smoke or
regression use. A result intended to evaluate an engine change needs its
condition qualified and frozen outside the `run` command.

The summary includes the currently supported, schema-aware pathology counts.
Broader tool-call, repeat, churn, and context telemetry remains deferred until
an engine-side emitter can supply it without Evals parsing a private transcript
format.

## summarize

Rebuild `summary.json` for a completed run output directory from the
preserved attempt records. Uses the same tally as `run`, so the rebuilt
file matches the run's own byte-for-byte.

```console
satyrn-evals summarize OUTPUT_DIR [--tasks-root DIR]
```

- `OUTPUT_DIR` — a run output directory: `<task>-<stamp>` attempt
  directories, each with an `attempt.json`, plus the run's `summary.json`.
- `--tasks-root DIR` — task root; default the bundled tasks.

The rebuild is anchored on the exact cells the run's `summary.json` names:
a stray sibling directory or an un-appended crash cell never changes the
rebuilt artifact. A directory whose run aborted is refused — an aborted
run writes `aborted.json` (requested/completed/error plus the partial
tallies), never `summary.json`.

Exit codes: `0` — summary written; `2` — not a directory, not a run output
directory (no `summary.json`), unknown task, or a moved cell; `3` — the
batch aborted (see `aborted.json`), an anchor, record, or receipt that
exists but cannot be read, a named cell missing from disk, or inconsistent
identity across cells.

## regrade

Re-run the grader over one preserved attempt's patch and rewrite its
receipt and record — re-scoring without re-running the attempt.

```console
satyrn-evals regrade ATTEMPT_DIR [--tasks-root DIR]
```

- `ATTEMPT_DIR` — an attempt directory holding `attempt.json`,
  `patch.diff`, and the preserved transcript.
- `--tasks-root DIR` — task root; default the bundled tasks.

A `GRADE_FAILED` or `OK` record is re-graded and its record updated to
`OK` with the new verdict. A refusal record has nothing to grade — a note
is printed and the command exits `0`. Exit codes: `0` — graded pass or
fail (or nothing to grade); `2` — not an attempt directory, identity
mismatch, or unknown task; `3` — verdict unavailable or an unreadable
record.

## session

Drive one ordered conversation through an adapter, retain a checkpoint after
each reached prompt, and grade those saved checkpoints offline. Session is a
separate interface for adapters that implement its event protocol; it is not a
replacement for `attempt` or `run`.

```console
satyrn-evals session TASK [--tasks-root DIR] [--output DIR]
    [--start-timeout SECONDS] [--step-timeout SECONDS]
    [--close-timeout SECONDS] -- ADAPTER...
```

- `TASK` and `--tasks-root DIR` identify the task as for `attempt`.
- `--output DIR` stores the session directory; default `./sessions/`.
- `--start-timeout SECONDS`, `--step-timeout SECONDS`, and
  `--close-timeout SECONDS` bound adapter start, each prompt, and graceful
  close; their defaults are 60, 600, and 30 seconds.
- `ADAPTER...` is the required executable adapter command. Everything after
  `--` is passed to it verbatim.

Every session that starts writes `session-record.json`, including adapter,
timeout, and cleanup failures. The record and its retained checkpoint patches,
snapshots, transcript, and receipts—not adapter stdout or exit status—are the
evidence to inspect. Exit `3` reports workspace, cleanup, or grading
unavailability; other terminal product outcomes still leave their record.

## census

Scan retained run transcripts for named pathologies. It is a diagnostic view
over existing evidence: it launches no attempt command, grades nothing, and
does not establish a verdict or an evaluation conclusion.

```console
satyrn-evals census RUNS_ROOT [RUNS_ROOT ...] [--json PATH]
```

- `RUNS_ROOT` — one or more run-output roots to scan.
- `--json PATH` — optionally write the full per-cell census record.

The observed-file denominator is the `transcript.txt` files that exist below
the supplied roots; a missing transcript creates no census cell and is not
silently counted as zero. For an existing transcript outside the supported
vocabulary, `v10_unmeasured` makes that limit explicit. Other detector zeros
describe only the files scanned, not proof that absent evidence is clean.
