# C4: would stopping at green have helped? — verify

**Draft for the maintainer to place, 2026-10-03.** The evidence page is [`evidence/2026-10-03-c4-counterfactual/README.md`](../../evidence/2026-10-03-c4-counterfactual/README.md). The rule was pre-registered before any C3 cell existed ([pre-registration](../../docs/superpowers/specs/2026-10-03-c4-finishing-counterfactual-rederive.md), `9163fdb`), the script was built on synthetic data (`60a29bc`), and the one decision run is committed at `4bc9831` (stamp: evals `c6f51ba`, `dirty=False`).

## The question

The C3 census ran 36 Baseline cells under confinement: six tasks, 6 cells each, all 36 admitted. Many cells reached a passing state and kept working. If each cell had stopped at the first turn where its own tests ran green, inside the 32,000-token / 48-turn line, how many passes would that add (rescues) and how many would it break (harms)? Answered offline from the retained cells: no model, no new runs.

## The answer

- **The deciding reading (run 2) says `verify`.**
- **The stricter reading kept beside it (run 1) says `not-the-lever`.** It does not decide.

Per task, run 2, admitted cells as the denominator. Tasks are never added together.

| task | admitted | not passing at the line | kind | rescues | harms | net | unmeasured |
|---|---|---|---|---|---|---|---|
| run-record-gate | 6 | 6 | budget-shaped | 3 | 0 | +3 | 1 |
| docs-linter | 6 | 2 | floor | 1 | 0 | +1 | 2 |
| preflight-quiet | 6 | 6 | budget-shaped | 2 | 0 | +2 | 0 |
| depth-3 | 6 | 1 | floor | 0 | 0 | 0 | 0 |
| cell-loop | 6 | 6 | budget-shaped | 0 | 0 | 0 | 0 |
| speed-probe (outside the decision) | 6 | 6 | — | 0 | 0 | 0 | 0 |

## Why `verify` and not `go`

`go` needed three things: two budget-shaped tasks with net ≥ 1 and at most 1 unmeasured cell; fewer than 2 harms across the floor tasks; and no floor task with more than 1 unmeasured cell. The first two hold: run-record-gate and preflight-quiet qualify, and floor harm is 0. The third fails: docs-linter, a floor task, has 2 unmeasured cells. So the rule falls to `verify`, which needs only one qualifying task.

The two docs-linter cells (`556770`, `007105`) and one run-record-gate cell (`688591`) are withheld because the replay could not reproduce the harness's pass: each cell made a stray file and later deleted it with a shell command, and the replay skips such commands. Run 2's raw column had called the two docs-linter cells harms and the run-record-gate cell a rescue.

## Why the stricter reading says `not-the-lever`

Run 1 withholds any cell carrying an unmeasured reason. Every rescue run 2 counts in a budget-shaped task carries one (`unverified-rescue`: the cell ran shell commands before the green turn that the replay could not prove harmless). With those withheld, no budget-shaped task has a net rescue.

Withheld cells, per task (run 2 / run 1): run-record-gate 1 / 5, docs-linter 2 / 4, preflight-quiet 0 / 2, every other task 0 / 0. The evidence page lists each with its reason.

## What `verify` opens

From the pre-registration's §5 table, unchanged: "The R0 sitting asks whether a one-task claim is worth a release. On 2026-09-15, power 0.26 at n = 12 was judged too small. If yes, size n first." It does not open an Engine spec. (This `verify` arrived with two tasks qualifying; the row is quoted as written.)

## Power, an input to the R0 sitting's §8.3, not a rule

No candidate n is named yet; the 2026-09-15 documents used n = 12 per arm with a one-sided Fisher test at 0.05. Baseline passed 0 of 6 at the line on both qualifying tasks. Taking the stipulated Engine rate as Baseline plus net / admitted:

| task | Baseline | stipulated Engine | power at n = 12 |
|---|---|---|---|
| run-record-gate | 0.00 | 0.50 | 0.93 |
| preflight-quiet | 0.00 | 0.33 | 0.61 |

A Baseline of 0 is a 6-cell point estimate; any non-zero Baseline lowers both numbers.

## Limits

- Run 2 grades the tree at the green turn by a replay that skips shell commands which write files; that is why three cells are withheld.
- Both "beside" counts (flagged cells that leaked only after green; cells flagged only by harmless refusals) are 0, because no C3 cell was flagged at all.
- Confinement sees only access it can observe: five admitted cells ran disk-wide searches the harness neither refused nor counted (C3 census page). All stay admitted by ruling.
- The pre-registration's author knew the isolated census's readings (now superseded); the C3 census page was signed before the decision run, as the plan ordered. Neither entered the rule.

## Recompute

The script runs once and refuses while `decision.txt` exists, so recompute in a scratch clone:

```bash
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals
S=$(mktemp -d); git clone -q . "$S/evals" && cd "$S/evals" && git checkout -q 4bc9831
rm evidence/2026-10-03-c4-counterfactual/decision.txt
uv run --project . python evidence/2026-10-03-c4-counterfactual/decide.py --census evidence/2026-10-03-c3-census --c1-date 2026-10-02; echo "exit $?"
for f in decision.txt table.md; do diff <(tail -n +2 evidence/2026-10-03-c4-counterfactual/$f) <(git show 4bc9831:evidence/2026-10-03-c4-counterfactual/$f | tail -n +2); echo "$f diff exit $?"; done
```

The stamp line differs in the clone (`4bc9831`, `dirty=True`), hence the comparison from line 2. Power: the one-line command is on the evidence page.
