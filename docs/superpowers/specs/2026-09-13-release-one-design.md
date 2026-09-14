# Release one — design

**Written 2026-09-13, from the re-planning session of that day. This is the
first document of the restarted trees; it authorizes Phase 0 below and nothing
that spends inference.** It supersedes every design under `docs/current/` as
operating guidance; those remain evidence, tagged on the old `main`.

## North star, and the one claim release one makes

Keep a small model on track, so a Python developer can use local AI and stay
at the wheel. The developer's engineering is domain engineering — write down
what you are building, in specs and tests — not agent engineering.

**Release one ships an Engine that beats bare Pi at three mechanical
pathologies, and an Eval that proves it.** The pathologies, each observed on
`gemma-4-12B-it-MLX-8bit` with an existing mechanical remedy:

| # | pathology | evidence | remedy |
|---|---|---|---|
| 1 | repeat / read-lock loops | 281 identical `read` calls per locked cell (V11c); Baseline locked 8/12 vs Engine 1/12 (V14b); a 158-turn phase-1 loop, 2026-09-13 | the loop breaker, keyed on workspace revision |
| 2 | never running its own tests | runner took Engine 6/12 → 12/12 (V13e); "wrote tests, edited them twice, never ran one" (`lessons.md`) | the self-test command in the model's loop, result read from the exit code |
| 3 | writing outside the declared scope | `SCOPE_VIOLATION` sessions 09-04, 09-08, 09-13; Flask + `instance/clinic.db` in the Baseline n=4 | contract-aware writable paths; the mutator refuses the write |

Nothing else is claimed. Spec compliance (`complaints` vs `complaints_db`,
Pydantic for dataclass) is the model and the developer's writing-down, not the
engine; the eval counts it and does not remediate it.

## What the evidence settled

- **The autonomous chain is retired.** Every "Engine" loss since 2026-09-09 was
  a cost of a fresh-context worker in an orchestrated chain run *without* the
  engine's guards: route-dropping edits 19/23 vs Baseline 3/12; suites rewritten
  every phase (12/12 cells); validation that agreed with itself. That measured
  isolation, not the engine.
- **What preserved behaviour in Baseline was tests, not memory.** Baseline's
  own tests covered `POST /complaints` 12/12; when the worker's did (8/16), the
  destroyed route was restored 3/3. The edit guard held the route in 0/9
  delivered candidates. A public check in the self-test cleared the phase-2 wall
  2/2 on first use.
- **Every retained run started from an empty session.** "Engine phases peak
  under 8k" is evidence about cold starts only. Real use starts warm; the
  tokens-per-second collapse with context is unmeasured. Not evidence against
  isolation — a gap in the eval, closed below.
- **Pointer prompts lose** (PD5: 1/8). Facts go inline in the contract; only
  executable checks live on disk.
- **Autonomous contract authoring by an SLM lost** (3/8 vs 8/8 by hand; a
  remediated prompt 0/8). The contract is derived by code.
- **Taking tools away lost** (V13d: removing `bash`/`write` cost 8/12). Both
  arms keep the model's native tools; the engine sits at the boundary.

## The product: `/implement`

The developer works in an ordinary, long Pi session. When they say "do Phase 3"
or "add a status badge to the complaints page", the engine runs that one
bounded piece in a **fresh, small model context**, in its **own worktree**,
under a **derived contract**, with the **guards loaded**, and hands back a
**candidate plus a compact receipt**. The main conversation receives the
receipt, never the transcript. The developer reviews the candidate.

### Components

1. **Contract derivation** (Python, deterministic; the request is the only free
   input). From the repo and the request: `objective` (the request; a roadmap
   phase's text is pulled inline as `facts`), `writable_paths` (files the phase
   names, or paths the request mentions plus project layout — shown to the
   developer for confirmation), `self_test_command` (from `pyproject`),
   `preserve` (the tests that exist now), `checks` (everything under a
   developer-owned `checks/` directory), budgets (turn limit, deadline). The
   developer sees it on one screen and says go. Nobody hand-writes it. Reuses
   HP1's builder and schema (`packet.py`), renamed to what it is.
2. **Dispatch** (Python core; TS adapter). One fresh Pi invocation with the
   same model and the same native tools as the developer's session, plus the
   engine extension. Worktree branched from the developer's current HEAD. One
   process per operation, no sidecar — the engine BRIEF's architecture.
3. **Guards** (TS, in `emitToolCall`, per the engine BRIEF's blast-radius
   argument): the revision-keyed loop breaker (pathology 1); the writable-path
   check on every mutation (pathology 3); and a symbol-preservation refusal — an
   `edit` whose `oldText` removes a symbol the accepted base defines is refused
   with a message that names what to do instead. Loaded on the dispatch route,
   always.
4. **Accepted tests carried read-only.** `preserve` tests are copied to a path
   outside `writable_paths` and included in the self-test command, so a
   destroyed behaviour fails in the model's own loop. The developer's `checks/`
   ride the same way.
5. **Compact results.** The runner returns failed test ids and the first
   assertion line, not the pytest transcript; a successful edit returns the
   changed hunk, not the file. Both are counted in tokens per attempt, so
   "compact" is a measurement, not an adjective.
6. **Receipt.** Candidate commit, validation exit code (authoritative — never
   the model's prose), turns and tool calls used, tokens in and out, guard
   firings, budget state. One JSON file. This is what the main session sees.

### What `/implement` does not do

No orchestrator, no roadmap-driving loop, no retry or repair campaign, no
subagent the developer did not invoke, no packet pool, no hidden-grader access.
Context isolation exists only inside `/implement`; whether it earns its cost is
what the eval's warm condition decides.

## The eval

**Arms.** *Baseline*: bare Pi 0.85.1, tools `read,bash,edit,write`, no
extensions, the frozen model. *Engine*: the same session, with each phase run
through `/implement`. Identical prompts, identical native tools, identical
model. This is a **product comparison**; attributing a difference to isolation
versus guards is release two's ablation.

**Conditions.** *Cold*: the session starts empty (every run to date). *Warm*:
the session starts with a **recorded prefix** — one real developer session of
ad-hoc work on AgentClinic, recorded once, replayed byte-identically for every
cell — then the phases run. Real work, not filler, so it is a condition and not
a handicap.

**Workloads.** `agentclinic-repair-misleading-locus` at R1 (pathologies 1–2;
the one place bare Pi demonstrably read-locks) and the plain four-phase
`agentclinic-complaint-lifecycle` (pathologies 1 and 3; the warm workload,
because Baseline is 12/12 on it cold). Both re-qualified on import: known-good,
known-broken, prompt-faithful witnesses; hidden grader byte-identical to the
tagged tree.

**Measures, per cell, from retained artifacts only.**

- Primary outcome: hidden-grader completion.
- Pathology counts: longest identical-consecutive tool-call run; self-test
  invocations before the last mutation; out-of-scope writes. Counted from
  `tool_execution_start`, one per call, by `census`.
- Cost: turns, tool calls, tokens in/out (`usage_totals`), guard firings,
  and **seconds per turn against context size** — within one machine only,
  never across machines.
- Preservation: destroyed-then-not-restored accepted behaviour in the
  delivered candidate.

**Decision rule, fixed here.** Release one succeeds if both hold at n=12 per
cell:

- **Cold parity.** On each workload, a one-sided Fisher test for *Baseline
  better than Engine* on completion does not reject at α=0.05, and Engine
  delivers no candidate with an accepted behaviour destroyed in more than 1 of
  12. (n=12 detects only a large deficit; the pre-run record states this and
  carries `scripts/power.py`'s figure for the stipulated effect.)
- **Warm win.** On `complaint-lifecycle`, Engine completes more often than
  Baseline, one-sided Fisher α=0.05, with the stipulated effect worth acting
  on set in the pre-run record before the batch. Seconds-per-turn and the
  pathology counts are declared secondaries, reported whatever the outcome.

If cold parity fails with all four engine pieces in place, the shape is wrong
and release one stops with a stated negative. If cold parity holds and the warm
win fails, bare Pi's warm figure is the finding, and isolation is dropped from
release two's design. Both are legitimate completions.

**Denominators.** Every launched cell stays in its cell's denominator; only an
established infrastructure failure replaces one. Nothing pools across
conditions, workloads, models or machines, and no figure from the tagged
trees enters any release-one denominator.

## The model

Frozen by the Ornith 1.5 9B pathology probe
(`docs/current/ornith-9b-pathology-probe-brief.md` on the tagged tree): if two
or more of the three pathologies appear in ≥ 2 of 8 Baseline cells, release one
runs on Ornith 1.5 9B and the 16 GB target is alive. Otherwise it runs on
`gemma-4-12B-it-MLX-8bit` at 32 GB, with Ornith 1.0 35B a second candidate.
Either way the model is one frozen condition for the whole release; the guards'
limits are re-checked against it before Phase 3.

## The restart

Tag both `main`s (`pre-release-one-2026-09-13`). In each repo,
`git worktree add --orphan -b release-one .claude/worktrees/release-one`.
Nothing arrives by default; every imported file is `git checkout <sha> -- path`
with the source SHA recorded in `PROVENANCE.md`.

**`satyrn-evals` imports:** `grade`, `capture`, `attempt`, `session` and their
core (`workspace`, `patch`, `oracle_hook`, `verdict`, `receipt`, `manifest`,
`taskenv`, `deadline`, `repeat_limit`, `contamination`, `errors`); the Pi
adapters; `census`, `preflight*`, `interleave`, `tally`, `usage_totals`,
`power`; the two workloads with witnesses; `packet.py` as the contract;
`BRIEF.md`'s invariants and comparison policy; `pathologies.md`,
`remediations.md`, `lessons.md`. **Leaves behind:** the packet route
(`route`, `chain_record`, `engine_delivery`, `hp7_live_route`), Phase V
(`claim_*`, `phase_ledger`, `reconcile_claims`, the gap register), the
overnight launchers and grading extractors, the user-story variant,
`session-ordering-regression`, `session-mechanics`, and all of `docs/current`.

**`satyrn-engine` imports:** contract, protocol and adapter, mutator, runner,
worktree/candidate/receipt delivery, the TS guards and their replay fixtures,
V4 authoritative validation, V5 turn/deadline budget. **Leaves behind:**
`deliver_chain` and the HP3 orchestration surface.

Tests come with their modules; the planted subprocess tripwire comes first.

## Process, and how it is enforced

**Unattended is for building; attended is for deciding and spending.** The
maintainer and the design agent decide phases and specs in sittings; overnight
agents execute a written plan, task by task, and stop at anything the plan did
not foresee.

Per phase: brainstorm → spec → plan (attended) → execution (overnight,
subagent-driven: implementer, then spec-compliance review, then code-quality
review, per task; TDD against fakes and replay fixtures) → one acceptance
review (one pass, one model, "accept" or an itemized list; no reviews of
reviews). Morning: one status page.

**Mechanical gates, because prose did not hold:**

- The launcher is the only path to a model. It refuses without a frozen JSON
  record (schema-checked: task digest, arm, model, n, stop rule, decision
  rule), the previous result committed, and n and wall-clock under the cadence
  cap. Unattended mode is a flag only the weekly-batch profile may set.
- `docs/`: a result is one file, ≤ 120 lines, with a fenced recompute
  command; at most twelve result files before one is folded into
  `pathologies.md` or `lessons.md`; no new directories. `ROADMAP.md` ≤ 150
  lines. All fail the gate.
- Reviews run through one script (commit range, one model, one output file)
  that refuses if a review for that range exists.
- Repository hooks block `pi -p` outside the review script, and block writes
  to result and review files under `docs/` outside the launcher and review
  script; specs, plans, `pathologies.md` and `lessons.md` stay hand-editable.
- Overnight stop conditions: plan underspecified → write the question, stop;
  a task fails acceptance twice → stop; a red gate whose fix is not in the
  plan → stop; anything wanting inference → stop.
- Live inference only for what a recording cannot answer. Guards are proven by
  replay over retained transcripts before they run live; derivation against
  fixture repos; result shaping against recorded pytest output.

**Cadence.** Attended cycles (≤ 1 GPU-hour, n ≤ 8) until the guards-loaded
route runs clean once and the probe has answered; then one weekly powered batch
on the 32 GB M1 Pro (record and grant frozen in daylight). The instrument-only
cap stands: two consecutive instrument pieces stop the loop, and a token n=1
run does not restart it.

## Roadmap

| # | Phase | Mode | Done when |
|---|---|---|---|
| 0 | Restart: tags, orphan worktrees, the import with provenance, gates green, the launcher gate, docs cap, review script, hooks | overnight | both trees build; default tier green; `just gates` enforces the caps; `PROVENANCE.md` names every file's source SHA |
| 1 | Engine `/implement` v1: derived contract, guards on the dispatch route, carried tests, compact results, receipt | overnight, fake-first | every component has a replay or fixture test in both directions; a fake model completes `/implement` end to end with no inference |
| 2 | Eval core: two workloads re-qualified, `census` for the three counts, the warm prefix as a fixture, cold/warm launcher profiles | overnight, except the one attended prefix recording | the eval runs both arms and both conditions against a fake and produces the per-cell table |
| 3 | Route proof: one cell per arm per condition | attended | guards fire where retained evidence says they should; receipts read; the model probe has fixed the model |
| 4 | Comparison: n=12 per cell on the M1 Pro | unattended batch, frozen in daylight | one result page against the decision rule |
| 5 | Decide and ship, or stop | attended | release one published, or a stated negative |

The Ornith probe runs alongside 0–2.

## Carried gaps and risks

- The four engine pieces have never run together; two alone went 7/12 vs 4/12.
- Guards cost reach: the guard arm reached phase 4 in 8/13 vs plain 21/22. A
  refusal is a new signal to a model that repeats. Watched in Phase 3.
- What is not written down is lost: a fresh segment invented `required_fields`
  where the prior one had `fields`. The contract and checks are the writing-down;
  this is the product's ceiling and the eval's caveat.
- Path-less `edit` calls (141 across 19 cells, both arms, night-to-night
  variance) are counted, not remediated, in release one.
- The warm win is a prediction with no data behind it.
- Ad-hoc `/implement` is supported by design and exercised only through the
  warm recording; it is not separately powered.

## Deferred, deliberately

Contributors bringing their own workflows in as suites; a fifth roadmap phase
from the real AgentClinic roadmap; the isolation-vs-guards ablation; the
16 GB target if the probe is negative; the orchestrator skill; the
`session-ordering-regression` hazard question; any course-derived claim.
