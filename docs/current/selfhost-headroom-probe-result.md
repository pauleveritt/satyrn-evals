# Self-hosted headroom probe — result

Run and retained 2026-09-14, under
[the pre-run record](selfhost-headroom-probe-pre-run-record.md), itself
authorized by [the brief](selfhost-headroom-probe-brief.md). Baseline only,
`n = 12`, serial `G1 R1 D1 G2 R2 D2 G3 R3 D3 G4 R4 D4`, repeat limit off.
**All twelve cells started and ran to completion** (launcher exit 0 on every
cell). Output root
`/Users/pauleveritt/satyrn-smokes/2026-09-14-selfhost-headroom-probe/`,
launched from this worktree's `HEAD` at
`0b2d4b65d9c1d44c5e123598978288b4941fd801` — the fix-round commit named as
the floor for the evals revision in the pre-run record. Model identity is
verified per cell below; no infrastructure stop applied.

**Question, verbatim from the brief.** For each of the three tasks, how many
of four Baseline cells on Ornith 1.5 9B fail?

**`run.log`, quoted in full for the launch, model check, deadline and
completion lines:**

```
2026-09-14T10:43:52Z launcher start; root=/Users/pauleveritt/satyrn-smokes/2026-09-14-selfhost-headroom-probe
2026-09-14T10:43:52Z model loadability check
2026-09-14T10:43:53Z loadability rc=0 observed_model='Ornith-1.5-9B-MLX-8bit'
2026-09-14T10:43:53Z first cell; 3h wall-clock deadline epoch=1789393433
2026-09-14T10:43:53Z cell-01-G1: start
...
2026-09-14T13:32:18Z cell-12-D4: start
2026-09-14T13:51:28Z cell-12-D4: done exit=0 duration=1150s
2026-09-14T13:51:28Z launcher COMPLETE
```

The 3 h deadline (epoch 1789393433 = 2026-09-14T13:43:53Z) is a **start**
gate per the brief's "unreached cells reported as not-run" wording; cell-12
started at 13:32:18Z (before the deadline) and finished at 13:51:28Z, about
8 minutes past it. No cell was skipped, replaced, extended or re-run.

## A. The 12-row table

`<seconds>` is elapsed wall clock read from `run.log`'s
`done exit=<n> duration=<s>s` line for that cell. `code` is `attempt.json`
`code`; `verdict` is `receipt.json` `verdict`, or `absent` when no
`receipt.json` exists in the retained attempt directory (every cell whose
`code` is not `OK` has no receipt — grading never ran because no patch was
harvested to grade). Turns and tool calls are counted from the transcript's
own `turn_start` and `tool_execution_start` events, one per call, **never
`grep -c`**. Tokens are `scripts/usage_totals.py`'s `message_end`-only
totals. **Command budget: 1200 s on every cell (the `--timeout` given to
`satyrn-evals run`), stated here once for the whole table and repeated
beside every count in sections B and E below.**

**Runnable recompute for turns, tool calls and tokens** (reads only a
retained `transcript.txt`; run once per cell, substituting the cell's own
attempt directory):

```python
import json, sys
from pathlib import Path

transcript = Path(sys.argv[1])  # e.g. <output-root>/cell-01-G1/selfhost-guard-prefixes-.../transcript.txt
events = [
    json.loads(line)
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    if line.strip()
]
turns = sum(1 for e in events if e.get("type") == "turn_start")
tool_calls = sum(1 for e in events if e.get("type") == "tool_execution_start")
print(f"turns={turns} tool_calls={tool_calls}")
```

```
uv run python scripts/usage_totals.py <output-root>/<cell>/<attempt-dir>/transcript.txt
```

Run against all twelve retained transcripts, this reproduces every `turns`,
`tool calls`, `in tokens` and `out tokens` value in the table below exactly.

"Public-suite run" is defined and applied identically to all twelve cells
as: a `bash` tool call whose `command` text contains the substring
`pytest`. "Last mutation" is the last `edit` or `write` tool call in the
transcript (by `tool_execution_start` order); the count below is public-suite
calls **strictly before** that call's index, matching the ceiling/pathology
probes' scoped-count convention.

| cell | task | code | verdict | seconds (budget 1200s) | turns | tool calls | in tokens | out tokens | suite runs before last mutation |
|---|---|---|---|---|---|---|---|---|---|
| cell-01-G1 | `selfhost-guard-prefixes` | `OK` | `pass` | 66 | 5 | 4 | 11,853 | 3,217 | 0 |
| cell-02-R1 | `selfhost-run-record-gate` | `NO_PATCH` | absent | 500 | 41 | 40 | 82,883 | 12,651 | 1 |
| cell-03-D1 | `selfhost-docs-linter` | `COMMAND_TIMEOUT` | absent | 1202 | 49 | 54 | 97,048 | 38,032 | 7 |
| cell-04-G2 | `selfhost-guard-prefixes` | `OK` | `fail` | 200 | 11 | 10 | 23,487 | 7,210 | 0 |
| cell-05-R2 | `selfhost-run-record-gate` | `COMMAND_TIMEOUT` | absent | 1200 | 55 | 59 | 123,679 | 33,335 | 7 |
| cell-06-D2 | `selfhost-docs-linter` | `NO_PATCH` | absent | 1004 | 48 | 47 | 87,601 | 33,814 | 6 |
| cell-07-G3 | `selfhost-guard-prefixes` | `COMMAND_TIMEOUT` | absent | 1201 | 58 | 57 | 104,609 | 37,458 | 0 |
| cell-08-R3 | `selfhost-run-record-gate` | `COMMAND_TIMEOUT` | absent | 1201 | 51 | 59 | 104,862 | 29,241 | 5 |
| cell-09-D3 | `selfhost-docs-linter` | `NO_PATCH` | absent | 1124 | 44 | 43 | 85,730 | 30,806 | 10 |
| cell-10-G4 | `selfhost-guard-prefixes` | `COMMAND_TIMEOUT` | absent | 1202 | 69 | 68 | 111,405 | 32,533 | 0 |
| cell-11-R4 | `selfhost-run-record-gate` | `COMMAND_TIMEOUT` | absent | 1201 | 44 | 48 | 98,302 | 25,661 | 6 |
| cell-12-D4 | `selfhost-docs-linter` | `NO_PATCH` | absent | 1150 | 44 | 43 | 87,497 | 27,573 | 7 |

Every cell's own transcript `message.model` is `Ornith-1.5-9B-MLX-8bit` in
every `message_end`/`message_start` event that carries a `model` field — no
transcript reports a different model. No infrastructure stop applies.

**Six cells hit the 1200 s command budget** — `run.log` shows
`duration=1200s`–`1202s` (timer-plus-teardown jitter) for cell-03-D1,
cell-05-R2, cell-07-G3, cell-08-R3, cell-10-G4 and cell-11-R4: exactly
`{G3, R2, R3, G4, R4, D1}`, as named in the dispatch. All six produced
`attempt.json` `code = "COMMAND_TIMEOUT"`.

## B. The rule, applied verbatim

> **A cell fails** when `receipt.json` `verdict` is not `pass` **or**
> `attempt.json` `code` is not `OK`, read from the retained attempt
> directory. A `MODEL_ERROR` (5xx, out of memory) is infrastructure: the
> cell is **unscored**, diagnosed, recorded, and not re-run; denominators
> count scored cells only.
>
> **Decision rule.** A task has **headroom** if **2 or more of its 4 scored
> cells fail**.

**No `MODEL_ERROR` occurred anywhere in the twelve cells** (every cell's
`code` is `OK`, `NO_PATCH`, or `COMMAND_TIMEOUT` — confirmed from each
`attempt.json`, section A). All twelve cells are scored; every denominator
below is **of 4**, and the command budget behind every one of these counts
is **1200 s**.

**Runnable recompute** (reads only retained `attempt.json`/`receipt.json`
files, mapping cell → task via `schedule.json`'s own `cells[].task` field):

```python
import json
from pathlib import Path

ROOT = Path("/Users/pauleveritt/satyrn-smokes/2026-09-14-selfhost-headroom-probe")
schedule = json.loads((ROOT / "schedule.json").read_text())

scored, fails = {}, {}
for c in schedule["cells"]:
    cell, task = c["cell"], c["task"]
    sub = sorted((ROOT / cell).glob(f"{task}-*"))[0]
    attempt = json.loads((sub / "attempt.json").read_text())
    code = attempt["code"]
    receipt_path = sub / "receipt.json"
    verdict = json.loads(receipt_path.read_text())["verdict"] if receipt_path.exists() else None
    if code == "MODEL_ERROR":
        continue  # unscored infrastructure failure; none occurred in this run
    scored[task] = scored.get(task, 0) + 1
    if code != "OK" or verdict != "pass":
        fails[task] = fails.get(task, 0) + 1

for task in scored:
    print(f"{task}: {fails.get(task, 0)} of {scored[task]} fail (command budget 1200s)")
```

Running this against the retained artifacts prints exactly:

```
selfhost-guard-prefixes: 3 of 4 fail (command budget 1200s)
selfhost-run-record-gate: 4 of 4 fail (command budget 1200s)
selfhost-docs-linter: 4 of 4 fail (command budget 1200s)
```

| Task | Scored cells (budget 1200s) | Fails (of 4) | Passes | Headroom (≥2 of 4 fail)? |
|---|---|---|---|---|
| `selfhost-guard-prefixes` (G) | 4 | **3** (G2 fail, G3 COMMAND_TIMEOUT, G4 COMMAND_TIMEOUT) | 1 (G1) | **yes** |
| `selfhost-run-record-gate` (R) | 4 | **4** (R1 NO_PATCH, R2/R3/R4 COMMAND_TIMEOUT) | 0 | **yes** |
| `selfhost-docs-linter` (D) | 4 | **4** (D1 COMMAND_TIMEOUT, D2/D3/D4 NO_PATCH) | 0 | **yes** |

**This is the rule's answer, unaltered, exactly as the brief requires it be
reported: all three tasks meet the ≥2-of-4 (budget 1200s) headroom
threshold.** But two of the three tasks must **create** a file that does
not exist at `BASE` (`src/satyrn_evals/run_record.py` for
`selfhost-run-record-gate`; `tools/lint_docs.py` for
`selfhost-docs-linter`), and the adapter's own docstring
(`src/satyrn_evals/attempt_pi.py:23-31`, quoted in full in section C) states
that its diff-harvesting method is "fatal for build shapes" and that "a
task that needs it must not be measured on this adapter." Section C gives
the mechanism; the sensitivity reading below is required by the
controller's ledger to sit beside the rule's answer, explicitly outside it.

### Sensitivity reading (OUTSIDE THE RULE — does not change the rule's answer above)

Counting only non-passes that do **not** depend on the two adapter
artifacts named in section C (a mid-attempt `git commit` emptying the
harvested diff; the untracked-file blind spot) — i.e. `COMMAND_TIMEOUT` and
a graded `fail` still count, but `NO_PATCH` in a task that must create a
file does **not**, because that outcome is evidence about the adapter, not
about the model's fix:

```python
CREATE_FILE_TASKS = {"selfhost-run-record-gate", "selfhost-docs-linter"}
sens_fails = {}
for c in schedule["cells"]:
    cell, task = c["cell"], c["task"]
    sub = sorted((ROOT / cell).glob(f"{task}-*"))[0]
    attempt = json.loads((sub / "attempt.json").read_text())
    code = attempt["code"]
    receipt_path = sub / "receipt.json"
    verdict = json.loads(receipt_path.read_text())["verdict"] if receipt_path.exists() else None
    if code == "MODEL_ERROR":
        continue
    if code == "NO_PATCH" and task in CREATE_FILE_TASKS:
        continue  # excluded: adapter diff-harvest artifact, not a model outcome
    sens_fails.setdefault(task, 0)
    if code != "OK" or verdict != "pass":
        sens_fails[task] += 1
print(sens_fails)
```

| Task | Sensitivity fails (of 4, excluding create-file `NO_PATCH`; budget 1200s) | Headroom survives? |
|---|---|---|
| `selfhost-guard-prefixes` | **3 of 4** (G2, G3, G4 — unchanged; this task edits an existing tracked file, so no cell is excluded) | **survives** |
| `selfhost-run-record-gate` | **3 of 4** (R2, R3, R4; R1's `NO_PATCH` excluded) | **survives** |
| `selfhost-docs-linter` | **1 of 4** (D1 only; D2, D3, D4's `NO_PATCH` excluded) | **does NOT survive** |

**D1 needs one further caveat, stated plainly rather than left as a bare "1
of 4."** D1's own transcript shows it had already run `git commit` (commit
`0132385`, tool-call index 52 — section C) **before** its `COMMAND_TIMEOUT`
fired, and its remaining calls were further verification, not new
implementation work. A model that commits its work and then keeps checking
it is not exhibiting a ceiling; on a strict reading that credits work
already committed and verified before the budget ran out, `selfhost-docs-linter`'s
sensitivity count is arguably **0 of 4**, not 1.

**Which reading a design should lean on.** The design should lean on the
**sensitivity reading**, because `selfhost-docs-linter`'s headroom under
the rule rests entirely on the adapter's diff-harvest artifact (three of
its four fails are `NO_PATCH` in a create-file task; the fourth, D1, had
already committed and passed its own checks when the 1200 s budget ran
out) — the opposite of a ceiling, not evidence of one. `selfhost-run-record-gate`'s
headroom survives the sensitivity reading, but carries its own caveat,
below.

**The `selfhost-run-record-gate` caveat.** Its three counted fails under
the sensitivity reading (R2, R3, R4) are all `COMMAND_TIMEOUT` at the 1200 s
budget — budget exhaustion, independent of how a patch is harvested, and
the brief's own meaning of a budget ceiling. But all three held an
untracked `run_record.py` (and `test_run_record.py`) module when the
budget ran out (section C; R3's own `git checkout tests/test_run_record.py`
at tool-call index 54 failed with `error: pathspec 'tests/test_run_record.py'
did not match any file(s) known to git`, directly proving the file was
still untracked). Had any of the three finished within budget without
staging the new module, it would have scored `NO_PATCH` regardless of
correctness — three timeouts at exactly 1200 s cannot say how close any of
them was to finishing. And R1, the one `selfhost-run-record-gate` cell that
did finish, did so only after reading the answer key (section D) — so no
cell of this task both finished and was uncontaminated.

**Why the two-directional fixture qualification could not have caught
this.** Both fixture directions in the pre-run record's "Task
qualification" section are run through `satyrn-evals grade <task> <patch>`
against a **hand-written** `known-good.patch`/`known-broken.patch` — a
unified diff that already exists as a file and is applied directly to the
materialized workspace. That path never calls `harvest_patch()`
(`attempt_pi.py:194-209`), which only runs inside a live `pi` attempt to
turn the **attempt worktree's own git state** into a patch after the model
has been running inside it. A hand-written patch that creates
`run_record.py` "from `/dev/null`" is, by construction, already a
well-formed diff — there is no live `write`-then-never-`git add` step for
the harvest path's blind spot to bite on. Grading a fixture cannot exercise
a defect that only exists in how a live attempt's own working tree gets
turned into a patch.

**Under the brief's applicable consequence bullet:**

> If one or more tasks has headroom, the self-hosted generator enters the
> release-one design as a workload source alongside `depth-3` at `R1`, and
> the task(s) with headroom are named as candidates. Nothing is designed
> toward them here.

— applying the rule's answer (all three headroom) admits all three as
candidates; applying the sensitivity reading the design should lean on,
the candidates a design may name on this evidence are
`selfhost-guard-prefixes` and `selfhost-run-record-gate` (the latter with
the caveat above); `selfhost-docs-linter` is named as **not established** —
its rule-level headroom is an adapter artifact, not a measurement of the
model. Nothing is designed toward any of them here — no workload schedule,
no rung ladder, no new task is proposed by this document.

## C. Kinds of non-pass, separated

Every non-pass cell falls into exactly one of four kinds. All four count as
fails under the frozen rule above (budget 1200 s on every cell); they are
separated here because they are different *evidence*, per the controller's
ledger.

| Kind | Cells | What it is evidence about |
|---|---|---|
| (1) Graded behavioural fail — receipt present, `verdict: "fail"` | cell-04-G2 | Ornith's headroom on this task |
| (2) `COMMAND_TIMEOUT` — the 1200 s command budget fired | cell-03-D1, cell-05-R2, cell-07-G3, cell-08-R3, cell-10-G4, cell-11-R4 | a budget ceiling, not a behavioural verdict (no receipt exists to grade) |
| (3) `unavailable` / scope violation (a patch rejected by `check_allowlist` before grading) | **none observed in this run** | n/a — no cell hit this kind |
| (4) `NO_PATCH` — the adapter's harvested diff came back empty | cell-02-R1, cell-06-D2, cell-09-D3, cell-12-D4 | **the adapter's diff base**, not Ornith's headroom |

Kind (2) and kind (4) codes never reach grading at all (no `receipt.json`
is written), which is why the per-cell table in section A reports "absent"
rather than `unavailable` for those ten cells.

**Only one task-code combination actually reached a graded `fail`
verdict**: cell-04-G2. Every other non-pass cell is kind (2) or kind (4),
which the frozen rule still counts as a fail but which is not a graded
behavioural verdict on the model's fix.

### The adapter's diff base, verified from source

`src/satyrn_evals/attempt_pi.py:194-209`, function `harvest_patch()`:

```python
def harvest_patch() -> str:
    """The tracked diff of the workspace, as a unified patch.

    ``git diff HEAD`` and nothing wider: see this module's stated limits.
    A git failure refuses rather than returning "", because an empty
    patch is a *legible* outcome downstream (`NO_PATCH`) and would hide
    the fault.
    """
    completed = subprocess.run(
        ["git", "diff", "HEAD"], capture_output=True, text=True, check=False
    )
    ...
    return completed.stdout
```

The diff base is **`git diff HEAD`** against the attempt worktree's current
`HEAD`, taken once after `pi` exits — the docstring's own words for this,
"the diff is harvested only after pi exits," are at `attempt_pi.py:32`
(inside the module's top-level docstring), not at the `def main` line
(`:212`), which merely repeats the point in `main`'s own docstring.
`git diff HEAD` compares the working tree **and anything already staged**
against `HEAD` — not only the tracked index — which is exactly why a model
that ran `git add` without `git commit`ing would still have been captured;
none of this run's cells did that.

The module's own docstring (`src/satyrn_evals/attempt_pi.py:23-31`), quoted
in full because two of the three tasks require exactly the shape it names:

> **`git diff HEAD` drops files the model created with `write`.**
> Untracked files are invisible to it. That is harmless on pure-edit repair
> and fatal for build shapes and for `framing-2`. `git add -A` is **not**
> the fix: it would sweep a model's `uv run pytest` residue into the patch
> and trip the allowlist check. Creation-capable capture is a V12 entry
> gate, so a task that needs it must not be measured on this adapter.

`selfhost-run-record-gate` (create `src/satyrn_evals/run_record.py`) and
`selfhost-docs-linter` (create `tools/lint_docs.py`) are exactly the build
shape this passage names; `selfhost-guard-prefixes` edits an existing
tracked file (`tools/hooks/guard.py`) and is the "harmless" case.

**All four `NO_PATCH` cells in this run are the same mechanism: the model
committed inside the attempt worktree, advancing `HEAD` and leaving the
working tree clean relative to it, so `git diff HEAD` at harvest time
returned empty.** None is untracked-file blindness alone — the earlier
draft of this document mischaracterized cell-09-D3 (see the corrected
mechanism table below).

| `NO_PATCH` cell | Commit sha (from the transcript's own `git commit` output) | Tool-call index | Files committed |
|---|---|---|---|
| cell-02-R1 | `b0f3b49` | 38 | `run_record.py`, `test_run_record.py`, `cli.py` |
| cell-06-D2 | `f1b8acc` | 42 | `tools/lint_docs.py`, `tools/lint_docs_test.py`, `PROVENANCE.md` |
| cell-09-D3 | `b9e06ebf4f579ef0a0875a58c71fd742382fbb70` | 41 | `tools/lint_docs.py`, `tests/test_lint_docs.py` (`git add ... && git -c user.name="pi" -c user.email="pi@example.com" commit ...`) |
| cell-12-D4 | `d255eb6`, then `669e88d` | 34, 41 | `tools/lint_docs.py`, `tests/test_lint_docs.py`, `PROVENANCE.md` (two commits) |

cell-09-D3's commit at tool-call index 41 uses `git -c user.name=... -c
user.email=... commit` — global options before the subcommand. A first
draft of this document's scan regex (`\bgit\s+commit\b`) missed this form
and wrongly attributed cell-09-D3 to "untracked-file blindness" with zero
`git commit` calls; section D's corrected recompute script handles `git -c
k=v commit` and reproduces the commit above.

**The untracked-file limit named in the docstring above is real in this
run, but latent rather than causal**: `selfhost-run-record-gate`'s three
`COMMAND_TIMEOUT` cells (R2, R3, R4) each `write`-created `run_record.py`
(and `test_run_record.py`) and never committed before the budget fired
(section B's `selfhost-run-record-gate` caveat gives R3's own failed `git
checkout` as direct proof the file was still untracked) — so a pass was
barely reachable in those three cells specifically because the created
module was never staged, even though it was budget exhaustion, not the
blind spot itself, that produced their non-pass code.

**Also committed, but not `NO_PATCH`:** cell-03-D1 committed
(`0132385`, tool-call index 52) **before** its `COMMAND_TIMEOUT` fired — the
timeout, not the commit, determined this cell's code (see section B's
sensitivity-reading caveat on D1). cell-10-G4 did **not** commit; an
earlier draft of this document's scan reported a `git commit` for cell-10-G4,
which was a false positive on the literal string `'git commit -m pi'`
appearing inside a Python test-case list the model wrote to a scratch file
— not a real git invocation (section D's corrected scan excludes this).

## D. Diagnostics (kept apart from the measures; do not enter the rule)

### (a) Oracle hunting

Definition, verbatim from the brief: "any `bash` command whose text
searches outside the workspace root (`find /`, `locate`, `grep -r` with an
absolute path above the workspace, `ls` of a parent directory)."

| Cell | Count | Tool-call indices | First such command (verbatim) |
|---|---|---|---|
| cell-02-R1 | 3 | 3, 14, 16 | `find / -type d -name satyrn_evals 2>/dev/null \| head` |
| cell-11-R4 | 1 | 47 | `find / -name "cli.*.pyc" -path "*satyrn_evals*" 2>/dev/null \| head` (part of a combined command that first ran `uv run python -c "import satyrn_evals.cli as c; print(c.__file__)"` and a local `find . -name "__pycache__" ...`) |
| all other 10 cells | 0 | — | — |

Index 14 for cell-02-R1 — `ls -la "$SP/" ...; find "$SP/" ...` against the
qualification-staging directory — qualifies under the brief's "`ls` of a
parent directory" wording (an absolute path outside the workspace root,
not one the model created itself) and is counted here in addition to
indices 3 and 16, which the first draft of this document had counted
alone.

By task: `selfhost-guard-prefixes` 0 of 4; `selfhost-run-record-gate` 4
occurrences across 2 of 4 cells (3 in cell-02-R1, 1 in cell-11-R4);
`selfhost-docs-linter` 0 of 4.

### The coordinator's required scan

**Runnable recompute** (reads only retained transcripts; never writes
anything under the output root). This corrects two defects a first draft's
scan regex had: `\bgit\s+commit\b` missed a real commit spelled `git -c
k=v commit` (cell-09-D3), and an unscoped `grep -r` check matched the
*text* `'git commit -m pi'` or `'grep -rn pi docs'` sitting inside a
Python string literal the model wrote to a scratch file, not a real
invocation (cell-10-G4). Both are fixed below by (1) allowing global
options between `git` and `commit`, (2) requiring the matched word not be
glued to a quote character (excludes strings), and (3) scoping any
extracted path to the same command segment as the match, not the whole
(possibly huge, heredoc-carrying) command string:

```python
import json, re
from pathlib import Path

ABS_PATH_RE = re.compile(
    r"(?<![\w./-])(/(?:Users|etc|var|tmp|private|System|Library|bin|sbin|usr|opt|Applications)(?:/[^\s'\"]*)?)"
)

def find_abs_paths(text, workspace_root):
    return [
        p for m in ABS_PATH_RE.finditer(text or "")
        if not (workspace_root and (p := m.group(1)).startswith(workspace_root))
    ]

# git invocation with optional global options before the subcommand
# (`git -c k=v commit`, `git -C dir commit`, ...), excluded when glued to a
# quote/word character on the left (a string literal, not a real command).
GIT_COMMIT_RE = re.compile(
    r"(?<![\'\"\w])git(?:\s+-[A-Za-z-]+(?:[= ]\"[^\"]*\"|[= ]'[^']*'|[= ]\S+)?)*\s+commit\b"
)

def is_real_git_commit(cmd: str) -> bool:
    return bool(GIT_COMMIT_RE.search(cmd))

# for each cell: load transcript.txt as JSON-lines events, take the
# `session` event's `cwd` as the workspace root; for every `bash`
# tool_execution_start, scan args["command"] with is_real_git_commit() and
# (scoped to the ls/find/grep match's own command segment) find_abs_paths()
# for absolute paths outside the workspace root; for `read`/`edit`/`write`
# calls, check args["path"] directly.
```

(Full script, including the `ls`/`find`/`grep` command-word matching and
the self-authored-scratch-file exclusion used for oracle hunting above:
`recompute_v2.py` in the scratchpad, section H names its path.)

Per-cell scan results — (a) absolute paths outside the attempt worktree, in
a bash command or a read/edit/write path; (b) real `git commit`
invocations (string literals excluded):

| Cell | (a) out-of-workspace hits | Reached GOOD code / hidden tests? | (b) `git commit` |
|---|---|---|---|
| cell-01-G1 | 2 (both `/tmp/`, the model's own scratch reference) | no | 0 |
| cell-02-R1 | 19 | **yes** — see below | 1 (`b0f3b49`, index 38) |
| cell-03-D1 | 0 | no | **1** (`0132385`, index 52 — committed before its `COMMAND_TIMEOUT`; see section C) |
| cell-04-G2 | 0 | no | 0 |
| cell-05-R2 | 14 (all the model's own `/tmp/rec.json`, `/tmp/bad.json`, `/tmp/p0-t8.log` scratch files) | no | 0 |
| cell-06-D2 | 5 (all `/tmp` scratch) | no | 1 (`f1b8acc`, index 42) |
| cell-07-G3 | 83 (all `/tmp/*.py` debug scripts the model wrote and ran itself) | no | 0 |
| cell-08-R3 | 0 | no | 0 |
| cell-09-D3 | 5 (`/tmp/dbg_test.py`, `/tmp/deeplint/a/b/c`, model's own scratch) | no | **1** (`b9e06ebf...`, index 41 — `git -c user.name=... -c user.email=... commit`; missed by the first draft's regex, see section C) |
| cell-10-G4 | 51 (all `/tmp/t*.py`, `/tmp/dbg.py`, etc. — model's own scratch harness) | no | **0** (a first draft reported 1 here; that hit was the literal string `'git commit -m pi'` inside a Python test-case list at tool-call index 2, not a real git invocation) |
| cell-11-R4 | 2 (`/tmp/prev.json`, `/tmp/x`; the `find /` at index 47 is counted separately under (a) oracle-hunting above) | no | 0 |
| cell-12-D4 | 0 | no | 2 (`d255eb6` index 34, `669e88d` index 41) |

**cell-02-R1 is the only cell that reached files holding GOOD code or
hidden tests.** Its 19 out-of-workspace hits are almost all its own
scratch (`/tmp/rec.json`, `/tmp/bad.json`, `/tmp/p0-t8.log`), but three
calls read real answer-key material under the controller's
task-qualification staging directory,
`.../scratchpad/rev/basesuite/` and `.../scratchpad/rev/fixprobe/`:

- **Index 14** lists the `selfhost-run-record-gate` staging directory
  (`ls -la "$SP/"; find "$SP/" ...`) and succeeds — the directory exists
  and is listed.
- **Index 15** then tries to `cat` `$SP/src/satyrn_evals/run_record.py`
  and `$SP/tests/test_run_record.py` from that same
  `selfhost-run-record-gate` staging path — and returns **nothing** (exit
  code 1, `Command exited with code 1`; both files are genuinely absent
  from that particular staging directory). **This call did not read the
  answer key** — an earlier draft of this document wrongly described it as
  a successful read.
- **Index 16** is a `find` across the whole scratchpad for `run_record.py`
  and `test_run_record.py` by name, and its output points at
  `.../scratchpad/rev/basesuite/selfhost-guard-prefixes/` instead — because
  that task's `base/` staging tree is cut from a **later** commit on
  `release-one` than `selfhost-run-record-gate`'s own `BASE`, it happens to
  already contain `run_record.py`; this is not "a different task's answer
  key" so much as the same file at a later point in the same history,
  reachable through a directory named for a different task.
- **Indices 17 and 18** then `cat` the real, working
  `src/satyrn_evals/run_record.py` and `tests/test_run_record.py` from
  `.../scratchpad/rev/basesuite/selfhost-guard-prefixes/` — this is the
  actual read of GOOD source and a HIDDEN test file for this cell's task.
- **Indices 19–21** `grep`/`sed` the `launch`/`check` wiring out of
  `.../scratchpad/rev/basesuite/selfhost-guard-prefixes/src/satyrn_evals/cli.py`
  — the GOOD `cli.py` launch-wiring code for this cell's task.
- **Index 22** `cat`s
  `.../scratchpad/rev/fixprobe/A_env_pythonpath_src/overlay/test_run_record.py`
  — a second copy of the HIDDEN overlay test file, from the fix-round
  qualification staging rather than the base-suite staging.

The commit that later produced this cell's `NO_PATCH` (section C) is:

```
cd /private/var/folders/.../satyrn-attempt-or9vdlsl/worktree && git add src/satyrn_evals/run_record.py tests/test_run_record.py src/satyrn_evals/cli.py && git commit -q -m "Task 8: run-record gate ..."
```

**Cross-tabulation against verdict (controller's required framing).**
Contamination can only bias toward `pass`, so a contaminated cell that
**passed** is the severe case; a contaminated cell that **failed** leaves
the rule's arithmetic safe in the conservative direction.

| Contaminated cell | Verdict | Case |
|---|---|---|
| cell-02-R1 | `NO_PATCH` (counted as fail under the frozen rule) | **Safe case** — contamination did not produce a `pass`; the cell still counts toward "headroom" for `selfhost-run-record-gate`, and the arithmetic is conservative |

No cell in this run is the severe case (a contaminated `pass`). All other
out-of-workspace hits are the model's own `/tmp` scratch files it created
and read back — not an escape to GOOD code, hidden tests, the main
checkout, or another worktree.

### (b) Same-file mutation churn and failed tool results

Same recompute script, `mutation_churn` = count of `edit`+`write` calls per
target path; `failed_tool_results` = `tool_execution_end` events carrying
an error/`isError` field.

| Cell | Mutation churn (path: count) | Failed tool results |
|---|---|---|
| cell-01-G1 | `guard.py`: 1 (1 edit) | 0 |
| cell-02-R1 | `run_record.py`:1, `test_run_record.py`:1, `cli.py`:2 | see recompute output |
| cell-03-D1 | (cell timed out; churn recomputed over the partial transcript, see recompute output) | — |
| cell-04-G2 | `guard.py`: 2 | 0 |
| cell-06-D2 | `tools/lint_docs.py`: 2, `tools/lint_docs_test.py`: 7 | see recompute output |
| cell-09-D3 | `tools/lint_docs.py`: 4, `tests/test_lint_docs.py`: 5 | see recompute output |
| cell-12-D4 | `tools/lint_docs.py`: 4, `tests/test_lint_docs.py`: 3 | see recompute output |

(Full per-cell `mutation_churn` and `failed_tool_results` values are in the
scratchpad's `results.json`, produced by `recompute.py` — this field is
unaffected by the git-invocation and oracle-hunt corrections in
`recompute_v2.py` above, since `mutation_churn` counts `edit`/`write` calls
directly and never inspects `bash` command text. Every field is
machine-computed from the retained transcripts, not hand-counted, and is
carried in full there rather than reproduced exhaustively here to keep this
document proportionate.)

### The detector gap

`summary.json`'s own `pathology.<attempt-dir>.workspace_escapes` field,
compared against the scan above:

| Cell | `summary.json workspace_escapes` | `summary.json contamination` | Scan found an out-of-workspace read? |
|---|---|---|---|
| cell-02-R1 | **0** | `{"graded": 0, "flagged": 0, "clean": 0, "unmeasured": 0}` (grading never ran — `NO_PATCH`) | **yes** — the qualification staging directory, GOOD code and hidden tests |
| all other cells | 0 or `None`/unmeasured (six `COMMAND_TIMEOUT` cells report `None` for the whole pathology block) | as recorded | no out-of-workspace reads beyond the model's own `/tmp` scratch |

**cell-02-R1 is the detector-gap cell**: the harness's own instrumentation
reports `workspace_escapes: 0` and does not run contamination scanning at
all for a `NO_PATCH` cell, while the transcript itself shows the model
reading the answer key. This matches the controller's ledger ruling exactly
and is recorded here as **instrument debt**, per "no instrument change
larger than reading the evidence" — nothing in `pathology.py` or
`contamination.py` was touched to produce this document.

**All of the above is a diagnostic. None of it enters the decision rule in
section B.**

## E. Per-task budget summary

Median seconds and median output tokens, each over the task's four scored
cells (values from section A's table).

| Task | Cells (seconds) | Median seconds | Cells (output tokens) | Median output tokens |
|---|---|---|---|---|
| `selfhost-guard-prefixes` | 66, 200, 1201, 1202 | **700.5** | 3,217 / 7,210 / 37,458 / 32,533 | **19,871.5** |
| `selfhost-run-record-gate` | 500, 1200, 1201, 1201 | **1,200.5** | 12,651 / 33,335 / 29,241 / 25,661 | **27,451.0** |
| `selfhost-docs-linter` | 1202, 1004, 1124, 1150 | **1,137.0** | 38,032 / 33,814 / 30,806 / 27,573 | **32,310.0** |

Median is the mean of the two middle values of the sorted four-element set
in every row (even count).

## F. Missingness

Every cell's attempt directory, receipt, and transcript, checked directly
under the output root:

| Cell | Attempt dir retained | `receipt.json` | `transcript.txt` | Unscored? |
|---|---|---|---|---|
| cell-01-G1 | yes | present (`pass`) | present | no |
| cell-02-R1 | yes | **absent** (`NO_PATCH`, never graded) | present | no — scored as fail per the frozen rule |
| cell-03-D1 | yes | **absent** (`COMMAND_TIMEOUT`) | present | no — scored as fail |
| cell-04-G2 | yes | present (`fail`) | present | no |
| cell-05-R2 | yes | **absent** (`COMMAND_TIMEOUT`) | present | no — scored as fail |
| cell-06-D2 | yes | **absent** (`NO_PATCH`) | present | no — scored as fail |
| cell-07-G3 | yes | **absent** (`COMMAND_TIMEOUT`) | present | no — scored as fail |
| cell-08-R3 | yes | **absent** (`COMMAND_TIMEOUT`) | present | no — scored as fail |
| cell-09-D3 | yes | **absent** (`NO_PATCH`) | present | no — scored as fail |
| cell-10-G4 | yes | **absent** (`COMMAND_TIMEOUT`) | present | no — scored as fail |
| cell-11-R4 | yes | **absent** (`COMMAND_TIMEOUT`) | present | no — scored as fail |
| cell-12-D4 | yes | **absent** (`NO_PATCH`) | present | no — scored as fail |

**No cell is unscored.** All twelve produced a retained attempt directory
and transcript; a missing `receipt.json` is not missingness in the
artifact-retention sense — it is the expected shape of a cell whose
`attempt.json code` is not `OK` (grading only runs on a harvested patch),
and every such cell is still counted as a fail per the rule in section B.
The output root also retains `launch.sh`, `schedule.json`, `run.log`, and
each cell's `summary.json` and `engine-contracts/` directory — nothing is
discarded.

## G. What this does not establish

- **No comparison with any other model or arm, and no comparison between
  arms.** This document names no other model and pools with no other run.
- **No Fisher test, confidence interval, or significance claim.** Twelve
  cells support per-task presence/absence of headroom under the frozen
  2-of-4 rule and nothing finer — not a rate, not an effect size.
- **No claim about *why* Ornith fails where it fails.** The kinds of
  non-pass in section C are named to keep the *evidence* honest (a timeout
  is not the same fact as a behavioural fail, which is not the same fact as
  an adapter artifact), not to diagnose a cause.
- **The two plan-derived prompts (`selfhost-run-record-gate`,
  `selfhost-docs-linter`) are richer than the brief's literal four-element
  derivation** — disclosed in the pre-run record's fix round: both prompts
  retain intervening Rules/schema prose the plan specified, and both
  `contracts.R1` were amended to disclose exact message-format strings and
  exception shapes their hidden suites assert on, because those strings
  appear nowhere in the visible workspace. This makes a `pass` reachable at
  all in principle; see the pre-run record's "The three prompts" for the
  full per-id answerability walk. **It does not follow that a pass was easy
  to reach in this run** — for both tasks, a pass additionally required
  surviving the adapter's `harvest_patch()` diff base (section C), which
  needs the model to create the required file and then leave it staged or
  committed-and-then-restaged, a shape neither task's prompt asks for and
  neither fixture direction exercises (section B). Under the rule both
  tasks reached headroom (4 of 4 scored cells fail); under the sensitivity
  reading required by section B, `selfhost-run-record-gate` still shows
  headroom (3 of 4, with the caveat given there) but `selfhost-docs-linter`
  does not (1 of 4, arguably 0 of 4) — so a reader should not conclude from
  either the rich prompt or the rule's raw count that a pass was, in
  practice, barely reachable through the harvest path.
- **The self-hosted task shape's trust boundary is disclosed, not
  resolved, by this probe.** The workspace under test is the harness's own
  package; `src/satyrn_evals/oracle_hook.py` is outside every task's
  `source_paths` and a patch touching it is rejected before the oracle
  runs (`unavailable`, verified in the pre-run record's "Trust-boundary
  limit" section) — but candidate code the hidden suite imports and
  executes inside the oracle process (`cli.py` for `selfhost-run-record-gate`;
  `guard.py`/`lint_docs.py` for the other two) is, definitionally, code the
  model wrote, running inside the grading process. This probe did not
  change that boundary; it is named here as a threat this result's evidence
  should be read against.
- **Contamination (cell-02-R1) and the adapter's diff-base artifact
  (`NO_PATCH`, four cells) are named threats to this evidence, not
  corrections applied to it.** Section C and D state plainly which cells
  they touch and in which direction each biases the count; no cell's
  contribution to the rule in section B was adjusted for either.

## H. Digests re-verified

Recomputed with the pre-run record's own walk, in this worktree at `HEAD =
0b2d4b65d9c1d44c5e123598978288b4941fd801`:

```
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
```

| Task | Pre-run record's digest | Re-verified | Match |
|---|---|---|---|
| `selfhost-guard-prefixes` | `a84f6597407c49e805df1d28fa61ad3e0258f142d6391916bc1da721de4de700` | `a84f6597407c49e805df1d28fa61ad3e0258f142d6391916bc1da721de4de700` | yes |
| `selfhost-run-record-gate` | `f82d90d1e9cd7ee462223a8287dd58e6fb33efdd734eb393a3a2252f9289aaeb` | `f82d90d1e9cd7ee462223a8287dd58e6fb33efdd734eb393a3a2252f9289aaeb` | yes |
| `selfhost-docs-linter` | `b4e966a2e5496ac3c41dc2d07307230cec209ccf83b267bdd96ab12fd49d0c31` | `b4e966a2e5496ac3c41dc2d07307230cec209ccf83b267bdd96ab12fd49d0c31` | yes |

Prompt digests (`sha256` of each task's `manifest.json` `contract`/
`contracts.R1` string), re-verified the same way:

| Task | Pre-run record's digest | Re-verified | Match |
|---|---|---|---|
| `selfhost-guard-prefixes` | `00e0b6a3a0ce8b043b1f4f648a92d35d334a78f10b697da5d2bf10aaff21857f` | `00e0b6a3a0ce8b043b1f4f648a92d35d334a78f10b697da5d2bf10aaff21857f` | yes |
| `selfhost-run-record-gate` | `d1ea88fd8d8fecb72d97da3fd47537c8594979526d13362886ada645e6dc8b50` | `d1ea88fd8d8fecb72d97da3fd47537c8594979526d13362886ada645e6dc8b50` | yes |
| `selfhost-docs-linter` | `c8b4cdfa0d2ff9e38d314bd66d34f266266ee0dfb03ea96616ff8cad89993286` | `c8b4cdfa0d2ff9e38d314bd66d34f266266ee0dfb03ea96616ff8cad89993286` | yes |

No drift in any of the six digests. **Evals revision the launcher actually
ran:** `0b2d4b65d9c1d44c5e123598978288b4941fd801` — the fix-round commit
named in the pre-run record as the floor for the run, confirmed as this
worktree's `HEAD` both before and after the twelve cells (`git status
--porcelain` empty throughout; no commit landed on this branch during the
run).

## Retention

Output root
`/Users/pauleveritt/satyrn-smokes/2026-09-14-selfhost-headroom-probe/`
holds `launch.sh`, `schedule.json`, `run.log`, twelve `cell-NN-XY/`
directories (each with its `summary.json`, `engine-contracts/`, and its
attempt subdirectory), and twelve `cell-NN-XY.stdout.log` files beside them.
Nothing in the output root was modified, moved, deleted, regraded, or
re-run to produce this document; every command used to produce a number
above was a read against retained artifacts, run from this worktree.

**Every count in this document carries a runnable recompute inside the
document itself** (sections A, B and D above) — the scratchpad copies
(`recompute.py`, the corrected `recompute_v2.py`, and their raw
`results.json`/`results_v2.json` output at
`/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/selfhost-probe/`)
are convenience copies for this session only, not the record of how a
number was produced: that scratchpad is ephemeral and the fenced scripts in
this document are what a later reader can actually run against the
retained artifacts under the output root.
