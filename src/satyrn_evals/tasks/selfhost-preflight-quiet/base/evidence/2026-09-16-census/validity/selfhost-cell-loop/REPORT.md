# Report: the cell loop

## What I changed

- **Created `src/satyrn_evals/launch.py`** — the night's scheduling layer.
- **Created `tests/test_launch.py`** — 32 offline unit tests for it (fakes only:
  a counter clock, a recording sleep, and cell processes that write a result
  file or not).

No other files were modified. `uv run pytest -q` is green (1997 passed, 313
deselected), and `uv run ruff check` and `uv run pyrefly check` are clean on the
new files.

## How the implementation is shaped

**Planning and paths.** `Slot` is a frozen dataclass whose `name` property
formats the index as two digits. `plan_slots(arms, n)` produces `n` slots per
arm, cycling arms by `i % len(arms)`; `slot_path` is `<night>/slots/<NN>.json`.
`read_slots` walks `<night>/slots`, keeps only regular files whose stem is all
digits (so `.replaced-*` archives and stray names are skipped), and returns an
index-sorted dict.

**Classification.** `INFRASTRUCTURE_CODES` is a frozenset of the seven harness
failure `AttemptCode` members. `infrastructure_reason` renders the literal
`slot <NN> (<arm>): <code>: <message>` for those, the special
`... DEADLINE_EXCEEDED in <phase>: <message>` for a non-`command` deadline, and
`None` for every model outcome. Because `AttemptCode` is a `StrEnum`, the set
answers both member and plain-string membership.

**The loop.** `launch_cells` first creates `<night>/slots/`, then archives every
finished slot whose result is infrastructure to `<NN>.replaced-<M>.json` (a
single 1-based counter for the launch), recording each in `outcome.replaced`
with a `replaced_because` key. Pending slots are the planned slots with no
result file left on disk. The loop repeatedly starts pending slots in index
order while fewer than `k` run and the wall-clock budget
`(clock() - start) + cell_seconds <= max_seconds` holds, calling `drift()`
immediately before each spawn. Each tick sleeps `poll_interval` and polls the
running cells; exits append the parsed result to `outcome.finished` in finish
order. The first infrastructure result (or a missing result file) stops new
starts and lets the in-flight cells drain before returning. A clean drain with
nothing left is `COMPLETE`; a drain with slots that never started is `CAPPED`
with a reason containing `<count> slot(s) wait`.

**Signals.** The whole loop runs inside `run._abort_on_signals`, and
`launch_cells` catches `run.SignalAbort`/`KeyboardInterrupt` (from any call,
including `sleep`). It terminates each running cell once, polls out a
`grace`-second window on the injected clock, kills only survivors, and returns
`INTERRUPTED` with the exception type name in the reason. A second signal
during shutdown is swallowed so the function still never re-raises.

**Ledger.** `write_ledger` seeds `<night>/launch.json` with the identity keys,
`sittings` and `replaced` on first write; every write appends the sitting plus
`status`/`reason`/`ended`, extends `replaced`, refreshes the top-level
`status`/`reason`, and rewrites `slots` from the finished results in index
order. `check_night` is a no-op without a ledger and raises `UsageError`
(containing `belongs to another record`) when any identity value differs.

## Notes / judgement calls

- `n` in `plan_slots`/`launch_cells` is slots **per arm** (so `len(arms) * n`
  total), matching the phrase "n slots per arm".
- The replacement counter `M` is a single 1-based counter across the launch's
  replacement pass, which is the most direct reading of "M counts from 1".
- A cell that exits with no result file is treated as an infrastructure stop.
- Drift and the missing-record case stop new starts and let running cells
  finish, consistent with the infrastructure-result rule.
- `just gates` cannot pass in this tree: `PROVENANCE.md` is absent at the base
  commit, and `tools/provenance.py check` (which I ran once and then removed the
  template it auto-created) reports every file as missing a row. That is
  pre-existing, unrelated to this change. I did not commit anything.
