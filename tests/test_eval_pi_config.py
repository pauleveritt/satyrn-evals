"""Eval config must not depend on the maintainer's Pi installation.

Keep real config selection and environment construction; replace only file
reads, so these tests never open the developer's real credentials.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals import pi_models
from satyrn_evals.adapters.pi_session import session_child_environment
from satyrn_evals.attempt_engine import delivery_environment
from satyrn_evals.attempt_pi import clean_pi_environment
from scripts import prereqs

_EVAL_CONFIG = Path(__file__).resolve().parents[1] / "config" / "pi"
_MODELS = {"providers": {"omlx": {"baseUrl": "http://eval-server:8000/v1"}}}
_PERSONAL_MODELS = {"providers": {"personal": {"apiKey": "not-for-evals"}}}
_READERS = [pi_models.read_pi_models, pi_models.read_local_pi_models, prereqs._read_pi_models]


@pytest.mark.parametrize("reader", _READERS)
def test_default_model_lookup_reads_only_eval_config(reader, monkeypatch: pytest.MonkeyPatch) -> None:
    reads = []

    def read(path: Path, **_kwargs) -> str:
        reads.append(path)
        return json.dumps(_MODELS if path == _EVAL_CONFIG / "models.json" else _PERSONAL_MODELS)

    monkeypatch.setenv("HOME", "/a/personal/home")
    monkeypatch.setenv("PI_CODING_AGENT_DIR", "/another/personal/config")
    monkeypatch.setattr(Path, "read_text", read)
    assert reader() == _MODELS
    assert reads == [_EVAL_CONFIG / "models.json"]


@pytest.mark.parametrize("reader", _READERS)
def test_missing_eval_config_never_falls_back_to_personal_models(
    reader, monkeypatch: pytest.MonkeyPatch
) -> None:
    reads = []

    def read(path: Path, **_kwargs) -> str:
        reads.append(path)
        if path == _EVAL_CONFIG / "models.json":
            raise FileNotFoundError(path)
        return json.dumps(_PERSONAL_MODELS)

    monkeypatch.setattr(Path, "read_text", read)
    if reader is prereqs._read_pi_models:
        assert reader() == {}
    else:
        with pytest.raises(FileNotFoundError):
            reader()
    assert reads == [_EVAL_CONFIG / "models.json"]


@pytest.mark.parametrize("clean", [clean_pi_environment, delivery_environment, session_child_environment])
@pytest.mark.parametrize("active_venv", [False, True])
def test_pi_children_override_personal_config_without_changing_the_parent(
    clean, active_venv: bool
) -> None:
    environment = {
        "HOME": "/a/personal/home",
        "PI_CODING_AGENT_DIR": "/another/personal/config",
        "PATH": "/usr/bin",
    }
    if active_venv:
        environment["VIRTUAL_ENV"] = "/evals/.venv"
        environment["PATH"] = "/evals/.venv/bin:/usr/bin"
    cleaned = clean(environment)
    assert cleaned["PI_CODING_AGENT_DIR"] == str(_EVAL_CONFIG)
    assert cleaned["HOME"] == environment["HOME"]
    assert cleaned["PATH"] == "/usr/bin"
    assert environment["PI_CODING_AGENT_DIR"] == "/another/personal/config"


@pytest.mark.parametrize("clean", [clean_pi_environment, delivery_environment, session_child_environment])
def test_pi_children_set_eval_config_even_without_an_inherited_override(clean) -> None:
    assert clean({})["PI_CODING_AGENT_DIR"] == str(_EVAL_CONFIG)
