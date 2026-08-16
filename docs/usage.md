# Usage

V1 ships one command: `grade`. See the [glossary](glossary.md) for the vocabulary.

## grade

Apply a {term}`patch` to a bundled {term}`task`'s base state, run the
task's {term}`oracle`, and record the {term}`verdict` in a
{term}`receipt` — offline and deterministically, with no model and no
network.

```console
satyrn-evals grade TASK PATCH [--receipt PATH]
```

- `TASK` — a bundled {term}`task` name. `format_number` is the first bundled task:
  a small pure-Python function task with known-good and known-broken
  fixture patches.
- `PATCH` — path to a unified-diff {term}`patch` file.
- `--receipt PATH` — where the {term}`receipt` is written; default `receipt.json`
  in the current directory.

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
