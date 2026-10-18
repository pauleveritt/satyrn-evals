# Satyrn Evals

Proves, from retained evidence, whether the Satyrn engine keeps a small local
model on track better than bare Pi. Start with `BRIEF.md`, then `ROADMAP.md`,
then `docs/superpowers/specs/2026-09-13-release-one-design.md`.

To run the stack on your own machine (unsloth, ollama, or oMLX), see
docs/user-guide.md.

**The result:** `docs/numbers.md` — the release-two comparison, pre-registered
and read once (Engine 16 of 24 against Baseline 2 of 24 on the primary task),
with where it did not help and what it costs. `STATE.md` has the reading order.

    uv sync
    just gates

Everything before this tree is tagged `pre-release-one-2026-09-13` on `main`.
It is evidence, not guidance; `PROVENANCE.md` names where each file here came from.

## Eval-owned Pi configuration

Evals do not read `~/.pi/agent`. Baseline, Engine, the session adapter, and
preflight use this checkout's `config/pi/`. Child processes override any
inherited `PI_CODING_AGENT_DIR`. Your interactive Pi configuration stays separate.

Before running cells, copy the example:

```sh
cp config/pi/models.json.example config/pi/models.json
```

Set the server URLs and an eval-specific proxy key in `config/pi/models.json`.
The example covers the Ornith oMLX and unsloth arms. Add entries for other
models before using their arms. Keep model fields consistent with each arm's
`inference` block. `config/pi/settings.json` pins compaction and high reasoning.
The reasoning setting preserves the intended condition recorded in
`docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md`, decision 18.

Git ignores local `models.json`, credentials, and runtime files. Do not copy
personal `auth.json`, extensions, skills, or settings into this directory.
Missing eval configuration never falls back to personal Pi configuration.
Run preflight before launching a record. A missing model entry refuses the run.

## Model settings are verified, not declared

`arms/baseline-ornith15-9b.json` carried a full `inference` block --
context window, sampling params, reasoning -- and nothing enforced it: the
served id was absent from the oMLX server's `model_settings.json`, the
config that actually governs sampling, while pi's `models.json` did carry
a matching entry. One of two configs agreeing is not the setting being
enforced, and the gap was invisible for exactly that reason. Run
`uv run satyrn-evals-preflight-settings arms/<arm>.json` before trusting an
arm's `inference` block. It checks the fields listed in
`src/satyrn_evals/preflight_settings.py`. Compaction settings are checked by
`satyrn-evals-preflight-inference`, not this command. It is also wired into `scripts/preflight.sh`'s step
0a and fails the batch on any mismatch or missing entry, writing the
provenance block (`arm_sha256`, `omlx_entry_sha256`, `pi_entry_sha256`,
and the two entries themselves) to `$OUTPUT/settings-<arm>.json` next to
`preflight.json`, one file per arm.
