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
