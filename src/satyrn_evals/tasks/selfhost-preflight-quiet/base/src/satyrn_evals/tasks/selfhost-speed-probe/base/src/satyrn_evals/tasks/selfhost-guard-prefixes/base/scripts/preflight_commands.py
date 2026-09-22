#!/usr/bin/env python3
"""Resolve each arm's command against PATH, before a batch spends on it.

Instrument, not production code. It exists because on 2026-09-05 preflight
went green -- engine commit, both source digests, clean trees, pi version,
a live completion -- while `satyrn-engine` was not on PATH at all: the
binary lives in the engine repo's own virtualenv. The Engine V5d smoke
launched from that shell died in under a second with "attempt command
cannot start", and a 24-cell spike launched the same way would have
aborted its whole Engine half.

Checking a commit and a digest proves *which* code would run. It does not
prove the command can be found. This closes that gap and nothing more: a
resolvable command is not a working one, which is what the V5d smoke is
for.

Deliberately no subprocess -- `shutil.which` is a PATH lookup, and the
default test tier forbids spawning.

Usage::

    scripts/preflight_commands.py arms/baseline.json arms/engine.json
"""

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

type Resolution = tuple[str, str, str | None]
"""One arm's ``(arm name, command, resolved absolute path or None)``."""


def resolve_arm_commands(
    arm_paths: Sequence[Path], *, path: str | None = None
) -> list[Resolution]:
    """Resolve every arm's ``argv[0]``, preserving the given arm order.

    ``path`` overrides the PATH searched, which is what makes this
    testable without touching the caller's environment.
    """
    resolutions: list[Resolution] = []
    for arm_path in arm_paths:
        arm = json.loads(Path(arm_path).read_text(encoding="utf-8"))
        match arm.get("argv"):
            case [str() as command, *_]:
                resolutions.append(
                    (
                        str(arm.get("arm", arm_path)),
                        command,
                        shutil.which(command, path=path),
                    )
                )
            case _:
                raise ValueError(f"{arm_path}: arm has no argv[0] to resolve")
    return resolutions


def unresolved(resolutions: Sequence[Resolution]) -> list[Resolution]:
    """The arms whose command PATH could not find -- the refusal set."""
    return [entry for entry in resolutions if entry[2] is None]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("arms", nargs="+", type=Path)
    args = parser.parse_args(argv)

    resolutions = resolve_arm_commands(args.arms)
    if missing := unresolved(resolutions):
        for arm, command, _ in missing:
            print(
                f"preflight FAILED: arm {arm!r} command {command!r} is not on PATH; "
                "a batch would abort rather than measure",
                file=sys.stderr,
            )
        return 1
    for arm, command, resolved in resolutions:
        print(f"preflight ok: arm {arm} command {command} resolves to {resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
