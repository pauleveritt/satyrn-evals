> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V16 — the diagnostic suite, admitted on three axes

**Status: proposed 2026-09-06; amended the same day after review, before
any code. Awaiting maintainer confirmation.** Three of the arguments in the
first draft were wrong and are corrected in place, with the corrections
marked. See §7. No code
until it is confirmed (`CLAUDE.md`). This changes a recorded design
decision — the admission rule in `BRIEF.md`'s "Two selection rules" — so it
is the maintainer's to accept.

## 1. What changed, and why the rule must

`BRIEF.md` names the unsolved problem: "Nothing in the prior repository
reliably produced tasks in the middle band. Every suite it built
saturated." Three measurements today say the diagnosis was wrong in a
specific way.

**The inventory was an artifact of `n=6`.** The whole V12 placement profile
ran at `n=6`. `depth-2` Baseline has since read 3/6, 7/12, 2/6 and 7/12.
V13c re-measured three "saturated" tasks at `n=12` and found the suite
wider than recorded (`~/satyrn-smokes/2026-09-06-v13c-200158/RESULT.md`).

**A task at ceiling for one arm can still discriminate.**
`plausible-wrong-fix` was discarded at Baseline 6/6. At `n=12` it is
Baseline **12/12** against Engine **6/12**. What refuses it is V5a point 4
— "a task whose reference arm sits at or near ceiling admits nothing"
(`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md:111-113`)
— **not** the middle-band reading, which V5a already applies to the arms
under comparison. And in fact no admission rule was ever applied to this
task: the V12 profile was reference-arm-only, so no comparison arm ran on
it. **The precise reopen is: V5a point 4 assumes a product arm cannot sit
below a ceiling reference; `plausible-wrong-fix` records exactly that.**
(Corrected after review; the first draft said the middle-band rule read on
the reference arm threw the task away, which restates a superseded reading.
It is also not "the widest gap this project has measured" — V11c recorded
10/12 vs 5/12 pre-pin, and the V5a pilot 6/6 vs 0/6.)

**Outcomes cannot be afforded. Whether cost can is now the open question.**
Powering the observed outcome effect needs ~100 cells per arm, about four
hours per task. Cost-to-succeed in **tool calls** separated at p = 0.00009,
but **every such p-value is the floor of the exact test at that `n`** —
complete separation, silent about magnitude — and the same cells in
**tokens** read p = 0.247 / 0.057 / 0.036. On `plausible-wrong-fix` the
call separation is the surface: one `bash` turn against three `read` turns,
with token medians 11,659 and 12,048. **The unit must be decided before it
is frozen.**

**And the payload has been pathology, not bands.** Every engine change made
today came from reading transcripts: the 973 schema refusals were found and
fixed that way, and the comparison that surfaced them was a null. The six
`NO_PATCH` cells are a second, *unexplained* pathology — see §7 for what was
claimed about them and refuted.

## 2. The rule

A task is admitted to the **diagnostic** suite when, probed at `n=12` per
arm with the arms interleaved in one batch, it shows **at least one** of:

- **(A) a nameable failure shape** — a pathology named by a
  **transcript-computable predicate**, not prose, occurring in two or more
  cells of one arm **and absent or rarer in the other arm**. The
  cross-arm clause is the discriminator (`BRIEF.md` rule 8): at temperature
  1.0 some two-cell shape exists in nearly every arm, so a shape present in
  both is a model property, not an engine diagnostic.
- **(B) a cost separation** — **provisional until §3 decides the unit.**
  Reported as an exact one-sided rank test beside both medians **in both
  units** (tool calls and tokens), with at least five successes in each
  arm, and beside the **unconditional** figure — total cost divided by
  successes, which needs no conditioning. A separation that holds in one
  unit and not the other is **not** an admission; it is a finding about the
  tool surface.
- **(C) an outcome gap** — arms differing by **4 or more of 12**,
  **provisional until a second interleaved batch repeats it**. Two arms at
  the same true rate differ by ≥4/12 about 15% of the time (one-sided
  ~7%), which this project has already seen: `depth-2` Baseline read 2/6
  and 7/12 under one configuration.

The three are recorded **separately and never pooled**, and the admission
record names which axis admitted the task. This extends the V5a rule that
keeps outcome, retained-patch production and conditional patch quality
apart; cost-to-succeed is a fourth quantity under the same discipline, and
is **always conditional on success**.

The **grader-fixture** rule in `BRIEF.md` is untouched: offline,
deterministic, no network, no third-party dependencies. This changes only
the diagnostic-workload rule.

## 3. What this phase ships

Deliberately small. The suite's problem was never machinery.

1. **`cost_to_succeed` in the tally — only once the unit is decided.**
   `scripts/tally.py` gains a per-arm block reporting **both** units (tool
   calls and turn-level `usage` tokens) over **passing** cells, each with
   its median and `n`, plus the **unconditional** cost per success. Both,
   because they disagree: p = 0.00005 against p = 0.247 on the same cells. Computed offline from the retained pathology counts
   that V10 already produces (`pathology.py:52`), so it is re-scorable from
   disk and needs no new capture. A cell whose pathology is `unmeasured` is
   **`unmeasured`, never zero** — the discipline four silent-zero incidents
   paid for.
2. **The admission record** — a short document per admitted task naming the
   axis, the cells, and the failure shape in one sentence.
3. **`BRIEF.md` and `ROADMAP.md` amended** with this rule, the old wording
   kept visible and dated.

**No new tasks are authored in this phase.** V13c's evidence is that four
of five runnable tasks already carry information on at least one axis;
`framing-2-edit` is the only one that carries none. Authoring waits until
the engine's queued fixes land and the suite is re-measured against a
changed engine, because every band moves when the engine does.

## 4. Non-goals

Statistical power on outcomes; any admission claim about a task not probed
at `n=12`; a second application; workflow/session tasks; changing the
grader-fixture rule; `framing-2` (creation-capable capture is still owed);
any new framework — this is one metric and a rule.

## 5. Acceptance

- `scripts/tally.py` reports `cost_to_succeed` per arm, and **re-running it
  over V13c's retained cells reproduces the medians in its `RESULT.md`** —
  the re-scoring property, demonstrated rather than asserted. (V13b's
  `RESULT.md` carries no cost figure; its cost numbers were computed after
  reading the cells and are **post hoc**. V13c pre-declared the metric.)
- A sibling for the blind spot: `depth-3`'s two most expensive Engine cells
  read `unmeasured: unknown_event` because pi emitted
  `compaction_start`/`compaction_end`, which are outside V10's vocabulary
  (`src/satyrn_evals/pathology.py:21-29`). Under this metric, cost would go
  blind precisely on the most expensive cells. Recognise both events before
  shipping, and label any hand-counted figure as hand-counted — the "300
  calls" in V13c's `RESULT.md` was counted outside the instrument.
- A refusal sibling: a cell with `unmeasured` pathology makes the arm's
  cost `unmeasured` and does not silently drop out of the denominator.
- A success sibling: an arm whose cells are all measured reports a
  distribution whose `n` equals its passing-cell count.
- Full gates green (`just gates`).

## 6. Stopping rule, for the authoring that follows later

When authoring does happen: at most **four** task variants, each probed
once at `n=12` both arms. If fewer than two are admitted on any axis, stop
and conclude the application is exhausted — the answer is then a second
application, not more variants of this one.

## 7. What the first draft got wrong, recorded

Written 2026-09-06, corrected the same day after an independent review, and
kept rather than edited away.

1. **"The mechanism runs end to end."** The claim that a missing test
   runner drives a read loop that the breaker then terminates before any
   edit. Two of three links are refuted by cells in the same batches: eight
   bare-Pi cells reached an identical-read run of ≥5 before any edit and
   **0 of 8 recovered**, so the breaker does not cost the patch; and the
   Baseline lock cells on `misleading-locus` run `pytest` as their *second*
   call and lock anyway, with Baseline locking 5/12 there against Engine's
   0/12. The lock's cause is **untested**.
2. **The cost axis as settled.** Its p-values are the exact test's floor at
   that `n`, and the token unit disagrees with the call unit on the task
   carrying the strongest signal.
3. **The reopen sentence.** It named the middle-band rule; what actually
   refuses `plausible-wrong-fix` is V5a point 4, and no admission rule was
   ever applied to that task because the profile was reference-arm-only.

All three share one shape, which is also this project's recorded failure
mode: a claim stated more broadly than the corpus behind it. `BACKLOG.md`
owes a reopen condition for the selection rules — `CLAUDE.md` says each
protected decision has one, and the selection rules have none.
