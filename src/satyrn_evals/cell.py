"""Confinement plumbing: the profile a committed record names, and the test seam.

Isolation is policy-level, not OS-level (design C1): the model runs as the
maintainer under the shared confinement extension (``packages/confinement``).
The ``Isolation`` values are still read, because a committed record names one
and ``run_record`` maps it, but no run uses an isolating profile: the launcher
runs the confinement condition instead.

The PATH seam is the one the launch tests use to put a fake ``pi`` first on the
attempt's PATH; a deciding run refuses it.
"""

import os
from collections.abc import Mapping
from enum import StrEnum

#: What a record names and the harness exports: which profile this attempt
#: would run under. ``local`` is the only condition the design runs.
ISOLATION_ENV = "SATYRN_ISOLATION"
#: Directories prepended to the attempt's PATH. A test seam (fake ``pi``).
CELL_PATH_PREFIX_ENV = "SATYRN_CELL_PATH_PREFIX"


class Isolation(StrEnum):
    """The profile a record names.

    ``isolated`` (two-uid) and ``sandbox`` (``bwrap``) are historical values a
    committed record still carries; the design retires both, so ``gate``
    refuses to run an isolating profile rather than silently run another.
    """

    ISOLATED = "isolated"
    SANDBOX = "sandbox"
    LOCAL = "local"

    @property
    def isolating(self) -> bool:
        """True for the two retired OS profiles, false for the confinement condition."""
        return self is not Isolation.LOCAL


def isolation_from(environment: Mapping[str, str]) -> Isolation:
    """The profile the harness exported; absent means local."""
    raw = environment.get(ISOLATION_ENV, Isolation.LOCAL.value)
    try:
        return Isolation(raw)
    except ValueError:
        raise ValueError(
            f"{ISOLATION_ENV} must be one of {', '.join(profile.value for profile in Isolation)}, got {raw!r}"
        ) from None


def path_prefix_from(environment: Mapping[str, str]) -> tuple[str, ...]:
    """The PATH prefix the launch tests export, as directory entries."""
    return tuple(entry for entry in environment.get(CELL_PATH_PREFIX_ENV, "").split(os.pathsep) if entry)
