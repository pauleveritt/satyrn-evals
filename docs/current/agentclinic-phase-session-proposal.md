# Proposal: build the phased application as a session

Written 2026-09-08, after twelve Baseline sessions on the synthetic task.
**This proposes work; it authorizes no implementation and no spending.**

## Why the synthetic task is the wrong vehicle

`session-ordering-regression` was built to carry a cross-prompt dependency: a
later request that regresses an earlier one. Twelve sessions say it does not
carry it in practice.

- The regression is reached only by refactoring `normalize` into a shared
  helper. **No session did — 0 of 8 measurable.** The route was never entered.
- The hazard is therefore *optional*. Making it reliable would mean asking step
  2 for something impossible without touching the shared code, which
  manufactures the accident instead of observing one.
- Its yield was three fully gradable sessions out of twelve.

The task keeps its value as a **grader fixture**: its witness proves
per-checkpoint grading detects a regression when one happens. That is a claim
about the machinery, and it stands.

## Why the phased application is the right one

`agentclinic-repair-*` already vendors an application with a **three-phase
roadmap**, and its acceptance suite is that roadmap: the Phase 3 contract with
Phases 1 and 2 carried forward as preservation checks
(`overlay/test_acceptance.py:1-5,44`). Nothing invents a dependency, because
the phases genuinely depend on each other — Phase 3's Add Complaint needs
Phase 2's model and board, which need Phase 1's layout.

The suite splits along those lines without editing a single assertion:

| phase | checks | examples |
|---|---|---|
| 1 — layout and navigation | 4 | doctype, `html lang`, tagline, nav links |
| 2 — board and model | 6 | seed complaint listed, card details, model contract, seed count |
| 3 — add complaint | 3 | 303 redirect, posted complaint appears, form rendered |

That is exactly the shape `session.json` wants: three steps whose
`new_feature_selectors` are those three groups, graded cumulatively, with the
existing preservation machinery unchanged. The oracle has been exercised across
many batches and is known to discriminate on **12 of its 13 bullets** — its own
notes record one violation no suite catches (`p3-ignores-agent-name`,
`overlay/test_acceptance.py:236-240`).

**One thing this does not fix.** The phased dependency is real, but it is still
*offered* rather than forced, exactly as the toy's was. Nothing in the evidence
says a solver takes it more often here; that would itself have to be measured.
What changes is that the dependency is intrinsic to the application rather than
invented for the task, so forcing it would not be an option anyway.

## What it needs

**Authoring, and mostly only authoring:**

1. A **base** the session starts from. Either an empty skeleton (build all
   three phases) or the Phase 1 app (build 2 and 3). The second is smaller
   *for the solver* but **not smaller to author**: no Phase 1 application
   exists in the repository — every AgentClinic `base/` is the finished Phase 3
   app — so it must be derived by deletion, along with a phase-1-only public
   test for `base_preservation_selectors` (the current `base/tests/test_app.py`
   tests Phase 3) and its own known-good, known-broken and prompt-faithful
   fixtures.
2. **Per-phase selector groups** in `session.json`, taken from the split above.
3. **Phase requirements in the prompts** — what each phase must deliver.

**A correction to something I claimed earlier.** I said this was blocked on
vendoring `specs/roadmap.md`, which V11a deliberately reversed. That looks
wrong: a session prompt *is* where a requirement is stated, so the phase
requirements belong in the step prompts and no `specs/` directory need be
vendored. The V11a reversal was about a single-prompt contract's workspace,
which is a different question.

**A second claim, whose conclusion holds but whose reason was wrong.** I said
this needs no creation-capable capture because the outstanding concern was
about `capture --revert` building a task. That is a different backlog entry.
The recorded concern **is** about capturing an attempt that adds files: `git
diff HEAD` drops files created with `write`, which is "fatal for build shapes"
(`archive/2026-09-07-pre-reset/docs/development/arm-substrate.md:114-121`), and
`attempt_pi.py:195-201` still uses `git diff HEAD` today.

The conclusion survives because the **session** path does not share that limit:
`build_cumulative_patch` seeds an alternate index and runs `git add -N --all`
(`session_patch.py:74-75`), and new files do appear as `new file mode` hunks in
retained checkpoint patches. **Caveat that belongs with it:** those new files
were captured but never *graded* — every checkpoint containing one had feature
grading skipped as a scope violation (`session_grader.py:78`), so "captured" is
demonstrated and "graded" is not.

## Prerequisites, measured rather than suspected

Both come from the same twelve sessions and should land first:

1. **A repeated-call limit on the session path**, which solves half of one
   problem and should be scoped as such. Four of twelve sessions hit the 600 s
   step timeout, but only two are repetition locks — sessions 02 and 05, with
   longest identical-consecutive runs of 127 and 129 against ≤5 in successful
   sessions. Session 11 made **194** tool calls with no two consecutive calls
   alike, which no consecutive-repeat limit reaches. It also cannot be ported
   unchanged: `RepeatTripwire` keys on `tool_execution_start`
   (`repeat_limit.py:29`), an event the session adapter does not map
   (`pi_session.py:45-53`); the session key would be `toolcall_end.toolCall`.
2. **Grade against trusted checks, independently of solver-authored tests.**
   Nine of twelve sessions wrote under `tests/`. **Permitting new test files
   would not have removed most of it:** eight edited the *protected existing*
   file, and only session 11 was new-file-only — and it timed out anyway. So
   the earlier framing of this prerequisite was wrong. The workload should let
   the solver add tests freely, and grade preservation from checks it cannot
   reach, rather than policing where it writes.

## What it would and would not establish

It would give a multi-prompt workload with genuine cross-phase dependencies, a
proven oracle, and preservation checks that already carry forward per phase —
the conditions under which a later request regressing an earlier one can
actually be observed.

It would **not** say anything about Engine versus Baseline. No Engine session
arm exists, and building one is engine design rather than adapter glue: the
mutator and runner assume one frozen contract carrying a `test_command`, and a
session has no per-prompt equivalent.

## The alternative this proposal has to answer: do nothing

> **Correction, 2026-09-09.** This section argued the proposal was "not pulled
> by anything" and recommended deferring it behind further instrument fixes.
> **That was wrong, and it deferred the stated goal.** Testing a multi-phase
> workload *is* the development need — it was asked for directly, and "no
> evaluation should be manufactured" guards against inventing questions, not
> against answering the one on the table.
>
> A second thing this got wrong: requiring a step that must extend shared
> behaviour is **not** "manufacturing an accident". Requiring a *regression*
> would be. A realistic request can demand extending shared behaviour while
> preserving earlier requirements, and that is ordinary development.

The two prerequisites are different — both are justified on their own by the
retained batch, and both are **re-scorable against the 12 sessions already on
disk with no further inference**. So the cheaper course, and the one I would
default to, is: **land the two fixes, re-score the twelve retained sessions,
and defer the phased workload until a session-shaped engine question exists.**
This proposal should be adopted when that question arrives, not before.

Also unexercised: no session has ever run on an AgentClinic base. That route
would need the suite brief's route-verification step before any measurement —
materialization, `uv run pytest` residue, and the absence of a `.gitignore` in
`base/` are all unknowns here.

## Scope

One task, existing machinery, no new framework. A first run would be Baseline
only and bounded, with its own frozen conditions and its own authorization.
