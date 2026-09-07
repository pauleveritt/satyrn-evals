> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# Brief for the next agent — after three hypotheses died in one day

**Revised 2026-09-07, later the same day.** The first version of this brief
proposed a seam-visibility experiment. That hypothesis is dead too; it is
recorded, with what killed it, in
[false completion §7](2026-09-07-false-completion.md). This revision
replaces the direction and keeps the discipline.

**Read first:** `BRIEF.md`, `ROADMAP.md`, `CLAUDE.md`,
[the harvest index](2026-08-16-harvest-index.md),
[`docs/development/lessons.md`](../../development/lessons.md),
[the V15 premise correction](2026-09-07-v15-premise-correction.md), and
[false completion](2026-09-07-false-completion.md) — the last one **banner
and §7 first**, since its body is refuted.

## Why you exist

On 2026-09-07 three hypotheses were proposed and all three were refuted,
**at zero inference cost**, against roughly one batch of machine time
saved:

1. **V15's premise** — "five single-anchor repairs leave an engine nothing
   to coordinate." The fixtures refute it: `depth-2` ⊂ `depth-3` is a
   byte-identical nested 2/3-seam ladder that V14b already ran.
2. **A controlled seam-count ladder** — its missing rung already ships as
   `plausible-wrong-fix`, and both its endpoints are pinned (12/12 twice,
   0/12 twice).
3. **False completion / seam visibility** — killed by two equally invisible
   seams closing at 13/23 and 0/23, and by `depth-3` at R3 reading **12/12**
   with the same blind suite.

Nothing new was built and no task was authored. **That is the result, and
it is a good one** — but it means you inherit an open direction, not a
plan.

## The one thing today established

**`depth-3` is not a quality floor**, a label it carried from V11c until
now. **Within one batch, one reference arm, one night**, it reads R1
**0/6** and R3 **6/6** at *each* of the two capability points — every R3
patch touching all three files. (Cite it that way. An earlier draft of this
brief paired V14b's R1 with the overnight R3 across two batches; the pooled
numbers coincide, which is how a bad derivation survives a read.)

```bash
for d in ~/satyrn-smokes/2026-09-06-overnight-232554/*depth-3*R3*; do
  echo "== $(basename $d)"; grep -h '^+++ b/' $d/cell-*/*/patch.diff | sort | uniq -c
done
```

Same base, same seeded defects, same workspace suite; **only the contract
text differs.** R3 says "the model's stored complaint timestamp lost its
timezone"; R1 says `assert None is not None`. That is a controlled,
within-task, two-rung result already on disk, and its significance for the
"floor" label was never drawn until today.

## What we trust in the instrument, and what we do not

Assembled from what actually got exercised. This is the most useful thing
in this brief; read it before designing anything.

### Trusted, and demonstrated rather than argued

- **The verdict.** Hook-written, never stdout or an exit code
  (`BRIEF.md` rule 4). Every task's evidence floor is gated per-task in
  `tests/test_agentclinic_manifests.py`: known-good accepted, known-broken
  rejected.
- **Capture separate from grading** — `BRIEF.md` rule 3, and the property
  that paid for itself today. A brand-new measure (per-seam closure) was
  computed over **96 retained cells with zero re-runs**, and it is what
  refuted hypothesis 3. This is the single most-validated thing in the
  repository. Lean on it.
- **The strict tally.** Refuses a malformed batch rather than shrinking a
  denominator, and model identity is checked from each transcript's own
  `message.model` (`scripts/tally.py:155-227`), not the requested argv.
- **Per-cell pass/fail counts, within one interleaved batch.**
- **The gates.** They caught real errors this session: `lint-docs` refused
  an over-long phase row rather than letting the planning surface drift.

### Not trusted — two were demonstrated broken today

- **`attempt.json.code` as a behavioural signal.** `OK` means "a patch and
  transcript existed and grading ran" (`attempt.py:270`). It is
  **arm-asymmetric**: a Baseline lock reaches Evals' tripwire and codes
  `REPEAT_LIMIT`; an Engine lock is cut by the engine's own breaker, exits
  0, and codes `OK`. Any per-arm statistic over these codes compares
  different things.
- **`census` `anchor_refusal` and `noop_edit`.** Structurally arm-specific
  vocabularies printed in adjacent columns of a per-arm table
  ([premise correction §4](2026-09-07-v15-premise-correction.md)).
- **`read_lock`.** Its cause is untested — recorded in `BACKLOG.md` and
  `ARCHIVE.md` — and it is task-specific: 8/1 on `misleading-locus`, 0/0 on
  both multi-file tasks in the same batch.
- **`stall`** — a magnitude with no denominator, recorded as such.
- **Any cross-batch count.** Demonstrated twice today, most cleanly:
  Baseline touched all three `depth-3` seams in 2/12 cells in V13c and 0/11
  in V14b — same task, same rung, identical arm configuration.

### The gap nobody has looked at

**Nothing ever runs a task's `public_suite`.** It is validated as a list of
command strings and emitted into the engine contract
(`manifest.py:53-76`, `engine_contract.py:93-95`) — and that is all. No
check that it is red at base, green at known-good, or covers any particular
seam.

```bash
grep -rn "public_suite" src/satyrn_evals/*.py
```

That matters because the workspace suite is what the agent uses to decide
it is finished, and it is the one artifact in the task the harness holds no
opinion about. A miswritten public suite would be invisible to every gate.
**This is a real, cheap, offline instrument gap** — no model, no network,
integration tier only.

### The uncomfortable summary

`BRIEF.md` opens with "Diagnosis first, claims much later." **The claims
layer is the trustworthy half and the diagnostic layer is not.** The
verdict, the tally and the retention property have all been exercised hard
and hold. Almost every behavioural signal is either untested, task-specific
or arm-asymmetric. Whatever direction you choose, that inversion is the
honest starting point.

## Traps, from ten wrong calls in three days

Six are in the superseded V15 brief. Four are from 2026-09-07, all made by
the agent that wrote this file:

7. **"More seams means more to read, so Engine's read-lock resistance pays
   off more."** Refuted by the batch cited for it: `read_lock` is 8/1 on
   the one-file task and **0/0** on both multi-file tasks.
8. **Proposing to author `depth-1`.** It ships as `plausible-wrong-fix`.
   Nobody had run `diff -r` over the two `base/` trees.
9. **"Invisible seams cause the agent to stop early."** Refuted by two
   equally invisible seams at 13/23 and 0/23, and by R3's 12/12.
10. **Reading `OK` as "terminated voluntarily."** It means grading ran. The
    field's own assignment site says "Never the exit code."

All ten share one shape: **a real number with an untested causal story
attached.** Numbers 7, 9 and 10 were each refuted by evidence *already on
disk and already read* in the same session. Re-deriving is not the same as
re-reading, and the failure is invisible from inside the sentence that
repeats it.

**The adversary caught 7, 8, 9 and 10.** It has now caught more than any
other activity in this project. Told to attack, handed the evidence
directly, and kept out of the context that formed the belief, it is the
highest-yield thing you can spend tokens on. Budget for it *before* a
batch, never only after.

## Rules that bind you

All of `CLAUDE.md`. The ones this cycle nearly broke or did break:

- **Search the rungs before naming a mechanism.** R0/R1/R3 are a control
  that is already run. `grep -rn "R3" ROADMAP.md` costs nothing and would
  have killed hypothesis 3 before it was written.
- **Read the gate's exit code, unpiped.** `just gates | tail` swallowed a
  status this session.
- **A detector must discriminate in both directions**, and a **structural
  zero is not an observation** — a statistic that cannot fire on one arm is
  not evidence about that arm.
- **`n=12` is the working size**; outcome differences of the size seen here
  need ~100/arm.
- **Never edit the tree while a batch runs.** Use a worktree.

## What not to build

- **No second application.** V15's case is refuted; V16 §6's stopping rule
  has not fired.
- **No `depth-1`, no `depth-3-visible`.** The first exists; the second
  tests a dead hypothesis.
- **No new census detector** until something uses it.
- **No admission machinery**, no new framework.

Weight, recomputed 2026-09-07: `src` (excluding vendored tasks) **9,660**,
`scripts`+`arms` **2,096**, `tests` **22,953**. W1 has still never run.

## Candidate directions, none chosen

Deliberately unranked, because choosing is the maintainer's and choosing
fast is how three hypotheses died.

1. **Trust the diagnostic layer, or stop reporting it.** The census is the
   project's diagnosis instrument and half its columns are not
   cross-arm-readable. Either fix what the per-arm table means, or narrow
   it to what survives. Cheapest of the four; re-scorable; blocks nothing.
2. **Close the `public_suite` gap.** An offline authoring gate: red at
   base, green at known-good, per-seam coverage recorded. No model time.
3. **Ask what R1→R3 actually buys, since it is the only controlled lever
   with a measured effect** (0/6 → 6/6, within batch, at both capability
   points). It is already run for
   `depth-3`; whether it generalises is a question the retained profile may
   partly answer for free before any batch.
4. **W1.** Overdue on measured weight, and it is where withdrawn code —
   including `scripts/rescore_seams.py`, which has no test — is removed.

## The Opus / Sonnet / Fable split

Held again, more sharply: **roughly two-thirds of the hours were
delegatable and none of the errors were.** All four new wrong calls were
reasoning about evidence. All four catches were adversarial review. Zero
implementation defects, because almost no implementation happened.

| work | who | why |
|---|---|---|
| Read evidence, choose the measure, freeze the criterion | **Opus** | All ten recorded errors live here |
| Write the spec with acceptance stated up front | **Opus** | Sonnet's quality tracks spec precision almost exactly |
| Implement against that spec | **Sonnet** | High reliability, and it finds spec gaps |
| Review the diff | **Opus** | Cheap, and verify at source rather than accepting a report |
| Attack the hypothesis **before** cells are spent | **Fable** | It has killed three plans for a fraction of one batch |
| Attack the reading **after** a result | **Fable** | Must not be the context that formed the belief |
| Run any batch | **maintainer** | Budgeted inference, frozen checkout, quiet machine |

Directions 1 and 2 above are the most Sonnet-shaped work available: both
are bounded, offline, and testable with acceptance criteria stated up
front. Neither needs a model to run. Give Sonnet the acceptance criteria
before it writes anything and it will tell you the spec is wrong instead of
improvising — and never let its report substitute for your own check at
source.

## Open items this cycle did not close

- **`BACKLOG.md` owes V15 a reopen condition.** Its old trigger is gone.
  V16 §7 already flagged that the selection rules owe one too.
- **The census cross-arm defect** is unfixed. Re-scorable, blocks nothing.
- **`scripts/rescore_seams.py` has no committed test.** It owes one or it
  should be deleted. It is the tool that refuted hypothesis 3, so it earned
  its keep once; that is not the same as earning a permanent place.
- **`arms/engine.json`'s `tools` list may mis-describe the arm** — an
  unverified review claim that Engine receives `bash` through `runner.ts`.
  Checking it is a `CLAUDE.md` condition-(d) obligation before the next
  batch.
