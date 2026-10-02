"""Where an arm's model server actually lives: the Pi model config it will load.

The launch preflight's model-server check (`model_server.py`) needs
`providers[provider].baseUrl` and `apiKey`, so this module holds the one reader
for the config `pi` reads -- the maintainer's own, since confinement runs the
model as the maintainer (design C1).
"""

import json
from collections.abc import Mapping
from pathlib import Path

DEFAULT_PI_MODELS = Path.home() / ".pi" / "agent" / "models.json"


def read_local_pi_models(path: Path = DEFAULT_PI_MODELS) -> dict:
    """The maintainer's own Pi model config, read directly."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_pi_models(path: Path = DEFAULT_PI_MODELS) -> dict:
    """The Pi model config a launch's arms will load."""
    return read_local_pi_models(path)


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


def provider_api_key(pi_models: Mapping[str, object], provider: str) -> str | None:
    """`providers[provider].apiKey`, or None when absent or not a usable string.

    An OpenAI-compatible server may require a bearer token (unsloth's proxy
    does); the launch preflight's ``GET /v1/models`` must send the same key
    pi sends, or a reachable server answers 401 and preflight refuses a
    sitting that would have run fine.
    """
    providers = pi_models.get("providers")
    if not isinstance(providers, dict):
        return None
    block = providers.get(provider)
    if not isinstance(block, dict):
        return None
    key = block.get("apiKey")
    return key if isinstance(key, str) and key else None
