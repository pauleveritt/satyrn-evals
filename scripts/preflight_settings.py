#!/usr/bin/env python3
"""Check that an arm's declared inference settings are the ones enforced.

Instrument, not production code, in the style of `preflight_models.py` and
`preflight_inference.py` -- but where `preflight_inference.py` compares an
arm against pi's *declared* config only, this checks both sides of the
actual serving path: the oMLX server's per-model settings
(`~/.omlx/model_settings.json`) and pi's per-model entry
(`~/.pi/agent/models.json`).

`arms/baseline-ornith15-9b.json` carries a full `inference` block --
context window, sampling params, reasoning -- and nothing enforced it.
`Ornith-1.5-9B-MLX-8bit` was absent from `model_settings.json` -- the
config the oMLX server actually applies -- while pi's `models.json` did
carry a matching entry. One of two configs agreeing is not the setting
being enforced: the server ignored a `model_settings.json` id it does not
list, silently, and the arm file's block became a claim nobody checked
against the side that governs sampling. `gemma-4-12B-it-MLX-8bit` is a
live example of the same gap from the other side: it *is* registered on
the server, but the server does not enforce `temperature` at all, so the
arm's `temperature: 1.0` is a bet on nothing.

This checks only the fields in `_OMLX_FIELDS` / `_PI_DIRECT_FIELDS` /
`_PI_SAMPLING_FIELDS` below. `compaction_enabled` and
`compaction_reserve_tokens`, also present in an arm's `inference` block,
are `scripts/preflight_inference.py`'s to check (step 0c of
`preflight.sh`), which also compares `context_window`, `max_tokens` and
`temperature` against pi's `models.json` by a different lookup
(`_find_model`, matching `server_model` anywhere in the document, not
`providers[provider].models[].id`) -- two checks, two lookups, kept
deliberately separate rather than merged into one wider one.

**Stated limit.** A clean result means "the arm's numbers match what both
config files say", never "the server actually samples this way" -- that
would take a live completion, which is a different check's job.

Deliberately no subprocess: these are file reads.

Usage::

    scripts/preflight_settings.py arms/baseline-ornith15-9b.json \\
        [--omlx-settings ~/.omlx/model_settings.json] \\
        [--pi-models ~/.pi/agent/models.json] \\
        [--record PATH]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from satyrn_evals.arms import ArmError, load_arm  # noqa: E402

DEFAULT_OMLX_SETTINGS = Path.home() / ".omlx" / "model_settings.json"
DEFAULT_PI_MODELS = Path.home() / ".pi" / "agent" / "models.json"

# arm field -> oMLX `models[server_model]` field. Checked only where the
# arm declares the field: an arm that does not pin a setting is not making
# a claim this check can contradict.
_OMLX_FIELDS = {
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "min_p": "min_p",
    "context_window": "max_context_window",
    "max_tokens": "max_tokens",
    "declares_reasoning": "enable_thinking",
}

# arm field -> pi model-entry field, read directly off the entry.
_PI_DIRECT_FIELDS = {
    "context_window": "contextWindow",
    "max_tokens": "maxTokens",
    "declares_reasoning": "reasoning",
}

# arm field -> pi model-entry field, read out of `entry["samplingParams"]`.
_PI_SAMPLING_FIELDS = {
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "min_p": "min_p",
    "presence_penalty": "presence_penalty",
    "repetition_penalty": "repetition_penalty",
}


def omlx_entry(settings: dict, server_model: str) -> dict | None:
    """The `models[server_model]` entry from a parsed `model_settings.json`, or None."""
    return (settings.get("models") or {}).get(server_model)


def pi_entry(models_json: dict, provider: str, model_id: str) -> dict | None:
    """The entry under `providers[provider].models[]` whose `id == model_id`, or None."""
    provider_block = (models_json.get("providers") or {}).get(provider) or {}
    for entry in provider_block.get("models") or []:
        if entry.get("id") == model_id:
            return entry
    return None


def _agrees(arm_val: object, entry_val: object) -> bool:
    """Equal *and* not a bool standing in for a number, or vice versa.

    `True == 1` in Python, so a plain `==` would accept `enable_thinking: 1`
    for `declares_reasoning: true` -- and `min_p: false` for `min_p: 0.0`.
    int/float agreement is deliberate: `top_k: 20` and `top_k: 20.0` are the
    same config value.
    """
    if (type(arm_val) is bool) != (type(entry_val) is bool):
        return False
    return arm_val == entry_val


def compare(arm_inference: dict, omlx: dict | None, pi: dict | None) -> list[str]:
    """Human-readable mismatch lines; empty when the arm's claims agree.

    A missing entry (``None``) is one mismatch line naming which side
    lacks the id. A field the arm declares that a present entry lacks is
    also a mismatch. Comparison is exact: these are config values, not
    measurements with tolerance.
    """
    lines: list[str] = []

    if omlx is None:
        lines.append(
            "omlx: no entry for this model in model_settings.json -- the "
            "server applies its own defaults, not the arm's inference block"
        )
    else:
        for arm_field, omlx_field in _OMLX_FIELDS.items():
            if arm_field not in arm_inference:
                continue
            arm_val = arm_inference[arm_field]
            if omlx_field not in omlx:
                lines.append(
                    f"omlx: arm declares {arm_field}={arm_val!r} but "
                    f"model_settings.json has no {omlx_field!r}"
                )
                continue
            omlx_val = omlx[omlx_field]
            if not _agrees(arm_val, omlx_val):
                lines.append(
                    f"omlx: {arm_field} arm={arm_val!r} but "
                    f"model_settings.json {omlx_field}={omlx_val!r}"
                )

    if pi is None:
        lines.append(
            "pi: no entry for this model in models.json -- pi applies "
            "samplingParams only to ids it lists"
        )
    else:
        for arm_field, pi_field in _PI_DIRECT_FIELDS.items():
            if arm_field not in arm_inference:
                continue
            arm_val = arm_inference[arm_field]
            if pi_field not in pi:
                lines.append(
                    f"pi: arm declares {arm_field}={arm_val!r} but "
                    f"models.json entry has no {pi_field!r}"
                )
                continue
            pi_val = pi[pi_field]
            if not _agrees(arm_val, pi_val):
                lines.append(
                    f"pi: {arm_field} arm={arm_val!r} but "
                    f"models.json {pi_field}={pi_val!r}"
                )

        sampling_declared = any(field in arm_inference for field in _PI_SAMPLING_FIELDS)
        if sampling_declared and "samplingParams" not in pi:
            lines.append(
                "pi: arm declares sampling settings but the models.json "
                "entry has no samplingParams block at all"
            )
        elif sampling_declared:
            sampling = pi["samplingParams"]
            for arm_field, pi_field in _PI_SAMPLING_FIELDS.items():
                if arm_field not in arm_inference:
                    continue
                arm_val = arm_inference[arm_field]
                if pi_field not in sampling:
                    lines.append(
                        f"pi: arm declares {arm_field}={arm_val!r} but "
                        f"samplingParams has no {pi_field!r}"
                    )
                    continue
                pi_val = sampling[pi_field]
                if not _agrees(arm_val, pi_val):
                    lines.append(
                        f"pi: {arm_field} arm={arm_val!r} but "
                        f"samplingParams.{pi_field}={pi_val!r}"
                    )

    return lines


def _digest(obj: object) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def provenance(arm_path_text: str, omlx: dict | None, pi: dict | None) -> dict:
    """The record a pre-run note pastes: what was compared, and its digests.

    Digests are over canonical JSON (`sort_keys=True`), so a dict with the
    same content in a different key order digests the same -- the digest
    names *content*, not the byte layout of whichever file it came from.
    """
    arm_obj = json.loads(arm_path_text)
    return {
        "arm_sha256": _digest(arm_obj),
        "omlx_entry_sha256": _digest(omlx) if omlx is not None else None,
        "pi_entry_sha256": _digest(pi) if pi is not None else None,
        "omlx_entry": omlx,
        "pi_entry": pi,
    }


def _read_json(path: Path) -> dict:
    """Parse `path` as a JSON object; raises on any unreadable input.

    Callers convert `OSError` and `json.JSONDecodeError` into the CLI's
    exit code 2 -- this function does not know about exit codes, only
    about what "unreadable" means.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arm", type=Path)
    parser.add_argument("--omlx-settings", type=Path, default=DEFAULT_OMLX_SETTINGS)
    parser.add_argument("--pi-models", type=Path, default=DEFAULT_PI_MODELS)
    parser.add_argument("--record", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        # `load_arm` is the house reader (`preflight_models.py` uses it
        # too): it refuses a missing/wrong-typed field and, separately, a
        # `model` that does not address its `server_model` -- both authoring
        # errors, not a settings mismatch, so both belong at exit 2, not a
        # traceback that `preflight.sh` would misreport as "not verified".
        loaded_arm = load_arm(args.arm)
        # Read again, raw, only for what `load_arm` does not model:
        # `inference` (not part of `Arm`) and the exact text `provenance`
        # digests.
        arm_text = args.arm.read_text(encoding="utf-8")
        arm = json.loads(arm_text)
        omlx_settings = _read_json(args.omlx_settings)
        pi_models = _read_json(args.pi_models)
    except (OSError, json.JSONDecodeError, ArmError) as exc:
        print(f"preflight_settings: unreadable input: {exc}", file=sys.stderr)
        return 2

    provider, _, model_id = loaded_arm.model.partition("/")
    server_model = loaded_arm.server_model

    omlx = omlx_entry(omlx_settings, server_model)
    pi = pi_entry(pi_models, provider, model_id)
    inference = arm.get("inference") or {}

    mismatches = compare(inference, omlx, pi)
    record = provenance(arm_text, omlx, pi)

    payload = json.dumps(record, indent=2, sort_keys=True)
    print(payload)
    if args.record is not None:
        try:
            args.record.write_text(payload + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"preflight_settings: cannot write record: {exc}", file=sys.stderr)
            return 2

    if mismatches:
        for line in mismatches:
            print(f"preflight_settings FAILED: {line}", file=sys.stderr)
        return 1

    print(
        f"preflight_settings ok: {loaded_arm.arm!r} settings verified "
        f"against oMLX and pi config",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
