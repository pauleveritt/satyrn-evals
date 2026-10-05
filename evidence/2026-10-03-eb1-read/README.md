# EB1 - offline read of the EB0 cells (confinement harness, engine 1869397, M5 Max)

Development cells; this is a diagnosis, not a floor-parity read.

```
python3 evidence/2026-10-03-eb1-read/eb1.py ~/satyrn-runs
```

Input: `~/satyrn-runs/2026-10-02-eb0-{agentclinic-repair-depth-3,selfhost-guard-prefixes,selfhost-review-script}/{baseline,engine}/`, 6 cells per arm per task (36 cells), none missing. Stdlib only, no model, no network; the simulation seed is 20261003. Tool calls come from `tool_execution_start`, one per call. Context for a turn is `usage.input + usage.cacheRead`. A delivered pass is `verdict == "pass"`. Medians are given with ranges, and nothing is pooled across tasks or arms. B = Baseline (bare Pi), E = Engine.

## 1. The floor set

**Rule, stated before applying it (spec section 3, EB1 row):** "a task is in it when both arms deliver at least 4 of 6 and one arm's output tokens per pass are higher in at least 3 of every 4 cross-arm pass pairs (27 of 36 at 6 and 6)". Ties count for neither arm.

| task | B delivered | E delivered | pairs | E higher | B higher | needed | in? |
|---|---|---|---|---|---|---|---|
| depth-3 | 6/6 | 6/6 | 36 | 22 | 14 | 27 | no |
| guard-prefixes | 4/6 (1 `BUDGET_EXCEEDED`, 1 `unavailable`) | 5/6 (1 fail) | 20 | 20 | 0 | 15 | **yes** |
| review-script | 5/6 (1 fail) | 5/6 (1 fail) | 25 | 25 | 0 | 19 | **yes** |

**The floor set is {guard-prefixes, review-script}.** One of the 4 guard-prefixes B passes (`022915-123908`) has a confinement refusal, so it is un-admitted. It is still a delivered pass under the rule above, and it is counted. Output tokens per delivered pass:

| task | B | E | turns B / E | peak context B / E | span (min) B / E |
|---|---|---|---|---|---|
| depth-3 | 7,096 (3,566-16,077) | 8,410 (4,165-16,876) | 14 / 11 | 12,903 / 14,594 | 5.4 / 6.0 |
| guard-prefixes | 6,364 (3,654-6,769) | 21,086 (9,918-45,268) | 11.5 / 35 | 10,532 / 29,823 | 3.4 / 15.0 |
| review-script | 8,047 (6,390-9,300) | 13,102 (11,364-17,744) | 21 / 19 | 20,758 / 29,147 | 5.7 / 10.3 |

## 2. Attribution per floor-set task

**Method.** Each assistant turn goes into exactly one category, and the first rule that matches wins:

1. *final*: the turn makes no tool call.
2. *post-steer*: the turn makes tool calls after the first `finish_nudged` message.
3. *retry:<shape>*: the previous turn had a rejected (`isError`) `edit`/`write` call. The shape is that of the first rejection: Pi schema "Validation failed", `ANCHOR_MISSING`, `NO_CHANGE_REQUESTED`, Pi "No changes made", Pi "Could not find", confinement ("outside the attempt worktree"), or Engine scope refusal ("outside the contract's writable paths").
4. *test file*: the turn writes or edits a test file the model created, or runs a bash command that names it. A created test file is one that `patch.diff` shows as `new file` under `tests/` or `test_*.py`, or a successful `write` to such a path that is absent from the patch.
5. *pre-edit*: the turn comes before the first turn with a landed (non-error) `edit`/`write`.
6. Everything else, in order: *src edit*, *test run* (bash `pytest` or `self_test`), *probe*.

**Upper bounds and limits.**
- Retry figures are upper bounds, because a retry turn also re-emits the plan and the edit.
- The pre-edit and test-file figures for the Engine are the tokens of those turns. They are not the part that the contract's lines caused.
- Medians are taken over different cells, so the category rows do not sum. The residual shown is total Δ minus the sum of category Δs. Means do sum, so both are given.

**guard-prefixes** (B n=4, E n=5):

| category | B med | E med | Δ med | B mean | E mean | Δ mean | E cells >0 | B cells >0 |
|---|---|---|---|---|---|---|---|---|
| pre-edit | 38 | 5,921 | +5,883 | 928 | 6,723 | +5,795 | 5/5 | 4/4 |
| test file | 0 | 1,769 | +1,769 | 146 | 2,898 | +2,752 | 3/5 | 1/4 |
| retry: schema | 0 | 536 | +536 | 0 | 796 | +796 | 4/5 | 0/4 |
| retry: ANCHOR_MISSING / NO_CHANGE_REQUESTED | 0 | 0 | 0 | 0 | 220 / 47 | +267 | 2/5, 1/5 | 0/4 |
| retry: scope refusal (Engine) | 0 | 0 | 0 | 0 | 441 | +441 | 2/5 | 0/4 |
| retry: Pi no-change / confinement | 0 | 0 | 0 | 194 / 94 | 0 | -288 | 0/5 | 1/4, 1/4 |
| src edit | 2,214 | 2,969 | +756 | 2,362 | 2,186 | -176 | 4/5 | 4/4 |
| test run | 0 | 156 | +156 | 0 | 239 | +239 | 4/5 | 0/4 |
| probe | 1,194 | 3,062 | +1,868 | 1,703 | 12,462 | +10,759 | 5/5 | 4/4 |
| post-steer (tool calls) | - | 0 | 0 | - | 0 | 0 | 0/5 | - |
| final | 362 | 536 | +174 | 360 | 548 | +187 | 5/5 | 4/4 |
| **total** | 6,364 | 21,086 | **+14,722** | 5,788 | 26,559 | **+20,771** | | |

The residual of the medians is +3,580. Turns before the first landed edit: B 1 (1-2), E 8 (5-11). Calls before it: B 1, E 8 (5-13). Calls touching tests before it: B 0 (0-1), E 3 (2-5). Test files created: 3 of 5 E passes write `tests/test_guard.py`, against 1 of 4 B passes, and that B file is a scratch `tools/hooks/_test_lead.py`, deleted again. Under the `tests/`-only count, B is 0 of 4 and E is 4 of 6 cells. The mean probe gap (+10.8k) is two E passes, `023425` (20.5k of probe) and `030807` (35.5k, 57 probe turns). Both are long runs of inline `python3 -c` regex experiments after the first edit; see section 7.

**review-script** (B n=5, E n=5):

| category | B med | E med | Δ med | B mean | E mean | Δ mean | E cells >0 | B cells >0 |
|---|---|---|---|---|---|---|---|---|
| pre-edit | 2,556 | 4,296 | +1,740 | 2,636 | 5,421 | +2,785 | 5/5 | 5/5 |
| test file | 2,320 | 3,472 | +1,152 | 2,040 | 3,775 | +1,736 | 5/5 | 5/5 |
| retry: schema | 0 | 0 | 0 | 0 | 1,176 | +1,176 | 2/5 | 0/5 |
| retry: ANCHOR_MISSING | 0 | 0 | 0 | 0 | 237 | +237 | 1/5 | 0/5 |
| retry: Pi "Could not find" | 0 | 0 | 0 | 55 | 0 | -55 | 0/5 | 2/5 |
| post-steer (tool calls) | - | 0 | 0 | - | 144 | +144 | 1/5 | - |
| src edit | 2,139 | 1,494 | -645 | 2,086 | 2,148 | +62 | 5/5 | 5/5 |
| test run / probe | 144 / 353 | 0 / 0 | -497 | 102 / 443 | 0 / 379 | -166 | 0/5, 2/5 | 3/5, 4/5 |
| final | 455 | 966 | +511 | 467 | 1,079 | +611 | 5/5 | 5/5 |
| **total** | 8,047 | 13,102 | **+5,055** | 7,830 | 14,358 | **+6,528** | | |

The residual of the medians is +2,794. Both arms create `tests/test_review.py`, because both prompts say `Create: ... tests/`. Turns before the first landed edit: B 6 (4-9), E 8 (4-17). Calls before it: B 6, E 14 (4-17). Calls touching tests before it: B 1 (1-2), E 5 (2-6).

**depth-3** (not floor, for reference): total Δ +1,315. Pre-edit Δ +4,058, set against B's src-edit, probe and test-run turns (Δ -2,097). Schema retries appear in 6 of 6 E cells and 0 of 6 B cells (median 356).

**All cells, rejected edit/write calls.**
- depth-3: B 0. E 16 in 6/6 cells: 14 schema, of which 10 are per-item path in one file, 3 multi-file and 1 truncated `edits` string; plus 2 `ANCHOR_MISSING`.
- guard-prefixes: B 10 in 4/6 cells: 7 Pi no-change, 2 confinement, 1 "Could not find". E 16 in 6/6 cells: 6 schema (5 nested one-file, 1 per-item), 4 scope refusals, 3 `NO_CHANGE_REQUESTED`, 3 `ANCHOR_MISSING`.
- review-script: B 4 in 3/6 cells (3 "Could not find", 1 schema). E 7 in 3/6 cells (6 schema, all per-item one-file; 1 `ANCHOR_MISSING`).
- Engine `confinement_refused`: 0 in 18 cells.

## 3. The self_test path

There are 31 events on the Engine arm, in all 18 cells. 13 are model-called `self_test` tool results: 7 on depth-3 and 6 on guard-prefixes. 18 are "The Engine also ran self_test" notes appended to a model bash test run: 1 on depth-3, 4 on guard-prefixes and 13 on review-script.

Wall clock is the timeline duration of the call. For a note, that duration includes the model's own targeted run, which takes under 1 s plus `uv` start-up. Note bytes run from `[satyrn-engine note` to the end; for a tool event, they are the whole result.

| | depth-3 | guard-prefixes | review-script |
|---|---|---|---|
| events (tool / note), cells | 8 (7/1), 6 of 6 | 10 (6/4), 6 of 6 | 13 (0/13), 6 of 6 |
| two suite summaries | 8/8 | 10/10 | 13/13 |
| call wall clock, s | tool 1.8 (1.5-3.6); note 3.0 | tool 63.8 (61.9-64.9); note 63.8 (33.8-64.3) | note 62.5 (33.3-64.8) |
| Engine seconds per cell (6 cells) | 3 (2-5) | 81 (62-192) | 112 (63-250) |
| bytes | 4,572 (1,428-4,761) | tool 4,858 (3,154-9,633); note 4,402 (2,520-4,711) | 4,711 (2,521-4,711) |
| of which dot lines; `VIRTUAL_ENV` warning | 1,000; 6 of 8 | 3,000-4,000; 10 of 10 | 4,000; 13 of 13 |
| model's own run before a note: targeted / full; red / green | 0 / 1; 0 / 1 | 4 / 0; 2 / 2 | 13 / 0; 5 / 8 |
| Engine red | 2 of 8 (both tool calls) | 4 of 10 | 5 of 13 |
| red after a red targeted model run: any failure outside the files the model ran | none of 0 | 0 of 2 | 0 of 5 |

- **The two summaries are not identical runs.** The first is the declared command over the whole tree. On guard-prefixes and review-script it counts the model's new test file: 1,515 = 1,509 + 6 on review-script, and 1,548-1,555 on guard-prefixes. The second, the `preserve` run, counts only the carried tests (1,509 and 1,521), so it can never see the model's own failure. In all 9 red selfhost events the second run was green. Each run takes about 31 s.
- **The red depth-3 events have no measured preceding run.** The model called `self_test` directly, and the two compacted red results lack the dots and the warning.
- **Tool events are model-chosen, not automatic.** For the 13 tool events, the model's "preceding run" is not well defined: the model invoked `self_test` without a bash test run first.

## 4. Context and wall clock (declared secondaries, delivered passes)

The peak is the last turn in every one of the 31 passes. Context at the peak breaks down exactly as first-turn context + Σ earlier output + Σ injected tokens, where injected(i) = ctx(i+1) - ctx(i) - out(i). No turn showed a negative injection, so the model's whole output, reasoning included, stays in context. Injected tokens are split among result classes in proportion to their bytes; that split is an approximation, but the total is exact.

| median tokens at peak | guard B | guard E | Δ | review B | review E | Δ | depth-3 Δ |
|---|---|---|---|---|---|---|---|
| peak | 10,532 | 29,823 | +19,291 | 20,758 | 29,147 | +8,389 | +1,691 |
| first turn | 1,870 | 1,992 | +122 | 1,997 | 2,124 | +127 | +152 |
| model's own earlier output | 6,002 | 20,468 | **+14,466** | 7,565 | 12,685 | **+5,120** | +1,331 |
| edit-result echo | 44 | 1,563 | +1,518 | 58 | 75 | +17 | +188 |
| Engine notes (self-test, command bound) | 0 | 605 | +605 | 0 | 873 | +873 | +1,073 |
| finish steer | 0 | 50 | +50 | 0 | 44 | +44 | +97 |
| rejection messages | 41 | 637 | +596 | 0 | 34 | +34 | +395 |
| other tool results | 2,546 | 4,848 | +2,302 | 11,292 | 11,018 | -274 | -2,059 |

**Model time against tool time.** Per turn, model time is the gap from the assistant message's timestamp to its last tool result, minus the union of that turn's timeline tool intervals. The final turn has no end stamp, so it is unmeasured and excluded.

| task | model time, B / E (s) | tool time, B / E (s) | model s per 1k output tokens, B / E |
|---|---|---|---|
| guard-prefixes | 206 / 840 | 1 / 70 | 38.9 / 47.3 |
| review-script | 315 / 516 | 35 / 98 | 42.8 / 41.3 |
| depth-3 | 328 / 361 | 5 / 5 | 47.5 / 45.8 |

The Engine's extra minutes are mostly model time, meaning more output. Tool time is the self-test: one or two runs of about 62 s each per pass. On guard-prefixes the Engine also generates more slowly per token, probably because its context is about 3 times larger.

## 5. Remedy ranking

All figures are in output tokens per delivered pass, over Engine passes. Each remedy is scored by whether a replay of the recordings can score it (R0 section 1.4: an estimate is valid only when the remedy's effect begins at or after the measured point).

| rank | remedy (spec section 3) | class targeted | cells that show it | estimate: guard / review (depth-3) | can a replay score it? |
|---|---|---|---|---|---|
| 1 | light path for small requests | everything the Engine adds on a modify-only task with one symbol | guard 5/5 E passes; review does not qualify (it creates files) | **≤ +14,722** / n.a. (≤ +1,315, not robust) | **No.** It changes calls from turn 1. Upper bound: the whole E-B median gap. |
| 2 | the contract's test lines | pre-edit survey of `tests/` and writing the test file | guard: pre-edit 5/5, test file 3/5; review: survey 5/5 | **≤ +11,690** / **≤ +3,618** (≤ +4,058) | **No.** It changes calls from turn 1. Upper bound: E median (pre-edit + test file) minus B median. Review keeps its test file, because both prompts ask for it. |
| 3 | R2 parity: normalizer for unambiguous `edit` shapes | schema-rejection retries | guard 4/5, review 2/5, depth-3 6/6 E passes | 536 (0-2,205), mean 796 / 0 (0-4,112), mean 1,176 (0, mean 338) | **Partly.** A replay can check that the recorded call is accepted, since the effect begins at that call. Dropping the retry turn is an upper bound, because that turn carries the plan, and later turns are not scored. |
| 3b | R2 parity: all schema + `ANCHOR_MISSING` retries (adds descriptions, guidelines, fuzzy fallback) | same, plus exact-anchor misses | as above, plus `ANCHOR_MISSING` in guard 2/5, review 1/5 | 747, mean 1,016 / 1,183, mean 1,412 (400) | **No for descriptions and guidelines:** they change the earlier call. Fuzzy matching is not checked against the file state here. Upper bound. |
| 4 | edit-result echo trimming | context | guard 3,910 B per cell | output: none measurable / none (none). Context at peak: -1,563 / -75 (-270) tokens | **Bytes yes, effect no.** Replay scores the bytes removed; later output is not scored. |
| 5 | self-test dedup after a red model run; drop the second run; dot filter; `VIRTUAL_ENV` strip | wall clock, context | review 5 red notes; every event | output: none measurable. Seconds per pass: dedup 0 (0-34) / 33 (0-188); second run 31 (30-94) / 62 (30-122). Note bytes per pass: 4,211 / 6,422. | **Seconds and bytes yes.** Output is not scored. The dedup is safe on this evidence: 0 of 7 red Engine runs after a red targeted model run found anything new. |

- **Remedies 1 and 2 overlap on guard-prefixes**, so their figures do not add. The whole guard-prefixes gap is 14.7k.
- **None of the five is aimed at the largest unexplained guard cost**: inline regex probing (section 7).
- **Reviewer's note, 2026-10-03: rank 3 is a remedy, not R2 parity.** Pi 0.85.1's `edit` requires a top-level `path` and never hoists one; its three argument repairs rescue 0 of EB0's 26 Engine schema rejections. Hoisting the unambiguous shapes goes beyond Pi and moves to EB2 (design spec section 7). R2 parity is the descriptions, the guidelines and Pi's three repairs, whose effect a replay cannot score.

## 6. The parity rule's power

**Rule** (spec section 4), applied per floor task with n = 6 per arm: parity holds when the Engine median is at most 1.25 × Baseline's, and an exact one-sided Mann-Whitney test of "Engine ≤ Baseline" does not reject at 0.05. The test is a permutation over all 924 splits, with midranks for ties.

**Simulation.** Both arms draw 6 values from the observed Baseline passes, and the Engine draws are multiplied by m. Two draw models are used:
- *resample*: with replacement from B's 4-5 passes. This understates spread and creates ties.
- *log-normal*: fitted to those passes; σ is 0.290 on guard-prefixes and 0.156 on review-script.

Each figure is 4,000 repetitions with seed 20261003.

| P(rule declares parity) | m = 1.0 | 1.1 | 1.25 | 1.5 | 2.0 |
|---|---|---|---|---|---|
| guard-prefixes, resample | 0.864 | 0.557 | 0.337 | 0.122 | 0.000 |
| guard-prefixes, log-normal | 0.868 | 0.720 | 0.473 | 0.145 | 0.004 |
| review-script, resample | 0.937 | 0.647 | 0.397 | 0.000 | 0.000 |
| review-script, log-normal | 0.951 | 0.747 | 0.272 | 0.008 | 0.000 |
| depth-3 (not floor), log-normal | 0.715 | 0.621 | 0.486 | 0.334 | 0.123 |

**n = 6 cannot reliably tell 1.0 from 1.25.** An Engine that is truly 1.25 × Baseline is declared at parity 27-47% of the time. A truly equal Engine fails the rule 5-14% of the time, almost all of that from the median clause. The rule does separate 1.0 from 1.5 and above on the two floor tasks.

**The margin the Baseline spread alone justifies.** This is the 95th percentile of median(E)/median(B) under true parity, which is the margin that true parity would pass 95% of the time:
- guard-prefixes: 1.34 (resample), 1.37 (log-normal)
- review-script: 1.24, 1.18
- depth-3: 2.33, 2.00

On review-script, 1.25 sits at about the 95th percentile. On guard-prefixes it sits at about the 90th, so the margin would need to be about 1.35. These come from 4-5 Baseline passes, so they too are uncertain. The observed gaps (3.3× and 1.6×) are far outside every margin considered.

## 7. Surprises, and disagreements with README sections 1-7 and 8b

**Surprises**
- **Inline probing is the largest guard-prefixes cost no listed remedy targets.** It accounts for 52% of the mean gap (probe Δ mean +10.8k of +20.8k), almost all from 2 of 5 passes. The model tested its regex in long runs of bash inline Python. In `022519` it switched only after "Bash is mangling the escaping": it tried `write /tmp/t.py`, which the Engine refused as outside the contract's writable paths, then `tests/test_scratch.py`, also refused. Scope refusals hit 2 of 5 E passes; on B, confinement refused `/tmp` writes in 2 cells. This is not in section 2 or 3 of the spec. It is named here, not proposed.
- **The Engine prompt's budget does not match the Engine receipts.** The prompt says "Budget: 48000 output tokens and 72 turns", but every Engine receipt (19 of 19, smoke included) records `token_limit 64000`, `turn_limit 74`. Which one binds cannot be measured from these cells, because no Engine cell hit either. Reviewer's note, 2026-10-03: this is designed headroom, not a defect. The harness passes `deliver` the record's budgets plus a margin so that the harness's own tripwire stops a cell before the Engine's does (`src/satyrn_evals/attempt_engine.py` lines 88-89 set `DELIVER_TOKEN_HEADROOM = 16_000` and `DELIVER_TURN_HEADROOM = 2`; lines 177-178 pass `--token-limit token_budget + 16_000` and `--turn-limit turn_budget + 2`; lines 59-87 give the rationale; 48,000 + 16,000 = 64,000 and 72 + 2 = 74).
- **Review-script's Engine final report is twice as long** as Baseline's (966 against 455, 5/5 against 5/5).
- **The `preserve` run excludes the model's own new test file** (section 3), so the second suite run is pure re-verification of carried tests.

**Against README sections 1-7** (older harness, unconfirmed). What reproduces, in direction:
- the guard-prefixes survey: 8 against 1 calls before the first landed edit (section 2 said 9.5 against 1);
- Engine-only schema rejections;
- red self-test failures confined to files the model ran: 7 of 7 here, against 87 of 87;
- peak context mostly the model's own output;
- no robust depth-3 difference.

What differs:
- **The unambiguous share of schema rejections is lower.** Here 22 of 26 Engine schema rejections are unambiguous; section 3 had 82 of 95. Depth-3's 3 multi-file calls stay refused.
- **"No guard fired on any floor pass" (section 2) no longer holds.** `scope_refused` fired in 2 of 5 guard-prefixes E passes.
- **The double suite run is not a duplicate** (section 4); see section 3 above.
- **Edit echo is about 1.6k tokens at the guard-prefixes peak**, against section 5's ~900. On review-script it is about 0.
- **Post-steer tool turns** occur in 3 of 16 E passes here, against "14 of 15 stop at once"; that is consistent.

**Against 8b.**
- Every table value reproduces from `cells.py`. Guard-prefixes B turns are a median of 11.5, which `cells.py` truncates to 11.
- **"4 of 6 (1 over budget)" leaves out a cell.** The sixth guard-prefixes B cell is `unavailable` (`030759`).
- **I cannot reproduce "21 of 23 results carry two suite summaries".** I find 31 events (13 tool, 18 note), and all 31 carry two summaries.
- **"All 23 carry dot lines and the warning" does not hold for all events.** 29 of 31 carry them; the 2 red depth-3 tool results are compacted and carry neither.
- 8b's "automatic self-tests 1 / 4 / 13" counts notes only, and that agrees with the counts here.

**Cannot be measured from these cells:** the final turn's model time; whether ANCHOR_MISSING calls would match under Pi's fuzzy fallback; any downstream effect of a remedy.
