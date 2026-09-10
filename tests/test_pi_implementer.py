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
    read_env_paths,
    read_projection,
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
    model, tools, pi_bin, timeout = parse_args(["--model", MODEL])
    assert model == MODEL
    assert tools == ("read", "write", "edit")
    assert "bash" not in tools
    assert pi_bin == "pi"
    assert timeout == pi_implementer.DEFAULT_TIMEOUT_SECONDS


def test_explicit_tools_parse_in_the_order_given() -> None:
    _, tools, _, _ = parse_args(["--model", MODEL, "--tools", "read,edit"])
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


def test_an_explicit_timeout_parses() -> None:
    _, _, _, timeout = parse_args(["--model", MODEL, "--timeout", "120"])
    assert timeout == 120


def test_a_non_integer_timeout_is_refused() -> None:
    with pytest.raises(AdapterError, match="--timeout must be an integer"):
        parse_args(["--model", MODEL, "--timeout", "soon"])


def test_a_non_positive_timeout_is_refused() -> None:
    with pytest.raises(AdapterError, match="--timeout must be positive"):
        parse_args(["--model", MODEL, "--timeout", "0"])


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


def test_no_self_test_command_adds_no_extension_or_tool() -> None:
    argv = build_pi_argv(MODEL, ("read", "write"), "prompt")
    assert "-e" not in argv
    assert "run_self_test" not in ",".join(argv)


def test_an_empty_self_test_command_adds_no_extension_or_tool() -> None:
    argv = build_pi_argv(
        MODEL, ("read", "write"), "prompt", self_test_command=()
    )
    assert "-e" not in argv


def test_a_declared_self_test_command_adds_the_extension_and_tool() -> None:
    argv = build_pi_argv(
        MODEL,
        ("read", "write"),
        "prompt",
        self_test_command=("uv", "run", "pytest"),
    )
    assert "-e" in argv
    extension_path = argv[argv.index("-e") + 1]
    assert extension_path.endswith("self_test_tool.ts")
    tools_value = argv[argv.index("--tools") + 1]
    assert "run_self_test" in tools_value.split(",")


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


# --- legible failures, not bare tracebacks -----------------------------------


def test_read_env_paths_refuses_a_missing_packet_var() -> None:
    with pytest.raises(AdapterError, match=PACKET_ENV):
        read_env_paths({RESULT_ENV: "/tmp/result.json"})


def test_read_env_paths_refuses_a_missing_result_var() -> None:
    with pytest.raises(AdapterError, match=RESULT_ENV):
        read_env_paths({PACKET_ENV: "/tmp/packet.json"})


def test_read_env_paths_resolves_a_relative_result_path(tmp_path: Path) -> None:
    """A relative `SATYRN_IMPLEMENTER_RESULT` must anchor to the caller's
    cwd rather than silently producing a workspace directory nothing else
    agrees on -- caught by resolving both paths."""
    import os

    old_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        _, result_path = read_env_paths(
            {PACKET_ENV: "packet.json", RESULT_ENV: "out/result.json"}
        )
    finally:
        os.chdir(old_cwd)
    assert result_path.is_absolute()
    assert result_path == (tmp_path / "out" / "result.json").resolve()


def test_read_env_paths_accepts_real_absolute_paths(tmp_path: Path) -> None:
    packet, result = read_env_paths(
        {PACKET_ENV: str(tmp_path / "p.json"), RESULT_ENV: str(tmp_path / "r.json")}
    )
    assert packet == (tmp_path / "p.json").resolve()
    assert result == (tmp_path / "r.json").resolve()


def test_read_projection_refuses_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AdapterError, match="cannot read"):
        read_projection(tmp_path / "does-not-exist.json")


def test_read_projection_refuses_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "packet.json"
    path.write_text("{not json")
    with pytest.raises(AdapterError, match="not valid JSON"):
        read_projection(path)


def test_read_projection_refuses_a_json_list(tmp_path: Path) -> None:
    path = tmp_path / "packet.json"
    path.write_text("[1, 2, 3]")
    with pytest.raises(AdapterError, match="JSON object"):
        read_projection(path)


def test_read_projection_accepts_a_real_projection(tmp_path: Path) -> None:
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(PROJECTION))
    assert read_projection(path) == PROJECTION


# --- main(), subprocess replaced ---------------------------------------------


class _FakeRun:
    def __init__(
        self,
        *,
        exit_code: int = 0,
        writes: dict[str, str] | None = None,
        stderr_text: bytes = b"",
        raise_timeout: bool = False,
    ) -> None:
        self.exit_code = exit_code
        self.writes = writes or {}
        self.stderr_text = stderr_text
        self.raise_timeout = raise_timeout
        self.calls: list[list[str]] = []
        self.timeouts: list[object] = []
        self.envs: list[object] = []
        self.cwds: list[object] = []

    def __call__(self, argv: list[str], **kwargs: object) -> object:
        self.calls.append(list(argv))
        self.timeouts.append(kwargs.get("timeout"))
        self.envs.append(kwargs.get("env"))
        self.cwds.append(kwargs.get("cwd"))
        cwd = kwargs["cwd"]
        assert isinstance(cwd, Path)
        if self.raise_timeout:
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))
        for name, text in self.writes.items():
            path = cwd / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        stdout = kwargs["stdout"]
        stderr = kwargs["stderr"]
        assert hasattr(stdout, "write") and hasattr(stderr, "write")
        stdout.write(b'{"type": "agent_start"}\n')  # type: ignore[union-attr]
        if self.stderr_text:
            stderr.write(self.stderr_text)  # type: ignore[union-attr]
        if kwargs.get("check") and self.exit_code != 0:
            raise subprocess.CalledProcessError(self.exit_code, argv)
        return subprocess.CompletedProcess(argv, self.exit_code)


@pytest.fixture()
def seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """`main()` is called in-process here, not via a real subprocess with
    an explicit `cwd=` the way `command_implementer` sets one -- so
    `edit_dir` (`Path.cwd()`) must be chdir'd to `tmp_path` explicitly to
    reproduce the same "edit_dir == harness_dir" shape HP2's real seam
    gets for free. Without this, `main()`'s edits would land wherever the
    test runner's own cwd happens to be, not in `tmp_path` at all."""
    packet_path = tmp_path / ".satyrn-packet.json"
    result_path = tmp_path / ".satyrn-result.json"
    packet_path.write_text(json.dumps(PROJECTION))
    monkeypatch.setenv(PACKET_ENV, str(packet_path))
    monkeypatch.setenv(RESULT_ENV, str(result_path))
    monkeypatch.chdir(tmp_path)
    return {"packet": packet_path, "result": result_path, "workspace": tmp_path}


def test_main_refuses_a_corrupted_packet_before_launching_pi(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The concrete failure a review reproduced against the first version:
    a projection missing `objective` rendered its other fields and launched
    Pi anyway. It must now refuse before `subprocess.run` is ever called."""
    seam["packet"].write_text(json.dumps({"facts": ["FastAPI 0.115"]}))
    fake = _FakeRun()
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    with pytest.raises(AdapterError, match="objective"):
        main(["--model", MODEL])
    assert fake.calls == []
    assert not seam["result"].exists()


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


def test_main_sets_the_self_test_env_var_when_declared(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """PROJECTION already declares a self_test_command; this is the
    default shape every other main() test in this file already runs
    under."""
    fake = _FakeRun()
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    main(["--model", MODEL])
    env = fake.envs[0]
    assert isinstance(env, dict)
    assert json.loads(env[pi_implementer.SELF_TEST_COMMAND_ENV]) == [
        "uv", "run", "python", "-m", "pytest", "tests",
    ]


def test_main_omits_the_self_test_env_var_when_not_declared(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    projection_without_self_test = {
        key: value for key, value in PROJECTION.items() if key != "self_test_command"
    }
    seam["packet"].write_text(json.dumps(projection_without_self_test))
    fake = _FakeRun()
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    main(["--model", MODEL])
    env = fake.envs[0]
    assert isinstance(env, dict)
    assert pi_implementer.SELF_TEST_COMMAND_ENV not in env
    assert "-e" not in fake.calls[0]


def test_edit_dir_and_harness_dir_can_differ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The property the edit/harness split exists for: Pi's own edits land
    in cwd, never in the harness bookkeeping directory, when the two are
    not the same path -- proven by actually separating them, not by
    reading the implementation and trusting it. HP2's own seam keeps them
    identical (see the sibling tests above and below, all built on the
    `seam` fixture, which sets cwd nowhere and lets them default to the
    same tmp_path); this is the seam HP3 composition needs instead."""
    edit_dir = tmp_path / "worktree"
    edit_dir.mkdir()
    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()
    packet_path = harness_dir / ".satyrn-packet.json"
    result_path = harness_dir / ".satyrn-result.json"
    packet_path.write_text(json.dumps(PROJECTION))
    monkeypatch.setenv(PACKET_ENV, str(packet_path))
    monkeypatch.setenv(RESULT_ENV, str(result_path))
    monkeypatch.chdir(edit_dir)

    fake = _FakeRun(writes={"app.py": "# built\n"})
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    assert main(["--model", MODEL]) == 0

    assert fake.cwds[0] == edit_dir
    assert (edit_dir / "app.py").is_file()
    assert not (harness_dir / "app.py").exists()
    assert (harness_dir / pi_implementer.TRANSCRIPT_NAME).is_file()
    assert not (edit_dir / pi_implementer.TRANSCRIPT_NAME).exists()
    result = json.loads(result_path.read_text())
    assert result["changed_files"] == ["app.py"]


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
    assert b'{"type": "agent_start"}' in transcript.read_bytes()
    result = json.loads(seam["result"].read_text())
    assert pi_implementer.TRANSCRIPT_NAME not in result["changed_files"]


def test_the_transcript_and_stderr_accumulate_across_phases(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Corrected 2026-09-10: the first version truncated both files every
    call, so only the last phase's evidence survived a chain. Three calls in
    the same workspace -- exactly what `run_phases` does, once per step --
    must leave all three phases' bytes on disk, each behind its own marker."""
    fake = _FakeRun(writes={"app.py": "# built\n"}, stderr_text=b"warning: slow turn\n")
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)

    for _ in range(3):
        main(["--model", MODEL])

    transcript_text = (seam["workspace"] / pi_implementer.TRANSCRIPT_NAME).read_bytes()
    stderr_text = (seam["workspace"] / pi_implementer.STDERR_NAME).read_bytes()
    assert transcript_text.count(b'{"type": "agent_start"}') == 3
    assert transcript_text.count(b'"adapter_marker"') == 3
    assert b'"index": 0' in transcript_text and b'"index": 2' in transcript_text
    assert stderr_text.count(b"warning: slow turn") == 3
    counter = seam["workspace"] / pi_implementer.COUNTER_NAME
    assert counter.read_text() == "3"


def test_stderr_is_captured_rather_than_discarded(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeRun(stderr_text=b"model server unreachable\n")
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    main(["--model", MODEL])

    stderr_log = seam["workspace"] / pi_implementer.STDERR_NAME
    assert b"model server unreachable" in stderr_log.read_bytes()
    result = json.loads(seam["result"].read_text())
    assert pi_implementer.STDERR_NAME not in result["changed_files"]


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


def test_the_default_timeout_reaches_subprocess_run(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeRun()
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    main(["--model", MODEL])
    assert fake.timeouts == [pi_implementer.DEFAULT_TIMEOUT_SECONDS]


def test_an_explicit_timeout_reaches_subprocess_run(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeRun()
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    main(["--model", MODEL, "--timeout", "45"])
    assert fake.timeouts == [45]


def test_a_hung_pi_process_propagates_as_a_timeout_rather_than_hanging(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `TimeoutExpired` here is not handled specially: it propagates out
    of `main` the same as any other crash, for `run_phases`'s HP6 crash
    handling to retain one layer up."""
    fake = _FakeRun(raise_timeout=True)
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    with pytest.raises(subprocess.TimeoutExpired):
        main(["--model", MODEL, "--timeout", "5"])
    assert not seam["result"].exists()
