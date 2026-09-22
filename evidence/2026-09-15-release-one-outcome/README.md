# Evidence for the Phase 3b deep review

Scripts (read-only over `~/satyrn-runs`; nothing under `/Users/Shared` touched; no model inference):

- `cells.py` -> `cells.json`, `cells.md`: per-cell spend over every retained transcript (turns, output tokens, estimated thinking/text/tool-argument split, tool calls, first mutation turn, first test run, first failing-test signal, context growth, tool-result bytes, per-turn table).
- `reconstruct.py` -> `recon.json`, `recon.log`, `snapshots/<cell>/turn-NN.patch(+.receipt.json)`, `recon/<cell>/` (scratch worktrees): replays each cell's `write`/`edit`/file-writing bash calls into a copy of the task base and grades every mutation snapshot offline with `satyrn-evals grade` (hidden suite, allowlist as in the harness; for run-record-gate also a variant with `errors.py` included, allowlist off). Validation: reproduces the harness verdict for 11 of 14 graded cells; the 3 misses are all `selfhost-guard-prefixes`, where the model's decisive edit went through a bash form the replay skips. No ceiling-task verdict diverged.
- `phases.md`: phase breakdown for the ceiling cells (turns/tokens to first mutation, biggest single thinking turn, first hidden-pass state, spend after it).
- `stats.py` -> `stats.txt`: Fisher thresholds, power grid, futility-look pass probability, P(>= 2 of 3 reject).
- `grade-probe/`: timing probe of an offline grade (1.5 s for the known-good patch).
