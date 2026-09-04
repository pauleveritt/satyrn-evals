"""V8 agentclinic manifests: load, hidden-oracle shape, digest contracts.

The contract is a failure digest: it may name failing test ids and
assertion messages, but never a grader-only path. The V7 validator
refuses any hidden-task contract containing an overlay name at load
(manifest.py:111-127); these tests pin both directions.
"""

import json
import shutil
from pathlib import Path

import pytest
from test_agentclinic_reconstruction import STATES

from satyrn_evals.errors import ManifestError
from satyrn_evals.manifest import load_manifest, resolve_task

FORBIDDEN = ("overlay", "test_acceptance.py", "overlay/test_acceptance.py")


@pytest.mark.parametrize("state", STATES)
def test_manifest_loads_and_is_hidden(state: str) -> None:
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    assert manifest.oracle_visibility == "hidden"
    assert manifest.grader_overlay == "overlay"
    assert len(manifest.expected_test_ids) == 13
    assert len(set(manifest.expected_test_ids)) == 13
    assert all(
        tid.startswith("test_acceptance.py::") for tid in manifest.expected_test_ids
    )
    assert manifest.source_paths == ("app.py", "models.py", "templates", "tests")


@pytest.mark.parametrize("state", STATES)
def test_contract_names_no_grader_path(state: str) -> None:
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    for name in FORBIDDEN:
        assert name not in manifest.contract, f"{state} contract names {name}"


@pytest.mark.parametrize("state", STATES)
def test_contract_names_the_recorded_failing_check(state: str) -> None:
    """The digest carries the fixture's failing test name(s) as a localization
    signal — each state's contract cites at least one real failure."""
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    assert "Repair the seeded bug" in manifest.contract
    # Every state's digest must point at a real check: the four assertion
    # states name their failing tests; the two collection-abort states name
    # the abort symptom without any file.
    if state in ("framing-2", "framing-2-edit"):
        assert "aborts at collection" in manifest.contract
    else:
        assert "failing check" in manifest.contract


def test_manifest_whose_contract_names_overlay_is_refused(tmp_path: Path) -> None:
    """End-to-end refusal at load: a hidden-task contract naming a grader-only
    path must raise ManifestError from load_manifest itself.

    The poisoned task dir is a real copy (not symlinks): the overlay path
    must resolve as a real directory so the ONLY defect is the contract, and
    the refusal comes from the contract-name check, not the overlay-symlink
    guard.
    """
    src = resolve_task("agentclinic-repair-plausible-wrong-fix")
    data = json.loads((src / "manifest.json").read_text())
    data["contract"] = "the failure is in test_acceptance.py — fix it"
    root = tmp_path / "tasks"
    target = root / data["name"]
    shutil.copytree(src, target)
    (target / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError):
        load_manifest(target)
