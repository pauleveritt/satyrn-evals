# What the head-tolerance fix would have delivered on the four discarded cells

Offline bound for ruling 2 of the ledger entry "2026-10-06 — Review of the comparison and EB re-plan: eight rulings". Reconstruction-grade, never deciding, never pooled with or read into the decided run-record-gate comparison (which stays at engine `23a0ef6`).

**The fix** (engine branch `eb-head-tolerance`, commits `2d308a5`, `b615477` and `b60bf2b`, reviewed; not yet merged or pinned): when the model's command leaves the isolated worktree on a **detached HEAD that moved** (it ran `git commit`), `deliver` keeps the candidate, built as before from the worktree's tree with `base_commit` as its only parent, and records `head_moved: true` on the receipt. An **attached HEAD** (a branch the model created, whose ref lands in the source repository) is still refused as `COMMAND_CHANGED_HEAD`. The maintainer confirmed that narrowing on 2026-10-06 ("Confirm the narrowing"). Before the fix, both cases were discarded.

**The four cells.** All four committed on a detached HEAD; none ran `git switch`, `git checkout -b` or `git branch` (transcripts checked 2026-10-06), so the fix keeps all four candidates. Grades are from the review's §2.1 (`README.md` in this directory).

| cell | task, night | commit turn | tree the fixed Engine delivers | grade | adds |
|---|---|---|---|---|---|
| `192351-988718` | run-record-gate, campaign a | t53 | final worktree tree = line tree plus `tests/test_run_record.py` edits (replaced by the hidden overlay) | pass (reconstruction) | +1 |
| `015113-247011` | run-record-gate, campaign b | t23, t24 | same reasoning | pass (reconstruction) | +1 |
| `104033-813847` | run-record-gate, campaign c | t28 | final tree still carries the committed strays `committed.json`, `results/prev.json` | unavailable → not delivered under D2 | +0 |
| `005058-171727` | review-script, `2026-10-04-eb-s1` | t13 | reconstructed from 2 `write`s and 3 `edit`s (`review-recon.diff`) | pass, 6 of 6 hidden tests (`review-recon.receipt.json`) | +1 |

**Bound, denominators stated:**
- run-record-gate: at most **+2 of 36** (Engine 24/36 against Baseline 10/36). Not read into the decided claim; the comparison measured the Engine as pinned.
- review-script: **+1 of 12** (Engine 7/12 against Baseline 11/12). The floor cost negative stands: total output tokens ÷ delivered passes 149,080 ÷ 7 = 21,297 against Baseline 13,180.

**What is not measured:** the fixed Engine's behaviour on fresh cells. The fix changes nothing before the model's last turn (its effect begins after the command ends), so the bound is valid offline under R0 §1.4; a smoke cell after the re-pin (plan Task 3, Step 5) exercises the code path, not the rate.
