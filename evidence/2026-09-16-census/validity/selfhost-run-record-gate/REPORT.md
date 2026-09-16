# Task 8 report: the run-record gate

## What changed

- **`src/satyrn_evals/run_record.py` (new).** Defines `RunRecordError(UsageError)`,
  the frozen/slotted `RunRecord` dataclass (fields in the required schema order),
  `load_run_record`, and `gate`.
- **`src/satyrn_evals/cli.py` (modified).** Adds the `launch` subparser with its
  single `--check RECORD` flag, a small `previous_result_committed` helper that
  shells out to `git ls-files --error-unmatch`, and the dispatch branch.
- **`tests/test_run_record.py` (new).** 77 tests covering the accepted path and
  every refusal, plus the CLI check. No test spawns a subprocess (all records use
  a null `previous_result`), so the default-tier tripwire stays closed.

## Implementation notes

`load_run_record` reads and parses the file first, wrapping OS and JSON-syntax
failures in `RunRecordError` messages that include the path. A parsed value that
is not a dict is refused with the phrase `not a JSON object`.

Field validation walks the schema in declaration order, so the first missing or
ill-typed field is the one named. Integer columns are checked with `type(x) is
int`, which deliberately rejects JSON booleans and floats as well as strings.
After presence/type, value rules run: `condition` in `{cold, warm}`,
`task_tree_sha256` matching `[0-9a-f]{64}` via `fullmatch`, `mode` in
`{attended, batch}`, and non-whitespace `stop_rule`/`decision_rule`.
`previous_result` is validated as null-or-string.

`gate` is pure: it enforces the per-mode cadence caps (attended 8 cells / 60
minutes, batch 12 cells / 720 minutes) and refuses a named `previous_result`
unless `previous_result_committed is True`. Cap messages name the mode; the
provenance message names `previous_result`.

The CLI computes committedness only when `previous_result` is non-null and
passes it to `gate`; a `RunRecordError` is a `UsageError`, so the existing
`except SatyrnError` path prints it and returns exit 2. Without `--check`,
`launch` prints `launch: cells are Phase 2; use --check` and returns 2.

## Verification

- `uv run pytest tests/test_run_record.py -q` -> 77 passed.
- `uv run pytest -q` -> 1566 passed, 270 deselected.
- `uv run ruff check` -> all checks passed.
- `uv run pyrefly check` adds no errors for the two changed source files.
- `uv run satyrn-evals launch --check <good>.json` -> `launch: record accepted`,
  exit 0; an over-budget record prints the attended-cap refusal, exit 2;
  `uv run satyrn-evals launch` prints the Phase 2 note, exit 2.
