> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V11b-trim — a reproducible two-arm substrate

**Status: confirmed 2026-09-05.** Design of record is the revised proposal
[`2026-09-05-v11-trim-and-spike-proposal.md`](../research/2026-09-05-v11-trim-and-spike-proposal.md),
§9 items 1–3, confirmed by the maintainer on 2026-09-05. Sibling spec:
[V11a-trim](2026-09-05-v11a-trim-contract-rungs-design.md). Thin by
instruction (proposal §2.5).

## 1. What ships

1. `satyrn_evals/attempt_pi.py` plus a console script — the Baseline
   adapter, moved in-tree from the scratch wrapper.
2. `arms/baseline.json` and `arms/engine.json` — committed arm definitions
   with argv template, tools, model id, and pins.
3. A small reader that makes those files **executable inputs**, not parallel
   documentation.
4. `scripts/preflight.sh`, `scripts/interleave.py`, `scripts/tally.py`.

## 2. Non-goals

- **Envelope.** Deferred to V13 scoping (proposal §2.4). `pi` 0.84.4 has no
  turn or token budget flag, and the 900 s / 8192 tokens / 80k context in
  the de-admission record are pi and model settings, **not** what
  `envelope-cap.ts` capped — nobody knows what it capped. The cap value is a
  fresh choice that must be argued, and a kill is not an in-loop cap.
- **An arm registry or framework.** Two JSON files and one reader.
  `CLAUDE.md`: no framework before three concrete implementations need the
  same shape.
- **Rungs, the manifest, the generated contract.** V11a.
- **Running any cell.** The smokes are the proposal's step 2; the
  mini-probe and spike are behind a separate maintainer gate.
- **Creation-capable patch capture.** A V12 entry gate — see §6.

## 3. The adapter

`attempt_pi.py`: `--model`, `--tools`, then `git diff HEAD` harvested after
`pi` exits, written to `SATYRN_PATCH`; the JSON stream teed to
`SATYRN_TRANSCRIPT`.

- The prompt is `SATYRN_TASK_CONTRACT`, exported by evals
  (`attempt.py:108-110`). **The adapter takes no `--rung`** — this is the
  seam that keeps the two tracks independent.
- Model is addressed in the pi-facing form `omlx/<id>`; the server
  advertises the bare id. Both naming surfaces are recorded.

## 4. Arm definitions

```json
{
  "arm": "baseline",
  "argv": ["…"],
  "tools": ["read", "bash", "edit", "write"],
  "model": "omlx/gemma-4-12B-it-MLX-8bit",
  "pins": {"pi": "0.84.4", "engine_commit": null, "digests": {}}
}
```

`arms/engine.json` pins engine commit `75d4863` and the sha256 of
`engine.ts` and `mutator.ts`. Preflight asserts that exact HEAD, a clean
tree, and the digests. The reader refuses an arm file missing any pin.

## 5. Scripts as instrument

These live outside production code and are still part of the instrument.

- **`preflight.sh`** — asserts arm pins; a **live one-word completion**
  against the model, never `/v1/models`; writes the realized arm order
  before the first cell; records the evals SHA and an empty
  `git status --porcelain`.

  *Why a completion and not a listing.* A phantom `gemma-4-26B-A4B-it-OptiQ-4bit`
  was advertised on `:8001` during the 2026-09-05 session, with weights
  nowhere on the machine, and cleared later the same session. The listing is
  not stable within a session. Precedent: the harvest index's "preflight
  that could not fail".

- **`interleave.py`** — seeded, committed schedule construction. Writes
  **one directory per expected cell**, because `run` cannot interleave and
  `summarize` needs a `summary.json` anchor, so twelve `run --n 1` calls
  into one directory would overwrite it.

- **`tally.py`** — reads exactly the expected `summary.json` set and
  **refuses** rather than shrinking a denominator: missing, duplicate,
  aborted, unexpected-task, wrong-rung, wrong-digest, wrong-model, or
  wrong-arm. Reports counts only. Flagged cells stay in the denominator.

## 6. Stated limits

- **`git diff HEAD` drops files created by `write`** (untracked). Harmless
  on pure-edit repair, fatal for `framing-2` and for build shapes.
  `git add -A` is **not** the fix — it would sweep a model's `uv run pytest`
  residue into the patch and trip the allowlist check. The limit is
  documented, not papered over. Creation-capable capture is a **V12 entry
  gate**, because `framing-2` otherwise measures this adapter limit as model
  behavior.
- **Timeout harvesting.** The adapter harvests `git diff` only after `pi`
  exits, so a timeout retains no intermediate patch. Report this beside
  retained-patch production; do not infer a capability wall from a
  completion floor under this adapter.
- **No durations.** Counts only (`BRIEF.md`).
- **Tool surface is a confound, predeclared.** Baseline holds
  `read,bash,edit,write`; Engine holds `read,edit` and wraps its prompt with
  the handoff builder. Any comparison is meaningful only as *"the shipped
  Engine versus bare Pi as shipped"* — a product-level comparison, no
  mechanism sentence.

## 7. Evidence floor (BRIEF rule 2, rule 6)

**Default tier** — no model, no network, no subprocess.

| # | Refuses | Accepts |
|---|---|---|
| 1 | an arm file missing a pin | a complete `baseline.json` |
| 2 | an arm file with an unknown tool name | the four Baseline tools |
| 3 | argv construction with no model | Baseline argv built from `baseline.json` |
| 4 | — | Engine argv built from `engine.json`, differing only in tools/argv |
| 5 | a tally over a **missing** expected cell | a tally over the exact expected set |
| 6 | a tally over a **duplicate** cell | (same success row as 5) |
| 7 | a tally over a **wrong-rung** cell | a tally where every cell's rung matches |
| 8 | a tally over a **wrong-digest** cell | matching digests |
| 9 | a tally over a **wrong-model** cell | matching model |
| 10 | a tally over an **aborted** cell (`aborted.json`) | all `summary.json` |
| 11 | — | the interleave schedule is reproducible from its recorded seed |

**Integration tier.** The adapter against the existing `fake_pi_v4` fixture
produces a patch and a transcript. Marked `integration`.

## 8. What this phase does not prove

It ships the substrate; it measures nothing. The two V5d smokes (proposal
step 2) are the first evidence that either arm runs, and they are
**required**: the in-tree Baseline adapter is a new executable, and Engine
with a *generated* multi-file contract has never run.

The Baseline smoke also carries **V10's vocabulary duty**: its pathology
block must read `measured: true`, and the observed event types, tool names,
and `bash`/`write` argument shapes are checked against the parser. All eight
preserved 2026-09-03 Baseline reprobe transcripts currently read
`unmeasured: unknown_event` because they contain `tool_execution_update`.
A non-empty transcript is not proof V10 can measure it. If either smoke is
unmeasured, V10 is amended with a discriminating fixture and test **before
any budgeted cell**.

## 9. Amendment — `-nc` pinned in both arms (maintainer, 2026-09-05)

Recorded as an amendment, not edited into §4, per `CLAUDE.md`.

Measurement, same model and prompt: an empty directory cost 1,267 input
tokens, this repository's root cost 9,753, and the root with `-nc` cost
**686**. `pi --help` documents `--no-context-files, -nc` as "Disable
AGENTS.md and CLAUDE.md discovery and loading," so ~93% of the repo-root
call was context-file discovery and pi's own floor is ~686 tokens. Full
record, including a retracted attribution and two unresolved figures:
[`2026-09-05-pi-context-file-loading-and-arm-parity.md`](../research/2026-09-05-pi-context-file-loading-and-arm-parity.md).

**`arms/baseline.json` pins `-nc`, for two independent reasons.**

1. **An undetected contamination surface.** A stray `AGENTS.md` in a future
   task's `base/` would silently inject instructions into the model's
   context and nothing would flag it — the V7/V8 detector scans for grader
   overlay text, not instruction files. Pinning closes the surface by
   construction, which is cheaper than a second detector.
2. **Arm parity.** `satyrn-engine` already passes `--no-context-files`
   (`satyrn-engine/src/satyrn_engine/attempt.py:240-264` at `75d4863`), so
   **no Engine change is owed** — but the scratch Baseline wrapper has no
   such flag, and pi's discovery includes *home* files. A Baseline cell in a
   materialized workspace therefore loads ~3 KB that Engine is shielded
   from. That is `BRIEF.md` rule 8's "an arm protected from a harness defect
   its rivals were exposed to", with Engine as the protected arm, and it
   applies retrospectively to the eight preserved 2026-09-03 Baseline
   reprobe cells. It does **not** overturn the `local-pings` de-admission,
   which rested on both arms occupying the same band.

**Added duty for `scripts/preflight.sh` (§5).** It records the real per-cell
input-token floor **measured from inside a materialized workspace**, during
the V5d smokes. Real attempts do not run in the repository root —
`run_workspace` materializes a clean workspace and the adapter runs there —
so the earlier 13.6k figure was an artifact of test location, not a property
of the arms. That measured number is the input to the Envelope cap decision
(§2 non-goals; proposal §2.4), and it must be a measurement, not an estimate.

## 10. Correction — `ruff format` was never this project's gate

Recorded, not edited away.

The V11b implementation plan listed `uv run ruff format --check .` in its
definition of done. **That was my error in writing the plan, not a defect in
the work.** This project has never run `ruff format`: the `Justfile` has no
format target, `pyproject.toml` configures `ruff check` only, and
`.github/workflows/pages.yml` runs the strict docs build and nothing else.

Recompute:

```bash
grep -n ruff Justfile .github/workflows/*.yml    # no match
uv run ruff format --check . 2>&1 | grep -c 'would be reformatted'   # 75
```

75 files across `src/`, `tests/` and `tools/` would be reformatted, all
**pre-existing** and none introduced by V11a or V11b. The implementing agent
formatted its own files, reported the tree-wide failure, and **declined to
reformat the rest** — the correct call twice over: the work was not V11b's,
and a tree-wide reformat touches files whose diffs this project reads as
evidence.

**A second correction, mine.** I first attributed those 75 to a misinvocation
sweeping in the deliberately excluded `src/satyrn_evals/tasks/` fixture tree,
and reported the gate as passing. That was wrong: my count grepped for
`Would reformat`, while ruff emits `unformatted: File would be reformatted`,
so the check silently returned zero. **A detector that cannot fire reported a
clean result** — the exact shape `BRIEF.md` rule 8 exists to catch, and the
harvest index's "preflight that could not fail". It is recorded here because
the failure was invisible from inside the sentence that stated it.

**Standing decision:** `ruff format` is not adopted as a gate by this phase.
`uv run ruff check` remains the lint gate. Whether to adopt formatting
tree-wide is its own proposal, and a `W1`-shaped one — a single mechanical
commit, not something folded into a feature phase.
