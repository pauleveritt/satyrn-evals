"""Pins the validity README's strict vs. loose leak-tell computation (finding I1).

`evidence/2026-09-17-census-2/validity/README.md` says the named leak tells
were checked over each run's `solution.diff` and `REPORT.md` and were clean
on both runs. The procedure's own tell (Ruling 5) is a full expected test id
-- ``test_preflight_quiet.py::test_name`` -- appearing verbatim; in that
strict form both runs are clean. A looser reading, the bare test *function*
name without the ``::`` prefix, is not the procedure's tell but is what a
reader who skims the id list might apply, and under that reading
``run-1/solution.diff`` has exactly one hit
(``test_decode_rate_is_none_with_fewer_than_last_completions``) --
convergent naming, not a leak (the solver could not read the overlay and the
strict tell is clean).

This test computes both forms over every committed validity run directory
and pins today's known result, plus a sibling test proving each detector
bites on a synthetic diff that really does contain an id. If a future run
changes the pinned outcome, this test fails and a human has to look, rather
than the README's prose quietly going stale.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
TASKS = ROOT / "src" / "satyrn_evals" / "tasks"


def expected_test_ids(task_name: str) -> list[str]:
    manifest = json.loads((TASKS / task_name / "manifest.json").read_text(encoding="utf-8"))
    return list(manifest["expected_test_ids"])


def strict_hits(text: str, ids: list[str]) -> list[str]:
    """The procedure's own tell: a full ``module.py::test_name`` id, present verbatim."""
    return [test_id for test_id in ids if test_id in text]


def loose_hits(text: str, ids: list[str]) -> list[str]:
    """A looser reading some readers might apply: the bare function name, sans ``::``."""
    names = [test_id.split("::", 1)[1] for test_id in ids]
    return [name for name in names if name in text]


def _run_dirs() -> list[Path]:
    return sorted(path for path in EVIDENCE.glob("**/validity/*/run-*") if path.is_dir())


def test_every_committed_validity_run_directory_is_discovered() -> None:
    """A change here (a run added, renamed or removed) should be a visible
    diff to this test, not something the pinned result below silently stops
    covering."""
    names = [str(path.relative_to(EVIDENCE)) for path in _run_dirs()]
    assert names == [
        "2026-09-17-census-2/validity/selfhost-preflight-quiet/run-1",
        "2026-09-17-census-2/validity/selfhost-preflight-quiet/run-2",
    ]


def test_strict_form_is_clean_on_every_run_and_loose_form_has_one_convergent_hit() -> None:
    ids = expected_test_ids("selfhost-preflight-quiet")
    results: dict[str, tuple[list[str], list[str]]] = {}
    for run_dir in _run_dirs():
        for filename in ("solution.diff", "REPORT.md"):
            text = (run_dir / filename).read_text(encoding="utf-8")
            results[f"{run_dir.name}/{filename}"] = (strict_hits(text, ids), loose_hits(text, ids))

    assert all(strict == [] for strict, _ in results.values()), {
        key: strict for key, (strict, _) in results.items() if strict
    }

    loose = {key: hits for key, (_, hits) in results.items()}
    assert loose == {
        "run-1/solution.diff": ["test_decode_rate_is_none_with_fewer_than_last_completions"],
        "run-1/REPORT.md": [],
        "run-2/solution.diff": [],
        "run-2/REPORT.md": [],
    }


def test_the_detector_bites_on_a_synthetic_diff_that_really_contains_an_id() -> None:
    """The sibling: both forms must actually detect a real hit, not just
    stay quiet on the clean fixtures above."""
    ids = ["test_x.py::test_something_specific"]
    diff = "--- a/x\n+++ b/x\n+# see test_x.py::test_something_specific\n"
    assert strict_hits(diff, ids) == ["test_x.py::test_something_specific"]
    assert loose_hits(diff, ids) == ["test_something_specific"]
