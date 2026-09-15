"""``model_server_problems``: unreachable vs. reachable-but-wrong-model, no real network.

Every refusal has a success sibling over the same shape.
"""

import io
import json
import urllib.error

import pytest

from satyrn_evals.model_server import DEFAULT_MODEL_SERVER_URL, model_server_problems

BASE_URL = "http://127.0.0.1:8001"
SERVER_MODEL = "Ornith-1.5-9B-MLX-8bit"


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _listing(*ids: str) -> bytes:
    return json.dumps({"data": [{"id": model_id} for model_id in ids]}).encode()


def test_a_server_listing_the_model_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "satyrn_evals.model_server.urllib.request.urlopen",
        lambda url, timeout: _FakeResponse(_listing("other-model", SERVER_MODEL)),
    )
    assert model_server_problems(BASE_URL, SERVER_MODEL) == []


def test_a_refused_connection_is_named_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def refused(url: str, timeout: float) -> object:
        raise ConnectionRefusedError("[Errno 61] Connection refused")

    monkeypatch.setattr("satyrn_evals.model_server.urllib.request.urlopen", refused)
    problems = model_server_problems(BASE_URL, SERVER_MODEL)
    assert problems == [f"the model server at {BASE_URL} is unreachable: [Errno 61] Connection refused"]


def test_a_timeout_is_named_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def timed_out(url: str, timeout: float) -> object:
        raise TimeoutError("timed out")

    monkeypatch.setattr("satyrn_evals.model_server.urllib.request.urlopen", timed_out)
    assert model_server_problems(BASE_URL, SERVER_MODEL) == [f"the model server at {BASE_URL} is unreachable: timed out"]


def test_a_non_2xx_status_is_named_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def not_found(url: str, timeout: float) -> object:
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))

    monkeypatch.setattr("satyrn_evals.model_server.urllib.request.urlopen", not_found)
    problems = model_server_problems(BASE_URL, SERVER_MODEL)
    assert len(problems) == 1 and problems[0].startswith(f"the model server at {BASE_URL} is unreachable: HTTP Error 404")


def test_invalid_json_is_named_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "satyrn_evals.model_server.urllib.request.urlopen", lambda url, timeout: _FakeResponse(b"not json")
    )
    problems = model_server_problems(BASE_URL, SERVER_MODEL)
    assert len(problems) == 1 and problems[0].startswith(f"the model server at {BASE_URL} is unreachable:")


def test_a_reachable_server_without_the_model_names_the_model_not_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "satyrn_evals.model_server.urllib.request.urlopen", lambda url, timeout: _FakeResponse(_listing("some-other-model"))
    )
    problems = model_server_problems(BASE_URL, SERVER_MODEL)
    assert problems == [f"the model server at {BASE_URL} does not serve {SERVER_MODEL}"]


def test_the_url_joins_base_url_and_v1_models(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def urlopen(url: str, timeout: float) -> _FakeResponse:
        seen["url"], seen["timeout"] = url, timeout
        return _FakeResponse(_listing(SERVER_MODEL))

    monkeypatch.setattr("satyrn_evals.model_server.urllib.request.urlopen", urlopen)
    assert model_server_problems(BASE_URL, SERVER_MODEL, timeout=2.5) == []
    assert seen == {"url": f"{BASE_URL}/v1/models", "timeout": 2.5}


def test_the_default_base_url_is_the_omlx_port() -> None:
    assert DEFAULT_MODEL_SERVER_URL == "http://127.0.0.1:8001"
