"""Test root.

With a src layout the project is importable because uv installs it
editable into the venv; this file marks the tests root and hosts the
spawn tripwire.

The tripwire is a CPython audit hook: any subprocess spawn during the
default (non-integration) tier raises, failing the build. The
`integration` marker opens the gate for tests that legitimately spawn
(git, the oracle).
"""

import sys

import pytest

_BLOCKED_EVENTS = {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"}
_spawn_blocked = True


def _audit_hook(event: str, args: tuple) -> None:
    if _spawn_blocked and event in _BLOCKED_EVENTS:
        raise RuntimeError(f"subprocess spawn blocked by tripwire: {event}")


sys.addaudithook(_audit_hook)


@pytest.fixture(autouse=True)
def _tripwire_gate(request: pytest.FixtureRequest) -> None:
    global _spawn_blocked
    _spawn_blocked = request.node.get_closest_marker("integration") is None
