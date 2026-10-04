# The R0 sitting — agenda (draft for the maintainer; ruled 2026-10-04, ledger "R0 sitting")

**Drafted 2026-10-04 by an agent (Opus) at the maintainer's request, at phase-c1 `1051d21` (clean tree), read-only. Not approved; nothing here is decided.** The sitting is an attended decision sitting of at most 60 minutes. The maintainer alone decides; this page frames the decisions and prints the inputs. It is not a spec and not a plan for Engine work. C4 plan Task 6 sets the three inputs: C3's signed table (`evidence/2026-10-03-c3-census/`, classified at `0c3ad1f`), C4's verdict (`evidence/2026-10-03-c4-counterfactual/decision.txt`, decision run at `c6f51ba`, committed `4bc9831`), and census design §8 items 1–4 (`docs/superpowers/specs/2026-09-15-release-two-census-design.md`), taken in their fixed order. R0 constraints §1, §2, §3 and §5 bind the sitting. The engine-budget design (`docs/superpowers/specs/2026-10-02-engine-budget-design.md`) is not on this branch. It was not read here.

Suggested time boxes: Item 0 (`verify`) 15 min; §8.1 claim row 5; §8.2 ceiling set 10; §8.3 budget, win rule, power and n 20; R0 §5 questions and held items 5; recording 5.

## Inputs on one page

Per task, never pooled. Pass and class columns are from `<task>/cells.json` and `classes.md` (classifier at `0c3ad1f`, columns signed 2026-10-03). C4 columns are from `table.md`, run 2 (the deciding reading, `c6f51ba`). Denominator: 6 cells per task, and all 36 cells are admitted (`<task>/confinement.json`). Six cells is a small sample, so every rate below is a point estimate from six.

| night | task | shape | pass 32k/48 | pass 48k/72 | signed primaries (6) | adm. | C4 kind | resc. | harm | net | unmeas. | insuff. | decides |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | selfhost-run-record-gate | build | 0 | 4 | finishing 5, budget 1 | 6 | budget-shaped | 3 | 0 | 3 | 1 | no | yes |
| A | selfhost-docs-linter | build | 4 | 5 | pass 4, finishing 1, capability 1 | 6 | floor | 1 | 0 | 1 | 2 | **yes** | yes |
| A | selfhost-preflight-quiet | build | 0 | 3 | finishing 4, capability 1, budget 1 | 6 | budget-shaped | 2 | 0 | 2 | 0 | no | yes |
| B | agentclinic-repair-depth-3 (R2) | repair | 5 | 5 | pass 5, hunting 1 | 6 | floor | 0 | 0 | 0 | 0 | no | yes |
| B | selfhost-cell-loop | build | 0 | 0 | runaway 5, hunting 1 | 6 | budget-shaped | 0 | 0 | 0 | 0 | no | yes |
| B | selfhost-speed-probe | build | 0 | 0 | capability 4, ambiguity 1, runaway 1 | 6 | outside | 0 | 0 | 0 | 0 | no | **no** (D6) |

Run 1, printed beside, gives net 0 on every task and `not-the-lever`. Run 1 never decides (C4 pre-registration §4).

The facts that bear on reading the table:
- **Two wall-clock cuts.** depth-3 `499793` (turn 11) and cell-loop `389181` (turn 12) each sat in a whole-disk search until the 4,800 s backstop. Both stand as named cuts, with primary hunting and capability False (ledger "C3 nights A and B ran"; census page "Ruled at signing" 1).
- **The replay artifact behind docs-linter's two withheld rows.** `classify.py`'s replay skips bash writers. docs-linter `556770` and `007105` created a stray file and later deleted it with bash, so the replayed tree grades `unavailable` where the harness graded pass. Each row carries `fidelity:`, and C4's rule withholds it (run 2 would have called both rows harms). These two rows are the only thing that failed `go`'s condition "no floor task insufficient" (C4 README, "Replay limits"). run-record-gate `688591` is the third such row, a withheld rescue.
- **speed-probe's `ambiguity`.** Five cells fail one hidden test whose expectation the prompt does not state. This was signed as a task defect (census page, ruling 3), and R0 §2 says never to claim against one. The ambiguity column is True on 5 of 6 cells. The primary is ambiguity on only 1, and capability on 4.
- **The root-search harness gap.** Five admitted cells searched from `/` or the temp root, and one ran a sibling cell's interpreter, without being refused or counted. All 36 cells stay admitted by ruling. Admission means observed access only, and the gap is a harness build item after C4 (ledger "C3 root searches").
- **UNCONFIRMED (35c298d); nothing in this sitting may rest on these:** `docs/numbers.md` (Engine 16/24 against Baseline 2/24; AGENTS.md still calls it release two's result), the 2026-09-17 and 2026-09-19 route proofs, and the red-stop replay (ledger entry C4, "KEPT UNCONFIRMED"). The isolated census nights 1–3 and the 2026-09-15 counterfactual runs are SUPERSEDED for building.

## Item 0 — the `verify` question (before §8)

D7's row for `verify` (C4 pre-registration §5, quoted unchanged): "The R0 sitting asks whether a one-task claim is worth a release. On 2026-09-15, power 0.26 at n = 12 was judged too small. If yes, size n first". The row does not open an Engine spec.

**The mismatch, stated.** The row speaks of "a one-task claim", but two budget-shaped tasks qualified: run-record-gate (net 3) and preflight-quiet (net 2). The verdict came through `go`'s third condition, an insufficient floor task (docs-linter), and the row was not written for that path. Its 0.26 is release one's arithmetic (Baseline 0.25, Engine 0.50, n = 12). C4's own arithmetic at n = 12 is 0.93 for run-record-gate and 0.61 for preflight-quiet, with Baseline at 0 of 6 (C4 README "Power"). The row stands as written. Only the maintainer may read "one-task" as "per-task".

**Options:**
- **A. Accept `verify` as pre-registered, answer yes, and size n (§8.3).** The claim is per qualifying task. §8.1 and §8.2 proceed, and §8.3 sizes n before anything else. The Engine spec stays unopened by D7.
- **B. Accept `verify` and answer no.** No finish-on-green claim is made. No document names the next step for this branch. The sitting must name one, for example R0 §5 question 3, or ending release two with the harness and a numbered ceiling (census §2 row 3's release, without its evidence).
- **C. Fix the replay's bash-writer defect and re-read.** The pre-registration allows one decision run (§6), and `decide.py` refuses a second while `decision.txt` exists. §2–§5 do not change after the run. D2 fixes `classify.py` "unchanged", and the skipped writer is a documented limit that D3's fidelity rule already handles. The header's clause "A bug found afterwards is fixed and re-run only with the bug and both results recorded beside each other" therefore fits poorly. A re-read needs a new dated pre-registration or amendment, approved before it runs, and the result is chosen after seeing that these rows alone blocked `go` (D9's reason against post-hoc judgment).
  - Possible outcomes: `go` if at most one of `556770` and `007105` is a real harm. `verify` if both are, because floor harm would be 2. The outcome is not knowable without reading.
  - **The instrument-pieces rule** (AGENTS.md; ROADMAP "two consecutive instrument-only pieces stop the loop"). The recent pieces were C1 (re-cut and records), `f1887da` (an instrument fix whose status as a piece is unruled, ledger "C2 and three C3 decisions ruled"), C2 (a measurement, with the `c9ce8e5` fix inside it), C3 (Task 1's driver and audit fix, then the nights: a measurement) and C4 (`decide.py`, then the read: a measurement). A replay fix now would be one instrument piece after a measurement, so on its own it does not trip the rule.
  - The pieces already queued are also instruments: the root-search gap, the inner-Pi `SATYRN_CONFINEMENT_ROOT` fix and the engine re-pin. Whichever instrument piece comes next after a replay fix would stop the loop. AGENTS.md adds: "If a fix is larger than the measurement it unblocks, stop and ask."

**Drafter's recommendation: A.** The pre-registration fixed this verdict and what it opens. A re-read costs an instrument piece ahead of a queue of instrument pieces, and it can still land on `verify`.

## §8.1 — which row of census design §2's table the census supports

"Build" follows design §4's shape column, with preflight-quiet a build by its authored design (`2026-09-17-release-two-authored-task-design.md`, "Shape: build"). That gives five build tasks. depth-3 is a repair task and not counted. Whether speed-probe, an ambiguous prompt, still counts is unclear; the readings below say where it matters.

- **Row 1** reads: "finishing or ceremony in ≥ 30% of build cells on ≥ 3 tasks, and Baseline within 32k at ≤ 2 of 6".
  - ≥ 30% of 6 means ≥ 2 cells. Finishing column True: run-record-gate 5, preflight-quiet 4, docs-linter 1, cell-loop 0, speed-probe 0. That is 2 tasks.
  - "Ceremony" is no class column. Read broadly, as "a pass state inside the line, then more turns", it counts run-record-gate 5, docs-linter 3, preflight-quiet 4. That is 3 tasks, but docs-linter's 4 of 6 within 32k fails "≤ 2 of 6".
  - Either way, at most 2 tasks meet both clauses. **Not supported.**
- **Row 2** reads: "Baseline stops on its own with a pass by 48k on most build cells".
  - Self-stops with a pass: run-record-gate 4, docs-linter 5, preflight-quiet 3, cell-loop 0, speed-probe 0. Per task, 2 of 5 tasks have more than half.
  - Counted across cells, which the row implies but "nothing pools" forbids: 12 of 30, or 12 of 24 without speed-probe. That is not "most".
  - On run-record-gate, every self-stop is above 32,000 tokens and above turn 48. **Not supported.**
- **Row 3** reads: "capability-bound failures dominate at 48k on valid prompts".
  - Failures at 48k with capability as primary: docs-linter 1 of 1, preflight-quiet 1 of 3, run-record-gate 0 of 2, cell-loop 0 of 6. cell-loop's capability column is True on 5 of its 6 cells, but its signed primary is runaway.
  - Primaries are argued at 32k (design §7), so no signed column reads 48k. speed-probe's prompt is not valid. **Not supported.**
- **Drafter's recommendation: record "none".** What the census shows is the two-task finishing shape that C4's `verify` already carries.

## §8.2 — the ceiling set by the rule as written

The rule: Baseline within 32k at ≤ 2 of 6, and primary classes budget, finishing, runaway or hunting. Information and ambiguity are fixed and re-admitted, or dropped (fixed by census §8.2 and R0 §2).

| task | within 32k | primaries | rule says | C4 run-2 net / admitted |
|---|---|---|---|---|
| run-record-gate | 0/6 | finishing 5, budget 1 | **in** | 3/6 |
| preflight-quiet | 0/6 | finishing 4, budget 1, capability 1 | **in** if "primary classes" means the task's dominant class. Out if every cell's primary must be listed (`274281` is capability) | 2/6 |
| cell-loop | 0/6 | runaway 5, hunting 1 | **in** as written | 0/6: no finish-on-green effect, so R0 §2 ("under-powered by the rule's own test is floor or out") removes it from a finish-on-green comparison. Runaway is a different class, with no offline estimate |
| speed-probe | 0/6 | capability 4, ambiguity 1, runaway 1 | ambiguity, signed a task defect: **fix and re-admit, or drop** | outside |
| docs-linter | 4/6 | pass 4 | **out** (floor) | — |
| depth-3 | 5/6 | pass 5 | **out** (floor) | — |

**Drafter's recommendation:** the ceiling set is run-record-gate and preflight-quiet, with `274281` named as the exception. cell-loop is recorded as in by the rule and out of the finish-on-green comparison by R0 §2. speed-probe is dropped: fixing it means a re-cut and a re-admission night, an instrument piece for a task that holds no finishing evidence.

## §8.3 — comparison budget, win rule, power

**Corrected 2026-10-04, later the same day (ledger "Correction: the Engine development read is 5 of 6 at the line").** The paragraph below rests on the classifier's replay, which drops most bash writes (design read in the ledger). The launcher's own line harvest (`line.diff`, written when a cell crosses the declared line) graded offline: `597439` pass, `534866` pass, `843732` unavailable (a real stray file). With the three cells that ended inside the line on a harness pass, the Engine read at the line is **5 of 6**, not 3 of 6, and the "two cells passed and lost it" finding was a replay artifact. The staged gate opens either way. Power at Engine 5/6 (one-sided Fisher, α = 0.05; n = 6 / 9 / 12 per arm): Baseline 0/6 0.94 / 1.00 / 1.00; 1/6 0.68 / 0.83 / 0.96; 2/6 0.39 / 0.54 / 0.77. The paragraph is kept as written as the record of what was read first.

**Read first: the finishing finding from the staged step 2 read (2026-10-04, engine `6d30479`, ledger "Engine development read on run-record-gate").** Six Engine development cells on run-record-gate, read beside C3's Baseline 0 of 6 and never pooled: 3 of 6 passed inside the 32k/48 line; two more (`597439` at turn 29 and 16,959 tokens; `534866` at turn 22 and 21,702 tokens) reached a passing tree inside the line and lost it by continuing to work, one re-passing at turn 56 and one tripping 48k; one never passed. The `finish_nudged` guard fired once in every cell and stopped none. So the finishing class is now observed in the Engine arm at this pin, and the record's gate for n = 12 opens (3 or more). What it means for this item: the counterfactual's stipulated effect, +3/6 on run-record-gate, is a stop-at-green rule replayed on Baseline cells; the Engine as pinned does not stop at green, and read as it is it scored 3 of 6 where a stop-at-green Engine would have read 5 of 6. The sitting therefore decides which Engine the comparison measures: (a) the Engine as pinned, whose own six-cell rate (3 of 6, a point estimate) is the honest stipulated effect for sizing, not the counterfactual's; or (b) an Engine with finish-on-green, which D7's `verify` row does not open (no Engine spec) and which would need the sitting to answer the verify question first and then fix §8.3's rule before any spec. Under (a) the honest stipulated effect is the Engine's observed 3 of 6; the table's Baseline-0/6 row uses the same 0.50 and is exact, while its 1/6 and 2/6 rows add +3/6 to the Baseline rate and so overstate power for an Engine that stays at 0.50 (the observed rate: 0.43 and 0.15 at n = 12 for Baseline 1/6 and 2/6, recomputed with the same Fisher arithmetic). Under (b) nothing is sized until the spec exists. The drafter recommends the sitting rule (a) or (b) explicitly before reading the table.

**The self-stop distribution** comes from `cells.json` (`self_stop_tokens`, `self_stop_turn`). A cell that tripped the 48k/72 budget or was cut has no self-stop. That leaves the distribution right-censored.

| task | self-stopped / tripped or cut | self-stop tokens min / median / max | self-stop turns | pass-state tokens (n) min / median / max |
|---|---|---|---|---|
| run-record-gate | 4 / 2 tripped | 32,469 / 33,754 / 39,330 | 60, 61, 69, 71 | (6) 11,866 / 15,697 / 30,464 |
| preflight-quiet | 5 / 1 tripped | 32,822 / 39,933 / 44,345 | 40, 47, 53, 60, 64 | (5) 18,287 / 26,261 / 42,253 |
| docs-linter | 6 / 0 | 21,453 / 30,288 / 35,739 | 42, 42, 42, 44, 44, 48 | (3) 13,464 / 24,051 / 24,591 |
| depth-3 | 5 / 1 cut | 2,094 / 4,875 / 8,052 | 7, 11, 12, 12, 14 | (5) 1,162 / 3,920 / 7,202 |
| cell-loop | 5 / 1 cut | 16,955 / 17,485 / 22,847 (all NO_PATCH) | 9, 13, 15, 21, 22 | none |
| speed-probe | 1 / 5 tripped | 16,603 (NO_PATCH) | 4 | none |

What can be determined: on both ceiling tasks, every Baseline self-stop falls after the 32,000-token line, while pass states sit well inside it. That is the finishing shape. On run-record-gate, every self-stop is also past turn 48.

What cannot be determined:
- where the tripped cells would have stopped;
- any Engine stop distribution, since no Engine cell exists on this harness after C4;
- a stipulated effect at any line other than 32k/48, because C4 measured only there.

**Budget options:**
- **(a)** Read at the 32k/48 line with a run budget of 48k/72, as C3 did. R0 §3 allows a run budget past the line, read by one reconstruction per arm. C4's effect applies.
- **(b)** Read at 48k. Baseline would then be 4/6 and 3/6 on the ceiling tasks, with no counterfactual estimate there, so R0 §2 leaves no stipulated effect and the claim cannot be sized.

**Drafter's recommendation: (a).**

**Win rule and power.** The test is one-sided Fisher exact at α = 0.05, per task, as in `evidence/2026-09-15-release-one-outcome/stats.py`.
- Stipulated Engine rate = Baseline rate + C4 run-2 net / admitted, per R0 §2: +3/6 for run-record-gate, +2/6 for preflight-quiet, 0 for cell-loop.
- C3's Baseline rate is 0 of 6 on all three, a point estimate from six cells. Power is therefore also shown at 1/6 and 2/6.
- Engine passes needed to reject at Baseline 0, 1 or 2: 4, 5, 6 of 6; 4, 6, 7 of 12; 5, 6, 8 of 18; 5, 6, 8 of 24. run-record-gate's 1/6 and 2/6 rows are mirror images, so their powers are equal.

| task, Baseline p | n = 6 | n = 12 | n = 18 | n = 24 |
|---|---|---|---|---|
| run-record-gate, 0/6 (Engine 0.50) | 0.34 | 0.93 | 0.98 | 1.00 |
| run-record-gate, 1/6 (0.67) | 0.39 | 0.77 | 0.91 | 0.97 |
| run-record-gate, 2/6 (0.83) | 0.39 | 0.77 | 0.91 | 0.97 |
| preflight-quiet, 0/6 (0.33) | 0.10 | 0.61 | 0.77 | 0.94 |
| preflight-quiet, 1/6 (0.50) | 0.16 | 0.43 | 0.59 | 0.72 |
| preflight-quiet, 2/6 (0.67) | 0.18 | 0.42 | 0.58 | 0.68 |
| cell-loop, 0/6, 1/6, 2/6 (effect 0) | ≤ 0.01 | ≤ 0.03 | ≤ 0.03 | ≤ 0.03 |

**Wall clock, an estimate.** It uses the measured C3 sitting per 6-cell record (census page): run-record-gate 1.82 h and preflight-quiet 1.67 h. The Engine arm is assumed to cost the same, a rough doubling, since no post-C4 Engine cell exists.

Both arms, n = 6 / 12 / 18 / 24 per arm: run-record-gate 3.6 / 7.3 / 10.9 / 14.5 h; preflight-quiet 3.3 / 6.7 / 10.0 / 13.3 h.

Two caps apply. A batch sitting is 720 min (ROADMAP), and `run_record.CAPS["batch"]` caps a record at n ≤ 12 (ledger "C3's remaining decisions ruled", D2). So n = 18 or n = 24 means two records per arm, and n = 24 for one task takes more than one sitting.

**Drafter's recommendation, revised 2026-10-04 at the maintainer's direction ("Proceed with the recommendation. You have the GPU"), a staged order:**
1. **Hold the sitting with no new runs.** Item 0, §8.1 and §8.2 need no GPU.
2. **If the claim is worth a release, one cheap development read first:** six Engine cells on run-record-gate at the re-pinned engine (confinement root fix in), purpose `development`, never a deciding record, about 2 GPU hours. C3's Baseline 0 of 6 is the informal comparison. It also gives EB its first confinement-grade cost numbers on a medium task.
3. **That read gates the powered run.** Engine 0 or 1 of 6 inside the line: the claim is dead at this model and budget, and the 7.3 hours are saved. Engine 3 or more of 6: n = 12 per arm with run-record-gate deciding (power 0.77 to 0.93, about 7.3 GPU hours), preflight-quiet at the same n as a declared per-task secondary (power 0.42 to 0.61, printed, never pooled). Engine 2 of 6: the maintainer rules.
The power table assumes the Engine realises the full replayed effect; the Engine is not Baseline plus a stop rule (EB0: the Engine spends more output tokens than Baseline on small tasks, which counts against the 32k line), so the powers shown are upper bounds. The stipulated effects come from six cells.

## R0 §5's four questions, as the evidence stands

1. **Is finishing dominant on build tasks?** On 2 of 5 build tasks: run-record-gate (5/6 primary) and preflight-quiet (4/6). It is not dominant on docs-linter, cell-loop or speed-probe (C3 page, class counts). Stopping at green scores run-2 net +3/6 and +2/6 there, 0 on cell-loop, and +1 with 2 unmeasured on docs-linter. Run 1 scores 0 everywhere (C4 `table.md`).
2. **New ceiling candidates?** Not answerable from C3/C4, which name no new candidate. The existing two carry validity blocks measured on the nested bases and carried over at the C1 re-cut (ledger C1).
3. **Is 9B the right model?** Not answerable from C3/C4: no other model or budget ran. cell-loop's runaway and speed-probe's capability are inputs, not an answer.
4. **Smallest claim, and is it worth a release?** The smallest supported claim is outcome within 32k on run-record-gate alone, at about n = 12 (§8.3). Whether it is worth a release is Item 0, the maintainer's.

## Held — not on this agenda

- **§8.4, the Engine remediation list: held.** Under `verify`, the sitting reaches §8.4 only if the maintainer first answers yes to Item 0 and §8.3 fixes a rule and its power. Even then, D7 opens no Engine spec.
- An Engine spec of any kind; EB2, which needs offline estimates on EB0 cells and follows this sitting's rule.
- The engine re-pin and the inner-Pi `SATYRN_CONFINEMENT_ROOT` fix, both before the first post-C4 Engine read; the root-search harness gap, a build item after C4.
- `derive-new-top-level-module`, which stays parked: this instrument cannot name it.
- Merges. `phase-c1` is unmerged and unpushed.

## What the sitting must produce (a ledger entry, one line each)

- Item 0: A / B / C, the maintainer's words: ________
- Reading of "one-task" (as written / per qualifying task): ________
- §8.1 row (1 / 2 / 3 / none): ________
- §8.2 ceiling set; preflight-quiet `274281` reading; cell-loop; speed-probe fix or drop: ________
- §8.3 line and run budget; win rule; n per arm; deciding task(s); secondaries: ________
- R0 §5 answers recorded as above, or amended: ________
- Instrument-pieces status of `f1887da`, still unruled: ________

**Next document, by Item 0's outcome:**
- **A:** a dated comparison pre-registration fixing §8.3's line, rule, n and per-task tasks, written before any Engine cell. §8.4 and the Engine spec stay held until the maintainer releases them.
- **B:** the document the sitting names, since none is fixed.
- **C:** a dated amendment to the C4 pre-registration, for the replay fix and one re-read, approved before it runs. A second R0 sitting follows.

```bash
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals   # read-only recompute of every number above
uv run python -c "from math import comb;F=lambda a,b,n:sum(comb(n,x)*comb(n,a+b-x) for x in range(a,min(a+b,n)+1) if a+b-x<=n)/comb(2*n,a+b);B=lambda k,n,p:comb(n,k)*p**k*(1-p)**(n-k);P=lambda pb,pe,n:sum(B(b,n,pb)*B(a,n,pe) for b in range(n+1) for a in range(n+1) if F(a,b,n)<=0.05);[print(t,k,[round(P(k/6,min(1,k/6+e),n),2) for n in (6,12,18,24)]) for t,e in (('rrg',3/6),('pq',2/6),('cl',0)) for k in (0,1,2)]"
uv run python -c "import json,statistics as s;[print(t,len(c),sum(x['actual_32k'] for x in c),sum(bool(x['actual_48k']) for x in c),'selfstop',len(v),(min(v),s.median(v),max(v)) if v else '-',[x['self_stop_turn'] for x in c if x['self_stop_turn']]) for t in 'run-record-gate docs-linter preflight-quiet cell-loop speed-probe'.split() for c in [json.load(open(f'evidence/2026-10-03-c3-census/selfhost-{t}/cells.json'))['cells']] for v in [[x['self_stop_tokens'] for x in c if x['self_stop_tokens']]]]"
```
