# Frozen conditions: misleading-locus R3, route verification and screen

Written 2026-09-08, before any cell runs. Stages 3 and 4 of
[the AgentClinic suite brief](agentclinic-suite-brief.md). Budget authorized by
the maintainer 2026-09-08. Nothing below is tuned after a result is read.

## The cell

| | |
|---|---|
| task | `agentclinic-repair-misleading-locus` |
| rung | `R3` |
| contract digest (sha256 of the R3 text) | `c5330e8c2e5a8c01861f3593015da2ce98851f9c20145385978e6799dbd80fbf` |
| qualification record | the task's `qualification.json`, three behaviors over all 13 hidden checks, three witnesses derived from real suite runs |

Recompute the digest:

```
uv run python -c "import hashlib,sys;sys.path.insert(0,'src');
from satyrn_evals.manifest import load_manifest, resolve_task;
print(hashlib.sha256(load_manifest(resolve_task('agentclinic-repair-misleading-locus')).contracts['R3'].encode()).hexdigest())"
```

## Arms, recorded separately

The two arms are product surfaces. Their tool sets differ **by design**; the
requirement is that each is frozen and written down before the run, not that
the two are made the same. **No component attribution follows from any
difference between them.**

| | Baseline | Engine |
|---|---|---|
| arm file | `arms/baseline.json` | `arms/engine.json` |
| argv | `satyrn-evals-attempt-pi` | `satyrn-engine attempt` |
| effective tools | `read`, `bash`, `edit`, `write` | `read`, `edit`, and a **bounded `bash` test runner** |
| engine commit | none | `fc22622ac39f71ff9d0ad42718da4e1bd3500ac3` |

> **Correction, recorded 2026-09-08 after the run.** As first written, this
> table gave Engine's effective tools as `read, edit` alone, copied from the
> `tools` field of `arms/engine.json`. That was **false as a description of the
> arm's surface**. The engine registers a further tool of its own, named `bash`
> but **bounded**: it executes only the contract's declared `test_command` and
> refuses every other command by name
> (`satyrn-engine packages/engine/runner.ts:218-228`;
> `src/satyrn_engine/runner.py:136-148`). The rendered R3 contract for this
> task carries that `test_command`, and **every Engine cell in this batch used
> the runner** — 3, 2 and 3 `bash` calls in the route-verification cell and the
> two Engine screen cells.
>
> This is an **intended product-surface difference**, and the whole point of
> freezing each arm's surface separately is that such a difference is stated
> rather than assumed away. It changes nothing that was run, so **no re-run
> follows** — but a frozen record has to be true, so the row is corrected and
> the original wording is kept here rather than erased. It remains the case
> that no component attribution follows from any difference between the arms.

Engine source digests are pinned in `arms/engine.json` (`engine.ts`,
`mutator.ts`, `runner.ts`, `orchestrator.ts`). The engine checkout at
`~/projects/pauleveritt/satyrn-engine` is at that commit with a clean tree;
preflight re-verifies both, and refuses a mismatch.

## Shared settings, identical across arms

| | |
|---|---|
| model (server) | `gemma-4-12B-it-MLX-8bit` |
| model (client id) | `omlx/gemma-4-12B-it-MLX-8bit` |
| pi | `0.84.4` |
| context window | 80,000 |
| max tokens | 8,192 |
| compaction | enabled, 16,384 reserve |
| temperature | 1.0 |
| repeated-call limit | `--max-repeated-calls 10` |
| command timeout | `--timeout 900` |
| whole-attempt deadline | `--attempt-timeout 1200` |
| base URL | `http://127.0.0.1:8001/v1` |

**Where the limits come from.** The 24 retained `misleading-locus` cells in
`~/satyrn-smokes/2026-09-07-v14b-133236` ran, per the driver log's own start
and done stamps, between 30 s and 75 s end to end, pooled across both arms
(n=24; the pooled figure is a limit input, never an arm comparison — this
project has retracted two published figures for comparing wall clock between
contiguous arms). A 900 s command timeout is more than ten times the slowest
retained cell, and the 1200 s whole-attempt deadline sits above it so the
command timeout fires first and the deadline catches only a setup, preservation
or grading pathology. Both are far inside the 10–15 minute useful-feedback
target. Recompute the durations:

```
grep -E "misleading-locus/cell-.*(start|done)" \
  ~/satyrn-smokes/2026-09-07-v14b-133236/run.log
```

Those cells ran at `R1` on an older engine, so they bound *duration*, nothing
else. They are not evidence about outcomes at `R3`.

## Stage 3 — route verification

One Engine attempt on the cell above. Its purpose is to establish that the
condition executes, preserves its artifacts, and regrades offline.

**It stays outside the stage-4 denominator.** It is reported as route
verification and never pooled with the screen's cells.

An ordinary failed repair still verifies the route. Infrastructure failure
stops the stage and the evidence is retained. Neither outcome authorizes a
retry, a second task, or a change to anything above.

## Stage 4 — the matched screen

Two attempts per arm, four cells, interleaved on a seeded schedule written
before the first cell:

```
scripts/interleave.py --seed 20260912 --n 2 \
  --task agentclinic-repair-misleading-locus --rung R3 \
  --contract-digest c5330e8c2e5a8c01861f3593015da2ce98851f9c20145385978e6799dbd80fbf \
  --output RUNS_ROOT/screen arms/baseline.json arms/engine.json
```

Realized order, written before the first cell: `engine, baseline, engine,
baseline`.

**The seed is 20260912 because the order must alternate.** `build_order` has no
run-length constraint, and at two cells per arm a clumped order is a coin flip
that would confound arm with position over four cells. The first seed tried,
`20260908`, gave `engine, engine, baseline, baseline`. The rule fixed before
any cell ran — smallest seed >= 20260908 whose order alternates — selects
`20260912`. It is recorded, deterministic, and could not be outcome-driven: no
cell had run. Full statement and recompute: `SEED-RULE.md` in the batch
directory.

Output root: `/Users/pauleveritt/satyrn-smokes/2026-09-08-misleading-locus-r3-174721`,
with `scripts/preflight.sh` re-run into that directory immediately before the
first cell.

**Stopping rules, frozen.** Four cells, and four is the whole budget: no
extension after reading any outcome, no added rung, no added task, no re-run of
a completed cell. A cell with `summary.json` is complete; an incomplete cell
directory is moved aside and never reused. Infrastructure failure stops the
remaining launches and the completed cells are reported with their true
denominator. An ordinary failed repair is a counted observation.

**What four attempts can support.** Counts by arm, with denominators, and a
second reading of the live route. Not a rate, not a superiority claim, not a
mechanism, and not a difficulty band.

## Preconditions, checked before spending

1. The engine checkout is clean and at the pinned commit.
2. The model server answers a live completion — never a `/v1/models` listing,
   which this project has recorded as unreliable within a single session.
3. The machine is quiet. The one voided mini-probe in this project's history
   was a GPU out-of-memory, which no code fix prevents.
4. `preflight.sh` has been re-run into this batch's own output directory and
   passed.
