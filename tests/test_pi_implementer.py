"""HP7's real implementer adapter: its pure surface, no real Pi.

Same shape as `test_attempt_pi.py`: `subprocess.run` is replaced in the
module namespace, so the executable shell (`main`) is verified in process
rather than assumed, with no model and no real subprocess.
"""

import json
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.adapters import pi_implementer
from satyrn_evals.adapters.pi_implementer import (
    AdapterError,
    build_pi_argv,
    main,
    parse_args,
    result_from_mutation,
)
from satyrn_evals.route import PACKET_ENV, RESULT_ENV

MODEL = "omlx/gemma-4-12B-it-MLX-8bit"

PROJECTION = {
    "objective": "Build the home page.",
    "facts": ["FastAPI 0.115"],
    "preserve": [],
    "writable_paths": ["app.py", "templates/*"],
    "self_test_command": ["uv", "run", "python", "-m", "pytest", "tests"],
}


# --- argument parsing --------------------------------------------------------


def test_default_tools_are_read_write_edit_and_never_bash() -> None:
    model, tools, pi_bin = parse_args(["--model", MODEL])
    assert model == MODEL
    assert tools == ("read", "write", "edit")
    assert "bash" not in tools
    assert pi_bin == "pi"


def test_explicit_tools_parse_in_the_order_given() -> None:
    _, tools, _ = parse_args(["--model", MODEL, "--tools", "read,edit"])
    assert tools == ("read", "edit")


def test_missing_model_is_refused() -> None:
    with pytest.raises(AdapterError, match="--model"):
        parse_args([])


def test_an_unknown_argument_is_refused() -> None:
    with pytest.raises(AdapterError, match="unknown adapter argument"):
        parse_args(["--model", MODEL, "--rung", "R1"])


def test_empty_tools_value_is_refused() -> None:
    with pytest.raises(AdapterError, match="--tools needs"):
        parse_args(["--model", MODEL, "--tools", ""])


# --- pi argv -----------------------------------------------------------------


def test_build_pi_argv_is_space_form_and_one_shot() -> None:
    argv = build_pi_argv(MODEL, ("read", "write", "edit"), "do the thing")
    assert argv == [
        "pi", "--print", "--mode", "json", "--no-session",
        "--model", MODEL,
        "--no-extensions", "--no-skills", "--no-prompt-templates",
        "--no-themes", "--no-context-files", "--no-approve",
        "--tools", "read,write,edit",
        "do the thing",
    ]


def test_an_empty_prompt_is_refused() -> None:
    with pytest.raises(AdapterError, match="empty prompt"):
        build_pi_argv(MODEL, ("read",), "   ")


# --- the honest delivered/refused reading -----------------------------------


def test_a_nonempty_diff_is_delivered() -> None:
    result = result_from_mutation(("app.py",))
    assert result.reported_outcome == "delivered"
    assert result.changed_files == ("app.py",)


def test_an_empty_diff_is_refused_not_a_silent_delivery() -> None:
    """The sibling: a settled turn that touched nothing is a refusal, the
    same rule `ImplementerResult` itself enforces for a claimed delivery."""
    result = result_from_mutation(())
    assert result.reported_outcome == "refused"
    assert result.changed_files == ()
    assert result.message


# --- main(), subprocess replaced ---------------------------------------------


class _FakeRun:
    def __init__(self, *, exit_code: int = 0, writes: dict[str, str] | None = None) -> None:
        self.exit_code = exit_code
        self.writes = writes or {}
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **kwargs: object) -> object:
        self.calls.append(list(argv))
        cwd = kwargs["cwd"]
        assert isinstance(cwd, Path)
        for name, text in self.writes.items():
            path = cwd / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        stdout = kwargs["stdout"]
        assert hasattr(stdout, "write")
        stdout.write(b'{"type": "agent_start"}\n')  # type: ignore[union-attr]
        if kwargs.get("check") and self.exit_code != 0:
            raise subprocess.CalledProcessError(self.exit_code, argv)
        return subprocess.CompletedProcess(argv, self.exit_code)


@pytest.fixture()
def seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    packet_path = tmp_path / ".satyrn-packet.json"
    result_path = tmp_path / ".satyrn-result.json"
    packet_path.write_text(json.dumps(PROJECTION))
    monkeypatch.setenv(PACKET_ENV, str(packet_path))
    monkeypatch.setenv(RESULT_ENV, str(result_path))
    return {"packet": packet_path, "result": result_path, "workspace": tmp_path}


def test_main_writes_a_delivered_result_when_pi_changes_the_workspace(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeRun(writes={"app.py": "# built\n"})
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    assert main(["--model", MODEL]) == 0

    result = json.loads(seam["result"].read_text())
    assert result["reported_outcome"] == "delivered"
    assert result["changed_files"] == ["app.py"]
    assert "--tools" in fake.calls[0] and "bash" not in fake.calls[0][fake.calls[0].index("--tools") + 1]


def test_main_writes_a_refused_result_when_nothing_changed(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeRun()
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    assert main(["--model", MODEL]) == 0

    result = json.loads(seam["result"].read_text())
    assert result["reported_outcome"] == "refused"
    assert result["changed_files"] == []


def test_the_transcript_is_written_and_excluded_from_the_diff(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The harness's own bookkeeping file must never read as the worker's
    own mutation -- it is retained evidence, listed in `HARNESS_FILES`."""
    fake = _FakeRun(writes={"app.py": "# built\n"})
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    main(["--model", MODEL])

    transcript = seam["workspace"] / pi_implementer.TRANSCRIPT_NAME
    assert transcript.is_file()
    assert transcript.read_bytes().strip() == b'{"type": "agent_start"}'
    result = json.loads(seam["result"].read_text())
    assert pi_implementer.TRANSCRIPT_NAME not in result["changed_files"]


def test_a_crashing_pi_process_propagates_rather_than_writing_a_result(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """HP6's crash handling lives in `run_phases`, one layer up: this adapter
    does not swallow a non-zero exit into a fabricated result."""
    fake = _FakeRun(exit_code=1)
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    with pytest.raises(subprocess.CalledProcessError):
        main(["--model", MODEL])
    assert not seam["result"].exists()
