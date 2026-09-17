"""The frozen census records still match the task trees they pin, and night 2's
three records carry the parameters their design fixed.

A record's ``task_tree_sha256`` is checked by the launcher at launch, which
refuses on drift; these rows catch the drift in the default tier instead, before
a night is started. The 2026-09-16 fix wave moved ``selfhost-cell-loop``'s
digest under a record frozen the day before and nothing in the gates saw it.
No model, network, or subprocess.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.qualify import CENSUS_TASKS
from satyrn_evals.task_tree import tree_digest

ROOT = Path(__file__).resolve().parent.parent
RECORDS = ROOT / "records"


def _frozen(prefix: str) -> list[Path]:
    return sorted(p for p in RECORDS.glob(f"{prefix}*.json") if not p.name.endswith(".result.json"))


NIGHT1 = _frozen("2026-09-16-census-")
NIGHT2 = _frozen("2026-09-17-census2-")
NIGHT3 = _frozen("2026-09-18-census3-")
AUTHORED_TASK = "selfhost-preflight-quiet"
AUTHORED_SPEC = "docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md"
NIGHT1_TASKS = {
    "agentclinic-repair-depth-3", "selfhost-cell-loop", "selfhost-docs-linter",
    "selfhost-run-record-gate", "selfhost-speed-probe",
}
REPLACED = {"selfhost-run-record-gate", "selfhost-cell-loop", "selfhost-speed-probe"}
REPLACEMENT_CELL_IDS = {
    "selfhost-run-record-gate": ("470484", "533788", "609675"),
    "selfhost-cell-loop": ("631530", "918779", "320931"),
    "selfhost-speed-probe": ("529092", "941646", "944467"),
}
DECISION_RULE = (
    "none for outcomes: release-two admission is decided in section 8 of "
    "2026-09-15-release-two-census-design.md from the classified table, not "
    "from a pass count"
)


def _authority_has_id_triple(authority: str, task: str, ids: tuple[str, str, str]) -> bool:
    return f"replacement for contended cells {', '.join(ids)} of 2026-09-16-census-{task};" in authority


@pytest.mark.parametrize(
    "record_path", NIGHT1 + NIGHT2 + NIGHT3, ids=[p.stem for p in NIGHT1 + NIGHT2 + NIGHT3]
)
def test_a_frozen_census_record_pins_the_current_task_tree(record_path: Path) -> None:
    record = json.loads(record_path.read_text())
    task_dir = DEFAULT_TASKS_ROOT / record["task"]
    assert record["task_tree_sha256"] == tree_digest(task_dir), (
        f"{record_path.name} pins a tree that has drifted; re-issue the record "
        "with `record new` before the night"
    )


def test_the_five_night_one_records_are_all_present() -> None:
    assert {p.stem.removeprefix("2026-09-16-census-") for p in NIGHT1} == NIGHT1_TASKS


AUTHORED = {"selfhost-preflight-quiet"}


def test_night_two_is_the_three_replacements_and_the_census_set_gains_only_the_authored_task() -> None:
    """Amendment 2026-09-17 (night-2 design section 4): record 1, the third
    candidate, was withdrawn and Task 2 deferred to a separate spec. Night 2 is
    the three replacement records only. The authored task
    (2026-09-17-release-two-authored-task-design.md) is that deferred third
    build task; it joins CENSUS_TASKS and gets its own night-3 record, and it
    must not widen night 2's record set."""
    assert set(CENSUS_TASKS) == NIGHT1_TASKS | AUTHORED
    assert {json.loads(p.read_text())["task"] for p in NIGHT2} == REPLACED


@pytest.mark.parametrize("record_path", NIGHT2, ids=[p.stem for p in NIGHT2])
def test_a_night_two_record_carries_the_designs_parameters(record_path: Path) -> None:
    """Design section 4: Baseline, admission, batch, isolated, k = 3, 48,000 / 72,
    a 4,800 s backstop, 240 minutes, chained from the night-1 speed-probe result."""
    record = json.loads(record_path.read_text())
    assert record["arm"] == "baseline"
    assert record["purpose"] == "admission"
    assert record["mode"] == "batch"
    assert record["isolation"] == "isolated"
    assert record["k"] == 3
    assert record["token_budget"] == 48_000
    assert record["turn_budget"] == 72
    assert record["command_backstop_s"] == 4_800
    assert record["max_minutes"] == 240
    assert record["command_backstop_s"] + 300 <= record["max_minutes"] * 60
    assert record["previous_result"] == "records/2026-09-16-census-selfhost-speed-probe.result.json"
    assert record["n"] == 3
    assert record["rung"] == "R1-plan"
    assert record["model"] == "omlx/Ornith-1.5-9B-MLX-8bit"
    assert record["decision_rule"] == DECISION_RULE


@pytest.mark.parametrize("task", sorted(REPLACED))
def test_a_replacement_record_says_the_originals_stand_in_their_denominator(task: str) -> None:
    """Design section 4, verbatim: the caveat travels with the record, not only the page."""
    record = json.loads((RECORDS / f"2026-09-17-census2-{task}.json").read_text())
    assert record["authority"].startswith("replacement for contended cells ")
    assert f"of 2026-09-16-census-{task};" in record["authority"]
    assert record["authority"].endswith(
        "originals stand in their denominator and this record is reported beside "
        "them, never in their place"
    )
    assert _authority_has_id_triple(record["authority"], task, REPLACEMENT_CELL_IDS[task])


@pytest.mark.parametrize("task", sorted(REPLACED))
def test_a_replacement_authority_would_reject_a_transposed_id_triple(task: str) -> None:
    """Sibling of the pinned-id check above: a transposed or wrong triple must not
    match, or the check above would be vacuous."""
    record = json.loads((RECORDS / f"2026-09-17-census2-{task}.json").read_text())
    wrong = tuple(reversed(REPLACEMENT_CELL_IDS[task]))
    assert wrong != REPLACEMENT_CELL_IDS[task]
    assert not _authority_has_id_triple(record["authority"], task, wrong)


def _authoring_spec_resolves(manifest_body: dict, root: Path) -> bool:
    """Whether an authored manifest's ``generator.authoring.spec`` names a file
    that exists in the repository (design section 5: the disclosure must point
    at something real, not a typo'd or later-deleted path)."""
    generator = manifest_body.get("generator")
    authoring = generator.get("authoring") if isinstance(generator, dict) else None
    if not isinstance(authoring, dict):
        return True
    spec = authoring.get("spec")
    return isinstance(spec, str) and (root / spec).is_file()


def test_every_authored_census_tasks_disclosed_spec_resolves_to_a_real_file() -> None:
    """Review finding 2: nothing else checks that ``authoring.spec`` names a file
    that exists; a typo'd or later-deleted design-spec path would otherwise
    qualify clean and point at nothing."""
    for task in sorted(CENSUS_TASKS):
        manifest_body = json.loads((DEFAULT_TASKS_ROOT / task / "manifest.json").read_text())
        assert _authoring_spec_resolves(manifest_body, ROOT), (
            f"{task}: generator.authoring.spec does not resolve to a file in the repository"
        )


def test_the_resolving_check_would_catch_a_missing_spec_path() -> None:
    """Sibling of the check above: it actually bites on a spec path that is absent."""
    body = {"generator": {"authoring": {
        "spec": "docs/superpowers/specs/does-not-exist-2026-09-99.md", "roles": {"heading": "Opus"}}}}
    assert not _authoring_spec_resolves(body, ROOT)


def test_night_three_is_the_one_authored_record() -> None:
    """Authored-task design section 4: one Baseline admission record for the
    third medium-build task, which is authored rather than cut."""
    assert {json.loads(p.read_text())["task"] for p in NIGHT3} == {AUTHORED_TASK}


@pytest.mark.parametrize("record_path", NIGHT3, ids=[p.stem for p in NIGHT3])
def test_a_night_three_record_carries_the_designs_parameters(record_path: Path) -> None:
    """Section 4: Baseline, admission, batch, isolated, n = 6, k = 3, 48,000 / 72,
    a 4,800 s backstop, 240 minutes, chained from the night-2 speed-probe result."""
    record = json.loads(record_path.read_text())
    assert record["arm"] == "baseline"
    assert record["purpose"] == "admission"
    assert record["mode"] == "batch"
    assert record["isolation"] == "isolated"
    assert record["n"] == 6
    assert record["k"] == 3
    assert record["token_budget"] == 48_000
    assert record["turn_budget"] == 72
    assert record["command_backstop_s"] == 4_800
    assert record["max_minutes"] == 240
    assert record["command_backstop_s"] + 300 <= record["max_minutes"] * 60
    assert record["previous_result"] == "records/2026-09-17-census2-selfhost-speed-probe.result.json"
    assert record["rung"] == "R1-plan"
    assert record["model"] == "omlx/Ornith-1.5-9B-MLX-8bit"
    assert record["decision_rule"] == DECISION_RULE


def test_the_night_three_record_names_the_authored_task_design_and_its_approval() -> None:
    """The disclosure travels with the record, not only with the page: a reader of
    the record alone learns the task was authored and under which approved spec,
    and can find the pre-registered post-hoc read for the hidden suite's disclosed
    gaps."""
    record = json.loads((RECORDS / f"2026-09-18-census3-{AUTHORED_TASK}.json").read_text())
    assert AUTHORED_SPEC in record["authority"]
    assert "approved 2026-09-17" in record["authority"]
    assert "authored not cut" in record["authority"]
    assert "evidence/2026-09-18-census-3/postreg.md" in record["authority"]


def test_the_authored_task_manifest_discloses_itself() -> None:
    """Sibling of the record check, one layer down: the task tree says the same
    thing the record says, inside the body `cut_task.py check` compares."""
    body = json.loads((DEFAULT_TASKS_ROOT / AUTHORED_TASK / "manifest.json").read_text())
    assert body["generator"]["authored"] is True
    assert body["generator"]["authoring"]["spec"] == AUTHORED_SPEC
    assert body["generator"]["authoring"]["roles"]
    assert body["validity"]["passed"] is True


def test_a_cut_census_task_carries_no_authored_disclosure() -> None:
    """The refusal's sibling: the five cut tasks must not claim to be authored,
    or the census page's authored/cut split would be meaningless."""
    for task in NIGHT1_TASKS:
        body = json.loads((DEFAULT_TASKS_ROOT / task / "manifest.json").read_text())
        assert "authored" not in (body.get("generator") or {})


# The three route-proof records (2026-09-17-release-two-engine.md, operator section;
# progress.md, "The three route-proof records: issued, checked, and deliberately NOT
# committed"). None of these exists in the tree today: the ledger explains why -- the
# second and third cannot be gated until their predecessors' results exist, and the
# first cannot be frozen ahead of the maintainer's sequencing decision against the
# authored-task dispatch's own chain tail. This is a PRE-REGISTERED guard: it names the
# frozen shape the plan fixes now, before the operator commits any of the three files,
# so the shape cannot drift between the ledger and whatever eventually lands.
ROUTE_PROOF_N = {
    "records/2026-09-17-route-proof-engine-selfhost-run-record-gate.json": 2,
    "records/2026-09-17-route-proof-engine-selfhost-docs-linter.json": 2,
    "records/2026-09-17-route-proof-engine-selfhost-cell-loop.json": 3,
}
ROUTE_PROOF_AUTHORITY = (
    "maintainer: route proof on the claim tasks, approved in "
    "2026-09-17-release-two-engine-design.md section 7 on 2026-09-17; these cells are "
    "read for behaviour only and are excluded from every comparison denominator"
)
ROUTE_PROOF_DECISION_RULE = (
    "section 7 go criterion, behaviour only, no outcome: the steer fires in 3 of 4 "
    "own-green cells and the model stops within three turns in 2 of those 3; a resume "
    "produces a tool call in 2 of 3. Below that, the design returns to the maintainer."
)


def test_a_route_proof_record_would_carry_the_designs_parameters_when_frozen() -> None:
    """PRE-REGISTRATION, not a pass: as of this commit none of the three route-proof
    records exists (ledger: "issued, checked, and deliberately NOT committed" -- the
    operator ran `record new` and `launch --preflight`/`--check` on all three, then
    removed the files, leaving the tree clean, because the chain and the sequencing
    decision are not this dispatch's to freeze). A reader must not mistake the
    `pytest.skip` below for a pass: it means the guard has nothing to check yet, not
    that the records are correct. The moment the operator commits any of the three,
    this test binds on it and checks the whole frozen shape section 7 and Ruling 11
    fix: task, rung, arm, n, k, purpose, isolation, mode, the budgets, the backstop
    arithmetic, and the two exclusion markers (authority, decision_rule)."""
    existing = [path for path in ROUTE_PROOF_N if (ROOT / path).is_file()]
    if not existing:
        pytest.skip(
            "no route-proof record is committed yet (pre-registered guard; this is "
            "not a pass -- see progress.md, 'issued, checked, and deliberately NOT "
            "committed')"
        )
    for path in existing:
        record = json.loads((ROOT / path).read_text())
        task = Path(path).stem.removeprefix("2026-09-17-route-proof-engine-")
        assert record["task"] == task
        assert record["rung"] == "R1-plan"
        assert record["arm"] == "engine"
        assert record["n"] == ROUTE_PROOF_N[path]
        assert record["k"] == 3
        assert record["purpose"] == "route-proof"
        assert record["isolation"] == "isolated"
        assert record["mode"] == "batch"
        assert record["max_minutes"] == 120
        assert record["command_backstop_s"] == 4_800
        assert record["command_backstop_s"] + 300 <= record["max_minutes"] * 60
        assert record["token_budget"] == 48_000
        assert record["turn_budget"] == 72
        assert "2026-09-17-release-two-engine-design.md" in record["authority"]
        assert "approved" in record["authority"] and "2026-09-17" in record["authority"]
        assert "excluded from every comparison denominator" in record["authority"]
        assert record["authority"] == ROUTE_PROOF_AUTHORITY
        assert "section 7" in record["decision_rule"] or "§7" in record["decision_rule"]
        assert "behaviour only" in record["decision_rule"] and "no outcome" in record["decision_rule"]
        assert record["decision_rule"] == ROUTE_PROOF_DECISION_RULE


def test_no_route_proof_record_exists_outside_the_three_named_paths() -> None:
    """NOT conditional -- this is the half of the guard that is live today, and the
    reason the guard above is not vacuous in the meantime: a fourth record, a
    misnamed one, or a stray `route-proof` file is caught the moment it lands, before
    any of the three expected records exists."""
    found = {f"records/{p.name}" for p in RECORDS.glob("2026-09-17-route-proof-engine-*.json")}
    assert found <= set(ROUTE_PROOF_N)
