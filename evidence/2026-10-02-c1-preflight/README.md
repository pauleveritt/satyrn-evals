# C1 preflight: six Baseline census records under confinement

Plan: `docs/superpowers/plans/2026-10-02-c1-requalify.md`, Task 5.
Design: `docs/superpowers/specs/2026-10-02-c1-requalify-design.md`, §5.
Run on 2026-10-03, after EB0 finished, so no cell shared the machine. The
directory carries the records' issue date (2026-10-02). No model ran: the
preflight asks oMLX only for `GET /v1/models`, then runs each task's public
suite on its base and on its known-good state.

- **Machine:** Apple M5 Max, `hw.memsize` 137438953472 (128 GiB).
- **Branch:** `phase-c1` at `5b42167`. Records issued at `591a519`, on the
  bases re-cut at `7fc679f`.
- **Settings:** `scripts/preflight_settings.py arms/baseline-ornith15-9b.json`
  exited 0. oMLX and `~/.pi/agent/models.json` agree on `max_tokens` /
  `maxTokens` 16,000 and the arm's sampling. Hashes: `arm_sha256` e5936f49…,
  `omlx_entry_sha256` d84e6f97…, `pi_entry_sha256` ab238d18….

| record | preflight exit | problems | base_exit | known_good_exit | repair_base |
|---|---|---|---|---|---|
| 2026-10-02-c1-agentclinic-repair-depth-3 | 0 | none | 1 | 0 | true |
| 2026-10-02-c1-selfhost-cell-loop | 0 | none | 0 | 0 | false |
| 2026-10-02-c1-selfhost-docs-linter | 0 | none | 0 | 0 | false |
| 2026-10-02-c1-selfhost-preflight-quiet | 0 | none | 0 | 0 | false |
| 2026-10-02-c1-selfhost-run-record-gate | 0 | none | 0 | 0 | false |
| 2026-10-02-c1-selfhost-speed-probe | 0 | none | 0 | 0 | false |

depth-3 is a repair task: its base is the defect the prompt asks the model to
fix, so a red base with a green known-good is the expected shape
(`task_selftest.py`). Each `<task>.json` here is the preflight's full stdout
report. Every stderr was empty. The model server answered at
`http://127.0.0.1:8001`.

Recompute (oMLX serving the arm's model, from the evals checkout):

```sh
uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json; echo "exit $?"
D=2026-10-02; E=evidence/$D-c1-preflight
for R in records/$D-c1-*.json; do
  T=$(basename "$R" .json); T=${T#$D-c1-}
  uv run satyrn-evals launch --preflight "$R" --arm arms/baseline-ornith15-9b.json > "$E/$T.json"
  echo "$T exit $?"
done
```
