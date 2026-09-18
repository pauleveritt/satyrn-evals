# Release two — the Engine (design)

**Status:** approved by the maintainer 2026-09-17, with route proof on the
claim tasks chosen for section 7; drafted by Fable at the maintainer's
request. Bound by `2026-09-15-release-two-r0-constraints.md`.
This is the first Engine design since release one's negative, and R0 §1's
order is satisfied: harness validity (census build, `b2720a4`), task
validity (five tasks checked, one dropped), diagnosed admission (39 cells
classified and signed, `evidence/2026-09-16-census/`), and an offline
counterfactual for the one remedy that can be replayed. Every component
below names its class and the cells that justify it. Nothing is built until
the maintainer approves this design and the R0 sitting fixes the win rule.

## 1. What the census says the Engine must do

| class | cells | what the cells did | Engine-reachable |
|---|---|---|---|
| finishing | 10 of 15 medium-build cells, primary | held a hidden-suite pass inside the 32k/48 line, then ran coverage and lint gates the task never asked for, repaired their own scaffolding, deleted their own tests to match "9 passed", and in four cells regressed the tree | yes: the Engine sees its own `self_test` go green |
| runaway | 8 of 33 build cells, primary | one 16,000-token design think with no tool call ended the session before or during the build | yes: the turn ends at `agent_end` with no tool call, which the runner already observes |
| capability | 11 large-tier cells, primary | never reached a pass state; own tests green, hidden suite red | no; a scoping rule, section 6 |
| information | 0 on the fixed harness; 7 of 7 on release one's R1 | the one fact the prompt hid, which pytest's explanation line carries | yes, in the product: the self_test result must carry that line |

Guards 1 to 3 (loop breaker, scope refusal, symbol preservation) fired on no
live cell in 39. They stay as built and claim nothing.

## 2. Component A: finish-on-green

**Class:** finishing. **Cells:** run-record-gate 470484, 533788, 609675,
275888, 891860, 949626, 016509; docs-linter 374751, 453263, 845472
(`evidence/2026-09-16-census/classes-summary.md`).

**Mechanism.** When a `self_test` run through the Engine inside a turn
(explicit, or the Engine's own run after it detected pytest's summary line in
a bash result; not the completion gate's own run, which only happens when the
model was already stopping; plan Ruling 3) exits 0 and at least one source
mutation has landed since the last green, the runner sends one steer message
before the next turn:

> self_test passes on the current tree. If the requested change is complete,
> stop now and report what you changed. Do not commit, add provenance rows,
> run the full repository suite, run linters or type checkers, or change
> your tests to match a count; the developer reviews the candidate and does
> those. If something in the request is still missing, say which part and
> continue.

Delivered with `deliverAs: "steer"` so it lands before the model's next
turn, once per mutation generation, recorded as `finish_nudged` in the
receipt and counted by evals like the other firings. A nudge, never a hard
stop: cell 511653 in release one had its own suite green with the hidden
suite at 19 of 20 and fixed the last case five turns later.

The trigger's input is the Engine's **output detection**, not a shell parse:
when a bash result carries pytest's summary line and no self-test has run
since the last mutation, the Engine runs its own once and appends the compact
result to that result under one sentence saying so (`self_test_detected`); a
green there arms the steer exactly as an explicit `self_test` does. A run
hidden in a compound command, a heredoc or a wrapper script therefore still
reaches it. The cost is one self-test, about 35 s, at most once per mutation
generation. The appended sentence and result are model-visible; the
identical-prompt rule allows them as the Engine's own message, and the
numbers page discloses them.

**Offline estimate.** Replaying "stop at own-green" over the census cells at
the 32k/48 line: run 2's method rescues 5 of 9 run-record-gate cells and 2
of 6 docs-linter cells, harm 0 in 39; run 1's pre-registered rules count 0
with those cells unmeasured. The stipulated effect for sizing is the run-2
figure with run 1's 0 printed beside it. What the replay cannot say is
whether a 9B model obeys the steer when a five-step recipe is in front of
it; that is section 7's first measurement.

**What it does not do.** It does not fire on the public suite alone (a
runaway before any mutation has no generation), and it does not fire when
self_test is red.

## 3. Component B: runaway resume

**Class:** runaway. **Cells:** cell-loop 442168, 346861, 332393, 225004,
507079; speed-probe 691593, 524583, 771490.

**Why the existing gate is not enough.** The completion gate runs
`self_test` when a final turn has no tool call and no self-test has run
since the last mutation. On a length-cut turn before any mutation the
public suite is green, so the gate lets the session end, which is what
happened in all eight cells. On a length-cut turn after mutations the gate
fires only if the tree is red.

**Mechanism.** When the final turn's `stopReason` is `length` and it holds
no tool call, the runner sends one follow-up, at most twice per cell:

> Your last turn hit the per-turn output cap with no tool call, so nothing
> was done. Do not restate the plan. Make the next concrete change with a
> tool call: read the one file you need, or edit.

Recorded as `runaway_resumed` with the turn's token count. The cap stays at
16,000 on both arms, a sampling setting; the resume is the Engine's own
message, which the identical-prompt rule allows. Two resumes per cell
bounds the cost at two more turns.

**Estimate.** None replayable: the intervention changes the events after
it. The eight cells give the population and the trigger, not the effect.
Section 7 measures it live.

## 4. Component C: the self_test result carries pytest's explanation

**Class:** information, as the product would reproduce it. **Cells:** the
seven depth-3 cells of release one at R1 (0 found the seam) against six of
six at R2, whose only difference is the line `where None =
first.timestamp.tzinfo`.

**Mechanism.** `compact_output` keeps, for each failed test, the `E ` lines
of its traceback block after the assertion, up to three, in addition to the
`FAILED` summary line. Counted in tokens as today; the receipt reports the
compact result's size so "compact" stays a measurement.

## 5. Parity and hygiene, not claims

Fixed before any Engine cell runs, because the comparison's identical-tools
premise is not met today:

1. **Multi-edit.** `mutator.ts` `maxItems: 1` lifted; the Python apply takes
   many replacements. Baseline's edit already allows it.
2. **Prompt collapse.** `build_prompt` lists patterns, not every tracked
   test file, and does not list carried files as writable. The Engine
   prompt was 3 to 4 times Baseline's.
3. **Writable paths from `Files:`.** Derive admits only paths the request's
   `Files:` block names, so it cannot admit a path the grader rejects.
4. **Deliver timeout follows the record.** `DELIVER_TIMEOUT_SECONDS = 1800`
   becomes the record's `command_backstop_s`; the census runs at 4,800.
5. **The contract's budget follows the record.** `derive` takes the record's
   `token_budget`/`turn_budget`, wired like the backstop (absent or
   unparseable is an error), so the Engine has no stop the record does not
   name. The product default stays 32,000/48 for a developer; only the eval
   contract changes, and both arms run the record's budget. The route proof
   hid the opposite: the Engine self-stopped near 32,100 tokens while
   Baseline ran to 48,000, so a candidate the Engine delivered was graded as
   a pass where Baseline at the same count tripped the wire.

## 6. What the Engine refuses to attempt

The large tier: 18 of 18 cells with no pass state. Derive measures the
request against the medium class and, above it, returns the contract with
an advisory refusal that asks the developer to split the request.
**Predicate, ratified by the maintainer 2026-09-17 (the first draft's
"one module in `Files:`" separates neither tier):** at most 2 non-test
paths in `Files:` and at most 10 symbols in `Interfaces: Produces:`; on
the bundled tasks the produced counts are 5, 2, 7, 1, 0 against 23 and 16
for the two large-tier tasks (the first draft said 24; the mechanical
count is 23). A developer can under-declare symbols, so it
is a guide, stated as such. This is a product behaviour, not a claim,
and it is disclosed on the numbers page as the boundary the census found.

## 7. Measurement before the comparison

R0 §3 asks that a remediation be measured on development tasks that exhibit
its class. The only tasks that exhibit finishing are the two claim tasks;
no other task on the branch reaches green and overruns. Two ways through;
**the maintainer chose the first, 2026-09-17:**

- **Route proof on the claim tasks, disclosed and excluded.** Engine at the
  new commit, n = 2 per claim task, read for behaviour only: did the steer
  fire at own-green, did the model stop within three turns of it, did a
  runaway resume produce a tool call. Those cells are named on the census
  page and excluded from every comparison denominator.
- **Wait for the authored task.** If `selfhost-preflight-quiet` admits as
  finishing-shaped, it becomes the development task and the claim set stays
  two tasks wide.

Runaway resume is measured on cell-loop, which is outside the claim: n = 3
Engine cells, read for whether a resumed turn makes a tool call.

Go criterion for the comparison: the steer fires in 3 of 4 own-green cells
and the model stops within three turns in 2 of those 3; a resume produces a
tool call in 2 of 3. Below that, the design returns here.

## 8. The comparison, sized at the R0 sitting

Inputs from the census: Baseline within the line 1 of 9 on run-record-gate
and 1 of 6 on docs-linter; stipulated Engine rate from the counterfactual
0.5 on the tier; harm 0. Under the one-sided Fisher rule at n = 12 per arm,
power against 0.13 versus 0.5 is about 0.6; at n = 20 about 0.85. Two
claim tasks now, three if the authored task admits. Win rule, n, and
whether the authored task joins are the sitting's to fix; the effect size
is not, and is printed with run 1's 0 beside it.

**The line is read by reconstruction, per arm.** The run budget is the
record's (48,000/72), but the win rule reads the verdict at the
pre-registered 32,000-token / 48-turn line, per arm, by the classifier's
reconstruction of that arm's transcript -- never by the process exit code.
A cell whose exit code is a budget trip can still hold a pass state inside
the line, and under identical budgets the two arms are compared by the same
instrument. This is the rule the route proof forced: both docs-linter Engine
cells "passed" at about 32,166 tokens, over the line, and an exit-code read
would have scored them either way.

Secondary, declared and reported whatever the outcome: turns, tokens and
seconds to the candidate, and floor parity on depth-3 at R2, guard-prefixes
and review-script at n = 6.

## 9. What is claimed and what is not

Claimed, if the comparison holds: on medium-build tasks, `/implement`
delivers a passing candidate inside the 32,000-token / 48-turn line -- read
per arm by the classifier's reconstruction, never the exit code -- more often
than bare Pi, on Ornith 1.5 9B, and stops when the developer's tests are
green. Not claimed: any lift on large builds, any capability the model does
not have, and anything about guards 1 to 3.

## 10. Rules carried

Two-uid isolation; the launcher is the only path to a model; records frozen
in daylight; identical prompts, tools, model and sampling across arms, the
Engine's own messages and tool results being the product; no Docker or
sandbox; Opus steers and reviews, Sonnet implements, no haiku; a whole-path
reviewer before any Engine cell; commits with explicit paths; never push,
merge or amend; the engine repo's own gates and replay fixtures both
directions for every component.
