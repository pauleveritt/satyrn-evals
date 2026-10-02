"""The engine checkout an Engine arm pins, and the refusal when it is not that engine.

The Engine arm runs ``/implement`` from a checkout the harness verifies. The
arm names a commit (``pins.engine_commit``); the checkout is the arm's optional
``--engine-repo`` when present, else ``$SATYRN_ENGINE_REPO``, else the sibling
``../satyrn-engine``. Nothing is exported and no cells root is involved: under
the confinement condition the model runs as the maintainer, so the engine is an
ordinary readable checkout. ``uv run --project`` builds the checkout's working
tree, not a commit, so what must be verified is that the *running* checkout is
the pinned commit and carries the pinned guard bytes -- the failure that ran
the wrong engine silently when the arm pinned ``78ab87d`` and the sibling sat
on ``main``.
"""

import hashlib
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

from satyrn_evals.arms import Arm

#: The eval root, so the default sibling resolves the same on any machine.
ROOT = Path(__file__).resolve().parents[2]
#: The variable that names a checkout when the arm's argv does not.
ENGINE_REPO_ENV = "SATYRN_ENGINE_REPO"


def default_checkout(environment: Mapping[str, str] | None = None) -> Path:
    """The checkout ``$SATYRN_ENGINE_REPO`` names, or the sibling ``../satyrn-engine``."""
    configured = (os.environ if environment is None else environment).get(ENGINE_REPO_ENV)
    return Path(configured) if configured else ROOT.parent / "satyrn-engine"


def checkout_root(arm: Arm, environment: Mapping[str, str] | None = None) -> Path:
    """The checkout an Engine arm runs: its argv's path, the variable, or the sibling."""
    argv = list(arm.argv)
    if "--engine-repo" in argv[:-1]:
        return Path(argv[argv.index("--engine-repo") + 1])
    return default_checkout(environment)


def engine_checkout_problems(arm: Arm, environment: Mapping[str, str] | None = None) -> list[str]:
    """Why the Engine arm's checkout is not the engine the arm pins; empty when it is.

    Refuses by name when the checkout is absent, its HEAD is not the pinned
    commit (HEAD is what ``uv run --project`` builds), or a pinned
    ``packages/engine`` source is missing or differs. Other arms have no
    checkout and no problems.
    """
    if arm.arm != "engine":
        return []
    root = checkout_root(arm, environment)
    if not (root / "packages" / "engine").is_dir():
        return [f"the engine checkout {root} is missing or is not an engine tree (run `just fetch-engine`)"]
    head = subprocess.run(
        ["git", "-C", os.fspath(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if head.returncode != 0:
        return [f"the engine checkout {root} is not a Git tree: {head.stderr.strip()}"]
    actual = head.stdout.strip()
    if arm.pins.engine_commit is not None and actual != arm.pins.engine_commit:
        return [
            f"the engine checkout {root} is at {actual}, not the arm's pinned {arm.pins.engine_commit} "
            "(run `just fetch-engine`)"
        ]
    problems: list[str] = []
    for name, digest in sorted(arm.pins.digests.items()):
        source = root / "packages" / "engine" / name
        try:
            actual_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        except OSError:
            problems.append(f"the engine checkout {root} has no packages/engine/{name}")
            continue
        if actual_digest != digest:
            problems.append(f"the engine checkout {root} has packages/engine/{name} other than the pinned bytes")
    return problems
