"""The session adapter's effective tool boundary.

Why (2026-09-08). The session adapter launched pi with no tool restriction at
all, so a session ran on whatever the installed runtime happened to expose. On
the first bounded Baseline session the model reached an installed extension
(`pi-subagents`) and dispatched a **detached** worker, which wrote two files
across two checkpoint boundaries with no retained events. Per-step turn, tool
and context figures understated the work by an unknown amount, and nothing
could re-score it afterwards, because the evidence was never captured.

A `--tools` allowlist alone is not the fix: the worker came from an extension,
so extension DISCOVERY has to be off as well. The attempt adapter already does
both (`attempt_pi.py` build_pi_argv), which is why no `subagent` call appears
in any of the 36 R1 Baseline transcripts. These rows hold the session adapter
to the same boundary.
"""

import pytest

from satyrn_evals.adapters.pi_session import build_pi_argv
from satyrn_evals.errors import ProtocolError

TOOLS = ("read", "bash", "edit", "write")


def test_the_argv_disables_extension_discovery() -> None:
    """The flag that removes the installed subagent tool."""
    assert "--no-extensions" in build_pi_argv("omlx", "m", TOOLS)


def test_the_argv_carries_the_tool_allowlist_joined_once() -> None:
    """pi applies --tools to built-in, extension and custom tools alike."""
    argv = build_pi_argv("omlx", "m", TOOLS)
    assert argv[argv.index("--tools") + 1] == "read,bash,edit,write"


def test_the_argv_disables_the_other_ambient_sources() -> None:
    """Skills, prompt templates and context files are ambient input too.

    Not because any of them produced the detached worker, but because an
    effective boundary is one where every discovery path is off and the
    remaining surface is the declared one.
    """
    argv = build_pi_argv("omlx", "m", TOOLS)
    for flag in ("--no-skills", "--no-prompt-templates", "--no-context-files"):
        assert flag in argv, flag


def test_the_argv_still_drives_one_rpc_conversation() -> None:
    """Success sibling: the boundary did not change what the adapter is.

    Without this row, an adapter that returned an empty argv would satisfy
    every assertion above about what is absent.
    """
    argv = build_pi_argv("omlx", "gemma-4-12B-it-MLX-8bit", TOOLS)
    assert argv[0] == "pi"
    assert argv[argv.index("--mode") + 1] == "rpc"
    assert "--no-session" in argv
    assert argv[argv.index("--provider") + 1] == "omlx"
    assert argv[argv.index("--model") + 1] == "gemma-4-12B-it-MLX-8bit"


def test_an_empty_tool_allowlist_is_refused() -> None:
    """Refusal direction: an unstated surface is the defect being fixed.

    Defaulting to 'everything' is exactly what produced the detached worker,
    and defaulting to 'nothing' would silently disarm the session instead.
    """
    with pytest.raises(ProtocolError, match="tools"):
        build_pi_argv("omlx", "m", ())
