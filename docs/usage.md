# Usage

V2 ships two commands: `grade` and `capture`. See the
[glossary](glossary.md) for the vocabulary.

## grade

Apply a {term}`patch` to a bundled {term}`task`'s base state, run the
task's {term}`oracle`, and record the {term}`verdict` in a
{term}`receipt` — offline and deterministically, with no model and no
network.

```console
satyrn-evals grade TASK PATCH [--receipt PATH] [--tasks-root DIR]
```

- `TASK` — a {term}`task` name. `format_number` is the first bundled task:
  a small pure-Python function task with known-good and known-broken
  fixture patches.
- `PATCH` — path to a unified-diff {term}`patch` file.
- `--receipt PATH` — where the {term}`receipt` is written; default `receipt.json`
  in the current directory.
- `--tasks-root DIR` — where to find tasks; default: the bundled tasks that
  ship in the wheel. Point it at a captured-task directory to grade a
  {term}`capture record`'s output.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Grading completed; the {term}`receipt` says `pass` or `fail` |
| 2 | Usage error — unknown task, unreadable {term}`patch`, bad arguments |
| 3 | Operational failure — the {term}`receipt` says `unavailable` and names the cause |

The {term}`verdict` never comes from stdout or the exit code. Read the
{term}`receipt`.

### The receipt

```json
{
  "task": "format_number",
  "patch_digest": "251a3d81e289f932d69bb1d93116fda757f47b9dcbdb11e9bc68aab7dd687ebc",
  "verdict": "pass",
  "reason": "",
  "evidence": {
    "executed_test_ids": ["test_solution.py::test_large", "test_solution.py::test_negative"],
    "outcomes": {"test_solution.py::test_large": "passed", "test_solution.py::test_negative": "passed"},
    "counts": {"passed": 2, "failed": 0, "error": 0, "skipped": 0}
  }
}
```

`patch_digest` is the sha256 of the {term}`patch` file, so a {term}`receipt`
names the exact input it graded — re-scoreable without re-running anything.
`evidence` is the {term}`hook result` verbatim.

### Example

```console
$ satyrn-evals grade format_number known-good.patch --receipt r.json
$ echo $?
0
$ python -c "import json; print(json.load(open('r.json'))['verdict'])"
pass
```

A {term}`patch` that does not apply, or an {term}`oracle` that produces no
trustworthy {term}`hook result`, records `unavailable` and exits 3 — never
a clean zero that proved nothing.

## capture

Turn a real fixing commit in a repository into a {term}`task` — manifest,
base state, and a known-good {term}`patch` — winnable by construction, in
minutes. The task's base is the fix's parent tree; the known-good patch is
the fix diff restricted to non-test source paths; the {term}`oracle`
runs only the tests that fail at base and pass with the fix (the
{term}`discriminating set`).

```console
satyrn-evals capture --revert SHA [--repo PATH] [--name NAME] [--contract TEXT] [--output DIR]
```

- `--revert SHA` — the fixing commit. Required.
- `--repo PATH` — the source repository; default: the current directory. Its
  working tree, index, branch, and `HEAD` are never touched.
- `--name NAME` — the task directory name; default: a slug of the fix
  commit's subject line.
- `--contract TEXT` — the task statement; default: the fix subject line.
- `--output DIR` — where the task directory is written; default `./tasks/`.

Four deterministic checks run during capture (source preflight, base
oracle runs, un-done at base, winnable); a failed check refuses with a
precise `code` in the {term}`capture record`. Exit codes: `0` captured,
`2` usage error, `3` refusal.

### The capture record

```json
{
  "version": 1,
  "outcome": "captured",
  "code": "OK",
  "message": "task captured",
  "repo": "/src/app",
  "base_sha": "…",
  "fix_sha": "…",
  "task_dir": "tasks/fix-off-by-one",
  "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook", "test_solution.py::test_one"],
  "expected_test_ids": ["test_solution.py::test_one"],
  "check_outcomes": {
    "source_preflight": "passed",
    "base_oracle": "passed",
    "un_done_at_base": "passed",
    "winnable": "passed"
  }
}
```

The record is the authoritative result; the exit code is coarse by design.
A refusal writes the same shape with `outcome: refused` and a precise
`code` (e.g. `REPO_DIRTY`, `NO_DISCRIMINATING_TESTS`, `CLEANUP_FAILED`).

Grade a captured task with `--tasks-root`:

```console
$ satyrn-evals capture --revert <sha> --repo /src/app --output tasks
$ satyrn-evals grade --tasks-root tasks fix-off-by-one tasks/fix-off-by-one/fixtures/known-good.patch
```
