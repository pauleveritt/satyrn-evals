"""``pi_models``: reading a Pi model config and finding a provider's base URL, no network."""

import json

from satyrn_evals.pi_models import (
    provider_api_key,
    provider_base_url,
    read_local_pi_models,
    read_pi_models,
)

MODELS = {"providers": {"omlx": {"baseUrl": "http://127.0.0.1:8001/v1", "models": []}}}


def test_provider_base_url_drops_the_trailing_v1() -> None:
    assert provider_base_url(MODELS, "omlx") == "http://127.0.0.1:8001"


def test_provider_base_url_is_none_for_an_unknown_provider() -> None:
    assert provider_base_url(MODELS, "anthropic") is None


def test_provider_base_url_is_none_without_a_providers_block() -> None:
    assert provider_base_url({}, "omlx") is None


def test_provider_api_key_returns_the_providers_key() -> None:
    models = {"providers": {"unsloth": {"apiKey": "sk-test", "models": []}}}
    assert provider_api_key(models, "unsloth") == "sk-test"


def test_provider_api_key_is_none_for_an_unknown_provider() -> None:
    assert provider_api_key(MODELS, "unsloth") is None


def test_provider_api_key_is_none_for_an_empty_or_non_string_key() -> None:
    assert provider_api_key({"providers": {"unsloth": {"apiKey": ""}}}, "unsloth") is None
    assert provider_api_key({"providers": {"unsloth": {"apiKey": 7}}}, "unsloth") is None


def test_read_pi_models_reads_the_given_path(tmp_path) -> None:
    path = tmp_path / "models.json"
    path.write_text(json.dumps(MODELS), encoding="utf-8")
    assert read_pi_models(path) == MODELS
    assert read_local_pi_models(path) == MODELS
