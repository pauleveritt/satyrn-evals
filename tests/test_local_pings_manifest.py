"""Default tier: the captured local-pings task's manifest shape.

V5c's deliverable is a captured task whose manifest asserts the five-id
oracle the re-recorded qualification gate measured (V5c spec amendment,
2026-09-02): three upstream local-ping tests plus the two curator
preservation parametrizations [order0]/[order1]. This test reads only files;
it spawns nothing (the audit-hook tripwire forbids it).
"""

from pathlib import Path

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest

EXPECTED_IDS = (
    "tests/test_container.py::TestServicePing::test_local_pings_are_retrieved",
    "tests/test_container.py::TestServicePing::test_local_pings_override_global_pings",
    "tests/test_container.py::TestServicePing::test_local_services_without_pings_discard_global_pings",
    "tests/test_eval_preservation.py::test_local_ping_keeps_registry_ping_order[order0]",
    "tests/test_eval_preservation.py::test_local_ping_keeps_registry_ping_order[order1]",
)


def _task() -> Path:
    return DEFAULT_TASKS_ROOT / "local-pings"


def test_local_pings_manifest_lists_the_five_oracle_ids() -> None:
    manifest = load_manifest(_task())
    assert manifest.expected_test_ids == EXPECTED_IDS


def test_local_pings_manifest_shape_matches_format_number() -> None:
    """Known-good and known-broken fixtures, engine contract, source path."""
    manifest = load_manifest(_task())
    assert manifest.fixtures["known_good"] == "fixtures/known-good.patch"
    assert manifest.fixtures["known_broken"] == "fixtures/known-broken.patch"
    assert manifest.engine_contract == "engine-contract.yaml"
    assert manifest.source_paths == ("src/svcs/_core.py",)


def test_local_pings_canary_test_is_not_an_oracle_id() -> None:
    """The gate's canary guards qualification; it is not part of grading."""
    manifest = load_manifest(_task())
    canary = "tests/test_eval_preservation.py::test_environment_scrambles_registry_type_set"
    assert canary not in manifest.expected_test_ids
    # ...but the base tree still carries it, so a future qualification run in
    # the same process can consult it.
    base = _task() / "base"
    assert (base / "tests" / "test_eval_preservation.py").exists()
    assert canary.split("::")[1] in (
        base / "tests" / "test_eval_preservation.py"
    ).read_text()
