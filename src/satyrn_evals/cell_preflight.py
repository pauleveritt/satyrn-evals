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
import stat
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from satyrn_evals.cell import (
    CELL_HOME,
    CELL_PATH,
    CELL_USER,
    CELLS_ROOT,
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
#: F5/R13: the readable-path loop and the hunt run as the cell and read only
#: stdout; if the sudo/sh wrapper itself fails, stdout is empty and both
#: would report a clean certificate. Every as-cell probe prints this as the
#: last line of its own stdout, whether or not the probed command succeeded
#: (``find`` exits non-zero on permission errors, for one), so a missing
#: sentinel names the wrapper failure instead of silently passing.
SENTINEL = "__satyrn_done__"


def _with_sentinel(argv: Sequence[str]) -> list[str]:
    """ARGV, wrapped so its stdout always ends with ``SENTINEL``."""
    return ["/bin/sh", "-c", '"$@"; echo ' + SENTINEL, "sh", *argv]


def _strip_sentinel(stdout: str) -> tuple[str, bool]:
    """(stdout without the trailing sentinel line, whether it was present)."""
    lines = stdout.splitlines()
    if lines and lines[-1].strip() == SENTINEL:
        return "\n".join(lines[:-1]), True
    return stdout, False

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


def _cells_root_problems(cells_root: Path, tolerated: Sequence[Path] = ()) -> list[str]:
    """A non-sticky root or an entry it does not vouch for (F2/R11).

    Read-only, run as the maintainer: a cell that can rename or remove
    entries in a group-writable, non-sticky root could plant its own
    directory carrying a matching export marker, so preflight names any
    entry that is not a maintainer-owned directory named ``engine-*``.

    ``tolerated`` (R5) additionally excuses an entry the launcher itself
    put there under a test seam (``cell_scratch``'s ``satyrn-test-*``
    directory, named through ``SATYRN_CELL_PATH_PREFIX``) -- but only when
    that entry is still a maintainer-owned directory; a cell-owned or
    non-directory entry at a tolerated path is still a problem, since
    tolerating it blind would let a cell plant exactly what this check
    exists to catch.
    """
    problems: list[str] = []
    try:
        mode = cells_root.stat().st_mode
    except OSError as exc:
        return [f"cannot stat the cells root {cells_root}: {exc}"]
    if not stat.S_ISVTX & mode:
        problems.append(f"the cells root {cells_root} lacks the sticky bit; fix: chmod +t {cells_root}")
    owner = os.getuid()
    try:
        entries = sorted(cells_root.iterdir())
    except OSError as exc:
        problems.append(f"cannot list the cells root {cells_root}: {exc}")
        return problems
    tolerated_set = set(tolerated)
    for entry in entries:
        try:
            info = entry.stat()
        except OSError as exc:
            problems.append(f"cannot stat {entry}: {exc}")
            continue
        maintainer_owned_dir = stat.S_ISDIR(info.st_mode) and info.st_uid == owner
        if entry in tolerated_set and maintainer_owned_dir:
            continue
        if not (maintainer_owned_dir and entry.name.startswith("engine-")):
            problems.append(f"unexpected entry in the cells root: {entry}")
    return problems


def preflight_cell(
    *,
    pinned_pi: str,
    protected: Sequence[Path],
    tasks_root: Path = DEFAULT_TASKS_ROOT,
    hunt_root: str | None = "/",
    cells_root: Path = CELLS_ROOT,
    tolerated: Sequence[Path] = (),
    run: Runner = subprocess.run,
) -> CellPreflight:
    """Every check; ``hunt_root=None`` skips the hunt (minutes on a real disk).

    ``tolerated`` (R5) is threaded straight to ``_cells_root_problems``:
    a maintainer-owned directory at one of these paths is silent, and is
    recorded in ``checked`` for the report.
    """
    if (reason := cell_unavailable_reason(run)) is not None:
        return CellPreflight([reason])
    environment = {"HOME": os.fspath(CELL_HOME), "PATH": os.pathsep.join(CELL_PATH)}
    root = Path("/")
    problems: list[str] = []

    def as_cell(argv: list[str], name: str, timeout: float = 60) -> str:
        """Stdout of ARGV run as the cell, sentinel-checked and stripped.

        A missing sentinel means the sudo/sh wrapper itself failed before
        NAME's own output could be trusted (F5/R13): named as its own
        problem rather than read as a silent, clean certificate.
        """
        completed = run(
            cell_command(_with_sentinel(argv), cwd=root, environment=environment),
            cwd="/", stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=timeout, check=False,
        )
        stdout, complete = _strip_sentinel(completed.stdout)
        if not complete:
            problems.append(f"the {name} probe did not complete (no sentinel; the cell wrapper may have failed)")
        return stdout

    problems += _cells_root_problems(cells_root, tolerated)
    ps = run(["/bin/ps", "-A", "-o", "pid=,uid=,command="], capture_output=True, text=True, check=False, timeout=60)
    stale = stale_cell_processes(ps.stdout, pwd.getpwnam(CELL_USER).pw_uid)
    problems += [f"a cell process is still running: {line}" for line in stale]
    paths = [os.fspath(path) for path in protected]
    readable = as_cell(["/bin/sh", "-c", _READABLE, "sh", *paths], "readable-path")
    problems += [f"the cell can read {path}" for path in _lines(readable)]
    version = as_cell(["pi", "--version"], "pi --version").strip()
    if version != pinned_pi:
        problems.append(f"the cell's pi --version is {version or 'missing'}, the arm pins {pinned_pi}")
    names = hunt_names(tasks_root)
    hits: list[str] = []
    if hunt_root is not None:
        hits = _lines(as_cell(hunt_argv(names, hunt_root), "hunt", timeout=HUNT_TIMEOUT))
        problems += [f"the cell can find {hit}" for hit in hits]
    checked: dict[str, object] = {
        "cell_user": CELL_USER,
        "cells_root": os.fspath(cells_root),
        "tolerated": [os.fspath(path) for path in tolerated],
        "pi_version": version,
        "unreadable_checked": paths,
        "hunt_root": hunt_root,
        "hunt_names": list(names),
        "hunt_hits": hits,
        "stale_processes": stale,
    }
    return CellPreflight(problems, checked)
