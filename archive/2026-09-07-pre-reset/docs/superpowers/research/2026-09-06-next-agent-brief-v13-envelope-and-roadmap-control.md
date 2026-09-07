> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# Next-agent brief: Envelope is `read,edit`, then V13, then the roadmap under control

**Date:** 2026-09-06. **Status:** handoff. Nothing in §4–§7 has been
started. The decision in §2 was made by the maintainer in conversation
and is recorded here first.

**Read `BRIEF.md`, `ROADMAP.md`, and this whole file before touching
anything.** Every number below carries the command that recomputes it,
per `BRIEF.md` rule 1. Where this brief says "verified" it means a
command was run and its output read; where it says "not checked" it
means exactly that.

---

## 1. Where everything is

```
HEAD                 5b1d230  Bring BACKLOG back under cap; verify the gates properly
tree                 clean
uv run pytest -q     exit 0   (505 passed, 284 deselected)   ← read the exit code, not the tail
uv run ruff check    exit 0
ROADMAP.md           398 lines   (cap 400 — two lines from a red gate)
BACKLOG.md           395 lines   (cap 400)
```

**Evidence on disk, all tallies accepted, 216 cells since the last
defect-driven void:**

| batch | cells | what |
|---|---|---|
| `~/satyrn-smokes/2026-09-05-v11c-miniprobe-2` | 12 | Baseline mini-probe |
| `~/satyrn-smokes/2026-09-05-v11c-spike-184017` | 24 | Engine 10/12 vs Baseline 5/12 |
| `~/satyrn-smokes/2026-09-05-compaction-probe-214218` | 6 | compaction rescues no locked loop |
| `~/satyrn-smokes/2026-09-06-overnight-232554` | 126 | R1/R3 profile, both capability points (120 + one 6-cell calibration duplicate) |
| `~/satyrn-smokes/2026-09-06-r0-profile-081459` | 48 | R0 profile, four tasks |

Recount: `for d in <each>; do find "$d" -name attempt.json | wc -l; done`.
The 5-cell `2026-09-06-r1b-headtohead-085246` is **abandoned**, not a
result, and is not in that sum (`ABANDONED.md` there).

**V13's preregistration is committed and frozen except §7:**
`docs/superpowers/specs/2026-09-06-v13-preregistration.md`. Primary cell
`agentclinic-repair-depth-2`, R1, `gemma-4-12B-it-MLX-8bit` (3/6, 4/6
patches). Its status line still reads *draft, awaiting confirmation* —
the maintainer's confirmation must be recorded on it before the first
non-reference cell runs. §7 is Envelope, decided below.

**A hazard that is live at handoff.** Two sessions were editing this one
checkout during the review that produced this brief — `HEAD` moved
twice under it and `BACKLOG.md` was dirty between commits. Preflight
refuses a dirty tree, so V13 cannot start from a checkout anyone is
editing. **Before §5: one session per checkout.** Do the document work
of §4 and §6 in a worktree (`git worktree add`, never a `cp` loop), land
it, and run V13 from a clean `main`.

---

## 2. The decision: Envelope is bare pi on Engine's tool surface

**Envelope = `satyrn-evals-attempt-pi` with tools `read,edit`**, every
other setting identical to Baseline (`arms/baseline.json`), no engine
code, no budget cap.

Why this and not "Baseline plus a stall cap":

- A stall cap can only terminate cells early, so it can never record
  *more* successful attempts than Baseline — a pointless outcome arm —
  and it converges mechanistically with Engine's loop breaker, which
  weakens the three-way contrast V13 exists for (prereg §7 says this).
- The canonical product Envelope **was** a restricted tool surface, not
  a budget: "the canonical product Envelope, which used only
  `read,write`"
  (`docs/superpowers/research/2026-08-27-local-pings-envelope-engine-followup.md:24-27`).
  Engine exposes `read,edit` (`arms/engine.json`, `"tools"`). Putting
  bare pi on exactly that surface gives three whole-product arms —
  Baseline's four tools, Engine's two tools without Engine, Engine — and
  an Envelope that *can* out-score Baseline.
- It needs no argument from the 1,546-token floor, no engine edit (the
  engine stays byte-identical at `25ca0be`, which V13's own preflight
  requires), and no new mechanism.

**This is a prospective arm, not a reproduction** — `write` versus
`edit` differs from the historical surface, and the era's pi, prompt and
adapter are unrecoverable (`BACKLOG.md`, "Historical Envelope artifact
recovery"). Say so in prereg §7 and §4.

**Consequential amendments, recorded not edited away:**

- `ROADMAP.md:140-142` freezes "the rule mapping reference-arm budget
  evidence to Envelope's cap" and `ROADMAP.md:170-174` says the cap
  "must be argued from a per-cell floor." Envelope is now a tool
  surface, so there is no cap and no budget rule. Amend both passages
  with a dated note pointing here; keep the old sentence visible.
- `BACKLOG.md`'s entry "Envelope's definition is owed to `satyrn-engine`"
  is resolved by this decision. Prune it (backlog rule 3); the
  loop-breaker entry beside it stays — it is a separate engine-side item.
- `BACKLOG.md`'s "Where pi's ~9,000 unexplained repo-root tokens come
  from" reopened "when the Envelope cap is argued." It no longer reopens
  on V13. Leave it, change its reopen condition.

---

## 3. Check the adapter honors it — before anything else in §5

**Not checked in this review** (the grep was interrupted). It is the
one thing that could turn the Envelope decision into engineering.

1. Find where an arm file's `"tools"` list reaches pi's argv. Start at
   `src/satyrn_evals/attempt_pi.py` and `scripts/preflight.sh` (check 0c
   reads the arm's `inference` block; does anything read `tools`?).
   `arms/baseline.json` lists `["read","bash","edit","write"]` — is that
   *passed*, or merely *recorded*?
2. If pi is given the arm's tools (a `--tools`-style flag or equivalent
   in the adapter's argv), write `arms/envelope.json` as a copy of
   `arms/baseline.json` with `"arm": "envelope"` and
   `"tools": ["read","edit"]`, and confirm `scripts/preflight.sh`
   accepts a third arm name and `scripts/tally.py` / `scripts/interleave.py`
   schedule three arms.
3. If the list is only recorded, the adapter needs to pass it. That is a
   small change to the argv builder with a **refusal sibling** (an arm
   naming a tool pi does not have is refused before any cell) and a
   **success sibling** (the four-tool Baseline argv is byte-identical to
   today's — `BRIEF.md` rule 6). Do not weaken the planted-spawn
   tripwire to test it.
4. Either way the Envelope path is a **materially new execution path**
   and owes one uncounted V5d smoke cell before the first budgeted cell
   (`docs/superpowers/specs/2026-09-03-v5d-preflight-smoke-check-design.md`).
   Read its attempt record and its transcript: the point of the smoke
   is to see, in `tool_execution_*` events, that `bash` and `write` are
   absent and `edit` is present — positive evidence the restriction
   held, not the absence of an error.

---

## 4. Cleanup first — three open items, none blocking the run

All three are document edits; do them in the worktree and land them in
one commit before V13 so the run pins a tree whose records are right.

1. **Three backlog entries lost their titles.** `BACKLOG.md:365`, `:378`,
   `:387` open with a bare `** (decided`, `** (found 2026-09-06 by the`,
   `** (owed 2026-09-05, when`. Recovered from history (verified with
   `git show <commit>:BACKLOG.md | grep`):

   | now reads | original title | added | dropped |
   |---|---|---|---|
   | `** (decided` | **R2, R3 and the two framing tasks are out of placement** | `669b2fb` | `d08a872` |
   | `** (found 2026-09-06 by the` | **R3 carries almost no placement information** | `a4d15e9` | `669b2fb` |
   | `** (owed 2026-09-05, when` | **Re-validate the repeated-call limit per model** | `f1d5fe5` | later |

   Restore the first two verbatim. **Prune the third** instead: the
   overnight result already retired it — "That retires the per-model
   re-validation the backlog owed"
   (`~/satyrn-smokes/2026-09-06-overnight-232554/RESULT.md:58-69`) — and
   backlog rule 3 says a resolved entry is deleted once a record carries
   the outcome. Point the V12 row at that RESULT line when you prune.

   **The pattern is the finding.** Each title vanished in a *different*
   consecutive commit, which means an editing step is stripping
   `**Title**` down to `**` when it touches the line after it. Before
   committing any `BACKLOG.md` change, run
   `git diff BACKLOG.md | grep -n '^[-+]\*\* ('` and expect no output.
2. **`ROADMAP.md` contradicts itself** — the exact drift `CLAUDE.md`'s
   "one current status record" rule names:
   - line 147 "V12 keeps all four rungs, including R2" vs row 77 (R2
     unauthored, R3 dropped);
   - line 152 "the 288 cells need a resume-safe driver" vs 168 cells run
     in staged batches of ≤60 with no driver;
   - row 77 "**queued after V11b**" while the profile has run; row 78
     "**queued after V10 and V12**" while the prereg is committed.
   Fix the opening paragraph and the table **in the same edit**. §6
   below is where this edit happens, because the file is two lines from
   its cap and the fix adds lines.
3. **Prereg §3 says "Seven of 29 profiled cells."** It is 28 distinct
   cells plus the Part B/Part C duplicate at `misleading-locus` 26B R1
   (both 6/6). The recompute at §3:60 globs both `tally.json`s. Selection
   is unaffected; the sentence should say "28 distinct (29 tallies; one
   calibration duplicate, both at ceiling)."

---

## 5. Run V13

In this order, from a clean `main` that nobody else is editing:

1. §3 done; `arms/envelope.json` exists; the Envelope smoke cell is on
   disk with a unique name under `~/satyrn-smokes/`.
2. Prereg §7 filled with §2 of this brief; §4's table names the arm
   file; the status line records the maintainer's confirmation and its
   date. Commit — the freeze is "written before any non-reference arm
   runs," and the commit is the timestamp.
3. Quiet the machine (the voided mini-probe was a GPU OOM; `MODEL_ERROR`
   classifies one after the fact, it does not prevent one).
4. Preflight into a fresh output directory. Check 0c must see three
   arms with identical `inference` blocks.
5. `n=12` per arm, 36 cells, interleaved on a seed recorded before the
   first cell; `--max-repeated-calls 10` on for every arm (prereg §5).
   Expect roughly 30–50 s per Baseline cell — the R0 profile ran 48
   cells in 24 min, Part A 60 in 53 min — so under an hour is
   plausible; Engine cell durations were not measured for this brief.
6. `scripts/tally.py` must accept the set or there is no result.
7. `RESULT.md` beside the cells with the recompute command, then the
   four publishability conditions from `CLAUDE.md` before any count
   leaves the runs directory: (a) strict tally accepts; (b) model
   identity from each transcript's `message.model` — `tally.py:155-227`
   does this; (c) every open finding classified verdict-counts vs
   diagnostic-only, none touching verdict counts; (d) every inference
   setting in the arm record, checked by preflight.
8. A null is recorded as prominently as a positive. `n` and the cell do
   not change afterwards.

---

## 6. Get `ROADMAP.md` under control: `ARCHIVE.md`

**Neither `ARCHIVE.md` nor `docs/superpowers/phase-history.md` exists**
(`ls` both — verified). `ROADMAP.md:207` promises the latter;
`docs/sdd.md:20-22` says completed phases "move to the archive section
of `ROADMAP.md`." That section — "Prior work," lines 205–390 — is 186 of
the file's 398 lines, and it is why the file cannot absorb a status fix.

Do this:

1. **Create `ARCHIVE.md` at the repository root.** Move "Prior work"
   there **verbatim** — it is a record, and a record is moved, not
   rewritten. Add a two-line header: what the file is (completed phases
   and superseded framings, in reverse order), and that it is
   append-only and deliberately uncapped. Leave a three-line "Prior
   work" stub in `ROADMAP.md` pointing at it, matching the existing
   Backlog stub at `ROADMAP.md:200-203`.
2. **Every link into "Prior work" must still resolve.** `BACKLOG.md`,
   `BRIEF.md`, the specs, and `ROADMAP.md`'s own table say "see Prior
   work below" in several rows (V5c, V7, V8, V5a/V5b, and the "Complete,
   and recorded in Prior work below" sentence at line 51). Grep for
   `Prior work` and repoint each. `just lint-docs` and `just docs` are
   the gates.
3. **Register the file in the operating documents:**
   - `docs/sdd.md:20-22` — "the archive section of `ROADMAP.md`" becomes
     `ARCHIVE.md`.
   - `docs/sdd.md` cap table (lines 52–61): add a row for `ARCHIVE.md`,
     **uncapped, deliberately** — the roadmap cap exists so the planning
     surface stays readable; the archive is where the overflow is
     supposed to go, and capping it would only create a third file. Say
     that in the row, the way the Excludes column already explains its
     own exemption.
   - `tests/test_doc_caps.py` / `tools/lint_docs.py` — a test that
     `ARCHIVE.md` is *not* capped, as the Excludes column has
     (`test_a_long_excludes_cell_is_not_capped`), so a later "tidy" does
     not silently cap it.
   - `ROADMAP.md:3-6` header and `README.md` if it lists the planning
     files: one line each naming `ARCHIVE.md`.
   - `CLAUDE.md` says read `BRIEF.md` and `ROADMAP.md` in full every
     session. **Do not add `ARCHIVE.md` to that list** — the point of the
     move is that a session need not hold the history to work.
4. **Then, and only then, the status fix from §4.2** — with the room the
   move created, restate the "Now" paragraph in one short block and
   bring rows 77 and 78 current: V12's profile is run and staged, its
   remaining entry gates are closed by evidence (§7 below) rather than
   by code; V13 is confirmed and pending Envelope's smoke.
5. Remove the dead pointer to `docs/superpowers/phase-history.md` at
   `ROADMAP.md:207`.

`BACKLOG.md` exists and is within cap; it needs no structural change.
Its rule 3 already says entries are pruned, not archived in place — so
**nothing from `BACKLOG.md` moves to `ARCHIVE.md`**; resolved entries
are deleted once a phase row or research doc records the outcome.

`docs/sdd.md` is 719 lines, most of it per-phase verification records.
It has no cap and this brief does not propose one; if it ever gets one,
those records are the obvious `ARCHIVE.md` candidates.

---

## 7. Over-engineered, or done by evidence — do not build

- **Slice 3, the resume-safe driver** (`docs/superpowers/plans/2026-09-05-v11d-instrument-fixes-and-v12-entry.md:102-119`).
  Staging in ≤60-cell batches made it moot: 168 cells landed with no
  interruption loss. Mark the slice withdrawn in the plan with the
  reason; delete `ROADMAP.md:152`'s "288 cells need a resume-safe driver."
- **Slice 5's remaining entry gates** are closed by evidence, not code:
  the observed-`message.model` check exists (`scripts/tally.py:155-227`);
  the well-formed-tool-call canary is answered by 216 cells of
  well-formed tool calls at both capability points; creation-capable
  capture is needed only if `framing-2` enters placement, and it is
  excluded by a recorded gate. Record that in the V12 row; build nothing.
- **`--max-calls-without-edit`** (`BACKLOG.md`, "The repeated-call rule
  catches repetition, not stalling"). Well-argued and a change to a
  frozen stopping rule. Not before V13 reads out.
- **R1b.** Abandoned, correctly; it answers a contract-design question
  V13 does not need. Leave the four manifests' R1b text alone.
- **`test_real_e5_*`** (`BACKLOG.md`, "fail against the pinned engine")
  — the Engine arm ran 12/12 spike cells and 12 more are about to run,
  so the real-engine attempt path is proven by evidence. These are stale
  integration tests, not a V12 gate; fix or retire them after V13.
- **W1, V14, V15.** After.
- **Anything in `satyrn-engine`.** It is pinned at `25ca0be` and must
  stay byte-identical until the pin moves. Both engine-side backlog
  entries say so.

## 8. What not to trust — and what to do about each

- **"Cells at ~20 s."** Measured: 30 s (R0 profile) and 53 s (Part A).
  Use the measured figures when estimating; never compare wall-clock
  across arms (`BRIEF.md:39-40`).
- **"29 profiled cells."** 28 + one duplicate; §4.3 fixes the wording.
- **The suite is two tasks wide.** `plausible-wrong-fix` is 6/6 and
  `depth-3` is 0/6 at every rung and point; `framing-2` is excluded;
  `framing-2-edit` is 5/6 everywhere. All headroom sits at R1 on
  `depth-2` and `misleading-locus`. V13's result rests on one cell of
  one task at `n=12`, by design — say so in `RESULT.md` and in the
  roadmap sentence that reports it.
- **Gates run through `tail`.** Both sessions on 2026-09-06 checked a
  gate's status by reading `tail`'s exit code — a check that could not
  fail, which is this project's named instrument defect. §9.1 makes it
  structural rather than a habit.
- **`--max-repeated-calls 10` fires asymmetrically** — the prereg says
  so and the evidence that it cannot move the primary metric is strong
  (no patch-producing cell exceeds an identical run of 2 across 231
  cells). Trust the disclosure; do not re-argue it after the counts.
- **Prereg "frozen" but "awaiting confirmation."** Until the maintainer's
  confirmation is on the document, it is a draft. Get it recorded before
  the smoke cell, not after.

## 9. Low-hanging fruit

1. **A `just gates` recipe** that runs `uv run pytest -q`, `uv run ruff
   check`, `just lint-docs`, `just docs` and fails on the first non-zero
   exit — no `| tail`, no `&&` chain typed by hand. Then `CLAUDE.md`'s
   "full gates at integration" sentence names the recipe. Ten lines;
   closes the defect in §8 for good.
2. **`python -m satyrn_evals.cli` silently no-ops** (`BACKLOG.md`,
   "silently no-ops"): a two-line `__main__` guard plus the tripwire the
   entry already specifies. It once cost a confused capture run.
3. **Per-cell duration in the tally.** `attempt.json` has no duration
   field this brief could find (a probe over the R0 profile read none of
   `duration_s`/`elapsed_s`/`wall_seconds`). Counts only, per `BRIEF.md`
   — but a *per-cell* duration in the record, never summarised across
   arms, would have answered "how long is 36 cells" without guessing.
   Only if it is already in the transcript timestamps; do not add a
   clock to the attempt path for it.
4. **Remove the stale `docs/superpowers/phase-history.md` pointer** —
   folded into §6.5.

## 10. After V13: W1, then the headroom proposal — not V14

Nothing past V13 is ready to plan, and the evidence says which
conditions are met.

### W1 — Weight, moved up

"Independent after V9" (`ROADMAP.md:79`) and untouched since. Run it
directly after V13 reads out. The numbers that make it due:

```
find src -name '*.py' -not -path '*/tasks/*' | xargs wc -l | tail -1   # 9,015
find scripts arms -type f | xargs wc -l | tail -1                       # 1,893
find tests -name '*.py' | xargs wc -l | tail -1                         # 22,092
```

against `BRIEF.md:27-29`, which names a 6,065-line harness measuring a
340-line engine as *the trap*. Not there yet; trending there, and the
weight check has never been run. W1 is also where §7's items are
**removed**, not merely left unbuilt: the resume-driver slice, the
stale `test_real_e5_*`, and any code path whose only caller was a gate
now closed by evidence. Its own row says what it keeps — the 100%
branch gate, with the coverage reduction recorded.

### The headroom proposal — design work owed, not a phase

`BRIEF.md:150-156` and `ROADMAP.md:182` call this out; the profile has
now measured it. Four of six tasks carry no information at any rung or
point; every middle-band value sits at R1 on `depth-2` and
`misleading-locus`. Write the proposal **with V13's counts in hand** —
that is not a peek, it is the V11c consequence table doing its job
(`ROADMAP.md:128-133`): a positive keeps the pure-edit path; a null
makes the Engine test runner the next prerequisite.

Two candidate answers, in cost order. The proposal chooses, it does not
pre-choose:

1. **More repair tasks at R1 on the same app.** No engine change, no
   creation-capable capture, the same oracle shape as the two tasks that
   discriminate. Cheapest by far.
2. **V14, build rungs.** Half its condition is met (headroom is needed)
   and half is blocked: Engine exposes only `read,edit` — no test
   runner, no file creation — and is pinned until V13 ends; evals-side,
   creation-capable capture is owed (`framing-2` is excluded for exactly
   that). V14 cannot start before the pin moves.

### V15's condition is written on a refuted premise

Its trigger — "every AgentClinic rung, including build, ceilings for
the 26B-A4B point" (`ROADMAP.md:81`) — assumes the 26B is the point that
exhausts the suite first. The profile refuted the ordering: the 26B is
*worse* on `depth-2` R1 (1/6 vs 3/6), and `ROADMAP.md:153-156` now
forbids "larger model" language. Nothing in V13, W1 or the headroom
proposal tests that trigger, because nothing runs a build rung. The
headroom proposal should **rewrite the row**, keyed to tasks rather
than a model: *reopens when no task on the current app places any
compared pair in different bands* — the admission rule's own question,
and one the next steps actually answer. Record the old wording beside
it.

## 11. Order of work, and the acceptance for each

| step | done when |
|---|---|
| §1 one session per checkout | `git status` clean on `main`; document work in a named worktree |
| §3 adapter check | either the argv already carries `tools`, cited by `file:line`, or the change lands with its refusal/success siblings |
| §4 cleanup + §6 archive | `ROADMAP.md` well under 400 with one consistent status; `ARCHIVE.md` holds "Prior work" verbatim; every `Prior work` link resolves; `just lint-docs`, `just docs`, `uv run pytest -q` all exit 0 — **read the exit codes** |
| §2 prereg §7 + confirmation | committed, status line dated and confirmed |
| §3.4 Envelope smoke | one uncounted cell on disk whose transcript shows `edit` and no `bash`/`write` |
| §5 V13 | 36 cells, tally accepted, `RESULT.md` with recompute, (a)–(d) checked, roadmap rows 77–78 and "Now" updated in one edit |
| §7 withdrawals | plan slice 3 marked withdrawn; V12 row records gates closed by evidence |
| §9.1 `just gates` | the recipe exists and `CLAUDE.md` names it |
| §10 W1 | its own row's done-when; the three line counts above re-run and recorded beside the before figures |
| §10 headroom proposal | a confirmed design proposal per `CLAUDE.md`, written after V13's `RESULT.md`, choosing between the two candidates and rewriting V15's row |

Commits are the maintainer's (`CLAUDE.md`). Leave the worktree
reviewable at each step; ask before committing.
