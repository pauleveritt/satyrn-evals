# The finishing counterfactual re-derived on the C3 census — C4 (2026-10-03)

**Unsigned agent draft, 2026-10-03** (Opus), C4 Task 4 Step 1 of `docs/superpowers/plans/2026-10-03-c4-counterfactual.md`; the maintainer signs it (Task 4 Step 2). Stamp of the one decision run, from `decision.txt`: `evals c6f51ba2ddb879bc2200515d238658ae28f463a3 dirty=False argv=['--census', 'evidence/2026-10-03-c3-census', '--c1-date', '2026-10-02']`. Pre-registration `docs/superpowers/specs/2026-10-03-c4-finishing-counterfactual-rederive.md` at `9163fdb`; `decide.py` at `60a29bc`; decision commit `4bc9831` (`decision.txt`, `table.md`). Every number below is recomputed from `table.md` and the six `evidence/2026-10-03-c3-census/<task>/cells.json`; the recomputation agrees with `table.md` in every cell. Nothing pools across tasks, nights, the isolated census, the 2026-09-15 counterfactual, EB0 or any Engine cell.

## Verdict

- **Deciding reading, run 2 (std replay, fidelity-withheld): `verify`.**
- **Beside, run 1: `not-the-lever`.** The two readings disagree; run 1 never decides (pre-registration §4).

**Why run 2 gives `verify`, from `decide()` and the table.** Kinds come from admitted cells and `actual_32k` (§5, D5): run-record-gate, preflight-quiet and cell-loop each have 6 of 6 admitted cells not passing at the 32,000 / 48 line, so they are budget-shaped (≥ 3 admitted, ≥ ⌈6/2⌉ = 3 not-pass); docs-linter (2 of 6 not-pass) and depth-3 (1 of 6) are floor. Two budget-shaped tasks qualify: run-record-gate (net 3, 1 unmeasured, not insufficient) and preflight-quiet (net 2, 0 unmeasured); cell-loop has net 0. Floor harm is 0 (< 2). The third condition of `go`, "no floor task insufficient", fails: docs-linter has 2 unmeasured admitted cells (556770, 007105), and more than 1 is `insufficient`. Step 1 (`go`) therefore fails on that condition alone, and step 2 (`verify`: at least one task qualifies) applies.

**Why run 1 gives `not-the-lever`.** Run 1 withholds a cell on any `unmeasured` reason (§4, 7.4). Every run-2 rescue in a budget-shaped task (run-record-gate 922721, 427312, 547893; preflight-quiet 343289, 420082) carries an `unverified-rescue` reason, so each is unmeasured under run 1; and `classify.py`'s own run 1 column records change `none` on all 36 cells. Every budget-shaped task's run 1 net is 0, so no task qualifies and none, sufficient or not, has net ≥ 1: step 3 applies, and 7.1's gap (step 4) does not arise.

## Per task, both readings (`table.md`)

Admitted is the denominator (all 36 cells admitted: refusals 0, reaches 0; C3 census page). speed-probe is computed and never enters the verdict (D6).

| reading | task | admitted | not-pass@line | kind | rescues | harms | net | unmeasured | insufficient |
|---|---|---|---|---|---|---|---|---|---|
| run2 | selfhost-run-record-gate | 6 | 6 | budget-shaped | 3 | 0 | 3 | 1 | False |
| run2 | selfhost-docs-linter | 6 | 2 | floor | 1 | 0 | 1 | 2 | True |
| run2 | selfhost-preflight-quiet | 6 | 6 | budget-shaped | 2 | 0 | 2 | 0 | False |
| run2 | agentclinic-repair-depth-3 | 6 | 1 | floor | 0 | 0 | 0 | 0 | False |
| run2 | selfhost-cell-loop | 6 | 6 | budget-shaped | 0 | 0 | 0 | 0 | False |
| run2 | selfhost-speed-probe | 6 | 6 | outside | 0 | 0 | 0 | 0 | False |
| run1 | selfhost-run-record-gate | 6 | 6 | budget-shaped | 0 | 0 | 0 | 5 | True |
| run1 | selfhost-docs-linter | 6 | 2 | floor | 0 | 0 | 0 | 4 | True |
| run1 | selfhost-preflight-quiet | 6 | 6 | budget-shaped | 0 | 0 | 0 | 2 | True |
| run1 | agentclinic-repair-depth-3 | 6 | 1 | floor | 0 | 0 | 0 | 0 | False |
| run1 | selfhost-cell-loop | 6 | 6 | budget-shaped | 0 | 0 | 0 | 0 | False |
| run1 | selfhost-speed-probe | 6 | 6 | outside | 0 | 0 | 0 | 0 | False |

## The two beside counts (§2; never decide)

Flagged after trigger: 0 in every task. Flagged only by non-protected refusals: 0 in every task. Both counts are defined over flagged cells, and C3 has none: 36 of 36 admitted, 0 flagged, 0 unmeasured-by-confinement, 0 replaced. A zero here is therefore true by construction. It says the denominator lost no cell to a post-trigger leak or a scratch refusal; it says nothing about how often either would occur.

## Every unmeasured cell, with its reason

Withheld under **both** readings (a `fidelity:` or `raised:` reason; no row has `raised` set):

| task | attempt | run 2 change withheld | `unmeasured` reasons (`cells.json`) |
|---|---|---|---|
| selfhost-run-record-gate | 688591 | rescue | `fidelity: harness pass, replay unavailable`; `unverified-rescue: bash at turns 3, 5, 6, 23` |
| selfhost-docs-linter | 556770 | harm | `fidelity: harness pass, replay unavailable`; `skipped bash writer at turn 14` |
| selfhost-docs-linter | 007105 | harm | `fidelity: harness pass, replay unavailable`; `skipped bash writer at turn 17` |

Withheld under **run 1 only** (other reasons; run 2 counts the change shown):

| task | attempt | run 2 change | `unmeasured` reasons (`cells.json`) |
|---|---|---|---|
| selfhost-run-record-gate | 922721 | rescue | `unverified-rescue: bash at turns 7, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28` |
| selfhost-run-record-gate | 977901 | none | `skipped bash writer at turn 40` |
| selfhost-run-record-gate | 427312 | rescue | `unverified-rescue: bash at turns 21, 30, 31, 32, 33, 34, 35` |
| selfhost-run-record-gate | 547893 | rescue | `unverified-rescue: bash at turns 10, 29` |
| selfhost-docs-linter | 646828 | rescue | `unverified-rescue: bash at turns 2, 6, 7, 8, 16, 17, 18` |
| selfhost-docs-linter | 708458 | none | `skipped bash writer at turn 29`; `skipped bash writer at turn 30` |
| selfhost-preflight-quiet | 343289 | rescue | `unverified-rescue: bash at turns 1, 3, 6, 9, 12` |
| selfhost-preflight-quiet | 420082 | rescue | `unverified-rescue: bash at turns 4, 5, 7, 9` |

Counts per task (run 2 / run 1): run-record-gate 1 / 5, docs-linter 2 / 4, preflight-quiet 0 / 2, depth-3 0 / 0, cell-loop 0 / 0, speed-probe 0 / 0; equal to `table.md`'s `unmeasured` column. Each unmeasured cell counts as no change (§4).

## What `verify` opens (D7, pre-registration §5, as written)

| verdict | opens | does not open |
|---|---|---|
| **verify** | The R0 sitting asks whether a one-task claim is worth a release. On 2026-09-15, power 0.26 at n = 12 was judged too small. If yes, size n first | Engine spec |

This `verify` came through D7's condition "an insufficient floor task", with two tasks qualifying; the row is quoted unchanged. Under any verdict (§5): EB2 remedies need offline estimates on EB0 cells; the Engine's inner-Pi `SATYRN_CONFINEMENT_ROOT` fix lands before the first post-C4 Engine read; `derive-new-top-level-module` stays parked, since this instrument scores a stop rule on Baseline cells and cannot name a derive remedy.

## Disclosure (pre-registration §7) and what was read since

§7 stands as written: before drafting the rule, its author knew the isolated census's finishing-bound reading of the medium builds (UNCONFIRMED, `35c298d`), the 2026-09-15 run 2 Verify (docs-linter net +1, isolation-era release-one cells), C2's hunting and in-worktree reach counts, and EB0's aggregate counts; none is a C3 tally. Read since the rule was committed (`9163fdb`, before C3's freeze at `60a29bc`), and before the decision run: C3's `cells.json`, class columns and census page, signed at `0cb1ffe` (20:38 EDT) and closed out at `c6f51ba`, the commit the decision ran at; the decision commit is 21:39 EDT. That is the plan's order (C3 Task 8 signs, then C4 Task 3 runs). `decide.py` reads only `actual_32k`, `raised`, `unmeasured`, `run1`/`run2` change and `own_green_turn` from `cells.json`, plus admission and transcripts; C3's class columns, flags and `hunting` did not enter the verdict (§6).

## Replay limits

- **Std replay only.** Run 2 is the hidden-suite verdict of the tree at the end of the trigger turn as `classify.py` replays it; the `ext` replay of the 2026-09-15 run 2 is not carried over (D2; `_snapshot_replay`'s docstring).
- **Skipped bash writers.** The replay does not execute bash commands that write. Run 1 withholds a cell with a skipped writer before the trigger, and 7.4 withholds a rescue unless every bash command to the trigger replayed or is provably read-only. Run 2 withholds neither (D3).
- **The three `fidelity:` rows** (run-record-gate `688591`, docs-linter `556770`, `007105`) come from a replay artifact recorded in the ledger ("C3 root searches", instrument note): each cell created a stray file and later deleted it with bash, the replay skipped the delete, and the replayed final tree grades `unavailable` where the harness graded pass (the reason text); the harness patches hold only source-path files. How they bear, mechanically: run 2's column calls 688591 a rescue and 556770 and 007105 harms. Withheld, run-record-gate is net 3 with 1 unmeasured (still sufficient), and docs-linter is rescues 1, harms 0, net 1, unmeasured 2, so `insufficient`; floor harm is 0. The one condition of `go` that failed, "no floor task insufficient", failed on exactly these two docs-linter rows.
- **Admission is observed access only.** The extension neither refuses nor counts a bash search rooted above the worktree; five admitted cells ran one (C3 census page, "Root searches"). All 36 stay admitted by the maintainer's ruling.

## Power (an input to §8.3, not a rule)

The plan names no candidate n for the R0 sitting. The 2026-09-15 documents name n = 12 per arm (`evidence/2026-09-15-release-one-outcome/stats.py`: one-sided Fisher, α = 0.05, no futility look), so the table is at n = 12. Baseline's C3 rate at the line is 0 of 6 on both qualifying tasks; the stipulated Engine rate is that rate plus C4's per-task net / admitted (R0 §2): run-record-gate 0 + 3/6 = 0.50, preflight-quiet 0 + 2/6 ≈ 0.33. With Baseline 0 of 12, rejection needs Engine ≥ 4 of 12.

| task | Baseline p (C3, 0 of 6) | stipulated Engine p | power at n = 12 |
|---|---|---|---|
| selfhost-run-record-gate | 0.00 | 0.50 | 0.93 |
| selfhost-preflight-quiet | 0.00 | 0.33 | 0.61 |

The same arithmetic reproduces 2026-09-15's 0.26 (Baseline 0.25, Engine 0.50). A Baseline rate of 0 is a point estimate from 6 cells; any non-zero rate lowers both powers. Command (scipy is not a project dependency, so an exact hypergeometric sum):

```bash
uv run python -c "from math import comb;F=lambda a,b,n:sum(comb(n,x)*comb(n,a+b-x) for x in range(a,min(a+b,n)+1) if a+b-x<=n)/comb(2*n,a+b);B=lambda k,n,p:comb(n,k)*p**k*(1-p)**(n-k);P=lambda pb,pe,n:sum(B(b,n,pb)*B(a,n,pe) for b in range(n+1) for a in range(n+1) if F(a,b,n)<=0.05);print([round(P(0,e,12),2) for e in (3/6,2/6)],round(P(0.25,0.5,12),2))"
# [0.93, 0.61] 0.26
```

<div class="record-recompute" markdown="1">

## Recompute

`decide.py` refuses (exit 2) while `decision.txt` exists, so the recompute runs in a scratch clone with it removed. Not run by the drafting agent (the pre-registration allows one run, and it is made). The clone's stamp will read `4bc9831` and `dirty=True` (the deleted file sits under `evidence/`), so compare from line 2.

```bash
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals
S=$(mktemp -d); git clone -q . "$S/evals" && cd "$S/evals" && git checkout -q 4bc9831
rm evidence/2026-10-03-c4-counterfactual/decision.txt
uv run --project . python evidence/2026-10-03-c4-counterfactual/decide.py --census evidence/2026-10-03-c3-census --c1-date 2026-10-02; echo "exit $?"
for f in decision.txt table.md; do diff <(tail -n +2 evidence/2026-10-03-c4-counterfactual/$f) <(git show 4bc9831:evidence/2026-10-03-c4-counterfactual/$f | tail -n +2); echo "$f diff exit $?"; done
```

</div>

Unsigned agent draft; the maintainer signs it (Task 4 Step 2) and writes `docs/results/2026-10-03-c4-counterfactual.md`. Per the plan's Task 5 template (the ledger is the maintainer's): SUPERSEDED for building are the isolated census's counterfactual columns (nights 1–3) and `evidence/2026-09-15-finishing-counterfactual/` runs 1 and 2; KEPT UNCONFIRMED (`35c298d`) are `docs/numbers.md` (Engine 16/24 vs Baseline 2/24), the route proofs of 2026-09-17 and 2026-09-19, and the red-stop replay, which need Engine cells under confinement after the inner-Pi fix.
