# Ornith 1.5 9B pathology probe — result addendum: Block B turn-level churn

Written 2026-09-13, after
[the result](ornith-9b-pathology-probe-result.md) was committed at `bbc3a6e`.
It is an **offline walk over the retained artifacts** under
`/Users/pauleveritt/satyrn-smokes/2026-09-13-ornith9b-pathology-probe/`. No
model ran, no cell was re-run or extended, and nothing in the output root was
written or moved. It records a turn-level diagnostic of the four longer Block B
(complaint-lifecycle session) cells that the frozen result did not capture. It
**changes no frozen number**: the three pathology counts and the decision
rule's negative branch stand exactly as committed in the result.

## What the frozen measures already say

For Block B the frozen result scores the three declared pathologies as follows.

- **Pathology 1, repeat lock (longest identical consecutive run >= 5): 0 of 8.**
  The longest identical consecutive run is **1** in each of the four Block B
  cells, exactly as in the four Block A cells, so no cell reaches the floor of
  5. The churn table below is **not** pathology 1: churn counts mutations to one
  path across a whole cell, not a run of consecutive identical calls, and its
  scale (8–16) is a different quantity from the run length (1).
- **Pathology 2, no verification (zero test-runner calls before the cell's last
  mutation): 1 of 8, in `cell-05-A3` (Block A).** The Block B scoped counts are
  **8, 13, 11, 12** for `B1`–`B4`, all above zero.
- **Pathology 3, out-of-scope write: 0 of 8.** All sixteen Block B steps carry
  `scope_violations: []` and all four cell codes are `COMPLETE`.

The result's decision rule needs a pathology present in >= 2 of 8; none
reaches it, and this addendum adds no measure to any of the three.

## Block B churn, turn by turn

One row per session cell, all on task `agentclinic-complaint-lifecycle`,
Baseline only, repeat limit off. `tool calls` counts `tool_execution_start`
events in the cell's `transcript.jsonl` after unwrapping the adapter envelope
(see *measurement gap* below). `app.py mutations` counts `edit` and `write`
calls whose `args.path` is `app.py`; the cell also mutated `models.py`,
`tests/test_app.py`, `templates/base.html`, `templates/complaints.html` and
`templates/home.html`. The last column is **context read from the receipts, not
a measure**: the brief does not ask pass/fail, and neither this table nor the
frozen result scores the phase-4 outcome.

| Cell | Turns | Tool calls | Tool mix | Longest identical consecutive run | Identical repeats | `app.py` mutations | Phase-4 receipt verdict |
|---|---|---|---|---|---|---|---|
| `cell-02-B1` | 36 | 32 | bash 11, edit 13, write 8 | 1 | 4 | 8 | `fail` |
| `cell-04-B2` | 76 | 72 | bash 42, edit 17, write 10, read 3 | 1 | 4 | 11 | `fail` |
| `cell-06-B3` | 60 | 56 | bash 18, edit 20, write 12, read 6 | 1 | 6 | 16 | `pass` |
| `cell-08-B4` | 57 | 58 | bash 26, edit 19, write 8, read 5 | 1 | 8 | 12 | `pass` |

`Turns` is `turn_start` events. `Identical repeats` is
`sum(count - 1)` over distinct `(toolName, args)` keys, so a command run four
times contributes 3. The verdict column is the `verdict` field of each cell's
`receipts/04-phase-4-resolve-reopen.json`; the same cell's
`session-record.json` carries `code: COMPLETE` and all four step outcomes
`settled`, because a phase receipt's verdict is not what the code records.
The tool-call counts (32, 72, 56, 58) are the same four values the frozen
result validated against `sum(step.tool_count)` over each cell's four steps.

## The only identical repeated calls

Across all four cells, `edit` and `write` args never repeat: the maximum
occurrences of any single `(toolName, args)` mutation pair is **1** in every
cell, so every mutation has a distinct payload. The complete list of repeats is:

- `cell-02-B1` — `bash`: `uv run python -m pytest tests -q 2>&1 | tail -6`
  **x4**; `bash`: the same command with `tail -15` **x2**.
- `cell-04-B2` — `bash`: `cd "$(pwd)"; uv run python -m pytest tests -q 2>&1 |
  tail -6` **x3**; `bash`: the same command with `tail -5` **x3**.
- `cell-06-B3` — `bash`: `uv run python -m pytest tests 2>&1 | tail -6` **x4**;
  `bash`: the same command with `tail -4` **x2**; `read app.py` **x2**;
  `read tests/test_app.py` **x2**.
- `cell-08-B4` — `bash`: `uv run python -m pytest tests 2>&1 | tail -4` **x5**;
  `bash`: the same command with `tail -6` **x3**; `bash`: the same command with
  `tail -5` **x2**; `read app.py` **x2**.

Every repeated `bash` is the suite re-run; every repeated `read` is the same
path read twice. **None of the repeats is consecutive** — the longest
identical consecutive run is 1 in each cell — so the repeats are re-runs
separated by other work, not the lock shape the frozen pathology names.

## Recompute

Verbatim, the script that produced the table. It reads the retained
`transcript.jsonl` under each cell, unwrapping the adapter envelope, and prints
turns, tool calls, longest identical consecutive run, identical repeats, tool
mix and mutation counts per path.

```python
import glob, json, os
from collections import Counter
ROOT = os.path.expanduser("~/satyrn-smokes/2026-09-13-ornith9b-pathology-probe")
CELLS = ["cell-02-B1", "cell-04-B2", "cell-06-B3", "cell-08-B4"]
def unwrap(e):
    p = e.get("payload")
    return p if isinstance(p, dict) and "type" in p else e
def load(p):
    return [unwrap(json.loads(l)) for l in open(p) if l.strip()]
def sig(e):
    return (e.get("toolName"), json.dumps(e.get("args"), sort_keys=True))
for c in CELLS:
    f = glob.glob(f"{ROOT}/{c}/**/transcript.jsonl", recursive=True)[0]
    evs = load(f)
    starts = [e for e in evs if e.get("type") == "tool_execution_start"]
    sigs = [sig(e) for e in starts]
    cnt = Counter(sigs)
    reps = sum(v - 1 for v in cnt.values())
    best = cur = 0; prev = None
    for s in sigs:
        cur = cur + 1 if s == prev else 1
        best = max(best, cur); prev = s
    names = Counter(e.get("toolName") for e in starts)
    churn = Counter((e.get("args") or {}).get("path") for e in starts
                    if e.get("toolName") in ("edit", "write"))
    turns = sum(1 for e in evs if e.get("type") == "turn_start")
    print(c, "turns", turns, "tools", len(starts), "longest", best,
          "repeats", reps, "mix", dict(names), "churn", dict(churn.most_common()))
```

Printed for the four cells, in cell order:

    cell-02-B1 turns 36 tools 32 longest 1 repeats 4 mix {'bash': 11, 'write': 8, 'edit': 13} churn {'app.py': 8, 'templates/complaints.html': 4, 'tests/test_app.py': 4, 'models.py': 3, 'templates/base.html': 1, 'templates/home.html': 1}
    cell-04-B2 turns 76 tools 72 longest 1 repeats 4 mix {'bash': 42, 'write': 10, 'read': 3, 'edit': 17} churn {'app.py': 11, 'models.py': 5, 'tests/test_app.py': 5, 'templates/complaints.html': 4, 'templates/base.html': 1, 'templates/home.html': 1}
    cell-06-B3 turns 60 tools 56 longest 1 repeats 6 mix {'bash': 18, 'write': 12, 'edit': 20, 'read': 6} churn {'app.py': 16, 'tests/test_app.py': 6, 'models.py': 4, 'templates/complaints.html': 3, 'templates/base.html': 2, 'templates/home.html': 1}
    cell-08-B4 turns 57 tools 58 longest 1 repeats 8 mix {'bash': 26, 'write': 8, 'edit': 19, 'read': 5} churn {'app.py': 12, 'models.py': 5, 'tests/test_app.py': 4, 'templates/complaints.html': 3, 'templates/home.html': 2, 'templates/base.html': 1}

## Block B measurement gap (restated)

The churn numbers above are a hand walk because the instrument does not read a
session cell, for the reasons the frozen result already states.

- A session cell retains `transcript.jsonl` as the adapter's own envelope
  (`{"version": 1, "type": "event", "step_id": ..., "payload": {...}}`); the Pi
  events sit inside `payload`, not at the line's top level.
- The record's literal recompute command therefore counts **0** on that file —
  measured here again on `cell-02-B1`: it prints `0 starts= 0`, a false absence,
  not a measurement. The result's hand walk unwrapped the payload first, and the
  unwrapped `tool_execution_start` count was checked against the adapter's own
  tally: **32, 72, 56 and 58**, exactly `sum(step.tool_count)` over each cell's
  four steps.
- V10's `count_transcript` **refuses** the unwrapped session stream, returning
  `{"measured": false, "reason": "malformed"}` (re-measured here on
  `cell-02-B1`), because the session adapter retains no Pi `session` header.
- The census does not discover the file at all: its transcript discovery is
  `transcript.txt` and the adapter's `.satyrn-implementer-transcript.jsonl`
  (`census.py:462-472`), while a session cell writes `transcript.jsonl`
  (`session.py:73`). So `census`, `repeats`, `test_runner_commands` and
  `read_lock` exist for Block A only; **all four** Block B cells
  (`cell-02-B1`, `cell-04-B2`, `cell-06-B3`, `cell-08-B4`) have no census row.

This is the same gap the frozen result's *Missingness* section records; it is
restated here because this addendum's whole table rests on the same hand walk.
Closing it is instrument work, not measurement, and it was not authorized by
this addendum.

## What this does not establish

- **Churn is not one of the three frozen pathologies.** It is not repeat lock
  (longest consecutive identical run, still **1** in every cell, pathology 1
  still **0 of 8**), not missing verification (pathology 2 still **1 of 8**),
  and not an out-of-scope write (pathology 3 still **0 of 8**). The frozen
  counts and the frozen decision are unchanged.
- **Churn does not predict the phase-4 outcome.** The highest `app.py` churn is
  `cell-06-B3` at 16 and its phase-4 receipt passed; `cell-04-B2` at 11 failed,
  while `cell-08-B4` at 12 passed. Four cells with two pass and two fail cannot
  order churn against an outcome, in either direction.
- **No rate, no interval, no significance test.** These are four cells on one
  model in one run on one day. A per-cell count is an observation about that
  cell, not an estimate of a rate.
- **No comparison.** Nothing here is compared with gemma, with any other model,
  with Block A, or with the 2026-09-09 Ornith probe, and no count pools across
  runs.
- **No architecture claim and no Engine arm.** Baseline only; the engine and the
  instrument were not changed, and no cell was re-run to produce this table.
- **The verdict column is context, not a measure.** Pass/fail rates are not
  asked by the record and are not reported; the column exists only to show that
  the churn column does not line up with the phase-4 outcome.
