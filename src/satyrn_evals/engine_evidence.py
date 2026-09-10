"""Git-backed evidence for the engine-composed route.

The isolated worktree `satyrn-engine deliver` creates is deleted on a
successful phase -- confirmed against `delivery.py`'s own cleanup path
during the HP3 composition design's research. Only the repository and its
commits survive across phases, so candidate content and mutation kinds
are read from git directly, never from a directory snapshot the way
`attribution.snapshot`/`diff_snapshots` do for HP2's shared-workspace
seam. This module is that seam's sibling, not its replacement -- HP2's
route is untouched.
"""

import subprocess
from pathlib import Path

from satyrn_evals.attribution import Mutation, MutationKind

_STATUS_KINDS: dict[str, MutationKind] = {"A": "created", "D": "deleted"}


def git_diff_mutations(repo: Path, base: str, candidate: str) -> tuple[Mutation, ...]:
    """Every path that changed between two commits, classified the way
    `git diff --name-status` already classifies it -- one call, not a
    per-path existence probe. A status this module does not recognize
    (a rename, a copy) is treated as `modified`: conservative, and the
    same shape as everywhere else in this repository choosing the
    less-surprising reading over a guess.
    """
    result = subprocess.run(
        ["git", "diff", "--name-status", base, candidate],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    mutations: list[Mutation] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        kind = _STATUS_KINDS.get(status[0], "modified")
        mutations.append(Mutation(path=path, kind=kind))
    return tuple(mutations)


def git_show_content(repo: Path, commit: str, path: str) -> str | None:
    """One file's text content at one commit, or `None` when it does not
    exist there -- a deletion, read the same honest way `capture_candidate`
    already reads a deleted path as absent rather than as empty text.
    """
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout
