# V11c — spike protocol and V13 firewall

**Status: CONFIRMED by the maintainer, 2026-09-05.** Gate [G] #2 is closed.

Per the
[trim proposal](../research/2026-09-05-v11-trim-and-spike-proposal.md) §4
step 3, this gate could not be self-confirmed; it was confirmed explicitly.

**Confirmation is not a start signal.** It authorizes the mini-probe and the
spike *as specified here*, and nothing beyond them. §0's five preconditions
still gate execution, and **three of them can still stop the run**: an
unmeasured smoke (2 or 3) sends V10 back for a discriminating fixture before
any budgeted cell, and a red preflight (5) stops it outright. Rules §2.4 and
§2.5 can also end the sequence after the mini-probe without a spike ever
running. None of those outcomes reopens this confirmation — they are the
protocol working.

**Everything below must be frozen *before* the mini-probe runs.** A rule
written after seeing a count is not a rule.

## 0. Preconditions

| # | Precondition | State |
|---|---|---|
| 1 | V11a-trim and V11b-trim landed, full gate green | *pending* |
| 2 | Baseline V5d smoke passed, pathology `measured: true` | *pending* |
| 3 | Engine V5d smoke passed on a **generated** contract | *pending* |
| 4 | Per-cell input-token floor measured inside a materialized workspace | *pending* |
| 5 | `preflight.sh` green: pins, clean trees, **live one-word completion** | *pending* |

If precondition 2 or 3 comes back `unmeasured`, **V10 is amended with a
discriminating fixture and test before any budgeted cell.** A non-empty
transcript is not proof V10 can measure it.

## 1. What this buys, and what it does not

It buys an early product-level signal for **at most 36 cells and two
unattended nights**, before the plan's single largest inference block (V12).

It is **exploratory**. It is **not preregistered** and **not admissible**. It
admits no workload, replaces no phase, and licenses no mechanism sentence.

## 2. Mini-probe — frozen before it runs

Baseline only, **R1**, `n=4`, three candidate tasks, 12 cells, sequential.

**Candidates:** `plausible-wrong-fix`, `misleading-locus`, `depth-3`.
`framing-2` is excluded — Engine cannot create files, and `git diff HEAD`
drops untracked files, so it would measure an adapter limit as model
behavior.

**No usable per-task prior exists.** Block B is a different model and
harness; overnight block 7's rates are on fixtures that are never named and
cannot be mapped onto these six; `misleading-locus` has nothing at all. Any
task choice made from recall would be recall dressed as evidence.

**Primary metric:** successful attempts out of four. Retained-patch
production and conditional retained-patch quality are recorded **separately**
and never substituted. The metric does not change after the results appear.

**The selection rule, frozen:**

1. Exclude an operationally invalid candidate; it has **no** success count.
2. If any valid candidate is interior (`1/4`, `2/4`, `3/4`), pick the one
   maximizing `min(successes, 4 − successes)`.
3. If none is interior but a valid candidate is `0/4`, pick a floor
   candidate. **A Baseline floor is not a capability wall** — this project
   has recorded Engine gains from Baseline-floor tasks.
4. If every valid candidate is `4/4`, **the spike does not run**; author R0
   before proceeding toward V12.
5. If no candidate is valid, repair the instrument and run **no** further
   model cell until a new confirmed protocol says how.

**Ties:** `misleading-locus`, then `depth-3`, then `plausible-wrong-fix`.

The result may state "no interior count observed among these candidates." It
may **not** generalize that R1 has no headroom.

Selecting from the reference arm alone keeps arm comparison out of the cell
choice.

## 3. Spike — frozen before it runs

Baseline vs Engine, the selected task at R1, **`n=12` per arm**, 24 cells,
interleaved on a seeded schedule committed before the first cell.

**Two arms, not three.** Baseline vs Engine is the only contrast with a prior
(`stringified-annotations` 6/6 vs 0/6; `local-pings` 2/4 vs 0/4). Envelope is
a decision owed its own proposal and V13 must preregister it.

**`n=12` is a spending limit, not a powered design.** Under true rates 0.50
versus 0.125, exact enumeration gives about **36% power** at `α = 0.025`. The
spike therefore carries **no significance threshold**; Fisher's one-sided
value is descriptive beside the counts and bands. **No extension after
reading the result.**

**Expected cell identities.** 24 cells, each its own output directory, each
carrying task, rung `R1`, `contract_digest`, model, and arm. The strict tally
reads exactly those 24 and **refuses** — missing, duplicate, aborted,
unexpected-task, wrong-rung, wrong-digest, wrong-model, wrong-arm — rather
than shrinking a denominator.

**Reporting states.** Counts only; never a duration. `workspace_escapes`,
`overlay_windows` and `unmeasured` reported **per arm**. Flagged cells stay
**in** the denominator. `unmeasured` is its own state, never zero.

## 4. Confounds, predeclared

- **Tool surface.** Baseline `read,bash,edit,write`; Engine `read,edit` with
  its prompt wrapped by the handoff builder. Meaningful only as *"the shipped
  Engine versus bare Pi as shipped"* — product-level. No mechanism sentence.
- **A null is uninformative about machinery**, because the missing Engine
  test runner may dominate. Written down before running, not after.
- **Grader hunting is not closed by any text check.** V10's counters are
  tripwires: `workspace_escapes` misses paths embedded in `bash`;
  `overlay_windows` misses paraphrase. Engine still has `read`.
- **Timeout harvesting.** The adapter harvests `git diff` only after `pi`
  exits, so a timeout retains no intermediate patch. Do not infer a
  capability wall from a completion floor under this adapter.
- **Context files.** Both arms pin `-nc`. Without it the arms are not at
  parity — Engine already passes `--no-context-files` and the scratch
  Baseline wrapper did not.
- **Model identity.** Live one-word completion before the batch, never
  `/v1/models`; one omlx process for all cells; model id read back from each
  transcript.
- **Provenance.** Record the evals SHA and an empty `git status --porcelain`.

## 5. Predeclared consequences — what each outcome changes

| Outcome | Consequence |
|---|---|
| Engine higher than Baseline | Retain the product-path hypothesis; continue V12. Still exploratory. |
| Tie, or Engine lower, instrument valid | Continue the reference-only V12 profile, **and** make the missing Engine test runner a prerequisite before any V13 null is read as evidence about the Engine composite. |
| Both arms ceiling | Bring R0 forward before further comparison work. |
| Any instrument-invalid batch | Repair and re-smoke the substrate before another model cell. |

## 6. The V13 firewall — frozen here, reading no spike outcome

Both algorithms below are frozen **now**, use **reference-arm data only**,
and are never revised in light of a spike result.

**6.1 Primary-cell selection (V13).** From V12's reference-arm profile,
ordered, first match wins:

1. Eligible cells are **pure-edit repair** task-rungs placed **below ceiling
   and above a capability wall** for a named model.
2. Among eligible cells, prefer the **interior** band, maximizing distance
   from both bounds.
3. Ties break by task name ascending, then rung ascending (R0 < R1 < R2 < R3),
   then model identifier ascending.
4. That yields **exactly one** primary `(model, task, rung)` cell. Any other
   eligible cell is a **descriptive replication**, not an independent chance
   at a positive claim.

**6.2 Envelope budget selection (V13).** Envelope's cap is set from the
**measured per-cell input-token floor inside a materialized workspace**
(precondition 4) plus reference-arm consumption recorded in V12 — never from
the de-admission record's 900 s / 8192 / 80k, which are **pi and model
settings, not what `envelope-cap.ts` capped**. The cap is a fresh choice, it
is argued in V13's own proposal, and the extension is pinned by digest.

**6.3 Disclosure.** If the V13 primary cell **coincides** with the spike
cell, V13 discloses the prior peek and labels the fresh comparison a
**replication**. **Spike cells are never pooled with V13 cells.**

**Why a firewall at all.** The `local-pings` precedent is narrower than
first stated: that task was de-admitted because Baseline 3/8 and Engine 4/8
occupied the **same band**, not because its preregistration followed an arm
comparison. The general contamination risk still applies prospectively, which
is what this section closes.

## 7. What the maintainer is being asked

1. Confirm §2 — the mini-probe's metric, candidates, and frozen rule.
2. Confirm §3 — two arms, `n=12`, no threshold, no extension.
3. Confirm §5 — the predeclared consequences.
4. Confirm §6 — both V13 algorithms, frozen before the spike.

Confirming this document authorizes **the mini-probe and the spike, and
nothing beyond them**. V12 and V13 remain separate phases needing their own
proposals.
