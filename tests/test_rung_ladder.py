"""The rung ladder is monotone in evidence, checked by authoring.

`ROADMAP.md` calls rung labels "unverified authoring claims until V12".
This is the authoring half of that: a rung that claims to give *less*
evidence must not name the hidden checks a higher rung names. It cannot
prove a rung is harder for a model — only a profile does that — but it
catches the authoring mistake of pasting a richer contract into a
sparser rung.

R0 was derived from each task's own base row, not from recall: all four
run their public suite red before the change (1 failed, 3 passed), which
is what R0's text claims. Recompute with, per task::

    cd src/satyrn_evals/tasks/agentclinic-repair-<task>/base
    uv sync && uv run python -m pytest tests/ -q
"""

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest, resolve_task

#: The tasks R0 is authored for. `framing-2` and `framing-2-edit` are
#: deliberately absent: their public suite is green at base, so a fair R0
#: would need `specs/` vendored into `base/`, which V11a reversed to keep
#: `base/` byte-identical -- changing it re-derives the contamination
#: pairs and the 24/24 gate. That is a separate slice, not authoring.
R0_TASKS = [
    "agentclinic-repair-depth-2",
    "agentclinic-repair-depth-3",
    "agentclinic-repair-misleading-locus",
    "agentclinic-repair-plausible-wrong-fix",
]


def _manifest(task: str):
    return load_manifest(resolve_task(task, tasks_root=DEFAULT_TASKS_ROOT))


def _hidden_names(manifest) -> set[str]:
    """The bare hidden check names, as R1 is allowed to carry them."""
    return {tid.split("::")[-1] for tid in manifest.expected_test_ids}


@pytest.mark.parametrize("task", R0_TASKS)
def test_r0_names_no_hidden_check(task: str) -> None:
    """R0 is the sparsest rung: it may say an unseen suite decides, but
    naming even one of its checks would make it R1."""
    manifest = _manifest(task)
    named = {n for n in _hidden_names(manifest) if n in manifest.contracts["R0"]}
    assert named == set(), f"{task}: R0 names hidden checks {sorted(named)}"


@pytest.mark.parametrize("task", R0_TASKS)
def test_r1_does_name_hidden_checks(task: str) -> None:
    """The sibling that makes the check above meaningful. If R1 named none
    either, the test would pass on a ladder with no rungs at all -- the
    'a check that cannot fail' shape this project has already paid for."""
    manifest = _manifest(task)
    named = {n for n in _hidden_names(manifest) if n in manifest.contracts["R1"]}
    assert named, f"{task}: R1 names no hidden check, so R0 < R1 is untested"


@pytest.mark.parametrize("task", R0_TASKS)
def test_r0_is_authored_for_every_task_the_profile_places(task: str) -> None:
    """A missing rung would silently shrink the profile rather than fail
    it, so the task list is asserted rather than discovered."""
    assert "R0" in _manifest(task).contracts
