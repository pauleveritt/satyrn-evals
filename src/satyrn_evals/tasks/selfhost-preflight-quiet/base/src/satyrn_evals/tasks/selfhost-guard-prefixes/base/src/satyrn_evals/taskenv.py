"""Task-owned project environments: detection and freeze attestation (pure)."""

from pathlib import Path


def has_locked_project(base: Path) -> bool:
    """True when ``base`` is a uv project: pyproject.toml AND uv.lock present.

    A pyproject without a lock is not a locked environment; the whole point
    of V8's environment story is that the lock, not resolution, decides.
    """
    return (base / "pyproject.toml").is_file() and (base / "uv.lock").is_file()


def parse_freeze(text: str) -> dict[str, str]:
    """Map ``uv pip freeze`` output to {normalized name: exact version}.

    Accepts only ``name==version`` lines; editable (``-e ...``) and comment
    lines are skipped. A freeze is an attestation of what is installed, so
    unparseable lines are ignored rather than fatal.
    """
    frozen: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "-e ")) or "==" not in stripped:
            continue
        name, _, version = stripped.partition("==")
        frozen[name.strip()] = version.strip()
    return frozen
