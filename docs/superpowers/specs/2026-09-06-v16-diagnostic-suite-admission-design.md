# V16 — the diagnostic suite, admitted on three axes

**Status: proposed 2026-09-06, awaiting maintainer confirmation.** No code
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

**A task at ceiling for one arm can be the most discriminating task in the
suite.** `plausible-wrong-fix` was discarded at Baseline 6/6. At `n=12` it
is Baseline **12/12** against Engine **6/12** — the widest gap this project
has measured. The middle-band rule, read on the reference arm alone, threw
away the best task.

**Outcomes cannot be afforded; costs can.** On V13b's 48 cells the outcome
contrast was p = 0.333 while cost-to-succeed separated at p = 0.00009. To
power the observed outcome effect needs ~100 cells per arm — about four
hours per task. Cost separates below `n = 10`. A count per cell carries far
more than a pass/fail bit.

**And the payload has been pathology, not bands.** Every engine change made
today came from reading transcripts: 973 schema refusals, and six
`NO_PATCH` cells whose mechanism runs from a missing test runner through a
read loop to a breaker that terminates before the first edit. The
comparison that surfaced the first was a null.

## 2. The rule

A task is admitted to the **diagnostic** suite when, probed at `n=12` per
arm with the arms interleaved in one batch, it shows **at least one** of:

- **(A) a nameable failure shape** — a describable, recurring pathology in
  **two or more cells of one arm**, not already represented by an admitted
  task. Named in the admission record, in one sentence, with the cells.
- **(B) a cost separation** — cost-to-succeed distributions that separate,
  reported as an exact one-sided rank test beside both medians, with **at
  least five successes in each arm**. No threshold is declared; the value
  is descriptive and the distributions are published.
- **(C) an outcome gap** — arms differing by **4 or more of 12**.

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

1. **`cost_to_succeed` in the tally.** `scripts/tally.py` gains a per-arm
   block: the distribution of total tool calls over **passing** cells, its
   median, and its `n`. Computed offline from the retained pathology counts
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
  over V13b's and V13c's retained cells reproduces the medians already in
  their `RESULT.md` files** — the re-scoring property, demonstrated rather
  than asserted.
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
