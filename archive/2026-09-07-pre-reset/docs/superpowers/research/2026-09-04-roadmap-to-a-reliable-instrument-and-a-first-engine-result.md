> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# Roadmap to a reliable instrument, a fitting suite, and a first Engine result

**Status: DRAFT for maintainer review. Not committed. No code follows until
each phase posts its own design proposal and is confirmed (`CLAUDE.md`).**
Written 2026-09-04 against `main` @ `a58f583`. Companion to the deep review
(`2026-09-04-v5-v8-deep-review-and-agentclinic-ladder.md`, same scratchpad),
which carries the findings this plan responds to; findings are cited here as
**E**n / **M**n / **T**n from that document.

## 0. The three goals, and what a roadmap can actually promise

| | Goal | Deliverable a roadmap can guarantee |
|---|---|---|
| **a** | A reliable eval harness | Yes — defects are enumerated and fixable (T1–T14, §3 of the review) |
| **b** | AgentClinic suites that fit the purpose | Yes — "fit" is measurable as a placement profile, and the suite is authored to hit it |
| **c** | An initial Engine result that beats Envelope (and Baseline) | **No — and this is the most important sentence in this document** |

Goal (c) names an *outcome*. A roadmap that promises it is a roadmap that
will tune until it gets it, which is the failure this repository already
refused once by name: the `local-pings` re-admission entry sets aside
"simply increasing n" as a **"tune-until-separated risk"**
(`BACKLOG.md:145-151`), and the harvest index records "never switch the
admission metric after seeing the result"
(`S/research/2026-08-16-harvest-index.md:161-163`).

So what this roadmap delivers for (c) is: **a preregistered, adequately
powered, confound-controlled three-arm comparison on cells chosen for
headroom before any arm runs — whose null result is published with the
same prominence as a positive one.** If Engine does not beat Envelope,
that is the finding, and it is worth more than the alternative, because it
would redirect engine work that is currently justified by a retracted
ranking (`S/research/…overnight…md:87-89`, "Does not survive: the ranking,
and any use of this block to justify an engine change").

Two things make a positive result plausible enough to be worth the nights:
the three-arm pilot recorded Baseline 0/6, Envelope 0/6, **Engine 6/6** on
`stringified-annotations` (`S/specs/2026-09-02-v5a-admission-rule-design.md:222-232`),
and the Engine arm moved a floored `local-pings` to 2/4 in the follow-up
(`:147-155`). Neither is on this repository's qualified path, and both
predate the V7/V8 instrument — which is exactly why (c) is a phase and not
a citation.

## 1. Decisions recorded (maintainer, 2026-09-04)

1. **Reopen "Transcript-derived summary metrics"** — yes. Its reopen
   condition said "when the engine exposes these counts across the seam"
   (`BACKLOG.md:37-38`); the maintainer reopens it on the different ground
   that the artifact is already preserved and the reader is offline. The
   entry is amended, not deleted, and the change of grounds is recorded.
2. **Contract rungs are a manifest field** — `contracts: {R0…R3}`, with
   today's `contract` remaining the default and equal to R3.
3. **Model ladder: Gemma 12B and Gemma 26B-A4B only.** Mellum is excluded
   for now. 26B-A4B stands in for 27B.
4. **Vendor `specs/` into `base/`** — yes (re-runs the 24/24 gate and
   re-derives every contamination pair).
5. **Amend V5a's band note** with the power observation (M4).
6. **W1 keeps the 100% branch gate as the invariant**; coverage falls out
   of deleting the arms, with a recorded correction in `docs/sdd.md`.

### The ladder, verified rather than listed

`gemma-4-12B-it-MLX-8bit` answered a **real one-word completion** on the
local oMLX server on 2026-09-04 (`127.0.0.1:8001`), not merely appearing
in `/v1/models` — the harvest index's "preflight that could not fail"
incident is exactly this check (`…harvest-index.md:113-117`):

```
gemma-4-12B-it-MLX-8bit          'OK'   usage 19
```

**26B point revised, same day, before any batch ran.** The originally
verified `gemma-4-26B-A4B-it-OptiQ-4bit` (4-bit) is being replaced with
**`mlx-community/gemma-4-26b-a4b-it-8bit`**, currently downloading
(~35 GB against 128 GB RAM; confirmed to exist via the HF models API this
session). Reason: at 4-bit the 26B point carried *fewer effective bits per
active parameter* than the 12B's 8-bit, conflating parameter count with
quantization noise in any "does the bigger model do better" reading.
Matching quantization isolates the one variable this ladder is meant to
vary. **Re-verify with a live one-word completion once the download
finishes and before V12's first cell** — the same check the 12B already
passed, not a listing check.

**Stated limit, to be carried in every profile table regardless.** These
remain two capability points, **not a size scale**: the 12B is dense; the
26B-A4B is a mixture-of-experts with **4B active parameters** — fewer
active parameters than the 12B despite the larger total and matched 8-bit
quantization. Any sentence of the form "the larger model…" is unsupported
by this pair. The honest phrasing is "gemma-12B-8bit" and
"gemma-26B-A4B-8bit", named in full, every time.

## 2. Goal (a): a reliable eval harness

Three phases, **none of which runs a model**, so they cost no inference
nights and can proceed while batches run.

### V9 — Loop integrity and re-scoring

The batch machinery goal (c) depends on cannot presently survive a batch.
`run.py:35-46` has no per-cell failure boundary: one exception in cell k
discards the whole summary and the k−1 completed cells are unsummarized
(**T1**). `attempt.json` is written only after grading returns (**T2**),
so a grading exception makes a cell invisible. Nothing rebuilds a summary
from disk — `load_attempt_record` has no production caller (**T3**), so
BRIEF rule 3 ("a grading defect must be fixable and re-scored without
re-running a model", `BRIEF.md:72-75`) has no executable form. Summaries do
not name their arm (**T4**).

Ships: a per-cell boundary that records a cell's failure as a cell outcome
and continues; record-before-grade ordering; `regrade ATTEMPT_DIR` and
`summarize OUTPUT_DIR`; `task`/`command`/`timeout` on the summary; fixes
for the V7 preservation-overlay regression (**T5**), the umask-002 refusal
of every hidden task (**T6**), the wheel-install `PYTHONPATH` mis-attestation
(**T7**), and grading's ambient-environment `git init` (**T8**); the
oracle-result forgery limit (**T9**) recorded beside BRIEF rule 4; the 30 s
attempt default raised (**T14**). Every fix with its refusal/success pair.

*Why first:* a 200-cell batch on today's loop risks losing a night to one
exception in cell 190, and V5d's smoke discipline cannot catch it because
smoke is n=1.

### V10 — Pathology counts from the preserved transcript

Decision 1 reopens this. An offline reader of the preserved Pi stream-JSON
— the same relationship `grade` already has to `patch.diff` — counts, per
attempt: tool calls by name, identical repeats, churn, no-op edits,
test-runner invocations, announce-and-stop turns, reach outside the
workspace, and overlay-content windows in the transcript bytes. Reports
`unmeasured`, never zero, where the artifact is absent or unparseable
(the absence-of-signal rule, `…overnight…md:161-163`). Carried by
`summarize` beside the verdict counts; **no wall-clock**.

*Why it matters for (c):* BRIEF's question is "did my engine fix help,
**and if not, why**" (`BRIEF.md:22-24`). Verdict counts answer the first
half. Every pathology in the predecessor's own catalogue — the 245× `ls -R`,
no-op edits, path-keyed churn, announce-and-stop, grader hunting — is in
these transcripts and currently uncounted. The V8 smoke already shows the
shape: 6 reads, 2 edits, **0 test runs** (audit; **M3**), invisible to
`summary.json`.

*Sequencing:* it reads artifacts V12 will already have preserved, so it can
land after the first batch and be applied retroactively to it.

### W1 — Weight

~350 of `workspace.py`'s 1,138 lines and ~270 of `capture.py`'s 754 serve
hypotheticals no recorded incident produced; ~2,000 default-tier test lines
exist to reach those arms, and the 100% branch gate and the arms are
feeding each other (review §5). Ships: the nested cleanup ladders collapsed
to `try/finally` plus a ~20-line containment check; one git-plumbing module
replacing four git runners (two of which skip the safety config); legacy
record generations and the Windows branch deleted; four code enums (33
values) unified; capture frozen; glossary and `docs/reference/formats.md`
brought up to V6–V8. Coverage stays 100% and falls; the correction is
recorded in `docs/sdd.md`, not edited away.

*Land after V9* — same files.

## 3. Goal (b): suites that fit the purpose

"Fit for purpose" is made measurable: **the suite fits model M when M has
at least one task-rung in each band, and has headroom at M when at least
one task-rung sits below ceiling on the reference arm.**

### V11 — The evidence ladder

Today every shipped contract states the fix — the L3 rung — four of six
name hidden test ids, and all six name the file (**M1**, **M2**). The
fixtures' own author warned that this makes `plausible-wrong-fix` "an L3
cell wearing L1 clothes" (`F/repair/README.md:67-76`). The difficulty dial
exists and is welded to its easiest setting.

Ships, per decision 2, one manifest field:

| rung | contract carries | fair when |
|---|---|---|
| **R0 blind** | task + "the acceptance suite is red; the spec is in `specs/`, public tests in `tests/`" | the public suite or spec exposes the defect |
| **R1 digest** | + failing hidden test ids and assertion text | always |
| **R2 located** | + the file(s) | always |
| **R3 stated** | + the fix in prose — **today's contracts** | always |

Also ships: `specs/` vendored into every `base/` (decision 4); the hidden-id
leak closed by widening the V7 name check beyond overlay *filenames*
(**M2**); the engine contract **generated** from manifest + rung, so the
text the model sees is the text on record (the V8 smoke's hand-authored
contract differed from the manifest by a token and narrowed
`writable_paths` to `[app.py]`); and a shipped **`satyrn-evals-attempt-pi`**
adapter that takes `--tools` and `--extension`, replacing the baseline
wrapper that today lives in a scratch directory with a recorded "minor
drift between this source and the executable"
(`S/research/2026-09-03-local-pings-reprobe-protocol.md:110-143`). That one
adapter defines all three arms of goal (c) by recorded argv plus pinned
digests — which is why it belongs here rather than in V13.

**Authoring gate (the rung is a claim, so it gets a check):** a task-rung
is mislabeled if successful attempts are not non-decreasing R0→R3 at fixed
n for a given model. V12 measures it; a violation sends the contract back.

Public-suite state at base, re-derived this session
(`uv run --locked pytest tests` per shipped `base/`): five of six are red
(1 failed / 3 passed ×4, plus one collection abort); `framing-2-edit` is
**4 passed** — its defect is visible only to the hidden suite, so R0 is a
wall there by construction and the profile must say so rather than record
a floor.

### V14 — Build rungs on the same app

Repair is 1–3 line edits on a 66-line app; it is a microbenchmark, not
development. The build shapes use the same app, the same 13-test hidden
oracle, and the vendored spec: phase-3-missing, phases-2–3-missing,
all-missing (from `broken/app.py`), then the three-prompt **session** task
— the V6 machinery's first real consumer. `framing-2` joins this rung as
the author-from-scratch cell. The cumulative-suite backlog entry
(`BACKLOG.md:206-217`) closes as "hand-authored", its recorded exit.

*Conditional on V12*: build rungs are how the 26B gets headroom if it
ceilings on repair. **Engine-side blocked** — see §5.

### V15 — A second application

Reopens only when the profile places the 26B at ceiling on every AgentClinic
rung including build. A larger fixture (≥500 lines, ≥3 modules, a real
dependency graph), packaged the V8 way.

## 4. Goal (c): a first Engine result

### V12 — The placement profile (prerequisite, reference arm only)

Gemma-12B and Gemma-26B-A4B × 6 tasks × 4 rungs on the **reference arm
only** (`satyrn-evals-attempt-pi`, bare Pi, `read,bash,edit,write`), at
fixed n, recording V5b's three-way split — successful-attempt outcome,
retained-patch production, conditional retained-patch quality — plus V10's
pathology counts. Bands per V5a's definitions. Ships a **per-model
tool-call preflight**: two of the six roster models scored zero for
protocol rather than capability (`…overnight…md:199-203`), so V5d's
"positive evidence the model started" is extended to "positive evidence the
model emitted a well-formed tool call", one canary turn before a model's
first cell.

**Expected bands are written down before the first cell**, from swiftstar's
Block B (n=20, TSV-recomputable: `plausible-wrong-fix` 19/20, `depth-2`
12/19, `depth-3` 8/18, `framing-2` ~1/6 — `R/2026-08-29-block-b-negative-result-analysis.md:49-60`)
and from overnight block 7's gemma-12B repair rates (7/12, 7/12, 11/12 —
`…overnight…md:25-29`, the confounded block, used as a prior and labelled
as one). Writing the prediction first is what stops the profile from being
read after the fact.

Output: a table placing every (task, rung, model) cell in a band — the
first artifact in this project's history that answers "is this suite the
right difficulty for this model."

### V13 — The three-arm probe

**The arms.** Baseline and Engine exist; **the Envelope must be defined
prospectively**, and this is a decision, not a reconstruction. Verified
again this session: all seven `envelope-cap.ts` copies on this machine hash
`0448af10…`, never the canonical pin `b7455133…`, and the era's Pi version,
adapter, and harvesting were never recorded — so "**any** Envelope
assembled with current Pi, a new adapter, or a selected prompt is a new
prospective arm, not a reproduction"
(`S/research/2026-09-03-local-pings-deadmission.md:38-44`). The phase
therefore ships an Envelope *definition* — a re-authored budget-cap
extension pinned by sha256, `--tools read,write`, recorded argv — and calls
it what it is.

**What each arm isolates.** Baseline: bare Pi, broad tools, contract as
prompt. Envelope: bare Pi + a spend cap + narrowed tools — the *cheap*
intervention. Engine: handoff contract + mutator + loop breaker + bounded
replacement, `read,edit`. **Engine > Envelope** therefore means "the
engine's machinery beats merely capping the budget," which is the product
claim worth making.

**The tool-surface asymmetry, stated as a limit rather than hidden.** The
three arms do not share a tool surface (**M3**): Baseline has `bash`,
Envelope can create files, Engine can do neither ("Do not create files",
`E/attempt.py:238`; `--tools read,edit`, `:263-264`). Because each surface
is that product's own design choice, a **product-level** comparison is
legitimate. A **mechanism** claim ("the mutator is what helped") is not
available from this design and must not be written — that is precisely the
error the overnight run made when `factonly`'s advantage and its protection
shared one cause (`…overnight…md:74-80`). Consequence for scope: **the
first probe runs on pure-edit repair rungs**, where the surfaces are
closest (neither Envelope nor Engine can run tests), and the author/build
rungs wait for the engine-side work in §5.

**Choosing n by arithmetic rather than habit.** One-sided Fisher exact,
computed this session, as *design input for choosing n* — the reported
result stays counts and bands, with no intervals and no void accounting
(the claims layer stays deferred, `BRIEF.md:33-36`):

| Engine | Envelope | p |
|---|---|---|
| 4/8 | 0/8 | 0.039 |
| 4/8 | 1/8 | **0.141** |
| 6/12 | 0/12 | 0.007 |
| 6/12 | 1/12 | 0.034 |
| 8/12 | 3/12 | 0.050 |

n=8 suffices only if Envelope lands at exact floor; a single Envelope
success at n=8 destroys the separation. **n=12 per arm** on a small number
of cells is the defensible choice, and the preregistration must state what
happens when Envelope is not at 0 — decided before the run, not after.

**Cell selection** comes from V12: cells where the reference arm is *not*
at ceiling and *not* a capability wall (floor with no retained patch
passing a preservation-safe oracle) — V5a's own criteria
(`…v5a…design.md:104-110`). Arms are **interleaved** cell by cell, not run
as contiguous blocks: the harvest index retracted two published figures
for contiguous-block scheduling (`…harvest-index.md:187-190`), and while
the reported metric is counts, timeouts are load-sensitive and timeouts
become counts.

**Success and null are both publishable, and the null is specified now:**
if no arm pair separates on any selected cell, the finding is "the engine's
current composite does not move this suite for this model at this n," the
`facts` field's justification stays unearned (`satyrn-engine/BACKLOG.md:48-54`),
and V14's build rungs become the next candidate rather than a bigger n.

## 5. Owed to satyrn-engine (blocking, not this repository's phases)

1. **Merge `d5d5d37`** (pi `--model` as separate tokens) to `main`. The V8
   smoke's pass currently depends on an unmerged branch,
   `research/facts-field-backlog` (**E8**) — a hard blocker for any Engine
   arm.
2. **A test runner the model can invoke.** The overnight record's own
   requirement for a corrected profile (`…overnight…md:124-126`); without
   it the Engine arm cannot attempt R0 and cannot self-verify, and V8
   §11.7's "working local runner" is true only of the Baseline arm.
3. **File creation** for the author and build rungs. Blocks `framing-2`
   and every V14 shape for the Engine arm.
4. **The `facts` field stays where the engine's backlog put it** — after an
   Evals experiment isolates contract content from contract delivery
   (`satyrn-engine/BACKLOG.md:48-54`). V11+V13 is that experiment's
   instrument; item 2 is what makes the isolation clean.

## 6. Critical path and cost

```
V9 ──► V11 ──► V12 ──► V13   (first Engine result)
 │       ▲       │       ▲
 └► W1   │       └► V10  │
      E-1┘ (engine: merge d5d5d37)   E-2/E-3 (runner, write) ──► V14 ──► V15
```

- **No-model work** (V9, V10, V11, W1) blocks no inference and can proceed
  between batches.
- **V12**: 6 tasks × 4 rungs × 2 models × n=6 = 288 reference cells. At the
  reprobe's observed per-cell range, three to five nights. Trimmable by
  dropping R2 from the first pass.
- **V13**: 3 arms × n=12 × the selected cells. Four selected cells = 144
  cells, two to three nights.
- Everything before the first Engine result is roughly **a week of nights
  plus the no-model phases**, assuming E-1 lands.

## 7. What would make this fail, stated in advance

1. **Both Gemma points ceiling on repair at R1.** Likely for R3 given Block
   B's 19/20. Mitigation: R0/R1 and V14's build rungs carry the headroom;
   this is why the rungs come before the probe.
2. **The 26B-A4B floors everywhere** (4B active is small). Then it is a
   capability wall, not a headroom point, and the 12B is the workhorse —
   recorded, not tuned around.
3. **Envelope and Engine both floor** on every selected cell. Then the
   comparison is unmeasurable at this difficulty and the selection moves
   down a rung — a rung change is a new preregistration, never a re-read of
   completed cells.
4. **The engine's missing test runner dominates** whatever its machinery
   contributes. This is the outcome I consider most likely if E-2 does not
   land, and it would make a null result uninformative about the machinery
   — which is the argument for treating E-2 as a blocker rather than a
   nice-to-have.
5. **Rungs prove non-monotone** (the V11 authoring gate fires), meaning a
   contract is mislabeled. Cheap to fix, but it invalidates that cell's
   placement and must be caught in V12, not in V13.

## 8. Still open

1. **Envelope's definition** is a design decision owed its own proposal:
   what the re-authored cap extension caps (turns? tokens? both?), and
   whether the Envelope keeps `write`. My recommendation: cap turns and
   tokens at the pilot's recorded values (900 s wall, 8192 max tokens, 80k
   context — `…deadmission.md:52-56`), keep `read,write`, and pin the new
   extension by digest.
2. **n for V12.** I propose 6 (placement only, explicitly not an admission
   claim), reserving 12 for V13's confirmatory pair.
3. **Does V12 include R2?** Dropping it saves 72 cells; keeping it makes
   the monotonicity gate stronger.
4. **Where the arm definitions live** — a committed `arms/` directory in
   evals with pinned digests, versus a protocol document per probe. I
   recommend the former; the latter is what produced the recorded
   source-versus-executable drift.
