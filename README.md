# Satyrn Evals — release one

Proves, from retained evidence, whether the Satyrn engine keeps a small local
model on track better than bare Pi. Start with `BRIEF.md`, then `ROADMAP.md`,
then `docs/superpowers/specs/2026-09-13-release-one-design.md`.

    uv sync
    just gates

Everything before this tree is tagged `pre-release-one-2026-09-13` on `main`.
It is evidence, not guidance; `PROVENANCE.md` names where each file here came from.

## Model settings are verified, not declared

`arms/baseline-ornith15-9b.json` carried a full `inference` block --
context window, sampling params, reasoning -- and nothing enforced it: the
served id was absent from both the oMLX server's `model_settings.json`
and pi's `models.json`, so every Ornith cell ran on whichever defaults
those programs fall back to while the arm file claimed otherwise. Run
`scripts/preflight_settings.py arms/<arm>.json` before trusting an arm's
`inference` block; it is also wired into `scripts/preflight.sh` and fails
the batch on any mismatch or missing entry. A pre-run record pastes the
provenance block the command prints on stdout (`arm_sha256`,
`omlx_entry_sha256`, `pi_entry_sha256`, and the two entries themselves).
