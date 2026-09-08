# First useful engine comparison: execution plan

This plan follows the accepted [offline milestone](first-milestone-design.md)
and [whole-attempt deadline work](whole-attempt-deadline-design.md). It applies
the repository's `BRIEF.md` evidence and development-feedback policies to the
next sequence. Writing this plan authorizes neither implementation, a commit,
nor model inference. Live work needs an explicitly authorized frozen budget;
authorization covers only its stated stages and scope.

## Outcome

Use one qualified task-condition to make a defensible decision about one engine
change, supported by retained behavior-level evidence and measured cost:

> Under the declared task, model, tools, and budget, this engine change improved,
> regressed, or made no detectable difference to these required behaviors.
> Here are the observations, uncertainty, retained artifacts, and measured cost.

An inconclusive result is valid when the evidence cannot distinguish the
alternatives. Positive improvement is not an acceptance requirement. Fixture
success and exploratory live observations do not establish model capability,
success rates, headroom, or a causal effect.

The sequence is preparation, one live smoke, a small matched triage screen,
separately planned confirmation, and an evidence-backed engine decision. Start
with `agentclinic-repair-depth-3` at `R3`. Expand only when a named requirement
or engine behavior demonstrates why that condition cannot answer the question.

## 1. Prepare the smallest real execution path

Record the accepted offline baseline and link this next sequence from the
roadmap and current guidance. Preserve the reviewed qualification, synthetic
route, deadline semantics, and evidence-retention contracts.

Choose a concrete baseline engine/model combination from the available
environment. Inspect its executable-command integration and existing retained
attempts before proposing adapter code. Reuse `attempt`, explicit `run --n 1`,
the existing schedule/interleave and counts-only tally machinery, and offline
regrade wherever their interfaces fit. The first-milestone fixture launcher has
a synthetic identity; do not relabel its output as live evidence.

Write one human-readable run record with these fields before any launch:

| Frozen choice | Required contents |
| --- | --- |
| Question and condition | Smoke question, task/rung, task and oracle revisions, qualification reference, exact prompt/contract identity. |
| Executor | Exact command and configuration digest, engine revision, model identity and settings, tools and their revisions. |
| Environment | Evals revision, dependency/environment identity, model server or provider, hardware, concurrency and cache/warm-up policy. |
| Limits | Command timeout, whole-attempt deadline, token/repeat limits where relevant, and total spending ceiling with explicit units. |
| Schedule | One planned attempt, output location, launch order, interruption handling, stopping rules, and evidence-review steps. |

Populate concrete values during preparation; unresolved identity or budget
fields block the live stage. Keep credentials out of the record. Any warm-up
that invokes a model belongs in the authorized spending budget and is recorded
separately from scored attempts.

Target useful feedback within 10–15 minutes. Inspect representative retained
attempts before choosing short limits; if no relevant evidence exists, label
the smoke budget provisional and use its measurements to propose the next
budget. A changed budget creates a new condition. Account for the deadline's
documented finalization allowance and local-I/O limitation. Do not use a
repeat limit when recovery from repetition is the behavior under study.

Verify executable/configuration identity, task materialization, artifact paths,
and the grading route without model inference where possible. Add only the
adapter or measurement changes a demonstrated gap requires. Default tests stay
model-, network-, and subprocess-free; real process/Git/oracle checks are
marked integrations, with sibling successes for refusals.

**Exit:** a concrete smoke record, passing relevant offline checks, and Sol's
review of readiness. Request only unresolved user choices and the concrete live
budget when it is not already authorized. Preparation itself requires no GPU.

## 2. Run one bounded live smoke and review its evidence

After the frozen smoke is authorized, execute exactly one scheduled attempt.
Verify observed engine/model identity against the record. Retain the patch and
transcript before grading or cleanup, and derive the verdict from fresh hook
evidence with the expected executed checks and no collection errors.

Inspect whether the real engine received the intended contract and exercised
the relevant edit/test path. Record a refusal or timeout as observed. A failed
repair may prove that the route works; a refusal that never exercises the path
does not prove the full integration. Do not turn either into an automatic retry.

Report cost as the monotonic total around the invocation plus usage counted by
the terminal-per-response rule; a streaming transcript repeats the same usage
and inflates a naive sum. Lifecycle phase durations are unmeasured: state that
missingness rather than substituting filesystem intervals, which do not
correspond to phases. Retain raw usage when the engine or provider exposes it,
and state input/output and cache accounting definitions and any missing usage,
including spending that was never retained. Price-based monetary
estimates need a recorded rate source; local GPU time is not a dollar cost.
Deadline elapsed time alone is not a general duration measurement. Keep tally
counts-only; a small linked measurement artifact is sufficient.

Regrade the retained patch offline without invoking the executor and compare
the receipt's behavior outcomes. A disagreement or unavailable grade needs
diagnosis before proceeding. Preserve the original receipt and provenance when
producing later evidence. Keep the hook-path authorship limitation visible in
the interpretation, as described in [trust boundaries](../topics/trust-boundaries.md).

Infrastructure failure stops remaining launches. Preserve the partial record
and turn the reproducible component into a cheap regression test. Repair it
and prepare a separately identified replacement smoke with a newly frozen
one-slot schedule and budget. Launch it only if authorization explicitly covers
that replacement; unused money in the original ceiling does not add a slot.
Ordinary failed repairs remain counted observations. Completed
attempts are never replaced; mid-attempt interruption retains evidence and
blocks automatic continuation pending review.

**Exit:** one fully exercised real route with an interpretable hook-derived
result, retained/regradable artifacts, explicit denominator and missingness,
and trustworthy timing measurements. Any further smoke requires a declared
reason, slot, and budget. Sol reviews the evidence and readiness for triage.

## 3. Choose one engine change and run a small matched screen

Select the behavior first, then the condition. A condition is chosen because it
exercises the named behavior, never because it is convenient or because an
earlier result looked favorable.

### 3.1 Name the change and its predicted effect

Name one engine change: two revisions, or two settings of one revision. State
the behavior it should improve, the required task behaviors that would show
that improvement, and the regressions it might introduce. Write the prediction
down before choosing a condition and before any spending.

The current shortlist — widen the loop-breaker window, enlarge the post-edit
region, or tighten the consecutive-block limit — contains efficiency
hypotheses. Fewer repeats or less churn do not establish improved task
capability, and the retained evidence does not establish a verdict benefit
from these changes. If capability improvement is the objective, revisit the
shortlist and name a supported capability hypothesis before freezing a pair.
This is a limit on the evidence, not proof that a verdict benefit is impossible.

If the change has a deterministic failure component, write its reproducer
first and keep it as a cheap regression test. Work on the candidate in the
engine's own scoped checkout and freeze its revision after focused tests and
review. This plan does not assume permission to edit an external engine.

### 3.2 Choose the condition that exercises that behavior

Start from `agentclinic-repair-depth-3` at `R3` and ask whether it exercises
the named behavior. Its retained evidence is 12 baseline passes under earlier
limits and one engine pass from the smoke. That is **not** a demonstrated
ceiling: it leaves unresolved whether the condition can distinguish two engine
configurations, and passing remains compatible with useful regression
detection.

The engine smoke `2026-09-08-first-smoke-123843` reports `repeats: 1`, not
zero. Repetition therefore occurred at R3; do not justify leaving it by claiming
that repeat behavior is absent. Distinguish an observed repeat from reaching
the loop-breaker's blocking threshold or exercising window eviction and
re-admission. Any proposal to change conditions must address the trigger for
the named candidate, rather than treating those behaviors as interchangeable.

Keep `R3` unless the named behavior cannot appear there. If it cannot, write
down which behavior is missing and why, then qualify exactly one additional
condition. `depth-2` at `R1` is a candidate worth examining; its retained 6 of
12 baseline against 8 of 12 engine is an exploratory lead under different
limits and does not establish an engine benefit. Before using any new
condition, qualify its accessible requirements, public feedback, hidden checks,
and base, known-good, and incomplete witnesses through the existing gates. Do
not infer one rung's qualification from another. Review the new record before
spending.

### 3.3 Freeze a matched before-and-after pair

Freeze two configurations differing only in the named engine change. Hold the
task, rung and prompt, model and its settings, budgets, grading, and the tool
surface constant — including the bounded test runner the contract enables.

Establish each configuration's **effective** tool surface from three sources
together: the rendered contract, the pinned engine implementation, and the
generated command. The arm file is not one of them — the smoke ran
`read,edit,bash` where its arm file pinned `read,edit`, because the engine
enables a test runner when the contract declares one. The contract alone is
not enough either: the same contract can expose different tools under a
different engine revision or extension set, which is exactly the axis a
before-and-after pair varies.

Compare tool **semantics**, not just names. A tool of the same name may differ
in what it permits, how it reports failure, or what it does to the workspace,
and a pair that matches on names while differing on semantics is not matched.
An unchecked surface breaks the "differ only in the engine change" premise
silently, and in the direction that looks like a clean result. Record any
unavoidable difference and the claims it prevents.
Predeclare order, seed policy where supported, and cache and model-server
treatment to limit carryover.

### 3.4 Run four attempts as triage

Authorize and run two attempts per configuration: four planned attempts total.
Keep the smoke outside this denominator.

Give each configuration its own schedule and output root so their counts cannot
pool — `ArmName` is a closed vocabulary and a tally groups by it — while
keeping one predeclared interleaving order across both roots. This needs no
change to the arm vocabulary.

Inspect each completed attempt before the next launch for infrastructure
failure. Count ordinary failures and completed unavailable grades; name missing
or interrupted slots explicitly. Do not substitute retries, extend budgets, or
add configurations because of which result looks favorable.

Report behavior outcomes and measured cost for all four slots. Cost is the
monotonic total plus usage counted by the terminal-per-response rule; report
any phase decomposition only as far as the resolved timing convention
supports. This screen selects a candidate for investigation; it establishes no
success rate, causal effect, or headroom conclusion.

Recommend whether confirmation can answer a worthwhile question, including when
triage shows no apparent improvement. If the condition did not exercise the
behavior, propose one revised hypothesis or condition and repeat this section
with a separately frozen and authorized four-attempt screen. Allow at most one
such additional screen; keep both screens' evidence and denominators separate.
If neither supports a useful confirmation question, report the limitation and
propose a revised plan.

**Before any Stage 3 spending:** the smoke's tool-surface record and usage
accounting are corrected, and the timing reporting convention is resolved and
written down.

**Exit:** a reviewed decision to confirm one candidate, or the bounded
candidate-selection path is exhausted with an evidence-backed next proposal.
The latter is partial progress, not completion of the engine-comparison goal.

## 4. Freeze and execute a focused confirmation experiment

For the selected candidate, write a separate confirmation protocol before new
spending. State the primary required behaviors, regression checks, comparison
unit, effect worth acting on, sample-size/budget rationale, uncertainty method,
and decision thresholds. Tests within one attempt are not independent attempts.
Specify how refusals, unavailable grades, and unstarted slots affect analysis
without silently shrinking the planned population.

Freeze matched configurations, exact attempts per configuration and total
denominator, per-attempt command/whole-attempt/token limits, total spending
ceiling with units, execution order, environment treatment, stopping rules,
and the analysis method. Use fresh attempts; exploratory observations
remain separately labeled and do not enter confirmation totals. Changes to
prompt, task, budget, model, tools, or multiple engine components constrain
attribution and require a revised protocol. Do not tune against confirmation
outcomes and continue presenting the run as a frozen test.

Sol reviews the protocol before requesting any missing budget authorization.
Run only the approved schedule. Apply the same infrastructure-stop, retention,
and recovery rules as the smoke. Do not extend the sample after inspecting an
unfavorable or ambiguous result. If the affordable sample cannot support the
intended decision, narrow the claim or report inconclusive.

**Exit:** the planned experiment is settled, or its interruption is explicitly
accounted for, with retained evidence sufficient for the declared analysis and
all missingness visible. Execution completion alone does not establish an effect.

## 5. Produce the decision and obtain final acceptance

Create one concise result note linked to the frozen protocol, schedule,
attempts, receipts, qualification, and timing/usage sources. Regenerate the
behavior comparisons from retained evidence. Show the planned and observed
denominators, unavailable evidence, uncertainty, per-stage time, available
usage, and any costs that remain unmeasured.

State whether the evidence supports adopting, rejecting, or further testing
the engine change, and which behaviors improved, regressed, or remain
unresolved. A recommendation does not authorize merging an external engine
change. Limit conclusions to the measured condition; list the next useful
question and what would require a different task or budget.

Run checks proportionate to the changes: default tests and affected marked
integrations for code, and documentation lint, strict Sphinx, and
`git diff --check` for the final guidance. Sol reviews implementation slices
and recommendations throughout. Astra performs the final deep acceptance
review after focused checks pass, covering instrument integrity, qualification,
matched controls, denominators, cost provenance, and the strength of the claim.
Repair findings with retained evidence where possible before proposing more
model spending.

**Acceptance:** one bounded live route has worked; the selected engine question
has been addressed by the declared confirmation analysis; the decision is
reproducible from retained evidence; and Astra accepts the conclusion and its
limits. A negative or inconclusive decision can satisfy this goal. A blocked
smoke or abandoned triage screen is reported as partial progress.

## Scope and working arrangement

Use Terra for implementation, Sol for iterative reviews and recommendations,
and Astra for final acceptance. Continue routine authorized work without
repeated permission requests. Escalate missing external-engine authority,
material condition choices, new spending, or a scope expansion with the
concrete proposal and evidence needed to decide.

Defer a broad deletion pass, general qualification/scheduling/reporting
platforms, a multi-task or all-rung matrix, telemetry repair, and infrastructure
optimization without measured need. Remove or simplify code only when it
directly obstructs this sequence and its consumers and protections are known.
Broader suite expansion follows a demonstrated question from this comparison.
