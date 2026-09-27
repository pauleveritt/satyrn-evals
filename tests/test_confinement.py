"""The confinement audit's pure core: terms, and both directions of the scan.

No model, network or subprocess. The companion replay lives in the integration
tier; here the transcript is built directly, so the scan's shape is pinned
without a process.
"""

import json
from pathlib import Path

from satyrn_evals.confinement import Protected, audit, protected

CWD = "/work"


def _transcript(*events: dict) -> str:
    lines = [{"type": "session", "cwd": CWD}, *events]
    return "\n".join(json.dumps(event) for event in lines) + "\n"


def _call(tool: str, **args: object) -> dict:
    return {"type": "tool_execution_start", "toolName": tool, "args": args}


def _tasks_root(tmp_path: Path) -> Path:
    task = tmp_path / "tasks" / "selfhost-x"
    (task / "overlay").mkdir(parents=True)
    (task / "overlay" / "test_hidden.py").write_text("x", encoding="utf-8")
    (task / "fixtures").mkdir()
    (task / "fixtures" / "known-good.patch").write_text("p", encoding="utf-8")
    return tmp_path / "tasks"


def test_protected_names_the_roots_and_the_grader_filenames(tmp_path: Path) -> None:
    terms = protected(_tasks_root(tmp_path))
    assert str((tmp_path / "tasks").resolve()) in terms.roots
    assert str((tmp_path / "tasks" / "selfhost-x").resolve()) in terms.roots
    assert terms.names == ("test_hidden.py", "known-good.patch")


def test_a_clean_cell_reaches_nothing(tmp_path: Path) -> None:
    terms = protected(_tasks_root(tmp_path))
    text = _transcript(
        _call("read", path="solution.py"),
        _call("bash", command="uv run pytest -q"),
        _call("bash", command="find / -name '*.py'"),
    )
    assert audit(text, protected_=terms) == ()


def test_a_file_tool_read_of_a_hidden_grader_is_flagged(tmp_path: Path) -> None:
    root = _tasks_root(tmp_path)
    terms = protected(root)
    hidden = root / "selfhost-x" / "overlay" / "test_hidden.py"
    text = _transcript(_call("read", path=str(hidden)))
    reached = audit(text, protected_=terms)
    assert [(r.kind, r.protected) for r in reached] == [("file_tool", "test_hidden.py")]


def test_a_file_tool_read_of_a_fixture_by_name_is_flagged(tmp_path: Path) -> None:
    terms = protected(_tasks_root(tmp_path))
    text = _transcript(_call("read", path="/elsewhere/known-good.patch"))
    reached = audit(text, protected_=terms)
    assert [(r.kind, r.protected) for r in reached] == [("file_tool", "known-good.patch")]


def test_a_bash_command_naming_a_protected_root_is_flagged(tmp_path: Path) -> None:
    root = _tasks_root(tmp_path)
    terms = protected(root)
    target = root / "selfhost-x" / "overlay" / "test_hidden.py"
    text = _transcript(_call("bash", command=f"cat {target}"))
    reached = audit(text, protected_=terms)
    assert [(r.kind, r.protected) for r in reached] == [("bash", "test_hidden.py")]


def test_a_bash_command_that_stays_in_the_worktree_is_not_flagged(tmp_path: Path) -> None:
    """The sibling of the bash refusal: a command that never names a protected
    term must not be flagged, or every cell would be."""
    terms = protected(_tasks_root(tmp_path))
    text = _transcript(_call("bash", command="grep -rn tzinfo solution.py && uv run pytest -q"))
    assert audit(text, protected_=terms) == ()


def test_an_empty_protected_set_flags_nothing(tmp_path: Path) -> None:
    """A guard against a vacuous audit: with no terms, every call is clean."""
    terms = Protected(roots=(), names=())
    text = _transcript(_call("read", path="/etc/passwd"), _call("bash", command="cat /etc/passwd"))
    assert audit(text, protected_=terms) == ()
