# Engine budget — what `/implement` spends that bare Pi does not

**UNCONFIRMED.** Every number here was read from cells produced under the
retired two-uid isolation harness (`records/2026-09-21-comparison-*`, engine
`78ab87d`, M1 Pro), which ledger entry C0 marks unconfirmed. Nothing is built
on these numbers; they are hypotheses for EB1 to re-count on confinement
cells (`docs/superpowers/specs/2026-10-02-engine-budget-design.md`).

Read 2026-09-23 to 2026-10-02: one Opus 5.5 session (the attribution,
the pytest experiment, the small-request rule), then three independent Opus
reports commissioned by Fable on 2026-10-02 — a harness read of evals `main`
`1432bff`, a cost-surface audit of engine `main` `f9436aa` against Pi 0.85.1,
and a second attribution that did not see the first and reproduced its
medians exactly. Recompute the cell tables with:

```
uv run python evidence/2026-10-02-engine-budget/cells.py ~/satyrn-runs/2026-09-21-comparison-*
```

Rules followed: tool calls counted from `tool_execution_start`, one per call;
medians with ranges; denominators and missingness stated; nothing pooled
across tasks or arms; context for a turn is `usage.input + usage.cacheRead`.

## 1. Per task × arm, delivered passes only

| task | arm | n | pass | output tokens | turns | tool calls | peak context | span (min) |
|---|---|---|---|---|---|---|---|---|
| depth-3 | B | 6 | 6 | 5,682 (4,085–21,827) | 13 (9–18) | 14 (12–18) | 10,765 (9,053–28,383) | 3.4 (3.1–15.0) |
| | E | 6 | 6 | 8,066 (3,222–15,114) | 16.5 (9–28) | 23 (17–37) | 14,133 (8,915–22,923) | 5.1 (2.2–10.2) |
| guard-prefixes | B | 6 | 4 | 8,042 (5,707–17,330) | 14 (7–40) | 13 (6–39) | 13,362 (9,093–23,278) | 4.8 (3.0–12.9) |
| | E | 6 | 4 | 18,740 (11,004–20,190) | 23.5 (16–28) | 26 (16–29) | 27,203 (18,111–28,966) | 15.1 (9.9–18.3) |
| review-script | B | 6 | 2 | 6,682 (4,808–8,555) | 23.5 (19–28) | 22.5 (18–27) | 15,138 (10,824–19,451) | 5.3 (3.5–7.1) |
| | E | 6 | 5 | 10,737 (6,547–14,410) | 17 (12–26) | 19 (11–32) | 24,821 (15,389–33,957) | 10.8 (6.3–15.8) |
| docs-linter | B | 12 | 7 | 31,865 (24,620–47,683) | 38 (26–60) | 37 (25–59) | 46,059 (35,621–55,948) | 25.2 (18.0–33.6) |
| | E | 12 | 8 | 32,599 (30,425–39,816) | 28 (14–43) | 28 (20–44) | 49,672 (40,785–72,271) | 30.3 (25.1–39.1) |
| run-record-gate A | B | 12 | 2 | 30,712 (26,596–34,827) | 51 (39–63) | 61.5 (45–78) | 60,991 (54,105–67,876) | 30.2 (25.6–34.8) |
| | E | 12 | 8 | 33,398 (24,684–46,541) | 43.5 (25–59) | 45.5 (26–60) | 72,480 (53,821–85,669) | 38.1 (25.8–56.9) |
| run-record-gate B | B | 12 | 0 | — | — | — | — | — |
| | E | 12 | 8 | 32,725 (26,431–42,927) | 40.5 (30–68) | 42 (29–67) | 66,580 (54,915–82,605) | 35.3 (23.4–50.8) |

Excluded: guard B 2 fail; guard E 2 `BUDGET_EXCEEDED` (no receipt or patch);
review B 2 fail, 1 `unavailable`, 1 `BUDGET_EXCEEDED`; review E 1 fail. No
length-cut turn in any floor cell. Review B is 2 survivors of 6: a selected
sample. Model time per 1,000 output tokens is the same on both arms (about
42 s on depth-3 and guard, 44 s on review), so extra minutes are extra output
plus tool time.

**Pairwise:** guard Engine higher in 15 of 16 cross-arm pairs; depth-3 Engine
higher in 21 of 36 — no robust difference, the median gap is outliers on both
sides (one Engine cell spent ~5k grepping site-packages; one Baseline cell
spent 14.8k in two thinking turns).

## 2. Where the floor gap goes (output tokens, median over delivered passes)

Each assistant turn in one category, first match wins: final (no tool call);
post (after `finish_nudged`); rej (every call rejected); pre (at or before
the first landed edit); src (edit to a non-test file); testfile (write or
edit under `tests/`); testrun (bash with pytest, or `self_test`); probe.

| | depth-3 B | depth-3 E | guard B | guard E | review B | review E |
|---|---|---|---|---|---|---|
| pre | 4,429 | 4,285 | 2,777 | 5,912 | 2,660 | 5,978 |
| rej | 0 | 1,296 | 0 | 506 | 302 | 0 |
| src | 240 | 136 | 1,534 | 908 | 174 | 0 |
| testfile | 0 | 0 | 0 | 1,450 | 1,280 | 1,047 |
| testrun | 100 | 119 | 0 | 400 | 344 | 919 |
| probe | 485 | 0 | 2,630 | 3,322 | 1,438 | 750 |
| post | 0 | 0 | 0 | 0 | 0 | 0 |
| final | 392 | 560 | 441 | 488 | 484 | 825 |
| **total Δ** | | **+2,384** | | **+10,698** | | **+4,056** |

Category medians are over different cells and do not sum to the total.

- **Guard-prefixes.** Only the Engine prompt adds `tests/test_guard.py (new
  file)` and "Tests carried from the accepted base … 97 files". All four
  Engine passes reason about that file, survey `tests/` (9.5 calls before the
  first edit against 1; 4.5 of them touching `tests/` against 0; 10.6 KB read
  against 4.1 KB), land the first edit at turn 6–10 against turn 2, and write
  the file (4 of 4 against 0 of 4, ~1,450 tokens). Rejected edits 1.5 per
  pass. No scope refusal, runaway or loop-breaker fired. The steer's own
  cost: the final turn, 488 against 441.
- **Depth-3.** Schema-rejected edits in 6 of 6 Engine cells, 0 of 6 Baseline
  (4 rejected calls per pass, 2.5 of them schema); the 1,296 is an upper
  bound since those turns also carry the edit plan. Baseline hand-checks
  after editing (485); the Engine runs `self_test` and stops.
- **Review-script.** More reading before the first edit (33.8 KB against
  17.5 KB), three automatic self-tests per pass, a longer final turn.
  Baseline spends ~1.4k on commit, PROVENANCE and AGENTS.md chores that the
  Engine skips after the steer.
- **After the steer,** 14 of 15 Engine floor passes stop at once.

## 3. `edit` rejections across all 108 cells

| | calls failing Pi's schema validation | cells affected |
|---|---|---|
| Baseline | 3 | 3 of 54 |
| Engine | 95 | 40 of 54 |

Shapes of the 95: per-item `path`, one file, no top-level `path` — 67;
nested `{path, edits:[…]}`, one file — 15; multi-file — 3; top-level `path`
present with another fault (e.g. `edits` as a string) — 4; other — 6. The
first two (82) are unambiguous. Retry turns per cell: depth-3 1.5 (659
tokens), guard 2.3 (2,021), review 0.7 (422), docs-linter 1.0 (923),
run-record-gate 1.5–2.2 (1,415–1,572). Beyond schema failures the Engine
also refuses `ANCHOR_MISSING` on exact-byte anchors (10–14 per medium
record) where Pi falls back to a fuzzy match, and `REVISION_STALE`,
`NO_CHANGE_REQUESTED`, `ANCHOR_ALREADY_APPLIED`.

**Why (engine `main` `f9436aa`; `mutator.ts` unchanged since `78ab87d`).**
Pi 0.85.1's native `edit` (`dist/core/tools/edit.js:11-92`) has parameter
descriptions on `path`, `edits`, `oldText`, `newText`; four
`promptGuidelines`; an open schema at both levels; and `prepareArguments`
that parses `edits` sent as a string, wraps a bare edit object, and folds
legacy top-level `oldText`/`newText`. The Engine's override
(`packages/engine/mutator.ts:127-159, 396-407`) has none of these: no
descriptions, no guidelines, `additionalProperties:false` at both levels
(item `path` tolerated but must equal the top-level), no normalizer, and
`parseEditInput` runs after Pi's validation. Nine shapes Pi accepts, the
Engine refuses; none the other way. Net per-request prompt plus tool
definitions: the Engine is **−125 tokens** — the saving is the missing
instructions.

## 4. The automatic self-test

Triggered when a bash result carries a pytest count and duration and no
Engine self-test has run since the last landed edit (`runner.ts:252-264,
477-491`). Per record, Engine arm:

| record | triggered runs | model's own run was targeted | Engine run red / green | Engine suite s per cell | red runs whose failures were all in files the model had just run |
|---|---|---|---|---|---|
| run-record-gate A | 32 | 32 | 22 / 10 | 78 | 22 of 22 |
| run-record-gate B | 32 | 32 | 20 / 12 | 75 | 20 of 20 |
| docs-linter | 37 | 37 | 26 / 11 | 101 | 26 of 26 |
| review-script | 16 | 16 | 10 / 6 | 88 | 10 of 10 |
| guard-prefixes | 12 | 12 | 9 / 3 | 35 | 9 of 9 |
| depth-3 | 1 | 0 (full) | 0 / 1 | ~0 | — |

Suite time read from pytest's own `in N s` plus ~1.5 s for `uv` start. A
run reporting "35 passed in 0.02s" took 66 s wall clock. Each note is ~4.3
KB (2.1–9.9; n = 130). The runner (`runner.py:262-280`) runs the declared
command, then declared + `preserve`, then declared + `checks`; `derive`
(`derive.py:332-334`) puts every tracked `tests/test_*.py` in `preserve`, so
the suite is suspected to run twice per self-test. **To verify on EB0 cells
before counting.** `VIRTUAL_ENV` is removed for the Pi process
(`attempt.py:1350-1366`) but `uv run --project <engine>` re-exports it to the
protocol process and nothing strips it on the test path or in `deliver`'s
validation (`delivery.py:1746-1756`); hence the warning in every note.

## 5. Context

| median | depth-3 B | depth-3 E | guard B | guard E | review B | review E |
|---|---|---|---|---|---|---|
| first prompt (bytes) | 680 | 1,396 | 788 | 1,385 | 1,391 | 1,993 |
| first-turn context | 1,702 | 1,869 | 1,811 | 1,945 | 1,938 | 2,078 |
| Σ earlier outputs | 5,261 | 7,316 | 7,728 | 18,252 | 6,198 | 10,132 |
| tool results and injected text | 3,802 | 4,948 | 3,824 | 6,643 | 7,002 | 14,265 |
| ↳ edit-result echo | 48 | 713 | 71 | 917 | 65 | 334 |
| ↳ Engine notes and steer | 0 | ~200 | 0 | ~1,510 | 0 | ~3,040 |
| Engine-injected bytes per cell | 0 | 708 (708–5,724) | 0 | 5,573 (708–18,325) | 0 | 11,451 (8,119–14,919) |

The peak is the last turn in every pass; the model's own output stays in
context. The Engine's `edit` returns the post-edit region, numbered, 3 lines
of context, capped at 40 lines / 4,000 B (`mutator.ts:296-307`), where Pi
returns "Successfully replaced N block(s)" (~57 B).

## 6. pytest output: no flag removes the progress dots

Full suite of this repository, two deliberately failing tests, ~34 s each.
"Parser needs" are what `runner.py:143-194` reads: `FAILED` lines, `___ name
___` headers, `E` lines.

| variant | bytes | dot chars | FAILED | headers | `E` lines | uv warning |
|---|---|---|---|---|---|---|
| `-q` (current) | 4,819 | 2,842 | 2 | 2 | 13 | yes |
| `-qq` | 4,771 | 2,842 | 2 | 2 | 13 | yes |
| `-q --tb=short` | 4,670 | 2,842 | 2 | 2 | 13 | yes |
| `-q --tb=line` | 4,683 | 2,842 | 2 | **0** | **2** | yes |
| `-q -o console_output_style=count` | 5,059 | 2,842 | 2 | 2 | 13 | yes |
| `-q -o console_output_style=classic --tb=short` | 4,313 | 2,842 | 2 | 2 | 13 | yes |
| `-q`, `VIRTUAL_ENV` unset | 4,648 | 2,842 | 2 | 2 | 13 | **no** |
| `-q` + drop lines matching `^[.sFExX]+\s+\[\s*\d+%\]$` | **1,447** | **0** | 2 | 2 | 13 | no |

The compactor already drops dots on red runs (it keeps only `FAILED`/`E`
lines); green runs keep the last 20 lines verbatim, dots included.

## 7. A small-request rule

On the prompts each comparison ran at, "creates no file and declares at
most one `Produces:` symbol" is true of depth-3 (no `Files:` block) and
guard-prefixes (modify only, 1 symbol) and false of every medium build
(run-record-gate 2 files/5 symbols, docs-linter 1/2, preflight-quiet 1/9,
review-script 1/7). Fitted to eight tasks with three on the small side;
"creates a file" does most of the work.

## 8. Harness notes found on the way (evals `main` `1432bff`)

- The harness sets `SATYRN_CONFINEMENT_ROOT` to the eval worktree; the
  Engine's Pi runs in `$TMPDIR/satyrn-engine-*/worktree` and inherits it.
  `inside()` resolves relative paths against the root, so `edit app.py`
  passes; an absolute path inside the Engine worktree is refused, logged
  `confinement_refused`, and the cell is never admitted. No integration test
  covers the extension inside an Engine spawn.
- The Engine arms pin `1869397`; the sibling checkout sat at `f9436aa` and
  would have been refused by name. Fixed 2026-10-02 by `git checkout --detach
  1869397`; `engine_checkout_problems` now returns `[]`.
- No harness field holds context size or wall clock (`budget.py:9-12`:
  "cacheRead and input tokens are not budget"). Both are computable from
  `transcript.txt` and `timeline.jsonl`, which every cell retains.
- Floor parity has no operational definition: the release-two floor records
  say "the Engine costs no more … no test, n = 6 per arm".
- `_test_for` (`derive.py:132-134`) matches only `test_<stem>.py`; in a real
  repository it misses `test_hook_guard.py` and proposes a second file. Not
  measurable in the eval (that test is hidden).

## 8a. EB0 smoke, 2026-10-02 (confinement harness, engine `1869397`, M5 Max)

`records/2026-10-02-eb0-smoke-agentclinic-repair-depth-3.json`: one Engine
cell on depth-3, `confinement: extension`. **Pass, admitted**: 0
`confinement_refused`, 0 reaches; 4,877 output tokens, 8 turns, 15 tool
calls, peak context 10,242, 2.1 min; one finish steer, stop on the next
turn; 0 rejected edits. All seven file-tool calls used relative paths
(`app.py`, `models.py`, `templates/*.html`, `tests/test_app.py`), so the
root check in §8 passed them; the absolute-path case stays untested. The
engine receipt's `validation_output` holds two identical suite runs ("4
passed … in 0.41s", then "in 0.40s") and the `VIRTUAL_ENV … will be
ignored` warning: the double run in §4 is confirmed on `deliver`'s
validation path; the `self_test` path is still to read on EB0 cells. The
receipt's `guard_firings` carries the retired `self_test_redirected` key
and no red-stop key (the cleanup audit's item). Launching also found a
launcher crash: a settings refusal whose text starts with the provenance
JSON raised `JSONDecodeError` before `launch FAILED:` printed; fixed at
`cd0c9fe` with a test both ways. The refusal itself was host drift —
`~/.pi/agent/models.json` had `maxTokens: 32000` for Ornith against the
arms' 16,000 — set back to 16,000 before the run.

## 8b. EB0, 2026-10-02/03 — the first confinement-grade read

`records/2026-10-02-eb0-*.json`, three development records, both arms, n = 6,
k = 3, engine `1869397`, M5 Max, 2 h 37 min wall clock for all three
(21:50–00:27). No infrastructure failure, no replaced cell. Delivered passes
only; medians with ranges; this is EB1's input, not a floor read, and
nothing here pools with release two's numbers (different machine and
harness).

| task | arm | pass | output tokens | turns | peak context | span (min) | Engine higher, pairs |
|---|---|---|---|---|---|---|---|
| depth-3 | B | 6 of 6 | 7,095 (3,566–16,077) | 14 | 12,903 | 5.4 | |
| | E | 6 of 6 | 8,410 (4,165–16,876) | 11 | 14,593 | 6.0 | 22 of 36 |
| guard-prefixes | B | 4 of 6 (1 over budget, 1 unavailable) | 6,364 (3,654–6,769) | 11 | 10,531 | 3.4 | |
| | E | 5 of 6 | 21,086 (9,918–45,268) | 35 | 29,823 | 15.0 | **20 of 20** |
| review-script | B | 5 of 6 | 8,047 (6,390–9,300) | 21 | 20,758 | 5.7 | |
| | E | 5 of 6 | 13,102 (11,364–17,744) | 19 | 29,147 | 10.3 | **25 of 25** |

**Pre-registered counts** (all cells):

| | depth-3 B / E | guard B / E | review B / E |
|---|---|---|---|
| calls before first edit (touching `tests/`) | 7 (3) / 9 (2) | 1 (0) / 7 (3) | 6 (3) / 14 (6) |
| cells writing a test file | 0 / 0 | 0 / 4 | 6 / 6 |
| rejected edit/write calls, cells | 0 / 16 in 6 | 10 in 4 / 16 in 6 | 4 in 3 / 7 in 3 |
| of which Pi schema validation | 0 / 14 | 0 / 6 | 1 / 6 |
| automatic self-tests | 0 / 1 | 0 / 4 | 0 / 13 |
| note bytes per cell | 0 / 215 | 0 / 215 (–9,016) | 0 / 7,529 |
| edit-result bytes per cell | 145 / 749 | 114 / 3,910 | 114 / 253 |
| turns from steer to stop | – / 1 (1–3) | – / 1 | – / 1 (1–7) |
| `confinement_refused` | 0 / 0 | 2 / 0 | 0 / 0 |

**What reproduced on this harness.** The gap on the two build-shaped floor
tasks, in every pair; depth-3 again without a robust difference. Schema-
rejected `edit` calls on the Engine arm only (26 against 1 across 18 cells
each). The test-file survey and writing on guard-prefixes (4 of 6 against 0
of 6; 7 calls before the first edit against 1). The edit-result echo (3,910 B
per guard cell). On the `self_test` path: all 31 Engine self-test events (13 model-called tool results, 18 automatic notes) carry two suite summaries, and 29 of 31 carry the `VIRTUAL_ENV` warning (the two red depth-3 results are compacted). The two runs are not duplicates: the second, declared + `preserve`, counts only the carried tests and leaves out the model's new test file, so it re-verifies the carried tests and never sees the model's own failure; each run takes about 31 s on the self-hosted base (EB1 §3). Corrected 2026-10-03 from EB1: this sentence first said 21 of 23 and 'all 23', and called the second run a double run.
No `confinement_refused` on the Engine arm in 18 cells; every Engine
file-tool path was relative, so §8's absolute-path case remains untested.

**Harness findings, not EB's.**
- Confinement bites Baseline, not the Engine: two guard-prefixes Baseline
  cells tried to `write` scratch tests to `/tmp/test_*.py`, were refused, and
  are un-admitted (Baseline 4 admitted / 2 flagged; Engine 6 / 0). Three of six Engine guard-prefixes cells made the same kind of write (`/tmp/t.py`, `/tmp/probe.py`); the Engine's contract scope refused them first, the extension logged nothing, and those cells stay admitted. Admission is therefore arm-asymmetric on this task, to be ruled before any cross-arm floor read (EB3, R5).
- The reach audit flags a cell for touching **its own** file when the
  basename matches a hidden test's: review-script's hidden suite is
  `tests/test_review.py`, the name every model gives the test it writes for
  `tools/review.py`, so all 12 review-script cells are flagged with 0
  refusals (`confinement.py` `names=('test_review.py', …)`). A false positive
  by construction; it will recur on any census task whose hidden test shares
  the obvious new-test name.
- The grader's `grader_content_in_patch` flagged 3 of 6 Engine guard-prefixes
  cells (one a fail) because the test file the contract told the model to
  create reproduces a block of the hidden `test_hook_guard.py`; the prompt
  enumerates the cases, so convergence is expected. Verdicts unchanged.

EB1's read of these cells is `evidence/2026-10-03-eb1-read/README.md`.

## 9. Against `docs/numbers.md`

Agrees: every floor median; parity fails on guard and review. Disagrees:
"self-test runs and guard messages are real overhead" — self-tests cost wall
clock and context, not tokens (test-run turns differ by +20 to +576), and no
guard fired on a floor pass; the unnamed causes are the prompt's test lines,
schema-rejected edits, and more reading before the first edit. "On a
ten-turn fix they do not pay for themselves" rests on depth-3, which shows no
robust difference. Review's Baseline denominator (2 of 6) is not caveated.
The larger peak context is mostly the model's own output.
