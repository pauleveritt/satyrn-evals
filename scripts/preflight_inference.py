#!/usr/bin/env python3
"""Check pi's live inference settings against what each arm records.

Instrument, not production code. It exists because of F6: pi declared this
model's ``contextWindow`` as 262,144 while the server enforced 80,000, so
pi's compaction could never fire first -- and the V11c spike then spent 70
of its 102 minutes on seven Baseline cells walking into that wall. The
mismatch was recorded before the batch and was *not* what made the batch
invalid; the gap it exposed is that an arm record pinned pi's version but
none of the settings pi's behaviour actually depends on.

`CLAUDE.md`: "Inference settings are frozen between batches... decided and
recorded before a batch, never tuned mid-sequence." This makes that
mechanical -- a setting changed under a batch is a refusal, not a
discovery afterwards.

**Stated limit.** This compares the arm record against pi's *declared*
configuration. It cannot see what the server enforces; only a live request
does, and that is what the completion check and the batch itself are for.
A drift-free result therefore means "pi is configured as recorded", never
"pi and the server agree".

Deliberately no subprocess: these are file reads.

Usage::

    scripts/preflight_inference.py arms/baseline.json arms/engine.json \\
        [--pi-config-dir ~/.pi/agent]
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

type Drift = tuple[str, str, object, object]
"""One disagreement: ``(arm, setting, recorded, live)``."""

DEFAULT_PI_CONFIG_DIR = Path.home() / ".pi" / "agent"


def live_settings(config_dir: Path, model_id: str) -> dict[str, object]:
    """pi's declared settings for ``model_id``, read from its own config.

    ``model_id`` is the arm's ``server_model`` -- the id pi lists, without
    the provider prefix the arm's ``model`` carries.
    """
    models = json.loads(
        (config_dir / "models.json").read_text(encoding="utf-8")
    )
    entry = _find_model(models, model_id)
    if entry is None:
        raise ValueError(
            f"pi's models.json does not declare {model_id!r}; "
            "an arm cannot be checked against a model pi does not list"
        )
    settings = json.loads(
        (config_dir / "settings.json").read_text(encoding="utf-8")
    )
    compaction = settings.get("compaction") or {}
    # Temperature is read from the model entry's `samplingParams`, which is
    # the only path pi actually sends. Corrected 2026-09-06: this used to
    # read `settings["temperature"]`, a key pi never reads -- verified in
    # pi 0.84.4, where `buildBaseOptions` takes `temperature` only from the
    # caller's options while `samplingParams` comes from the model entry and
    # the provider does `Object.assign(params, options.samplingParams)`.
    # Both sides of the old comparison were therefore always None: a check
    # that could not fail, in the preflight whose job is to catch those.
    sampling = entry.get("samplingParams") or {}
    return {
        "context_window": entry.get("contextWindow"),
        "max_tokens": entry.get("maxTokens"),
        "compaction_enabled": compaction.get("enabled"),
        "compaction_reserve_tokens": compaction.get("reserveTokens"),
        "temperature": sampling.get("temperature"),
    }


def _find_model(node: object, model_id: str) -> dict | None:
    """The model entry with ``id == model_id``, anywhere in the document.

    pi nests models under provider keys, and that nesting is pi's to
    change; searching for the id is stable against it.
    """
    match node:
        case dict() if node.get("id") == model_id:
            return node
        case dict():
            for value in node.values():
                if (hit := _find_model(value, model_id)) is not None:
                    return hit
        case list():
            for value in node:
                if (hit := _find_model(value, model_id)) is not None:
                    return hit
    return None


def drifted(
    arm_paths: Sequence[Path], *, config_dir: Path
) -> list[Drift]:
    """Every disagreement between an arm's record and pi's live config.

    An arm that records no ``inference`` block is itself a drift entry:
    an unrecorded setting is the condition this check exists to prevent.
    """
    drifts: list[Drift] = []
    for arm_path in arm_paths:
        arm = json.loads(Path(arm_path).read_text(encoding="utf-8"))
        name = str(arm.get("arm", arm_path))
        recorded = arm.get("inference")
        if not isinstance(recorded, dict):
            drifts.append((name, "inference", "recorded", "absent"))
            continue
        live = live_settings(config_dir, str(arm["server_model"]))
        drifts.extend(
            (name, key, recorded.get(key), live.get(key))
            for key in sorted(live)
            if recorded.get(key) != live.get(key)
        )
        # An unpinned temperature is a drift even when both sides agree that
        # it is absent: agreeing on "nobody decided" is what a check that
        # cannot fail looks like. The sampler is then the server's default,
        # which no record names and which makes counts from different
        # batches incomparable -- measured on 2026-09-06, when Baseline on
        # the same task, rung and model read 7/12 in one batch and 2/6 in
        # the next.
        # Only the both-absent case is added here: a one-sided absence is
        # already an inequality the loop above reports, and reporting it
        # twice would make one drift look like two.
        if recorded.get("temperature") is None and live.get("temperature") is None:
            drifts.append(
                (name, "temperature", recorded.get("temperature"), live.get("temperature"))
            )
    return drifts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arms", nargs="+", type=Path)
    parser.add_argument("--pi-config-dir", type=Path, default=DEFAULT_PI_CONFIG_DIR)
    args = parser.parse_args(argv)

    if drifts := drifted(args.arms, config_dir=args.pi_config_dir):
        for arm, setting, recorded, live in drifts:
            print(
                f"preflight FAILED: arm {arm!r} records {setting}={recorded!r} "
                f"but pi is configured {setting}={live!r}; an inference "
                "setting changed under the batch",
                file=sys.stderr,
            )
        return 1
    for arm_path in args.arms:
        arm = json.loads(Path(arm_path).read_text(encoding="utf-8"))
        recorded = arm["inference"]
        print(
            f"preflight ok: arm {arm.get('arm')} inference matches pi's config "
            f"(context_window={recorded['context_window']}, "
            f"compaction_reserve_tokens={recorded['compaction_reserve_tokens']})"
        )
        print(
            f"preflight ok: arm {arm.get('arm')} pins temperature="
            f"{recorded['temperature']}, and pi's models.json sends it"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
