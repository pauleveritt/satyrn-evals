"""Check the prerequisites for running the Satyrn stack.

The stack is three things: the `satyrn-evals` harness, the `satyrn-engine`
adapter, and Pi driven by one local model backend. This module answers the
question a user hits first — "can I even run this?" — before they spend a
model budget: are git, uv, and pi on PATH, does the Python meet the pinned
floor, and is a backend (unsloth, ollama, or oMLX) available? `--check-servers`
verifies the one `SATYRN_MODEL` names. For each thing that is missing it prints
what to do. The `doctor` verb reaches this module directly.

It is a user's tool, so it is allowed to look at the machine. `shutil.which`
is a PATH lookup; the Python version probe and `--check-servers` are the only
two effects that spawn a process or open a socket. Both are injected seams
(`python_version`'s `run`, `server_reachable`'s `fetch`), so the logic and the
report are exercised by the default tier, which the spawn tripwire forbids
from spawning, and only the two thin seams touch the machine for real.

Usage::

    scripts/prereqs.py                 # tools + one backend
    scripts/prereqs.py --check-servers # also confirm the backend serves the model
    scripts/prereqs.py --backend ollama

Exit status is zero when every prerequisite is met and one when any is not, so
it composes with a build step without a pipe.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

#: The local backends, in the order the report lists them.
BACKEND_BINARIES: tuple[str, ...] = ("unsloth", "ollama", "omlx")

#: The Python floor to assume when `pyproject.toml` cannot be read.
FALLBACK_PYTHON: tuple[int, ...] = (3, 14)

#: Where each backend's server is expected, only used by `--check-servers`
#: when the Pi model config names no baseUrl for the provider.
DEFAULT_SERVER_HOSTS: dict[str, str] = {
    "unsloth": "http://localhost:8888",
    "ollama": "http://localhost:11434",
    "omlx": "http://localhost:8000",
}

#: How to fix each prerequisite when it is missing. Kept as data so the report
#: is a pure function of the check outcomes. The Python fix is built from the
#: project's own pin (`_python_fix`) rather than written here, so it cannot
#: drift from `requires-python`.
FIXES: dict[str, str] = {
    "git": "install git — https://git-scm.com/downloads",
    "uv": "install uv — https://docs.astral.sh/uv/#install",
    "pi": "install pi — https://pi.dev/docs/latest/quickstart",
    "unsloth": "install unsloth, then `unsloth start pi --persist --model ornith-ai/Ornith-1.5-9B-GGUF:Q8_0`",
    "ollama": "install ollama, then `ollama pull qwen2.5-coder:1.5b`",
    "omlx": "install oMLX (https://github.com/jundot/omlx), serve a model, then point the `omlx` provider at it",
    "model backend": "install and start one of unsloth, ollama, or omlx — see docs/user-guide.md",
}


def binary_present(name: str) -> tuple[bool, str]:
    """Whether `name` is on PATH. `shutil.which` is a PATH lookup, not a spawn."""
    path = shutil.which(name)
    if path is None:
        return False, "is not on PATH"
    return True, path


def _python_floor(spec: str) -> tuple[int, ...] | None:
    """The lower bound of a `requires-python` specifier.

    `>=3.14,<3.15` -> `(3, 14)`; `>=3.11` -> `(3, 11)`; `~=3.12.1` -> `(3, 12)`.
    None when no lower bound is present.
    """
    for clause in spec.split(","):
        clause = clause.strip()
        for prefix in (">=", "~=", "==", ">"):
            if clause.startswith(prefix):
                numbers = re.findall(r"\d+", clause)
                if numbers:
                    return tuple(int(number) for number in numbers[:2])
    return None


def required_python(pyproject: Path | None = None) -> tuple[int, ...]:
    """The Python floor this project pins, read from `requires-python`.

    Read rather than hardcoded so the check cannot drift from the pin in
    `pyproject.toml`. Falls back to `FALLBACK_PYTHON` when the file is absent
    or names no lower bound.
    """
    path = pyproject or Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return FALLBACK_PYTHON
    match = re.search(r'requires-python\s*=\s*"([^"]*)"', text)
    if match and (floor := _python_floor(match.group(1))):
        return floor
    return FALLBACK_PYTHON


def _format_version(version: tuple[int, ...]) -> str:
    """A version tuple as dotted text: `(3, 14, 4)` -> `3.14.4`."""
    return ".".join(str(part) for part in version)


def _python_fix() -> str:
    """The fix for an old Python, naming the project's own pin."""
    return (
        f"install Python {_format_version(required_python())} "
        "(or run through `uv`, which provisions it) — https://python.org/downloads"
    )


def _run_version(binary: str) -> str:
    """`binary --version` on stdout, or a note if it cannot run. Spawns."""
    try:
        completed = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"{binary}: could not run ({exc})"
    return (completed.stdout or completed.stderr or "").strip()


def _parse_python_version(output: str) -> tuple[int, ...]:
    """Parse a `python --version` line into a comparable tuple, best effort.

    Handles `Python 3.11.9`, `Python 3.11`, and odd spacing or a leading `v`.
    Anything unparseable is `(0,)`, which fails the floor.
    """
    version: list[int] = []
    tokens = output.split()
    for index, token in enumerate(tokens):
        if token.startswith("Python"):
            for part in token[len("Python"):].lstrip("v.").split("."):
                digits = "".join(ch for ch in part if ch.isdigit())
                if digits:
                    version.append(int(digits))
            for later in tokens[index + 1:]:
                for part in later.lstrip("v.").split("."):
                    digits = "".join(ch for ch in part if ch.isdigit())
                    if digits:
                        version.append(int(digits))
            break
    return tuple(version) if version else (0,)


def python_version(
    *,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[[str], str] = _run_version,
) -> tuple[bool, str]:
    """python3 meets the pinned floor. The probe is injected, not run for real."""
    if which("python3") is None:
        return False, "python3 is not on PATH"
    floor = required_python()
    version = _parse_python_version(run("python3"))
    if version < floor:
        return (
            False,
            f"python {_format_version(version)} is older than the pinned "
            f"{_format_version(floor)}; `uv` can provision it",
        )
    return True, f"python {_format_version(version)}"


def _provider_of(model: str) -> str | None:
    """The provider prefix of a `provider/model` address, or None."""
    if not model or "/" not in model:
        return None
    return model.split("/", 1)[0]


def _bare_id(model: str) -> str:
    """The id a server lists: everything after the provider prefix.

    `unsloth/ornith-ai/Ornith-1.5-9B-GGUF` becomes `ornith-ai/Ornith-1.5-9B-GGUF`;
    a bare id with no prefix is unchanged.
    """
    return model.split("/", 1)[1] if "/" in model else model


def _server_host(provider: str, models: dict) -> str:
    """The host a provider's server is expected on, from the Pi config or defaults."""
    providers = models.get("providers")
    if isinstance(providers, dict):
        block = providers.get(provider)
        if isinstance(block, dict) and block.get("baseUrl"):
            return str(block["baseUrl"]).rstrip("/")
    return DEFAULT_SERVER_HOSTS.get(provider, "http://127.0.0.1:8001")


def _provider_api_key(models: dict, provider: str) -> str | None:
    """The bearer token a provider block carries, or None.

    An OpenAI-compatible server may require one (unsloth's proxy does); the
    same key the harness's preflight sends must be sent here, or a reachable
    server answers 401 and this reads it as unreachable.
    """
    providers = models.get("providers")
    if not isinstance(providers, dict):
        return None
    block = providers.get(provider)
    if not isinstance(block, dict):
        return None
    key = block.get("apiKey")
    return key if isinstance(key, str) and key else None


def _read_pi_models() -> dict:
    """`~/.pi/agent/models.json`, or `{}` when it is absent or unreadable."""
    path = Path.home() / ".pi" / "agent" / "models.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _http_get(url: str, api_key: str | None) -> bytes:
    """One `GET url` with an optional bearer token. The only network call."""
    request = urllib.request.Request(url)
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.read()


def server_reachable(
    model: str,
    *,
    models: dict | None = None,
    fetch: Callable[[str, str | None], bytes] = _http_get,
) -> tuple[bool, str]:
    """`GET {host}/v1/models` lists the bare id of `provider/model`.

    `model` carries the provider prefix (`unsloth/ornith-ai/...`); the server
    lists the bare id (`ornith-ai/...`), so the membership test uses the bare
    one and the report names the full address. `fetch` is injected, so the
    logic is tested without a socket.
    """
    provider = _provider_of(model)
    if provider is None:
        return False, f"{model} is not a provider/model address"
    bare = _bare_id(model)
    config = _read_pi_models() if models is None else models
    host = _server_host(provider, config).removesuffix("/v1")
    url = f"{host}/v1/models"
    try:
        body = json.loads(fetch(url, _provider_api_key(config, provider)))
    except (OSError, ValueError) as exc:
        return False, f"{provider} server at {host} is unreachable: {exc}"
    ids = {entry.get("id") for entry in body.get("data", []) if isinstance(entry, dict)}
    if bare in ids:
        return True, model
    return False, f"{provider} server at {host} does not serve {bare}"


def check_backend(
    name: str,
    check_servers: bool,
    *,
    which: Callable[[str], str | None] = shutil.which,
    reach: Callable[[str], tuple[bool, str]] = server_reachable,
) -> tuple[bool, str]:
    """One named backend: on PATH, and (optionally) serving `SATYRN_MODEL`."""
    if which(name) is None:
        return False, "not on PATH"
    if not check_servers:
        return True, name
    model = os.environ.get("SATYRN_MODEL", "")
    if not model:
        return False, "SATYRN_MODEL is not set; start the backend and export it"
    return reach(model)


def check_backends(
    check_servers: bool,
    *,
    which: Callable[[str], str | None] = shutil.which,
    reach: Callable[[str], tuple[bool, str]] = server_reachable,
) -> tuple[bool, str]:
    """At least one backend on PATH; with `--check-servers`, the one `SATYRN_MODEL` names.

    Several backends can be installed at once; which one matters is named by
    `SATYRN_MODEL`'s provider, so that is what `--check-servers` verifies rather
    than refusing because more than one is present.
    """
    found = [name for name in BACKEND_BINARIES if which(name)]
    if not check_servers:
        if not found:
            return False, "no local model backend"
        return True, ", ".join(found)
    model = os.environ.get("SATYRN_MODEL", "")
    if not model:
        return False, "SATYRN_MODEL is not set; start a backend and export it"
    provider = _provider_of(model)
    if provider in BACKEND_BINARIES and provider not in found:
        return False, f"{provider} is not on PATH (present: {', '.join(found) or 'none'})"
    return reach(model)


def build_prereqs(check_servers: bool) -> list[tuple[str, str, Callable[[], tuple[bool, str]]]]:
    """The prerequisites, in report order: each is (label, fix, check)."""
    return [
        ("git", FIXES["git"], lambda: binary_present("git")),
        ("python", _python_fix(), python_version),
        ("uv", FIXES["uv"], lambda: binary_present("uv")),
        ("pi", FIXES["pi"], lambda: binary_present("pi")),
        ("model backend", FIXES["model backend"], lambda: check_backends(check_servers)),
    ]


def run_prereqs(check_servers: bool) -> list[tuple[str, tuple[bool, str], str]]:
    """Run every prerequisite, in report order. Each result is (label, (ok, detail), fix)."""
    results: list[tuple[str, tuple[bool, str], str]] = []
    for label, fix, run in build_prereqs(check_servers):
        results.append((label, run(), fix))
    return results


def summarize(results: Sequence[tuple[str, tuple[bool, str], str]]) -> tuple[int, int]:
    """How many prerequisites are missing and how many were checked.

    Each result is `(label, (ok, detail), fix)`, so the boolean is the first
    element of the second field, not the second field itself.
    """
    return sum(1 for result in results if not result[1][0]), len(results)


def render_report(results: Sequence[tuple[str, tuple[bool, str], str]]) -> str:
    """Render the prerequisite report. Pure: no process, no network."""
    missing, total = summarize(results)
    lines: list[str] = ["satyrn prerequisites:", ""]
    for label, (ok, detail), fix in results:
        if ok:
            lines.append(f"  {label:<14} OK   {detail}")
        else:
            lines.append(f"  {label:<14} MISSING {detail}")
            lines.append(f"               fix: {fix}")
    lines.append("")
    if missing == 0:
        lines.append(f"All {total} prerequisites are met.")
    else:
        lines.append(f"{missing} of {total} prerequisites are not met.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prereqs",
        description="Check the prerequisites for running the Satyrn stack.",
    )
    parser.add_argument(
        "--check-servers",
        action="store_true",
        help="also confirm the running backend serves the model (network)",
    )
    parser.add_argument(
        "--backend",
        choices=list(BACKEND_BINARIES),
        help="only check this one backend instead of requiring exactly one",
    )
    args = parser.parse_args(argv)

    if args.backend:
        detail = check_backend(args.backend, args.check_servers)
        results = [("backend", detail, FIXES[args.backend])]
    else:
        results = run_prereqs(args.check_servers)

    print(render_report(results))
    missing, _ = summarize(results)
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
