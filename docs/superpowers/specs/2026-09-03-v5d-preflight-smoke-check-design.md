# V5d — The pre-flight smoke check: design spec

**Phase:** V5d (`ROADMAP.md`). **Date:** 2026-09-03 (revised).
**Status:** proposal, revised and posted for confirmation per `CLAUDE.md`.
Supersedes the proposal at commit `9893d40` (branch
`v5d-realmodel-smoke-check`, cut from pre-close-out history `36d7974`),
which carried stale statements. No new machinery ships until confirmed.

## Revision (2026-09-03, maintainer review)

The proposal was carried onto current history and amended on four points:

1. **Stale re-probe statements corrected.** The re-probe is complete and
   its record merged: both arms ran at n=8 on the captured task and read
   middle — Baseline 3/8, Engine 4/8
   (`docs/superpowers/research/2026-09-03-local-pings-reprobe-protocol.md:216-231`),
   and the maintainer de-admitted `local-pings` as a diagnostic workload
   while retaining it as a bundled grader/smoke/regression fixture
   (`docs/superpowers/research/2026-09-03-local-pings-deadmission.md:8-10`).
2. **`NO_PATCH` and `COMMAND_TIMEOUT` are not automatic smoke passes.**
   They pass only with positive evidence that the model actually started
   (below). Without it they are indistinguishable from contract-load or
   argv failures — exactly how the two recorded defects presented — and
   an automatic pass would conceal them.
3. **Refusals have no receipt.** The checklist reads `attempt.json`
   always, and the receipt only when grading occurred
   (`src/satyrn_evals/attempt.py:204-241`).
4. **Smoke is scoped per materially distinct command/adapter/runtime
   path**, not merely once per task. A new prospective read/write Envelope
   adapter (a new prospective arm, not a reproduction — de-admission
   record `:41-44`) needs its own uncounted smoke even though
   `local-pings` already exercised the Engine path.

### Second revision (2026-09-03, maintainer review)

5. **Wording — a new prospective read/write Envelope, not a canonical
   one.** The historical canonical Envelope is unreconstructable
   (de-admission record, reconstruction stop), so this proposal's
   "canonical-Envelope adapter/probe" phrasings are replaced with "new
   prospective read/write Envelope" throughout.
6. **Smoke evidence is durable.** The practice's example output directory
   is no longer `/tmp/smoke` (ephemeral); smoke writes to a durable,
   uniquely named evidence directory whose path is recorded with the
   outcome, so it survives cleanup and can be re-graded.
7. **Completion at landing, not at the next captured task.** Waiting for
   "the next captured task" would leave V5d open indefinitely and could
   encourage capturing a task merely to close the phase. V5d completes
   when the confirmed practice lands; the next captured task must follow
   it, and any failure to do so reopens V5d.

## What V5d ships

A documented practice, not new code: before a materially distinct
real-model execution path is first used for a real diagnostic run, run one
real-model attempt (`run TASK --n 1 -- REAL_COMMAND`) against the task and
read the attempt record — always — plus the receipt when grading occurred,
checking a short, specific list of failure shapes before trusting anything
downstream. This is the smoke step V5b's `run` already makes possible and
the re-probe already pre-registered
(`2026-09-03-local-pings-reprobe-protocol.md:89-93`); V5d is the checklist
for when to run it and what a pass means, not a new command.

- **CLI surface:** none. `run` already exists (V5b).
- **Exit codes:** none.
- **Data shapes:** none. The check reads the existing attempt record and,
  when present, the receipt; nothing new is written.
- **Test layout:** none. This is deliberately not automated — see
  Out of scope.

## The problem

Two real defects in one captured task each reached the point of costing a
real attempt before anything caught them. Both were caught by the
re-probe's own smoke step — one uncounted `--n 1` attempt per arm, run
before the budgeted arms per the pre-registered protocol
(`2026-09-03-local-pings-reprobe-protocol.md:89-93`) — and the smoke
findings record names the shapes (`:155-186`):

1. **`local-pings`'s `engine-contract.yaml` was invalid YAML.** An
   unquoted `task:` value containing `": "` made the scalar ambiguous;
   the engine's own `check` refused the contract as
   `CONTRACT_INVALID_YAML` (exit 4) before any model ran
   (`2026-09-03-local-pings-reprobe-protocol.md:160-163`). `manifest.py`
   validates only the `engine_contract` *path*, never its content
   (`BACKLOG.md`, "Engine-contract content is never validated"), and
   V5c's done-when exercised `run` through a fake seam command, which
   never loads the contract. Caught by the smoke's first engine attempt
   and fixed by quoting the value (commits `8904429`, `d03e346`; the
   pre-fix contract is verifiable at `8904429^`, see Evidence below).
   *Correction note:* the earlier proposal (`9893d40`) and the BACKLOG
   entry dated this fix 2026-09-02; the commit record and the smoke
   findings both date it 2026-09-03 (commit `d03e346` adds the findings
   section). This spec follows the commit record.
2. **The Engine composite's `pi` child argv is incompatible with stock
   `pi`.** `satyrn-engine` builds `--model=VALUE` (equals form); `pi`
   0.80.10 through 0.84.4's hand-rolled parser only matches the literal
   token `--model` and rejects the equals form as an unknown option. Found
   in the same smoke episode, before the budgeted arms ran
   (`2026-09-03-local-pings-reprobe-protocol.md:164-176`), and verified
   directly against those pi builds; the re-probe ran the engine under a
   recorded argv-compat shim named `pi` (`:169-180`). This is a
   `satyrn-engine` backlog finding, not fixed here.

Neither is catchable by the default or integration tiers as they stand:
(1) is a schema `manifest.py` doesn't own and evals declares no YAML
parser to check (`BACKLOG.md`, same entry); (2) is an interaction between
the engine's argv construction and a specific `pi` build that only
manifests when a real `pi` process actually parses the arguments — no fake
seam reaches it.

## The practice

For each materially distinct real-model execution path, once, at that
path's first real use — after `capture`, before treating the path as ready
for `run --n 8` against a real arm:

```bash
satyrn-evals run TASK --n 1 --output "$SMOKE_OUTPUT" -- REAL_COMMAND
```

`SMOKE_OUTPUT` is a durable, uniquely named evidence directory — never
`/tmp`, where a smoke record would vanish before a defect review. Follow
the project's durable-scratch pattern (the re-probe's
`~/projects/pauleveritt/satyrn-v5c-scratch/runs/smoke-<task>-<path>-<date>/`)
and record the path with the smoke outcome so the evidence survives
cleanup and can be re-graded offline.

**Read the resulting `attempt.json` — always.** It is written for every
refusal and success (`src/satyrn_evals/attempt.py:200-241`) and records
the outcome, the attempt code, the command exit, and the patch/transcript
presence and digests. **Read the receipt only when grading occurred.**
Refusals write no receipt: the refused record carries `receipt_path: null`
and `grade` never runs (`src/satyrn_evals/attempt.py:204-221`); grading
and `receipt.json` happen only in the attempted branch (`:222-241`). The
recorded engine-smoke directory is the shape — `attempt.json` and
`transcript.txt` only, no `receipt.json` (Evidence below).

**Smoke fails** — stop, fix, do not proceed to a budgeted run — on any of:

- the command exits before the model runs at all (contract load, argv
  rejection, missing dependency, manifest error), recognized as a refusal
  with **no positive evidence that the model started** (below);
- a `NO_PATCH` or `COMMAND_TIMEOUT` **without positive evidence that the
  model actually started** — an empty or absent transcript, or (for
  `NO_PATCH`) a nonzero command exit. These codes are model behavior only
  when that evidence exists; without it they are indistinguishable from —
  and conceal — contract or argv failure (defect 1 exited 4 with no model
  output; defect 2's pi child never launched). They are **not** automatic
  passes;
- the attempt's `code` is not one the path should produce at the
  model-behavior stage (a plumbing code where model behavior was
  expected, or vice versa);
- the grade receipt itself fails to produce a verdict.

**Positive evidence that the model started** is the model's stream output
in the transcript: `transcript.txt` present and non-empty, holding real
stream content — not merely the command's own error text. For a
`NO_PATCH`, additionally the command exited normally (`command_exit` 0).
The recorded legitimate-refusal shape is exactly this: the engine smoke
attempt — `NO_PATCH`, `command_exit` 0, a 912,882-byte transcript, no
receipt (`2026-09-03-local-pings-reprobe-protocol.md:181-186`; scratch
`runs/engine-smoke/local-pings-20260903-114532-079942/`) — a model that
ran and refused by model behavior. Contract and argv failures exit nonzero
before any model stream exists.

**Smoke passes** on:

- an `OK` whose receipt carries a verdict (pass or fail) — grading ran
  offline and discriminated, and either verdict is model behavior, which
  is exactly what a budgeted run exists to measure; or
- a `NO_PATCH` with the positive evidence above — `command_exit` 0 and a
  non-empty transcript; or
- a `COMMAND_TIMEOUT` with the positive evidence above — a non-empty
  transcript where the path's harvest shape retains one through a kill.
  The command exit is never recorded on a timeout
  (`src/satyrn_evals/workspace.py:96-98` — `COMMAND_TIMEOUT` forbids
  `command_exit`), and whether a transcript survives a kill is a
  property of the path's harvest shape, not of the model: the baseline
  wrapper streams continuously, and its four recorded timeouts each
  retained a 0.4–1.8 MB transcript
  (`2026-09-03-local-pings-reprobe-protocol.md:217-223`); the engine
  composite writes its artifacts at completion, so its one recorded
  timeout retained none (`:224-231`, `:233-239`). A timeout without
  transcript evidence is unproven — consult the command's own log before
  blessing the path. Never auto-pass.

Passing does not certify the task's difficulty or its oracle, and for a
probe path it does not earn admission; it certifies that a real model can
reach the model-behavior stage on that path.

This is the same check the re-probe pre-registered and ran — "Smoke, one
`--n 1` per arm, results not counted — plumbing before budget"
(`2026-09-03-local-pings-reprobe-protocol.md:89-93`) — and it caught three
plumbing defects before the budgeted arms (`:155-186`). V5d records it as
a named practice so the next captured task, and each new path on an
existing task, gets it deliberately rather than by a contributor happening
to smoke-test first.

## Scope

Applies **once per materially distinct execution path**, at that path's
first real use — not per commit, not per CI run, not repeated once a path
has passed it. A materially distinct path is a distinct executable/seam
command with its own tool surface, adapter, or runtime: the re-probe
exercised two such paths on `local-pings` — the baseline wrapper and the
`satyrn-engine attempt` composite — each with its own uncounted smoke
(`2026-09-03-local-pings-reprobe-protocol.md:89-93`; the baseline smoke
outcome is recorded at `:210-212`, the engine's in the smoke findings).

**A path that has already had a budgeted real-model run against the task
does not need a smoke**; the budgeted run itself already exercised
everything smoke would check, at higher cost. Distinct paths do not share
a smoke. A new prospective read/write Envelope adapter — current Pi
restricted to the `read,write` surface under a new adapter, which the
de-admission record defines as a **new prospective arm, not a
reproduction**
(`docs/superpowers/research/2026-09-03-local-pings-deadmission.md:41-44`) — has
never run against `local-pings` (the recorded Envelope was a budget-only
variant of a broader tool surface,
`2026-09-03-local-pings-reprobe-protocol.md:27-32`) and is a materially
distinct path. Its first real use therefore includes its own uncounted
smoke, even though `local-pings` already exercised the Engine path.

**V5c impact — limited to process.** A new prospective read/write
Envelope admission probe — a newly preregistered qualifying probe under
the re-admission entry's condition (`BACKLOG.md`) — includes one
uncounted smoke under this rule before its budgeted attempts. That smoke validates the new adapter's
plumbing; it does not change V5c's recorded evidence (no recorded cell is
rerun or reinterpreted, de-admission record `:31`) and it does not itself
earn admission — admission is decided only by the preregistered probe's
recorded measurements. V5d neither reopens nor blocks V5c; no V5c result
needs rerunning.

## Why this is not automated

`CLAUDE.md:47-48`: no framework before three concrete implementations need
the same shape. One smoke episode caught three real plumbing defects for
the cost of a few uncounted attempts
(`2026-09-03-local-pings-reprobe-protocol.md:155-186`); that is evidence
the practice is worth naming, not evidence it is worth building a
harness for. A real-model attempt also costs real wall-clock time and,
depending on the model, real money — the reason to keep this manual and
narrowly scoped rather than folding it into the default or
integration tier, or running it on every capture regardless of whether the
task or path is about to be used.

## Out of scope (deferred, with what reopens each)

- **Automated engine-contract content validation** — a default-tier
  assertion that the contract parses under the engine's own loader,
  requiring evals to declare a parser dependency on the engine's schema.
  The BACKLOG entry's second reopen condition has fired: the re-probe's
  engine arm was the first real engine run on the captured task
  (`2026-09-03-local-pings-reprobe-protocol.md:224-231`), so the fuller
  fix is owed per that entry's own words; V5d's manual practice is a
  stopgap, not a replacement, and does not close the entry.
- **The `pi` argv incompatibility itself.** Recorded as a `satyrn-engine`
  backlog finding (`2026-09-03-local-pings-reprobe-protocol.md:164-176`),
  not fixed here; V5d only ensures it gets caught before a budgeted run,
  not that it stops recurring. *Reopens in `satyrn-engine`'s own backlog.*
- **Running smoke in CI or the default/integration tiers.** Explicitly
  rejected above — the cost is the reason this is a checklist, not a test.
- **A smoke record in the manifest** (e.g., "smoke-tested: true"). Schema
  change, out of V5d's declared scope; the practice is process, not data.
  *Reopens if a contributor loses track of which paths have been
  smoke-tested without one.*
- **Deciding `local-pings` re-admission or a new prospective read/write
  Envelope's admission.** The de-admission record and the
  re-admission/Envelope-recovery backlog entries are the maintainer's
  records; V5d does not decide them.

## Done-when

- This spec is committed, revised, and confirmed by the maintainer; the
  practice lands as an active practice on confirmation, not before.
- The practice is referenced from `BACKLOG.md`'s engine-contract entry as
  the interim mitigation.
- **Completion at landing.** V5d is complete when the maintainer confirms
  this spec and the practice lands — not when the next task captured after
  `local-pings` runs its smoke. Waiting for the next capture would keep
  the phase open indefinitely and could encourage capturing a task merely
  to close it. The next task captured after `local-pings` **must** follow
  this practice — its capture or reconstruction doc records whether smoke
  ran under it and what it found, even when the answer is "passed
  cleanly." A captured task that reaches a budgeted real-model run
  without its smoke, or a smoke that passes while concealing a defect,
  **reopens V5d**.

## Evidence and recomputation

Both defects cited above are independently reproducible without a model.
(1) is cross-repo — it needs a `satyrn-engine` checkout, path below is
this machine's, adjust for another:

```bash
# (1) the invalid contract, as it shipped before the fix in 8904429
git show 8904429^:src/satyrn_evals/tasks/local-pings/engine-contract.yaml \
  | uv run --directory /Users/pauleveritt/projects/pauleveritt/satyrn-engine \
    python -c "
import sys, tempfile
from pathlib import Path
from satyrn_engine.contract import load_contract
p = Path(tempfile.mktemp(suffix='.yaml')); p.write_text(sys.stdin.read())
load_contract(p)
"
# -> satyrn_engine.contract.ContractError: invalid YAML ...:
#    mapping values are not allowed here

# (2) the argv rejection, against a stock pi 0.80-0.84.x
#     (bypass the recorded compat shim if it is on PATH)
/path/to/stock/pi --model=anything
# -> Error: Unknown option: --model
```

The positive-evidence discriminator is checkable from the recorded smoke
records and the code path:

```bash
# the legitimate-refusal shape that passes smoke: NO_PATCH, command_exit 0,
# a non-empty transcript, and no receipt (refusals are never graded):
cat ~/projects/pauleveritt/satyrn-v5c-scratch/runs/engine-smoke/local-pings-20260903-114532-079942/attempt.json
ls -l ~/projects/pauleveritt/satyrn-v5c-scratch/runs/engine-smoke/local-pings-20260903-114532-079942/

# the no-receipt-on-refusal rule lives in the refused branch:
# src/satyrn_evals/attempt.py:204-221 (receipt_path null; grade never runs)
# grading and receipt.json happen only in the attempted branch: attempt.py:222-241
```
