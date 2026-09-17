# Report: docs linter to the release-one caps

## Files changed

- `tools/lint_docs.py` (new) — the linter.
- `tests/test_doc_caps.py` (new) — 12 unit tests over synthetic trees.

`Justfile` already carried the `lint-docs` target, so it needed no edit.

## What `tools/lint_docs.py` does

`check(root: Path) -> list[str]` walks the tree and returns one plain string
per violation; `main()` lints `Path.cwd()`, prints each line, and exits 1 when
the list is non-empty. It imports only `sys` and `pathlib` — no project module,
no model, network, or subprocess.

Rules implemented, with the required message shapes:

- `ROADMAP.md` over 150 lines: `<path>: <n> lines > 150`.
- Each `docs/results/*.md` over 120 lines: `<path>: <n> lines > 120`.
- Each spec under `docs/superpowers/specs/` over 400 lines: `<path>: <n> lines > 400`.
  Plans are deliberately left uncapped.
- A result page with no line beginning with three backticks:
  `<path>: no fenced recompute block`. A four-space-indented command does not
  count; only a real backtick fence does.
- More than 12 files in `docs/results/` (`.gitkeep` excluded):
  `docs/results: <count> result files > 12`.
- A directory under `docs/` outside the permitted set (`superpowers`,
  `superpowers/specs`, `superpowers/plans`, `results`, `reviews`):
  `docs/<name>: directory not permitted under docs/`, with `<name>` relative to
  `docs/`.
- Trailing whitespace in any `*.md`: `<path>:<line>: trailing whitespace`
  (1-indexed).
- A blank final line: `<path>: blank line at EOF`.

All paths are `root`-relative and always use `/` as the separator. For one
file, every trailing-whitespace line is emitted in ascending line order before
that file's own blank-EOF line. A clean tree returns `[]`.

### Skip list and the nesting trap

The whitespace / blank-EOF sweep covers every `*.md` found by `root.rglob`,
skipping a fixed set of build/cache/vendor directory names
(`__pycache__`, `.venv`, `venv`, `node_modules`, `_build`, `build`, `dist`,
`.git`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.tox`). Membership is
tested against the parts of each file's path *relative to `root`*, so a
checkout sitting under a directory whose name happens to match a skip entry
(for example `.../build/repo`) lints exactly as if it were at the top level.
A test pins this by putting the synthetic root under `tmp_path/build/repo` and
asserting that a violation in `docs/` is still reported while a violation
inside `node_modules/` is ignored.

## Verification

- `uv run pytest tests/test_doc_caps.py -q` → 12 passed.
- `uv run pytest tests/ -q` → 1486 passed, 270 deselected (was 1474 before;
  the twelve-test increase is the new file).
- `uv run ruff check` → All checks passed.
- `uv run python tools/lint_docs.py; echo "EXIT: $?"` → `EXIT: 0` on the real
  tree. `just lint-docs` likewise exits 0.
- No spec in the tree exceeds 400 lines, so no cap was raised.

## Note on provenance

The fixture tree carries no `PROVENANCE.md`, and `tools/provenance.py check`
reports every tracked file as unrecorded on the untouched baseline, so a
provenance row could not be added meaningfully. The two new files are left
untracked in the working tree; nothing was committed.
