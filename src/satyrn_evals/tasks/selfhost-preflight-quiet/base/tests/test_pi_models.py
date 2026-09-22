"""``pi_models``: reading a Pi model config and finding a provider's base URL, no network."""

import json
import subprocess

import pytest

from satyrn_evals.pi_models import (
    CELL_PI_MODELS,
    provider_base_url,
    read_cell_pi_models,
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


def test_read_cell_pi_models_parses_the_sudo_cat_stdout() -> None:
    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert argv[:5] == ["sudo", "-n", "-H", "-u", "satyrn-cell"]
        assert argv[-1] == str(CELL_PI_MODELS)
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(MODELS), stderr="")

    assert read_cell_pi_models(run=run) == MODELS


def test_read_cell_pi_models_raises_oserror_on_a_nonzero_exit() -> None:
    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="sudo: a password is required")

    with pytest.raises(OSError, match="a password is required"):
        read_cell_pi_models(run=run)


def test_read_local_pi_models_reads_the_given_path(tmp_path) -> None:
    path = tmp_path / "models.json"
    path.write_text(json.dumps(MODELS), encoding="utf-8")
    assert read_local_pi_models(path) == MODELS


def test_read_pi_models_true_reads_the_cell_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("satyrn_evals.pi_models.read_cell_pi_models", lambda: {"cell": True})
    monkeypatch.setattr("satyrn_evals.pi_models.read_local_pi_models", lambda: pytest.fail("must not read local"))
    assert read_pi_models(True) == {"cell": True}


def test_read_pi_models_false_reads_the_local_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("satyrn_evals.pi_models.read_local_pi_models", lambda: {"cell": False})
    monkeypatch.setattr("satyrn_evals.pi_models.read_cell_pi_models", lambda: pytest.fail("must not read cell"))
    assert read_pi_models(False) == {"cell": False}
