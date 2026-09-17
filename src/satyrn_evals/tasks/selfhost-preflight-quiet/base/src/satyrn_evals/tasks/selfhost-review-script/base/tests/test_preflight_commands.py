"""Preflight resolves each arm's command, and refuses one PATH cannot find.

The refusal is the point -- preflight went green on 2026-09-05 while
`satyrn-engine` was absent from PATH -- so each refusal here has its
sibling success, per `BRIEF.md` rule 6.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from preflight_commands import (  # noqa: E402, I001
    resolve_arm_commands,
    unresolved,
)


def _arm(tmp_path: Path, name: str, command: str) -> Path:
    arm_path = tmp_path / f"{name}.json"
    arm_path.write_text(
        json.dumps({"arm": name, "argv": [command, "attempt"]}), encoding="utf-8"
    )
    return arm_path


@pytest.fixture
def bin_dir(tmp_path: Path) -> Path:
    """A PATH entry holding one executable named ``present-command``."""
    directory = tmp_path / "bin"
    directory.mkdir()
    executable = directory / "present-command"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    return directory


def test_arm_whose_command_is_on_path_resolves(tmp_path: Path, bin_dir: Path) -> None:
    arm_path = _arm(tmp_path, "baseline", "present-command")
    resolutions = resolve_arm_commands([arm_path], path=str(bin_dir))
    assert unresolved(resolutions) == []
    assert resolutions[0][0] == "baseline"
    assert resolutions[0][2] == str(bin_dir / "present-command")


def test_arm_whose_command_is_absent_is_refused(tmp_path: Path, bin_dir: Path) -> None:
    arm_path = _arm(tmp_path, "engine", "satyrn-engine")
    resolutions = resolve_arm_commands([arm_path], path=str(bin_dir))
    assert unresolved(resolutions) == [("engine", "satyrn-engine", None)]


def test_one_missing_arm_among_several_is_named(tmp_path: Path, bin_dir: Path) -> None:
    """The recorded shape: baseline resolved, engine did not."""
    arms = [
        _arm(tmp_path, "baseline", "present-command"),
        _arm(tmp_path, "engine", "satyrn-engine"),
    ]
    missing = unresolved(resolve_arm_commands(arms, path=str(bin_dir)))
    assert [entry[0] for entry in missing] == ["engine"]


def test_a_directory_is_not_a_resolvable_command(tmp_path: Path, bin_dir: Path) -> None:
    """A non-executable match must not read as resolved."""
    (bin_dir / "a-directory").mkdir()
    arm_path = _arm(tmp_path, "baseline", "a-directory")
    assert unresolved(resolve_arm_commands([arm_path], path=str(bin_dir)))


def test_arm_without_argv_is_an_error(tmp_path: Path) -> None:
    arm_path = tmp_path / "broken.json"
    arm_path.write_text(json.dumps({"arm": "broken", "argv": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="argv"):
        resolve_arm_commands([arm_path])
