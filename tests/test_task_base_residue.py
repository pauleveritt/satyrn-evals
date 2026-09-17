"""Guard against runtime residue in a persisted task base (findings C1, C2).

C1: an in-place ``uv sync`` / pytest run inside
``src/satyrn_evals/tasks/selfhost-preflight-quiet/base/`` during round 2 left
1,103 untracked, gitignored residue paths -- a whole ``.venv/``, a
``.pytest_cache/`` and ten ``__pycache__/`` directories. Three of them
(``base/.venv/bin/{activate,deactivate,pydoc}.bat``) have CRLF line endings
that normalise to LF on checkout, so Git materialization no longer matched
the persisted base and ``uv run satyrn-evals qualify`` refused every cell
with ``AttemptCode.WORKSPACE_FAILED`` -- a code in ``INFRASTRUCTURE_CODES``
that stops a whole census night. The controller has since removed the
residue; this test makes a recurrence a default-tier failure instead of a
night-of discovery.

C2: ``task_tree.tree_digest`` deliberately ignores ``RESIDUE_PARTS`` (a run
record pins the task's structural identity, not runtime noise), while
``workspace.snapshot_tree`` -- the Git-representable comparison the launcher
actually uses to decide whether a materialized workspace matches the
persisted base -- does not filter residue at all. That asymmetry is why a
residue-laden base can still match its pinned ``digests.task_tree``, pass
``cut_task.py check`` and show a clean ``git status`` (``base/.gitignore``
ignores the residue), yet refuse every cell. The residue guard above is the
only thing that catches it; the test below pins the asymmetry as a known,
deliberate fact so that if ``snapshot_tree`` is ever made residue-aware,
whoever does it is pointed back at this guard rather than discovering the
asymmetry closed by surprise.
"""

from pathlib import Path

from satyrn_evals.task_tree import RESIDUE_PARTS, tree_digest
from satyrn_evals.workspace import snapshot_tree

TASKS_ROOT = Path(__file__).resolve().parent.parent / "src" / "satyrn_evals" / "tasks"


def residue_paths(base: Path) -> list[Path]:
    """Every path under ``base`` with a residue path component, relative to base.

    Uses ``task_tree.RESIDUE_PARTS`` rather than a second hard-coded list, so
    the guard and the digest's own exclusion cannot drift apart.
    """
    return sorted(
        path.relative_to(base)
        for path in base.rglob("*")
        if path.is_file() and RESIDUE_PARTS.intersection(path.relative_to(base).parts)
    )


def test_every_persisted_task_base_is_free_of_residue() -> None:
    bases = sorted(TASKS_ROOT.glob("*/base"))
    assert bases, "expected at least one committed task base under src/satyrn_evals/tasks"
    dirty = {str(base.relative_to(TASKS_ROOT)): found for base in bases if (found := residue_paths(base))}
    assert dirty == {}


def test_the_residue_predicate_finds_nothing_in_a_clean_base(tmp_path: Path) -> None:
    """The success sibling of the refusal test below."""
    base = tmp_path / "base"
    base.mkdir()
    (base / "real.py").write_text("x = 1\n")
    assert residue_paths(base) == []


def test_the_residue_predicate_names_the_offending_path(tmp_path: Path) -> None:
    """The refusal sibling: build a base with residue and assert the predicate names it."""
    base = tmp_path / "base"
    (base / ".venv" / "bin").mkdir(parents=True)
    (base / ".venv" / "bin" / "activate.bat").write_text("REM\r\n")
    (base / "real.py").write_text("x = 1\n")
    assert residue_paths(base) == [Path(".venv/bin/activate.bat")]


def test_tree_digest_ignores_residue_while_snapshot_tree_does_not() -> None:
    """Pins the C2 asymmetry with the two real functions, not a description of them.

    If this assertion starts failing because ``snapshot_tree`` stopped seeing
    the residue file, that is good news for materialization but it means the
    guard test above (not this pin) is the thing that has to keep working --
    revisit this module rather than deleting it unnoticed.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="satyrn-residue-clean-") as clean_dir, tempfile.TemporaryDirectory(
        prefix="satyrn-residue-dirty-"
    ) as dirty_dir:
        clean, dirty = Path(clean_dir), Path(dirty_dir)
        (clean / "real.py").write_text("x = 1\n")
        (dirty / "real.py").write_text("x = 1\n")
        (dirty / ".venv" / "bin").mkdir(parents=True)
        (dirty / ".venv" / "bin" / "activate.bat").write_text("residue\n")

        assert tree_digest(clean) == tree_digest(dirty), "tree_digest is residue-blind by design (C2)"
        assert snapshot_tree(clean) != snapshot_tree(dirty), (
            "snapshot_tree is NOT residue-blind -- this is the C1/C2 asymmetry: "
            "a residue-laden base matches its pinned task_tree digest but not "
            "what materialization actually compares"
        )
