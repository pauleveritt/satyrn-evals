"""The prerequisite script's logic.

The script's two real effects — the Python version probe and the model-server
check — are injected seams (`python_version`'s `run`, `server_reachable`'s
`fetch`), so this default tier exercises the whole decision path with fakes:
the version floor read from `pyproject.toml`, the report, the "exactly one
backend" rule, and the server check's URL construction and membership test.
The spawn tripwire is never tripped because no test calls the real seams.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import prereqs  # noqa: E402

# --- version parsing and the floor -----------------------------------------


def test_parse_python_version_reads_a_full_line() -> None:
    assert prereqs._parse_python_version("Python 3.14.4\n") == (3, 14, 4)
    assert prereqs._parse_python_version("Python 3.11.9") == (3, 11, 9)
    assert prereqs._parse_python_version("Python3.11") == (3, 11)


def test_parse_python_version_is_unparseable_or_old_when_blank() -> None:
    assert prereqs._parse_python_version("") == (0,)
    assert prereqs._parse_python_version("Some other text") == (0,)
    assert prereqs._parse_python_version("Python") == (0,)


def test_python_floor_takes_the_lower_bound() -> None:
    assert prereqs._python_floor(">=3.14,<3.15") == (3, 14)
    assert prereqs._python_floor(">=3.11") == (3, 11)
    assert prereqs._python_floor("~=3.12.1") == (3, 12)
    assert prereqs._python_floor("<3.13") is None
    assert prereqs._python_floor("") is None


def test_required_python_reads_the_pin_from_a_file(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nrequires-python = ">=3.12,<3.13"\n', encoding="utf-8")
    assert prereqs.required_python(pyproject) == (3, 12)


def test_required_python_falls_back_when_the_file_is_absent(tmp_path: Path) -> None:
    assert prereqs.required_python(tmp_path / "missing.toml") == prereqs.FALLBACK_PYTHON


def test_python_fix_names_the_live_pin() -> None:
    floor = ".".join(str(part) for part in prereqs.required_python())
    assert floor in prereqs._python_fix()


def test_python_version_accepts_the_pinned_interpreter() -> None:
    ok, detail = prereqs.python_version(
        which=lambda name: "/usr/bin/python3", run=lambda name: "Python 3.14.4\n"
    )
    assert ok is True
    assert "3.14.4" in detail


def test_python_version_refuses_an_old_interpreter() -> None:
    ok, detail = prereqs.python_version(
        which=lambda name: "/usr/bin/python3", run=lambda name: "Python 3.9.1\n"
    )
    assert ok is False
    assert "older than" in detail


def test_python_version_reports_absent_python() -> None:
    ok, detail = prereqs.python_version(which=lambda name: None)
    assert ok is False
    assert "not on PATH" in detail


# --- PATH presence ----------------------------------------------------------


def test_binary_present_reports_absent_without_spawning() -> None:
    ok, detail = prereqs.binary_present("definitely-not-a-real-binary-xyz")
    assert ok is False
    assert "not on PATH" in detail


def test_binary_present_reports_a_path_when_found() -> None:
    ok, detail = prereqs.binary_present("git")
    assert ok is True
    assert detail


# --- provider / bare id -----------------------------------------------------


@pytest.mark.parametrize(
    ("provider", "model", "expected_bare"),
    [
        ("unsloth", "unsloth/ornith-ai/Ornith-1.5-9B-GGUF", "ornith-ai/Ornith-1.5-9B-GGUF"),
        ("ollama", "ollama/qwen2.5-coder:1.5b", "qwen2.5-coder:1.5b"),
        ("omlx", "omlx/Ornith-1.5-9B-MLX-8bit", "Ornith-1.5-9B-MLX-8bit"),
    ],
)
def test_provider_and_bare_id(provider: str, model: str, expected_bare: str) -> None:
    assert prereqs._provider_of(model) == provider
    assert prereqs._bare_id(model) == expected_bare


# --- the model-server check -------------------------------------------------


_UNSLOTH_CONFIG = {
    "providers": {
        "unsloth": {"baseUrl": "http://localhost:8888/v1", "apiKey": "secret-key"}
    }
}


def test_server_reachable_uses_the_base_url_strips_v1_and_sends_the_key() -> None:
    seen: dict[str, str | None] = {}

    def fetch(url: str, api_key: str | None) -> bytes:
        seen["url"], seen["key"] = url, api_key
        return json.dumps({"data": [{"id": "ornith-ai/Ornith-1.5-9B-GGUF"}]}).encode()

    ok, detail = prereqs.server_reachable(
        "unsloth/ornith-ai/Ornith-1.5-9B-GGUF", models=_UNSLOTH_CONFIG, fetch=fetch
    )
    assert ok is True
    assert detail == "unsloth/ornith-ai/Ornith-1.5-9B-GGUF"
    # baseUrl already ends in /v1; the URL must not double it.
    assert seen["url"] == "http://localhost:8888/v1/models"
    assert seen["key"] == "secret-key"


def test_server_reachable_reports_a_server_without_the_model() -> None:
    def fetch(url: str, api_key: str | None) -> bytes:
        return json.dumps({"data": [{"id": "some-other-model"}]}).encode()

    ok, detail = prereqs.server_reachable(
        "unsloth/ornith-ai/Ornith-1.5-9B-GGUF", models=_UNSLOTH_CONFIG, fetch=fetch
    )
    assert ok is False
    assert "does not serve ornith-ai/Ornith-1.5-9B-GGUF" in detail


def test_server_reachable_reports_an_unreachable_server() -> None:
    def fetch(url: str, api_key: str | None) -> bytes:
        raise OSError("connection refused")

    ok, detail = prereqs.server_reachable(
        "unsloth/ornith-ai/Ornith-1.5-9B-GGUF", models=_UNSLOTH_CONFIG, fetch=fetch
    )
    assert ok is False
    assert "unreachable" in detail


def test_server_reachable_rejects_a_bare_address() -> None:
    ok, detail = prereqs.server_reachable("just-a-name")
    assert ok is False
    assert "provider/model" in detail


def test_server_reachable_falls_back_to_the_default_host() -> None:
    def fetch(url: str, api_key: str | None) -> bytes:
        raise OSError(f"probe {url}")

    ok, detail = prereqs.server_reachable(
        "omlx/Ornith-1.5-9B-MLX-8bit", models={}, fetch=fetch
    )
    assert ok is False
    assert prereqs.DEFAULT_SERVER_HOSTS["omlx"] in detail


# --- backend selection ------------------------------------------------------


def test_check_backends_requires_at_least_one() -> None:
    ok, detail = prereqs.check_backends(False, which=lambda name: None)
    assert ok is False
    assert "no local model backend" in detail


def test_check_backends_lists_each_present_backend() -> None:
    ok, detail = prereqs.check_backends(
        False, which=lambda name: name if name in ("unsloth", "ollama") else None
    )
    assert ok is True
    assert detail == "unsloth, ollama"


def test_check_backends_runs_the_server_check_with_more_than_one_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Several backends on PATH is not an error; `--check-servers` verifies SATYRN_MODEL's."""
    monkeypatch.setenv("SATYRN_MODEL", "ollama/ornith-1.5:9b")
    ok, detail = prereqs.check_backends(
        True,
        which=lambda name: name if name in ("unsloth", "ollama") else None,
        reach=lambda model: (True, model),
    )
    assert ok is True
    assert detail == "ollama/ornith-1.5:9b"


def test_check_backends_reports_the_named_provider_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATYRN_MODEL", "ollama/ornith-1.5:9b")
    ok, detail = prereqs.check_backends(
        True,
        which=lambda name: name if name == "unsloth" else None,
        reach=lambda model: pytest.fail("must not probe when the provider's binary is absent"),
    )
    assert ok is False
    assert "ollama is not on PATH" in detail


def test_check_backends_runs_the_server_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATYRN_MODEL", "unsloth/ornith-ai/Ornith-1.5-9B-GGUF")
    ok, detail = prereqs.check_backends(
        True,
        which=lambda name: name if name == "unsloth" else None,
        reach=lambda model: (True, model),
    )
    assert ok is True
    assert detail == "unsloth/ornith-ai/Ornith-1.5-9B-GGUF"


def test_check_backends_fails_when_the_server_check_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATYRN_MODEL", "unsloth/ornith-ai/Ornith-1.5-9B-GGUF")
    ok, detail = prereqs.check_backends(
        True,
        which=lambda name: name if name == "unsloth" else None,
        reach=lambda model: (False, "connection refused"),
    )
    assert ok is False
    assert "connection refused" in detail


def test_check_backends_without_satyrn_model_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SATYRN_MODEL", raising=False)
    ok, detail = prereqs.check_backends(
        True,
        which=lambda name: name if name == "ollama" else None,
        reach=lambda model: pytest.fail("server check must not run without SATYRN_MODEL"),
    )
    assert ok is False
    assert "SATYRN_MODEL is not set" in detail


def test_check_backend_runs_the_server_check_when_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SATYRN_MODEL", "ollama/qwen2.5-coder:1.5b")
    ok, detail = prereqs.check_backend(
        "ollama", True, which=lambda name: name, reach=lambda model: (True, model)
    )
    assert ok is True
    assert detail == "ollama/qwen2.5-coder:1.5b"


# --- the report and the prerequisites list ---------------------------------


def test_build_prereqs_lists_the_expected_tools_with_fixes() -> None:
    built = prereqs.build_prereqs(check_servers=False)
    assert [label for label, _, _ in built] == ["git", "python", "uv", "pi", "model backend"]
    labels = {label: fix for label, fix, _ in built}
    assert "install git" in labels["git"]
    assert prereqs._python_fix() == labels["python"]
    assert prereqs.BACKEND_BINARIES[0] in labels["model backend"]


def test_run_prereqs_reports_each_outcome_with_its_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the three checks so no real process or socket is touched."""
    monkeypatch.setattr(prereqs, "binary_present", lambda name: (name == "git", name))
    monkeypatch.setattr(prereqs, "python_version", lambda: (False, "old"))
    monkeypatch.setattr(prereqs, "check_backends", lambda check_servers: (True, "unsloth"))

    results = prereqs.run_prereqs(check_servers=False)
    by_label = {label: (ok, detail) for label, (ok, detail), _ in results}
    assert by_label["git"] == (True, "git")
    assert by_label["uv"] == (False, "uv")
    assert by_label["python"] == (False, "old")
    assert by_label["model backend"] == (True, "unsloth")
    # git and the backend pass; python, uv, and pi do not.
    assert prereqs.summarize(results)[0] == 3


def test_render_report_sums_and_counts_missing() -> None:
    results = [
        ("git", (True, "git 2.47.0"), "install git — https://git-scm.com/downloads"),
        ("python", (False, "python (2, 7) is older than the pinned (3, 14)"),
         "install Python 3.14+ — https://python.org/downloads"),
    ]
    report = prereqs.render_report(results)
    assert "satyrn prerequisites:" in report
    assert "1 of 2 prerequisites are not met." in report
    assert "install Python 3.14+ — https://python.org/downloads" in report


# --- the CLI ----------------------------------------------------------------


def test_main_returns_nonzero_when_a_prerequisite_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prereqs, "run_prereqs", lambda check_servers: [("git", (False, "is not on PATH"), "install git")]
    )
    assert prereqs.main([]) == 1


def test_main_returns_zero_when_every_prerequisite_is_met(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prereqs, "run_prereqs", lambda check_servers: [("git", (True, "/usr/bin/git"), "install git")]
    )
    assert prereqs.main([]) == 0


def test_main_backend_runs_the_named_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        prereqs, "check_backend", lambda name, check_servers: (False, "not on PATH")
    )
    assert prereqs.main(["--backend", "ollama"]) == 1
