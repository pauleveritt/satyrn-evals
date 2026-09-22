# Satyrn Evals

Proves, from retained evidence, whether the Satyrn engine keeps a small local
model on track better than bare Pi. Start with `BRIEF.md`, then `ROADMAP.md`,
then `docs/superpowers/specs/2026-09-13-release-one-design.md`.

**The result:** `docs/numbers.md` — the release-two comparison, pre-registered
and read once (Engine 16 of 24 against Baseline 2 of 24 on the primary task),
with where it did not help and what it costs. `STATE.md` has the reading order.

    uv sync
    just gates

Everything before this tree is tagged `pre-release-one-2026-09-13` on `main`.
It is evidence, not guidance; `PROVENANCE.md` names where each file here came from.

## Model settings are verified, not declared

`arms/baseline-ornith15-9b.json` carried a full `inference` block --
context window, sampling params, reasoning -- and nothing enforced it: the
served id was absent from the oMLX server's `model_settings.json`, the
config that actually governs sampling, while pi's `models.json` did carry
a matching entry. One of two configs agreeing is not the setting being
enforced, and the gap was invisible for exactly that reason. Run `uv run
python scripts/preflight_settings.py arms/<arm>.json` before trusting an
arm's `inference` block; it checks the fields listed in the script's
docstring -- compaction settings are `preflight_inference.py`'s to check,
not this script's. It is also wired into `scripts/preflight.sh`'s step
0a and fails the batch on any mismatch or missing entry, writing the
provenance block (`arm_sha256`, `omlx_entry_sha256`, `pi_entry_sha256`,
and the two entries themselves) to `$OUTPUT/settings-<arm>.json` next to
`preflight.json`, one file per arm.
