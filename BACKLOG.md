# Backlog: satyrn-evals

Deferred work. Read [`BRIEF.md`](BRIEF.md) first; the phase list is in
[`ROADMAP.md`](ROADMAP.md).

**Three rules, from `docs/sdd.md`:**

1. **Every entry states what reopens it.** An entry that cannot say what would
   make it relevant again is deleted, not kept "just in case".
2. **An entry over its cap owes a research doc.** The entry then keeps a
   summary, a link, and the reopen condition — not the argument.
3. **Entries are pruned, not archived in place.** Resolved, retired and
   superseded entries are removed once their outcome is recorded in a phase row
   or a research doc that the row links.

This file exists because a predecessor project's `ROADMAP.md` reached roughly
1,000 lines, about 800 of them Backlog, one defensible paragraph at a time.

## Entries

**Instruction-file contamination has no detector** (V11b, 2026-09-05). A
stray `AGENTS.md` or `CLAUDE.md` in a task's `base/` would silently inject
instructions into the model's context: the V7/V8 contamination detector scans
for **grader overlay text**, not instruction files, so the surface is
undetected rather than reported. V11b-trim closes it *by construction* — both
arms pin pi's `--no-context-files` (`arms/baseline.json`; `satyrn-engine`
already passes it at `attempt.py:240-264`) — which is cheaper than a second
detector. Evidence and the arm-parity finding:
[`2026-09-05-pi-context-file-loading-and-arm-parity.md`](docs/superpowers/research/2026-09-05-pi-context-file-loading-and-arm-parity.md).
**Reopens** if any arm is ever run without `-nc`, or if a captured task ships
an instruction file in `base/` — at which point construction no longer closes
the surface and a detector is owed.

**Where pi's ~9,000 unexplained repo-root tokens come from** (V11b,
2026-09-05). `CLAUDE.md` (~1,260 tokens) plus ~3 KB of home files does not
account for the 9,753-token repo-root measurement, and the same directory
gave 13,645 on one call and 9,753 on another. Both need a stream capture that
was not obtained. Unresolved, and no number from that record may be used as a
budget input until it is. **Reopens** when the Envelope cap is argued (V13,
proposal §2.4) — that argument needs a measured per-cell floor from inside a
materialized workspace, which the V5d smokes are tasked to capture.

**`stringified-annotations` capture** (V5c, 2026-09-03). Deferred from V5c,
which captures `local-pings` only: its Engine arm is pinned at ceiling (6/6,
`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md:78`), so it
buys regression detection rather than headroom. **Reopened for proposal
(2026-09-03): the stated trigger — the diagnostic loop has run on
`local-pings` — has occurred** (the re-probe ran V5b's `run` at n=8 on both
arms; `2026-09-03-local-pings-reprobe-protocol.md`). Reopened means the
capture may now be proposed as next work; it is not captured, not
admitted, and not selected.

**`local-pings` oracle improvement — drop `_svc_type`.** The corrected
probe's preservation test identifies registry pings through the private
`_svc_type` field
(`docs/superpowers/research/2026-08-27-local-pings-corrected-probe.md:46-49`),
coupling the oracle to an implementation detail. Changing it changes what is
measured and voids comparison with the recorded probes, so it is not done in
V5c. **Reopens as its own proposal** — a future admission candidate observing
public names or callable execution order.

**Automated commit mining.** Reopens after three manual captures show which
steps repeat.

**Paired A/B of two engine versions.** Reopens when a contributor needs "did my
fix help" across versions.

**Resumable large batches.** Reopens only if the prior checkpoint transplants
verbatim.

**The whole claims layer** — pre-registration, confidence intervals, condition
enforcement, cells and digest pinning, void and retry accounting, the
pilot/confirmatory distinction, model canaries, A/B publication machinery.
Deferred by the diagnosis-before-claims split, which is the decision governing
everything else and is not reopened here. **Reopens on a later consumer**, in
`BRIEF.md`'s own words (`BRIEF.md:33-36`).

**OS-level containment for the attempt** (reopens when all four recorded
blockers are cleared, or when detection proves insufficient in practice). A
whole-process sandbox profile was built and measured during the 2026-09-01
spike and is **deferred, not adopted**: it is macOS-only; it silently removed
the model's own test runner, so an entire block measured models that could not
self-verify; a hard link created inside the run root still read the grader
through it; and it conflicts with V4's absolute external engine-contract path
— though the V6 design already routes around that last one by copying a public
contract into the worktree rather than referencing it by task path. V7
detected after-the-fact instead — the detector and its stated limit are the
shipped spec
(`docs/superpowers/specs/2026-09-04-v7-task-visibility-leak-detection-design.md`).
*Recorded direction change:* an
earlier note in this planning cycle said "make containment genuinely usable,
including a test runner"; this entry defers it rather than fixing it, and a
still earlier draft wrote "refused" where the evidence only supports
"deferred".

**Text-contract support.** Reopens when a roster model cannot emit tool calls —
two of six models measured in the spike could not, so this is when, not if.

**Writable-scope injection.** Reopens if scope overreach is measured here.

**An orchestrator process.** Remains unjustified — every effect measured so far
was obtained without one, and autonomous contract authoring measured worse than
hand authoring.

**Captured base trees must not be filtered by the repository `.gitignore`**
(V5c, 2026-09-02). A bundled task's `base/` is a vendored foreign tree; the
repo's `.gitignore` patterns (`.idea/`, `.coverage*`, `node_modules/`,
`docs/_build/`, …) silently drop any *legitimately tracked* file of that name
when the task is committed, and the loss surfaces only on a fresh clone.
`local-pings` was unaffected (only ruff's `.ruff_cache/` junk was filtered),
but the mechanism is live. **Reopens with the next capture whose base tracks a
file matching a repo `.gitignore` pattern** — fix by committing the vendored
tree with an explicit allow (e.g. `git add -f`) or by verifying disk-vs-index
parity after `git add`.

**Engine-contract content is never validated** (V5c, 2026-09-02).
`manifest.py` validates only the `engine_contract` *path*
(`src/satyrn_evals/manifest.py:28-54`) — a safe relative path naming a regular
file. Nothing checks the file parses as satyrn-engine's contract schema,
because that schema is the engine's and evals declares no YAML parser. The
captured `local-pings` contract shipped invalid — an unquoted `task:` scalar
containing `": "`, rejected by `satyrn_engine.contract.load_contract` — and no
evals test could have caught it: V5c done-when #4 exercised `run` through a
fake seam command, which never loads the contract (fixed 2026-09-02). The only
check today is a real engine attempt. **Reopens when a second captured task
carries an engine contract, or when the first real engine run lands** — the
fix is a default-tier assertion that the contract parses under the same loader
the engine uses, which costs a declared parser dependency. *The second reopen
condition has fired* — the re-probe engine arm
(`2026-09-03-local-pings-reprobe-protocol.md:224-231`) — so the fuller fix is owed;
the V5d pre-flight smoke check
(`docs/superpowers/specs/2026-09-03-v5d-preflight-smoke-check-design.md`) is
interim mitigation.

**`python -m satyrn_evals.cli` silently no-ops** (V5c, 2026-09-02). `cli.py`
has no `if __name__ == "__main__"` guard, so module invocation imports the
parser, does nothing, and exits 0 — it cost one confused capture run (reported
"captured", wrote nothing). The console script `satyrn-evals` is the supported
entry. **Reopens when module invocation should either work or fail loudly** —
the fix is a two-line guard plus a tripwire test asserting `python -m` runs.

**`local-pings` re-admission** (2026-09-03). De-admitted as a diagnostic
workload: the captured-task re-probe recorded Baseline 3/8 and Engine 4/8,
both middle-band, so no compared pair occupies different bands
(`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md` caveat;
[de-admission record](docs/superpowers/research/2026-09-03-local-pings-deadmission.md)).
The task remains a valid bundled grader/smoke/regression fixture.
**Reopens with a newly preregistered qualifying probe** on the unchanged
captured N=6/five-ID task that records at least one compared pair in
different bands; simply increasing n was set aside as a
tune-until-separated risk. A materially revised task or adversary is a
separate track — a new admission candidate requiring its own capture and
fresh qualification, not a re-scoring of this task. The completed n=8
cells are not extended or reinterpreted.

**Historical Envelope artifact recovery** (2026-09-03). The canonical
`read,write` Envelope is unrecoverable on this machine: the pinned
`envelope-cap.ts` (`b7455133…`) exists in no revision here — all seven
copies hash `0448af10…`, the pilot's extension — and the era's Pi version,
adapter, and artifact harvesting were never recorded (`local-ai-pi`
`workloads/svcs/cells/gemma12b-envelope.toml`; the reconstruction-stop
evidence is in the de-admission record). Optional research, not a blocker.
**Reopens when the full recorded configuration is recoverable — the
`b7455133` extension *and* the era's Pi version, prompt, adapter, and
artifact-harvesting provenance — and the maintainer wants a faithful
reproduction.** Until then, any Envelope assembled with current Pi, a new
adapter, or a selected prompt is a new prospective arm, not a
reproduction.

**Replace the `local-pings` known-broken adversary** (V6 remediation,
2026-09-04). The allocator-sensitive adversary (a `get_pings` iterating
through a `set`) is credibly flaky: it sits on an N=8 knife edge of hash
stride versus set-table geometry and allocation phase (harvest index,
cross-machine record). This is fixture-reliability maintenance, not
evidence that changes the V5 result — the bundle stays a valid
grader/smoke/regression fixture until replaced. **Reopens when a
replacement adversary is proposed** that reproduces deterministically on
this machine with a canary reporting inconclusive on the wrong face.

**Raw-Pi message retention — decided (2026-09-04).** The Pi adapter
drops parseable-but-unmapped Pi events and malformed (non-JSON) lines.
Decision: retention is required only for the mapped event vocabulary —
the design of record requires the complete original Pi event in
`payload` for the mapped kinds so "its mapping and every count are
recomputable", and review fix 2 added `message_update` (the genuine
streaming evidence the smoke discriminator needs). The mapped set
already carries that evidence: `message_update` holds the stream,
`turn_end`/`tool_execution_end` hold completions, `agent_end`/
`auto_retry_end` hold terminal state. Unbounded retention of every Pi
event (per-token deltas, tool-execution updates) would defeat the
transcript's bounded, countable design without adding recomputable
evidence. Malformed lines cannot be forwarded without breaking the JSONL
protocol and are not retained; the session transcript and the retained
adapter-stderr log bound the evidence contract.

**CLI exit semantics for ADAPTER_ERROR / PROTOCOL_ERROR — decided
(2026-09-04).** Exit 0 stands for `ADAPTER_ERROR` and `PROTOCOL_ERROR`.
The design of record's coarse rule is: 0 for "a safely captured and
graded session, including a model failure or scope violation", 2 for
usage/start refusal, 3 for "operational refusal or unavailable grading".
An adapter-error or protocol-error session is still captured and graded
(checkpoints retained, offline grading ran, a durable record exists);
its terminal is a recorded outcome, not an infrastructure refusal.
Exit 3 stays reserved for where grading could not run or the workspace
failed (`GRADE_UNAVAILABLE`, `WORKSPACE_FAILED`, `CLEANUP_FAILED`). The
coarse exit reports whether evals captured and graded, never what the
terminal was.

**Cumulative-suite capture** (V8 input decision, 2026-09-04). `capture --revert`
records only the *discriminating set* — tests failing at base, passing at fix.
For a task whose intended oracle is a cumulative suite, that reduction is
unsound: the AgentClinic spike recorded a Phase-3 capture reduced to 3 of 14
tests accepting a patch that deleted the Phase 1 home route
(`docs/superpowers/research/2026-09-01-agentclinic-spike.md`, "Two defects
found in the Evals path"). V8's six AgentClinic repair tasks sidestep it by
being hand-authored bundled tasks whose oracle is the full 13-test acceptance
suite (hidden, overlaid), so `capture` is never exercised on them. **Reopens
when a task must be captured from git history whose intended oracle is a full
cumulative suite** — the task declares itself cumulative and `capture` records
the whole suite, or the capture is documented as hand-authored.

**AgentClinic repair admission probe** (V8 scope decision, 2026-09-04). V8
qualifies the six bundled `agentclinic-repair-*` tasks as a
dependency-bearing hidden-oracle path — offline rows plus one uncounted
smoke — but runs no budgeted measurement. The mid-band claim that motivated
the repair fixtures
(`docs/superpowers/research/2026-09-02-overnight-packet-and-isolation-run.md` §5)
must be re-tested on this repository's own path before any admission
decision; the scratchpad numbers it rests on are unadmitted.
**Reopens when the six tasks' offline qualification rows are green and the
V8 smoke passes** — a budgeted, preregistered admission probe of the repair
suite on the Evals path may then be proposed and confirmed separately.

**Roadmap update (2026-09-04).** Both conditions are now met; the repair
suite proceeds through V11a's evidence ladder and V12's reference placement
profile before V13 can propose an arm comparison. This records a queued
successor, not admission or a result.

**An infrastructure error is scored as a model refusal** (found 2026-09-05,
voided V11c mini-probe, `~/satyrn-smokes/2026-09-05-v11c-miniprobe/`). A GPU
out-of-memory turn — zero `usage`, `stopReason: "error"` — leaves `pi` exiting
0 with a clean tree, so `decide_refusal` checks the empty patch first and
returns `NO_PATCH` (`src/satyrn_evals/attempt.py:102`), never reading the
transcript fields saying the model never ran. The record is shape-identical to
a genuine no-edit cell. **The OOM's cause was environmental and is not the
finding** — the finding is that any model-side hard failure (server restart,
unloaded model, provider error) is indistinguishable from "worked and declined
to edit." Symptom family:
`docs/superpowers/research/2026-08-16-harvest-index.md:97-111`; this mechanism
is absent there. The session adapter already discriminates it
(`src/satyrn_evals/adapters/pi_session.py:60-84`); the attempt path does not.
**Reopens as a design proposal** — a non-scoring `MODEL_ERROR` read from the
preserved transcript before `decide_refusal`, so `regrade` re-derives it
without a model; never from the exit code (`BRIEF.md` rule 4). Until then,
**screen every batch**:
`grep -l '"stopReason":"error"' RUNS_ROOT/*/*/transcript.txt`.

**`tool_free_terminal_turns` is dead on every pi-adapter cell** (found
2026-09-05, same investigation; independent of the OOM above). The counter is
gated on `not had_patch` (`src/satyrn_evals/pathology.py:321`), but `rescore`
passes `had_patch=record.patch_path is not None`
(`src/satyrn_evals/rescore.py:214`) while `attempt_pi` writes `patch.diff`
unconditionally, empty or not (`src/satyrn_evals/attempt_pi.py:231`) and
`attempt.py:289` sets `patch_path` whenever the file exists. So `had_patch` is
always true and the counter can never fire. Demonstrated on a cell from the
voided batch: the published summary for
`plausible-wrong-fix/…-200622-258836` records `tool_free_terminal_turns: 0`;
recomputed from that same preserved transcript with the repo's own
`count_transcript`, it is **1**. The code matches the V10 spec's letter
(`record.patch_path is None`) and defeats its intent (§3.6: the floored model
that stops after a text turn without ever editing). This silently understates
every pi-adapter cell already collected, including the green post-landing
smokes. **Reopens with the fix** — `had_patch` must mean a non-empty patch —
**plus a refusal/success test pair** per `BRIEF.md` rule 6, since a counter
stuck at zero is precisely the defect that passes silently.

**A signal-killed run writes no `aborted.json`** (observed 2026-09-05, same
batch, lowest confidence of the three). `run.py:123-153` writes `aborted.json`
on any `BaseException`, but stopping the mini-probe mid-cell left
`misleading-locus/` with three cell directories, no `summary.json`, and no
`aborted.json`; the interrupted cell
(`…-200931-612268`, 191 KB of transcript, 17 tool calls) has no `attempt.json`
at all. Inferred, not verified: the process was ended by a signal that raises
no Python exception. **Reopens when someone can reproduce a SIGTERM against a
live `run`** — this is a V9 loop-integrity gap if it holds, and a
misattribution if it does not.
