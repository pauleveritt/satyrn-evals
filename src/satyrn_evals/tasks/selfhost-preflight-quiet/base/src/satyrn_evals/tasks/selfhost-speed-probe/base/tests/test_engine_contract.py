"""The generated Engine contract (V11a spec §6).

Today's ``engine-contract.yaml`` is hand-authored and shipped for two tasks
only; the six AgentClinic tasks have none, and the V8 smoke used a file that
differed from the manifest by a token. Generating the contract from the
manifest plus the selected rung makes the text the model sees the text on
record.

The ``writable_paths`` rows discriminate in both directions (BRIEF rule 8):
each pattern is shown to admit every declared source file of the named
fixture and to reject a neighbouring path outside it.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from satyrn_evals.engine_contract import (
    contract_id,
    render_engine_contract,
)
from satyrn_evals.manifest import TaskManifest


def _manifest(source_paths: tuple[str, ...]) -> TaskManifest:
    return TaskManifest(
        name="t",
        contract="Fix it.",
        oracle=("python", "-m", "pytest"),
        expected_test_ids=("test_solution.py::test_one",),
        source_paths=source_paths,
        fixtures={"known_good": "fixtures/known-good.patch"},
    )


def test_empty_source_paths_produces_no_contract(tmp_path: Path) -> None:
    """A contract with nothing writable cannot be delivered against."""
    with pytest.raises(ValueError, match="source_paths"):
        render_engine_contract(tmp_path, _manifest(()), rung="R1", contract_text="text")


def _render(tmp_path: Path, *, rung: str | None, text: str) -> bytes:
    (tmp_path / "base").mkdir(exist_ok=True)
    (tmp_path / "base" / "app.py").write_text("x = 1\n")
    (tmp_path / "base" / "templates").mkdir(exist_ok=True)
    (tmp_path / "base" / "templates" / "base.html").write_text("<p>\n")
    return render_engine_contract(
        tmp_path,
        _manifest(("app.py", "templates")),
        rung=rung,
        contract_text=text,
    )


# The pinned prefixes below are the first 12 hex of the SHA-256 of each text.
# Recompute with:
#   python3 -c 'import hashlib;print(hashlib.sha256(TEXT.encode()).hexdigest()[:12])'
R1_TEXT = "test_one fails: assert 307 == 303"
R3_TEXT = 'The seeded defect is in app.py; make the redirect a "303".'


def test_rendered_bytes_are_pinned_at_r1(tmp_path: Path) -> None:
    assert _render(tmp_path, rung="R1", text=R1_TEXT) == (
        b'id: "t@R1+cf4c6872834b"\n'
        b'task: "test_one fails: assert 307 == 303"\n'
        b"writable_paths:\n"
        b'  - "app.py"\n'
        b'  - "templates/*"\n'
    )


def test_rendered_bytes_are_pinned_at_r3(tmp_path: Path) -> None:
    assert _render(tmp_path, rung="R3", text=R3_TEXT) == (
        b'id: "t@R3+c04aa48663f6"\n'
        b'task: "The seeded defect is in app.py; make the redirect a '
        b'\\"303\\"."\n'
        b"writable_paths:\n"
        b'  - "app.py"\n'
        b'  - "templates/*"\n'
    )


def test_the_two_rungs_differ_only_in_id_and_task(tmp_path: Path) -> None:
    r1 = _render(tmp_path, rung="R1", text=R1_TEXT).decode().splitlines()
    r3 = _render(tmp_path, rung="R3", text=R3_TEXT).decode().splitlines()
    assert [line for line in r1 if line.startswith("  - ")] == [
        line for line in r3 if line.startswith("  - ")
    ]
    assert r1[0] != r3[0] and r1[1] != r3[1]


def test_rendered_mapping_carries_both_id_and_task(tmp_path: Path) -> None:
    """Engine requires `id` as well as `task` (proposal correction 14)."""
    lines = _render(tmp_path, rung="R1", text=R1_TEXT).decode().splitlines()
    keys = [line.split(":", 1)[0] for line in lines if not line.startswith(" ")]
    assert keys == ["id", "task", "writable_paths"]
    assert json.loads(lines[1].split(": ", 1)[1]) == R1_TEXT


def test_id_is_stable_for_the_same_task_rung_and_digest() -> None:
    digest = "a" * 64
    assert contract_id("t", "R1", digest) == contract_id("t", "R1", digest)


def test_id_changes_when_the_rung_text_changes() -> None:
    assert contract_id("t", "R1", "a" * 64) != contract_id("t", "R1", "b" * 64)


def test_id_of_the_default_contract_names_no_rung() -> None:
    """Sibling success: no --rung still yields a non-empty, stable id."""
    identifier = contract_id("t", None, "a" * 64)
    assert identifier.startswith("t@contract+")
    assert identifier == contract_id("t", None, "a" * 64)


def test_a_contract_omits_test_command_when_no_public_suite_is_declared(
    tmp_path: Path,
) -> None:
    """The default, and the sibling for the emission test below: a task that
    has not opted in must render exactly what it rendered before
    satyrn-engine E7, so its Engine arm gains no tool surface silently."""
    rendered = render_engine_contract(
        tmp_path, _manifest(("solution.py",)), rung="R1", contract_text="Fix it."
    ).decode("utf-8")

    assert "test_command" not in rendered


def test_a_declared_public_suite_is_emitted_as_test_command(tmp_path: Path) -> None:
    """Fixture: a manifest declaring `public_suite`. The Engine registers its
    `run_tests` tool only when this key is present."""
    declared = replace(
        _manifest(("solution.py",)), public_suite=("uv", "run", "pytest", "tests/")
    )

    rendered = render_engine_contract(
        tmp_path, declared, rung="R1", contract_text="Fix it."
    ).decode("utf-8")

    assert "test_command:" in rendered
    for token in ("uv", "run", "pytest", "tests/"):
        assert f'  - "{token}"' in rendered
