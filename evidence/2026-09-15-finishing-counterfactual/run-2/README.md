# Run 2 — the corrected reading, recorded beside run 1

Dated 2026-09-15, under the pre-registration's own clause: "a bug found
afterwards is fixed and re-run only with the bug and both results recorded
beside each other"
(`docs/superpowers/specs/2026-09-15-release-two-finishing-counterfactual.md`).
Run 1's outputs are untouched: `../cells.json`, `../table.md`,
`../decision.txt`, `../README.md`, from the reviewed script at `07e1142`.

## Both results

| | run 1 (pre-registered rules, committed) | run 2 (deep review, by inspection plus segment-wise replay) |
|---|---|---|
| decision | `not-the-lever` | **Verify on clean tasks** (section 5 as amended by 7.1) |
| docs-linter | 0 rescues, 1 unmeasured | **net +1** (970283) |
| run-record-gate | 0 rescues, 2 unmeasured, insufficient | 0 rescues, 0 unmeasured |
| depth-3 | 0 rescues | 0 rescues |
| floor harm | 0, two tasks insufficient | 0, no task insufficient |
| fidelity | 11 of 14 graded cells | 14 of 14 |
| unmeasured | 8 of 24 | 0 of 24 |

The honest verdict is therefore **not** "finishing is not the lever". It is
"undetermined by the pre-registered rules; one rescue by inspection, which is
**Verify**" — and either way the class is too small to build a release on
(section "What it does not change").

## The bugs, all in the rules' conservatism

Run 1 applied the pre-registered rules correctly; the review audited the
instrument, re-derived every trigger independently (`audit.py`, `audit.md`) and
found that three rules, each recorded before the run, together made a rescue
on a self-hosted task almost impossible to count:

1. **Plan Ruling 11's write heuristic.** A bash command containing
   `write_text(` and naming a source path counted as a possible writer. In
   970283 that was a `write_text` into `mkdtemp()`, and two python patches of
   `tools/lint_docs.py` that the *same command* restored from a backup two
   lines later (turn 40's pytest output shows none of the inserted `DBG`
   lines).
2. **A BSD `sed -i` error counted as a skipped write.** On macOS
   `sed -i 's/…/g' file` fails with "undefined label"; nothing was written in
   519278 (turns 29–30) or 688090 (turn 15).
3. **Amendment 7.4's read-only list was too strict.** It rejects
   `2>/dev/null`, `od`, `xxd`, `md5`, `python3 -c` and `for` loops. Of 151
   unverified commands through the triggers, 30 fail on `2>/dev/null` alone.
   All 21 commands that withheld 970283's rescue are read-only by inspection;
   so are the 11 that withheld the Engine cell 859943.

**The fix, as a method rather than a patch** (`trajectory.py`, mode `ext`):
replay python heredoc read-modify-write bodies and `cp`/`mv` segments in
order; treat a BSD `sed -i` error as a non-write; accept `2>/dev/null`. Its
trees agree with run 1's on every graded turn of 970283 and repair the three
guard-prefixes fidelity misses, which the harness graded pass.

## What run 2 measures

- **docs-linter 970283:** hidden-suite pass from turn 39 (27,773 output
  tokens) to the end; own-green at turn 40 (27,892). Actual outcome
  `BUDGET_EXCEEDED`. One rescue.
- **The other triggered budget-shaped cells are not finishing failures.**
  519278's green grades `unavailable` (it edited `errors.py`, outside
  `source_paths`); 028222's green fails the five `load_run_record` refusal
  tests; 147562's green is `unavailable` for `pyproject.toml` and fails one
  test when filtered. These are release one's named task defects, not a
  stopping problem.
- **Harm is zero under every trigger rule tried.** Across 43 cells graded at
  every turn, no cell that reached a pass-state ever left it
  (`trajectory.md`).
- **Alternative triggers change nothing** (`triggers.md`): whole-suite green,
  green after one or two non-editing turns, re-confirmed green, last green
  within budget, and an oracle "first hidden-pass turn" all find the same
  single decision rescue.
- **Engine cell 859943** (docs-linter route proof) also passed at its trigger
  and is a rescue by inspection; it sits outside the decision set.

## What it does not change

Finishing is real but small: 2 of 5 docs-linter cells across both arms
reached a within-budget pass-state and overran, plus 511653 on the
since-fixed run-record-gate prompt. It is Engine-addressable, but only on the
one task whose Baseline already passes 1 of 4; at n = 12 with Baseline 0.25
and Engine 0.5 the power is 0.26. depth-3 and run-record-gate fail at every
turn for information and ambiguity reasons. No Engine-addressable class
dominates the current ceiling set.

**Consequence taken by the maintainer, 2026-09-15:** do not build a
finish-on-green Engine on this evidence, and do not run a GPU night on the
current ceiling set. Release two ships the Engine as a product with honest
before-and-after numbers and no ceiling claim (`ROADMAP.md`).

**One release-one item resolved:** on 1,932 live completions the probe rule
holds — k = 1 gives 41 tok/s per stream, k = 3 about 89 tok/s total, 2.2×
(`q3stats.md`). The outcome page's open item 7 is answered: k = 3 was sound.

<div class="record-recompute" markdown="1">

## Recompute

```bash
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals/evidence/2026-09-15-finishing-counterfactual/run-2
python3 audit.py        # re-derive every trigger from the transcripts -> audit.md
python3 trajectory.py   # replay std and ext, grade every mutation turn -> trajectory.md
python3 triggers.py     # alternative trigger rules -> triggers.md
python3 q3stats.py      # token, turn, thinking and decode statistics -> q3stats.md
```

Large outputs (`audit.json`, `trajectory.json`, `serverlog_sept.json`,
`grades/`) are git-ignored; the scripts regenerate them. The full review is
`fable-review.md`.

</div>
