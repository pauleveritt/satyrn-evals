# Baseline development read on run-record-gate, line declared (2026-10-05)

Development, never deciding. This is the read ruled as item 4 of the ledger entry "2026-10-05 — EB after EB2: seven rulings". Record `records/2026-10-05-dev-baseline-selfhost-run-record-gate.json` (`db4b122`), result `d35db18`. Six Baseline cells on `selfhost-run-record-gate` at R1-plan, under `confinement: extension`. Settings: 48,000 tokens and 72 turns, the line declared at 32,000 tokens and 48 turns, k = 3, backstop 4,800 s. Ornith 1.5 9B on oMLX, Apple M5 Max. The sitting ran 09:46–11:13 EDT. The task tree digest (`068f216e…`) is the same as the C3 record's (`records/2026-10-02-c1-selfhost-run-record-gate.json`) and the Engine development read's (`records/2026-10-04-dev-engine-selfhost-run-record-gate.json`).

```
N=2026-10-05-dev-baseline-selfhost-run-record-gate
uv run satyrn-evals grade-line ~/satyrn-runs/$N --record records/$N.json --grade-root <dir outside any Python project> --out grade-line.json
uv run python evidence/2026-10-05-eb-cell-read/read_cells.py ~/satyrn-runs/$N > read.txt
```

`grade-line.json` and `read.txt` here are those two outputs. The sitting completed, with 0 replaced and 0 infrastructure cells, and no wall-clock cut. Admitted 5 of 6: cell `822790` has one confinement refusal, a `write` to `src/satyrn_evals/run_record.py` under a mistyped absolute path. The model shortened the temp-directory name, so the path fell outside the worktree.

## Results

| cell | code | final verdict | crossed the line | line verdict (`grade-line`) | turns | output tokens |
|---|---|---|---|---|---|---|
| `134623-715213` | BUDGET_EXCEEDED | none | turns, at turn 49 | pass | 72 | 35,442 |
| `134623-769808` | BUDGET_EXCEEDED | none | turns, at turn 49 | pass | 72 | 38,574 |
| `134623-822790` | BUDGET_EXCEEDED | none | turns, at turn 49 | pass | 72 | 43,639 |
| `142152-500874` | BUDGET_EXCEEDED | none | turns, at turn 49 | pass | 72 | 34,042 |
| `142526-263969` | BUDGET_EXCEEDED | none | tokens, at turn 44 | pass | 60 | 48,882 |
| `143357-241323` | BUDGET_EXCEEDED | none | turns, at turn 49 | pass | 72 | 38,992 |

- **Pass at the line: 6 of 6**, with 0 excluded. Each harvested `line.diff` passes all 20 hidden tests, and the contamination check is clean. The patches touch `src/satyrn_evals/{cli,run_record}.py` and tests; one also touches `PROVENANCE.md`, which the manifest ignores.
- **Delivered (final verdict `pass`): 0 of 6.** Every cell ran out of budget: five at 72 turns and one at 48,000 tokens. Each reached a passing tree before the line and kept working until the budget cut it off.
- **Under the decider ruled 2026-10-05** (total output tokens ÷ delivered passes), Baseline has no delivered pass, so the figure is undefined. Total output tokens over the six cells: 239,571.

## Beside it, never pooled

- **Engine development read** (`records/2026-10-04-dev-engine-selfhost-run-record-gate.json`, engine `6d30479`, same seven digests as the current pin): pass at the line 5 of 5 with 1 excluded (`grade-line`); delivered 4 of 6, codes OK 5 and BUDGET_EXCEEDED 1 (ledger, "Replay instrument piece landed").
- **C3's Baseline** on the same task tree (`records/2026-10-02-c1-selfhost-run-record-gate.json`, no line declared): delivered 4 of 6, codes OK 4 and BUDGET_EXCEEDED 2. Read from the cells' `attempt.json`, C3's cells ran 60, 61, 69, 71, 72 and 72 turns, with 32,469–45,095 output tokens. Today's ran 60–72 turns, with 34,042–48,882. Both populations work to the edge of the 72-turn budget. "Delivered" separates cells that stopped just under it (C3: 4) from cells that did not (today: 0).

## Why C3's "0 of 6 at the line" is in question

C3 recorded Baseline at 0 of 6 inside the 32k/48 line on this task. That reading came from the classifier's replay, because C3's records declared no line and so harvested no line tree. On 2026-10-04 the replay was ruled diagnostic only: it drops bash-made file writes other than a leading heredoc or a single `sed -i`/`printf >`/`echo >` (ledger, "Correction: the Engine development read is 5 of 6 at the line"). Today's Baseline cells edit source through `python3 - <<'PY' … PY` blocks; for example, cell `134623-715213`'s last calls rewrite `tests/test_cli.py` that way. The replay would not apply such writes. The line harvest reads the actual tree. These are different cells, so this note cannot show which C3 cells were misread. It shows that the two instruments disagree by 6 of 6 against 0 of 6 on the same task tree and harness, which is outside sampling variance for cells that all work to the budget edge.

## Limits

- Six cells; a point estimate.
- The decider's denominator is delivered passes, and here it is 0.
- The confinement refusal in `822790` was a mistyped absolute path, not a reach outside the worktree. That cell is un-admitted and is counted above, with the others.
