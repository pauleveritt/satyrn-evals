# Ornith 1.5 9B ceiling probe — result

Run and retained 2026-09-14, under
[the pre-run record](ornith-9b-ceiling-probe-pre-run-record.md). Baseline
only, `n = 12`, serial `A1 B1 C1 A2 B2 C2 A3 B3 C3 A4 B4 C4`, repeat limit
off. **12 of 12 cells ran**; launcher `run.log`: start `01:06:39Z`, `launcher
COMPLETE` at `02:45:07Z`, total wall clock 1h38m28s, no unreached cells, no
infrastructure stop. Model loadability check at launch: `rc=0
observed_model='Ornith-1.5-9B-MLX-8bit'`. No cell was replaced, extended or
re-run.

**Model identity, every cell.** Every one of the twelve cells' own
transcripts reports `message.model = Ornith-1.5-9B-MLX-8bit` — the eight
attempt cells directly (`message_end`/`message_start` events), the four
session cells after the payload unwrap (`turn_end.message.model`, and
`message_start`). **No cell reports any other model.** This is not
prominent because it needed to be flagged; it is prominent because the
brief required checking it before any cell counts.

**Question, verbatim from the brief.** In each block, how many of four
Baseline cells fail?

## The 12-cell table

`code` is the harness's own outcome code (`attempt.json` for A/B,
`session-record.json` for C). `verdict` is `receipt.json` `verdict` for A/B;
for C it is each step's `feature_verdict` in phase order. Seconds are
`run.log`'s per-cell `duration=`. Turns are `turn_start` events (A/B) or the
sum of each step's own `turn_count` (C, cross-checked equal to that cell's
own `turn_start` count). Tool calls are `tool_execution_start` events,
payload-unwrapped for C. Tokens are summed from the terminal usage-bearing
event, exactly once each (see "Measures and recompute commands" below for
which event type, and why it differs by kind).

| cell | block | task | rung | outcome code | verdict | seconds | turns | tool calls | input tok | output tok |
|---|---|---|---|---|---|---|---|---|---|---|
| cell-01-A1 | A | `agentclinic-repair-depth-3` | R1 | `COMMAND_TIMEOUT` | — (no receipt) | 902 | 6 | 10 | 14,038 | 3,516 |
| cell-02-B1 | B | `agentclinic-repair-depth-2` | R1 | `OK` | `pass` | 86 | 11 | 10 | 20,145 | 3,642 |
| cell-03-C1 | C | `agentclinic-complaint-lifecycle` | — | `COMPLETE` | pass, pass, pass, pass | 740 | 68 | 64 | 115,349 | 22,898 |
| cell-04-A2 | A | `agentclinic-repair-depth-3` | R1 | `COMMAND_TIMEOUT` | — (no receipt) | 901 | 26 | 25 | 52,169 | 15,203 |
| cell-05-B2 | B | `agentclinic-repair-depth-2` | R1 | `OK` | `pass` | 145 | 12 | 16 | 24,986 | 5,289 |
| cell-06-C2 | C | `agentclinic-complaint-lifecycle` | — | `COMPLETE` | pass, pass, pass, pass | 375 | 39 | 38 | 61,900 | 12,832 |
| cell-07-A3 | A | `agentclinic-repair-depth-3` | R1 | `OK` | `pass` | 725 | 23 | 29 | 58,760 | 21,150 |
| cell-08-B3 | B | `agentclinic-repair-depth-2` | R1 | `OK` | `pass` | 156 | 13 | 17 | 23,633 | 5,420 |
| cell-09-C3 | C | `agentclinic-complaint-lifecycle` | — | `COMPLETE` | pass, pass, pass, pass | 391 | 38 | 37 | 62,235 | 12,357 |
| cell-10-A4 | A | `agentclinic-repair-depth-3` | R1 | `COMMAND_TIMEOUT` | — (no receipt) | 901 | 5 | 6 | 12,732 | 6,628 |
| cell-11-B4 | B | `agentclinic-repair-depth-2` | R1 | `OK` | `pass` | 85 | 13 | 18 | 22,446 | 3,775 |
| cell-12-C4 | C | `agentclinic-complaint-lifecycle` | — | `COMPLETE` | pass, pass, pass, pass | 501 | 50 | 46 | 80,286 | 17,290 |

The three `COMMAND_TIMEOUT` cells (`cell-01-A1`, `cell-04-A2`,
`cell-10-A4`) never reached `receipt.json`: `attempt.json`'s `patch_path`,
`verdict` and `receipt_path` are all `null`, and `summary.json`'s
`code_counts` shows `COMMAND_TIMEOUT: 1`, `MODEL_ERROR: 0` for each. See
"The three depth-3 timeouts" below.

## Decision rule, applied verbatim

> **A cell fails** when, read from retained evidence only:
>
> | Kind | Fails when | Read from |
> |---|---|---|
> | repair (A, B) | `receipt.json` `verdict` is not `pass`, **or** `attempt.json` `code` is not `OK` | the cell's attempt directory |
> | session (C) | any step's `feature_verdict` is `fail`, **or** any step's `outcome` is not `settled`, **or** `session-record.json` `code` is not `COMPLETE` | `session-record.json` |
>
> A `MODEL_ERROR` (5xx, out of memory) is an infrastructure event: the cell
> is reported as **unscored**, not as a failure, the cause is diagnosed and
> recorded, and the cell is not re-run (`n = 12` is frozen). Denominators in
> the rule below count scored cells only, and the result states every
> unscored cell.
>
> **Decision rule.** A block is a **ceiling** if **2 or more of its 4 scored
> cells fail**. Report per block. Then:
>
> - If one or more blocks is a ceiling, the **lowest-complexity ceiling
>   block** (B before A before C, by the ordering in the table) is the
>   recommended release-one workload, because it is the smallest gap an
>   Engine has to close. Name it; do not design toward it.
> - If no block is a ceiling, say so plainly. Ornith 9B has no measured
>   ceiling on this task fleet, and the next probe needs harder tasks; list
>   candidates by name only. Do not run any.

### Per-cell determination against the rule's exact criteria

**Block A — `agentclinic-repair-depth-3`, R1.**

| Cell | `attempt.json` `code` | `receipt.json` `verdict` | Fails because |
|---|---|---|---|
| A1 | `COMMAND_TIMEOUT` | none (no receipt) | code is not `OK` → **fail** |
| A2 | `COMMAND_TIMEOUT` | none (no receipt) | code is not `OK` → **fail** |
| A3 | `OK` | `pass` | neither condition met → **pass** |
| A4 | `COMMAND_TIMEOUT` | none (no receipt) | code is not `OK` → **fail** |

**Block A: 3 of 4 scored cells fail.**

**Block B — `agentclinic-repair-depth-2`, R1.**

| Cell | `attempt.json` `code` | `receipt.json` `verdict` | Fails because |
|---|---|---|---|
| B1 | `OK` | `pass` | neither condition met → **pass** |
| B2 | `OK` | `pass` | neither condition met → **pass** |
| B3 | `OK` | `pass` | neither condition met → **pass** |
| B4 | `OK` | `pass` | neither condition met → **pass** |

**Block B: 0 of 4 scored cells fail.**

**Block C — `agentclinic-complaint-lifecycle`.**

| Cell | `session-record.json` `code` | any step `feature_verdict = fail`? | any step `outcome != settled`? | Fails because |
|---|---|---|---|---|
| C1 | `COMPLETE` | no (4/4 pass) | no (4/4 settled) | none of the three conditions met → **pass** |
| C2 | `COMPLETE` | no (4/4 pass) | no (4/4 settled) | none of the three conditions met → **pass** |
| C3 | `COMPLETE` | no (4/4 pass) | no (4/4 settled) | none of the three conditions met → **pass** |
| C4 | `COMPLETE` | no (4/4 pass) | no (4/4 settled) | none of the three conditions met → **pass** |

**Block C: 0 of 4 scored cells fail.**

### The rule's consequence

- **Block A is a ceiling** (3 ≥ 2 of 4 scored cells fail).
- Block B is not a ceiling (0 of 4).
- Block C is not a ceiling (0 of 4).

Exactly one block is a ceiling, so the "lowest-complexity ceiling block"
ordering (B before A before C) has nothing to break a tie among: **Block A,
`agentclinic-repair-depth-3` at rung R1, is the recommended release-one
workload** — named only, per the rule; nothing is designed toward it here.

## The three depth-3 timeouts, reported plainly

`cell-01-A1`, `cell-04-A2` and `cell-10-A4` ran 902 s, 901 s and 901 s
respectively against the harness's `--timeout 900` for Block A
(`agentclinic-repair-depth-3 --n 1 --rung R1 --timeout 900
--attempt-timeout 1200`, frozen in the pre-run record). All three stopped
with `attempt.json` `code = COMMAND_TIMEOUT`, `message: "attempt command
exceeded 900 seconds"`, `patch_path: null`, `verdict: null`,
`receipt_path: null` — the attempt command was killed at the timeout
boundary before it produced a patch or a receipt. This is a timeout, stated
as a timeout: **not** re-run, **not** extended, and the decision rule above
is applied to exactly what these three `attempt.json` files say (`code` is
not `OK`), per the rule as written. See "What this does not establish" for
what a 900 s timeout does and does not tell us about a ceiling.

The fourth Block A cell, `cell-07-A3`, ran 725 s — inside the timeout — and
passed with 29 tool calls and 21,150 output tokens, the block's largest
figures on both counts.

## Diagnostics — exploratory, kept apart from the measures

**These counts did not enter the decision rule above.** They are carried
forward from the pathology probe's reviewer note (same-file mutation churn
in session cells) and from this probe's own read of failed tool results.
Nothing here says whether churn, or a failed tool result, is a problem in
either block.

Recompute script (session cells run over the unwrapped `event` payload
stream; repair cells over the transcript directly):

    uv run python -c "
    import json, sys, collections
    from pathlib import Path
    evs=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    starts=[e for e in evs if e.get('type')=='tool_execution_start']
    ends=[e for e in evs if e.get('type')=='tool_execution_end']
    churn=collections.Counter()
    for e in starts:
        if e.get('toolName') in ('edit','write'):
            path=(e.get('args') or {}).get('path') or (e.get('args') or {}).get('file_path')
            churn[path]+=1
    failed=sum(1 for e in ends if e.get('error') or e.get('isError'))
    print(dict(churn), 'failed_tool_results=', failed)
    " <transcript>

(For session cells, `evs` is built by unwrapping each `event` line's
`payload`, exactly as for the measures above.)

| cell | edit+write calls per target path | failed tool results |
|---|---|---|
| cell-01-A1 | none (`COMMAND_TIMEOUT` before any edit/write) | 0 |
| cell-02-B1 | `app.py`: 1, `templates/base.html`: 1 | 0 |
| cell-03-C1 | `app.py`: 10, `models.py`: 2, `templates/base.html`: 1, `templates/home.html`: 1, `templates/complaints.html`: 4, `tests/test_app.py`: 5 | 3 |
| cell-04-A2 | none (`COMMAND_TIMEOUT` before any edit/write) | 7 |
| cell-05-B2 | `app.py`: 1, `templates/base.html`: 1 | 0 |
| cell-06-C2 | `app.py`: 10, `models.py`: 4, `templates/base.html`: 1, `templates/home.html`: 1, `templates/complaints.html`: 3, `tests/test_app.py`: 5 | 2 |
| cell-07-A3 | `app.py`: 1, `models.py`: 2, `templates/base.html`: 1 | 3 |
| cell-08-B3 | `app.py`: 1, `templates/base.html`: 2 | 2 |
| cell-09-C3 | `app.py`: 9, `models.py`: 3, `templates/base.html`: 1, `templates/home.html`: 1, `templates/complaints.html`: 3, `tests/test_app.py`: 5 | 0 |
| cell-10-A4 | none (`COMMAND_TIMEOUT` before any edit/write) | 0 |
| cell-11-B4 | `./app.py`: 1, `./templates/base.html`: 1 | 3 |
| cell-12-C4 | `app.py`: 7, `models.py`: 2, `templates/base.html`: 2, `templates/complaints.html`: 6, `tests/test_app.py`: 5 | 3 |

`cell-11-B4`'s two paths are recorded with a leading `./` exactly as the
tool call's own `args` carried them — an artifact of how that cell's model
spelled its own tool-call paths, not a normalization applied here.

## Measures and recompute commands

Every number in the 12-cell table above carries its command below. `<t>` is
the cell's `transcript.txt` (A, B) or `transcript.jsonl` (C).

**Wall clock.** Read directly from `run.log`'s per-cell
`start`/`done exit=... duration=Ns` lines; no recomputation.

**Turns.**

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    print(sum(1 for e in evs if e.get('type')=='turn_start'))
    " <t>

For C, `evs` is the payload-unwrapped stream (below); the result is
cross-checked equal to `sum(step.turn_count)` over that cell's
`session-record.json` steps (C1 68, C2 39, C3 38, C4 50 — all four match
exactly).

**Tool calls.**

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    print(len([e for e in evs if e.get('type')=='tool_execution_start']))
    " <t>

For C, over the payload-unwrapped stream; cross-checked equal to
`sum(step.tool_count)` (C1 25+14+7+18=64, C2 11+8+7+12=38, C3
10+6+10+11=37, C4 11+19+8+8=46 — all four match exactly).

**Payload unwrap for session cells (`<t>` = `transcript.jsonl`), used by
every walk above that reads a C cell:**

    evs=[]
    for l in Path("<t>").read_text().splitlines():
        if not l.strip(): continue
        e=json.loads(l)
        evs.append(e.get('payload') or {} if e.get('type')=='event' else e)

**Input and output tokens.**

    uv run python scripts/usage_totals.py <transcript.txt>   # A, B only

For A and B this ran as written and produced the eight figures above
directly, summing `message.usage` over `message_end` events exactly once
each (`msg_end_count` 6, 11, 25, 12, 23, 13, 5, 13 for A1 B1 A2 B2 A3 B3 A4
B4 respectively — matches the events where a usage object was present).

`usage_totals.py` refuses `transcript.jsonl` outright (wrapped stream, no
top-level `message_end`). Per the brief, the fix is to unwrap each `event`
payload first. **That unwrap surfaced a second, larger gap than the brief
anticipated: after unwrapping, a session transcript carries zero
`message_end` events of any kind** (`grep`-free check: counting event types
over all 3,479+ unwrapped payload lines in `cell-03-C1` alone gives
`message_start: 136, message_update: 3075, turn_start: 68, turn_end: 68,
tool_execution_start: 64, tool_execution_end: 64, agent_end: 4,
step_finished: 4, session_started: 1` — no `message_end` anywhere). The
brief's instruction to "sum `message.usage` over `message_end` events" is
therefore inapplicable to this stream shape as literally written; see
"Missingness" below for the substitution used and why it is judged safe.

The substitute walk actually run for C:

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[]
    for l in Path(sys.argv[1]).read_text().splitlines():
        if not l.strip(): continue
        e=json.loads(l)
        evs.append(e.get('payload') or {} if e.get('type')=='event' else e)
    input_tok=output_tok=n=0
    for e in evs:
        if e.get('type')=='turn_end':
            usage=(e.get('message') or {}).get('usage')
            if usage:
                input_tok+=usage.get('input',0); output_tok+=usage.get('output',0); n+=1
    print('input=',input_tok,'output=',output_tok,'counted=',n)
    " <transcript.jsonl>

Result: C1 input=115,349 output=22,898 (68 counted); C2 input=61,900
output=12,832 (39 counted); C3 input=62,235 output=12,357 (38 counted); C4
input=80,286 output=17,290 (50 counted). Every one of the 68/39/38/50
`turn_end` events in its cell carried a usage object with `role: assistant`
(checked directly: 0 non-assistant `turn_end` events in `cell-03-C1`), so
there is no ambiguity of the kind `message_end` has in the repair stream
(where only assistant messages among several roles carry usage) — the
count-once discipline is the same, applied to the one event type this
stream actually has.

## Missingness / instrument debt

- **No unscored cells. There are none.** `MODEL_ERROR` count is `0` in
  every one of the twelve cells' own `summary.json` / `session-record.json`
  (checked directly, not inferred from a `COMPLETE`/`OK` code elsewhere).
  All twelve cells are scored; the fail counts above are out of 4 scored
  cells in every block.
- **Instrument debt 1 — the payload unwrap, as anticipated by the brief.**
  `usage_totals.py` and a literal `turn_start`/`tool_execution_start` walk
  both refuse or silently under-count `transcript.jsonl` because its lines
  are the session adapter's own envelope (`{"type": "event", ...,
  "payload": {...}}` for the Pi-level events, interleaved with
  `session_started` and `step_finished` at the top level). Every C-cell
  count above unwraps `payload` before counting, as the brief anticipated
  and instructed.
- **Instrument debt 2 — larger than the brief anticipated.** The brief's
  literal instruction ("sum `message.usage` over `message_end` events") does
  not apply to the unwrapped session stream at all: that stream contains no
  `message_end` event of any type, in any of the four C cells. The
  terminal, once-per-turn, usage-bearing event in this stream is `turn_end`
  instead (one `turn_end` per `turn_start`, every one carrying
  `message.usage` with `role: assistant`). The token totals for Block C
  above sum `turn_end` usage instead of `message_end` usage, following the
  same "terminal event, counted exactly once" discipline `usage_totals.py`
  documents for `message_end` in the repair stream — but this is a second,
  unanticipated substitution on top of the payload unwrap, not merely the
  unwrap itself, and it has not been reviewed against a wider sample of
  session transcripts than these four.
- **No receipt, no patch for the three `COMMAND_TIMEOUT` cells.** `A1`,
  `A2` and `A4` have no `receipt.json` and no `patch.diff`; every number
  reported for them above comes from `attempt.json`, `summary.json` and
  `transcript.txt` alone.

## What this does not establish

- **A 900 s timeout does not separate a capability ceiling from a budget
  ceiling.** Three of Block A's four cells stopped at the harness's
  `--timeout 900` boundary, not at a graded failure the model produced and
  a receipt recorded. Nothing here distinguishes "Ornith 1.5 9B cannot solve
  `depth-3` at R1" from "Ornith 1.5 9B could solve it, given more than 900
  wall-clock seconds." The one Block A cell that finished inside the
  timeout (`cell-07-A3`, 725 s) passed. The decision rule was applied
  exactly as written to what the three timed-out `attempt.json` files say
  (`code` is not `OK`), and that is the only claim made about Block A here:
  it is a ceiling **under the frozen rule and the frozen 900 s budget**,
  not a ceiling shown to be inherent to the task at any budget.
- **No rate and no capability claim beyond presence/absence.** Twelve cells
  on one model, in one run, on one day, support per-block presence/absence
  of a ceiling and nothing finer — not a pass rate, not a probability, not
  an estimate of how often Block A would fail at a longer timeout.
- **No comparison.** Nothing here is compared with gemma, with any other
  model, or with one arm against another, and no count pools with the
  pathology probe, the 2026-09-09 Ornith run, or any gemma run.
- **No explanation of why Ornith fails where it fails.** The three timeouts
  are reported as timeouts; no cause is diagnosed beyond the harness's own
  `COMMAND_TIMEOUT` code and message.
- **No Engine arm and no architecture claim.** Baseline only; nothing was
  changed in the engine, and the two instrument substitutions forced by the
  session transcript's shape (the payload unwrap, and the `turn_end`
  substitution for `message_end`) are stated above with the checks that
  validate them.
- **The diagnostics table is exploratory.** Churn and failed-tool-result
  counts did not enter the decision rule and say nothing about whether
  churn, or a failed tool call, is a problem in either block.
- **No design or engine change toward Block A.** The rule names Block A as
  the recommended release-one workload; nothing here designs toward
  closing that gap.

## Task-tree digests, re-verified after the run

Recomputed with the pre-run record's own walk, after the last cell, in this
worktree:

    uv run python -c "
    import hashlib, sys
    from pathlib import Path
    d = Path('src/satyrn_evals/tasks') / sys.argv[1]
    h = hashlib.sha256()
    for p in sorted(d.rglob('*')):
        if p.is_file():
            h.update(p.relative_to(d).as_posix().encode()); h.update(p.read_bytes())
    print(h.hexdigest())
    " <task>

| Block | Task | Frozen digest | Re-verified after the run | Drift |
|---|---|---|---|---|
| A | `agentclinic-repair-depth-3` | `2090e5fe0ce32551f62c1236bb96f0862d45378892fa073a6a1c801ab356b23b` | `2090e5fe0ce32551f62c1236bb96f0862d45378892fa073a6a1c801ab356b23b` | none |
| B | `agentclinic-repair-depth-2` | `91b9e2fafcb905812b33b90783c2701d29b93363a172e7b197da40355b0bb662` | `91b9e2fafcb905812b33b90783c2701d29b93363a172e7b197da40355b0bb662` | none |
| C | `agentclinic-complaint-lifecycle` | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` | none |

No drift in any of the three task trees. As the pre-run record states, the
Baseline `run` command carries no `--task-tree-sha256` flag, so these
digests are a recorded identity, not a command-enforced gate.

## The budget side — per-block medians

The maintainer's question was not only "how many of four pass" but also
"what does it cost" — the two measures below are the medians of the
per-cell figures in the 12-cell table, computed over the block's 4 cells
(fails included; the brief's measures apply to every cell, not only the
passing ones).

| Block | Median seconds | Median output tokens |
|---|---|---|
| A | 901 (`725, 901, 901, 902` → sorted `725, 901, 901, 902`) | 10,915.5 (`3,516, 6,628, 15,203, 21,150` → sorted, mean of middle two `6,628` and `15,203`) |
| B | 115.5 (`85, 86, 145, 156` → mean of middle two `86` and `145`) | 4,532 (`3,642, 3,775, 5,289, 5,420` → mean of middle two `3,775` and `5,289`) |
| C | 446 (`375, 391, 501, 740` → mean of middle two `391` and `501`) | 15,061 (`12,357, 12,832, 17,290, 22,898` → mean of middle two `12,832` and `17,290`) |

Block A's seconds median is dominated by its three `COMMAND_TIMEOUT` cells
sitting at the 900 s wall; the one cell that finished (`cell-07-A3`, 725 s)
is the block's minimum, not its median.

## Retention and revision

Output root
`/Users/pauleveritt/satyrn-smokes/2026-09-14-ornith9b-ceiling-probe/` holds
`launch.sh`, `schedule.json`, `run.log` (per-cell start/end timestamps and
the model-loadability check), the twelve cell directories and, beside each,
`cell-NN-XY.stdout.log`. Each attempt cell (A, B) holds its
`transcript.txt`, `attempt.json`, and — for the one that produced one — its
`receipt.json` and `patch.diff`; the three `COMMAND_TIMEOUT` cells hold
`transcript.txt` and `attempt.json` only, as recorded above. Each session
cell (C) holds its `transcript.jsonl`, `session-record.json`, four phase
patches, four receipts, four snapshots and four checkpoints, plus
`adapter-stderr.log`. Nothing was discarded and no cell was re-run. The
evals revision for the run is this worktree's `HEAD` at the pre-run
record's commit; this result document is committed after it on the same
branch. No merge to `main`.
