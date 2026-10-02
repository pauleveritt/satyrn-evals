"""The confinement preflight: the condition is the extension, not a mount view.

No cell user, no ``bwrap``, no cells root. ``preflight_confinement`` checks the
one structural fact the condition needs -- the shared extension is present --
plus the absence the design requires: no task's ``base/`` carries grader
material, because the run tree is materialized from ``base/`` alone (design C2).
The rest of the condition is the audit (``confinement.audit``), which runs on
the retained transcript after each cell.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from satyrn_evals.confinement import EXTENSION_PATH

#: The grader directories that must stay siblings of a task's ``base/`` (design
#: C2). The run tree holds ``base/`` and the contract, nothing else; a grader
#: directory nested inside ``base/`` would be copied into the model's workspace.
GRADER_DIRS = ("overlay", "fixtures")


@dataclass(frozen=True, slots=True)
class CellPreflight:
    problems: list[str]
    checked: dict[str, object] = field(default_factory=dict)


def _grader_material_in_base(tasks_root: Path) -> list[str]:
    """Tasks whose ``base/`` carries a grader directory (design C2).

    Static and cheap: it reads only directory names, never overlay content, so
    it can run before a single cell. ``tasks_root`` must already be a real
    directory; the caller checks that first.
    """
    problems: list[str] = []
    for task_dir in sorted(path for path in tasks_root.iterdir() if path.is_dir()):
        base = task_dir / "base"
        if not base.is_dir():
            continue
        for name in GRADER_DIRS:
            if (base / name).exists():
                problems.append(
                    f"task {task_dir.name} carries grader material in its base: {base / name}"
                )
    return problems


def preflight_confinement(
    *,
    pinned_pi: str,
    protected: Sequence[Path] = (),
    tasks_root: Path | None = None,
    hunt_root: str | None = None,
) -> CellPreflight:
    """The confinement condition's preflight: the extension is present and no
    task materializes grader material into the ``base/`` the run tree is built
    from (design C1, C2).

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
        if not corpus.is_dir():
            problems.append(f"the task corpus is missing: {corpus}")
        else:
            problems += _grader_material_in_base(corpus)
    return CellPreflight(problems, checked)
