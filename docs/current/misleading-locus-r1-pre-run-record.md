# Frozen conditions: misleading-locus R1 comparison

Written 2026-09-08, before any cell. The design is
[the R1 comparison design](misleading-locus-r1-comparison-design.md); this
record fixes its concrete values. **No spending is authorized by this document.**

## The cell

| | |
|---|---|
| task | `agentclinic-repair-misleading-locus` |
| rung | `R1` |
| contract digest (sha256 of the R1 text) | `184d0507cca75e08242ef83a6ff80b75ae4aafcdb01cbc4ef1f9f00b7690e856` |
| qualification record | `qualification-R1.json`, three behaviors over all 13 hidden checks, three witnesses re-derived by running both suites |

What `R1` withholds, and why this rung was chosen: it names the failing check
and its symptom, and does **not** name `app.py`, say the handler appends to a
copy, or say where to look. Locating the defect is left to ordinary code
reasoning over a readable workspace — the behaviour `R3` discloses away.

Recompute the digest:

```
uv run python -c "import hashlib,sys;sys.path.insert(0,'src');
from satyrn_evals.manifest import load_manifest, resolve_task;
print(hashlib.sha256(load_manifest(resolve_task('agentclinic-repair-misleading-locus')).contracts['R1'].encode()).hexdigest())"
```

## Arms, recorded separately

Tool surfaces differ **by design**; each is frozen and written down, and **no
component attribution follows** from any difference between them.

| | Baseline | Engine |
|---|---|---|
| arm file | `arms/baseline.json` | `arms/engine.json` |
| argv | `satyrn-evals-attempt-pi` | `satyrn-engine attempt` |
| effective tools | `read`, `bash`, `edit`, `write` | `read`, `edit`, and a **bounded `bash` test runner** |
| engine commit | none | `fc22622ac39f71ff9d0ad42718da4e1bd3500ac3` |

Engine's `bash` executes **only** the contract's declared `test_command` and
refuses every other command by name
(`satyrn-engine packages/engine/runner.ts:218-228`,
`src/satyrn_engine/runner.py:136-148`). Baseline's is a general shell. This is
the corrected surface description; the R3 record's first version got it wrong
by copying the arm file's `tools` field, and that correction is recorded there.

## Shared settings, identical across arms

| | |
|---|---|
| model (server / client) | `gemma-4-12B-it-MLX-8bit` / `omlx/gemma-4-12B-it-MLX-8bit` |
| pi | `0.84.4` |
| context window / max tokens | 80,000 / 8,192 |
| compaction | enabled, 16,384 reserve |
| temperature | 1.0 |
| repeated-call limit | `--max-repeated-calls 10` |
| command timeout | `--timeout 900` |
| whole-attempt deadline | `--attempt-timeout 1200` |
| base URL | `http://127.0.0.1:8001/v1` |
| seed | **20260908** |

The repeated-call limit is retained because recovery from repetition is **not**
the question here; a limit would be wrong if it were.

## Measures, declared before the run

**Primary — outcome.** Successful-attempt probability (verdict `pass` from
hook-written evidence). **One** contrast, **one-sided Fisher exact**,
`alpha = 0.05`, `n = 36` per arm.

**Secondary — cost, descriptive.** Turns, tool calls, and terminal-response
token usage via `scripts/usage_totals.py`. Reported **whatever the primary
shows**. Monetary cost is unmeasured: this is a local provider. Wall-clock is
never compared between arms.

**No cost decision rule is declared, because no adoption decision currently
hangs on cost.** Adding a threshold after seeing the figures would be choosing
a rule from the data.

**Power, with its assumptions.** Attempts independent within and across arms;
each arm's underlying success probability fixed for the batch; the single
pre-declared test above; alternatives *stipulated*, not carried over from the
earlier batch.

| alternative | power |
|---|---|
| 0.50 → 0.75 | 0.651 |
| 0.50 → 0.80 | **0.809** |
| 0.50 → 0.85 | 0.921 |

```
uv run scripts/power.py --n 36 --p-reference 0.50 --p-alternative 0.80
```

Powered for **+30 points**; **underpowered for +25**. A null here is not
equivalence.

## Disclosure

`R1` on this task was chosen **because** an earlier interleaved batch recorded
Engine 11/12 against Baseline 4/12 there. Those counts stay **outside** this
denominator and are never pooled. This run is a replication of a disclosed
prior observation.

## Schedule and stopping rules

1. **Route check** — 1 cell per arm. Retained, reported, **outside the primary
   denominator**.
2. **Scored batch** — 72 cells, interleaved on the seed above, order written
   before the first cell. Staged in blocks with checkpoints after cells
   **6, 24 and 48**.
3. **Analysis once**, over all 72.

`n = 36` per arm is the whole budget. **No extension after reading anything**,
no added rung, no added task, no sequential stopping.

Alternation is **not** constrained at this `n`: the clumping that forced a
declared seed rule on the four-cell screen is negligible over 72 cells. The
backlog entry on `build_order` stands regardless.

**Checkpoints follow `BRIEF.md`'s comparison policy**: verify identity,
artifact integrity and execution health; stop remaining launches only when
evidence establishes an infrastructure failure; preserve ordinary unsuccessful
attempts in their denominator; if the cause is uncertain, pause for diagnosis
without replacing the attempt. Refusals, timeouts, deadline expiries and
schema/tool refusals are **measurements, not triggers**.

**No restart from zero by default.** Establish which attempts are affected and
whether the repair changes conditions. A healthy interrupted run resumes; a
materially changed condition means a separately authorized replacement
experiment with the original partial batch reported separately.

**Runtime, extrapolated.** Retained `R1` cells ran 30–75 s, so 72 scored cells
imply 36–90 minutes and 74 cells 37–92.5 — before preflight, materialization,
grading and other overhead. An extrapolation, not a guarantee.

## Preconditions

1. Engine checkout clean and at the pinned commit.
2. A live completion returns text — never a `/v1/models` listing.
3. The machine is quiet.
4. `preflight.sh` re-run into this batch's own output directory, passing.
