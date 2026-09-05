# V9 P6 — Documentation, the stated forgery limit, and the verification record

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** State T9 (the oracle-result forgery limit) beside BRIEF rule 4
and in the trust-boundaries topic; bring the public docs current with
V9's commands, record fields, and summary fields; add the V9 row to the
ROADMAP phase table; record the verification run in `docs/sdd.md`.

**Architecture:** Documentation and records only — no production code. The
BRIEF note follows the file's recorded-amendment style; the ROADMAP row
follows the V6/V7/V8 row pattern; the verification record follows the V4/V6
pattern in `docs/sdd.md` and is written from real command output, never
asserted.

**Tech Stack:** Markdown, Sphinx terms (`{term}`), and the repo's own
`just lint-docs` checker.

**Spec:** `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md`
§9 (T9), done-when 14, §11 (verification shape). Depends on P1–P5b landed
and their default + integration suites green.

## Global Constraints

- **No commits.** Commits are maintainer-controlled (`docs/sdd.md`).
- **Verify, don't assert.** Every number in the verification record comes
  from a command run in this task; carry the command next to the number.
- Document caps are enforced (`just lint-docs`): ROADMAP ≤400, specs and
  plans ≤400, BACKLOG ≤400. Check after every edit.
- Default tier must stay green and the 100% coverage gate must pass with
  `-m ''` (this task runs it for the first time across all of V9 and fixes
  any residual uncovered branch by adding a test, not by deleting code).
- The strict Sphinx build (`uv run --group docs sphinx-build -W -b html
  docs docs/_build/html`) must pass — `{term}` targets must exist.

---

### Task 1: State T9 — BRIEF rule 4 note and the trust-boundaries topic

**Files:**
- Modify: `BRIEF.md`, `docs/topics/trust-boundaries.md`
- Test: none (docs), but a stale-forged-result test already exists at
  `tests/test_verdict.py:69` — confirm it runs green and references it in
  the note.

- [ ] **Step 1: Amend BRIEF rule 4**

After BRIEF rule 4's paragraph (BRIEF.md:76-79) append, in the file's
recorded-amendment style:

```
> **Recorded amendment (V9, 2026-09-04).** A stated limit beside this rule:
> the result file's path is in the oracle's environment, and the loader
> checks shape, internal consistency, and freshness only. Model code
> imported at collection time — which runs in the oracle's process — can
> write a shape-valid, fresh result file and exit 0 without running the
> tests, forging a pass. Standing mitigations: the path is reserved and
> unlinked before the run, the graded tree is grading's private copy, and
> the oracle's stdout/exit code are never read. There is no binding of the
> result to the process that produced it; that is the seam's stated limit,
> not a fixed property. See the V9 design spec §9 and the trust-boundaries
> topic.
```

- [ ] **Step 2: Extend the trust-boundaries topic**

In `docs/topics/trust-boundaries.md`, after the "A receipt is evidence; a
process status is not" section, add:

```
## A result file is checked for shape, not for authorship

The oracle result path is reserved by grading, unlinked before the run, and
validated for shape, internal consistency, and freshness against the run's
start. What the loader cannot check is *who wrote it*: the path is in the
oracle's environment, and code the oracle imports at collection time runs in
the same process. Model code could write a shape-valid result and exit
without running the tests. Evals does not claim to bind a result to its
producer; the verdict never comes from stdout or an exit code, and the
result file is not signed. This is a limit of the seam, stated here and in
the brief.
```

- [ ] **Step 3: Verify the stale-forgery test exists and passes**

Run: `uv run pytest -q tests/test_verdict.py -k stale`
Expected: PASS — the loader's freshness check is the one defense that
exercises without a model (spec done-when 12).

- [ ] **Step 4: Check docs lint and line caps**

Run: `uv run python tools/lint_docs.py`
Expected: all within cap (BRIEF.md has no cap; ROADMAP/BACKLOG/specs/plans
unchanged by this task).

### Task 2: Public docs — formats, CLI reference, guide

**Files:**
- Modify: `docs/reference/formats.md`, `docs/usage.md`,
  `docs/guides/run-a-diagnostic-batch.md`

- [ ] **Step 1: formats.md — attempt record**

In `docs/reference/formats.md`'s "Attempt directory and record" section:

1. Add `timeout` to the `attempt.json` example object (with the other
   scalars, e.g. after `command_exit`):

```json
  "timeout": 900.0,
```

2. After the refusal paragraph, add a paragraph and a code sample:

```
An admitted attempt whose grading did not complete is recorded with code
`GRADE_FAILED`: outcome `attempted`, no verdict, no receipt — the patch and
transcript are preserved and the cell is visible to `regrade`. The record is
written before grading starts, so a grading failure never leaves an invisible
cell:

```json
{
  "version": 1, "outcome": "attempted", "code": "GRADE_FAILED",
  "message": "attempt preserved and admitted; grading did not complete: <exception>",
  "patch_path": "patch.diff", "transcript_path": "transcript.txt",
  "verdict": null, "receipt_path": null
}
```
```

3. Note the `timeout` field and the generations sentence: records written
   by V9 always carry `timeout`; older generations load without it.

- [ ] **Step 2: formats.md — run summary and re-scoring**

In the "Run summary" section, extend the field table with three rows and
close with the re-score loop:

| `task` | the task name from the attempt records |
| `command` | the effective attempt command from the records (including any engine-contract suffix) |
| `timeout` | the attempt timeout in seconds |

```
A summary can be rebuilt from disk: `satyrn-evals summarize OUTPUT_DIR`
recomputes `summary.json` from the preserved attempt records through the
same tally `run` uses, so a rebuilt summary is byte-identical to the run's
own. `satyrn-evals regrade ATTEMPT_DIR` re-runs the grader over a preserved
patch and rewrites its receipt and record — the executable form of
re-scoring without re-running an attempt.
```

- [ ] **Step 3: usage.md — the new subcommands**

Append two sections after the `run` section of `docs/usage.md`, following
the file's existing heading/exit-code/example shape:

```
## summarize

Rebuild `summary.json` for a run output directory from the preserved
attempt records. Uses the same tally as `run`, so the rebuilt file matches
the run's own byte-for-byte.

```console
satyrn-evals summarize OUTPUT_DIR [--tasks-root DIR]
```

- `OUTPUT_DIR` — a run output directory holding `<task>-<stamp>`
  attempt directories, each with an `attempt.json`.
- `--tasks-root DIR` — task root; default the bundled tasks.

Exit codes: `0` — summary written; `2` — not a directory, no attempt cells,
or an unknown task; `3` — an attempt record or receipt that exists but
cannot be read, or inconsistent identity across cells.

## regrade

Re-run the grader over one preserved attempt's patch and rewrite its
receipt and record — re-scoring without re-running the attempt.

```console
satyrn-evals regrade ATTEMPT_DIR [--tasks-root DIR]
```

- `ATTEMPT_DIR` — an attempt directory holding `attempt.json`,
  `patch.diff`, and the preserved transcript.
- `--tasks-root DIR` — task root; default the bundled tasks.

A `GRADE_FAILED` or `OK` record is re-graded and its record updated to
`OK` with the new verdict. A refusal record has nothing to grade — a note
is printed and the command exits `0`. Exit codes: `0` — graded pass or
fail (or nothing to grade); `2` — not an attempt directory, identity
mismatch, or unknown task; `3` — verdict unavailable or an unreadable
record.
```

- [ ] **Step 4: guide — the re-score workflow**

In `docs/guides/run-a-diagnostic-batch.md`, after the "Run the batch"
section, add:

```
## Re-score without re-running

If a grader defect is found after a run, fix the grader and re-score the
preserved patches — no model re-run:

```console
$ satyrn-evals regrade runs/engine/agentclinic-repair-plausible-wrong-fix-20260904-160143
$ satyrn-evals summarize runs/engine
```

`regrade` re-runs the grader over the preserved patch and rewrites the
attempt's receipt and record; `summarize` rebuilds `summary.json` from the
records on disk. A cell whose grading failed mid-run is recorded with code
`GRADE_FAILED` and is exactly what `regrade` is for.
```

- [ ] **Step 5: Verify docs**

Run:
`uv run python tools/lint_docs.py`
and
`uv run --group docs sphinx-build -W -b html docs docs/_build/html`
Expected: both pass.

### Task 3: ROADMAP phase row for V9

**Files:**
- Modify: `ROADMAP.md`

- [ ] **Step 1: Add the phase-table row**

Insert a V9 row at the top of the phase table (before V1), matching the
existing row format. The **Direction** cell states what V9 ships; the
**Excludes** cell is the spec's non-goals in condensed form; the **Status**
cell is "in progress — design spec confirmed 2026-09-04" (flipped to
complete at close-out by the maintainer).

| # | Phase | Direction (one sentence) | Excludes | Status |
|---|-------|--------------------------|----------|--------|
| V9 | Loop integrity and re-scoring | `run` survives a failing cell and writes every cell's record before grading; summaries name task/command/timeout; `regrade ATTEMPT_DIR` and `summarize OUTPUT_DIR` rebuild receipts and summaries from disk; T5–T8 fixed with refusal/success siblings; T9 stated; the 30 s attempt default raised | transcript metrics (V10); the ladder (V11); model profiles (V12); probes (V13); weight (W1); session re-scoring; any model run — see the design spec's non-goals | **in progress** — design spec `2026-09-04-v9-loop-integrity-and-rescoring-design.md` confirmed 2026-09-04; plans p1–p6; verification record lands in `docs/sdd.md` |

- [ ] **Step 2: Check the cap**

Run: `uv run python tools/lint_docs.py`
Expected: all within cap. ROADMAP has ~94 lines of headroom; the row must
stay a single table row (no wrapped lines inside a row).

- [ ] **Step 3: Note the V5b amendment**

Append a recorded-amendment note to
`docs/superpowers/specs/2026-09-02-v5b-diagnostic-loop-design.md`'s "Data
shapes" section:

```
> **Recorded amendment (V9, 2026-09-04):** the summary now also names its
> arm. `summary.json` gains `task`, `command`, and `timeout`, derived from
> the attempt records; the attempt record gains a `timeout` field; a new
> code `GRADE_FAILED` (outcome attempted, no verdict) represents an
> admitted cell whose grading did not complete, counted in `code_counts`
> beside the verdict tallies. `regrade ATTEMPT_DIR` and `summarize
> OUTPUT_DIR` make rule 3 executable. See
> `2026-09-04-v9-loop-integrity-and-rescoring-design.md`.
```

(The V7 §5 supersession note is added by plan P5 Task 2 Step 5; if it has
not landed, do it here.)

### Task 4: The verification record in docs/sdd.md

**Files:**
- Modify: `docs/sdd.md`

- [ ] **Step 1: Run the full gates and record real output**

Run each command and paste its tail into a new `## V9 verification record`
section at the end of `docs/sdd.md`, in the V4/V6 pattern:

1. `uv run pytest -q` (default tier counts)
2. `uv run pytest -q -m integration tests/integration --ignore=tests/integration/test_local_pings_bundled.py`
   (integration counts; the bundled local-pings exclusion is the V7-record
   precedent)
3. `uv run pytest -q -m '' --ignore=tests/integration/test_local_pings_bundled.py --cov=src/satyrn_evals --cov-branch --cov-report=term-missing --cov-fail-under=100`
   (100% statement-and-branch gate — fix any residual uncovered branch
   with a test in the appropriate tier before recording)
4. `uv run ruff check .`, `uv run python tools/lint_docs.py`, `uv run --group docs sphinx-build -W -b html docs docs/_build/html`, `git diff --check`
5. The V9 named evidence, each with its command:
   - the T5 divergent pair: `uv run pytest -q tests/integration/test_grade_preservation_auto_overlay.py -m integration` (names `mini-session-divergent`);
   - the `regrade`/`summarize` round trip: `uv run pytest -q tests/integration/test_rescore.py -m integration`;
   - the T7 wheel demonstration — build a real wheel into a scratch venv
     that also carries a conflicting `fastapi`, and grade the bundled
     `agentclinic-repair-plausible-wrong-fix` known-good from that venv:

```bash
SCRATCH=$(mktemp -d)
uv build --out-dir "$SCRATCH/dist"
uv venv "$SCRATCH/venv" --python 3.14
uv pip install --python "$SCRATCH/venv/bin/python" "$SCRATCH"/dist/*.whl \
    "fastapi==0.116.0"            # a version that conflicts with the task lock
"$SCRATCH/venv/bin/satyrn-evals" grade \
    --tasks-root src/satyrn_evals/tasks \
    agentclinic-repair-plausible-wrong-fix \
    src/satyrn_evals/tasks/agentclinic-repair-plausible-wrong-fix/fixtures/known-good.patch \
    --receipt "$SCRATCH/receipt.json"
python -c "import json;r=json.load(open('$SCRATCH/receipt.json'));print(r['verdict']);print(r['resolved_versions'].get('fastapi'))"
```

   Record: the verdict is `pass`, and `resolved_versions["fastapi"]` names
   the *task lock's* version (0.115.10 per the V8 record), never the
   scratch venv's 0.116.0 — the proof that the oracle ran against the
   locked environment. If the network/cache prevents `uv sync` of the task
   env in this run, record the command, the failure, and that the run must
   be repeated where the V8 agentclinic gate can sync — do not assert a
   pass you did not observe.

- [ ] **Step 2: Name the fixture discrimination**

In the record, name the V9 evidence-floor pairs in prose, asserted by
fixture: T5's `mini-session-divergent` (old call shape `UNAVAILABLE`, new
shape `PASS`); T6's `0o664` overlay load (success) vs the remaining
stored-file refusals; T8's hostile-ambient-git trap-repo test; the
`GRADE_FAILED`/`OK` refusal-success pair in `tests/test_attempt.py`.

- [ ] **Step 3: Final whole-tree check**

Run: `uv run pytest -q`, `uv run ruff check .`,
`uv run python tools/lint_docs.py`, and `git diff --check` one last time.
Expected: all clean. Leave the worktree uncommitted for maintainer review
and close-out.
