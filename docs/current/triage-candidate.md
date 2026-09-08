# Stage 3.1: the named engine change

This records the candidate the triage screen will test, and the candidates
already closed. Naming a candidate authorizes no spending.

## Closed: whole-attempt duplicate-call retention

**Question asked.** Does retaining duplicate-call history for the whole attempt
reduce eviction-driven cycling and total cost, without disrupting productive
repair and verification?

**Rejected** by the offline recovery guardrail, before any live spending. The
reproducer is retained at
`~/satyrn-smokes/2026-09-08-breaker-window-reproducer/`; it drives the real
`createLoopBreaker` from the pinned engine against a copy whose `WINDOW` alone
is unbounded, with no model and no engine-repo change.

Two findings are kept, both deterministic:

- **The candidate's sparse-repeat regression.** In a sparse repair pattern —
  edit, read back, run the suite, do other work, repeat — the current setting
  admits all 9 read-backs and all 9 test runs with 0 blocks, while
  whole-attempt retention admits 5 and refuses 4 of each. The refusal is
  permanent: `callKey` is `[toolName, canonicalJson(input)]` with no workspace
  version, so a read after an edit is the same key, and a blocked call is never
  pushed to `admitted`, so its count cannot decay. Eviction was the only thing
  that ever removed it. Where the model retries a refusal, consecutive blocks
  reach `CONSECUTIVE_BLOCK_LIMIT` and terminate the turn — 4 terminations
  against 0 today — which could reinforce the restart cycling the change was
  meant to reduce. The reproducer demonstrates the additional termination
  decisions; how a model responds to them is untested.
- **The existing dense-repeat limitation.** At high density the current
  `WINDOW=20` already refuses legitimate repeated reads and test runs: 5
  admitted, 4 blocked, identically under both settings. This is a property of
  `THRESHOLD=5` over a 20-call window today, not something the candidate
  introduced. It is recorded because it bounds what any repeat-based lever can
  claim.

The intended effect was real — re-admissions fell from 12 to 5 on the traced
cycling sequence — but it is not separable from the regression by widening
alone.

**Not adopted as corrections.** Versioned keys deserve their own hypothesis: a
global mutation counter could let unrelated edits, or edit-and-revert cycling,
reset protection. A merely larger finite window is not demonstrated lower risk:
it can still block legitimate repeats for the remainder of a bounded attempt,
and eventual eviction does not guarantee timely recovery.

## Named: enlarge the post-edit region

**Question.** Does a larger post-edit region reduce follow-up reads of the
edited file enough to offset its additional tool-result and input tokens, while
preserving repair outcomes?

This is an **efficiency** hypothesis. It predicts no capability improvement.
Tool-result expansion primarily adds model input and context, not output
tokens; the accounting must reflect that rather than assuming output grows.

**The lever.** `src/satyrn_engine/mutation.py` returns a region around a
successful edit, bounded by `REGION_CONTEXT_LINES = 3`,
`REGION_MAX_LINES = 40`, and `REGION_MAX_BYTES = 4_000`. The pair is two
settings of that one engine revision.

**Prior status.** The v14a protocol tested E9's *corrective* half — telling the
model that a change had already been applied — and refuted it. The
*preventive* half, showing a larger region at edit-success time, is a distinct
mechanism its own record flags as untested. This candidate is that half.

## Offline preparation

No live spending is required for any of it.

1. Inspect the traced edits and identify what useful context today's region
   omits. Work from retained transcripts, not from assumption. The bar is a
   **concrete follow-up read whose needed content a larger region would have
   supplied** — that is the link between a larger response and fewer reads.
   Finding edits and reads in the same attempt does not establish it.
2. Choose one concrete larger setting, justified by what step 1 found.
3. Verify the region's content, its truncation behavior, and that responses
   stay bounded.
4. Freeze how follow-up reads and total usage will be counted before any
   comparison.

### Preparation findings

**1. What the region omits, with a concrete instance.** Verified in v14a
`cell-001-engine`: call 15 edits `templates/base.html` with `code=OK` and its
region returns **lines 1-5 only**. Call 19 re-reads the same file and returns
content past line 5 — the stylesheet links, `<title>`, `</head>`, `<body>`, and
the `<nav>` element — none of it reachable from the edit's region. At a context
radius covering the file, that content would have been supplied. This is the
link the candidate needs. Its limit: it shows the content was outside the
region and that the model re-read to obtain it; it does not prove the model
would otherwise have skipped the read.

Across 152 `OK` edits where the file length could be measured, the region's
median coverage is 24% of the file, and 138 of 152 (91%) show under half.
Truncation never fires anywhere in this evidence: `REGION_MAX_LINES` and
`REGION_MAX_BYTES` are not binding at this scale, so neither has evidence
pressure behind changing it.

**Read the co-occurrence rates with care.** Same-path re-reads follow 90 of 120
`OK` edits (75%) at depth-3 `R1`, but two v14a cells are the flip-flop cycling
the closed candidate documents — one toggles `app.py` nine times. Excluding
them the rate is 32 of 62 (52%). Those cells re-read because they are looping,
not because they lack context, so the region is unlikely to help them. The
honest opportunity estimate is the lower figure.

**2. The setting, and what it actually means.** `REGION_CONTEXT_LINES = 30`,
with `REGION_MAX_LINES` and `REGION_MAX_BYTES` unchanged. At this task's scale
that is not "a larger window" but **the whole file**: every observed file is at
most 40 lines (median 37), so a radius of 30 reaches both boundaries in 129 of
129 simulated edits. The pair is therefore a 5-line window against the entire
file. The number is derived from this toy application's file sizes and is not
evidence about larger files.

**3. Verification — content, truncation, bounded size.** Replayed against the
pinned engine's own `_post_edit_region`. At this task's scale the region is
correct and well inside both caps: a 25-line file with a single-line edit gives
lines 1-25, 258 bytes, no truncation, against 76 bytes at the current setting.

A defect appears above this scale, and it is a **correctness** defect rather
than a cost one. Truncation keeps the *first* `REGION_MAX_LINES`, so leading
context consumes the cap before reaching the change. On a 200-line file with a
20-line edit at line 100, the current setting returns lines 97-122 with the
whole edit visible; `REGION_CONTEXT_LINES = 30` returns lines 70-109, truncated,
with the edit's **tail cut off**. The larger region shows less of the change it
exists to display.

**This is not waived on the grounds that today's files are short.** No retained
file exceeds 40 lines, but a repair attempt can *enlarge* one past the cap, so
the defect is reachable inside this very condition rather than only beyond it.
A candidate that can hide part of a successful edit is not frozen until safe
truncation is resolved — by reserving budget for the changed span before
spending it on leading context, or by centring the retained window on the
change instead of the file start. The reproducer for it is kept, not
discharged.

**4. Counting rules, frozen.** A *follow-up read* is a `read` whose path is
byte-identical to a prior `code=OK` `edit`'s path, later in the same attempt,
counted once per edit at the next such read. Report the unrestricted count and
a distance-limited variant of five calls side by side. Another `edit` to the
same path is not a follow-up read and is tracked separately.

Usage follows `scripts/usage_totals.py`: terminal `message_end` only. The trade
is asymmetric and both sides are measured, never assumed. Region growth is paid
on **every** successful edit whether or not a re-read would have followed, and
lands in input and context. An avoided read is saved only when it would have
happened, and saves its own tool result plus the assistant turn that emitted
it. With a re-read rate between 5% and 89% across batches, the sign of the net
effect is not predictable from the mechanism.

### The R1 qualification gap, and the clarified condition

`qualification.json` covers `R3` only. `R1` is a different rung and its
qualification is not inherited. Assessing it fresh: witnesses verified
unchanged — `base` 3 of 4 public and 9 of 13 hidden passing, `known-good`
13 of 13, `partial-no-303` failing only `see-other-redirect` — and four of the
five behaviors are accessible under `R1`.

`timezone-aware-timestamp` is not. **The reason is narrow, and an earlier
version of this record got it wrong.** It is *not* that `R1`'s prompt omits the
words "timezone" or "timestamp": qualification never required a requirement's
keywords to appear in the prompt, and diagnosing from visible code and ordinary
Python knowledge is legitimate evidence. The actual defect is that the only
visible hint —
`{{ complaint.timestamp.strftime("%Y-%m-%d %H:%M UTC") }}` in
`base/templates/complaints.html` — is a hardcoded literal inside a format
string, which a **naive** datetime renders identically. The visible evidence
labels the display as UTC without uniquely requiring timezone-aware *storage*.

The response is a minimally clarified condition, `R1c`: `R1`'s text plus one
sentence resolving that requirement alone, without importing `R3`'s causes or
locations for the other defects. `R1` and its historical results stay
byte-identical; `R1c` is a **new condition and carries its own qualification**.

The retained `R1` re-read observations are the *motivation* for this candidate.
They are not evidence that `R1c` will produce the same trajectories, and no
part of this record should be read as predicting that.

### What a four-attempt screen can and cannot show

The pass floor does not erase behavior-level signal. Across the 24 retained
engine attempts the required behaviors move independently of the overall
verdict: the redirect behavior shows 19 passing checks against 1 failing, and
the mapped page and layout behavior 13 passing against 7 failing, with 4
attempts carrying no receipt. Behaviors worth protecting therefore remain
observable even where only one attempt passes everything.

What follows is a bound on the claim, not on the design. Four attempts can
**flag an observed regression** in a named behavior. They cannot establish
general outcome preservation — at `R1`, `R1c`, or `R3`. The comparison is
reported as total time and usage, with behavior-level regression checks and
explicit missingness for attempts without receipts.

**Condition.** The task and rung are chosen *after* establishing where this
mechanism actually occurs. The requirement to leave `R3` is not inherited from
the previous candidate: whether post-edit re-reads appear at `R3` is a question
about this mechanism and is answered from evidence, not assumed.

What the one retained `R3` attempt shows: its five reads all precede its three
edits — reads at positions 3 to 7, edits at 8 to 10 — so it contains **zero**
post-edit reads. That attempt therefore offers no demonstrated read-saving
opportunity for this candidate. It does not establish that the behavior cannot
occur at `R3`; it is one attempt, and its trajectory happened to be linear.
