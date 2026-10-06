# Review of the run-record-gate decision, and a re-plan of EB ("costs extra")

**Provenance.** Written 2026-10-06 by Fable, read-only, at the maintainer's request ("Ask Fable for a deep review of the findings and re-plan of EB"). Copied into the repo the same day by the controller (Opus); the only edits are the scratchpad paths, rewritten to this directory. **All eight rulings in §4 were adopted by the maintainer 2026-10-06 ("Adopt all eight")**; the ledger entry "Review of the comparison and EB re-plan: eight rulings" records them, and `docs/superpowers/plans/2026-10-06-eb-replan.md` sequences the work. Supporting files: `scan.py`, `trace.py`, `scan.jsonl` (per-cell scan of the 72 campaign cells), `review-ops.json` and `review-recon.diff` (the reconstructed review-script tree, §2.1), `review-recon.receipt.json` and `budget-trees/*.{diff,receipt.json}` (offline grades). The reconstructed trees are reconstructions and never deciding.

Read-only review, 2026-10-06, for the maintainer. No file in either tree was changed (`git status` clean apart from the two pre-existing untracked drafts; engine checkout at `23a0ef6`). No model, no launch, no network. Offline grades ran from a session scratchpad with `uv run --project … satyrn-evals grade`; their diffs and receipts are copied here as `budget-trees/` and `review-recon.{diff,receipt.json}`. Transcript scans used `scan.py` and `trace.py`, in this directory (turns from `turn_start`, tokens from assistant `message_end` `usage.output`, tool calls from `tool_execution_start`, guard firings from `entry_appended` custom entries). Paths are relative to `satyrn-evals` unless they start with `satyrn-engine/`.

Every figure below says whether it is **established** (in a committed file or recomputed from retained evidence) or **judgment**.

---

## 1. Review of the findings

### 1.1 The number stands

Recomputed from `evidence/2026-10-05-rrg-delivery/decision.txt` counts: primary 22/36 vs 10/36, one-sided Fisher p = 0.0043; admitted-only 22/36 vs 10/35, p = 0.0056; beside 22/34 vs 10/36, p = 0.0020. The reader was frozen before launch (digest in the records' `decision_rule`), three pieces completed with 0 replaced, 0 infrastructure, no wall-clock cut, no verdict read before all three finished. **Established: the pre-registered rule rejects on both required counts. The claim in §1 of the pre-registration holds as written.**

### 1.2 What the claim licenses, and what it does not

It licenses exactly: on `selfhost-run-record-gate` R1-plan, confinement, Ornith 1.5 9B on oMLX, M5 Max, 48,000 tokens / 72 turns, engine `23a0ef6`, the Engine **delivers** (self-stops holding a passing patch) more often than bare Pi. It is a finishing claim, and the secondaries say so more strongly than the README does:

| reading (established from `grade-line-{a,b,c}.json`) | Baseline | Engine |
|---|---|---|
| delivered (harness verdict pass) | 10 / 36 | 22 / 36 |
| pass at the 32k/48 line (`line_verdict`, `unavailable` excluded) | 29 / 33 | 28 / 34 |
| **held a hidden-suite pass when the budget cut the cell** (`tripped_verdict` over `BUDGET_EXCEEDED` cells) | **22 / 26** (fail 2, unavailable 2) | **unmeasured** (0 of 8 have a `tripped.diff`; see §1.6) |
| cells ending with a passing tree, delivered or not | **32 / 36** | ≥ 22 + (8 budget cells: 8/8 pass at the line, 4/4 recoverable final source trees pass offline, §3.3) + 2 discarded cells whose line trees pass (§2) |

So **capability on this task is near parity; the difference is stopping.** The claim does not license: a capability claim, a cost claim (the floor negative stands), generalisation to any other task, or a component claim (nudge vs. budget line vs. "Stop when the task is complete"); the Engine prompt differs from bare Pi's by the derived-contract lines (`satyrn-engine/src/satyrn_engine/attempt.py:724-747`: writable paths, carried tests, "Verify with the self_test tool", "Budget: 48000 output tokens and 72 turns", "Stop when the task is complete") and the finish steer (`packages/engine/runner.ts:335,467-475`), and no matched control separates them. That is allowed for a product claim (R0 §4) and must stay a product claim.

**Recommendation (judgment):** the results page should carry the tripped row above. Without it a reader can take 22 vs 10 as "the Engine solves the task more often", which the retained evidence contradicts.

### 1.3 The deliver headroom: verified, no advantage to the Engine

- `src/satyrn_evals/attempt_engine.py:88-89` set `DELIVER_TOKEN_HEADROOM = 16_000`, `DELIVER_TURN_HEADROOM = 2`; `:177-178` pass `--token-limit 64000 --turn-limit 74` to `deliver` only. `derive_argv` carries the record's exact budget into the contract, which is what the prompt shows (`:731` in the engine).
- The harness stop is the same object for both arms: `src/satyrn_evals/attempt.py:314-317` exports `SATYRN_TOKEN_BUDGET/TURN_BUDGET` identically; `src/satyrn_evals/budget.py:37-63` `UsageCounter` counts `turn_start` and assistant `message_end.usage.output` from the transcript each arm writes; `workspace.py` feeds the same `BudgetTripwire` for both.
- Established from the cells: every Engine receipt records `turn_limit 74 / token_limit 64000`, and the 8 Engine `BUDGET_EXCEEDED` cells were stopped by the harness with the same messages as Baseline's ("started turn 73, over the budget of 72 turns"; "spent 49572 output tokens, over the budget of 48000"), with no receipt written (the process group was torn down). Receipt `turns_used` equals the harness turn count in every cell that has both (56 = 56, 54 = 54, 37 = 37). Token overshoot after the last `message_end` is the same on both arms (Baseline 48,100 / 48,196; Engine 49,572 / 48,119 / 48,073).

**Verdict: the Engine's own limit never binds; the headroom cannot explain any part of the gap.** The one real asymmetry in budget *information* is that the Engine's model is told the budget and Baseline's is not — a product message, not a harness defect.

### 1.4 Is "finishing" the right explanation? Yes, and the mechanism is visible

Established from the 72 transcripts (`scan.jsonl`):
- Baseline: 26 of 36 ran to the budget (20 at 72 turns, 6 at the token edge). The last green test run sits at turn 55–72 in 34 of 36 cells (median ≈ 65): the model keeps re-testing, polishing and executing the task's own five-step recipe (Step 4 verification commands, Step 5 "Record and commit") until the harness stops it. Baseline ran `git commit` in the worktree in 9 cells; 6 of those are among its 10 delivered passes.
- Engine: `finish_nudged` fired in 34 of 36 cells (first nudge median turn 33). The 25 delivered cells stopped a median of 4 turns after the first nudge (range 1–39); 18 of 25 made no further edit. The 8 budget cells: 6 were nudged (turns 36–58) and continued anyway — coverage runs, lint, test-count fiddling, the recipe (`836120`: nudged at t58, then `--cov`, removed an unused import at t71, re-nudged at t68 and t72); 2 were never nudged because the steer arms only on a green run (`runner.ts:467-471`) and their own test files never went green (`709608`: red at t50, t63, t69; green only at t71–72). The three `NO_PATCH` cells followed Step 5 after or around the nudge and committed; the steer's own text says "Do not commit" and the model committed anyway (`988718`: nudge t48, "Now let me commit" t51, commit t53).

**Judgment:** "finishing" is the right class on both arms. The Engine's remedy is a soft steer that works in about three cells of four; where it fails, it fails to the same recipe Baseline follows. Nothing in the harness manufactures the gap.

### 1.5 The D2/D3 rules, interleaving, the 72-turn edge

- **D2** reclassified 2 Engine cells (`200221-102589`, `054648-457847`); both are `rec.json` written inside the worktree (the task's Step 4 says `/tmp/rec.json`). No Baseline cell had a final `unavailable`, so D2 acted only against the Engine, as designed. Baseline's own `rec.json`-style strays appear in its tripped/line verdicts (2 tripped `unavailable`), so the behaviour is shared; only the arm it was charged to differs.
- **D3** excluded one Baseline cell (`055606-066842`, a `BUDGET_EXCEEDED` with one refusal) from the admitted denominator, which raises Baseline's rate; the rule still rejects.
- **Interleaving, k = 3:** slots alternate arms; tokens and turns are server-independent; no wall-clock cut; the Engine's 60 s self-tests add CPU load while Baseline generates, which touches wall clock only (reported descriptive, §5 item 4). k is not re-derived on the M5 Max (STATE); that affects schedule estimates, not the decision.
- **The 72-turn edge:** Baseline's token totals at 72 turns were 31k–48k, so a larger turn budget would mostly convert into token-edge stops. The claim is at this budget and says so.
- **Disclosed post-hoc endpoint:** the endpoint moved after the two n = 6 development reads; the 36 + 36 cells are fresh, the reader was frozen first, and the observed rates (0.61 / 0.28) sit near the planning inputs (0.67 / 0.33). Legitimate under BRIEF ("an informed selection is legitimate"), and properly labelled.

### 1.6 Things to mark or qualify (none affects the decision)

1. **A one-directional harvest asymmetry, against the Engine (established).** Baseline's final harvest is the cumulative diff from the base commit, "so a model `git commit` hides nothing" (`src/satyrn_evals/attempt_pi.py:222-226`, the 2026-09-14 fix). The Engine's line harvest tolerates commits too (`workspace.py:1474` → `_harvest_patch(total=True)` from base; `247011`'s `line.diff` after two commits graded pass). Only the Engine's *deliver* discards: `satyrn-engine/src/satyrn_engine/delivery.py:1001-1004` returns `COMMAND_CHANGED_HEAD` whenever HEAD ≠ base or HEAD is attached. The task text "Step 5: Record and commit" is identical in both arms (`src/satyrn_evals/tasks/selfhost-run-record-gate/manifest.json`). Baseline committed in the worktree in 9 cells (6 delivered passes); the Engine committed in the worktree in exactly its 3 `NO_PATCH` cells (its 5 other `git commit` calls were in scratch repos under `/tmp` or `mktemp`). **The claim is conservative with respect to this asymmetry.** Qualify the result page with the direction; do not re-read the comparison at a fixed pin.
2. **The Engine arm has no tripped secondary (harness gap, established).** `workspace.py:1212-1225` `_harvest_tripped` harvests `state.worktree` (the Evals worktree), which holds no candidate for the Engine arm until `attempt_engine.py` checks one out; the line harvest (`:1474`) takes the Engine worktree override, the tripped harvest does not. All 8 Engine `BUDGET_EXCEEDED` cells lack `tripped.diff`; `grade-line` shows `tripped_verdict: None` for them. STATE's "tripped worktrees harvested and graded as a declared secondary" (R0 §1.1) is true for Baseline only. Decisions whose evidence this could have produced: none deciding (the decider is delivery); it leaves the Engine's "pass at the cut" unmeasured. Mark it as a known defect; do not build the fix until a reading needs it.
3. **The leftover temp worktrees are explained (established).** Eight `satyrn-engine-*` directories remain under `$TMPDIR`, one per Engine `BUDGET_EXCEEDED` cell (session `cwd` in each transcript matches: `bqt3_c5y`=`836120`, `rl2giglz`=`768330`, `lpx5ovhc`=`709608`, `541d9gkv`=`694438`, `t56nnrz4`=`731802`, `iqkv7lz2`=`502157`, `4b7i2uw3`=`546937`, `tld5e1f3`=`939358`). The harness tears the process group down; the Engine's own cleanup never runs. Four still hold the two source files; the seed `.git` is gone, so they are not git worktrees any more. Housekeeping, not evidence; §3.3 uses them once, labelled.
4. **Pin coverage (judgment).** The arm pins `engine_commit` plus seven TS digests. `attempt.py` (prompt text), `delivery.py` (the discard rule), `derive.py` (the contract) are covered by the commit pin only. The "same Engine bytes" argument across `6d30479 → 5b681b0 → 23a0ef6` rested on the digests plus the stated commit diffs, which is fine; note that candidate 1's fix lives in `delivery.py`, outside the digest set.
5. **The 2026-10-04 "finishing in the Engine arm was a replay artifact" correction** is itself now qualified: on the comparison cells the Engine arm *does* show the class (8 budget cells, all passing at the line), read by `grade-line`, not by replay. The withdrawal was right for those six cells; it does not generalise.

---

## 2. Candidate 1, verified offline: tolerating a model commit

### 2.1 The four discarded cells

The discarded trees themselves were not retained (`worktree_path: null` in each receipt; the deliver worktree is cleaned on discard). What is retained: `line.diff` (the cumulative tree at the line crossing, on the Engine worktree), the transcript (every `edit`/`write` call with its full arguments, every bash command, every tool result), and for the review-script cell nothing but the transcript. The bounds below are reconstructions and say so.

| cell | commit | line tree (`grade-line`) | writes after the line crossing | offline grade of the final tree | adds |
|---|---|---|---|---|---|
| a `192351-988718` (rrg) | t53, after the nudge at t48 | pass (crossed by tokens at t37) | 9 `edit`s, all `tests/test_run_record.py` (t37–t47); bash writers only `/tmp/rec.json`, `/tmp/p0-t8.log`; Engine `self_test` after the commit at t55: 1560 passed, 1489 passed | final source tree = line tree; the hidden overlay replaces `tests/test_run_record.py` → **pass** (reconstruction) | +1 |
| b `015113-247011` (rrg) | t23, t24, before the line at t41 | pass (crossed by tokens at t41) | `edit`s t41, t45 and `python -c` rewrites t46, t49, all `tests/test_run_record.py`; `/tmp/rec.json` t51; `self_test` t50: 1517 / 1489 | same reasoning → **pass** (reconstruction) | +1 |
| c `104033-813847` (rrg) | t28, committing its own test artifacts `committed.json`, `results/prev.json` | **unavailable** (patch touches `committed.json`, `results/prev.json`) | t32 `rm -f committed.json untracked.json`; t33 `git checkout HEAD -- results/prev.json committed.json`, which restores the committed files it meant to remove | the final tree still carries both strays → `unavailable` → not delivered under D2 | +0 |
| review-script `005058-171727` (`2026-10-04-eb-s1`) | t13, right after the nudge at t12 | none (14 turns, 6,229 tokens, never crossed) | the whole tree is 2 `write`s and 3 `edit`s, all file-tool, no bash writer; every `oldText` matched exactly once | reconstructed and graded: **pass, 6 of 6 hidden tests, contamination clean** (`review-recon.receipt.json`) | +1 |

**Bound, per task, denominators stated (established on the retained evidence, reconstruction-grade):**
- run-record-gate: at most **+2 of 36** (24/36 vs 10/36 would give p = 0.00097). It changes nothing about the decided claim and must not be read into it; the comparison measured the Engine as pinned.
- review-script: **+1 of 12** (7/12 vs 11/12, p = 0.077 — the delivery gap would no longer reject at 0.05; the cost negative stands: 149,080 ÷ 7 = 21,297 against Baseline 13,180).
- Across the four cells: 3 of 4 held a passing tree; the fourth held a stray it had committed.

### 2.2 Parity, not a behaviour change

Under the EB spec's own ruling ("a change that gives the Engine what bare Pi already has … is harness parity under R2"), this is parity: Baseline's harvest tolerates a commit by an explicit 2026-09-14 fix, the Engine's line harvest tolerates it, and only the Engine's deliver does not.

**Safest fix: tolerate (option 1), and not by resetting HEAD.** The candidate is already built from the worktree, not from HEAD: `delivery.py:1019` `git add -A`, `:1041` `write-tree`, `:1091` `commit-tree … -p base_commit`. None of those reads HEAD; the carried-test restore (`git checkout base_commit -- …`) and validation (`checkout --detach candidate`) do not either. The change is to demote the check at `:1001-1016` from a discard to a receipt field (`head_moved: true`, the observed HEAD) and keep the `GIT_FAILED` paths. Do not touch the model's worktree (no reset); the tree is the tree. Fixtures both directions: a committed worktree yields a candidate equal to its tree; an unchanged tree still yields `NO_CHANGES`.

Why not the others:
- **Refuse `git commit` (option 2)** is a new guard: it changes the model's calls (R0 §1.4 says such a change cannot be scored offline), and it would also refuse legitimate scratch-repo commits the task itself invites (`git ls-files --error-unmatch` testing): 5 Engine cells and 11 Baseline cells committed in scratch repos under `/tmp` or `mktemp` without touching the worktree.
- **Drop the commit step (option 3)** is not available: "Step 5: Record and commit" is the task's text, identical in both arms; removing it is a prompt change and a different condition. The steer already says "Do not commit" and the model committed anyway.

Cost if wrong: one engine commit and a re-pin; no cell. The comparison's claim stays at `23a0ef6` and is not re-read.

---

## 3. Re-plan of EB ("costs extra")

Order under AGENTS.md: harness validity → diagnosed admission → offline counterfactual → build; two consecutive instrument-only pieces stop the loop. The last two pieces were a measurement (the comparison) and this reading, so the next piece may be a build. GPU costs use measured sittings: one n = 12-per-arm piece on run-record-gate took 5.1–5.7 h at k = 3; guard-prefixes Engine ran 6 cells in about 1 h and Baseline 12 in 56 min; review-script Engine 6 in about 28 min; C3's preflight-quiet Baseline 6 took 1.7 h.

**Step 0 — paperwork, 0 GPU.** Place the result page with: the tripped row (§1.2), the direction of the commit asymmetry (§1.6.1), the Engine-arm tripped gap as a known defect (§1.6.2), and the leftover-worktree explanation. Qualify STATE's "tripped worktrees harvested and graded" to Baseline. No deciding decision is marked unconfirmed by this review.

**Step 1 — candidate 1 as parity, 0 GPU (one attended smoke cell if the maintainer wants the re-pin exercised, about 10 min).** As in §2.2, with fixtures both directions and the ledger line naming the offline bound. It is diagnosed (four cells, two tasks), and its effect begins at the end of the run, so the offline bound is valid under R0 §1.4. It also closes backlog item 7 of the seven rulings.

**Step 2 — the light path, a product decision; if yes, scope it so the medium win cannot be touched.** Judgment on worth: the floor negative is 5.2× on guard-prefixes by total ÷ delivered (38,497 vs 23,888) and 15 min against 3.4 min of wall clock per pass (EB1 §1); for a developer "staying at the wheel" small edits are the common case, so the negative will sit beside any release claim until something moves it, and the light path is the only candidate with an effect of the gap's size. It is worth one measurement **only** in this shape:
- **Derive-time only.** The runner extension — the `self_test` tool, the automatic full-suite run on a model `pytest`, *and the finish steer* — is loaded only when the contract declares `test_command` (`satyrn-engine/src/satyrn_engine/attempt.py:787-838`). A light contract therefore needs no runtime change: `derive.py` already carries the medium-class predicate (`:189` onward); a request below it (no created file, at most one produced symbol — guard-prefixes qualifies, depth-3 does, run-record-gate / review-script / preflight-quiet do not) gets a contract without the test lines and without the automatic suite. The seven pinned digests stay unchanged.
- **No-harm on medium tasks without GPU:** a deterministic test that the derived contracts for run-record-gate, review-script and preflight-quiet are byte-identical before and after, plus unchanged runtime digests. That is the whole medium no-harm check; a GPU no-harm run (6 Engine cells, ≈ 1.5 h) is needed only if the light path turns out to need a runtime switch, in which case the finishing claim is at the old pin and says so.
- **Measurement, Engine against Engine, pre-registered:** 12 light-path Engine cells on guard-prefixes against the 12 retained `23a0ef6` cells (`evidence/2026-10-05-eb-cell-read/`), one-sided rank-sum on per-cell output tokens with delivery and total ÷ delivered beside it, stipulated effect 2× (under half the observed gap). About 2 GPU h plus one smoke cell. Rough power (judgment, log-normal on the Engine passes, σ_log ≈ 0.45): ≥ 0.9 at 2×, about 0.5 at 1.5×. The known risk the light path carries: without the steer, the light-path Engine is bare Pi plus confinement and scope, so its delivery on guard-prefixes should land near Baseline's 8 of 12; that is why delivery is reported beside the decider.
- Cost if wrong: about 2 GPU h and a half-day build; if the light path needs runtime changes, add the 1.5 h medium smoke and a re-pin.

**Step 3 — self-test hygiene does not ride along (judgment).** It changes `runner.ts` (a pinned digest), saves wall clock and context, not output tokens (EB2 §4), and bundling it with the light path would confound the one measurement that can attribute the gap. Bundle it later with the next runtime re-pin, measured as a wall-clock secondary only.

**Step 4 — the 8 Engine budget cells: diagnosed here, 0 GPU; nothing built.** All 8 pass at the line; the 4 recoverable final source trees pass the hidden suite (`budget-trees/*.receipt.json`; the trees are half-deleted, so strays are unknown — a bound on source correctness, not a verdict); 6 were nudged and ran on, 2 were never nudged because their own tests never went green. A completion gate (stop on green) is a remedy whose effect begins at the green turn, so it is replay-scorable as a prefix; its upper bound on this task is +10 of 36 (8 budget + 2 discarded line passes). Judgment: do not build it now. It is the component release one built from three cells and withdrew; the claim already holds; and the precondition in R0 §2 is a class that dominates the ceiling *set*, which is one task today. Record the diagnosis for the day a second task shows the same class.

**Step 5 — EB and the next claim.** On harness verdicts (not replay), C3's preflight-quiet Baseline delivered 3 of 6 (OK 5: pass 3, fail 2; BUDGET 1), i.e. it is not finishing-bound the way run-record-gate is (0 of 6 and 4 of 6 on two nights, all cells at the edge). Power for Engine 0.67 against Baseline 0.5 is 0.37 at n = 36 (exact enumeration, this review). Judgment: do not spend a deciding read on preflight-quiet; if a second task is wanted at all, gate it with a Baseline-only n = 6 `grade-line` read (≈ 1.7 GPU h) and expect it to say "not finishing-bound". A release can honestly frame one task: the Engine stops where bare Pi does not, on the one medium task measured; capability near parity; cost higher on floor tasks at this pin.

**Where this plan risks instrument work for its own sake:** the Engine-arm tripped harvest fix (park until a reading needs the Engine's pass-at-the-cut); any replay improvement to reconstruct nudge-turn trees (park); the strip-rule sensitivity read for the `rec.json` strays (both arms; park unless a release page wants the "beside" count); re-deriving k on the M5 Max (park); cleaning the leftover worktrees (housekeeping). None of these is on the path from Step 0 to a release.

---

## 4. Rulings, ranked, each with its cost if wrong

1. **The claim holds as written and is a finishing claim.** Add the tripped row and the commit-asymmetry direction to the results page. If wrong: a paragraph.
2. **Candidate 1 is parity; fix by demoting `COMMAND_CHANGED_HEAD` to a receipt field, no HEAD reset, no `git commit` guard, no prompt change.** Offline bound +2/36 on run-record-gate, +1/12 on review-script. If wrong: one engine commit reverted; no cell spent.
3. **Record the Engine-arm tripped gap and the leftover-worktree cause as known defects; build neither now.** If wrong: one instrument piece later.
4. **Light path, if the product wants it, is derive-only, gated by the existing medium predicate, proven harmless to medium tasks by byte-identical contracts and unchanged digests, and measured Engine-against-Engine on guard-prefixes at n = 12 (≈ 2 GPU h) with delivery beside the decider.** If wrong: 2 GPU h and half a day; a runtime switch adds 1.5 h and a re-pin.
5. **Self-test hygiene does not ride along.** If wrong: minutes of wall clock per cell stay.
6. **No completion gate from the 8 budget cells.** If wrong: up to +10/36 delivery stays on the table at this pin.
7. **No deciding read on preflight-quiet; at most a 6-cell Baseline `grade-line` gate (≈ 1.7 GPU h); the release frames one task.** If wrong: a second task's win waits.
8. **Note the pin-coverage gap** (Python modules covered by the commit pin only). If wrong: nothing.

---

## Appendix: recompute

```
# per-cell scan (nudge turn, commits, greens, turns, tokens)
python3 evidence/2026-10-06-eb-replan/scan.py ~/satyrn-runs/2026-10-05-campaign-selfhost-run-record-gate-{a,b,c}
# tails of the discarded cells
python3 evidence/2026-10-06-eb-replan/trace.py ~/satyrn-runs/2026-10-05-campaign-selfhost-run-record-gate-a/engine/selfhost-run-record-gate-20261005-192351-988718 30
# tripped and line verdicts per arm
python3 -c "import json,collections; ..."   # over evidence/2026-10-05-rrg-delivery/grade-line-{a,b,c}.json rows: (arm, code, verdict, tripped_verdict, line_verdict)
# offline grades (diffs and receipts copied into this directory)
uv run --project satyrn-evals satyrn-evals grade selfhost-review-script evidence/2026-10-06-eb-replan/review-recon.diff --receipt evidence/2026-10-06-eb-replan/review-recon.receipt.json
uv run --project satyrn-evals satyrn-evals grade selfhost-run-record-gate evidence/2026-10-06-eb-replan/budget-trees/836120.diff --receipt evidence/2026-10-06-eb-replan/budget-trees/836120.receipt.json   # and 502157, 709608, 939358
```
