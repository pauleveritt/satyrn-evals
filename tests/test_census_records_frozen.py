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

#: Every recorded revision of a census task's tree since its census record was
#: frozen, oldest first: ``chain[0]`` is the digest the frozen census records
#: pin, each later entry is a recorded revision, and the last is the tree as
#: committed now. A frozen record is never re-issued to follow its task; the
#: revision is recorded here, with its reason, instead.
#:
#: 2026-09-25: the five self-hosted bases gained the two host-independence
#: fixes their public suites needed on Linux (`src/satyrn_evals/tasks/`
#: KNOWN_DEFECTS.md).
#:
#: 2026-09-27: `a194500` changed the bases but left every committed
#: `manifest.digests.task_tree` stale, so `cut_task check` could not pass. The
#: manifests were regenerated with the recorded `base_edits` that reproduce the
#: bases byte for byte; the manifest is inside `tree_digest(task_dir)`, so the
#: recorded revised digest moved even though no model-facing byte changed. The
#: census records still pin the pre-2026-09-25 digest, unchanged.
TASK_TREE_REVISIONS: dict[str, tuple[str, ...]] = {
    "selfhost-cell-loop": (
        "406487a854b78b38b615d23de3c20f18eed39b04610ce3e905ff997e542f3173",
        "65ea33d4b34f2b27e6271e6af9bc78a8da5af7348ede832171f40453f2e0b74b",
    ),
    "selfhost-docs-linter": (
        "a8c1aaf0e2d5136be35ed6e5d2bf49cb88e06e15c7217ed0b481edfbd090b1c6",
        "3e3f7adf7cd962ba04a0948e4bf60f1f9056fc8fb96b9b45a11e780e2da7333e",
    ),
    "selfhost-run-record-gate": (
        "a7c74e5449d5a82e155f9e0161b793697ac9c973323818fe335297faf114ebcc",
        "068f216e08ef0abee4d3f2b1042ed38d68aaac5a638004c06a1052e03f52be05",
    ),
    "selfhost-speed-probe": (
        "dbb752affe8df090fa8594e8f046383c3ac57e6657fbb7c6181f31331270df28",
        "be6946cd336d318a1e5d3d2e04a6be6ab0fdbfa4be9f145841fdc52145cc26cd",
    ),
    "selfhost-preflight-quiet": (
        "1edcf796591ec22e9c19187744d43706f840e4fdc05dbe790f925c06cac86aa0",
        "0567373a69595a8c642b8332df407f83feedb06c4aefc706c2269bba122a5e25",
    ),
}


def revision_problem(task: str, pinned: str, current: str, chain: tuple[str, ...] | None) -> str | None:
    """Why a frozen census record no longer matches its task's tree, or None.

    With no recorded revisions the record must pin the tree as it is. With a
    chain, the tree must be the chain's last entry and the record must pin its
    first, so an unrecorded drift fails and so does a record that was quietly
    re-issued.
    """
    if chain is None:
        if pinned == current:
            return None
        return f"{task}: the record pins {pinned}, the tree is {current}; re-issue the record with `record new` before a night"
    if current != chain[-1]:
        return f"{task} is {current}, not its last recorded revision {chain[-1]}; record the revision in TASK_TREE_REVISIONS"
    if pinned != chain[0]:
        return f"{task}: the record pins {pinned}, not {chain[0]}, the digest its revisions are recorded against"
    return None


def _authority_has_id_triple(authority: str, task: str, ids: tuple[str, str, str]) -> bool:
    return f"replacement for contended cells {', '.join(ids)} of 2026-09-16-census-{task};" in authority


@pytest.mark.parametrize(
    "record_path", NIGHT1 + NIGHT2 + NIGHT3, ids=[p.stem for p in NIGHT1 + NIGHT2 + NIGHT3]
)
def test_a_frozen_census_record_pins_the_current_task_tree(record_path: Path) -> None:
    record = json.loads(record_path.read_text())
    task = record["task"]
    current = tree_digest(DEFAULT_TASKS_ROOT / task)
    assert revision_problem(task, record["task_tree_sha256"], current, TASK_TREE_REVISIONS.get(task)) is None


def test_the_five_night_one_records_are_all_present() -> None:
    assert {p.stem.removeprefix("2026-09-16-census-") for p in NIGHT1} == NIGHT1_TASKS


def test_the_revision_map_is_real_and_traceable() -> None:
    """Each chain records at least one revision, never repeats a digest, and
    starts at exactly what a frozen census record pins -- so the relaxation
    cannot hide a drift it was not recorded against."""
    census = {json.loads(p.read_text())["task"]: json.loads(p.read_text())["task_tree_sha256"] for p in NIGHT1 + NIGHT2 + NIGHT3}
    for task, chain in TASK_TREE_REVISIONS.items():
        assert len(chain) >= 2, task
        assert len(set(chain)) == len(chain), task
        assert census[task] == chain[0], task


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


# The route-proof records. Two nights: the void 2026-09-18 night (records dated
# 2026-09-17) and the second proof (records dated 2026-09-19, engine 2cccef1).
# The void night is excluded from every denominator and reported beside the
# second; the second is excluded the same way. The shape was fixed before any
# file landed, so it cannot drift between the ledger and what shipped. Each
# launched record leaves a `.result.json` beside it; the exclusion test drops
# that companion and the result test pins it to one of the records.
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
ROUTE_PROOF_2_N = {
    "records/2026-09-19-route-proof-engine-selfhost-run-record-gate.json": 2,
    "records/2026-09-19-route-proof-engine-selfhost-docs-linter.json": 2,
    "records/2026-09-19-route-proof-engine-selfhost-cell-loop.json": 3,
}
ROUTE_PROOF_2_AUTHORITY = (
    "maintainer: the second route proof, engine 2cccef1, on the claim tasks, approved "
    "2026-09-18; these cells are read for behaviour only and are excluded from every "
    "comparison denominator, and are reported beside the void 2026-09-18 night"
)
ROUTE_PROOF_NIGHTS: dict[str, dict[str, int]] = {
    "2026-09-17": ROUTE_PROOF_N,
    "2026-09-19": ROUTE_PROOF_2_N,
}
ROUTE_PROOF_AUTHORITIES = {
    "2026-09-17": ROUTE_PROOF_AUTHORITY,
    "2026-09-19": ROUTE_PROOF_2_AUTHORITY,
}
ROUTE_PROOF_DECISION_RULE = (
    "section 7 go criterion, behaviour only, no outcome: the steer fires in 3 of 4 "
    "own-green cells and the model stops within three turns in 2 of those 3; a resume "
    "produces a tool call in 2 of 3. Below that, the design returns to the maintainer."
)
_ALL_ROUTE_PROOF_RECORDS = {
    path for expected in ROUTE_PROOF_NIGHTS.values() for path in expected
}


def test_a_route_proof_record_would_carry_the_designs_parameters_when_frozen() -> None:
    """Both nights' records bind on the same frozen shape: task, rung, arm, n, k,
    purpose, isolation, mode, the budgets, the backstop arithmetic, and the two
    exclusion markers (authority, decision_rule). The authority differs per night
    and is pinned exactly. This is not vacuous while a night has no record: the
    exclusion test below is unconditional."""
    existing = {
        date: [path for path in expected if (ROOT / path).is_file()]
        for date, expected in ROUTE_PROOF_NIGHTS.items()
    }
    if not any(existing.values()):
        pytest.skip("no route-proof record is committed yet (pre-registered guard; this is not a pass)")
    for date, paths in existing.items():
        for path in paths:
            record = json.loads((ROOT / path).read_text())
            task = Path(path).stem.removeprefix(f"{date}-route-proof-engine-")
            assert record["task"] == task
            assert record["rung"] == "R1-plan"
            assert record["arm"] == "engine"
            assert record["n"] == ROUTE_PROOF_NIGHTS[date][path]
            assert record["k"] == 3
            assert record["purpose"] == "route-proof"
            assert record["isolation"] == "isolated"
            assert record["mode"] == "batch"
            assert record["max_minutes"] == 120
            assert record["command_backstop_s"] == 4_800
            assert record["command_backstop_s"] + 300 <= record["max_minutes"] * 60
            assert record["token_budget"] == 48_000
            assert record["turn_budget"] == 72
            assert record["authority"] == ROUTE_PROOF_AUTHORITIES[date]
            assert "excluded from every comparison denominator" in record["authority"]
            assert "section 7" in record["decision_rule"] or "§7" in record["decision_rule"]
            assert "behaviour only" in record["decision_rule"] and "no outcome" in record["decision_rule"]
            assert record["decision_rule"] == ROUTE_PROOF_DECISION_RULE


def test_no_route_proof_record_exists_outside_the_named_paths() -> None:
    """NOT conditional -- a fourth record, a misnamed one, or a stray `route-proof`
    file is caught the moment it lands, on either night.

    A launched record leaves its `.result.json` beside it; that companion is a
    result, not a fourth record, so it is excluded here and pinned by its own
    sibling below."""
    found = {
        f"records/{p.name}"
        for date in ROUTE_PROOF_NIGHTS
        for p in RECORDS.glob(f"{date}-route-proof-engine-*.json")
        if not p.name.endswith(".result.json")
    }
    assert found <= _ALL_ROUTE_PROOF_RECORDS


def test_every_route_proof_result_belongs_to_one_of_the_named_records() -> None:
    """The sibling of the exclusion above: a result file is not silently ignored --
    it must be the result of one of the pre-registered records, on either night, so a
    stray or misnamed result is still caught."""
    for date in ROUTE_PROOF_NIGHTS:
        for result in RECORDS.glob(f"{date}-route-proof-engine-*.result.json"):
            record = result.with_name(result.name.removesuffix(".result.json") + ".json")
            assert f"records/{record.name}" in _ALL_ROUTE_PROOF_RECORDS


A, B, C = "a" * 64, "b" * 64, "c" * 64


def test_an_unrevised_task_that_matches_its_record_has_no_problem() -> None:
    assert revision_problem("t", A, A, None) is None


def test_an_unrevised_task_that_drifted_is_named() -> None:
    assert revision_problem("t", A, B, None) == (
        f"t: the record pins {A}, the tree is {B}; re-issue the record with `record new` before a night"
    )


def test_a_tree_at_its_last_recorded_revision_has_no_problem() -> None:
    assert revision_problem("t", A, C, (A, B, C)) is None


def test_a_tree_that_moved_past_its_last_recorded_revision_is_named() -> None:
    assert revision_problem("t", A, B, (A, B, C)) == (
        f"t is {B}, not its last recorded revision {C}; record the revision in TASK_TREE_REVISIONS"
    )


def test_a_record_that_does_not_pin_the_chains_first_digest_is_named() -> None:
    assert revision_problem("t", B, C, (A, B, C)) == (
        f"t: the record pins {B}, not {A}, the digest its revisions are recorded against"
    )
