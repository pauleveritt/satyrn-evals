# Release two R0 — the task-validity check (procedure)

R0 §1.2 asks that a candidate qualify only if its prompt determines the
structural choices its hidden suite asserts — where a class lives, which
function refuses what, which files may change — and design section 4 records
that check per task as `validity: {by, commit, passed}` in the manifest. The
recipe below is what the controller runs once per census task: a cloud model
receives the cut prompt and a copy of `base/` and nothing else, writes a
solution, and the hidden suite is run against it offline. A task whose
prompt-only solution fails the hidden suite is a generator defect, not a
ceiling, and does not get a census record until it is fixed and re-checked.

## What the solver sees, and what it must not

For task `T` (Ruling 6), the controller builds exactly two things under a
scratchpad root:

- `<scratchpad>/validity/<T>/tree` — a copy of `<task>/base/`, then `git init`
  and one commit, so the tree is a clean starting point the harvest can diff.
- `<scratchpad>/validity/<T>/PROMPT.txt` — the manifest's `contracts[rung]`
  text for the rung `qualify.CENSUS_TASKS[T]` names, and nothing else.

The tree and `PROMPT.txt` are the solver's only readable and writable area.
Every other path is off limits, named individually so the instruction is
checkable:

- the `satyrn-evals` checkout, and inside the task directory
  `src/satyrn_evals/tasks/<T>/overlay/` (the hidden suite),
  `.../fixtures/` (the known-good and known-broken patches),
  `.../manifest.json` (the expected test ids) and `.../qualification.json`;
- `~/satyrn-runs/`, the retained cells;
- `/Users/Shared/`;
- `docs/superpowers/plans/`, which holds the plan the prompt was cut from.

Copying the task directory instead of `base/` would hand the solver the
answer; copying only `base/` is the same artefact a census cell receives.

## The dispatch

One `deepseek-v4-flash` subagent per task, run blocking. The project's
intended role for this check is Sonnet, but the harness could not select it,
so `by` records the model that actually ran. The maintainer ratified this substitution on 2026-09-16 as the instrument for R0 §1.2 (design amendment, section 4). It is given `PROMPT.txt`'s text
and the tree path, and nothing else: no plan, no hidden test ids, no
known-good patch, no qualification output. It writes a solution in the tree.
It does not run the hidden suite — it has no access to one — and it may run
whatever public suite the base carries. Its final report says what it changed
and why. No haiku, no GPU, and no network beyond the model itself.

## Harvest

The controller harvests, not the agent. In the tree:

```bash
git add -A
git diff --cached > <scratchpad>/validity/<T>/solution.diff
```

`solution.diff` is the artefact graded and leak-checked. The agent never
writes the diff.

## The two leak tells

Run both tells over `solution.diff` and the agent's final report:

1. Any id from the manifest's `expected_test_ids` appearing there.
2. Any of `overlay`, `known-good.patch`, `known-broken.patch`,
   `manifest.json`, or the task directory's path appearing there.

Matching the known-good patch is **not** a tell: a correct solution is
supposed to look like the fix. A tell voids the run; redo it with a fresh
agent and record the void.

## Grading

Grade from a directory that has no `pyproject.toml`, `pytest.ini`,
`.pytest.ini`, `tox.ini`, `setup.cfg` or `conftest.py` in it or above it —
otherwise pytest discovers configuration that is not the task's. From
`$HOME/satyrn-census-grades/validity/<T>/`:

```bash
UV_OFFLINE=1 uv run --project <evals-checkout> satyrn-evals grade \
  <T> <scratchpad>/validity/<T>/solution.diff --receipt receipt.json
```

The verdict is read from `receipt.json`'s `verdict` field, never from the exit
status.

## What is recorded

Write `validity` into the task's `manifest.json`:

- `by` — the model that wrote the solution (for example `deepseek-v4-flash`).
- `commit` — `git rev-parse HEAD` of the evals tree the prompt was read from.
- `passed` — `receipt.verdict == "pass"`.

A failed check is recorded with `passed: false`; the task does not get a
census record until it is fixed and re-checked. The block is a post-cut
annotation, so `tools/cut_task.py check` ignores it and a re-cut still matches
the committed tree.

For all five tasks the recorded `validity.commit` is `df33336`, and the
`selfhost-cell-loop` prompt edit landed in `fc870ba`; a re-derivation must
apply that edit to reproduce the checked cell-loop prompt.

## Recompute

The whole sequence for one task, `selfhost-docs-linter`:

```bash
T=selfhost-docs-linter
EVALS=$(pwd)
SCRATCH=${SCRATCH:-/tmp/satyrn-validity}
GRADE_ROOT="$HOME/satyrn-census-grades/validity/$T"
mkdir -p "$SCRATCH/validity/$T" "$GRADE_ROOT"

# 1. The solver's world: a copy of base/, one commit, and the cut prompt.
cp -R "src/satyrn_evals/tasks/$T/base" "$SCRATCH/validity/$T/tree"
git -C "$SCRATCH/validity/$T/tree" init -q
git -C "$SCRATCH/validity/$T/tree" add -A
git -C "$SCRATCH/validity/$T/tree" \
  -c user.name=validity -c user.email=validity@example.invalid commit -qm base
uv run python - "$T" "$SCRATCH/validity/$T/PROMPT.txt" <<'PY'
import json, sys
from pathlib import Path
from satyrn_evals.qualify import CENSUS_TASKS
task, out = sys.argv[1], Path(sys.argv[2])
body = json.loads((Path("src/satyrn_evals/tasks") / task / "manifest.json").read_text())
out.write_text(body["contracts"][CENSUS_TASKS[task]])
PY

# 2. Dispatch one deepseek-v4-flash subagent with PROMPT.txt and the tree path;
#    wait for its report. It writes a solution in the tree.

# 3. Harvest, controller-side.
git -C "$SCRATCH/validity/$T/tree" add -A
git -C "$SCRATCH/validity/$T/tree" diff --cached > "$SCRATCH/validity/$T/solution.diff"

# 4. The two leak tells, over solution.diff and the agent's report. A tell
#    voids the run: fresh agent, recorded void.

# 5. Grade offline, from a clean directory. No pyproject.toml, pytest.ini,
#    .pytest.ini, tox.ini, setup.cfg or conftest.py in it or above it.
cd "$GRADE_ROOT"
UV_OFFLINE=1 uv run --project "$EVALS" satyrn-evals grade "$T" \
  "$SCRATCH/validity/$T/solution.diff" --receipt receipt.json

# 6. Read the verdict from the receipt (never the exit status) and write the
#    block into src/satyrn_evals/tasks/$T/manifest.json.
cd "$EVALS"
uv run python - "$T" "$GRADE_ROOT/receipt.json" <<'PY'
import json, subprocess, sys
from pathlib import Path
task, receipt = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
path = Path("src/satyrn_evals/tasks") / task / "manifest.json"
body = json.loads(path.read_text())
body["validity"] = {"by": "deepseek-v4-flash", "commit": commit, "passed": receipt["verdict"] == "pass"}
path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(task, body["validity"])
PY
```

## Carried forward

1. **The Engine's `DELIVER_TIMEOUT_SECONDS` is 1800 and the record's backstop
   is not wired to it** (Ruling 3). An Engine cell under a 3,000 s backstop is
   stopped at 1,800 s inside `deliver` while a Baseline cell runs to 3,000 s.
   Fix before the first Engine record of release two; it is an arm-parity
   defect, not a census defect.
2. **Section 3.1's Pi-loop semantics are declared, not measured** (Ruling 9).
   The first census cell that shows a length-cut turn with tool calls ending a
   session contradicts them and is a finding.
3. **The census's `tripped_verdict` is a secondary with no denominator rule
   yet.** Section 8 decides whether it enters the claim; until then it is
   reported beside `verdict`, never instead of it.
