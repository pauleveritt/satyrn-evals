"""The Engine arm's checkout against its pins: HEAD, then the pinned bytes.

Integration tier: it makes a real Git repository and runs ``git``. The pure
resolution and the missing-tree refusal live in ``tests/test_cell_engine.py``.
"""

import hashlib
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from satyrn_evals.arms import ENGINE_SOURCES, Arm, load_arm
from satyrn_evals.cell_engine import engine_checkout_problems

pytestmark = pytest.mark.integration

ARMS = Path(__file__).resolve().parents[2] / "arms"
ENGINE_ARM = ARMS / "engine-ornith15-9b.json"


def _checkout(tmp_path: Path, *, runner: str = "// runner\n") -> tuple[Path, str, dict[str, str]]:
    root = tmp_path / "engine"
    (root / "packages" / "engine").mkdir(parents=True)
    texts = {name: f"// {name}\n" for name in ENGINE_SOURCES}
    texts["runner.ts"] = runner
    for name, text in texts.items():
        (root / "packages" / "engine" / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "-m", "engine"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    digests = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in texts.items()}
    return root, head, digests


def _arm(root: Path, commit: str, digests: dict[str, str]) -> Arm:
    committed = load_arm(ENGINE_ARM)
    return replace(
        committed,
        argv=("satyrn-evals-attempt-engine", "--engine-repo", str(root)),
        pins=replace(committed.pins, engine_commit=commit, digests=digests),
    )


def test_a_checkout_at_the_pin_with_the_pinned_bytes_has_no_problems(tmp_path: Path) -> None:
    root, head, digests = _checkout(tmp_path)
    assert engine_checkout_problems(_arm(root, head, digests), {}) == []


def test_a_checkout_at_another_commit_is_refused_and_names_both(tmp_path: Path) -> None:
    root, head, digests = _checkout(tmp_path)
    other = "a" * 40
    [problem] = engine_checkout_problems(_arm(root, other, digests), {})
    assert head in problem and other in problem
    assert "run `just fetch-engine`" in problem


def test_a_checkout_with_a_pinned_file_changed_or_missing_is_refused(tmp_path: Path) -> None:
    root, head, digests = _checkout(tmp_path)
    (root / "packages" / "engine" / "scope.ts").write_text("// edited\n", encoding="utf-8")
    (root / "packages" / "engine" / "paths.ts").unlink()
    assert engine_checkout_problems(_arm(root, head, digests), {}) == [
        f"the engine checkout {root} has no packages/engine/paths.ts",
        f"the engine checkout {root} has packages/engine/scope.ts other than the pinned bytes",
    ]
