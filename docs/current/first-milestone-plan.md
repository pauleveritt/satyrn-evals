# First-milestone execution plan

This plan supersedes the broader implementation sequence in the current
[design](first-milestone-design.md). Its first phase updates that design to the
narrower milestone before implementation. This plan does not authorize model
inference or a commit.

## Outcome

Deliver one dependable offline vertical slice for
`agentclinic-repair-depth-3` at `R3`:

1. its accessible requirements, public suite, hidden checks, and three
   deliberate witnesses agree in a concise reviewed record;
2. a small synthetic batch uses existing execution and tally machinery to
   retain and re-score evidence; and
3. incomplete work and unavailable grading remain visible rather than being
   silently retried or removed from the denominator.

This proves the instrument's route, not task headroom, model capability, cost,
or an engine mechanism. A live/model run needs a separate frozen configuration,
budget, and authorization after the stop gates below pass.

## 1. Simplify the operating surface first

Before code or task data changes, Terra updates the active documentation. Edit
the current design and roadmap as needed to agree with this plan; do **not**
make those edits as part of this planning-only change. Keep historical material
in `archive/`, where it is evidence rather than guidance.

### 1.1 Replace the active glossary with a small current vocabulary

`docs/glossary.md` should define only the terms a reader needs to start or
interpret an evaluation:

| Term | Plain meaning |
| --- | --- |
| task | A starting project, requested change, and declared checks. |
| evaluation condition / configuration | The complete frozen choice of task, prompt/rung, executor command, model, tools, limits, and relevant revisions. |
| attempt | One invocation of the attempt command, with whatever patch, transcript, and grading evidence it delivered and Evals retained. It may refuse or time out. |
| verdict | The hook-derived `pass`, `fail`, or `unavailable` judgment. |
| result | The recorded outcome, including the verdict when available, missingness, and links to retained evidence. |
| batch / run | A declared group of attempts and the execution that carries it out. It has an explicit planned denominator. |
| public suite / hidden checks | Feedback available to the solver / independent checks used to derive the verdict. |
| qualification | Evidence that one task-condition can measure its stated requirements. |
| headroom | Remaining useful separation for one frozen task-condition-budget combination. |

Keep `arm`, `rung`, `cell`, and `receipt` as short lookup entries only. An arm
is executor configuration, a rung is a named prompt form, a cell is a planned
attempt slot, and a receipt is a saved grading artifact. These terms must not
lead the ordinary user flow or imply that every combination is an experiment.

Correct these facts while rewriting rather than adding qualifications around
the old wording:

- An allowlist is the patch-writable path set. It does not promise that tests
  are immutable when the manifest allows `tests/`; hidden overlay checks remain
  protected separately.
- An arm is not the full evaluation condition. Prompt, task, limits, schedule,
  and other frozen context may live outside the arm file.
- An attempt command can refuse, time out, or otherwise leave a product
  refusal; this does not by itself mean evidence was not retained.
- The generated engine contract can include `test_command`, derived from the
  task's declared public suite.
- Hook-written evidence is the verdict source, but the hook-result path is
  supplied to the oracle process and can be forged by model-controlled imported
  code. State the documented authorship limitation plainly.
- Point the evidence-floor rule to the current BRIEF invariant 5, not a
  historical rule number.
- A refusal can retain a patch, transcript, or other diagnostic evidence even
  though it has no grading receipt. Report product outcome and evidence
  availability independently.

Define storage-schema and development terms at their point of use in the
formats or architecture reference rather than promoting all of them into the
starting vocabulary. Remove phase labels, phase-specific conclusions, and historical terms such as
`admission`, `band`, `capability wall`, and `completion floor` from the active
glossary. Recover them from the archive only for a named historical question.

### 1.2 Make the current command surface truthful

Correct `docs/usage.md`, the documentation index, and command references
before code work. They must list the actual supported command surface, including
regrade, summarize, session, and census where those remain supported. Do not
invent future commands or make a reader understand orchestration artifacts to
run one task. Present the glossary as optional lookup, not prerequisite reading.

When this documentation pass is complete, update the current design and
`ROADMAP.md` to say that the milestone qualifies one task-condition and proves
one synthetic batch. Remove claims that all four tasks or all rungs are in this
milestone. Keep the north star and its protections: executable-command seam,
preservation before judging, hook-derived verdicts, explicit denominators and
missingness, matched controls for causal claims, offline rescoring, and frozen
conditions before a budgeted run.

**Stop gate A — Astra review.** Show the rewritten glossary, navigation, design,
and roadmap together. Do not begin code until their public vocabulary and
milestone scope agree.

## 2. Qualify one task-condition with existing gates

Qualify only `agentclinic-repair-depth-3`/`R3`. Read its manifest, R3 contract,
public suite, hidden checks, and existing integration gate. The qualification
record is concise, task-local, and human-authored; it records behavior IDs,
accessible R3 evidence, linked public and hidden checks, and expected outcomes
for each witness. It derives the public command from `manifest.json`'s
`public_suite`; it must not store a duplicate `public_command` field.

The record uses reviewer-neutral conclusions such as `justified`, `gap`, and
`pending`. Do not encode an Astra/Terra/model name or staffing arrangement in
its durable fields. Astra reviews the completed record for semantic adequacy.
An unresolved R3 requirement gap blocks the milestone and is reported with the
missing accessible evidence and affected hidden check IDs. Do not make a v2
task as part of this milestone.

Extend `tests/integration/test_agentclinic_gate.py` first. Do not create a
general qualification module, schema, or command-line tool unless that narrow
extension demonstrably cannot hold the record and its checks. The integration
gate must execute real public and hidden paths with hook evidence and assert
fresh, nonempty executed IDs and no collection errors. It must judge outcomes
from hook records, never stdout or exit status. The default test tier remains
model-, network-, and subprocess-free; real Git, workspaces, commands, and
oracle work belong in marked integration tests.

Use exactly these three offline witnesses:

| Witness | Required evidence |
| --- | --- |
| Base | The exact known hidden failures for the unchanged base task, recorded as the base witness. |
| Known-good repair | Declared public suite and all hidden checks pass. |
| Declared incomplete repair | At least one deliberate omitted required behavior fails its mapped hidden check(s); public outcome is recorded, even if green. |

Use the existing known-good and known-broken material where it fits. A
leave-one-repair-out patch is preferable for the incomplete repair because it
identifies the omitted behavior. Every refusal test must retain its sibling
success test. The qualification output distinguishes `pass`, `fail`, `gap`, and
`unavailable`; it never converts unavailable evidence into success.

**Stop gate B — Astra review.** Present the concise R3 record, exact hook
evidence for the three witnesses, and every requirement-to-check mapping. Stop
if any required behavior lacks accessible R3 evidence, a witness is ambiguous,
or fresh hook evidence does not contain the expected executed IDs with no
collection errors.

## 3. Prove a thin bounded synthetic batch

Only after gate B, decide whether code is actually needed. Reuse
`scripts/interleave.py`, `satyrn-evals run --n 1`, and `scripts/tally.py`.
If their existing interfaces can express the proof, add only a checked-in
fixture input and focused integration test. If a wrapper is necessary, make it
a thin launcher over those three paths; it must not become a general scheduler,
recipe system, source-copy framework, or reporting product.

The fixture batch has two planned synthetic attempts against the qualified task
and R3. Before any invocation it writes a schedule with task, rung,
fixture-executor identity, exact command/configuration digest, fixed limits,
and explicit denominator. Its synthetic identity is visibly not a model or
engine result. It retains each attempt's patch and transcript before grading or
cleanup, records hook-derived receipts, and supports offline regrading of those
retained artifacts without launching an executor.

The implementation must preserve these operational rules:

- A validated completed scheduled attempt is skipped on between-attempt resume;
  it is never rerun or replaced.
- An interruption during an attempt leaves retained paths and an explicit
  recovery-needed/blocked state. Resume stops for review; it does not invent a
  retry policy.
- Tally uses the prewritten schedule. Missing, aborted, or mismatched attempts
  prevent a complete tally while the planned denominator stays explicit. A
  completed `unavailable` grading result remains a counted observation.
- Result generation reads retained evidence and reports unavailable diagnostics.
  It does not use stdout, exit status, an earlier report, cost estimate, or a
  causal interpretation as its source of truth.

Prove three focused integration cases: clean two-attempt completion;
interruption between attempts followed by a resume that skips the validated
first attempt; and mid-attempt interruption that preserves evidence and blocks
automatic continuation. Use a sibling successful run for every refusal path.

Defer all of the following: four-task or all-rung inventory, a general
qualification schema/tool, fixture/live modes, source copying, new report or
regrade command surfaces, telemetry/census repair, cost collection, and causal
or engine comparisons. They need a demonstrated question after this slice,
not a place in its first implementation.

## 4. Acceptance and live-run boundary

Accept the offline milestone only when:

- active documentation presents the small vocabulary and truthful command
  surface, with phase debris removed from active guidance;
- `depth-3`/`R3` has an Astra-reviewed concise record with no requirement gap;
- base, known-good, and declared-incomplete witnesses have fresh hook evidence
  matching their stated hidden outcomes and public results;
- the synthetic batch writes its schedule before execution, retains its
  artifacts, has an explicit denominator, regrades offline, and proves both
  resume boundaries; and
- default and marked integration tests pass, including the subprocess
  tripwire in the default tier.

Do not start a live/model run automatically. A separate request must freeze the
complete evaluation condition, declare the question, controls if causal
attribution is intended, schedule, stopping rule, budget, and evidence review
plan. If any stop gate fails, report the retained evidence and repair that gate
before spending model time.

For that later live work, follow the `BRIEF.md` development-feedback policy:
start with deterministic reproduction, use one bounded attempt before a
two-attempt-per-matched-configuration triage screen, and plan a fresh
confirmation run for broader claims. Do not change `run`'s global `n=8`
default in this milestone: this route invokes `run --n 1` explicitly. Do not
add a whole-attempt deadline here either. It must bound setup, command,
preservation, grading, and cleanup without losing retained evidence, so it
requires its own design and focused tests before live use.

For Terra: preserve existing uncommitted work, work in this order, and do not
commit or invoke a model. Escalate only the two semantic review gates to Astra;
ordinary documentation and mechanical test decisions belong in the implementation.
