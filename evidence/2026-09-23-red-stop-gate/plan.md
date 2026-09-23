# Red-stop gate: send a follow-up when the model stops on a failing self-test

> **Outcome.** Implemented in satyrn-engine as `803df2d` on `release-one`
> (Revision 1 below is what shipped). The offline estimate recomputes with
> `uv run python evidence/2026-09-23-red-stop-gate/red_stop_scan.py` over
> `~/satyrn-runs`; the 92 / 64 / 1 below were counted before the red-stop
> rerun, which adds 6 cells (all no-call endings, none red), so it now
> prints 98 / 70 / 1. The live rerun on this engine is in
> `evidence/2026-09-22-mellum-tool-surface/README.md`. This plan moved here
> from the local, gitignored `.superpowers/` folder.

**Repo:** `satyrn-engine`, worktree `.worktrees/red-stop-gate`, branch
`phase/red-stop-gate`, cut from `78ab87d` (the commit the Engine arm pins).
Commit at task boundaries. Never merge, never push, never run a model.

## Why (diagnosis and offline estimate)

The completion gate (`packages/engine/runner.ts`, the `turn_end` handler)
runs `self_test` when the model ends a turn with no tool call **and no
self-test has run since the last landed mutation** (`checked !== generation`).
It never asks whether that last run *passed*. `run()` sets
`checked = at` whenever the exchange succeeds (`details.ok`), including a run
that exited 1.

Diagnosis, satyrn-evals development record
`records/2026-09-23-spike-mellum-class-review-script-n6.json`, Engine cell
`selfhost-review-script-20260923-130353-154738` (Mellum swe-pi step-500):
turn 3 writes `tools/review.py`, turn 5 writes `tests/test_review.py`,
turn 6 calls `self_test` -> `Test command exited 1` (`test_main_signature`),
turns 7-8 run pytest in bash and read the test file with no mutation, turn 9
ends with no tool call. `checked === generation`, so the gate is silent; no
finish nudge (green never happened). Engine receipt `TESTS_FAILED`. The hidden
grader passed it only because its overlay replaces the model's tests.

Offline estimate (scan of every recorded Engine cell under `~/satyrn-runs`,
script `red_stop_scan.py` beside this plan reconstructs generations from landed
`edit`/`write` results and self-test outcomes): 92 Engine cells, 64 ended on
a no-tool-call turn, **1** ended with the last self-test at the current
generation red -- the cell above. 0 of the Ornith cells.

**Honest scope.** One cell in 92 is not a binding constraint in the sense
`AGENTS.md` asks for. This is built at the maintainer's direct request as a
correctness fix to the completion gate's stated intent ("a failing run goes
back to the model"), not as a new component justified by admission. Any
evals record that uses it must re-pin the Engine arm to the new commit; that
is out of scope here.

## Design (decided; do not re-litigate)

1. `registerRunner` gains `lastPassed: boolean | null` (null: no completed
   run) and `lastResult: string` (the compact result text of the last
   completed run), set wherever `checked` is set: in `run()` and in the
   enforced branch. `passed` means `details.ok && exit_code === 0 &&
   !timed_out`, exactly as the enforced branch already computes it.
2. A new exported `redStopMessage(resultText)`:
   `Before you finish: the last self_test on the current tree did not pass, and nothing has changed since it ran. Fix the failure, or say which part of the request you cannot complete.\n${resultText}`
3. In `turn_end`, **after** the existing enforced branch and only when that
   branch did not run this turn: if `isFinalTurn(event.message)` and
   `checked === generation` and `lastPassed === false` and
   `redStopped !== generation`, set `redStopped = generation`, note
   `self_test_red_stop` with `{generation}`, send one follow-up
   (`customType: "self_test_red_stop"`, `deliverAs: "followUp"`), and set
   `gated = true` so the runaway resume is suppressed for the turn.
4. **No re-run.** The tree has not changed since the red run (same
   generation) and carried tests are restored before every self-test, so the
   stored result stands. This saves one full-suite run (60-100 s).
5. **Once per generation, and the enforced follow-up counts.** When the
   enforced branch sends its failure follow-up, set `redStopped = at` too,
   so a model that is told once and stops again is not told a second time
   for the same tree.
6. A new mutation (`generation` advances) re-arms both gates as today; the
   enforced branch then owns the next stop because `checked !== generation`.
7. A refused exchange (`details.ok` false) leaves `lastPassed` unchanged,
   matching how `checked` is only set on `details.ok`.

## Tasks

### Task 1: unit tests first, then the gate (`tests/test_runner.mjs`, `packages/engine/runner.ts`)

Write failing tests beside the existing completion-gate tests (around
`test_runner.mjs:363`), using the same fake Pi and fake exchange:

- **fires:** mutation, model `self_test` exits 1, final turn -> one
  follow-up equal to `redStopMessage(<that result text>)`, entry
  `self_test_red_stop {generation: 1}`, no enforced entry, no
  `runaway_resumed`.
- **sibling, green:** mutation, red `self_test`, mutation, green
  `self_test`, final turn -> no red-stop follow-up.
- **sibling, once:** red then final -> one follow-up; a second final turn
  with no mutation -> nothing further.
- **sibling, enforced counts:** mutation, no self-test, final turn ->
  enforced run exits 1 and sends its follow-up; next final turn with no
  mutation -> no red-stop follow-up.
- **sibling, new mutation re-arms the enforced gate, not red-stop:** red
  `self_test`, mutation, final turn -> the enforced branch runs.
- **detected route counts:** a bash pytest result that the Engine detects and
  runs `self_test` for, exiting 1, then a final turn -> red-stop fires.
- **length-cut red stop:** a `stopReason: "length"` final turn with a red
  last run -> red-stop follow-up and no `runaway_resumed`.
- **refused exchange:** a `self_test` whose exchange is refused
  (`details.ok` false) then a final turn -> behaviour unchanged from today.
- `redStopMessage("R")` exact text.

Run `node --test --experimental-strip-types tests/test_runner.mjs`; see them
fail; implement the design; see them pass. Commit.

### Task 2: replay fixtures (`tests/fixtures/events/`)

Add event fixtures in the existing format (see
`finish-on-green-not-steered-enforced.json`, `self-test-enforced.json`):

- `self-test-red-stop.json`: the recorded shape of cell 130353 -- two
  landed `write`s (one source, one test), a `self_test` result exiting 1
  with the recorded failure line, then a `turn_end` with
  `stopReason: "stop"` and no tool call. `expect.followUp` contains
  `the last self_test on the current tree did not pass`; `expectedEntries`
  holds the `self_test_red_stop` entry.
- `self-test-red-stop-not-after-green.json`: the sibling success fixture.
- `self-test-red-stop-once.json`: two final turns, one follow-up.

`node --experimental-strip-types tools/replay_events.mjs` must replay them.
Check that every existing fixture still replays unchanged; if any
`expectedEntries` or `expectedHandlers` needs to change, stop and report
instead of editing it. Commit.

### Task 3: docs, provenance, gates

- Describe the red-stop gate beside the completion gate wherever the
  completion gate is documented (`docs/usage.md`, `docs/glossary.md`,
  and the doc comment above `enforcedMessage` in `runner.ts`). Keep it to
  what it does and the diagnosis cell; no claims of effect.
- Add `PROVENANCE.md` rows for every new file.
- `just gates` must exit 0. Report its tail verbatim. Commit.

## Out of scope

- Re-pinning `arms/engine-*.json` in satyrn-evals or exporting a new engine
  cell under `/Users/Shared/satyrn-cells`.
- Any live run. Whether the gate changes outcomes is a later evals record.
- Detecting announce-then-stop from reasoning text. The gate keys on the
  tree being red, not on what the model said.

## Revision 1 (after Opus review, 2026-09-23)

Design points 1, 4 and 7 are reversed. The review found two ways a stored
result goes stale: a refused enforced run sets `checked` without updating
`lastPassed`, so an older generation's failure is sent as current; and a
change made through bash advances no generation, so "nothing has changed"
can be false. Reusing the stored result was the root of both.

Revised design:
- **Re-run, don't reuse.** The red-stop gate runs `self_test` again, through
  the same exchange as the enforced branch, and acts on that fresh result.
  Pass: send nothing. Fail or timeout: one follow-up. Refused: send nothing.
  The cost is one full-suite run, only in the red-stop case (1 of 92
  recorded Engine cells).
- **Condition.** `isFinalTurn` and the enforced branch did not run this turn
  and `lastPassed === false` and `lastAt === generation` (the generation the
  last completed run belongs to) and `redStopped !== generation`. Track
  `lastAt`; on any refused run (model, detected or enforced) set
  `lastPassed = null`.
- **Update state from the re-run** exactly as the enforced branch does
  (`checked`, `lastPassed`, `lastAt`), and set `redStopped = generation`
  whether or not it sends.
- **Message.** `redStopMessage(resultText)` becomes: `Before you finish: your
  last self_test did not pass, so the Engine ran it again on the current
  tree, and it still does not pass.\n${resultText}`
- **Entry.** `self_test_red_stop` with `{generation, code, exit_code,
  follow_up}`, the same shape as `self_test_enforced`.
- The enforced branch's failure follow-up still sets `redStopped = at`.
- `lastResult` is no longer needed; remove it.

New tests: the refused-enforced stale case (red at gen 1, edit, final turn
with a refused enforced run, final again: no red-stop); the bash-fix case
(red, then a green re-run at the same generation: red-stop entry with
`follow_up: false` and no message); a re-run that is refused (no message).
Fixture nits: rename `self-test-red-stop-not-after-green.json` to say what
it proves with one exit code; use cell 130353's recorded failure text in
`self-test-red-stop.json` if the replay tool lets a fixture set the
exchange's output, otherwise say so in the report. Docs and glossary: drop
"the tree has not changed" and the two-way "counts the other's" wording.
