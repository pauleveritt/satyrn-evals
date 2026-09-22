"""Cumulative patch capture from an evolving worktree, via an alternate index.

Each attempt adapter obtains its own patch with Git (Ruling 1: the adapter
stays the seam and harvests; Evals never reads the worktree directly). A
temporary index outside the worktree is seeded
from the exact base commit and given intent-to-add entries, making
untracked paths visible without touching the real index the next prompt
observes. The patch is cumulative from the base and includes binary,
mode, and delete changes.
"""

import os
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.workspace import GIT_SAFETY_CONFIG

#: Runtime residue a model's own tool runs leave in a worktree. A harvest
#: passes these so ``git add -N --all`` never sweeps them into a candidate;
#: the session path passes nothing and is unchanged.
#:
#: F4: satyrn-engine's mutator (``mutation.py``'s ``_atomic_replace``, ~623-646
#: at 0a6e5df) writes each edit through ``.<name>.satyrn-<16 hex>.tmp`` before
#: ``os.replace``-ing it over the real file; a harvest landing mid-write (the
#: line harvest fires from inside the still-running cell's own transcript
#: read, so this is not theoretical) would otherwise sweep the temp file into
#: the patch through ``add -N --all``. Shared here, not scoped to one harvest,
#: because no committed patch, evidence, fixture or test expectation anywhere
#: in this repository or under ``~/satyrn-runs`` names a path matching this
#: shape (checked before adding it) -- so widening it cannot change any
#: existing digest, and the final/session/tripped/line harvests all stay one
#: algorithm instead of three that can drift.
RESIDUE_EXCLUDES: tuple[str, ...] = (
    ":(exclude,glob)**/.pytest_cache/**",
    ":(exclude,glob)**/__pycache__/**",
    ":(exclude,glob)**/.ruff_cache/**",
    ":(exclude,glob)**/.venv/**",
    ":(exclude,glob)**/.*.satyrn-*.tmp",
)


@dataclass(frozen=True, slots=True)
class PatchCapture:
    patch_text: str
    changed_paths: tuple[str, ...]
    status_lines: tuple[str, ...]


def _git(
    worktree: Path,
    env: dict[str, str],
    *args: str,
    timeout: float | None = None,
    extra_config: Sequence[str] = (),
) -> bytes:
    result = subprocess.run(
        ["git", *GIT_SAFETY_CONFIG, *extra_config, *args],
        cwd=worktree,
        env=env,
        capture_output=True,
        check=True,
        timeout=timeout,
    )
    return result.stdout


def _parse_status_z(status_z: bytes) -> list[tuple[str, tuple[str, ...]]]:
    """Porcelain v1 -z records: XY <path>.

    The alternate index is always seeded from the base commit, so a
    worktree rename surfaces as a deletion record plus an intent-to-add
    record — never as porcelain R/C, which requires a staged rename in
    the index under inspection. Both paths are captured either way.
    """
    raw = [
        entry
        for entry in status_z.decode("utf-8", "surrogateescape").split("\0")
        if entry
    ]
    return [(entry[:2], (entry[3:],)) for entry in raw]


def build_cumulative_patch(
    worktree: Path,
    base_commit: str,
    environment: Mapping[str, str] | None = None,
    *,
    exclude: Sequence[str] = (),
    timeout: float | None = None,
    extra_config: Sequence[str] = (),
    deadline: float | None = None,
) -> PatchCapture:
    """Snapshot the whole tree as one cumulative patch from base_commit.

    ``environment`` must be the session's cleaned Git environment (the
    capture's git operations must never inherit a caller GIT_DIR or
    object-directory redirect). It defaults to the raw process
    environment for direct use, mirroring the session's own default of
    None meaning the caller's environment.

    ``timeout`` is a per-git-call ceiling in seconds, applied identically to
    each of the four git calls below; None keeps today's unbounded behaviour
    for the session and adapter callers. A tripped teardown passes a bound
    so a wedged git can never hold a cell open -- unchanged by ``deadline``.

    ``deadline`` (F2), when given, is a ``time.monotonic()`` instant that
    bounds all four git calls *together* rather than each individually: the
    per-call timeout passed to each one is however much of ``deadline``
    remains when that call starts, and a deadline already passed before a
    call starts raises ``subprocess.TimeoutExpired`` without starting it.
    Mutually exclusive with ``timeout`` in practice -- a caller passes one or
    the other, never both; ``deadline`` takes precedence if both are given.

    ``extra_config`` is forwarded to every git call as literal ``-c``
    arguments (e.g. a single ``safe.directory=<resolved path>`` scoped to
    a worktree whose Git admin data this process does not own -- C1: the
    Engine arm's own internal deliver worktree, created by the cell user).
    It is never a caller's job to widen this beyond one resolved path.
    """

    def _call_timeout() -> float | None:
        if deadline is None:
            return timeout
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(cmd="git", timeout=0.0)
        return remaining

    fd, index_path = tempfile.mkstemp(prefix="satyrn-session-index-")
    os.close(fd)
    os.unlink(index_path)  # read-tree creates it fresh
    env = {
        **(environment if environment is not None else os.environ),
        "GIT_INDEX_FILE": index_path,
    }
    try:
        _git(worktree, env, "read-tree", base_commit, timeout=_call_timeout(), extra_config=extra_config)
        _git(
            worktree, env, "add", "-N", "--all", "--", ".", *exclude,
            timeout=_call_timeout(), extra_config=extra_config,
        )
        patch_text = _git(
            worktree,
            env,
            "diff",
            "--binary",
            "--full-index",
            "--no-ext-diff",
            "--no-textconv",
            base_commit,
            timeout=_call_timeout(),
            extra_config=extra_config,
        ).decode("utf-8", "surrogateescape")
        status_z = _git(
            worktree,
            env,
            "status",
            "--porcelain",
            "--untracked-files=all",
            "-z",
            timeout=_call_timeout(),
            extra_config=extra_config,
        )
    finally:
        Path(index_path).unlink(missing_ok=True)
    changed: list[str] = []
    lines: list[str] = []
    for code, paths in _parse_status_z(status_z):
        changed.extend(paths)
        lines.append(f"{code} {paths[0]}")
    return PatchCapture(
        patch_text=patch_text,
        changed_paths=tuple(sorted(set(changed))),
        status_lines=tuple(lines),
    )
