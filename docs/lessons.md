# Evidence checks

Use these checks when interpreting a task or result:

- Identify the actual required behaviour, the public feedback, and the hidden
  oracle separately.
- Test known-good, known-broken, and plausible incomplete repairs before
  treating a task as qualified.
- Keep prompt, model, engine, tools, budget, and schedule explicit; changing
  one changes the condition.
- Use a detector across arms only if it can fire meaningfully for every arm.
- Read stopping behaviour from retained transcript evidence, not an attempt
  exit code.

## Indexed by symptom

**"The count looked plausible and was a whole multiple of the truth."**
A transcript is a *streaming* record: the same call and the same usage block
appear in several representations. Counting by matching a field name across
the whole file therefore multiplies. Tool calls first reported for the
2026-09-08 screen were inflated exactly 4x this way, and the same walk inflates
output tokens 5.5x — which is why `scripts/usage_totals.py` exists, with the
trap in its own docstring. **Count tool calls from `tool_execution_start`, one
per call, and read usage with `usage_totals.py`.** A plausible-looking count is
the dangerous case: nothing about 12 reads looks wrong until it is 3.

**"The file was not modified, so the tool did not write it."**
Equal content is not evidence a file was left alone. A `cmp` over a regraded
cell found `receipt.json` byte-equal and it was reported as untouched; its
mtime showed it had been rewritten with identical bytes. **Compare timestamps,
or snapshot before the operation and keep the hashes.** State only what the
retained artifacts prove — an empty log and no retained hashes support no
claim about what a command did or did not write.

**"I replayed the change over the old recordings and got a number."**
An intervention that changes *which events occur* cannot be evaluated by
replaying events recorded under a different intervention. A loop breaker
decides which tool calls execute, so a transcript's call sequence is endogenous
to the breaker that produced it; feeding it to another breaker measures a
counterfactual. The tell, when it happened on 2026-09-09: replaying the
*shipping* breaker — built to refuse less — over transcripts from the older one
produced **1,373 refusals against 532 recorded**. **Compare in lockstep and
stop at the first divergence**, so every decision counted is one both versions
actually faced, and report the result as a prefix agreement rate rather than a
run-level rate.

**"The count looked plausible and was a whole multiple of the truth" — the
rule, not the two fields.** The earlier entry named `tool_execution_start` and
`usage_totals.py`, and a third occurrence followed anyway on 2026-09-08
(`grep -o NO_CHANGE_REQUESTED` gave 466 against 47 real refusals, 9.9x; the
loop-breaker string runs 4.2x). The rule: **never `grep -c`/`-o` a string to count events** — a tool result is
re-streamed in the following message and quoted in model thinking. Count from
the authoritative event for the thing being counted, which is **not one event
type for everything**: a tool's *result* is a top-level `tool_execution_end`,
while the breaker's own firings are `entry_appended` with
`entry.customType == "loop_broken"`, and usage is a settled `message_end`.
Name the event you counted, and carry the recompute command beside the number.

Two neighbouring failures share the symptom and need separate checks: an
**invalid counterfactual replay** (see the entry above) and **uncertain token
semantics** — `usage.output` is the server's `completion_tokens`, and what it
includes is a property of that server, not something a character count can
settle.

**"The night produced commits, green gates, and no tested remedy."**
Every instrument fix was individually justified — each blocked the next
measurement — and the failure was cumulative, so nothing local caught it. Four
consecutive cycles produced parser, preflight, grading and protocol changes and
**zero enabled or tested remedies**. Two contributing causes, both specific:
mining retained evidence can only find pathologies of the code that produced
it, and that code was retired; and a deterministic-reproducer entry gate turns
most candidates into instrument corrections, because building the reproducer
means first proving the instrument reads the evidence correctly. `AGENTS.md`
now carries the currency check, the instrument-only cap, and the tax rule.

**"The waiter never returned and the work had already finished."**
`while pgrep -f "run-batch.sh"; do sleep 30; done` matches the **waiter's own
command line**, which contains the pattern as its argument, so the loop can
never exit. Three such waiters spun for 10–12 hours after their batches
finished, on a machine whose quietness is a stated precondition for unattended
batches. The mirror-image error is guessing a process name that matches
nothing, which returns instantly and looks like success. **Wait on a condition
the work itself produces** — a file appearing, a marker line in a log, a count
of completed cells — not on a process name; `pgrep -f "[r]un-batch.sh"` guards
the self-match but the file check is the right instrument for this job.

**"The oracle already carries every phase, so it can grade any phase."**
`agentclinic-repair-depth-3/overlay/test_acceptance.py` holds all 13 checks
and labels its own sections by phase, so it reads as a phase-structured
suite. It is not one. Its module body runs `from app import app`,
`import models`, `from models import Complaint`, and snapshots
`tuple(models.complaints)` at import (`overlay/test_acceptance.py:14-29`).
Selecting only the four phase-1 node ids does not avoid that: **collection
imports the module before any selection applies**, so grading a phase-1
workspace — which has no `models.py` — fails at import for every selector.
A design was written, reviewed and planned on the premise that the file
could grade phase 1 unchanged; three reviewers, including the one who
recommended the approach, read the phase-labelled section headers as
evidence of independent collectability. **A suite's section comments
describe its authors' intent; only its import graph describes what it can
run against.** Check the module body, not the headings, before promising a
file can grade a workspace smaller than the one it was written for.

**"Byte identity proves the artifact; it does not prove the fit."**
The same episode, generalized. Byte-identity with a recovered source
establishes provenance — that this oracle is the one that discriminated
before, unedited. It says nothing about whether the oracle suits a
*different* workload. Provenance and suitability are separate claims and
need separate evidence.

**"The model wrote tests, edited them twice, and never ran one."**
First phased session, 2026-09-09, Gemma 12B. Across three prompts it made 12
tool calls: one `bash` (returning "(no output)") and eleven `write`/`edit`.
At phase 3 it wrote `from fastapi.form import Form` — a module that does not
exist, where the prompt says verbatim "`Form` from `fastapi`" — and stopped.
Its own `tests/test_app.py`, which it had written and twice edited, fails with
the same `ModuleNotFoundError`; a single `pytest` run would have surfaced it.
Two consequences worth separating. The **pathology** is cross-phase: phases 1
and 2 passed, and phase 3's edit made them ungradeable without touching them,
because every grader module imports `app`. The **instrument defect** is that
this scores `unavailable`, not `fail`: the grader requires executed ids to
match expected, a collection error executes zero, and the mismatch reads as
"we could not measure" when the truth is "the model shipped code that does not
import". A scope violation is already "a candidate failure, never
infrastructure unavailability"; an import error in the *solver's* own code
belongs on that same side, and one in a *grader* module does not.

**"The detector was specified against the wrong event shape, and would have
fabricated rather than missed."**
A deferred no-edit-run detector was specified to read tool names through
`session_repeat_limit._tool_key`, whose shape is
`payload.assistantMessageEvent.toolCall` — the `message_update` shape. Real
`tool_end` payloads carry `payload.toolName`. Written as specified it would
have read `None` for every call and reported a no-edit run spanning the entire
session. The failure mode is not a silent zero but a **confident maximum**:
absent data rendered as the strongest possible finding. It was also aimed at
the wrong signature — built from a prior run's `follow_redirects` loop, while
this run's shape was all edits and no verification. Deferring it until a trace
demanded it is what kept it from being wrong in production.

**"The precondition passed because I verified a different proposition."**
A pre-run record required proving the environment its preamble promised the
model actually exists. The check materialized `base/`, ran the pinned install,
and confirmed the imports — all green, recorded PASS. The claim that mattered
was whether the **run's** workspace arrives installed, and it does not: the
first verification command in the session printed "Creating virtual
environment at: .venv / Installed 47 packages in 80ms". The preamble was
telling the model the environment was ready while also telling it not to
install anything, and the command it was told to run installs. Nothing broke
only because `uv run` self-heals from the lock in 80ms; with a cold cache or
no network that lands inside the model's step budget or reads as a model
failure. **A precondition names a proposition, and passing a check on a
neighbouring proposition is not evidence for it** — write the check against
the artifact the claim is about (here, the attempt workspace), not against a
convenient stand-in.

**"The instrument's virtualenv was exported into the subject's shell."**
Every bash call in the session carried
`VIRTUAL_ENV=<evals repo>/.venv does not match the project environment path
'.venv' and will be ignored`. `uv` ignored it and warned, so the run was
unaffected — but a tool without that defence would have run the model's tests
against the harness's interpreter and packages instead of the task's pinned
ones, and the result would have looked like a finding about the model. Env
inherited from the harness process is part of the measured surface; it belongs
in the same freeze as tools and sampling settings.

**"The control produced the behaviour we were about to attribute to the
instruction."**
A four-session triage screen tested one added sentence telling the model to
run its tests. Both instructed sessions verified after their final edits; of
the two controls, **one did and one did not** — the one that did was never
asked. Had the screen been run without controls -- or had it been the
48-session success-rate study it briefly became -- the obvious reading would
have been "the instruction produces verification", and the control refutes
that at n=2. **What a control refutes is necessity, not causation**: two
instructed sessions cannot show the instruction fails to raise the
likelihood, and the first version of this entry said it "made verification
consistent", which is a claim about a rate that four sessions do not carry.
The **denominator matters too**: phases are nested within sessions, so "6 of
6 phases" is two sessions, not six trials, and must never be counted as six.
The one clearly attributable effect is narrower and still useful: the
instruction **named a command that works**, where the unprompted control
burned calls on `pytest: command not found` before finding a working
invocation. **Two attempts per configuration was enough to kill the wrong
explanation**, which is the entire argument for running the cheap matched
screen before the expensive confirmation.

**"The experiment grew until it answered a question nobody had asked."**
A screen meant to decide whether a prompt change was operationally usable was
specified at n=24 per arm, ~3.25 hours, with an exact-Fisher power table
attached. The arithmetic was right; the design had drifted into a
success-rate confirmation study, and the actual question was "does this
behave usefully, and is further work warranted". BRIEF.md already prescribed
two attempts per configuration first. **The error was choosing an expensive
experiment before knowing which decision it served** -- not the power
calculation, which is the right tool once a rate is genuinely the output and
which does not by itself cause a misattribution. Corrected 2026-09-09: an
earlier version of this entry named "reaching for a power calculation at
all" as the tell, which is folklore and would make the next reader gun-shy
about a legitimate instrument. **Name the decision first, then size the
experiment to it** -- and if a screen acquires a power table, ask which
decision needs the rate.

**"The arm file's inference block was a claim, not a check."**
`arms/baseline-ornith15-9b.json` recorded `context_window`, `temperature`,
`top_p`, `top_k`, `min_p`, and `declares_reasoning` for the served id
`Ornith-1.5-9B-MLX-8bit`. That id was absent from the oMLX server's
`model_settings.json` (confirmed by direct read 2026-09-14), so the server
applied whatever it falls back to -- the side that actually governs
sampling. pi's `models.json` did carry a matching entry, which is why the
gap was invisible: one of two configurations agreeing is not the setting
being enforced. Every Ornith cell run before 2026-09-14 therefore executed
on unknown server defaults while the arm file's block said otherwise --
and nothing failed, because nothing compared the claim to either config
file. **The fix is a check that fails preflight, not a comment**:
`scripts/preflight_settings.py` reads both config files, reports every
field the arm declares that the live entry lacks or disagrees with, and
refuses (exit 1) rather than trusting the arm's own text. A frozen
precondition that is never verified against the system it describes is
not frozen; it is asserted.

**"We built the remedy for the failures we saw, and the failures we saw were the harness's."**
Release one's Engine components (guard 4's command bound, scope, the loop
breaker, `self_test`) were chosen on 2026-09-14 from the ceiling and headroom
probes: hunting, timeouts, piecemeal edits, `NO_PATCH`. Every one of those
signals was later traced, at least in part, to the instrument -- a hidden
suite leaked into pytest's temp directory and scratch staging, a 900 s cutoff
since removed, a harvest that missed the model's own commits, and server
default sampling. The harness was fixed item by item; the Engine's targets
were never re-derived from the clean harness. Under isolation, a real budget
and a working harvest, the binding failures were different in kind:
depth-3 was information-bound (R1 strips the one line naming `tzinfo`),
run-record-gate was ambiguity-bound (the prompt invites `errors.py`, which the
allowlist rejects), and docs-linter bound on finishing (cells reached a
passing state and kept working). The roadmap made it worse by scheduling the
Engine build (Phase 1) before the harness fixes (Phase 2) and admission
(Phase 3), and the gates that did exist counted outcomes -- admission counted
passes, qualification checked the grader, route proof checked that guards
fired -- so none asked *why* a cell failed. The same error recurred inside a
day: `self_test` enforcement was built from three route-proof cells and
measured rigorously on the wrong constraint. **Diagnose before building:
classify every admission cell's binding constraint from a turn-by-turn
reconstruction on the clean harness, estimate a remedy's effect offline, and
build only what the diagnosis says binds.** The offline estimate obeys the
replay entry above: it is valid only for an intervention whose effect begins
at or after the point measured (stopping at a reconstructed pass-state is a
prefix of the recorded run; a guard that changes earlier calls is not).
Outcome: `docs/superpowers/specs/2026-09-15-release-one-outcome.md`.

For a specific past incident or original line citation, retrieve its record
from [the archive](https://github.com/pauleveritt/satyrn-evals/tree/pre-release-one-2026-09-13/archive/2026-09-07-pre-reset).

For a catalog of specific observed pathologies, each traced to a live
source citation or an archived incident, see
[pathologies.md](pathologies.md) and its companion
[remediations.md](remediations.md).
