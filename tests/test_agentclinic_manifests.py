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
from test_agentclinic_reconstruction import (  # type: ignore[missing-import]  # pytest sibling resolution (tests/ on sys.path); pyrefly's src root cannot see it
    STATES,
)

from satyrn_evals.engine_contract import render_engine_contract
from satyrn_evals.errors import ManifestError
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.patch import parse_patch_paths, within_source

FORBIDDEN = ("overlay", "test_acceptance.py", "overlay/test_acceptance.py")

#: The (task, rung) pairs carrying an authored qualification record. A pair
#: joins this list when its record is derived from its own witness runs, not
#: before. tests/integration/test_agentclinic_gate.py imports this list rather
#: than repeating it, so the two tiers cannot disagree about what is qualified.
QUALIFIED: list[tuple[str, str]] = [
    ("depth-3", "R3"),
    ("misleading-locus", "R3"),
    ("misleading-locus", "R1"),
]


def qualification_path(task_dir: Path, rung: str) -> Path:
    """Where a rung's qualification record lives.

    R3 keeps the unsuffixed name it shipped with; every other rung is suffixed.
    Renaming the R3 file would be churn in committed evidence for no gain.
    """
    return task_dir / ("qualification.json" if rung == "R3" else f"qualification-{rung}.json")


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
    with pytest.raises(ManifestError, match="contract names grader-only path"):
        load_manifest(target)


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("fixture", ["known-good", "known-broken"])
def test_fixture_patch_is_in_scope_and_nonempty(state: str, fixture: str) -> None:
    """Both fixture patches must be non-empty and touch only source_paths
    files — a patch whose headers carry temp-dir components (git diff
    --no-index misuse) would fail the allowlist and void the whole attempt."""
    task_dir = resolve_task(f"agentclinic-repair-{state}")
    manifest = load_manifest(task_dir)
    patch = (task_dir / "fixtures" / f"{fixture}.patch").read_text()
    assert patch.strip(), (state, fixture)
    paths = parse_patch_paths(patch)
    assert paths, (state, fixture)
    for path in paths:
        assert within_source(path, manifest.source_paths), (state, fixture, path)


def test_all_manifests_share_identical_expected_test_ids() -> None:
    """The same-13 guarantee the qualification gate relies on: every task's
    oracle is byte-identical (spec §6 gate rows assume one oracle set)."""
    id_sets = [
        load_manifest(resolve_task(f"agentclinic-repair-{state}")).expected_test_ids
        for state in STATES
    ]
    assert all(id_sets[0] == other for other in id_sets[1:])


# --- V11a Task 8: R1 authored from this repository's own base rows ---
#
# The rows below are DERIVED, not recalled: each was produced by running the
# task's hidden overlay against that task's own base/ and reading the failing
# set from the oracle hook's record. The derivation, and the command that
# recomputes it, are in
# docs/superpowers/research/2026-09-05-v11a-r1-derivation.md.

DERIVED_FAILING_NAMES: dict[str, tuple[str, ...]] = {
    "depth-2": (
        "test_home_html_element_declares_english_language",
        "test_complaints_board_preserves_the_shared_layout",
        "test_post_complaint_redirects_to_complaints_board",
    ),
    "depth-3": (
        "test_home_html_element_declares_english_language",
        "test_complaints_board_preserves_the_shared_layout",
        "test_complaint_model_contract_is_preserved",
        "test_post_complaint_redirects_to_complaints_board",
    ),
    # The two collection-abort states collect nothing, so they have no
    # failing function names; their derived evidence is the abort message.
    "framing-2": (),
    "framing-2-edit": (),
    "misleading-locus": ("test_posted_complaint_appears_on_complaints_board",),
    "plausible-wrong-fix": ("test_post_complaint_redirects_to_complaints_board",),
}

DERIVED_ASSERTION_TEXT: dict[str, tuple[str, ...]] = {
    "depth-2": ("'NoneType' object has no attribute 'casefold'", "assert 307 == 303"),
    "depth-3": (
        "'NoneType' object has no attribute 'casefold'",
        "assert None is not None",
        "assert 307 == 303",
    ),
    "framing-2": ("ModuleNotFoundError: No module named 'models'",),
    "framing-2-edit": ("module 'models' has no attribute 'complaints'",),
    "misleading-locus": ("Codex acceptance test",),
    "plausible-wrong-fix": ("assert 307 == 303",),
}


#: Rung sets, pinned per task rather than assumed uniform. R0 was
#: authored 2026-09-06 for the four tasks whose public suite is red at
#: base; the two framing tasks are green at base, so a fair R0 would need
#: `specs/` vendored into `base/` -- reversed by V11a to keep `base/`
#: byte-identical -- and they keep the trim's set until that slice runs.
EXPECTED_RUNGS = {
    "depth-2": {"R0", "R1", "R1b", "R3"},
    "depth-3": {"R0", "R1", "R1b", "R3"},
    "misleading-locus": {"R0", "R1", "R1b", "R3"},
    "plausible-wrong-fix": {"R0", "R1", "R1b", "R3"},
    "framing-2": {"R1", "R3"},
    "framing-2-edit": {"R1", "R3"},
}


@pytest.mark.parametrize("state", STATES)
def test_manifest_ships_its_recorded_rung_set(state: str) -> None:
    """A rung appearing or vanishing unnoticed would silently change what
    a profile places, so the set is asserted per task, not discovered."""
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    assert set(manifest.contracts) == EXPECTED_RUNGS[state], state


@pytest.mark.parametrize("state", STATES)
def test_r3_is_the_default_contract_verbatim(state: str) -> None:
    """`contract` stays the default and stays equal to R3 (spec §3)."""
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    assert manifest.contracts["R3"] == manifest.contract, state


@pytest.mark.parametrize("state", STATES)
def test_every_contract_distinguishes_public_and_absent_acceptance_suites(
    state: str,
) -> None:
    """The public command is runnable; acceptance failures are not local tests."""
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    for label, text in {"default": manifest.contract, **manifest.contracts}.items():
        assert "uv run python -m pytest tests/" in text, (state, label)
        assert "acceptance suite" in text, (state, label)
        assert "not present in this workspace" in text, (state, label)


def test_framing_2_edit_contracts_do_not_falsely_blame_app_import() -> None:
    """Only the absent acceptance suite observes the legacy module attribute."""
    manifest = load_manifest(resolve_task("agentclinic-repair-framing-2-edit"))
    for label, text in {"default": manifest.contract, **manifest.contracts}.items():
        assert "models.complaints" in text, label
        assert "importing the app raises" not in text, label
        assert "repair the app's import" not in text, label


def test_plausible_wrong_fix_contracts_do_not_claim_recording_is_broken() -> None:
    manifest = load_manifest(resolve_task("agentclinic-repair-plausible-wrong-fix"))
    for label, text in {"default": manifest.contract, **manifest.contracts}.items():
        assert "complaint is recorded" not in text, label


@pytest.mark.parametrize("state", STATES)
def test_r1_names_no_source_file_and_no_grader_path(state: str) -> None:
    """What separates R1 from R3: no file name, no fix sentence.

    The file entries of source_paths are the seeded-defect locations
    (app.py, models.py); the bare directory entries are not localization.
    """
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    r1 = manifest.contracts["R1"]
    files = [entry for entry in manifest.source_paths if Path(entry).suffix]
    assert files, state  # not a vacuous check
    for entry in files:
        assert entry not in r1, (state, entry)
    for name in FORBIDDEN:
        assert name not in r1, (state, name)


@pytest.mark.parametrize("state", STATES)
def test_r1_carries_the_derived_failing_names(state: str) -> None:
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    r1 = manifest.contracts["R1"]
    for name in DERIVED_FAILING_NAMES[state]:
        assert name in r1, (state, name)


@pytest.mark.parametrize("state", STATES)
def test_r1_carries_the_derived_assertion_text(state: str) -> None:
    """The two collection-abort states have no failing names, so this row is
    the only one that can discriminate for them."""
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    r1 = manifest.contracts["R1"]
    for fragment in DERIVED_ASSERTION_TEXT[state]:
        assert fragment in r1, (state, fragment)


@pytest.mark.parametrize("state", STATES)
def test_r1_is_shorter_than_r3(state: str) -> None:
    """The two-point authoring gate the trim collapses R0->R3 to (spec §8).
    It is an authoring claim, not a measurement -- unverified until V12."""
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    assert len(manifest.contracts["R1"]) < len(manifest.contracts["R3"]), state


def _block(rendered: str, key: str) -> list[str]:
    """The `  - ` items under one top-level key, and no others.

    Collecting every `  - ` line instead would silently absorb a later
    block -- which is exactly what happened when `test_command` was added
    beneath `writable_paths`, and is the same positional-parsing defect
    `tools/lint_docs.py` records for its own column checker.
    """
    lines = rendered.splitlines()
    start = lines.index(key)
    items: list[str] = []
    for line in lines[start + 1 :]:
        if not line.startswith("  - "):
            break
        items.append(line)
    return items


@pytest.mark.parametrize("state", STATES)
def test_both_rungs_generate_an_engine_contract(state: str) -> None:
    """Every shipped rung renders; the two differ in id and task and agree
    on writable_paths."""
    task_dir = resolve_task(f"agentclinic-repair-{state}")
    manifest = load_manifest(task_dir)
    rendered = {
        rung: render_engine_contract(task_dir, manifest, rung=rung, contract_text=text)
        for rung, text in manifest.contracts.items()
    }
    r1, r3 = rendered["R1"].decode(), rendered["R3"].decode()
    assert r1 != r3, state
    assert r1.startswith(f'id: "agentclinic-repair-{state}@R1+'), state
    paths = _block(r1, "writable_paths:")
    assert paths == _block(r3, "writable_paths:")
    assert paths == [
        '  - "app.py"',
        '  - "models.py"',
        '  - "templates/*"',
        '  - "tests/*"',
    ], state


# --- Qualification records: structure only, no process ---
#
# The witness ROWS are verified by running the real suites
# (tests/integration/test_agentclinic_gate.py). These two rows are the part
# that `just gates` runs: a record whose behaviors stopped covering the oracle,
# or whose witnesses all went green, would otherwise be caught only in the
# integration tier, which the default gate run does not execute. Neither tier
# runs in GitHub CI -- .github/workflows/pages.yml builds the docs and nothing
# else -- so `just gates` is the only place either row fires.
#
# LIMIT, stated so a later reader does not over-trust the first row: it checks
# that the behaviors are EXHAUSTIVE over the oracle, not that each check is
# filed under the right behavior. A degenerate record with one catch-all
# behavior listing all 13 would pass it. A partition check would be wrong --
# depth-3 deliberately files two checks under two behaviors each -- so the
# guard against "merely exhaustive" is the per-task row in the gate, not this.


@pytest.mark.parametrize(("state", "rung"), QUALIFIED)
def test_qualification_behaviors_cover_the_whole_oracle(state: str, rung: str) -> None:
    task_dir = resolve_task(f"agentclinic-repair-{state}")
    manifest = load_manifest(task_dir)
    record = json.loads(qualification_path(task_dir, rung).read_text())

    assert record["task"] == manifest.name
    assert record["rung"] == rung
    assert rung in manifest.contracts, (state, rung)
    assert {behavior["assessment"] for behavior in record["behaviors"]} == {"justified"}
    assert {
        check for behavior in record["behaviors"] for check in behavior["hidden_checks"]
    } == set(manifest.expected_test_ids), state


@pytest.mark.parametrize(("state", "rung"), QUALIFIED)
def test_qualification_witnesses_declare_both_directions(state: str, rung: str) -> None:
    """A record whose every witness passes proves nothing, and one whose every
    witness fails cannot tell a repair from a wrong repair. Each qualified pair
    declares at least one of each, and every named patch exists."""
    task_dir = resolve_task(f"agentclinic-repair-{state}")
    record = json.loads(qualification_path(task_dir, rung).read_text())
    failing = [w for w in record["witnesses"] if w["hidden_expected_nonpassing_ids"]]
    clean = [w for w in record["witnesses"] if not w["hidden_expected_nonpassing_ids"]]

    assert failing, (state, rung)
    assert clean, (state, rung)
    for witness in record["witnesses"]:
        if witness["patch"] is not None:
            assert (task_dir / witness["patch"]).is_file(), (state, rung, witness["id"])


def test_misleading_locus_known_broken_touches_only_the_board_template() -> None:
    """The isolation argument rests on this patch's scope, so pin it.

    `base` and `known-broken` are argued to differ by exactly the template, which
    is what lets a preservation check that is silent at base and fires here be
    read as tracking the wrong repair rather than the unrepaired seam
    (qualification.json, witness `known-broken`). Widening this patch would void
    that argument while every other row stayed green, so the scope is asserted
    rather than assumed.
    """
    task_dir = resolve_task("agentclinic-repair-misleading-locus")
    patch = (task_dir / "fixtures" / "known-broken.patch").read_text()
    assert parse_patch_paths(patch) == ("templates/complaints.html",)
