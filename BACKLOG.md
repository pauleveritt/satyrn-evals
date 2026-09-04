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

**Transcript-derived summary metrics** — `tool_calls`, `repeat`, `churn`,
`context` (V5b, 2026-09-02). Their data is Pi's print-mode stream-JSON,
spooled verbatim by the engine as `transcript.jsonl`
(`satyrn-engine/src/satyrn_engine/attempt.py:578`, `:206-225`); parsing it in
evals would reach through the engine seam that V4 established as opaque to
evals. These counts belong engine-side, published as an artifact the engine
derives from its own Pi stream — not satyrn-engine's `facts` field, which is
prompt content rendered into the handoff, not run telemetry.
Definitions are recorded: `repeat` is identical `(toolName, arguments)` calls
counted regardless of success
(`docs/superpowers/research/2026-08-16-harvest-index.md:69-71`); `churn` is
the same target rewritten with differing content (`:74`), kept separate
(`docs/superpowers/research/2026-09-01-handoff-and-eval-harvest.md:360`); the
counts must report **unmeasured**, never zero, where a transcript yields no
parseable events
(`docs/superpowers/research/2026-09-02-overnight-packet-and-isolation-run.md:160-162`).
**Reopens when the engine exposes these counts across the seam** — not when a
transcript sample becomes available.

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
