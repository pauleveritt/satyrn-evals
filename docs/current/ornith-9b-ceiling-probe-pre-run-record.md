# Pre-run record — Ornith 1.5 9B ceiling probe, Baseline only, `n = 12`

**Written 2026-09-13, before any inference.** Every value below is frozen at
the moment of writing. Authorized by the ceiling-probe brief (Fable,
2026-09-13), `docs/current/ornith-9b-ceiling-probe-brief.md`. This record
fixes that brief's concrete values; it adds no question, no cell and no arm.

## The question, and the decision rule (verbatim from the brief)

**Question.** In each block, how many of four Baseline cells on Ornith 1.5
9B fail?

**A cell fails** when, read from retained evidence only:

| Kind | Fails when | Read from |
|---|---|---|
| repair (A, B) | `receipt.json` `verdict` is not `pass`, **or** `attempt.json` `code` is not `OK` | the cell's attempt directory |
| session (C) | any step's `feature_verdict` is `fail`, **or** any step's `outcome` is not `settled`, **or** `session-record.json` `code` is not `COMPLETE` | `session-record.json` |

A `MODEL_ERROR` (5xx, out of memory) is an infrastructure event: the cell is
reported as **unscored**, not as a failure, the cause is diagnosed and
recorded, and the cell is not re-run (`n = 12` is frozen). Denominators in the
rule below count scored cells only, and the result states every unscored cell.

**Decision rule.** A block is a **ceiling** if **2 or more of its 4 scored
cells fail**. Report per block. Then:

- If one or more blocks is a ceiling, the **lowest-complexity ceiling block**
  (B before A before C, by the ordering in the table) is the recommended
  release-one workload, because it is the smallest gap an Engine has to
  close. Name it; do not design toward it.
- If no block is a ceiling, say so plainly. Ornith 9B has no measured ceiling
  on this task fleet, and the next probe needs harder tasks; list candidates
  by name only. Do not run any.

**Also record, per cell, as measures (not diagnostics).**

| Measure | Read from |
|---|---|
| wall clock, seconds | the launcher's `run.log` start/end per cell |
| turns | `turn_start` events in the transcript (repair) / sum of steps' `turn_count` (session) |
| tool calls | `tool_execution_start` events, one per call, payload-unwrapped for session cells |
| input and output tokens | `scripts/usage_totals.py <transcript>` for repair cells. For session cells the stream is wrapped (`event` / `session_started` / `step_finished`) and `usage_totals` refuses it; unwrap each `event` payload and sum `message.usage` over `message_end` events exactly once each, per that script's docstring. Record the unwrap as instrument debt in the result |

**Diagnostics, kept apart from the measures.** Per cell: number of `edit`
plus `write` calls per target path, and the count of failed tool results.
Carry the recompute script. State in the result that these are exploratory,
that they did not enter the rule, and that nothing here says whether churn
is a problem.

**Not asked.** Any comparison with gemma or between arms; any Engine arm;
any Fisher test or interval; any sentence about why Ornith fails where it
fails. Twelve cells support per-block presence/absence of a ceiling and
nothing finer.

## Frozen conditions

| Field | Value |
|---|---|
| Model (server) | `Ornith-1.5-9B-MLX-8bit`, served at `127.0.0.1:8001/v1` — **verified with a live completion, never `/v1/models`** (see below) |
| Model (client id, `attempt-pi`) | `omlx/Ornith-1.5-9B-MLX-8bit` (the `--model` value; `attempt-pi` takes no `--provider`) |
| Model (client id, `session-pi`) | `--provider omlx --model Ornith-1.5-9B-MLX-8bit` |
| Inference (verbatim from `arms/baseline-ornith15-9b.json`) | context window 262,144; max tokens 32,000; temperature 0.6; top_p 0.95; top_k 20; min_p 0.0; presence_penalty 0.0; repetition_penalty 1.0; compaction enabled, 16,384 reserve; `declares_reasoning: true`. **Recorded, not normalised.** |
| Arm | Baseline only, `satyrn-evals-attempt-pi` / `satyrn-evals-session-pi`, tools `read,bash,edit,write`, pi `0.85.1` |
| Repeat limit | **off**, as in the pathology probe; a limit would change the condition between the two probes |
| Block A | `agentclinic-repair-depth-3`, rung `R1` — `satyrn-evals run agentclinic-repair-depth-3 --n 1 --rung R1 --timeout 900 --attempt-timeout 1200`, 4 cells |
| Block B | `agentclinic-repair-depth-2`, rung `R1` — `satyrn-evals run agentclinic-repair-depth-2 --n 1 --rung R1 --timeout 900 --attempt-timeout 1200`, 4 cells |
| Block C | `agentclinic-complaint-lifecycle` — `satyrn-evals session agentclinic-complaint-lifecycle --step-timeout 600`, 4 cells |
| Order | A1 B1 C1 A2 B2 C2 A3 B3 C3 A4 B4 C4, serial, one at a time |
| Output root | `~/satyrn-smokes/2026-09-14-ornith9b-ceiling-probe/` — **confirmed absent** at the time of writing |
| Wall-clock stop | 2 h from the first cell; unreached cells reported as not-run. Expected use: about 1 h (session cells ran 542–663 s each on 2026-09-13; repair cells 34–71 s, though `depth-3` may run longer) |

Both repair blocks (A and B) run at rung `R1`. `R3` is guided and answers
nothing about a ceiling; `R0` on these two tasks is unobservable by
construction (the workspace's public suite sees only the redirect seam). See
the brief, "The three blocks, and why these rungs."

## Task-tree digests, recomputed before this record

The digest is the same walk the pathology probe's result document uses
("Task-tree digests, re-verified"):

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

The Baseline `run` command carries **no** `--task-tree-sha256` flag, so for
this run the digest is a **recorded identity, not a command-enforced gate**.

| Block | Task | Task tree sha256 |
|---|---|---|
| A | `agentclinic-repair-depth-3` | `2090e5fe0ce32551f62c1236bb96f0862d45378892fa073a6a1c801ab356b23b` |
| B | `agentclinic-repair-depth-2` | `91b9e2fafcb905812b33b90783c2701d29b93363a172e7b197da40355b0bb662` |
| C | `agentclinic-complaint-lifecycle` | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` |

Block C's digest is byte-identical to the value recorded and re-verified in
the pathology probe's result document for the same task, confirming no
drift in that task tree since 2026-09-13.

## Evals revision

| Field | Value |
|---|---|
| Base | `main`, the commit that carries the ceiling-probe brief |
| Worktree | `.claude/worktrees/ornith-ceiling-probe`, branch `worktree-ornith-ceiling-probe` |
| Evals revision for the run | this record's own commit on that branch |
| pi version | `0.85.1` |

## Exact per-cell commands

**Block A — `run` cells, `depth-3` at `R1` (`<cell-dir>` per cell):**

    uv run satyrn-evals run agentclinic-repair-depth-3 --n 1 --rung R1 \
      --output <cell-dir> --timeout 900 --attempt-timeout 1200 -- \
      satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

**Block B — `run` cells, `depth-2` at `R1` (`<cell-dir>` per cell):**

    uv run satyrn-evals run agentclinic-repair-depth-2 --n 1 --rung R1 \
      --output <cell-dir> --timeout 900 --attempt-timeout 1200 -- \
      satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

**Block C — `session` cells (`<cell-dir>` per cell):**

    uv run satyrn-evals session agentclinic-complaint-lifecycle \
      --output <cell-dir> --step-timeout 600 -- \
      satyrn-evals-session-pi --provider omlx --model Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

Both run under `uv run` with the current working directory set to this
worktree, so the pinned executable is the worktree's own. Neither command
passes `--max-repeated-calls`: the repeat limit is off, by the frozen
condition above. Flag shapes are verified against the adapter parsers
(`src/satyrn_evals/attempt_pi.py`, `src/satyrn_evals/adapters/pi_session.py`)
and the retained pathology-probe `schedule.json` and `launch.sh` — not
`--help`; both adapters reject `--help` as an unknown argument.

## The cells, in execution order

| Cell | Block | Task | Rung | Kind |
|---|---|---|---|---|
| `cell-01-A1` | A | `agentclinic-repair-depth-3` | R1 | repair |
| `cell-02-B1` | B | `agentclinic-repair-depth-2` | R1 | repair |
| `cell-03-C1` | C | `agentclinic-complaint-lifecycle` | — | session |
| `cell-04-A2` | A | `agentclinic-repair-depth-3` | R1 | repair |
| `cell-05-B2` | B | `agentclinic-repair-depth-2` | R1 | repair |
| `cell-06-C2` | C | `agentclinic-complaint-lifecycle` | — | session |
| `cell-07-A3` | A | `agentclinic-repair-depth-3` | R1 | repair |
| `cell-08-B3` | B | `agentclinic-repair-depth-2` | R1 | repair |
| `cell-09-C3` | C | `agentclinic-complaint-lifecycle` | — | session |
| `cell-10-A4` | A | `agentclinic-repair-depth-3` | R1 | repair |
| `cell-11-B4` | B | `agentclinic-repair-depth-2` | R1 | repair |
| `cell-12-C4` | C | `agentclinic-complaint-lifecycle` | — | session |

Sequential, non-overlapping, one at a time, each into its own directory under
the output root. The launcher writes `schedule.json` before the first cell
and a per-cell log with start/end timestamps and elapsed seconds. No cell is
added, dropped or reordered after this record is committed. `n = 12` is
frozen: no extension, re-run or replacement for any result.

## Measures and their recompute commands

Every number in the result carries the command that produced it beside it.
Tool calls are counted from `tool_execution_start`, one per call — never
`grep -c`.

**Wall clock.** Read from the launcher's `run.log` per-cell start/end
timestamps and elapsed seconds; no recomputation, the log is the source.

**Turns.**

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    print(sum(1 for e in evs if e.get('type')=='turn_start'))
    " <transcript>

For session cells, sum each step's own `turn_count` from
`session-record.json` instead of re-deriving it from the wrapped stream.

**Tool calls.**

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    starts=[e for e in evs if e.get('type')=='tool_execution_start']
    print(len(starts))
    " <transcript>

For session cells the same walk is run over the unwrapped `event` payload
stream, exactly as the pathology probe's result document does it (its
"Pathology 1" section): each JSONL line is parsed, and when
`type == "event"` the count reads the line's `payload` instead of the
line itself. The unwrap is checked against `sum(step.tool_count)` over the
cell's `session-record.json` steps, as the pathology probe's result
document did for its own Block B.

**Input and output tokens.**

    uv run python scripts/usage_totals.py <transcript>

For session cells, `usage_totals.py` refuses the wrapped stream. Per the
brief: unwrap each `event` payload and sum `message.usage` over
`message_end` events exactly once each. This unwrap is recorded as
instrument debt in the result, following the same pattern the pathology
probe recorded for its own Block B (V10/`count_transcript` refusing the
session stream).

## Diagnostics (kept apart from the measures)

Per cell: number of `edit` plus `write` calls per target path, and the count
of failed tool results.

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

Session cells use the same walk over the unwrapped payload stream. These
counts did not enter the decision rule; the pathology probe's reviewer
observed same-file mutation churn (8 to 16 `app.py` writes per session cell)
that did not predict its phase-4 failures, and this probe carries the same
recompute script forward without claiming churn is a problem here.

## Model identity, verified before writing this

A live one-word completion was sent to
`127.0.0.1:8001/v1/chat/completions` with request
`"model": "Ornith-1.5-9B-MLX-8bit"`. It returned:

    {"id": "chatcmpl-1f87349d", "model": "Ornith-1.5-9B-MLX-8bit",
     "choices": [{"message": {"role": "assistant",
       "content": "The user asked me to reply with OK"}, "finish_reason": "length"}], ...}

The response's own `model` field is `Ornith-1.5-9B-MLX-8bit`. **The model is
loadable.** Identity is re-read from each cell's own transcript
(`message.model`) before any cell is counted; a wrong observed
`message.model` is an infrastructure stop, per the brief's frozen
conditions.

## Preflight performed before this record

| Check | Result |
|---|---|
| Working tree clean, probe worktree | `git status --porcelain` empty at `41b4314` on `worktree-ornith-ceiling-probe` |
| All three task-tree digests recomputed | match the values above (recomputed in this worktree, walk from the pathology probe's result document) |
| `satyrn-evals-attempt-pi` resolves | yes — console script at this worktree's `.venv/bin/satyrn-evals-attempt-pi` |
| `satyrn-evals-session-pi` resolves | yes — console script at this worktree's `.venv/bin/satyrn-evals-session-pi` |
| One live completion from the model | returned text, observed `model` = `Ornith-1.5-9B-MLX-8bit` (above) |
| No measurement-shaped Pi process | `ps -axo pid=,ppid=,command= \| uv run python scripts/preflight_processes.py --model omlx/Ornith-1.5-9B-MLX-8bit` returned empty, exit 0 |
| Output root absent | `~/satyrn-smokes/2026-09-14-ornith9b-ceiling-probe/` does not exist (confirmed by listing `~/satyrn-smokes/`) |
| `pi` version | `0.85.1` |
| Arm inference settings recorded verbatim | from `arms/baseline-ornith15-9b.json`, reproduced in Frozen conditions above |

## Review

Sonnet implements; Opus reviews this pre-run record before cell 1 and the
result before it is called accepted, per the brief. The review checks: the
rule was applied as written; every count has its recompute command; the
rungs are `R1` in both repair blocks; the diagnostics are labelled as such;
no sentence compares Ornith with gemma or one arm with another. **No Fable
review unless the maintainer asks.**

## Stopping rules and loop rules (verbatim from the brief)

1. **Established infrastructure failure only** stops launches: model not
   loadable, wrong observed `message.model`, missing executable, broken
   artifact path. A fail verdict, a timeout, a refusal or a scope violation
   is the observation this probe exists for; it is kept and counted, never
   replaced.
2. `n = 12` is frozen. No extension, re-run or replacement for any result.
3. Do not start any other inference on this machine while the launcher runs.
4. No Engine arm, no engine change, no architecture claim, no design
   rewrite.
5. No pooling with the pathology probe, the 2026-09-09 Ornith run, or any
   gemma run.
6. No instrument change larger than reading the evidence; where `census`,
   `usage_totals` or V10 refuse a stream, count by hand from events and
   record the debt.
7. The run ends with the result document.

## Retention

Every cell keeps its launch log, `schedule.json`, transcript, `attempt.json`
or `session-record.json`, patch(es) and receipts under its own directory.
Nothing is discarded, including cells that stop early. The output root keeps
the launcher log (`run.log`), the per-cell start/end timestamps and elapsed
seconds, and the batch `schedule.json`.

## Budget grant

**Granted 2026-09-13 by the maintainer, in session** ("I approve all 3 of
your points", approving the ceiling probe, the spend, and running it
alongside Phase 0): `n = 12` cells under the frozen conditions above, on
**exclusive GPU** for the duration of the run, unattended overnight. Cell 1
may start once this pre-run record is committed and reviewed.
