# Release two — constraints for the R0 design sitting

Written 2026-09-15 after release one's stated negative
(`2026-09-15-release-one-outcome.md`) and the lesson "We built the remedy for
the failures we saw, and the failures we saw were the harness's"
(`docs/lessons.md`). These bind the R0 sitting and the spec it produces. The
spec may add to them; changing one needs the maintainer's explicit decision,
recorded in the spec with the reason.

## 1. Order of work

No Engine component is designed, planned or built until steps 1–4 are done on
the harness the comparison will use.

1. **Harness validity.** The measurement defects listed in the outcome page
   are fixed or explicitly accepted, with fixture tests both directions:
   assertion explanations kept in AgentClinic rungs, a per-turn output cap
   applied to both arms, tripped worktrees harvested and graded as a declared
   secondary, k re-measured, and tool parity between arms.
2. **Task validity at qualification.** A candidate qualifies only if its
   prompt determines the structural choices its hidden suite asserts (where a
   class lives, which function refuses what, which files may change). The
   check is recorded per task: a solution written from the prompt alone, by
   someone other than the task's author and without the plan's code, passes
   the hidden suite. A task that fails this is a generator defect, not a
   ceiling.
3. **Admission with diagnosis.** Every admission cell gets a turn-by-turn
   reconstruction and is classified by its binding constraint: information,
   ambiguity, capability, budget, or finishing (a reconstructed pass-state
   the cell did not stop at). The class, the pass-state turn if any, and the
   reconstruction command are in the admission result. A count without a
   class does not admit a task.
4. **Offline counterfactual.** For each proposed Engine remedy, its effect is
   estimated on the retained admission cells before it is built. The estimate
   is valid only for a remedy whose effect begins at or after the point
   measured (for example, stopping at a reconstructed pass-state); a remedy
   that changes earlier calls cannot be scored from recordings and must say
   so. A remedy is built only if its estimate, on the diagnosed classes,
   clears the win threshold with the stated power.

## 2. What a claim may target

- **Only a constraint class that dominates the ceiling set's failures** on the
  clean harness. Information- and ambiguity-bound failures are task defects
  under identical prompts; they are fixed in the task or the task leaves the
  set, never claimed against.
- **The stipulated effect comes from the counterfactual,** not from a hoped-for
  rate. If the counterfactual cannot reach the threshold at the planned n, the
  claim is resized or not made.
- **Baseline rates are measured, not assumed.** A task whose admission rate
  makes a win under-powered by the rule's own test is floor or out.

## 3. Gates that ask why

- **Route proof** reads, per cell, whether each remedy acted on the diagnosed
  constraint, not only whether guards fired.
- **Any remediation iteration** names the constraint class it targets and the
  admission cells that justify it, and is measured on development tasks that
  exhibit that class. A development task that cannot exhibit the class (too
  easy, or no tests) cannot measure the remedy.
- **A mid-course finding that changes the diagnosis stops building** until the
  counterfactual is redone.
- **The win rule reads the verdict at the pre-registered line, per arm, by the
  same reconstruction, never by the process exit code.** The run budget may
  exceed the line; a cell whose exit code is a budget trip can still hold a
  pass state inside it, and both arms are read by one instrument (maintainer
  ruling 2026-09-18).

## 4. Carried from release one

- Two-uid isolation for every deciding record; no container, sandbox or
  wrapper process, ever.
- The launcher is the only path to a model; records frozen and committed;
  infrastructure stops, model outcomes never do.
- Identical prompts, tools, model and sampling across arms; the Engine's own
  tool results and messages are the product.
- Opus steers, designs and reviews; Sonnet implements; Fable only when the
  maintainer names it; no haiku.
- Schedules are stated in hours at the measured k, and a phase builds in half
  a day.

## 5. Questions R0 must answer

1. Is "finishing" (reconstructed pass-state not stopped at) the dominant class
   on build tasks under the fixed harness, and what does stopping there score
   offline on the retained cells?
2. Which new ceiling candidates exist whose Baseline failures are budget- or
   finishing-shaped, and do they pass the task-validity check?
3. Is 9B the right model for the claim, or does the diagnosis point to a
   different model or budget as the honest setting?
4. What is the smallest claim the counterfactual supports, and is it worth a
   release?
