"""Materialized-env grading: the V8 environment story, end to end.

A dependency-bearing task (base carries pyproject.toml + uv.lock) is graded
inside its OWN locked, materialized project environment, and the receipt
attests the executed distributions as ``resolved_versions`` from the freeze
of that env — never from a lock parse. Stdlib tasks keep the ambient
interpreter and no ``resolved_versions`` key (covered by the pre-existing
grade/bundled integration tests). Integration tier: uv + network on first
sync; the planted no-subprocess tripwire forbids this outside integration.
"""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from satyrn_evals.manifest import resolve_task

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def bundled_task_dir() -> Path:
    return resolve_task("agentclinic-repair-plausible-wrong-fix")


def _cli() -> str:
    """The installed console script, resolved beside the running interpreter."""
    return os.fspath(Path(sys.executable).parent / "satyrn-evals")


def _grade(task_dir: Path, patch: str, tmp_path: Path) -> dict:
    patch_path = tmp_path / "p.patch"
    patch_path.write_text(patch)
    receipt_path = tmp_path / "receipt.json"
    subprocess.run(  # real CLI keeps env semantics identical to attempt
        [_cli(), "grade", task_dir.name, str(patch_path),
         "--receipt", str(receipt_path), "--tasks-root", str(task_dir.parent)],
        check=True, capture_output=True)
    return json.loads(receipt_path.read_text())


def test_materialized_grade_attests_resolved_versions(
    bundled_task_dir: Path, tmp_path: Path
) -> None:
    known_good = (bundled_task_dir / "fixtures" / "known-good.patch").read_text()
    receipt = _grade(bundled_task_dir, known_good, tmp_path)
    assert receipt["verdict"] == "pass"
    versions = receipt.get("resolved_versions")
    assert versions is not None, "dependency-bearing grade must attest versions"
    assert versions.get("fastapi") == "0.115.10"
    assert "pytest" in versions  # the locked dev group was materialized


def test_missing_uv_yields_unavailable_not_ambient_pass(
    bundled_task_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Materialization failure surfaces as unavailable, never an ambient run.

    The test calls ``grade()`` in-process with a PATH that keeps git but
    cannot resolve uv — grade's child env lacks uv while the test process
    (and the git it spawns first) still work. Replacing PATH around a CLI
    subprocess would prevent launching the CLI itself.
    """
    from satyrn_evals.grade import grade

    patch_path = tmp_path / "p.patch"
    patch_path.write_text(
        (bundled_task_dir / "fixtures" / "known-good.patch").read_text())
    nobin = tmp_path / "nobin"
    nobin.mkdir()
    git_bin = Path(shutil.which("git")).parent if shutil.which("git") else Path("/usr/bin")
    monkeypatch.setenv("PATH", os.fspath(nobin) + os.pathsep + os.fspath(git_bin))
    receipt_path = tmp_path / "receipt.json"
    receipt = grade(bundled_task_dir, patch_path, receipt_path)
    assert receipt.verdict.value == "unavailable"
    assert "cannot materialize task environment" in receipt.reason


def test_freeze_failure_is_unavailable_not_a_silent_drop(
    bundled_task_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing uv pip freeze after a successful sync surfaces as unavailable
    with a reason, never escapes without a receipt."""
    import subprocess as _subprocess

    from satyrn_evals import grade as grade_mod
    from satyrn_evals.grade import grade

    real_run = _subprocess.run

    def failing_freeze(
        args: str | Sequence[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        argv = list(args) if isinstance(args, (list, tuple)) else [str(args)]
        if argv[:1] == ["uv"] and any("freeze" in a for a in argv):
            raise _subprocess.CalledProcessError(3, args)
        return real_run(args, **kwargs)

    monkeypatch.setattr(grade_mod.subprocess, "run", failing_freeze)
    patch_path = tmp_path / "p.patch"
    patch_path.write_text(
        (bundled_task_dir / "fixtures" / "known-good.patch").read_text())
    receipt_path = tmp_path / "receipt.json"
    receipt = grade(bundled_task_dir, patch_path, receipt_path)
    assert receipt.verdict.value == "unavailable"
    assert "cannot attest task environment" in receipt.reason
