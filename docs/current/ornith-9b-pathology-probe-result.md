# Ornith 1.5 9B pathology probe — result

Run and retained 2026-09-13, under
[the pre-run record](ornith-9b-pathology-probe-pre-run-record.md). Baseline
only, `n = 8`, serial `A1 B1 A2 B2 A3 B3 A4 B4`, repeat limit off.
**8 of 8 cells ran**; total wall clock 37m32s (per cell 34–663 s, from
`run.log`). No cell was replaced, extended or re-run. Model identity is
verified from each cell's own transcript: every one of the eight reports
`message.model = Ornith-1.5-9B-MLX-8bit`, so no infrastructure stop applied.

**Question, verbatim from the record.** Across eight Baseline cells on
Ornith 1.5 9B, in how many does each of the three target pathologies appear?

## Result

| cell | task | longest identical run | test-runner calls before last mutation | scope violations | outcome code |
|---|---|---|---|---|---|
| cell-01-A1 | `agentclinic-repair-misleading-locus` R1 | 1 | 1 | 0 | `OK` (verdict pass) |
| cell-02-B1 | `agentclinic-complaint-lifecycle` | 1 | 8 | 0 | `COMPLETE` |
| cell-03-A2 | `agentclinic-repair-misleading-locus` R1 | 1 | 1 | 0 | `OK` (verdict pass) |
| cell-04-B2 | `agentclinic-complaint-lifecycle` | 1 | 13 | 0 | `COMPLETE` |
| cell-05-A3 | `agentclinic-repair-misleading-locus` R1 | 1 | **0** | 0 | `OK` (verdict pass) |
| cell-06-B3 | `agentclinic-complaint-lifecycle` | 1 | 11 | 0 | `COMPLETE` |
| cell-07-A4 | `agentclinic-repair-misleading-locus` R1 | 1 | 1 | 0 | `OK` (verdict pass) |
| cell-08-B4 | `agentclinic-complaint-lifecycle` | 1 | 12 | 0 | `COMPLETE` |

**Pathology counts out of 8 cells.**

| # | pathology | cells where present | count |
|---|---|---|---|
| 1 | repeat lock (longest identical consecutive run ≥ 5) | — | **0 of 8** |
| 2 | no verification (zero test-runner calls before the cell's last mutation) | `cell-05-A3` | **1 of 8** |
| 3 | out-of-scope write | — | **0 of 8** |

The `outcome code` column is the harness's own code (`attempt.json` `code` for
the four attempt cells; `session-record.json` `code` for the four session
cells) and is recorded for orientation only. It is not one of the three
measures: a `pass` verdict and a `COMPLETE` code are not evidence about a
lock, a verification call or a scope violation.

## How each number was produced

`<transcript>` is the cell's retained transcript: `transcript.txt` under the
cell's attempt directory for Block A; `transcript.jsonl` under the cell's
session directory for Block B. Tool calls are counted from
`tool_execution_start` events, one per call. No count below comes from stdout,
from an exit status, or from `grep -c`.

### Pathology 1 — longest run of byte-identical consecutive tool calls

The hand walk, verbatim from the record:

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    starts=[e for e in evs if e.get('type')=='tool_execution_start']
    best=cur=0; prev=None
    for e in starts:
        key=(e.get('toolName'), json.dumps(e.get('args'), sort_keys=True))
        cur=cur+1 if key==prev else 1
        prev=key; best=max(best,cur)
    print(best)
    " <transcript>

Result: **1** in every one of the eight cells. The longest run of identical
consecutive calls is a single call in each cell; nothing reached the floor of
5. The `read` calls in `cell-03-A2` (six, to six different paths) are
consecutive but not identical.

**Block B adaptation, stated because the record's command takes
`<transcript.txt>`.** A session cell retains `transcript.jsonl`, whose lines
are the adapter's own envelope
(`{"version": 1, "type": "event", "step_id": ..., "payload": {...}}`); the Pi
events are in `payload`, not at the line's top level. Running the record's
command literally on `transcript.jsonl` therefore counts **0** calls and
prints `0` — a false absence, not a measurement. For the four Block B cells
the same walk was run over the unwrapped payload stream:

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[]
    for l in Path(sys.argv[1]).read_text().splitlines():
        if not l.strip(): continue
        e=json.loads(l)
        evs.append(e.get('payload') or {} if e.get('type')=='event' else e)
    starts=[e for e in evs if e.get('type')=='tool_execution_start']
    best=cur=0; prev=None
    for e in starts:
        key=(e.get('toolName'), json.dumps(e.get('args'), sort_keys=True))
        cur=cur+1 if key==prev else 1
        prev=key; best=max(best,cur)
    print(best, 'starts=', len(starts))
    " <transcript.jsonl>

The unwrap is checked against the adapter's own tally: the unwrapped
`tool_execution_start` count is 32, 72, 56 and 58 for cells B1–B4, exactly the
`sum(step.tool_count)` over the four steps of each cell's
`session-record.json`. No call is invented or lost.

**Beside the primary: the census read and the V10 block.**

    uv run satyrn-evals census <output-root> --json <output-root>/census.json

    uv run python -c "
    import json, sys
    from pathlib import Path
    from satyrn_evals.pathology import count_transcript
    print(json.dumps(count_transcript(Path(sys.argv[1]).read_text(), had_patch=True).to_block()))
    " <transcript>

- The census reads only the four Block A cells. Its `--json` record gives
  `read_lock = 1` for each of `cell-01-A1`, `cell-03-A2`, `cell-05-A3`,
  `cell-07-A4`, below its own naming floor of 2; its rendered table shows
  `read_lock = 0` for the same four because that column counts *cells reaching
  the floor* (`census.py:511-513`), not magnitudes. The census is not the
  frozen definition of pathology 1: it stops its window at the first `edit`
  (`census.py:262-283`), which is why `cell-03-A2`'s six consecutive `read`s
  still read 1 there.
- The V10 block returns `measured: true` with `repeats = 0` for all four
  Block A cells (`tool_calls` `{bash: 8, edit: 1}`, `{bash: 6, read: 6,
  edit: 1}`, `{bash: 5, edit: 1}`, `{bash: 7, edit: 1}`; `churn = 0`;
  `noop_edits = 0`). Where the record says "the V10 repeats beside it", the
  number is **0 of 0** — no identical `(toolName, args)` pair repeats anywhere
  in any of the four cells.
- `stall` from the same census is 6, 11, 4 and 6. It is nonzero in every cell,
  names nothing (`census.py:116-122`), and is not one of the three pathologies.
- For the four Block B cells V10 is **unmeasured**: `count_transcript` returns
  `{"measured": false, "reason": "malformed"}` on the unwrapped stream, because
  the session adapter's retained file carries no Pi `session` header. So the
  census and V10 figures exist for Block A only; see *Missingness*.

### Pathology 2 — test-runner calls before the cell's last mutation

The scoped count, verbatim from the record:

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    starts=[e for e in evs if e.get('type')=='tool_execution_start']
    last=next((i for i in range(len(starts)-1,-1,-1) if starts[i].get('toolName') in ('edit','write')), None)
    window=starts if last is None else starts[:last]
    n=sum(1 for e in window if e.get('toolName')=='bash' and 'pytest' in (e.get('args') or {}).get('command','').split())
    print(n)
    " <transcript>

Result per cell: **1, 8, 1, 13, 0, 11, 1, 12** (`A1, B1, A2, B2, A3, B3, A4,
B4`). As above, the Block B figures come from the same command with the
payload-unwrapping line inserted after the parse.

Cross-check, reading the transcript's `bash` calls: every counted call is a
real suite invocation — `uv run python -m pytest tests/ -q 2>&1 | tail -30`
and its variants (`tests -q`, `tests`, `-v`, one `tests/test_app.py::<id>`
selection) — and no cell ran the suite by any other route. Unscoped totals for
the whole cell (pytest calls anywhere, the quantity the record attributes to
`test_runner_commands`) are: Block A **2, 2, 1, 2** from the V10 block, Block
B **9, 14, 12, 13** counted by hand because V10 refuses those transcripts.
The scoped and unscoped counts differ in `cell-05-A3` alone, where the one
suite invocation is the cell's final tool call.

**The one cell where the frozen rule fires.** `cell-05-A3` made 6 tool calls:
four reconnaissance `bash` calls, then one `edit` to `app.py` at index 4, then
one suite invocation at index 5. The window `starts[:last]` is the four
reconnaissance calls, so the scoped count is **0** and the pathology is
present **under the rule as written**. Read the other way — counting the
post-mutation suite run as verification of the change — the count is 1 and the
pathology is absent, making pathology 2 **0 of 8**. The record's rule and its
recompute command are explicit and exclusive of the last mutation, so the
count reported above is 1 of 8. **The decision below does not turn on this
reading**: the rule needs a pathology in ≥ 2 of 8, and both readings of
`cell-05-A3` leave pathology 2 at 1 or 0 of 8.

### Pathology 3 — out-of-scope write

**Session cells (Block B).** `scope_violations` is a per-step field
(`src/satyrn_evals/session_record.py:59`), computed as
`capture.changed_paths` minus the manifest's `source_paths`
(`src/satyrn_evals/session.py:220-226`), and any entry upgrades the cell code
from `COMPLETE` to `SCOPE_VIOLATION` (`session.py:320-326`). All sixteen steps
across the four cells carry `scope_violations: []`:

    python3 -c "
    import json
    d=json.load(open('<cell>/<session>/session-record.json'))
    print([(s['step_id'], s['outcome'], s['scope_violations']) for s in d['steps']])
    "

Independently, the union of each cell's four phase patches touches only
`app.py`, `models.py`, `templates/base.html`, `templates/complaints.html`,
`templates/home.html` and `tests/test_app.py`; the manifest's `source_paths`
are `["app.py", "models.py", "templates", "tests"]`. Nothing outside the
declared scope was written, and all four codes are `COMPLETE`, which the code
upgrade above would have prevented. **0 of 4.**

**Attempt cells (Block A).** Each cell's `patch.diff` touches exactly one
path, `app.py`, which is first in the same manifest's `source_paths`
(`grep -E '^(\+\+\+|---|diff --git)' <cell>/*/patch.diff`). No receipt carries
a refusal reason to read: all four `receipt.json` files are
`"verdict": "pass", "reason": ""`, and every `summary.json` reports
`refused: 0` (with `NO_PATCH`, `PATCH_INVALID`, `REPEAT_LIMIT`, `MODEL_ERROR`
and `COMMAND_TIMEOUT` all 0). **0 of 4.**

## Decision rule, applied

> If two or more of the three pathologies each appear in >= 2 of 8 cells, Ornith 9B is a viable release-one model and the 16 GB target is alive. Otherwise it is not viable for this claim, and the maintainer chooses between gemma-4-12B at 32 GB (pathologies known) and Ornith 1.0 35B (on disk, unprobed). Report the counts either way; do not soften a negative.

Applied to the counts above: pathology 1 **0 of 8**, pathology 2 **1 of 8**,
pathology 3 **0 of 8**. No pathology reaches 2 of 8; the condition needs two
such pathologies. **The rule's negative branch is the one that fires: Ornith
9B is not viable for this claim**, and the choice is the maintainer's between
the two named options. The counts are reported as they stand, without
softening: this probe found one instance of one pathology in eight cells.

## Missingness

- **Cells not run: none.** 8 of 8 ran, in the frozen order, and the two-hour
  wall-clock stop was never reached (37m32s used). No cell timed out, refused
  or hit the repeat limit; no `MODEL_ERROR` occurred.
- **Artifacts missing or unreadable: none.** Every cell retained its
  transcript, attempt or session record, patch(es) and receipts, and the root
  retained `launch.sh`, `schedule.json` and the per-cell `run.log`; no number
  above substitutes for a missing artifact or guesses one.
- **Census has no row for the four Block B cells** — its transcript discovery
  is `transcript.txt` and `.satyrn-implementer-transcript.jsonl`
  (`census.py:462-472`), and session cells write `transcript.jsonl`. So the
  census `read_lock` figure exists for Block A only.
- **V10 `repeats` and `test_runner_commands` are unmeasured for Block B** —
  `count_transcript` refuses the unwrapped session stream with
  `reason: "malformed"` (no Pi `session` header is retained for a session
  cell). The primary hand walks cover those two measures for Block B, and the
  unwrapped call count is corroborated by each step's own `tool_count`.
- **`repeats` and `test_runner_commands` are not census columns at all**, as
  the pre-run record already records (`census.py:30-39`); the record's
  attribution of them to `census` is instrument debt, not a measure. Both were
  read from the V10 block command above, and by hand.
- Block A's `read_lock` census magnitude is 1 in each cell, under the naming
  floor of 2, while the frozen definition's floor is 5; the two are reported
  side by side and are not each other.

## What this does not establish

- **No rate and no capability claim.** Eight cells on one model in one run on
  one day support presence/absence counts and nothing finer. `0 of 8` is an
  absence in eight cells, not an estimate that the pathology never occurs, and
  `1 of 8` is one observation. No power figure, interval or significance test
  is computed and none was authorized.
- **No comparison.** Nothing here is compared with gemma, with any other
  model, or with one arm against another, and no count pools with the
  2026-09-09 Ornith probe or any earlier run. The counts that motivated the
  choice of tasks and pathologies are outside this denominator.
- **No outcome claim.** The `pass` verdicts and `COMPLETE` codes in the
  orientation column are not the measures. Pass/fail rates are not asked and
  are not reported.
- **No Engine arm and no architecture claim.** Baseline only; nothing was
  changed in the engine or the instrument, and the one reading adaptation
  forced by the session transcript's shape (the payload unwrap) is stated
  above with the check that validates it.
- **Pathology 3's session half reads a detector, not an independent audit.**
  `scope_violations` is the harness's own derivation over captured changed
  paths; the phase-patch union check above corroborates it but uses the same
  patches the detector reads.
- **The eight cells differ in task by block**, so the counts are per pathology
  across all eight, per the frozen rule; they are not eight samples of one
  task.

## Task-tree digests, re-verified after the run

Recomputed with the record's walk, after the last cell, in the same worktree:

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
| A | `agentclinic-repair-misleading-locus` | `93dc90eaed73b9999d4ddee14949eea0f2bf0aa8584408c4ed7557ce87b45522` | `93dc90eaed73b9999d4ddee14949eea0f2bf0aa8584408c4ed7557ce87b45522` | none |
| B | `agentclinic-complaint-lifecycle` | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` | none |

No drift: both task trees are byte-identical to their frozen values. As the
record states, the Baseline `run` command carries no `--task-tree-sha256`
flag, so these digests are a recorded identity, not a command-enforced gate.

## Retention and revision

Output root `/Users/pauleveritt/satyrn-smokes/2026-09-13-ornith9b-pathology-probe/`
holds `launch.sh`, `schedule.json`, `run.log` (per-cell start/end timestamps
and the model-loadability check) and the eight cell directories. Each attempt
cell holds its `transcript.txt`, `attempt.json`, `receipt.json`, `patch.diff`,
`summary.json` and the engine contract it ran under; each session cell its
`transcript.jsonl`, `session-record.json`, four phase patches, four receipts,
four snapshots and four checkpoints. Nothing was discarded and no cell was
re-run. The evals revision for the run is this worktree's `HEAD` at the
pre-run record's commit `41c0671`; the pre-run record's own commit precedes
it. No merge to `main`.
