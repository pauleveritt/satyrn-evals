# R0 §1.2 prompt-only solve — the solver's own final report

Task `selfhost-preflight-quiet`, run 2 (2026-09-18). Solver: a fresh Sonnet subagent given
`PROMPT.txt`'s text and a copy of `base/` as its only readable and writable area, with the
off-limits list named individually (the evals checkout, the task directory's `overlay/`,
`fixtures/`, `manifest.json` and `qualification.json`, `~/satyrn-runs/`, `/Users/Shared/`,
`docs/superpowers/plans/` including `2026-09-18-preflight-quiet.md`, and the authored-task design
spec). Reproduced verbatim below; the controller harvested the diff, the solver never wrote one.

---

Everything is in place. Full test suite (2482 tests), ruff, and lint-docs are all green.

## Summary

**Files created** (all inside the working tree):

1. `scripts/preflight_quiet.py` — the module. Three frozen/slotted dataclasses (`Process`, `Rate`,
   `Certificate`), the five module constants (`DEFAULT_CEILING`, `DEFAULT_CPU_FLOOR`,
   `DEFAULT_FLOOR_TOK_S`, `DEFAULT_LAST`, `IGNORE_PREFIXES`), the pure functions `load_problem`,
   `busy_processes`, `decode_rate`, `certificate`, and `main` with its two real-machine readers.
2. `tests/test_preflight_quiet.py` — the 20-test acceptance suite, written before the module
   existed (verified it failed first with `ModuleNotFoundError: No module named 'preflight_quiet'`).
3. `PROVENANCE.md` — created (didn't exist yet) with one row each for the two files above, via
   `uv run python tools/provenance.py new scripts/preflight_quiet.py tests/test_preflight_quiet.py`.

**Verification**: ran the acceptance suite alone (20/20 pass), then the full default tier
(`uv run pytest -q`: 2482 passed, 336 deselected), `uv run ruff check` (clean), and
`uv run python tools/lint_docs.py` (clean). No test was edited to fit the implementation.

**No commit made.** The outer task's rules explicitly forbid `git add`/`git commit` even though the
brief's Step 9 asks for one — I followed the overriding instruction and left the three files
(PROVENANCE.md, scripts/preflight_quiet.py, tests/test_preflight_quiet.py) as untracked additions
for someone else to harvest as a diff.

**Judgment calls where the brief left room:**

- **Regex for log lines**: built `_LOG_RE` to require the literal timestamp shape,
  ` - omlx.server - INFO - `, then any bracketed tag (`.*`), then
  ` - Chat completion: model=..., N tokens in Xs (R tok/s), prompt: P,`. This satisfies "carries
  both the timestamped prefix and the whole completion shape" while tolerating whatever sits in
  place of `[-]`.
- **`main`'s default `read_ps`**: a `subprocess.run(["ps", "-axo", "pid,pcpu,comm"], ...)` call,
  since the brief names this as one of the two real readers but doesn't specify implementation
  details.
- **`main`'s default `read_log`**: since the brief doesn't name a specific log path/convention, I
  read from an `OMLX_SERVER_LOG` environment variable when set, returning `[]` otherwise (never
  exercised by the acceptance suite, which always injects `read_log`).
- **`main`'s default `cores`**: `os.cpu_count() or 1`, since "the core count" wasn't tied to a
  specific stdlib call in the brief.
- **20-test breakdown**: mapped the brief's counts literally — 6 for parser good/bad, 6 for the
  three thresholds each at-edge/across-edge (ceiling on `load_problem`, cpu_floor on
  `busy_processes`, floor_tok_s on `certificate` since that's the function that actually takes
  `floor_tok_s`), 2 for the ignore list, 1 for token-weighting, 1 for fewer-than-N, 2 for
  certificate JSON shape/ordering, 2 for CLI exit codes.
- **`Certificate.record`** given a `field(default_factory=dict)` default so the dataclass is still
  usable with just `problems=` in ad hoc tests, though `certificate()` always supplies both.
