"""Where an arm's model server actually lives: the Pi model config it will load.

`scripts/preflight_settings.py --cell` already reads the cell user's
`~/.pi/agent/models.json` through `sudo -n -H -u satyrn-cell cat` (the
maintainer cannot open that home) to compare an arm's `inference` block
against pi's per-model entry. The launch preflight's model-server check
(`model_server.py`) needs the same file for a different field --
`providers[provider].baseUrl` -- so this module holds the one reader both
call, rather than each guessing a fixed port or duplicating the `sudo`
invocation.
"""

import json
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

from satyrn_evals.cell import CELL_HOME, CELL_USER

DEFAULT_PI_MODELS = Path.home() / ".pi" / "agent" / "models.json"
CELL_PI_MODELS = CELL_HOME / ".pi" / "agent" / "models.json"


def read_cell_pi_models(run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> dict:
    """The cell user's Pi model config, read as the cell user; OSError when it cannot be."""
    completed = run(
        ["sudo", "-n", "-H", "-u", CELL_USER, "--", "/bin/cat", str(CELL_PI_MODELS)],
        cwd="/", capture_output=True, text=True, check=False, timeout=30,
    )
    if completed.returncode != 0:
        raise OSError(f"cannot read {CELL_PI_MODELS} as {CELL_USER}: {completed.stderr.strip()}")
    return json.loads(completed.stdout)


def read_local_pi_models(path: Path = DEFAULT_PI_MODELS) -> dict:
    """The maintainer's own Pi model config, read directly."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_pi_models(cell: bool) -> dict:
    """The Pi model config a launch's arms will actually load.

    The cell user's under isolation (the config `pi` reads inside the
    sitting); the maintainer's own otherwise.
    """
    return read_cell_pi_models() if cell else read_local_pi_models()


def provider_base_url(pi_models: Mapping[str, object], provider: str) -> str | None:
    """`providers[provider].baseUrl` with a trailing `/v1` removed, or None when absent."""
    providers = pi_models.get("providers")
    if not isinstance(providers, dict):
        return None
    block = providers.get(provider)
    if not isinstance(block, dict):
        return None
    base_url = block.get("baseUrl")
    if not isinstance(base_url, str) or not base_url:
        return None
    return base_url.removesuffix("/v1")
