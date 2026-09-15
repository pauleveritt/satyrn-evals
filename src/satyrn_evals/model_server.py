"""Is the arm's model server actually up, checked once before the first cell.

2026-09-15 11:17: oMLX had shut down at 10:12. `launch` still passed
preflight, started a cell, and the cell died `MODEL_ERROR` "Connection
error" -- correctly classified as an infrastructure stop, but only after
wall clock and a slot were already spent finding that out. Preflight
already asks whether pi and the cell are ready (`cell_preflight`); this
asks the same question of the one dependency neither of those checks
touches -- the server a cell's first completion request will actually hit.

`GET <base_url>/v1/models` is the OpenAI-compatible listing endpoint both
oMLX and pi's `openai-completions` provider already speak; a clean
response is a JSON object with a `data` array of `{"id": ...}` entries.
Reachable-but-wrong (the server answers but never heard of this model) is
kept separate from unreachable-outright, since an operator fixes one by
starting oMLX and the other by pointing the arm at the right id.
"""

import json
import urllib.request

#: oMLX's default port on this host. Pi's own `models.json` names the same
#: origin with a `/v1` suffix already applied (`providers.omlx.baseUrl`);
#: this is the bare origin the `/v1/models` path is joined to.
DEFAULT_MODEL_SERVER_URL = "http://127.0.0.1:8001"

#: The spec's ceiling: a hung server must not turn a preflight into a
#: second thing to wait on.
MODEL_SERVER_TIMEOUT = 5.0


def model_server_problems(base_url: str, server_model: str, *, timeout: float = MODEL_SERVER_TIMEOUT) -> list[str]:
    """Zero or one problem: unreachable, or reachable but not serving `server_model`.

    `urllib.request.urlopen` raises `URLError`/`HTTPError` (both `OSError`)
    for a refused connection, a timeout, or a non-2xx status alike, so one
    except clause covers "nothing is listening" and "something is listening
    but answered badly" the same way -- both are "unreachable" from a
    launcher's point of view, distinct only from "reachable, wrong model".
    """
    url = f"{base_url}/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read()
    except (OSError, ValueError) as exc:
        return [f"the model server at {base_url} is unreachable: {exc}"]
    try:
        payload = json.loads(body)
    except ValueError as exc:
        return [f"the model server at {base_url} is unreachable: {exc}"]
    ids = {entry.get("id") for entry in (payload.get("data") or []) if isinstance(entry, dict)}
    if server_model not in ids:
        return [f"the model server at {base_url} does not serve {server_model}"]
    return []
