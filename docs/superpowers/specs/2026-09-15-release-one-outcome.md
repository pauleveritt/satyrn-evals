# Release one — outcome: a stated negative

Decided 2026-09-15 by the maintainer, under the spec's own completion rule
("If the four engine pieces are in place and no ceiling task rejects, release
one stops with a stated negative"). Phase 4 was not run. Engine frozen at
`8049d73`; evals at the commit that adds this page.

## The claim, and the answer

The claim was that on Ornith 1.5 9B (isolated as `satyrn-cell`, k = 3,
32,000 output tokens and 48 turns, identical prompts, tools, model and
sampling), `/implement` delivers a passing candidate within budget more often
than bare Pi on at least 2 of 3 ceiling tasks.

**It will not hold, and the reason is not a missing Engine piece.** Every
ceiling task fails for a reason the Engine cannot reach under identical
prompts, and the one task where budget binds is one Baseline already passes
too often for a win to be powered. Admission, route proof and an offline
reconstruction of every retained cell agree.

## Evidence per ceiling task

Counts are within budget; every counted pass was uncontaminated. Records and
results are under `records/`; cells under `~/satyrn-runs/`.

| task | Baseline admission | Engine route proof | binding constraint |
|---|---|---|---|
| `agentclinic-repair-depth-3` R1 | 0/4 (`dbc571c`) | over budget (`da0f969`) | information: the R1 text omits the one line naming `tzinfo` |
| `selfhost-run-record-gate` R1-plan | 0/4 twice (`4212ed3`, `b94b68d`) | over budget (`b467aa1`) | prompt ambiguity plus the allowlist |
| `selfhost-docs-linter` R1-plan | 1/4 (`edda258`) | over budget (`fcdfc5f`) | budget, after a passing state |

**depth-3.** Of 7 cells (4 Baseline, 3 Engine) none found the third seam,
`first.timestamp.tzinfo is not None`. R1 gives only "assert None is not None";
pytest's explanation line is what R1 strips. Two cells reached 12 of 13 and
said they left `models.py` untouched. Two cells (one per arm) spent the whole
budget in a single 32,000-token turn circling that sentence.

**run-record-gate.** Reconstructing each worktree from its transcript and
grading every mutation offline: 5 of 9 cells put `RunRecordError` in
`errors.py`, as the prompt's wording invites, and `errors.py` is outside
`source_paths`, so the patch is rejected. With it allowed, 8 of 9 reach 15 of
20 and fail the same five tests: the prompt's "gate rules" read as `gate()`'s
job, the hidden suite expects `load_run_record` to refuse. One Baseline cell
avoided both, held a passing worktree at turn 39, and overran polishing its
own tests. The Engine's derive listed `errors.py` as writable.

**docs-linter.** Three of five cells reached a passing state (turns 28, 39,
28), then spent 10–20 turns on the plan's clean-up steps and two tripped.
Baseline's within-budget rate is plausibly 0.15–0.3; at n = 12 it lands at
2 or more with probability 0.56–0.84, which the rule calls under-powered.

## What the Engine did on the live model

- Guard 4 bounded every bash command (6–38 per cell) and cut a root-wide hunt
  for the acceptance tests at 120 s that cost a Baseline cell 1,800 s.
- `self_test` was never called in the three route-proof cells. The Phase 3b
  redirect (`8049d73`) replaced ad-hoc pytest runs (24 to 3, all redirected) on
  development tasks; the completion gate never fired, because ceiling cells
  never stop before the budget does. Outcomes did not move.
- Two Engine defects were found and fixed on the way: derive made only
  test paths writable on a request naming no source file (`cf71c74`), and the
  protocol exchange re-synced a read-only export and crashed (`56f4ac0`).

## What is wrong with the measurement, stated for release two

1. R1 for AgentClinic strips assertion explanations that are text, not
   location. depth-3 does not discriminate arms at R1.
2. R1-plan can drop decisions only the stripped code made; qualification does
   not check that the prompt determines the hidden suite's structural choices.
3. The budget sits inside Baseline's finishing distribution on build tasks,
   so Baseline rates are 0.15–0.3, not the stipulated 0.10.
4. Per-turn `max_tokens` equals the whole budget; one runaway turn ends a cell.
5. BUDGET_EXCEEDED worktrees are discarded ungraded, so "never got there" and
   "got there and kept going" look the same.
6. The Engine arm is not tool-identical in practice: its edit schema allows
   one replacement per call, its prompt is 3–4 times Baseline's and lists
   carried files as writable, and derive admits paths the grader rejects.
7. The probe's k = 1 total (36.5 tok/s) is well below single-stream decode
   (55.9 tok/s); k = 3 needs re-measuring before it is relied on.

<div class="record-recompute" markdown="1">

## Recompute

```
python3 evidence/2026-09-15-release-one-outcome/cells.py        # per-cell spend over ~/satyrn-runs
python3 evidence/2026-09-15-release-one-outcome/reconstruct.py  # replay and offline-grade every mutation
python3 evidence/2026-09-15-release-one-outcome/stats.py        # thresholds, power, P(>= 2 of 3)
```

The full review, with per-cell tables and citations, is
`evidence/2026-09-15-release-one-outcome/fable-review.md`. The reconstruction
reproduces the harness verdict for 11 of 14 graded cells; its pass-states are
lower bounds.

</div>
