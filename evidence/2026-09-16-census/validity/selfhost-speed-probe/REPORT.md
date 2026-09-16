# Task 6 — probe tooling, roadmap row, and tests

## What changed

**`scripts/speed_probe.py` (new).** A two-halves instrument for the Phase 2b
GPU sitting. `run` drives oMLX and returns a plan of POSIX-second windows: one
request per context size, then `k` parallel worker threads per concurrency
level, each looping until the stream deadline passes. `analyze` reads that plan
and the server log and reports decode rate per prompt, total throughput per
`k`, the missing sizes, and the chosen `k`. The parsing/arithmetic half needs no
network, model, or subprocess.

Concrete choices, all pinned to the task's contract:

- `CONTEXT_SIZES`, `CONCURRENCY`, `K_THRESHOLD`, `SIZE_TOLERANCE` are the stated
  values.
- `Completion` is a frozen dataclass in the stated field order, with `started`
  as `ended - seconds`.
- `parse_line` uses one anchored regex that demands a leading
  `%Y-%m-%d %H:%M:%S,%f` stamp, an `omlx.server - INFO` logger, and the full
  `Chat completion: model=…, N tokens in Xs (R tok/s), prompt: P,` shape; blank
  lines, other loggers, and bare fragments return `None`.
- `nearest_size` picks the nearest size first and only then applies the 25 %
  tolerance, so the exact tie at 60000 resolves to the smaller size and fails
  the tolerance (as specified), while 21000 and 121600 resolve to 20000 and
  160000.
- `decode_by_size` medians per size with keys ascending; `total_throughput`
  divides summed tokens by latest-ended minus earliest-started and raises on an
  empty list; `choose_k` scans `CONCURRENCY` ascending, always keeping 1 as the
  baseline, and raises when 1 is absent.
- `analyze` unions the context phases' completions for decode, strings the
  keys, rounds values to one decimal, and lists missing sizes as ints.
- `request` POSTs to `<base_url>/chat/completions` with a body whose keys are
  exactly `model`, `messages`, `max_tokens`, `stream`; `run` sends it through
  the injected opener as a context manager and reads the response.
- `main` exposes `run` and `analyze`; `analyze` prints the report as JSON and
  returns 0, or 2 with a stderr message on `OSError`/`ValueError`/`KeyError`.

**`tests/test_speed_probe.py` (new).** 27 default-tier tests, no model, network,
or subprocess. Each refusal has a sibling success: the parser accepts the real
line and rejects a blank line, another logger, and a stamp-less fragment; the
tolerance rejects 60000 and accepts the two stated roundings; `choose_k` keeps 1
when nothing scales and raises without a baseline; `analyze` is checked with
missing sizes and with a scaling `k`; `run` is driven by a recording fake opener
and checked for one request per size, `k` requests per stream, `end > start`,
and the exact four body keys.

**`ROADMAP.md`.** Row 2b drops "warm prefix recorded" from its Phase cell and
"and recording" from its Mode cell, and its status becomes `done 2026-09-15`
(the release-two day, matching the spec this tree names as today). A new row 2c
carries the moved warm-prefix recording, marked `attended` and `not started`.

## Verification

- `uv run --offline pytest -q tests/test_speed_probe.py` → 27 passed.
- `uv run --offline pytest -q` → 1927 passed, 311 deselected.
- `uv run --offline ruff check` → all checks passed.
- `uv run --offline python tools/lint_docs.py` → all documents within cap.

## Not done here

Step 4's isolated admission preflight writes to `$SCR` outside this tree and
needs the live cell user, so it was not run; this tree is the task base, which
has no `PROVENANCE.md` (the provenance check creates an empty one and fails on
every file even before this change), so `just gates` is not runnable as a whole
here. The two files above and the roadmap row are the deliverables.
