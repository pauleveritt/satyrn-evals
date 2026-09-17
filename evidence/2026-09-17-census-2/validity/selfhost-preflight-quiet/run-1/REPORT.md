# The prompt-only solver's final report — `selfhost-preflight-quiet`

Verbatim, as returned by the solver on 2026-09-17. The solver saw `PROMPT.txt` and a copy of `base/` and
nothing else; the off-limits list of the validity procedure was given to it path by path, and it was told
not to run `git add`, `git commit`, or produce a diff — the controller harvested.

---

Left uncommitted, as instructed. Final report below.

## Report

**Created:**
- `scripts/preflight_quiet.py` — the module per spec: `Process`, `Rate`, `Certificate` (frozen/slotted), `load_problem`, `busy_processes`, `decode_rate`, `certificate`, `main`, and constants `DEFAULT_CEILING`/`DEFAULT_CPU_FLOOR`/`DEFAULT_FLOOR_TOK_S`/`DEFAULT_LAST`/`IGNORE_PREFIXES`.
- `tests/test_preflight_quiet.py` — 27-test acceptance suite (spec said "twenty"; I covered every named case plus a couple extra — problem ordering, JSON round-trip, five/fifteen-minute figures ignored).
- `PROVENANCE.md` — created (didn't previously exist in this tree) with rows for the two new files, via `uv run python tools/provenance.py new`.

**Verification run:** `uv run pytest tests/test_preflight_quiet.py -q` failed with `ModuleNotFoundError: No module named 'preflight_quiet'` before the module existed (per step 2), then 27 passed after. Full suite: `uv run pytest -q` -> 2489 passed. `uv run ruff check` -> all checks passed. `uv run python tools/lint_docs.py` -> within cap. Left uncommitted per my own task instructions (did not run `git add`/`commit`).

**Decisions where the prompt left room:**
1. **`read_log`'s default path.** The prompt never states where the server log lives. I found `~/.omlx/logs/server.log` confirmed in `scripts/speed_probe.py`'s docstring (dated 2026-09-14) and used that as `DEFAULT_SERVER_LOG`, returning `[]` if the file doesn't exist. This is the most load-bearing guess in the whole task, since it's untestable from the spec text alone.
2. **`cores` as a callable.** The interface line lists `cores` as a bare parameter, but step 7's prose calls all four inputs "keyword-only callables" with defaults "`os.getloadavg`, the core count, a ps subprocess, a log reader" — so I made `cores` default to a zero-arg callable (`os.cpu_count() or 1`) rather than a plain int, to keep all four uniformly callable as the prose implies.
3. **`_read_ps` subprocess shape.** Not specified beyond "a `ps -axo pid,pcpu,comm` subprocess" — used `subprocess.run(..., capture_output=True, text=True, check=True).stdout`.
4. **Existing repo-wide provenance gap.** `tools/provenance.py check` already fails for ~19 pre-existing files unrelated to this task (arms/, docs/, root config files) — that's a pre-existing condition in this scratch tree, not something the prompt asked me to fix, so I only recorded the two files this task added.

**Ambiguity noted, not acted on:** the regex for a completion line requires the literal `omlx.server - INFO` substring per spec wording ("timestamped `omlx.server - INFO` prefix"); I didn't anchor the timestamp format itself beyond `\S+ \S+`, since the spec gives one example format and doesn't state a stricter pattern.
