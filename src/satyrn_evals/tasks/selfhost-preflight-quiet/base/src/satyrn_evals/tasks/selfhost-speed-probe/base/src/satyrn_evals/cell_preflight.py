"""Before an isolated sitting: the cell reaches nothing that grades, and nothing of it is left running.

``satyrn-evals launch --preflight RECORD --arm ARM`` runs these as the
maintainer, spawning the cell-side commands through sudo:

- the cell user is set up (`cell.cell_unavailable_reason`);
- no cell process is left over from an earlier cell (system agents the OS
  starts for any user are not cells);
- the cell cannot read the maintainer's checkout, task root or home;
- the cell's own ``pi --version`` is the arm's pin;
- a root-anchored ``find`` run as the cell -- the hunt Ornith ran on
  2026-09-14 -- finds no file named like grader material: ``satyrn_evals``,
  a known-good or known-broken patch, or any bundled hidden-suite file name.

The parsers are pure; `preflight_cell` takes the runner so the default tier
can drive it without spawning.
"""

import os
import pwd
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from satyrn_evals.cell import (
    CELL_HOME,
    CELL_PATH,
    CELL_USER,
    cell_command,
    cell_unavailable_reason,
)
from satyrn_evals.hygiene import overlay_digests
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

HUNT_NAMES = ("satyrn_evals", "known-good.patch", "known-broken.patch", "test_acceptance.py")
#: Executables the OS runs for every user; a cell never starts these.
SYSTEM_PREFIXES = ("/usr/libexec/", "/usr/sbin/", "/System/", "/Library/Apple/")
HUNT_TIMEOUT = 1800
_READABLE = 'for p in "$@"; do if [ -r "$p" ]; then echo "$p"; fi; done'

type Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class CellPreflight:
    problems: list[str]
    checked: dict[str, object] = field(default_factory=dict)


def hunt_names(tasks_root: Path = DEFAULT_TASKS_ROOT) -> tuple[str, ...]:
    """The fixed names plus every bundled hidden-suite ``test_*.py`` file name.

    Other overlay files (``_seed.py``, ``_contract.py``) are helpers whose
    names third-party packages also use; hunting them would refuse on noise.
    """
    overlay = {Path(path).name for path in overlay_digests(tasks_root).values()}
    return tuple(sorted({*HUNT_NAMES, *(name for name in overlay if name.startswith("test_"))}))


def hunt_argv(names: Sequence[str], root: str = "/") -> list[str]:
    expression: list[str] = []
    for index, name in enumerate(names):
        expression += [*(["-o"] if index else []), "-name", name]
    return ["/usr/bin/find", root, "-xdev", "(", *expression, ")", "-print"]


def stale_cell_processes(ps_stdout: str, cell_uid: int) -> list[str]:
    """``pid command`` for every cell-owned process that is not an OS agent (``ps -A -o pid=,uid=,command=``)."""
    stale: list[str] = []
    for line in ps_stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or not parts[1].isdigit() or int(parts[1]) != cell_uid:
            continue
        if not parts[2].startswith(SYSTEM_PREFIXES):
            stale.append(f"{parts[0]} {parts[2]}")
    return stale


def _lines(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.strip()]


def preflight_cell(
    *,
    pinned_pi: str,
    protected: Sequence[Path],
    tasks_root: Path = DEFAULT_TASKS_ROOT,
    hunt_root: str | None = "/",
    run: Runner = subprocess.run,
) -> CellPreflight:
    """Every check; ``hunt_root=None`` skips the hunt (minutes on a real disk)."""
    if (reason := cell_unavailable_reason(run)) is not None:
        return CellPreflight([reason])
    environment = {"HOME": os.fspath(CELL_HOME), "PATH": os.pathsep.join(CELL_PATH)}
    root = Path("/")

    def as_cell(argv: list[str], timeout: float = 60) -> subprocess.CompletedProcess[str]:
        return run(
            cell_command(argv, cwd=root, environment=environment),
            cwd="/", stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=timeout, check=False,
        )

    problems: list[str] = []
    ps = run(["/bin/ps", "-A", "-o", "pid=,uid=,command="], capture_output=True, text=True, check=False, timeout=60)
    stale = stale_cell_processes(ps.stdout, pwd.getpwnam(CELL_USER).pw_uid)
    problems += [f"a cell process is still running: {line}" for line in stale]
    paths = [os.fspath(path) for path in protected]
    problems += [f"the cell can read {path}" for path in _lines(as_cell(["/bin/sh", "-c", _READABLE, "sh", *paths]).stdout)]
    version = as_cell(["pi", "--version"]).stdout.strip()
    if version != pinned_pi:
        problems.append(f"the cell's pi --version is {version or 'missing'}, the arm pins {pinned_pi}")
    names = hunt_names(tasks_root)
    hits: list[str] = []
    if hunt_root is not None:
        hits = _lines(as_cell(hunt_argv(names, hunt_root), timeout=HUNT_TIMEOUT).stdout)
        problems += [f"the cell can find {hit}" for hit in hits]
    checked: dict[str, object] = {
        "cell_user": CELL_USER,
        "pi_version": version,
        "unreadable_checked": paths,
        "hunt_root": hunt_root,
        "hunt_names": list(names),
        "hunt_hits": hits,
        "stale_processes": stale,
    }
    return CellPreflight(problems, checked)
