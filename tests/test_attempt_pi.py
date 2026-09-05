"""The Baseline adapter's pure surface: argv, environment, harvesting.

No model, no network, no real subprocess. ``main`` is exercised with
``subprocess.run`` replaced in the module namespace — the same shape the
shipped session adapter's driver test uses (`tests/test_pi_session_driver.py`
`test_main_shell_spawns_serves_and_reaps`), so the executable shell is
verified in process rather than assumed.

**Why both directions.** Every refusal below has a sibling success over the
same inputs: an adapter that refused everything would preserve nothing, and
a refusal that never fires would hand pi an argv it rejects — the exact
failure the 2026-09-04 V8 smoke lost a run to.
"""

import os
import subprocess
from pathlib import Path

import pytest

from satyrn_evals import attempt, attempt_pi
from satyrn_evals.attempt_pi import (
    AdapterError,
    build_pi_argv,
    clean_pi_environment,
    harvest_patch,
    main,
    parse_args,
    read_artifact_paths,
    read_prompt,
)

MODEL = "omlx/gemma-4-12B-it-MLX-8bit"


class _FakeRun:
    """Records each ``subprocess.run`` call and answers from a script."""

    def __init__(self, *, pi_exit: int, diff: str, diff_exit: int = 0) -> None:
        self.pi_exit = pi_exit
        self.diff = diff
        self.diff_exit = diff_exit
        self.calls: list[list[str]] = []
        self.environments: list[dict[str, str]] = []

    def __call__(self, argv: list[str], **kwargs: object) -> object:
        self.calls.append(list(argv))
        if environment := kwargs.get("env"):
            assert isinstance(environment, dict)
            self.environments.append(environment)
        if argv[0] == "git":
            return subprocess.CompletedProcess(argv, self.diff_exit, self.diff, "")
        stdout = kwargs["stdout"]
        assert hasattr(stdout, "write")  # the transcript file handle
        stdout.write(b'{"type": "agent_start"}\n')  # type: ignore[union-attr]
        return subprocess.CompletedProcess(argv, self.pi_exit)


@pytest.fixture()
def seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """The environment Evals exports around an attempt command."""
    patch_path = tmp_path / "patch.diff"
    transcript_path = tmp_path / "transcript.txt"
    monkeypatch.setenv(attempt_pi.CONTRACT_ENV, "Make the failing test pass.")
    monkeypatch.setenv(attempt_pi.PATCH_ENV, str(patch_path))
    monkeypatch.setenv(attempt_pi.TRANSCRIPT_ENV, str(transcript_path))
    return {"patch": patch_path, "transcript": transcript_path}


# --- the seam's variable names are pinned to attempt.py --------------------


def test_the_adapter_reads_exactly_the_names_attempt_exports() -> None:
    """A rename on either side would otherwise strand the adapter silently:
    the recorded 2026-09-03 wrapper and this module must name the same
    variables `attempt.py` writes (`attempt.py:109-112`)."""
    assert attempt_pi.CONTRACT_ENV == attempt.TASK_CONTRACT_ENV
    assert attempt_pi.PATCH_ENV == attempt.PATCH_ENV
    assert attempt_pi.TRANSCRIPT_ENV == attempt.TRANSCRIPT_ENV


# --- argument parsing ------------------------------------------------------


def test_model_and_default_tools_parse() -> None:
    args = parse_args(["--model", MODEL])
    assert args.model == MODEL
    assert args.tools == ("read", "bash", "edit", "write")
    assert args.pi_bin == "pi"


def test_explicit_tools_parse_in_the_order_given() -> None:
    args = parse_args(["--model", MODEL, "--tools", "read,edit"])
    assert args.tools == ("read", "edit")


def test_a_trailing_contract_path_is_accepted_and_ignored() -> None:
    """Evals appends the task's engine-contract path when the manifest
    declares one (`attempt.py:115-119`). The Baseline arm's prompt comes
    from the environment, so the path is accepted and not used."""
    args = parse_args(["--model", MODEL, "/tmp/engine-contract.yaml"])
    assert args.model == MODEL


def test_missing_model_is_refused() -> None:
    with pytest.raises(AdapterError, match="--model"):
        parse_args([])


def test_the_equals_form_of_model_is_refused() -> None:
    """pi 0.84.4 records `--model=VALUE` as an unknown flag; the adapter
    never accepts a form it cannot pass on. Sibling success: the space
    form two rows above."""
    with pytest.raises(AdapterError, match="--model"):
        parse_args([f"--model={MODEL}"])


def test_rung_is_refused_because_the_rung_is_not_an_adapter_argument() -> None:
    """Spec §3: the adapter takes no `--rung`. The rung reaches it as the
    contract text in SATYRN_TASK_CONTRACT, which is the seam that keeps
    the two V11 tracks independent."""
    with pytest.raises(AdapterError, match="rung"):
        parse_args(["--model", MODEL, "--rung", "R1"])


def test_an_unknown_tool_name_is_refused() -> None:
    with pytest.raises(AdapterError, match="telepathy"):
        parse_args(["--model", MODEL, "--tools", "read,telepathy"])


def test_an_empty_tools_value_is_refused() -> None:
    with pytest.raises(AdapterError, match="--tools"):
        parse_args(["--model", MODEL, "--tools", ""])


def test_a_second_positional_argument_is_refused() -> None:
    with pytest.raises(AdapterError, match="unexpected"):
        parse_args(["--model", MODEL, "one.yaml", "two.yaml"])


def test_a_flag_missing_its_value_is_refused() -> None:
    with pytest.raises(AdapterError, match="--model"):
        parse_args(["--model"])


def test_pi_bin_overrides_the_executable() -> None:
    assert parse_args(["--model", MODEL, "--pi-bin", "/x/pi"]).pi_bin == "/x/pi"


# --- pi argv ---------------------------------------------------------------


def test_pi_argv_uses_space_form_model_and_one_joined_tools_token() -> None:
    argv = build_pi_argv(parse_args(["--model", MODEL]), "the prompt")
    assert not any(token.startswith("--model=") for token in argv)
    assert argv[argv.index("--model") + 1] == MODEL
    assert argv[argv.index("--tools") + 1] == "read,bash,edit,write"
    assert argv[0] == "pi"
    assert argv[-1] == "the prompt"
    for flag in ("--print", "--mode", "--no-session", "--no-approve"):
        assert flag in argv


def test_pi_argv_refuses_an_empty_prompt() -> None:
    with pytest.raises(AdapterError, match="prompt"):
        build_pi_argv(parse_args(["--model", MODEL]), "")


# --- the environment seam --------------------------------------------------


def test_prompt_comes_from_the_contract_variable(seam: dict[str, Path]) -> None:
    assert read_prompt(os.environ) == "Make the failing test pass."


def test_an_empty_contract_is_refused(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(attempt_pi.CONTRACT_ENV, "   ")
    with pytest.raises(AdapterError, match=attempt_pi.CONTRACT_ENV):
        read_prompt(os.environ)


def test_a_missing_contract_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(attempt_pi.CONTRACT_ENV, raising=False)
    with pytest.raises(AdapterError, match=attempt_pi.CONTRACT_ENV):
        read_prompt(os.environ)


def test_artifact_paths_come_from_the_environment(seam: dict[str, Path]) -> None:
    patch_path, transcript_path = read_artifact_paths(os.environ)
    assert patch_path == seam["patch"]
    assert transcript_path == seam["transcript"]


def test_clean_pi_environment_removes_only_the_active_venv() -> None:
    environment = {
        "VIRTUAL_ENV": "/opt/evals/.venv",
        "PATH": "/opt/evals/.venv/bin:/usr/local/bin:/opt/other/.venv/bin",
        "UV_PROJECT_ENVIRONMENT": "/tmp/satyrn-evals-uv-unique",
    }
    cleaned = clean_pi_environment(environment)
    assert "VIRTUAL_ENV" not in cleaned
    assert cleaned["PATH"] == "/usr/local/bin:/opt/other/.venv/bin"
    assert cleaned["UV_PROJECT_ENVIRONMENT"] == "/tmp/satyrn-evals-uv-unique"
    assert environment["VIRTUAL_ENV"] == "/opt/evals/.venv"


def test_clean_pi_environment_keeps_path_without_an_active_venv() -> None:
    environment = {"PATH": "/usr/local/bin:/opt/other/.venv/bin"}
    assert clean_pi_environment(environment) == environment


def test_a_missing_patch_path_is_refused(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(attempt_pi.PATCH_ENV)
    with pytest.raises(AdapterError, match=attempt_pi.PATCH_ENV):
        read_artifact_paths(os.environ)


def test_a_missing_transcript_path_is_refused(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(attempt_pi.TRANSCRIPT_ENV)
    with pytest.raises(AdapterError, match=attempt_pi.TRANSCRIPT_ENV):
        read_artifact_paths(os.environ)


# --- harvesting ------------------------------------------------------------


def test_harvest_returns_the_tracked_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRun(pi_exit=0, diff="diff --git a/x b/x\n")
    monkeypatch.setattr(attempt_pi.subprocess, "run", fake)
    assert harvest_patch() == "diff --git a/x b/x\n"
    assert fake.calls == [["git", "diff", "HEAD"]]


def test_harvest_refuses_when_git_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sibling success: the row above. An unreadable diff must refuse, not
    write an empty patch that grading would read as `NO_PATCH`."""
    fake = _FakeRun(pi_exit=0, diff="", diff_exit=128)
    monkeypatch.setattr(attempt_pi.subprocess, "run", fake)
    with pytest.raises(AdapterError, match="git diff"):
        harvest_patch()


# --- the executable shell --------------------------------------------------


def test_main_preserves_transcript_and_patch_and_returns_pi_exit(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeRun(pi_exit=0, diff="diff --git a/s.py b/s.py\n")
    monkeypatch.setattr(attempt_pi.subprocess, "run", fake)
    assert main(["--model", MODEL]) == 0
    assert seam["transcript"].read_bytes() == b'{"type": "agent_start"}\n'
    assert seam["patch"].read_text(encoding="utf-8") == "diff --git a/s.py b/s.py\n"
    assert fake.calls[0][0] == "pi"
    assert fake.calls[0][-1] == "Make the failing test pass."
    assert fake.calls[1] == ["git", "diff", "HEAD"]


def test_main_starts_pi_without_the_evals_virtual_environment(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeRun(pi_exit=0, diff="")
    monkeypatch.setattr(attempt_pi.subprocess, "run", fake)
    monkeypatch.setenv("VIRTUAL_ENV", "/opt/evals/.venv")
    monkeypatch.setenv("PATH", "/opt/evals/.venv/bin:/usr/local/bin")
    assert main(["--model", MODEL]) == 0
    assert "VIRTUAL_ENV" not in fake.environments[0]
    assert fake.environments[0]["PATH"] == "/usr/local/bin"


def test_main_preserves_artifacts_even_when_pi_exits_non_zero(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRIEF rule 3: capture happens before anything else can drop it."""
    fake = _FakeRun(pi_exit=17, diff="")
    monkeypatch.setattr(attempt_pi.subprocess, "run", fake)
    assert main(["--model", MODEL]) == 17
    assert seam["transcript"].exists()
    assert seam["patch"].read_text(encoding="utf-8") == ""


def test_main_reads_sys_argv_when_given_no_arguments(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeRun(pi_exit=0, diff="")
    monkeypatch.setattr(attempt_pi.subprocess, "run", fake)
    monkeypatch.setattr(
        attempt_pi.sys, "argv", ["satyrn-evals-attempt-pi", "--model", MODEL]
    )
    assert main() == 0
    assert fake.calls[0][argv_index := fake.calls[0].index("--model") + 1] == MODEL
    assert argv_index > 0


# --- hermetic-flag parity with the Engine arm ----------------------------
#
# Confirmed amendment, 2026-09-05 (V11b spec §9). Measurement: the same model
# and prompt cost 1,267 input tokens in an empty directory, 9,753 in this
# repository's root, and 686 with `-nc` -- so ~93% of a repo-root call was
# context-file discovery. Two independent reasons the flag must not drift:
#
#   1. An undetected contamination surface. A stray AGENTS.md in a task's
#      base/ would silently inject instructions into the model's context, and
#      nothing would flag it: the V7/V8 detector scans for grader overlay
#      text, not instruction files.
#   2. Arm parity. satyrn-engine's build_pi_command already passes these
#      flags, so a Baseline that does not is an arm *protected from* a
#      surface its rival is exposed to -- BRIEF.md rule 8's shape, inverted.
#
# Nothing else in this suite pins the flags, so without this test a future
# edit could drop one and every other assertion would still pass.

ENGINE_HERMETIC_FLAGS = (
    "--no-extensions",
    "--no-skills",
    "--no-prompt-templates",
    "--no-themes",
    "--no-context-files",
    "--no-approve",
)


def test_pi_argv_carries_every_engine_hermetic_flag() -> None:
    """Success sibling: the shipped argv is at parity with the Engine arm."""
    argv = build_pi_argv(parse_args(["--model", MODEL]), "the prompt")
    missing = [flag for flag in ENGINE_HERMETIC_FLAGS if flag not in argv]
    assert not missing, (
        f"Baseline argv is missing {missing}; the arms are not at parity"
    )


def test_context_file_discovery_is_disabled_by_name() -> None:
    """The one flag the amendment turns on, pinned on its own.

    Named separately from the parity test above so a failure says *which*
    property broke: parity with Engine, or the contamination surface itself.
    """
    argv = build_pi_argv(parse_args(["--model", MODEL]), "the prompt")
    assert "--no-context-files" in argv


def test_an_argv_without_the_flag_is_detected_as_non_parity() -> None:
    """Refusal direction: the check fires on a known-bad from this batch.

    A detector that only ever sees the good case proves nothing (BRIEF.md
    rule 8), so this drops the flag from a real argv and asserts the parity
    comparison catches it.
    """
    argv = build_pi_argv(parse_args(["--model", MODEL]), "the prompt")
    tampered = [token for token in argv if token != "--no-context-files"]
    missing = [flag for flag in ENGINE_HERMETIC_FLAGS if flag not in tampered]
    assert missing == ["--no-context-files"]
