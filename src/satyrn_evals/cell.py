"""Two-uid isolation: the model runs as ``satyrn-cell``, everything else as the maintainer.

The spec's isolation condition ("Isolation, both arms"): the harness, grader,
task directories and retained cells stay under the maintainer's uid; the
worktree lives in a group directory the cell user writes and the grader
reads; the model process runs as a second local user with its own home,
per-cell ``TMPDIR``, Pi, uv and Pi model config. Nothing is sandboxed.

What this module knows, verified on the maintainer's Mac on 2026-09-14
(isolation spike):

- ``sudo -n -H -u satyrn-cell`` works without a password (one sudoers line).
  sudo keeps the caller's working directory, and node dies with
  ``EACCES uv_cwd`` when the cell cannot enter it, so every cell command
  ``cd``s first and every caller starts sudo from a cell-readable directory.
- sudo runs the command in the caller's process group (no pty when no
  terminal is attached) and relays SIGTERM to it, but the maintainer cannot
  signal a cell-owned process: ``killpg`` skips them silently and SIGKILL
  never reaches them. A cell-side ``kill -KILL -- -PGID`` does.
- Git refuses a repository the current user does not own ("dubious
  ownership"). Each cell gets its own global git config
  (``GIT_CONFIG_GLOBAL``, protected configuration) naming its one worktree
  as a ``safe.directory`` and a commit identity. ``GIT_CONFIG_COUNT`` would
  not do: it is a repository-local variable, and the engine's ``deliver``
  strips those before it runs git.
- The cell writes into maintainer-made entries through the group
  (``satyrn``, mode 2770/660). The maintainer reads and removes what the
  cell makes through an inherited ACL entry on the workspace parent: the
  engine creates its transcript ``0600`` with ``O_EXCL``, and a tool may make
  a ``0700`` directory, so neither umask nor group bits are enough.

``env -i`` gives the model an ordinary user environment: sudo's own
``SUDO_*`` variables and the maintainer's environment never reach it.
"""

import os
import pwd
import subprocess
from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path

CELL_USER = "satyrn-cell"
CELL_HOME = Path("/Users/satyrn-cell")
CELLS_ROOT = Path("/Users/Shared/satyrn-cells")
#: What the harness exports to an adapter: which profile this attempt runs under.
ISOLATION_ENV = "SATYRN_ISOLATION"
#: The workspace parent the harness allocated under ``CELLS_ROOT``; the
#: cell's TMPDIR, uv project environment and git config live beside the worktree.
CELL_PARENT_ENV = "SATYRN_CELL_PARENT"
#: Directories prepended to the cell's PATH. A test seam (fake ``pi``); the
#: launcher refuses an isolated admission, route-proof or campaign run with it set.
CELL_PATH_PREFIX_ENV = "SATYRN_CELL_PATH_PREFIX"
CELL_PATH: tuple[str, ...] = (
    os.fspath(CELL_HOME / ".local" / "bin"),
    os.fspath(CELL_HOME / ".npm-global" / "bin"),
    "/opt/homebrew/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
)
_CELL_SCRIPT = 'umask 007 && cd "$1" && shift && exec "$@"'


class Isolation(StrEnum):
    """The launcher profiles (Ruling 1): two-uid, or the maintainer's own uid."""

    ISOLATED = "isolated"
    LOCAL = "local"


def isolation_from(environment: Mapping[str, str]) -> Isolation:
    """The profile the harness exported; absent means local (contributors, Engine users)."""
    raw = environment.get(ISOLATION_ENV, Isolation.LOCAL.value)
    try:
        return Isolation(raw)
    except ValueError:
        raise ValueError(f"{ISOLATION_ENV} must be isolated or local, got {raw!r}") from None


def cell_paths(parent: Path) -> tuple[Path, Path, Path]:
    """(TMPDIR, uv project environment, git config) of the cell whose workspace parent is ``parent``."""
    return parent / "tmp", parent / "environment", parent / "gitconfig"


def cell_gitconfig(worktree: Path) -> str:
    """The per-cell global git config: the one safe directory and a commit identity."""
    return (
        f"[safe]\n\tdirectory = {os.fspath(worktree)}\n"
        f"[user]\n\tname = {CELL_USER}\n\temail = {CELL_USER}@localhost\n"
    )


def cell_environment(
    *,
    parent: Path,
    extra: Mapping[str, str] | None = None,
    path_prefix: Sequence[str] = (),
) -> dict[str, str]:
    """The whole environment a cell command sees; nothing else is inherited."""
    tmpdir, uv_environment, gitconfig = cell_paths(parent)
    environment = {
        "HOME": os.fspath(CELL_HOME),
        "USER": CELL_USER,
        "LOGNAME": CELL_USER,
        "SHELL": "/bin/zsh",
        "PATH": os.pathsep.join([*path_prefix, *CELL_PATH]),
        "TMPDIR": os.fspath(tmpdir),
        "UV_PROJECT_ENVIRONMENT": os.fspath(uv_environment),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_GLOBAL": os.fspath(gitconfig),
    }
    environment.update(extra or {})
    return environment


def model_environment(environment: Mapping[str, str], extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """The cell environment for an adapter, from what the harness exported."""
    if not (parent := environment.get(CELL_PARENT_ENV, "")):
        raise ValueError(f"{CELL_PARENT_ENV} is required under isolation")
    return cell_environment(parent=Path(parent), extra=extra, path_prefix=path_prefix_from(environment))


def path_prefix_from(environment: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(entry for entry in environment.get(CELL_PATH_PREFIX_ENV, "").split(os.pathsep) if entry)


def cell_command(argv: Sequence[str], *, cwd: Path, environment: Mapping[str, str]) -> list[str]:
    """``argv`` run as the cell user, in ``cwd``, with exactly ``environment``."""
    if not argv:
        raise ValueError("cell command is empty")
    return [
        "sudo", "-n", "-H", "-u", CELL_USER, "--",
        "/usr/bin/env", "-i", *(f"{key}={value}" for key, value in sorted(environment.items())),
        "/bin/sh", "-c", _CELL_SCRIPT, "satyrn-cell", os.fspath(cwd), *argv,
    ]


def cell_kill_command(process_group: int) -> list[str]:
    """SIGKILL, sent as the cell user, to every cell-owned process in ``process_group``."""
    if process_group <= 1:
        raise ValueError(f"refusing to signal process group {process_group}")
    return ["sudo", "-n", "-u", CELL_USER, "--", "/bin/kill", "-KILL", "--", f"-{process_group}"]


def kill_cell_group(
    process_group: int, *, timeout: float, run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run
) -> str | None:
    """Kill the cell's members of a process group; a description of any failure, else None.

    ``kill`` exits 1 when the group is already empty; that is success here.
    """
    try:
        completed = run(
            cell_kill_command(process_group), cwd="/", capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"cannot kill the cell's process group: {exc}"
    if completed.returncode not in (0, 1):
        return f"cell kill exited {completed.returncode}: {os.fsdecode(completed.stderr).strip()}"
    return None


def cell_unavailable_reason(run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run) -> str | None:
    """None when ``sudo -n -u satyrn-cell true`` works and the cells root exists; else why not."""
    if not CELLS_ROOT.is_dir():
        return f"{CELLS_ROOT} does not exist (run the isolation setup)"
    try:
        completed = run(
            ["sudo", "-n", "-u", CELL_USER, "--", "/usr/bin/true"], cwd="/", capture_output=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"sudo -n -u {CELL_USER} cannot run: {exc}"
    if completed.returncode != 0:
        return f"sudo -n -u {CELL_USER} true exited {completed.returncode}: {os.fsdecode(completed.stderr).strip()}"
    return None


#: The rights the maintainer keeps, inherited by every file and directory created below.
MAINTAINER_RIGHTS = (
    "list,search,add_file,add_subdirectory,delete_child,read,write,append,"
    "readattr,writeattr,readextattr,writeextattr,readsecurity,delete,file_inherit,directory_inherit"
)


def maintainer_ace() -> str:
    return f"user:{pwd.getpwuid(os.getuid()).pw_name} allow {MAINTAINER_RIGHTS}"


def grant_maintainer(
    directory: Path, run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run
) -> str | None:
    """Add the inherited maintainer ACL entry to ``directory``; why it failed, else None.

    Only entries created after this carry it, so call it on an empty directory.
    """
    try:
        completed = run(["/bin/chmod", "+a", maintainer_ace(), os.fspath(directory)], capture_output=True, check=False)
    except OSError as exc:
        return f"cannot run chmod +a: {exc}"
    if completed.returncode != 0:
        return f"chmod +a exited {completed.returncode}: {os.fsdecode(completed.stderr).strip()}"
    return None


def share_with_cell(root: Path, *, writable: bool = True) -> None:
    """Make every directory under ``root`` group-readable and every file group-readable.

    The cells root is ``pauleveritt:satyrn`` 2770, so new entries are already
    group ``satyrn`` (BSD group inheritance); only the mode needs widening.
    Entries the cell user created are its own to share (it writes under
    ``umask 007``) and are left alone, as are symbolic links.

    ``writable`` (the default) widens directories to 2770 and files to
    group rw, as workspaces need. Passing ``writable=False`` shares a tree
    read-only: directories 2750 (group r-x, setgid), files g+r and g+x only
    where the owner already has x -- no group write bit anywhere under the
    tree. The engine export uses this so a cell cannot write into it.
    """
    owner = os.getuid()
    for directory, _dirs, files in os.walk(root):  # never follows directory symlinks
        if os.stat(directory).st_uid == owner:
            os.chmod(directory, 0o2770 if writable else 0o2750)
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink() and (info := path.stat()).st_uid == owner:
                if writable:
                    os.chmod(path, info.st_mode & 0o7777 | 0o060)
                else:
                    group_bits = 0o040 | (0o010 if info.st_mode & 0o100 else 0o000)
                    os.chmod(path, info.st_mode & ~0o070 | group_bits)
