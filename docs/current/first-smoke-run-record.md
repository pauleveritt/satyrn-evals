# First live smoke: frozen run record

This record freezes one bounded live attempt for stage 2 of
[the first engine comparison plan](first-engine-comparison-plan.md). Writing it
authorizes no spending and no inference. The live stage begins only when every
unresolved field below is resolved and its budget is authorized.

## Status: executed

The smoke ran on 2026-09-08 and is settled. Nothing in this record remains
unresolved.

| Field | Resolution |
| --- | --- |
| Executor arm | Engine. |
| Command timeout | 900 s; whole-attempt deadline 1020 s. |
| Timing wrapper | `scripts/timing.py`, verified against a retained cell before the launch. |
| Seed | `20260908`. |
| Output directory | `~/satyrn-smokes/2026-09-08-first-smoke-123843/`. |
| Token-floor artifact | 1627, provenance recorded in the schedule section. |
| Engine repository path | `/Users/pauleveritt/projects/pauleveritt/satyrn-engine`. |
| Clean-tree gate | Satisfied; preflight recorded the launch revision. |
| Launch revision | `c7f93760d1f1f15d29bbf19b0039572417815a51`, from `preflight.json` `evals_commit`. It matched the commit this record was frozen at, so no code changed between freezing and launching. |
| Budget authorization | Given for preflight's one completion and one scored attempt. Both were used; nothing further was launched. |

The outcome is recorded in `RESULT.md` beside the evidence: one scored attempt,
verdict `pass`, 13 of 13 expected checks executed and passing, no refusals and
no missing evidence, 31.763 s total, and a byte-identical offline regrade. That
note owns the result; this record owns the conditions it ran under.

## Question and condition

The smoke asks one question: **does the complete live route work end to end on
the qualified condition, and does its retained evidence regrade to the same
verdict?** It establishes no success rate, no causal effect, and no headroom.

| Item | Frozen value |
| --- | --- |
| Task | `agentclinic-repair-depth-3` |
| Rung | `R3` |
| Contract identity | `sha256:96e3d49d4b6826cdf86272b79a1f126e30d330d93f62dff95bc9264d90eb29bb`, from `manifest.json` `contracts.R3` (869 bytes). Byte-identical to the manifest's default `contract`, so `--rung R3` is passed explicitly rather than relied on as a default. |
| Task base identity | `workspace_base_sha e9bca9d423273b46ecf8b762c303926740308f15`, content-addressed from `base/`. |
| Task and oracle revisions | Task directory, hidden overlay, and oracle hook are all at the evals launch revision. Upstream source is recorded in the task's `PROVENANCE`. |
| Oracle | `python -m pytest -p satyrn_evals.oracle_hook`, 13 expected test ids, hidden overlay. |
| Qualification | `qualification.json`, status `justified`; five behaviors each `justified`; witnesses `base`, `known-good`, `partial-no-303`. |

## Executor

| Item | Frozen value |
| --- | --- |
| Arm | **Engine.** `arms/engine.json`. |
| Command resolution | `satyrn-engine` is not on `PATH` by default. The launch prepends `/Users/pauleveritt/projects/pauleveritt/satyrn-engine/.venv/bin` to `PATH` so that `shutil.which` resolves it for preflight and for the attempt. The arm file is not edited, so its digest and the condition are unchanged. |
| Engine repository | `/Users/pauleveritt/projects/pauleveritt/satyrn-engine`, passed to preflight as `--engine-repo`. |
| Baseline arm | `arms/baseline.json`, `sha256:ad965200d6bd7aab…`; tools `read,bash,edit,write`. |
| Envelope arm | `arms/envelope.json`, `sha256:30749377bc107785…`; tools `read,edit`. |
| Engine arm | `arms/engine.json`, `sha256:d022e76e08f5bb6e…`; tools `read,edit`, fixed inside the engine and recorded rather than passed. |
| Engine revision | `8b52de932c70ad01e570decf97228434117c9387`, working tree clean; all four pinned source digests verified to match. |
| Model identity | `omlx/gemma-4-12B-it-MLX-8bit`, server model `gemma-4-12B-it-MLX-8bit`. |
| Model settings (declared) | Context window 80000, max tokens 8192, compaction enabled, compaction reserve 16384, temperature 1.0. Preflight compares pi's declared configuration, not what the server enforces. |
| Adapter | `pi 0.84.4`, matching every arm's pin. |

The arm files are the single source for these values; this record cites them by
digest rather than restating a second copy.

**Observed tool surface, corrected after the run.** The arm file pins
`read,edit`, but the pinned engine additionally enables `bash` when the
contract declares a test command, and `agentclinic-repair-depth-3` does. The
smoke's transcript contains three `bash` calls: one refused `ls -R` and two
runs of `uv run python -m pytest tests/`. The condition that ran was therefore
`read,edit,bash`, not the `read,edit` frozen above.

This invalidates an earlier claim in this record: the envelope arm
(`read,edit`) is **not** a tool-matched control for the engine arm, because the
engine's effective surface is wider than its arm file states. A matched
comparison must derive the engine's *effective* surface from the contract
rather than from the arm file, and must state any remaining difference and
the claims it prevents. The arm file is not wrong about what it passes; it is
incomplete as a description of what the engine enables.

Evals appends a rendered engine-contract path as the final argument of whichever
command is chosen; the recorded command includes it.

## Environment

| Item | Frozen value |
| --- | --- |
| Evals revision | Written at `2031fae`. The launch authority is preflight's `preflight.json` `evals_commit`, which is external to the working tree; this record is not edited to carry it, because that would dirty the tree the clean-tree gate has just checked. Documentation is reconciled with the recorded commit after the run. Any intervening code change is a new condition. |
| Dependencies | Python 3.14.2, uv 0.11.6, `uv.lock` `sha256:73becac27ab96dfad867e773457fe5249e5f4c492eb398ae6ff2ea0756818ca1`. |
| Model server | Local OpenAI-compatible server at `http://127.0.0.1:8001/v1`. A model listing on 2026-09-08 showed the pinned model present. A listing is not evidence that a cell can run; loadability is proven only by preflight's completion. |
| Hardware | Apple M5 Max, 128 GB, macOS 26.6.2. |
| Concurrency | One attempt at a time. No parallel cells. |
| Cache and warm-up | Preflight's completion warms the model, so the scored attempt starts against a resident model. That completion is spending, is authorized with the rest of the budget, and is recorded apart from the scored attempt. No other warm-up is planned. A cold-start launch is a different condition. |

## Limits

Proposed, pending authorization.

The retained cells below inform this budget; none matches the proposed
condition. The six 12B `R3` cells ran at `--timeout 900` with
`--max-repeated-calls 10`, on an earlier evals revision, with no whole-attempt
deadline. A changed budget creates a new condition, so these are a basis for
choosing limits, not a matched precedent.

| Limit | Frozen value | Basis |
| --- | --- | --- |
| Command timeout `--timeout` | 900 s | Engine-arm cells on this task at `R1` with the pinned engine range 29–901 s across 24 cells. Three exceed 300 s: two completed normally at about 445 s and 857 s, and one hit the 900 s ceiling as `COMMAND_TIMEOUT`. A shorter timeout would foreclose the 857 s class of completion. These are `R1` observations; they justify the ceiling without establishing an `R3` budget, for which no engine-arm evidence exists. |
| Whole-attempt deadline `--attempt-timeout` | 1020 s | Command timeout plus 120 s for setup, preservation, grading, and cleanup. Setup is inside this span: the deadline begins before the attempt directory is created. Observed setup is a few seconds and grading about 2 s, so 120 s is ample. Overrun by one teardown allowance and by local record I/O is expected and is not a defect. |
| Repeat limit `--max-repeated-calls` | Not set | Recovery from repetition is a behavior of interest. The retained cells cited here all ran with the limit at 10, so their durations are not a clean guide to unlimited behavior. |
| Total ceiling | 1 scored attempt plus preflight's one completion; 20 wall-clock minutes; USD 0.00 marginal | Local GPU inference. No provider rate applies, so no price-based monetary estimate is claimed. GPU time is a real cost this record does not convert to money. The 900 s ceiling exceeds the repository's 10–15 minute feedback target; that is a deliberate consequence of keeping the long-completion class observable. |

Retained timing evidence, measured as attempt-directory UTC timestamp to
`attempt.json` mtime. This is an external reconstruction: the harness records no
duration on a normal completion.

| Batch | Task / rung | Arm | Cells | Verdicts | Total wall time |
| --- | --- | --- | --- | --- | --- |
| `2026-09-06-overnight-232554` | depth-3 `R3` | baseline 12B | 6 | 6 pass | 49.2–81.8 s |
| `2026-09-06-overnight-232554` | depth-3 `R3` | baseline 26B | 6 | 6 pass | 23.6–33.3 s |
| `2026-09-07-v14a-123039` | depth-3 `R1` | engine | 12 | 1 pass, 7 fail, 4 refusals | 29–901 s |
| `2026-09-07-v14b-133236` | depth-3 `R1` | engine | 12 | 12 fail | 36–120 s |

## Schedule

One scored attempt. Denominator is one; the smoke stays outside the triage
screen's denominator. Preflight's completion is separate and is never scored.

- Output location `<RUNS_ROOT>`: `~/satyrn-smokes/2026-09-08-first-smoke-<HHMMSS>/`,
  alongside the existing retained batches, with `<HHMMSS>` fixed at launch. The
  repository's `attempts/` and `runs/` remain absent.
- Seed: `20260908`, following the existing batch convention. With one arm and
  one cell the interleave order is degenerate; the seed is recorded because
  `interleave.py` requires it, not because it varies anything here.
- Token-floor artifact: `$RUNS_ROOT/token-floor.json`, produced by
  `scripts/token_floor.py` before preflight, from the retained transcript
  `2026-09-06-overnight-232554/agentclinic-repair-depth-3-R3/`
  `cell-000-baseline/agentclinic-repair-depth-3-20260906-034728-708835/`
  `transcript.txt`, which yields a floor of 1627 from `usage.input`. That
  transcript is a **baseline**-arm cell: no engine-arm transcript exists at
  `R3`, so the floor is borrowed across arms. Preflight checks only that the
  record holds a positive integer, so this provenance is the real guarantee and
  is stated here rather than inferred from the file.
- Launch order: preflight, then the single attempt. Preflight is not
  identity-only — step 4 issues one live chat completion, and the script also
  requires `--token-floor-record`, `--seed`, and `--n`, and writes an interleave
  schedule before any cell runs.
- Exact invocations. Every input below is frozen.
  Preflight writes `schedule.json` and reserves one cell directory; the launch
  runs **into that cell**, using the schedule's derived command. Raw arm-file
  `argv` is not the launch command: `interleave.py` appends the model and, for
  the pi arms, the tool surface.

```text
export PATH=/Users/pauleveritt/projects/pauleveritt/satyrn-engine/.venv/bin:$PATH
RUNS_ROOT=~/satyrn-smokes/2026-09-08-first-smoke-$(date -u +%H%M%S)
SMOKES=~/satyrn-smokes/2026-09-06-overnight-232554/agentclinic-repair-depth-3-R3
mkdir -p "$RUNS_ROOT"

uv run python scripts/token_floor.py \
    "$SMOKES/cell-000-baseline/agentclinic-repair-depth-3-20260906-034728-708835/transcript.txt" \
    --record "$RUNS_ROOT/token-floor.json"

scripts/preflight.sh --engine-repo /Users/pauleveritt/projects/pauleveritt/satyrn-engine \
    --seed 20260908 --n 1 \
    --task agentclinic-repair-depth-3 --rung R3 \
    --contract-digest 96e3d49d4b6826cdf86272b79a1f126e30d330d93f62dff95bc9264d90eb29bb \
    --output "$RUNS_ROOT" --token-floor-record "$RUNS_ROOT/token-floor.json" \
    --arms arms/engine.json

DIR=$(python3 -c "import json;print(json.load(open('$RUNS_ROOT/schedule.json'))['cells'][0]['dir'])")
CMD=()
while IFS= read -r part; do CMD+=("$part"); done < <(python3 -c "import json
for p in json.load(open('$RUNS_ROOT/schedule.json'))['cells'][0]['command']: print(p)")
[ ${#CMD[@]} -gt 0 ] || { echo "empty command; refusing"; exit 2; }

uv run satyrn-evals run agentclinic-repair-depth-3 --n 1 --rung R3 \
    --timeout 900 --attempt-timeout 1020 \
    --output "$RUNS_ROOT/$DIR" -- "${CMD[@]}"
```

  Writing into `<RUNS_ROOT>` directly would leave the scheduled cell empty, and
  `tally.py` refuses a schedule it cannot reconcile against what is on disk.

- Interruption: a mid-attempt interruption retains evidence and blocks
  automatic continuation pending review. A completed attempt is never replaced.
- Stopping rule: an established infrastructure failure — wrong model, missing
  executable, invalid task setup, or broken artifact path — stops the stage and
  is repaired. An ordinary failed repair is a counted observation, not a retry.
- Evidence review: verify observed engine and model identity against this
  record; confirm the patch and transcript were retained before grading; derive
  the verdict from fresh hook evidence with the expected executed checks and no
  collection errors; copy the receipt aside and regrade the retained patch
  offline; compare and diagnose any disagreement before proceeding.

## Timing and cost reporting

**The convention, resolved 2026-09-08.** Cost is the monotonic total plus
usage counted by the terminal-per-response rule. Lifecycle phase durations —
setup, command, grading, preservation, cleanup — are **unmeasured**, and their
absence is reported as missingness rather than filled in.

- **Total.** A launch wrapper bounds the single `satyrn-evals run` invocation
  and takes `time.monotonic()` either side. This figure is sound.
- **Usage.** `scripts/usage_totals.py` counts one terminal `message_end` per
  assistant response. Summing every usage object in a streaming transcript
  inflates the total — 5.5x on the smoke — because `message_update` snapshots
  and `turn_end` repeat the same figures.
- **Phases.** Not reported. `scripts/timing.py` emits intervals between
  artifact events, and those are diagnostic context only: they do not
  correspond to lifecycle phases, and the artifact says so itself.

Why the intervals are not phases: the engine creates the transcript after the
command has started, so the leading interval absorbs command startup; and it
publishes the patch after the final transcript write, so the interval ending
at the receipt contains patch publication and preservation as well as grading.
The trailing residual is therefore not all preservation.

The harness could supply real phases. `attempt.py` already calls
`deadline.remaining(...)` at every `SETUP`, `COMMAND`, `PRESERVATION`,
`GRADING`, and `CLEANUP` boundary against a monotonic clock, so the boundaries
exist and are simply not persisted on a normal completion. Instrumenting them
is deferred: phase durations exist to justify infrastructure optimization,
which this plan defers until a measured need. Whoever takes it up should note
that `CLEANUP` is entered from several sites including error paths, so
non-overlapping spans need deliberate handling rather than a
first-and-last-entry rule.

Two operational constraints hold wherever the interval tool is used for
diagnosis:

- **Measure before regrading.** `regrade` rewrites `receipt.json` and
  `attempt.json`, destroying the mtimes it reads.
- **Measure the original cell, not a copy.** A copy does not carry birth times
  forward. Archive after measuring.

## Verification performed without inference

Completed on `claude/engine-comparison` at `2031fae`, before any live stage.

- Offline regrade reproduces retained verdicts exactly. Two retained cells were
  copied and regraded; both receipts came back byte-identical, with only
  `attempt.json`'s cosmetic `message` field changing. Today's code reproduces
  the 2026-09-06 verdicts.
- The token-floor prerequisite is satisfiable offline. `scripts/token_floor.py`
  against retained transcripts yields 1627 (12B) and 1629 (26B) from
  `usage.input`, so preflight's required record needs no inference.
- Executable and configuration identity: engine revision and all four source
  digests match; `pi 0.84.4` matches every arm's pin.
- Offline checks pass: 1338 tests passed with 298 deselected, `ruff` clean,
  `lint-docs` clean, `git diff --check` clean. Strict Sphinx is not run here
  because `intersphinx` requires network.

## Limits carried into interpretation

- The oracle result path is checked for shape, not authorship. A verdict is not
  bound to its producer. This limit is stated in
  [trust boundaries](../topics/trust-boundaries.md) and is not resolved here.
- The baseline adapter harvests `git diff HEAD`, so a file created by the
  `write` tool never reaches the patch.
- Arm tool surfaces are not equivalent; see the executor section.
- Grading drops the oracle's collection tracebacks before writing a receipt, so
  an `unavailable` verdict carries its identifier mismatch but not its cause.
- The harness records no duration on a normal completion, so wall time is
  measured externally and stated with its source.
- `regrade` overwrites the receipt and record in place; the original is copied
  aside first or the comparison destroys its own baseline. It also resets the
  mtimes the timing method reads, so timing is captured before re-scoring.
