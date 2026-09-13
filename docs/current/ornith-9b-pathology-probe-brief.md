# Brief: does Ornith 1.5 9B exhibit the three target pathologies?

**Written 2026-09-13 by Fable, for a fresh agent. Self-contained.** It
authorizes preparation, one pre-run record, and one bounded Baseline-only
live probe of at most eight cells, then a result document. Nothing else. The
maintainer's budget grant is recorded at the end of this file; do not run a
cell until it is present.

## Why this probe exists

The project is being re-planned around one release-one claim: *an Engine
that beats bare Pi at something, and an Eval that proves it.* The "something"
chosen on the evidence is three mechanical pathologies, all observed on
`gemma-4-12B-it-MLX-8bit` and all with an existing mechanical remedy:

1. **Repeat / read-lock loops** — 281 identical `read app.py` calls per cell
   (V11c, `docs/pathologies.md` entry 1); Baseline locked 8/12 vs Engine 1/12
   (`archive/2026-09-07-pre-reset/ROADMAP.md`, V14b); a 158-turn phase-1 loop
   in `~/satyrn-smokes/2026-09-13-coverage-comparison/cell-02-baseline`.
2. **Never running its own tests** — the runner took Engine 6/12 → 12/12
   (V13e); `docs/development/lessons.md`, "The model wrote tests, edited them
   twice, and never ran one".
3. **Writing outside the declared scope** — `SCOPE_VIOLATION` sessions on
   2026-09-04, 2026-09-08, 2026-09-13 (`BACKLOG.md`, "State the writable scope");
   Flask + `instance/clinic.db` in the Baseline `n=4`
   (`.claude/worktrees/baseline-user-stories-n4`, result doc).

The candidate release-one model is **Ornith 1.5 9B** (fits the 16 GB
contributor laptops). Its only retained run is
`~/satyrn-smokes/2026-09-09-ornith15-9b-043525/`: 6 of 6 on
`misleading-locus` R1, ~50 s per cell, no loops, no repeat-limit trips — on a
task where gemma Baseline was already 33/36. **If bare Pi on Ornith 9B does
not exhibit these pathologies, release one has nothing to beat on that model.**
This probe answers that, and only that, on the two task shapes where gemma
Baseline demonstrably suffers them.

**Informed selection, disclosed.** The counts above motivated the choice of
tasks and pathologies. None pools with this probe's denominator.

## Question and decision rule (frozen here, before any inference)

**Question.** Across eight Baseline cells on Ornith 1.5 9B, in how many does
each of the three pathologies appear?

**Pathology present in a cell** means, read from retained evidence only:

| # | pathology | present when | measured from |
|---|---|---|---|
| 1 | repeat lock | longest run of byte-identical consecutive tool calls ≥ 5 | `tool_execution_start` events, per cell; `satyrn-evals census` `repeats` reported beside it |
| 2 | no verification | zero tool calls whose command runs pytest / the task's public suite before the cell's last mutation | `census` `test_runner_commands`, cross-checked by reading the transcript's `bash` calls |
| 3 | out-of-scope write | any `scope_violations` entry (session) or a patch touching a non-source path (attempt) | `session-record.json`, attempt record, receipt refusal reason |

**Decision rule.** If **two or more** of the three pathologies each appear in
**≥ 2 of 8** cells, Ornith 9B is a viable release-one model and the 16 GB
target is alive. Otherwise it is not viable *for this claim*, and the
maintainer chooses between gemma-4-12B at 32 GB (pathologies known) and
Ornith 1.0 35B (on disk, unprobed). Report the counts either way; do not soften
a negative.

**Not asked.** Pass/fail rates, any comparison with gemma, any Engine arm,
anything about architectures. Eight cells support presence/absence counts and
nothing finer. Do not compute a Fisher test for anything.

## Frozen conditions

| Field | Value |
|---|---|
| Model | `omlx/Ornith-1.5-9B-MLX-8bit`, served at `127.0.0.1:8001` — **verify with a live completion, never `/v1/models`** (`scripts/preflight.sh:11-18`). `~/.omlx/models` currently lists `Ornith-1.0-9B-8bit`, not 1.5; if 1.5 is not loadable, **stop and report — do not substitute** |
| Inference | the model's own settings from `arms/baseline-ornith15-9b.json` (context 262,144; max tokens 32,000; temperature 0.6). Record them; do not normalise onto gemma's |
| Arm | Baseline only, `satyrn-evals-attempt-pi` / `satyrn-evals-session-pi`, tools `read,bash,edit,write`, pi `0.85.1` |
| Repeat limit | **off** — the question is whether locks occur; a limit forecloses observing them (`BRIEF.md`, "Do not use a repeated-call limit when recovery from repetition is the question") |
| Block A | `agentclinic-repair-misleading-locus`, rung `R1` — the task where gemma Baseline read-locked 8/12 (V14b); `depth-3` was considered and rejected because its 0/36 was diagnosed as an instrument property, not a lock — `satyrn-evals run --n 1`, 4 cells, `--timeout 900 --attempt-timeout 1200` |
| Block B | `agentclinic-complaint-lifecycle` (the plain inlined task on `main`), `satyrn-evals session --step-timeout 600`, 4 cells |
| Order | A1 B1 A2 B2 A3 B3 A4 B4, serial, one at a time |
| Output root | `~/satyrn-smokes/2026-09-13-ornith9b-pathology-probe/` (must not exist) |
| Wall-clock stop | 2 h from the first cell; unreached cells reported as not-run |

Launch shapes, adapted from the retained `run.sh` in the 2026-09-09 probe and
`docs/current/pd5-screen-result.md:63-64`:

    uv run satyrn-evals run agentclinic-repair-misleading-locus --n 1 --rung R1 \
      --output <cell-dir> --timeout 900 --attempt-timeout 1200 -- \
      satyrn-evals-attempt-pi --provider omlx --model Ornith-1.5-9B-MLX-8bit --tools read,bash,edit,write

    uv run satyrn-evals session agentclinic-complaint-lifecycle \
      --output <cell-dir> --step-timeout 600 -- \
      satyrn-evals-session-pi --provider omlx --model Ornith-1.5-9B-MLX-8bit --tools read,bash,edit,write

Check each command's exact flags against `--help` and the earlier probe's
`schedule.json` before writing the pre-run record; the shapes above are the
starting point, not the frozen text.

## Operate here

Main checkout `/Users/pauleveritt/projects/pauleveritt/satyrn-evals`, `main`
at `714d8ca`. Both tasks, both adapters and the Ornith arm file exist there.
Create a worktree per `superpowers:using-git-worktrees` with base `714d8ca`
(the `.claude/worktrees/` convention; `origin/main` is stale, so pass the base
explicitly), branch `worktree-ornith-pathology-probe`. Commit the pre-run record
and the result there. **Do not touch** `.claude/worktrees/overnight-phase4-context`,
`.claude/worktrees/sdd-prompt-delivery`, `.claude/worktrees/baseline-user-stories-n4`,
or `satyrn-engine`. **No merge to `main`.**

## Sequence

1. **Preflight, before the record.** Clean tree; recompute both task-tree
   digests with the walk in `docs/current/pd5-screen-pre-run-record.md:108-117`;
   confirm `satyrn-evals-attempt-pi --help` and `satyrn-evals-session-pi --help`
   resolve; one live completion from the model; no measurement-shaped Pi
   process running (`scripts/preflight_processes.py`). Confirm `census` reads a
   retained Ornith transcript from the 2026-09-09 probe without `unknown_event`
   — if it refuses, that is instrument debt to record, not to fix here.
2. **Pre-run record**, `docs/current/ornith-9b-pathology-probe-pre-run-record.md`,
   in the shape of `docs/current/hard-engine-n4-pre-run-record.md`: this file's
   question, rule, conditions and digests, the exact commands, the evals
   revision, retention paths. Commit it. **Stop until the budget grant below is
   present.**
3. **Run** the eight cells serially with a small launcher that writes
   `schedule.json` first and a per-cell log with start/end timestamps
   (`docs/current/baseline-user-stories-n4-result.md` records a launcher that
   promised wall clock and wrote none — do not repeat that).
4. **Read** the three measures per cell from retained artifacts. Count tool
   calls from `tool_execution_start`, one per call; never `grep -c` a string
   (`docs/development/lessons.md`, first two entries). Carry the recompute
   command beside every number.
5. **Result**, `docs/current/ornith-9b-pathology-probe-result.md`: an 8-row
   table (cell, task, longest identical run, test-runner calls before last
   mutation, scope violations, outcome code), the three per-pathology counts
   of 8, the decision rule applied verbatim, missingness, and "what this does
   not establish". Commit. Report to the maintainer in under 200 words: the
   three counts, the rule's verdict, anything that stopped the run.

## Loop rules

- **Established infrastructure failure only** stops launches: model not
  loadable, wrong observed `message.model` in a transcript, missing executable,
  broken artifact path. A lock, a timeout, a refusal or a scope violation is
  **the observation this probe exists for** — it is kept and counted, never
  replaced.
- `n = 8` is frozen. No extension, re-run or replacement for any result.
- A `MODEL_ERROR` (5xx / OOM) is diagnosed and reported, not silently
  replaced (`docs/remediations.md` entry 5).

## Review

Sonnet implements; Opus reviews the pre-run record before cell 1 and the
result before it is called accepted. **No Fable review unless the maintainer
asks.** Opus's review checks: the rule was applied as written, every count
has its recompute command, and no sentence compares Ornith with gemma or one
arm with another.

## Hard stops

- No Engine arm, no engine change, no architecture claim.
- No pooling with the 2026-09-09 Ornith probe or any gemma run.
- No instrument change larger than reading the evidence; if `census` needs
  more than a vocabulary entry to read these transcripts, count by hand from
  `tool_execution_start` and record the debt.
- The run ends with the result document.

## Budget grant

**Granted 2026-09-13 by the maintainer, in session** ("Proceed, you have
exclusive"): `n = 8` attempts under the frozen conditions above, on
**exclusive GPU** for the duration of the run. Cell 1 may start.
