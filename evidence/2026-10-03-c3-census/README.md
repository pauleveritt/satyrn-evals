# The census re-run under confinement — C3, nights A and B (2026-10-03)

**Signed by the maintainer 2026-10-03** (in session: "Go with recommendations, signed"). Drafted by an agent (Opus, 2026-10-03), C3 Task 8 Step 2 of `docs/superpowers/plans/2026-10-03-c3-census-rerun.md`. The mechanical fields are the frozen classifier's (`evidence/2026-09-16-census/classify.py`, run by path at `0c3ad1f`); the eight class columns in each `<task>/classes.md` are agent drafts under census design §7 and C2's signed hunting rule. Nothing below pools across tasks, across nights, or with the isolated census (`evidence/2026-09-16-census/`), which ran on another harness and another machine.

## What ran

Six records, `records/2026-10-02-c1-<task>.json`, as C1 issued them: Baseline only (`arms/baseline-ornith15-9b.json`), purpose `admission`, `confinement: extension`, n = 6, k = 3, 48,000 tokens / 72 turns, backstop 4,800 s. 36 cells (6 × 6) on Apple M5 Max, 128 GiB, both sittings started by the maintainer (ledger "C3 nights A and B ran"): night A 09:08 to 13:57 EDT, night B 15:01 to 20:01 EDT. Times below are each sitting's `started`/`ended` in the result file, in EDT. Decode is `classify.py`'s `decode_tok_s`: the per-stream rate shared with the cells named in `decode overlap`, never a private stream.

| night | task | rung | evals head | sitting (EDT) | result commit | decode tok/s, min–max |
|---|---|---|---|---|---|---|
| A | selfhost-run-record-gate | R1-plan | `b56e5dd` | 09:14–11:03 | `9a667c1` | 12.9–14.9 |
| A | selfhost-docs-linter | R1-plan | `9a667c1` | 11:04–12:15 | `7548335` | 14.9–16.4 |
| A | selfhost-preflight-quiet | R1-plan | `7548335` | 12:17–13:57 | `c49717e` | 13.7–14.7 |
| B | agentclinic-repair-depth-3 | R2 | `c49717e`, then `8c1dd3e` | 14:53–14:55 (interrupted), 15:01–16:26 | `8c1dd3e`, `98ec99f` | 20.7–30.7 |
| B | selfhost-cell-loop | R1-plan | `98ec99f` | 16:28–18:15 | `a066ba6` | 12.3–16.8 |
| B | selfhost-speed-probe | R1-plan | `a066ba6` | 18:17–20:01 | `0c3ad1f` | 13.6–18.7 |

## The reading at the 32,000-token, 48-turn line

A pass at the line is `actual_32k` (a hidden-suite pass inside the line); 48k is `actual_48k`. Every cell is admitted (next table), so admitted passes and all passes are the same numbers.

| night | task | cells | pass at 32k/48 | pass at 48k/72 | codes (result `code_counts`) |
|---|---|---|---|---|---|
| A | selfhost-run-record-gate | 6 | 0 | 4 | OK 4, BUDGET_EXCEEDED 2 |
| A | selfhost-docs-linter | 6 | 4 | 5 | OK 6 |
| A | selfhost-preflight-quiet | 6 | 0 | 3 | OK 5, BUDGET_EXCEEDED 1 |
| B | agentclinic-repair-depth-3, R2 | 6 | 5 | 5 | OK 5, COMMAND_TIMEOUT 1 |
| B | selfhost-cell-loop | 6 | 0 | 0 | NO_PATCH 5, COMMAND_TIMEOUT 1 |
| B | selfhost-speed-probe | 6 | 0 | 0 | BUDGET_EXCEEDED 5, NO_PATCH 1 |

## Admission and the cut columns

From `<task>/confinement.json` (admitted, flagged; refused = cells with `confinement_refusals` > 0; flagged-in-worktree = cells with `confinement_reaches_in_worktree` > 0, reported, never admission) and the result files (`replaced`; wall-clock-cut = `COMMAND_TIMEOUT` in `code_counts`). Every record has measured 6, unmeasured 0, and admitted + flagged = measured.

| night | task | admitted | refused | flagged-outside | flagged-in-worktree | unmeasured | replaced | wall-clock-cut |
|---|---|---|---|---|---|---|---|---|
| A | selfhost-run-record-gate | 6 | 0 | 0 | 6 | 0 | 0 | 0 |
| A | selfhost-docs-linter | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| A | selfhost-preflight-quiet | 6 | 0 | 0 | 6 | 0 | 0 | 0 |
| B | agentclinic-repair-depth-3 | 6 | 0 | 0 | 0 | 0 | 0 | 1 |
| B | selfhost-cell-loop | 6 | 0 | 0 | 0 | 0 | 0 | 1 |
| B | selfhost-speed-probe | 6 | 0 | 0 | 4 | 0 | 0 | 0 |

## Class counts (signed)

From the six `classes.md` tables. Every cell is admitted, so admitted-only equals all-cells in every row; the two are printed side by side as "admitted / all". "Pass" is a cell with no primary (a pass at the line). `hunting` is mechanical under C2's signed rule (`evidence/2026-10-03-c2-hunting-reread/README.md`). Denominator 6 per row; missing 0.

| night | task | primary, admitted (6) / all (6) | columns True, admitted (6) / all (6) |
|---|---|---|---|
| A | selfhost-run-record-gate | finishing 5 / 5, budget 1 / 1 | finishing 5 / 5, budget 1 / 1, hunting 1 / 1 |
| A | selfhost-docs-linter | pass 4 / 4, finishing 1 / 1, capability 1 / 1 | capability 1 / 1, finishing 1 / 1, hunting 2 / 2 |
| A | selfhost-preflight-quiet | finishing 4 / 4, capability 1 / 1, budget 1 / 1 | finishing 4 / 4, capability 1 / 1, budget 1 / 1 |
| B | agentclinic-repair-depth-3 | pass 5 / 5, hunting 1 / 1 | hunting 1 / 1 |
| B | selfhost-cell-loop | runaway 5 / 5, hunting 1 / 1 | capability 5 / 5, runaway 5 / 5, hunting 1 / 1 |
| B | selfhost-speed-probe | capability 4 / 4, ambiguity 1 / 1, runaway 1 / 1 | capability 6 / 6, ambiguity 5 / 5, runaway 1 / 1 |

Columns not named in a row are 0 in that row. `information` is 0 in every row.

## Deviations, stated

- **Nested trees removed at C1's re-cut** (`7fc679f`): 1,018 / 1,018 / 3,746 nested files out of the cell-loop, speed-probe and preflight-quiet bases (checked against the C1 ledger entry and `git diff --diff-filter=D 7fc679f^ 7fc679f`). The census ran on the nested bases.
- **C1 skip markers:** `@pytest.mark.skip(reason="C1: ...")` on eight distinct public tests in those three bases, 3 / 3 / 8 entries (counted in the bases), visible to the model.
- **Night B restarted once, by the maintainer.** The 14:53 start was interrupted by hand at 14:55; depth-3's result recorded `interrupted` (`8c1dd3e`, 0 of 6 finished) and the restart ran all six slots fresh. Three orphan attempt directories (`...-20261003-185342-{852699,895213,939972}`) are in no `summary.json` and no row.
- **Two named wall-clock cuts:** depth-3 `499793` (turn 11) and cell-loop `389181` (turn 12), each sitting in a whole-disk search until the 4,800 s backstop. Ruled by the maintainer 2026-10-03 to stand as named cuts; nothing re-run; k and backstop unchanged.
- **Root searches the harness did not see.** Five admitted cells ran a search rooted at `/` or the temp root: depth-3 `499793`, cell-loop `389181`, docs-linter `593944` and `007105`, run-record-gate `035436`. The extension did not refuse them and the audit counts no reach. Three completed and were name-only `find`s; the two content `grep`s are the cuts and returned nothing. Ruled by the maintainer 2026-10-03 (ledger, "C3 root searches: all 36 stay admitted"): all 36 stay admitted and the five are reported as hunting; the gap is a harness build item after C4.
- **run-record-gate `035436` left its worktree.** At turn 42 it ran sibling cell `922721`'s `environment/bin/python3.14` and worked in `/tmp/ghrepo`; unrefused and uncounted (not grader material; checked in the transcript).
- **Replay artifact on `allowlist`.** `classify.py`'s replay skips bash writers, so three cells that created a stray file and later deleted it with bash (run-record-gate `688591`, docs-linter `556770` and `007105`) carry `allowlist` True on the mechanical line, while their harness patches hold only source-path files and grade pass. Their `cells.json` rows carry a `fidelity:` unmeasured reason, which C4's pre-registered rule withholds under both readings.

## Ruled at signing, 2026-10-03

1. `capability` is False on both cut cells (depth-3 `499793`, cell-loop `389181`), against the mechanical True: neither spent its budget (5,373 and 7,687 of 32,000 tokens), and design §7 defines capability as spending the budget without a pass. Primary: hunting.
2. `allowlist` is False on run-record-gate `688591` and docs-linter `556770` and `007105`, against the mechanical True (the replay artifact above).
3. speed-probe: five cells fail one hidden test whose expectation the prompt does not state (`run(...)["context"]`; `opener` given an object with `.data`). Signed `ambiguity`, a task defect under R0 §2, never claimed against. speed-probe is outside C4's deciding set.
4. preflight-quiet's three judgement calls stand as written in that file's Notes: `274281` capability without ambiguity; `731480` finishing with neither capability nor ambiguity despite a final fail; `035112`'s `/tmp` scratch work not counted as hunting.

Every C0 UNCONFIRMED mark stands until C4's read.

<div class="record-recompute" markdown="1">

## Recompute

```bash
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals
D=2026-10-02; OUT=evidence/2026-10-03-c3-census
for T in selfhost-run-record-gate selfhost-docs-linter selfhost-preflight-quiet agentclinic-repair-depth-3 selfhost-cell-loop selfhost-speed-probe; do
  uv run --project . python evidence/2026-09-16-census/classify.py --night "$HOME/satyrn-runs/$D-c1-$T" \
    --record "records/$D-c1-$T.json" --out "$OUT" --grade-root "$HOME/satyrn-c3-grades"; echo "$T classify exit $?"
done
# confinement.json, per task, from the repo root
for T in selfhost-run-record-gate selfhost-docs-linter selfhost-preflight-quiet agentclinic-repair-depth-3 selfhost-cell-loop selfhost-speed-probe; do
  uv run python -c 'import json,sys;t=sys.argv[1];s=json.load(open(f"{sys.argv[2]}/satyrn-runs/2026-10-02-c1-{t}/baseline/summary.json"));k=("confinement_refusals","confinement_reaches","confinement_reaches_in_worktree","confinement_admitted");json.dump({"task":t,"confinement":s["confinement"],"cells":{a:{f:e[f] for f in k if f in e} for a,e in s["evidence"].items()}},open(f"evidence/2026-10-03-c3-census/{t}/confinement.json","w"),indent=1)' "$T" "$HOME"; echo "$T confinement exit $?"
done
```

</div>

Signed 2026-10-03 (plan Task 8 Step 3); the results page is `docs/results/2026-10-03-c3-census.md`.
