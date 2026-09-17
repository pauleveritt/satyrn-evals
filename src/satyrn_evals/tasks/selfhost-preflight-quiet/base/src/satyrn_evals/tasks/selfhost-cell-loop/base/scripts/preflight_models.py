#!/usr/bin/env python3
"""Check that every arm in a batch names the same model.

Instrument, not production code. `scripts/preflight.sh` used to compare
only the *first* and *last* arm file's model -- a two-arm holdover from
before a third arm existed. With three arms that comparison silently
skips the middle one: a first-vs-last check can pass while the middle arm
names a different model entirely, which is exactly the "pass on an arm
nobody checked" defect the script's own PATH-resolution comment already
warns about (see `preflight_commands.py`). This checks every arm named on
the command line, not just the two at the ends.

Two things must agree across every arm: `model`, the pi-facing string
requests are sent under, and `server_model`, the bare id the omlx server
advertises. A batch that ran cells under two different models would not
be comparable across arms, and the two fields could drift independently
of each other.

Deliberately no subprocess -- this only reads and parses the committed
arm files via `satyrn_evals.arms.load_arm`.

Usage::

    scripts/preflight_models.py arms/baseline.json arms/envelope.json arms/engine.json
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from satyrn_evals.arms import Arm, load_arm  # noqa: E402

type Disagreement = tuple[str, str, str]
"""One arm's ``(arm name, model, server_model)`` that does not match the
rest of the set."""


def load_arms(arm_paths: Sequence[Path]) -> list[Arm]:
    """Every arm file, in the order given."""
    return [load_arm(path) for path in arm_paths]


def disagreeing(arms: Sequence[Arm]) -> list[Disagreement]:
    """Every arm whose model or server_model differs from the first arm's.

    An empty result means all arms agree; it says nothing else about the
    arms passed in, including whether there was more than one.
    """
    if not arms:
        return []
    model, server_model = arms[0].model, arms[0].server_model
    return [
        (arm.arm, arm.model, arm.server_model)
        for arm in arms
        if arm.model != model or arm.server_model != server_model
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arms", nargs="+", type=Path)
    args = parser.parse_args(argv)

    arms = load_arms(args.arms)
    if mismatches := disagreeing(arms):
        # Every arm is printed, not only the mismatching ones: which arm is
        # *wrong* is a judgement the reader makes, and `disagreeing` measures
        # against the first arm, which may itself be the odd one out.
        for arm in arms:
            print(
                f"preflight FAILED: arm {arm.arm!r} names model={arm.model!r} "
                f"server_model={arm.server_model!r}",
                file=sys.stderr,
            )
        names = ", ".join(repr(name) for name, _, _ in mismatches)
        print(
            f"preflight FAILED: arm(s) {names} differ from the first arm on "
            "model or server_model; every arm is compared, so a middle arm "
            "cannot slip through the way it could first-vs-last",
            file=sys.stderr,
        )
        return 1
    print(f"preflight ok: {len(arms)} arm(s) agree on model {arms[0].model!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
