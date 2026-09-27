"""The confinement preflight: the condition is the extension, not a mount view.

No cell user, no ``bwrap``, no cells root. ``preflight_confinement`` checks the
one structural fact the condition needs -- the shared extension is present --
plus the absence the design requires (the task corpus is not inside the run
tree). The rest of the condition is the audit (``confinement.audit``), which
runs on the retained transcript after each cell.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from satyrn_evals.confinement import EXTENSION_PATH


@dataclass(frozen=True, slots=True)
class CellPreflight:
    problems: list[str]
    checked: dict[str, object] = field(default_factory=dict)


def preflight_confinement(
    *,
    pinned_pi: str,
    protected: Sequence[Path] = (),
    tasks_root: Path | None = None,
    hunt_root: str | None = None,
) -> CellPreflight:
    """The confinement condition's preflight: the extension is present and the
    run is not built inside the corpus (design C1, C2).

    ``pinned_pi``, ``protected`` and ``hunt_root`` are accepted for the
    launcher's uniform call shape and unused: there is no view to build and no
    host user to check.
    """
    problems: list[str] = []
    checked: dict[str, object] = {"confinement": "extension", "extension": os.fspath(EXTENSION_PATH)}
    if not EXTENSION_PATH.is_file():
        problems.append(f"the confinement extension is missing: {EXTENSION_PATH}")
    if tasks_root is not None:
        corpus = Path(tasks_root).resolve()
        checked["tasks_root"] = os.fspath(corpus)
        if corpus.is_relative_to(Path.cwd().resolve()):
            problems.append(f"the task corpus {corpus} sits inside the run tree; the run must not contain it")
    return CellPreflight(problems, checked)
