import subprocess
import sys

import pytest


def test_planted_spawn_attempt_is_blocked() -> None:
    with pytest.raises(RuntimeError, match="spawn blocked"):
        subprocess.run([sys.executable, "-c", "pass"])


@pytest.mark.integration
def test_integration_tier_may_spawn() -> None:
    result = subprocess.run([sys.executable, "-c", "pass"], capture_output=True)
    assert result.returncode == 0
