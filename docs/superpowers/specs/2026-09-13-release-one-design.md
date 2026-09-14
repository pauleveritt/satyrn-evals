# Release one — design

**Written 2026-09-13; rewritten 2026-09-14 after Phase 0 and three Ornith
probes. Phase 0 is done under the first version (git history). This version
authorizes Phases 1 and 2 and nothing that spends inference except the
attended admission sittings named below.** Probe results cited here live on
their probe branches in this repository and are evidence, not guidance.

## North star, and the one claim release one makes

Keep a small model on track, so a Python developer can use local AI and stay
at the wheel. The developer's engineering is domain engineering — write down
what you are building, in specs and tests — not agent engineering.

**Primary claim.** On the ceiling workload, the Engine delivers a passing
candidate within budget more often than bare Pi, on Ornith 1.5 9B.

**Secondary, declared, reported whatever the outcome.** On the floor
workload, where both arms pass, the Engine costs no more tokens and turns.

Budget is output tokens and turns. Seconds are a machine-specific backstop,
reported per machine and never compared across machines. Nothing else is
claimed. Spec compliance is the model's and the developer's writing-down; the
eval counts it and does not remediate it.

## What the evidence settled

Carried from the first version:

- **The autonomous chain is retired.** Every "Engine" loss since 2026-09-09
  was a fresh-context worker in an orchestrated chain run without the
  engine's guards. That measured isolation, not the engine.
- **Tests preserved behaviour, not memory.** Baseline's own tests covered the
  destroyed route 12/12; the edit guard held it in 0/9 candidates.
- **Pointer prompts lose** (PD5: 1/8). Facts go inline; only executable
  checks live on disk.
- **SLM-authored contracts lost** (3/8 vs 8/8). The contract is derived by code.
- **Taking tools away lost** (V13d). Both arms keep Pi's native tools.

New on 2026-09-14:

- **Ornith does not show gemma's pathologies.** Pathology probe: 0/8, 1/8,
  0/8 (`main:docs/current/ornith-9b-pathology-probe-result.md`). Ornith was
  chosen anyway: it fits 16 GB, decodes at a median 43.5 tok/s against
  gemma-4-12B's 25.8, and the goal is a better coding experience, not a model
  that fails measurably. The claim moved from pathologies to a ceiling.
- **Ornith has a ceiling on harder work.** AgentClinic `depth-3` at R1 is
  0 of 4 uncontaminated at a 900 s command budget
  (`worktree-ornith-ceiling-probe` 4f0ee53). Tasks cut from this repository's
  Phase 0 commits fail 3/4, 3/4 and 1/4 once the adapter's artifacts are set
  aside (`worktree-selfhost-headroom-probe` 635c12b).
- **The model hunts for the answer key, and the machine has one.** Five of
  twenty-four ceiling and headroom cells ran root-anchored `find`. The only
  `depth-3` pass read a copy of the hidden suite that a harness test had left
  in pytest's temp directory, ran it to 13 passed, then submitted. One
  self-hosted cell read the reference solution from a controller's staging
  directory. Neither cell was caught: the receipts said clean and the census
  counted at most one escape. Isolation is a condition of every cell.
- **The harvest lost work.** The Pi adapter takes `git diff HEAD`. Four cells
  committed inside the worktree and scored `NO_PATCH`; untracked new files
  are invisible to it.
- **Every Ornith number before 2026-09-14 14:25Z ran on server-default
  sampling.** The served id had no oMLX settings entry. It is registered and
  verified now. Earlier numbers admit nothing; they say which tasks are worth
  re-measuring.
- **Every retained run started from an empty session.** Real use starts warm.
  Decode rate falls with context: fitted 48–55 tok/s under 20k input,
  24–33 tok/s at 80–120k.

## The product: `/implement`

The developer works in an ordinary, long Pi session. When they say "do Phase 3"
or "add a status badge to the complaints page", the engine runs that one
bounded piece in a **fresh, small model context**, in its **own worktree**,
under a **derived contract**, with the **guards loaded**, and hands back a
**candidate plus a compact receipt**. The main conversation receives the
receipt, never the transcript. The developer reviews the candidate.

### Components

1. **Contract derivation** (Python, deterministic; the request is the only free
   input): `objective`, `writable_paths` (shown for confirmation),
   `self_test_command` from `pyproject`, `preserve` (tests that exist now),
   `checks` (the developer-owned `checks/` directory), and budgets in tokens
   and turns. The developer sees it on one screen and says go. Reuses HP1's
   builder and schema, renamed to what it is.
2. **Dispatch** (Python core; TS adapter). One fresh Pi invocation with the
   same model and native tools, plus the engine extension, in a worktree
   branched from the developer's HEAD. One process per operation.
3. **Guards** (TS, on Pi's `tool_call` event), each answering a pathology:

   | # | pathology | evidence | guard |
   |---|---|---|---|
   | 1 | repeat / read-lock loops | gemma: 281 identical reads per locked cell; Baseline locked 8/12 vs Engine 1/12 (V14b) | loop breaker keyed on workspace revision |
   | 2 | never running its own tests | gemma: runner took Engine 6/12 → 12/12 (V13e); Ornith G3/G4 timed out with zero suite runs | self-test command in the loop, result from exit code |
   | 3 | writing outside declared scope | gemma: `SCOPE_VIOLATION` 09-04, 09-08, 09-13 | writable-path check refuses the mutation |
   | 4 | unbounded command | Ornith: two `depth-3` timeouts spent 843 s and 861 s in `find /` | bash `timeout` set to 120 s when absent, clamped at 300 s; the result appends one sentence naming the bound and the self-test command |

   Plus a symbol-preservation refusal: an `edit` whose `oldText` removes a
   symbol the accepted base defines is refused with a message that says what
   to do instead. Guard 4 changes events, so it is proven live in Phase 3;
   guards 1–3 are proven by replay first.
4. **Accepted tests carried read-only.** `preserve` tests and `checks/` are
   copied outside `writable_paths` and run by the self-test command.
5. **Compact results.** The runner returns failed test ids and the first
   assertion line; a successful edit returns the changed hunk. Both are
   counted in tokens, so "compact" is a measurement.
6. **Receipt.** Candidate commit, validation exit code (authoritative, never
   the model's prose), turns, tool calls, tokens in and out, guard firings,
   budget state. One JSON file.

**Bounds ownership.** Pi owns the per-command bound: its bash `timeout` and
its own process-group kill. The engine only sets or clamps that field. No
wrapper process — `timeout`, alarms, `ulimit`, `sandbox-exec` — in either
tree. The engine's runner keeps its own subprocess timeout for the self-test
it runs itself. The 120/300 values are frozen in the Phase 1 plan against
measured suite durations.

### What `/implement` does not do

No orchestrator, no roadmap-driving loop, no retry campaign, no subagent the
developer did not invoke, no hidden-grader access, no filesystem sandbox.

## The model

Ornith 1.5 9B, served id `Ornith-1.5-9B-MLX-8bit` on oMLX, frozen for the
whole release. Native context 262,144; a cap is set only if the context-speed
probe says so. Sampling is the model card's coding setting: temperature 0.6,
top_p 0.95, top_k 20, min_p 0, thinking on.

**Settings are verified, not declared.** `scripts/preflight_settings.py`
compares each arm's `inference` block with the oMLX server entry and Pi's
model entry, fails preflight on any difference, and emits a provenance block
of digests that every run record carries. The server reads its settings at
start; a settings change counts only after a restart, and the first request
after it is logged.

**Context-speed and concurrency probe (Phase 2, attended, no task
outcome).** Decode tok/s at prompt sizes near 5k, 20k, 40k, 80k and 160k,
and total output tok/s with 1, 2 and 3 concurrent streams, read from server
logs. It decides whether a context cap is set, what the warm condition costs,
and the campaign's concurrency.

## The eval

**Arms.** *Baseline*: bare Pi 0.85.1, tools `read,bash,edit,write`, no
extensions, the frozen model. *Engine*: the same, with each task run through
`/implement`. Identical prompts, tools and model. A product comparison;
attributing a difference to isolation versus guards is release two's.

**Isolation, both arms.** The model runs as a second local user,
`satyrn-cell`, with its own home, per-cell `TMPDIR`, Pi, uv and Pi model
config. The harness, grader, task directories, scratch and retained cells
stay under the maintainer's uid at mode 700. The worktree lives in a
group directory the cell user writes and the grader reads. `~/satyrn-smokes`
is closed to other users. Nothing is sandboxed: `find /` still runs and finds
nothing that grades. No container, in this release or as a planned path.
The control is one condition of the campaign, never a per-arm setting.

**Budget, both arms.** 32,000 output tokens, thinking included, and 48 turns
per attempt, enforced by the harness reading the transcript as it is written.
A cell over either is `BUDGET_EXCEEDED`, a fail. Wall-clock backstop on this
machine: 1,800 s per attempt command, 2,100 s attempt deadline; a backstop
cell is `COMMAND_TIMEOUT`, also a fail. Every observed pass sits under 22k
tokens and 24 turns; the build tasks' finishing cells used 27–38k tokens and
44–49 turns. If every Baseline admission pass lands under 15,000 tokens and
24 turns, the campaign budget is 24,000 tokens and 36 turns instead; the
campaign record states which. Evals imposes no per-command bound in either
arm: Baseline commands are unbounded, because that is bare Pi.

**Concurrency, both arms.** Cells run k at a time, with k the largest of 1, 2
or 3 at which the probe measures total throughput at least 1.5 times k = 1.
The claim is in tokens and turns, so k does not touch it; seconds are
reported per k and never compared across k. k is frozen in the campaign
record and is the same for both arms, which stay interleaved.

### Workloads

**Why a set.** A claim resting on one hand-picked task is a claim about that
task. The ceiling set is four tasks of two shapes (repair, build) from two
sources (AgentClinic, this repository), plus two held-out tasks.

**Admission.** A task enters the ceiling set when, on declared sampling and
under isolation, bare Pi passes at most 1 of 4 attended cells within budget
and no passing cell read material outside its worktree. A task enters the
floor set when bare Pi passes 4 of 4. A ceiling candidate that passes 2 of 4
or more moves to the floor set.

| ceiling candidate | shape | source | evidence | admitted when |
|---|---|---|---|---|
| `agentclinic-repair-depth-3` R1 | repair, three seams | AgentClinic, imported with provenance | 0 of 4 uncontaminated at 900 s | 4 attended cells under isolation |
| `selfhost-run-record-gate` R1-plan | build, module + CLI wiring | this repo, `cc9ab53` → `b253c99` | 0 of 4 on the rule; three timeouts, one cell read the answer key | harvest fixed; 4 attended cells |
| `selfhost-guard-prefixes` R1-plan | repair, one regex | this repo, `3e996a1` → `4a54743` | 1 of 4; two timeouts with zero suite runs | 4 attended cells |
| `selfhost-review-script` R1-plan | build, pure core + CLI | this repo, Phase 0 plan Task 9 | untested | qualified; 4 attended cells |

**Floor set.** `agentclinic-repair-depth-2` R1 (4 of 4, 85–156 s) and
`selfhost-docs-linter` R1-plan, re-measured on the fixed harvest: its four
fails were the adapter's, and every model finished. `misleading-locus` and
`complaint-lifecycle` leave the claim; Ornith passes both 4 of 4.

**Held-out tasks.** Two tasks are cut by the generator at batch freeze, in
daylight, from commits no earlier task used, and committed with the campaign
record. They are qualified offline and never pre-measured. They run in
Phase 4 at n = 6 per arm, both in one night. They cannot supply a win; a
held-out task where the one-sided Fisher test for Baseline better rejects at
α = 0.05 counts as a loss (at n = 6 that needs a gap of at least 4 of 6). The
held-out check is a tripwire against tuning, not a powered test: it detects a
0.60 against 0.10 reversal with probability 0.38. No Engine change follows a
held-out result.

**Rungs.** AgentClinic repairs run at R1: failing check names and their
assertion text, no location. Self-hosted tasks run at R1-plan: the plan
task's title, Files, Interfaces → Produces, the prose of each step with code
fences removed, and the literal message formats the hidden suite asserts.
R1-plan is richer than R1 and is named so; the two are never compared.

**The self-hosted generator.** A task is `(BASE, GOOD, files, HIDDEN,
plan-anchor)`. `base/` is `git archive BASE` minus plans, specs, `.claude`,
`.github`, `PROVENANCE.md` and the hidden files, plus a `.gitignore` for
runtime residue. `overlay/` holds HIDDEN at GOOD. `known-good.patch` is GOOD's
diff restricted to `files`; `known-broken.patch` stubs the target.
`manifest.json` carries provenance shas, the task-tree digest and the prompt
digest. `tools/cut_task.py` builds it deterministically. Qualification is
offline: `grade` passes known-good and fails known-broken with zero
collection errors; a fake attempt that writes GOOD's files, leaves some
untracked and commits the rest is harvested whole and graded pass; the hidden
suite passes GOOD three times running. Every merged phase yields candidates.

**Conditions.** Every workload runs cold. Warm is a declared secondary on
`complaint-lifecycle` only: a recorded developer prefix replayed
byte-identically, measuring cost against context. It is outside the win rule.

### Measures, per cell, from retained artifacts only

Verdict; output tokens; turns; tool calls; wall seconds; per-turn seconds
from message timestamps; per-command seconds from the adapter's event
timeline; commands over 120 s and tool-reported timeouts; root-anchored
searches and absolute paths outside the worktree, in bash text and file-tool
paths; hidden-suite text in the transcript, scanned for every cell including
timeouts and `NO_PATCH`; `git commit` inside the worktree; suite runs before
the last mutation; guard firings. A passing cell with an out-of-worktree read
of grader material is reported contaminated and counted as a fail.

### Sample and decision rule

n = 12 per arm per task, arms interleaved, with one futility look. After 6
cells per arm, a ceiling task whose Engine passes 1 of 6 or fewer stops and
supplies no win. Futility stopping cannot raise the false-win rate; it lowers
power at the stipulated effect from 0.79 to 0.78 and stops 89% of tasks where
the Engine does nothing. No task stops early for a win: at n = 6 that needs
0 of 6 against 5 of 6, and it would cost power for a 10% saving
(`scripts/seq_design.py` computes both).

A ceiling task is 24 cells, worst case 12 h at k = 1, expected 6–8 h. At k = 2
two ceiling tasks share a night when their expected hours fit the cap.
Schedule: four ceiling tasks, one held-out night, one floor night — six nights
at k = 1, three to four at k = 2. A night the cap stops early completes the
next night under the same record.

**Per task:** one-sided Fisher exact, α = 0.05, on pass within budget.
Stipulated effect: Baseline ≤ 0.10, Engine ≥ 0.60 (power 0.79 at n = 12). A
ceiling task whose Phase 4 Baseline rate is 2 of 12 or more is under-powered: it
is reported and supplies no win.

**Release one wins** when at least 2 of the 4 ceiling tasks reject for the
Engine, no ceiling or held-out task rejects for Baseline, and every floor
task holds parity (the test for Baseline better does not reject). Under the
null, two or more of four rejecting has probability 0.014; the campaign
record states it and no correction is applied.

If the four engine pieces are in place and no ceiling task rejects, release
one stops with a stated negative. That is a legitimate completion.

**Campaign record.** One record, committed in daylight before night one,
freezes model and served id, the server settings digest, Pi version, engine
commit, every task-tree and prompt digest, budgets, isolation, k, the
stipulated effect, the futility look and this rule. Each night's run record names it; the launcher refuses
if any pin drifted.

**Denominators.** Every launched cell stays in its denominator; only an
established infrastructure failure replaces one. Nothing pools across
tasks, arms, conditions or machines. No figure from the tagged trees or from
a probe enters a release-one denominator.

## Harness work the workload depends on

In blocking order; all in Phase 2, both arms:

1. **Harvest against the base commit, untracked files included.** Reuse the
   session path's temporary-index diff with `workspace_base_sha`. Blocks
   every build task.
2. **Two-uid isolation**, including preflight reading the cell user's Pi
   config. Blocks every task: without it no pass reads as a pass.
3. **Token and turn tripwire** in the attempt wait loop. Blocks the rule.
4. **Census extended:** over `COMMAND_TIMEOUT` cells; escapes in bash text;
   transcript contamination scan for every cell; an adapter timeline of
   tool-call start and end times, since Pi's events carry none. Blocks the
   pathology-4 evidence and the contamination cross-tab.
5. **Hygiene, no control:** close `~/satyrn-smokes`, clear leftover attempt
   directories, and stop `tests/test_agentclinic_manifests.py` copying a real
   task into pytest's temp directory.
6. **The generator and R1-plan**, before any self-hosted task is re-measured.

**Before the Phase 1 plan freezes, no inference:** public-suite durations per
task from `grade` on known-good (current estimate 2–6 s AgentClinic, 30–45 s
this repository); decode rate against context from retained transcripts.

**Before admission, attended, after items 1–4:** Baseline only, on declared
sampling, under isolation, at the campaign budget: `depth-3`,
`run-record-gate`, `guard-prefixes`, `review-script`, 4 cells each, in
sittings under the attended cap.

## Process, and how it is enforced

**Unattended is for building; attended is for deciding and spending.** The
maintainer and the design agent decide phases and specs in sittings;
overnight agents execute a written plan and stop at anything it did not
foresee. Opus steers, writes plans and reviews; Sonnet implements; Fable
only when the maintainer names it.

Per phase: brainstorm → spec → plan (attended) → execution (subagent-driven,
TDD against fakes and replay fixtures, per-task review) → one acceptance
review. Morning: one status page.

**A phase builds in half a day.** Phase 1 took a day: 13 tasks, a 2,400-line
plan, and a fix round on most tasks. From Phase 2 on:

- A plan is at most six tasks. A roadmap phase that needs more is split into
  lettered plans (2a, 2b), each with its own final review.
- Before execution, the plan reviewer runs every test the plan specifies
  against the current trees and reports which fail for reasons other than
  the missing implementation. Plan defects are fixed in the plan, not found
  by implementers.
- Task reviews are Opus; scoped re-reviews of a fix diff are Sonnet.
- The controller blocks on every dispatch; nothing runs in the background.
- Tasks in different trees that share no file or interface run in parallel,
  one thread per tree.

**Mechanical gates, in place since Phase 0:**

- The launcher is the only path to a model. It refuses without a frozen run
  record, the previous result committed, n and wall-clock under the cadence
  cap, and a clean `preflight_settings` provenance block.
- `docs/`: a result is one file, ≤ 120 lines, with a fenced recompute
  command; at most twelve result files; `ROADMAP.md` ≤ 150 lines; this spec
  ≤ 400 lines.
- Reviews run through one script that refuses a second review of a range.
- Repository hooks block `pi -p` and direct runs outside the launcher, and
  writes to result and review files outside their tools.
- Live inference only for what a recording cannot answer.

**Cadence.** Attended sittings (≤ 60 min, n ≤ 8) for admission and route
proof. Phase 4 runs as batch nights on this machine, exclusive GPU, record
and campaign frozen in daylight. The batch cap is amended to one night: 24
cells across both arms, 720 minutes. The M1 Pro is not used.

## Roadmap

| # | Phase | Mode | Done when |
|---|---|---|---|
| 0 | Restart: orphan trees, provenance, gates, launcher gate, docs caps, review script, hooks | overnight | done 2026-09-14 |
| 1 | Engine `/implement` v1: derived contract, guards 1–4 and symbol preservation, carried tests, compact results, receipt | overnight, fake-first | every component has replay or fixture tests both directions; a fake model completes `/implement` end to end; 120/300 frozen against measured suite durations |
| 2a | Eval core: harvest, token and turn tripwire, census extensions, hygiene | overnight | harness items 1, 3, 4, 5 have fixture tests both directions; the Engine arm runs against a fake |
| 2b | Isolation and tasks: two-uid isolation, generator and R1-plan, candidates qualified, context-speed and concurrency probe, warm prefix recorded | overnight, plus attended isolation setup, probe and recording | the eval runs both arms against a fake under isolation with the budget tripwire; every candidate passes offline qualification; k measured; settings provenance verified by preflight |
| 3 | Admission and route proof: Baseline admission cells; one Engine cell per ceiling task | attended | ceiling and floor sets fixed; guards fire where retained evidence says they should; receipts read |
| 4 | Comparison: campaign record, held-out cut, three to six batch nights | unattended batch, frozen in daylight | one result page per task and one against the rule |
| 5 | Decide and ship, or stop | attended | release one published, or a stated negative |

## Carried gaps and risks

- The engine pieces have never run together; two alone went 7/12 vs 4/12.
- Guards cost reach: the guard arm reached phase 4 in 8/13 vs plain 21/22.
  A refusal is a new signal to a model that repeats. Watched in Phase 3.
- Hunting is Ornith's dominant ceiling mechanism on `depth-3`. Isolation
  removes the reward, not the behaviour; a Baseline that hunts until the
  budget runs out is the measured condition, and the result says so.
- The `depth-3` and `misleading-locus` hidden suites are byte-identical; a
  leak of one is a leak of both.
- Admission may empty the ceiling set: declared sampling or isolation may
  lift Baseline. Then release one reports the ceiling it found and stops.
- Three to six nights of exclusive GPU is the price of a claim resting on
  four tasks. A stopped night adds one. Concurrency may interact with the
  model's behaviour through prefill contention; the probe measures
  throughput, not behaviour, and Phase 3's route proof runs at k.
- What is not written down is lost; the contract and checks are the
  writing-down. This is the product's ceiling and the eval's caveat.
- Path-less `edit` calls are counted, not remediated.

## Deferred, deliberately

Contributors bringing their own workflows in as suites; the isolation versus
guards ablation; pattern refusal of hunting commands; a filesystem sandbox
for `/implement`; the orchestrator skill; a depth-4 AgentClinic task; any
course-derived claim.
