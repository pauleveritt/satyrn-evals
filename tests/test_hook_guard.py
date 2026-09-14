import pytest

from tools.hooks.guard import decide


@pytest.mark.parametrize("command", [
    "pi -p --provider zai --model glm-5.3 'review this'",
    "cd x && pi --print 'hi'",
    "uv run satyrn-evals run agentclinic-repair-misleading-locus --n 1 -- satyrn-evals-attempt-pi",
    "uv run satyrn-evals session agentclinic-complaint-lifecycle -- satyrn-evals-session-pi",
    "echo x > docs/results/2026-09-14-probe.md",
    "tee docs/reviews/a..b-zai.md < /tmp/x",
])
def test_blocked_bash_commands(command: str) -> None:
    assert decide("Bash", {"command": command}) is not None


@pytest.mark.parametrize("command", [
    "uv run python tools/review.py 8633149..9f1c2d3 zai/glm-5.3",
    "uv run satyrn-evals launch --check /tmp/rec.json",
    "uv run pytest -q",
    "git commit -m 'x'",
    "cat docs/results/2026-09-14-probe.md",
    "pip install x",
])
def test_allowed_bash_commands(command: str) -> None:
    assert decide("Bash", {"command": command}) is None


@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit"])
def test_direct_writes_to_results_and_reviews_are_blocked(tool: str) -> None:
    assert decide(tool, {"file_path": "/repo/docs/results/x.md"}) is not None
    assert decide(tool, {"file_path": "/repo/docs/reviews/x.md"}) is not None


def test_direct_writes_elsewhere_are_allowed() -> None:
    assert decide("Write", {"file_path": "/repo/docs/lessons.md"}) is None
    assert decide("Edit", {"file_path": "/repo/src/satyrn_evals/cli.py"}) is None


def test_unknown_tools_are_allowed() -> None:
    assert decide("Read", {"file_path": "/repo/docs/results/x.md"}) is None


# --- Fix round 1: finding 1 (reordered pi flags) -------------------------

@pytest.mark.parametrize("command", [
    "pi -p hi",
    "pi --print hi",
    "pi -p --provider zai",
    "pi -q -p hi",
    "pi --provider zai -p hi",
])
def test_pi_print_with_reordered_or_intervening_flags_is_blocked(command: str) -> None:
    assert decide("Bash", {"command": command}) is not None


@pytest.mark.parametrize("command", [
    "pip install x",
    "pipx -p",
    "mypi -p",
    "api -p",
])
def test_pi_lookalike_commands_are_allowed(command: str) -> None:
    assert decide("Bash", {"command": command}) is None


# --- Fix round 1: finding 2, part 1 (command-boundary anchor) ------------

def test_quoted_direct_run_token_in_commit_message_is_allowed() -> None:
    assert decide("Bash", {"command": "git commit -m 'satyrn-evals run x'"}) is None


@pytest.mark.parametrize("command", [
    "satyrn-evals run foo",
    "foo && satyrn-evals run foo",
])
def test_direct_run_at_a_command_boundary_is_still_blocked(command: str) -> None:
    assert decide("Bash", {"command": command}) is not None


# --- Fix round 1: finding 2, part 2 (writing token tied to the path) -----

@pytest.mark.parametrize("command", [
    "echo x > docs/results/a.md",
    "printf x >> docs/reviews/b.md",
])
def test_writing_that_targets_the_protected_path_is_blocked(command: str) -> None:
    assert decide("Bash", {"command": command}) is not None


@pytest.mark.parametrize("command", [
    "cat docs/results/x.md",
    "cat docs/results/x.md 2>&1",
    "head -5 docs/results/x.md > /tmp/out",
    "diff docs/results/a.md docs/results/b.md > /tmp/d",
    "grep -n foo docs/results/x.md",
    "wc -l docs/results/*.md",
])
def test_reading_or_redirecting_elsewhere_is_allowed(command: str) -> None:
    assert decide("Bash", {"command": command}) is None


# --- Fix round 1: per-rule message assertions -----------------------------

@pytest.mark.parametrize(("command", "expected_substring"), [
    ("pi -p hi", "tools/review.py"),
    ("pi --print hi", "tools/review.py"),
    ("pi -p --provider zai", "tools/review.py"),
    ("pi -q -p hi", "tools/review.py"),
    ("pi --provider zai -p hi", "tools/review.py"),
    ("satyrn-evals run foo", "satyrn-evals launch"),
    ("foo && satyrn-evals run foo", "satyrn-evals launch"),
    ("uv run satyrn-evals session agentclinic-complaint-lifecycle -- satyrn-evals-session-pi", "satyrn-evals launch"),
    ("echo x > docs/results/a.md", "docs/results and docs/reviews"),
    ("printf x >> docs/reviews/b.md", "docs/results and docs/reviews"),
    ("tee docs/reviews/a..b-zai.md < /tmp/x", "docs/results and docs/reviews"),
])
def test_blocked_command_message_identifies_the_rule(command: str, expected_substring: str) -> None:
    message = decide("Bash", {"command": command})
    assert message is not None
    assert expected_substring in message


@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit"])
def test_blocked_write_message_identifies_the_rule(tool: str) -> None:
    message = decide(tool, {"file_path": "/repo/docs/results/x.md"})
    assert message is not None
    assert "docs/results and docs/reviews" in message
