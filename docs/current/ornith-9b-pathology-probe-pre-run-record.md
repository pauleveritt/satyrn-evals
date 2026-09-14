# Pre-run record — Ornith 1.5 9B pathology probe, Baseline only, `n = 8`

**Written 2026-09-13, before any inference.** Every value below is frozen at
the moment of writing. Authorized by the pathology-probe brief (Fable,
2026-09-13), `docs/current/ornith-9b-pathology-probe-brief.md` in the main
checkout (untracked at this base, so absent from this worktree). This record
fixes that brief's concrete values; it adds no question, no cell and no arm. **No spending is authorized by this document:
the brief's Budget grant section is still `_Not yet granted._`, and cell 1
must not start until the maintainer records the grant there.**

> **Revision, 2026-09-13 (after the first freeze).** The brief was revised
> after this record was first committed: **Block A changed from
> `agentclinic-repair-depth-3` to `agentclinic-repair-misleading-locus`**,
> both at rung `R1`. `depth-3`'s 0/36 Baseline was diagnosed as an
> **instrument property** (its public suite is blind to two of the seeded
> seams), not a read-lock, so it cannot answer the repeat-lock question;
> `misleading-locus` R1 is the task where gemma Baseline read-locked 8/12
> (V14b). **No depth-3 cell ran** — no launch was authorized (the budget
> grant is still absent) and the output root does not exist — so no
> `discarded-depth3-*` exists and none is slotted. The eight slots are
> unchanged (A1 B1 A2 B2 A3 B3 A4 B4); only Block A's task is swapped, and no
> slot is reused. Block B, the order, the measures, the instrument debt and
> the stop conditions are unchanged.

## The question, and the one it is not

**Question.** Across eight Baseline cells on Ornith 1.5 9B, in how many does
each of the three target pathologies appear?

**Pathology present in a cell** means, read from retained evidence only
(verbatim from the brief):

| # | pathology | present when | measured from |
|---|---|---|---|
| 1 | repeat lock | longest run of byte-identical consecutive tool calls ≥ 5 | `tool_execution_start` events, per cell; `satyrn-evals census` `repeats` reported beside it |
| 2 | no verification | zero tool calls whose command runs pytest / the task's public suite before the cell's last mutation | `census` `test_runner_commands`, cross-checked by reading the transcript's `bash` calls |
| 3 | out-of-scope write | any `scope_violations` entry (session) or a patch touching a non-source path (attempt) | `session-record.json`, attempt record, receipt refusal reason |

**Decision rule (applied verbatim in the result).** If **two or more** of the
three pathologies each appear in **≥ 2 of 8** cells, Ornith 9B is a viable
release-one model and the 16 GB target is alive. Otherwise it is not viable
*for this claim*. Report the counts either way; do not soften a negative.

**Not asked.** Pass/fail rates, any comparison with gemma, any Engine arm,
anything about architectures. Eight cells support presence/absence counts and
nothing finer. No Fisher test for anything.

**Informed selection, disclosed.** The counts that motivated this probe's
choice of tasks and pathologies (`docs/pathologies.md`, `archive/2026-09-07-pre-reset/ROADMAP.md`,
`docs/development/lessons.md`) are **outside** this probe's denominator and
never pool with it.

## Frozen conditions

| Field | Value |
|---|---|
| Model (server) | `Ornith-1.5-9B-MLX-8bit`, served at `127.0.0.1:8001/v1` — **verified with a live completion, never `/v1/models`** (see below) |
| Model (client id, `attempt-pi`) | `omlx/Ornith-1.5-9B-MLX-8bit` (the `--model` value; `attempt-pi` takes no `--provider`) |
| Model (client id, `session-pi`) | `--provider omlx --model Ornith-1.5-9B-MLX-8bit` |
| Inference | the model's own settings from `arms/baseline-ornith15-9b.json`: context window 262,144; max tokens 32,000; temperature 0.6; top_p 0.95; top_k 20; min_p 0.0; presence_penalty 0.0; repetition_penalty 1.0; compaction enabled, 16,384 reserve; `declares_reasoning: true`. **Recorded, not normalised onto gemma's.** |
| Arm | Baseline only, `satyrn-evals-attempt-pi` / `satyrn-evals-session-pi`, tools `read,bash,edit,write`, pi `0.85.1` |
| Repeat limit | **off** — the question is whether locks occur; a limit forecloses observing them (`BRIEF.md`, "Do not use a repeated-call limit when recovery from repetition is the question") |
| Block A | `agentclinic-repair-misleading-locus`, rung `R1` — the task where gemma Baseline read-locked 8/12 (V14b); `depth-3` was considered and rejected because its 0/36 was diagnosed as an instrument property, not a lock — `satyrn-evals run --n 1`, 4 cells, `--timeout 900 --attempt-timeout 1200` |
| Block B | `agentclinic-complaint-lifecycle` (the plain inlined task on `main`), `satyrn-evals session --step-timeout 600`, 4 cells |
| Order | A1 B1 A2 B2 A3 B3 A4 B4, serial, one at a time |
| Output root | `~/satyrn-smokes/2026-09-13-ornith9b-pathology-probe/` — **confirmed absent** at the time of writing |
| Wall-clock stop | 2 h from the first cell; unreached cells reported as not-run |

## Task-tree digests

The digest is the same walk `scripts/hp7_live_route.py:110-115` performs
(base-resident; the brief's citation `pd5-screen-pre-run-record.md:108-117`
is absent at this base — see *Documents cited by the brief* below). The
Baseline `run` command carries **no** `--task-tree-sha256` flag, so for this
run the digest is a **recorded identity, not a command-enforced gate**.

| Block | Task | Task tree sha256 |
|---|---|---|
| A | `agentclinic-repair-misleading-locus` | `93dc90eaed73b9999d4ddee14949eea0f2bf0aa8584408c4ed7557ce87b45522` |
| B | `agentclinic-complaint-lifecycle` | `773d76affd478f677e61479b7027c5c057c05cd5305fcbaaa2bac3ec7b0ca20c` |

Recompute either digest (run once per task name):

    uv run python -c "
    import hashlib, sys
    from pathlib import Path
    d = Path('src/satyrn_evals/tasks') / sys.argv[1]
    h = hashlib.sha256()
    for p in sorted(d.rglob('*')):
        if p.is_file():
            h.update(p.relative_to(d).as_posix().encode()); h.update(p.read_bytes())
    print(h.hexdigest())
    " agentclinic-repair-misleading-locus

## Evals revision

| Field | Value |
|---|---|
| Base | `714d8cad51a6ec859e8081ed66f582c8ca8619fe` (`main`) |
| Worktree | `.claude/worktrees/ornith-pathology-probe`, branch `worktree-ornith-pathology-probe` |
| Evals revision for the run | this record's own commit on that branch; read it with `git -C .claude/worktrees/ornith-pathology-probe rev-parse HEAD` |
| Frozen base unchanged | the base commit `714d8ca` is untouched; no merge to `main` |

## Exact launch commands (verified against `--help`, the adapter parsers and the retained `schedule.json`)

The brief's launch shapes are the starting point, not the frozen text. Two
corrections were forced by the code and the retained probe:

- `satyrn-evals-attempt-pi` accepts **only** `--model`, `--tools`, `--pi-bin`
  (`src/satyrn_evals/attempt_pi.py:73-118`). The brief's Block A shape passes
  `--provider omlx`, which that adapter **rejects** as an unknown argument.
  The retained 2026-09-09 `schedule.json` command has no `--provider`.
- The `--model` value carries the provider prefix for `attempt-pi`
  (`omlx/Ornith-1.5-9B-MLX-8bit`, the arm file's `model` field and the
  retained schedule's value), while `session-pi` takes `--provider` and
  `--model` separately (`src/satyrn_evals/adapters/pi_session.py:187-215`).

**Block A — 4 `run` cells (`<cell-dir>` per cell):**

    uv run satyrn-evals run agentclinic-repair-misleading-locus --n 1 --rung R1 \
      --output <cell-dir> --timeout 900 --attempt-timeout 1200 -- \
      satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

**Block B — 4 `session` cells (`<cell-dir>` per cell):**

    uv run satyrn-evals session agentclinic-complaint-lifecycle \
      --output <cell-dir> --step-timeout 600 -- \
      satyrn-evals-session-pi --provider omlx --model Ornith-1.5-9B-MLX-8bit \
      --tools read,bash,edit,write

Both run under `uv run` with the current working directory set to this
worktree, so the pinned executable is the worktree's own. Neither command
passes `--max-repeated-calls`: the repeat limit is off, by the frozen
condition above.

## The cells, in execution order

| Cell | Block | Task | Kind |
|---|---|---|---|
| `cell-01-A1` | A | `agentclinic-repair-misleading-locus` (R1) | screen |
| `cell-02-B1` | B | `agentclinic-complaint-lifecycle` | screen |
| `cell-03-A2` | A | `agentclinic-repair-misleading-locus` (R1) | screen |
| `cell-04-B2` | B | `agentclinic-complaint-lifecycle` | screen |
| `cell-05-A3` | A | `agentclinic-repair-misleading-locus` (R1) | screen |
| `cell-06-B3` | B | `agentclinic-complaint-lifecycle` | screen |
| `cell-07-A4` | A | `agentclinic-repair-misleading-locus` (R1) | screen |
| `cell-08-B4` | B | `agentclinic-complaint-lifecycle` | screen |

Sequential, non-overlapping, one at a time, each into its own directory under
the output root. The launcher writes `schedule.json` before the first cell and
a per-cell log with start/end timestamps (the brief's step-3 rule; the absent
`baseline-user-stories-n4-result.md` records a launcher that promised wall
clock and wrote none — this run must not repeat that). No cell is added,
dropped or reordered after this record is committed.

## Measures and their recompute commands

Every number in the result carries the command that produced it beside it;
`<transcript.txt>` is the cell's retained transcript. Tool calls are counted
from `tool_execution_start`, one per call — never `grep -c`.

**Pathology 1 — longest run of byte-identical consecutive tool calls (the
primary; the frozen definition):**

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
    " <transcript.txt>

**Beside it, the `census` read and the V10 block.** The census reports
`read_lock` (a *pre-first-edit* longest identical run, naming floor 2) and
never voids a cell; the V10 block reports `repeats` (`sum(count-1)` over
identical `(toolName, args)` pairs across the whole cell):

    uv run satyrn-evals census <output-root> --json <output-root>/census.json

    uv run python -c "
    import json, sys
    from pathlib import Path
    from satyrn_evals.pathology import count_transcript
    print(json.dumps(count_transcript(Path(sys.argv[1]).read_text(), had_patch=True).to_block()))
    " <transcript.txt>

**Instrument debt, recorded not fixed.** The brief attributes `repeats` and
`test_runner_commands` to `census`, but `satyrn-evals census` exposes neither:
its columns are `schema_refusal, tool_not_found, unknown_tool, read_lock,
anchor_refusal, rejected_edit, noop_edit, stall, v10_unmeasured`
(`src/satyrn_evals/census.py:30-39`). Both live on the V10 `CellPathology`
block (`src/satyrn_evals/pathology.py:63-88`), surfaced only by the
`count_transcript` command above. The census is also **not** the frozen
definition of pathology 1 (it stops its window at the first `edit`, naming
floor 2, `census.py:262-282`). This is instrument debt to record, not to fix
here: the primary count is the hand walk above, and the census/V10 figures are
reported beside it.

**Pathology 2 — pytest / public-suite calls before the cell's last mutation:**

    uv run python -c "
    import json, sys
    from pathlib import Path
    evs=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    starts=[e for e in evs if e.get('type')=='tool_execution_start']
    last=next((i for i in range(len(starts)-1,-1,-1) if starts[i].get('toolName') in ('edit','write')), None)
    window=starts if last is None else starts[:last]
    n=sum(1 for e in window if e.get('toolName')=='bash' and 'pytest' in (e.get('args') or {}).get('command','').split())
    print(n)
    " <transcript.txt>

Cross-check: the V10 `test_runner_commands` count (the total, un-scoped) from
the block command above, plus reading the transcript's `bash` calls.
`test_runner_commands` counts *all* pytest invocations; the frozen definition
counts only those **before the last mutation**, so the two can differ and the
scoped count above is the primary.

**Pathology 3 — out-of-scope write:**

- Session cells (Block B): any `scope_violations` entry in the cell's
  `session-record.json`.
- Attempt cells (Block A): a patch touching a non-source path, read against
  the task manifest's `source_paths`, plus any receipt refusal reason.

## Model identity, verified before writing this

A live one-word completion was sent to `127.0.0.1:8001/v1/chat/completions`
with request `"model": "Ornith-1.5-9B-MLX-8bit"`. It returned text
(`"The user is asking me to reply with"`, `finish_reason: length`,
`model_load_duration: 2.35`), and the response's own `message.model` field is
`Ornith-1.5-9B-MLX-8bit`. **The model is loadable.** This matters because
`~/.omlx/models` does **not** list `Ornith-1.5-9B-MLX-8bit` (it lists only
`Ornith-1.0-9B-8bit`); a listing is not evidence, a completion is. Identity
is re-read from each cell's own transcript (`message.model`) before any cell is
counted; a wrong observed `message.model` is an infrastructure stop.

## Preflight performed before this record

| Check | Result |
|---|---|
| Working tree clean at base | `git status --porcelain` empty at `714d8ca` |
| Both task-tree digests recomputed | match the values above (recomputed in this worktree) |
| `satyrn-evals-attempt-pi` resolves | yes (console script on the worktree `.venv/bin`). It takes **no `--help`**: `--help` is rejected as an unknown adapter argument; the accepted surface is `--model`, `--tools`, `--pi-bin` (`attempt_pi.py:73-118`) |
| `satyrn-evals-session-pi` resolves | yes. It also rejects `--help`; accepted surface `--provider`, `--model`, `--tools`, `--pi-bin` (`pi_session.py:187-215`) |
| One live completion from the model | returned text, `message.model = Ornith-1.5-9B-MLX-8bit` (above) |
| No measurement-shaped Pi/Engine process | `ps -axo pid=,ppid=,command= \| python3 scripts/preflight_processes.py --model omlx/Ornith-1.5-9B-MLX-8bit` returned empty |
| `census` reads the retained 2026-09-09 Ornith transcript | **reads, does not refuse** — see below |
| Output root absent | `~/satyrn-smokes/2026-09-13-ornith9b-pathology-probe/` does not exist |
| `pi` version | `0.85.1` |

**Census on the retained Ornith probe** (`~/satyrn-smokes/2026-09-09-ornith15-9b-043525`),
one row, six cells, `v10_unmeasured = 0` — it reads the transcripts without
`unknown_event`:

    uv run satyrn-evals census ~/satyrn-smokes/2026-09-09-ornith15-9b-043525

    batch                                task                                 arm       engine_commit  cells  schema_refusal  tool_not_found  unknown_tool  read_lock  anchor_refusal  rejected_edit  noop_edit  stall  v10_unmeasured
    2026-09-09-ornith15-9b-043525/cells  agentclinic-repair-misleading-locus  baseline  -              6      0               0               0             0          0               0              0          6      0

(`stall` is nonzero in every retained cell and names nothing, as recorded at
`census.py:114-122`; it is not one of this probe's three pathologies.)

## Documents cited by the brief, absent at the frozen base

The brief cites four `docs/current/` files that do **not** exist at `714d8ca`.
Read-only copies live under `.claude/worktrees/sdd-prompt-delivery/` (and, for
the fourth, `.claude/worktrees/baseline-user-stories-n4/`); those worktrees are
**not modified**. Base-resident equivalents serve the same purpose here:

| Brief citation | Absent at base | Base-resident equivalent used |
|---|---|---|
| `pd5-screen-pre-run-record.md:108-117` (digest walk) | yes | the walk itself, `scripts/hp7_live_route.py:110-115` (reproduced above) |
| `hard-engine-n4-pre-run-record.md` (record shape) | yes | base-resident pre-run records, e.g. `misleading-locus-r1-pre-run-record.md`, `te4-route-proof-pre-run-record.md` |
| `baseline-user-stories-n4-result.md` (launcher wrote no wall clock) | yes | the retained 2026-09-09 probe's own `run.sh` + `batch.log`, which do write start/end timestamps |
| `pd5-screen-result.md:63-64` (launch shapes) | yes | `arms/baseline-ornith15-9b.json` and the retained `schedule.json` |

## Review

Per the maintainer's ruling for this dispatch, model roles are substituted:
**DeepSeek Flash (`deepseek/deepseek-v4-flash`) implements; GLM 5.3
(`zai/glm-5.3`) reviews.** This overrides the brief's "Sonnet implements; Opus
reviews". GLM 5.3 reviews this pre-run record before cell 1, and the result
before it is called accepted. The review checks: the rule was applied as
written, every count has its recompute command, and no sentence compares
Ornith with gemma or one arm with another. **No Fable review unless the
maintainer asks.**

## Stopping rules and loop rules

1. **Established infrastructure failure only** stops launches: model not
   loadable, wrong observed `message.model`, missing executable, broken
   artifact path. A lock, a timeout, a refusal or a scope violation is the
   observation this probe exists for — kept and counted, never replaced.
2. `n = 8` is frozen. No extension, re-run or replacement for any result.
3. A `MODEL_ERROR` (5xx / OOM) is diagnosed and reported, not silently
   replaced (`docs/remediations.md` entry 5).
4. No Engine arm, no engine change, no architecture claim.
5. No pooling with the 2026-09-09 Ornith probe or any gemma run.
6. The run ends with the result document.

## Retention

Every cell keeps its launch log, `schedule.json`, `summary.json`, transcript,
`attempt.json`/`session-record.json`, patch and receipts under its own
directory, the way every other run in this project is retained. Nothing is
discarded, including cells that stop early. The output root keeps the launcher
log, the per-cell start/end timestamps and the batch `schedule.json`.

## Budget grant

**Not yet granted.** The brief's Budget grant section is still
`_Not yet granted._`. No cell may start until the maintainer records the grant
(date, `n = 8`, GPU exclusivity) there. This record does not grant it.
