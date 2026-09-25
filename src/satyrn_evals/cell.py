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
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

#: Paths differ by platform and are overridable, so one tree runs on the
#: maintainer's Mac and on a Linux host without editing source. The cells
#: root is created and shared by the machine setup; these vars name where it
#: and the cell's home live. A value in the environment wins over the default.
CELL_HOME_ENV = "SATYRN_CELL_HOME"
CELLS_ROOT_ENV = "SATYRN_CELLS_ROOT"
_MACOS_CELL_HOME = "/Users/satyrn-cell"
_MACOS_CELLS_ROOT = "/Users/Shared/satyrn-cells"
_LINUX_CELL_HOME = "/home/satyrn-cell"
_LINUX_CELLS_ROOT = "/srv/satyrn-cells"

CELL_USER = "satyrn-cell"


@dataclass(frozen=True, slots=True)
class CellLayout:
    """Where the cell user, its home and the shared cells root live on this host."""

    home: Path
    cells_root: Path
    path: tuple[str, ...]
    shell: str


def cell_layout(environ: Mapping[str, str], *, on_macos: bool = sys.platform == "darwin") -> CellLayout:
    """The layout the environment names, or the platform's own defaults.

    Pure, and tested directly: the real layout is read once at import from the
    running interpreter's platform, which a default-tier test cannot vary
    without a second user and a real cells root.
    """
    home = Path(environ.get(CELL_HOME_ENV) or (_MACOS_CELL_HOME if on_macos else _LINUX_CELL_HOME))
    cells_root = Path(environ.get(CELLS_ROOT_ENV) or (_MACOS_CELLS_ROOT if on_macos else _LINUX_CELLS_ROOT))
    home_bins = (os.fspath(home / ".local" / "bin"), os.fspath(home / ".npm-global" / "bin"))
    system_bins = (
        ("/opt/homebrew/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin")
        if on_macos
        else ("/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin")
    )
    return CellLayout(home, cells_root, (*home_bins, *system_bins), "/bin/zsh" if on_macos else "/bin/bash")


_LAYOUT = cell_layout(os.environ)
CELL_HOME = _LAYOUT.home
CELLS_ROOT = _LAYOUT.cells_root
#: What the harness exports to an adapter: which profile this attempt runs under.
ISOLATION_ENV = "SATYRN_ISOLATION"
#: The workspace parent the harness allocated under ``CELLS_ROOT``; the
#: cell's TMPDIR, uv project environment and git config live beside the worktree.
CELL_PARENT_ENV = "SATYRN_CELL_PARENT"
#: Directories prepended to the cell's PATH. A test seam (fake ``pi``); the
#: launcher refuses an isolated admission, route-proof or campaign run with it set.
CELL_PATH_PREFIX_ENV = "SATYRN_CELL_PATH_PREFIX"
CELL_PATH: tuple[str, ...] = _LAYOUT.path
#: The cell's login shell; the model runs through it, not the maintainer's.
CELL_SHELL = _LAYOUT.shell
_CELL_SCRIPT = 'umask 007 && cd "$1" && shift && exec "$@"'


class Isolation(StrEnum):
    """The launcher profiles.

    ``isolated`` is the two-uid profile: the model runs as a second local
    user, and the kernel's permission bits are the isolation (macOS; see
    the module docstring). ``sandbox`` is the unprivileged ``bwrap`` mount
    namespace: the model runs as the maintainer under a filesystem view
    that simply does not contain the repo, the task roots or the home, so
    there is no host user, group or sudoers change (Linux). ``local`` runs
    as the maintainer with no isolation at all (contributors, Engine users,
    development plumbing).
    """

    ISOLATED = "isolated"
    SANDBOX = "sandbox"
    LOCAL = "local"

    @property
    def isolating(self) -> bool:
        """True for both isolation mechanisms, false only for the local profile."""
        return self is not Isolation.LOCAL


def isolation_from(environment: Mapping[str, str]) -> Isolation:
    """The profile the harness exported; absent means local (contributors, Engine users)."""
    raw = environment.get(ISOLATION_ENV, Isolation.LOCAL.value)
    try:
        return Isolation(raw)
    except ValueError:
        raise ValueError(
            f"{ISOLATION_ENV} must be one of {', '.join(profile.value for profile in Isolation)}, got {raw!r}"
        ) from None


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
        "SHELL": CELL_SHELL,
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
    if isolation_from(environment) is Isolation.SANDBOX:
        return sandbox_environment(parent=Path(parent), extra=extra, path_prefix=path_prefix_from(environment))
    return cell_environment(parent=Path(parent), extra=extra, path_prefix=path_prefix_from(environment))


def path_prefix_from(environment: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(entry for entry in environment.get(CELL_PATH_PREFIX_ENV, "").split(os.pathsep) if entry)


#: System trees a sandboxed cell needs read-only to run pi, uv and python.
#: One bind per root; a tree the host lacks is skipped.
SANDBOX_ROOTS: tuple[str, ...] = ("/usr", "/bin", "/sbin", "/lib", "/lib64", "/etc", "/run")


def sandbox_tool_binds(home: Path | None = None) -> tuple[tuple[str, str], ...]:
    """(source, dest) of the maintainer's tools bound read-only at neutral paths.

    pi's managed install and the ``uv`` binary live under the maintainer's
    home. They are bound at ``/opt/satyrn`` rather than at their own paths: a
    bind at ``$HOME/.pi`` would make ``$HOME`` itself exist in the view (as a
    mount point), and the sandbox is supposed to make the home *absent*, not
    empty. pi's managed launcher finds its install relative to its own path,
    so it runs unchanged from the new location.
    """
    base = home or Path.home()
    return (
        (os.fspath(base / ".pi"), "/opt/satyrn/pi"),
        (os.fspath(base / ".local" / "bin"), "/opt/satyrn/bin"),
    )


#: The sandbox cell's PATH: the bound tool dirs, then the host's system bins.
SANDBOX_PATH: tuple[str, ...] = (
    "/opt/satyrn/pi/agent/bin",
    "/opt/satyrn/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
)


def sandbox_environment(
    *, parent: Path, extra: Mapping[str, str] | None = None, path_prefix: Sequence[str] = ()
) -> dict[str, str]:
    """The whole environment a sandboxed cell sees; nothing else is inherited.

    ``HOME`` is a per-cell directory inside the workspace parent (the only
    writable place the sandbox binds), so pi reads its config from there and
    writes sessions there, never into the maintainer's home. ``UV_CACHE_DIR``
    is redirected for the same reason.
    """
    home = parent / "home"
    environment = {
        "HOME": os.fspath(home),
        "USER": os.environ.get("USER", "satyrn"),
        "LOGNAME": os.environ.get("LOGNAME", os.environ.get("USER", "satyrn")),
        "SHELL": CELL_SHELL,
        "PATH": os.pathsep.join([*path_prefix, *SANDBOX_PATH]),
        "TMPDIR": os.fspath(parent / "tmp"),
        "UV_PROJECT_ENVIRONMENT": os.fspath(parent / "environment"),
        "UV_CACHE_DIR": os.fspath(home / ".cache" / "uv"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_GLOBAL": os.fspath(parent / "gitconfig"),
    }
    environment.update(extra or {})
    return environment


def sandbox_command(
    argv: Sequence[str], *, parent: Path, cwd: Path, environment: Mapping[str, str]
) -> list[str]:
    """``argv`` run in an unprivileged ``bwrap`` view: tools visible, everything else not.

    The view is built by naming what to bind, never by binding ``/`` and
    hiding pieces: the repo, the task roots, the retained runs and the
    maintainer's home are absent rather than denied, which is the guarantee
    a mount namespace gives and permission bits do not. ``--tmpfs /tmp``
    comes before the workspace bind so a parent allocated under ``/tmp`` is
    re-exposed; ``--unshare-pid`` and ``--die-with-parent`` keep the command's
    process tree its own and tied to this launch.
    """
    if not argv:
        raise ValueError("sandbox command is empty")
    builder = [
        "bwrap", "--die-with-parent", "--unshare-pid",
        "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
    ]
    for path in SANDBOX_ROOTS:
        if Path(path).is_dir():
            builder += ["--ro-bind", path, path]
    # The workspace parent must be bound before anything placed *under* it
    # (pi's config), or this bind mounts over that one and hides it.
    builder += ["--bind", os.fspath(parent), os.fspath(parent)]
    for source, dest in sandbox_tool_binds():
        if Path(source).exists():
            builder += ["--ro-bind", source, dest]
    # The provider config pi reads from its sandbox HOME. Bound as this one
    # file (read-only) rather than the maintainer's config directory, so
    # extensions in settings.json never reach a cell.
    config = Path.home() / ".pi" / "agent" / "models.json"
    if config.is_file():
        builder += [
            "--ro-bind", os.fspath(config), os.fspath(parent / "home" / ".pi" / "agent" / "models.json")
        ]
    builder += ["--chdir", os.fspath(cwd)]
    for key, value in sorted(environment.items()):
        builder += ["--setenv", key, value]
    builder += ["--", *argv]
    return builder


def sandbox_unavailable_reason(
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run
) -> str | None:
    """None when ``bwrap`` is installed and can build the view; else why not."""
    if shutil.which("bwrap") is None:
        return "bwrap is not installed (no unprivileged sandbox on this host)"
    probe = ["bwrap", "--die-with-parent"]
    for path in SANDBOX_ROOTS:
        if Path(path).is_dir():
            probe += ["--ro-bind", path, path]
    probe += ["--dev", "/dev", "--proc", "/proc", "--", "/usr/bin/true"]
    try:
        completed = run(probe, cwd="/", capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"bwrap cannot build a view: {exc}"
    if completed.returncode != 0:
        return f"bwrap exited {completed.returncode}: {os.fsdecode(completed.stderr).strip()}"
    return None


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


def _maintainer_name() -> str:
    return pwd.getpwuid(os.getuid()).pw_name


def maintainer_ace() -> str:
    """The macOS ``chmod +a`` entry: full rights, inherited by new entries."""
    return f"user:{_maintainer_name()} allow {MAINTAINER_RIGHTS}"


def maintainer_acl() -> str:
    """The POSIX ``setfacl`` spec for the same: access and default entries.

    The ``u:``/``d:u:`` entries are the maintainer's, inherited by entries
    created below. The ``g::``/``d:g::`` entries are not decoration: a POSIX
    ``chmod`` sets a file's ACL *mask*, not its owning-group entry, so a
    directory granted only ``u:...`` keeps ``group::---`` (synthesized from
    the mode it had) and the *cell group* -- the user the whole design exists
    to let in -- is denied however the mask reads. Naming the group here is
    what keeps ``share_with_cell``'s ``chmod`` (which moves the mask) from
    locking the cell out.

    A named-user entry is capped by each file's mask, which the kernel derives
    from the mode its creator asked for: a cell writing a plain group-writable
    file (``umask 007``, the cell script's) leaves the mask permissive, so the
    maintainer's entry holds for the files an attempt produces. A file the cell
    deliberately creates ``0600`` masks both entries out and stays the
    maintainer's to reach as root -- the one place POSIX ACLs are weaker than
    the Mac's inherited entry.
    """
    name = _maintainer_name()
    return f"u:{name}:rwx,d:u:{name}:rwx,g::rwx,d:g::rwx"


def grant_maintainer(
    directory: Path, run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run
) -> str | None:
    """Add the inherited maintainer ACL entry to ``directory``; why it failed, else None.

    Only entries created after this carry it, so call it on an empty directory.
    macOS uses ``chmod +a``; every other platform uses ``setfacl``.
    """
    if sys.platform == "darwin":
        argv = ["/bin/chmod", "+a", maintainer_ace(), os.fspath(directory)]
        tool = "chmod +a"
    else:
        argv = ["setfacl", "-m", maintainer_acl(), os.fspath(directory)]
        tool = "setfacl"
    try:
        completed = run(argv, capture_output=True, check=False)
    except OSError as exc:
        return f"cannot run {tool}: {exc}"
    if completed.returncode != 0:
        return f"{tool} exited {completed.returncode}: {os.fsdecode(completed.stderr).strip()}"
    return None


def _cell_group_gid() -> int | None:
    """The cell user's primary group, or ``None`` when there is no cell user.

    A contributor who has not set up the second uid gets ``None``: sharing is
    then only the group-mode widening it has always been.
    """
    try:
        return pwd.getpwnam(CELL_USER).pw_gid
    except KeyError:
        return None


def share_with_cell(root: Path, *, writable: bool = True) -> None:
    """Make every directory under ``root`` group-readable and every file group-readable.

    On macOS the cells root is ``pauleveritt:satyrn`` 2770 and BSD group
    inheritance gives every new entry the group ``satyrn``; only the mode
    needs widening. Linux has no BSD group inheritance -- a file takes its
    creator's primary group unless its parent is setgid, and the worktree's
    ``.git`` is made before ``seed`` is setgid -- so off macOS each
    maintainer-owned entry is also ``chgrp``'d to the cell's group. Without
    that, ``git`` inside the cell cannot read the worktree's git dir.

    Entries the cell user created are its own to share (it writes under
    ``umask 007``) and are left alone, as are symbolic links.

    ``writable`` (the default) widens directories to 2770 and files to
    group rw, as workspaces need. Passing ``writable=False`` shares a tree
    read-only: directories 2750 (group r-x, setgid), files g+r and g+x only
    where the owner already has x -- no group write bit anywhere under the
    tree. The engine export uses this so a cell cannot write into it.
    """
    owner = os.getuid()
    cell_gid = _cell_group_gid() if sys.platform != "darwin" else None
    for directory, _dirs, files in os.walk(root):  # never follows directory symlinks
        if os.stat(directory).st_uid == owner:
            if cell_gid is not None:
                os.chown(directory, -1, cell_gid)
            os.chmod(directory, 0o2770 if writable else 0o2750)
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink() and (info := path.stat()).st_uid == owner:
                if cell_gid is not None:
                    os.chown(path, -1, cell_gid)
                if writable:
                    os.chmod(path, info.st_mode & 0o7777 | 0o060)
                else:
                    group_bits = 0o040 | (0o010 if info.st_mode & 0o100 else 0o000)
                    os.chmod(path, info.st_mode & ~0o070 | group_bits)
