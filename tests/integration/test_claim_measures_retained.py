"""The retained attempts, re-measured by the claim-level classifiers.

Integration because the artifacts live under ``~/satyrn-smokes`` and are not
committed. No model and no subprocess; a missing runs root or a missing
artifact is a loud skip naming the absent path, never a silent pass over an
empty event list.
"""

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from reconcile_claims import (  # noqa: E402  # scripts/ added via sys.path above
    ATTEMPTS,
    AttemptSpec,
    _phase4_reaching_engine_attempts,
)

from satyrn_evals.claim_measures import (  # noqa: E402
    destructive_edit,
    restoration,
    self_test_outcome,
    verification_claim,
)

pytestmark = pytest.mark.integration

RUNS_ROOT = Path(os.path.expanduser("~/satyrn-smokes"))

#: `self_test_outcome` cross-checks `chain.json`, which only the Engine arm
#: retains; Baseline has no chain record by design.
ENGINE_ATTEMPTS = tuple(spec for spec in ATTEMPTS if spec.arm == "engine")

#: The screen attempt whose final summary reports "2 passed" over the
#: `exit code 1` its own last retained `run_self_test` returned.
FALSIFIED_VERIFICATION = "2026-09-11-te4-screen-engine-01"

#: The published 15 phase-4-reaching Engine attempts, restated as run
#: directories so the chain.json enumeration can be pinned against it.
PUBLISHED_PHASE4_RUN_DIRS = frozenset({
    "2026-09-10-completionrate-engine-01",
    "2026-09-10-guardrail-reverify-engine-01",
    "2026-09-10-guardrail-reverify-engine-02",
    "2026-09-10-p4guardrail-engine-01",
    "2026-09-10-p4guardrail-engine-03",
    "2026-09-10-tightening3-engine-01",
    "2026-09-10-tightening3-engine-02",
    "2026-09-10-tightening4-engine-01",
    "2026-09-10-tightening4-engine-02",
    "2026-09-11-p4guardrail-round2-engine-01",
    "2026-09-11-p4guardrail-round2-engine-02",
    "2026-09-11-recurrence-engine-01",
    "2026-09-11-recurrence-engine-03",
    "2026-09-11-te4-screen-engine-01",
    "2026-09-11-te4-screen-engine-02",
})


def _require_runs_root() -> None:
    if not RUNS_ROOT.is_dir():
        pytest.skip(f"retained attempts absent: {RUNS_ROOT}")


def _require_retained(path: Path) -> Path:
    """The named path, or a loud skip. Absence never becomes empty evidence."""
    _require_runs_root()
    if not path.exists():
        pytest.skip(f"retained artifact absent: {path}")
    return path


def _transcript_path(spec: AttemptSpec) -> Path:
    """Engine transcripts are the named file; Baseline transcripts are nested."""
    _require_runs_root()
    run = RUNS_ROOT / spec.run_dir
    if spec.arm == "engine":
        return run / "harness" / ".satyrn-implementer-transcript.jsonl"
    found = next(run.rglob("transcript.jsonl"), None)
    if found is None:
        pytest.skip(f"retained artifact absent: {run} (no transcript.jsonl)")
    return found


def _events(spec: AttemptSpec) -> list[dict[str, object]]:
    path = _require_retained(_transcript_path(spec))
    return [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        if line.strip()
    ]


def _chain(spec: AttemptSpec) -> Mapping[str, object] | None:
    path = _require_retained(RUNS_ROOT / spec.run_dir / "chain.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, Mapping) else None


@pytest.mark.parametrize("spec", ATTEMPTS, ids=lambda spec: spec.label)
def test_every_retained_attempt_applied_a_content_changing_edit(
    spec: AttemptSpec,
) -> None:
    """Supports the `6 of 10` correction's denominator: every attempt in
    this set, both arms, applied at least one replacement. It does not by
    itself state the corrected denominator."""
    assert destructive_edit(_events(spec)) == "yes"


@pytest.mark.parametrize("spec", ATTEMPTS, ids=lambda spec: spec.label)
def test_restoration_answers_the_whole_population_with_a_tri_state(
    spec: AttemptSpec,
) -> None:
    """The published `restoration` figure (9 of 15 phase-4-reaching Engine
    attempts) is about a population this eight-attempt set is not, so no
    `yes`/`no` value is asserted here. What is checked is that the classifier
    answers over real events rather than throwing or silently declining."""
    assert restoration(_events(spec)) in {"yes", "no", "undecidable"}


def test_screen_engine_01_falsified_its_own_verification_claim() -> None:
    spec = next(s for s in ATTEMPTS if s.run_dir == FALSIFIED_VERIFICATION)

    assert verification_claim(_events(spec)) == "no"


def test_the_enumerated_phase4_run_dirs_match_the_published_population() -> None:
    """The chain.json enumeration must reproduce the published 15-run
    phase-4-reaching population; drift fails naming the enumerated set, and
    an absent runs root skips loudly."""
    _require_runs_root()
    enumerated = {
        spec.run_dir for spec in _phase4_reaching_engine_attempts(RUNS_ROOT)
    }

    assert enumerated == PUBLISHED_PHASE4_RUN_DIRS, (
        "phase-4 run-dir enumeration drifted from the published 15: "
        f"enumerated={sorted(enumerated)}"
    )


@pytest.mark.parametrize("spec", ENGINE_ATTEMPTS, ids=lambda spec: spec.label)
def test_engine_self_test_outcome_agrees_with_the_chain_record(
    spec: AttemptSpec,
) -> None:
    """`self_test_outcome` reads the transcript's last `run_self_test` exit
    code and refuses when any phase's independently recorded outcome
    disagrees. Agreement therefore shows up as a decided value that the chain
    does not change."""
    events = _events(spec)
    chain = _chain(spec)
    assert chain is not None, f"chain.json is not a mapping: {spec.run_dir}"

    from_transcript = self_test_outcome(events, chain=None)

    assert from_transcript != "undecidable"
    assert self_test_outcome(events, chain) == from_transcript


def test_a_missing_retained_artifact_is_a_loud_skip_naming_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling to the checks above: an absent artifact skips with its path in
    the reason, rather than running the classifiers over an empty list and
    reporting that absence as `undecidable`.

    `RUNS_ROOT` is redirected at an existing directory so the refusal under
    test is the artifact branch: with the real root absent,
    `_require_retained` skips naming the root before it ever reaches the
    artifact it was asked about, and the assertion below never exercises the
    behaviour it claims."""
    monkeypatch.setattr(sys.modules[__name__], "RUNS_ROOT", tmp_path)

    # The success sibling first: a redirect that silently failed to take could
    # otherwise let the refusal assertion below pass against the real root.
    present = tmp_path / "present-attempt" / "transcript.jsonl"
    present.parent.mkdir()
    present.write_text("{}\n", encoding="utf-8")
    assert _require_retained(present) == present

    absent = tmp_path / "absent-attempt" / "transcript.jsonl"

    with pytest.raises(pytest.skip.Exception) as excinfo:
        _require_retained(absent)

    assert str(absent) in str(excinfo.value)


def test_a_missing_runs_root_is_a_loud_skip_naming_the_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other refusal branch, kept separate so the artifact test above can
    hold its root: no runs root at all skips naming the root, which is what
    distinguishes an absent checkout from an absent artifact. The success
    sibling first, so a redirect that silently failed to take cannot let the
    refusal assertion below pass against a root that is really there."""
    monkeypatch.setattr(sys.modules[__name__], "RUNS_ROOT", tmp_path)
    assert _require_runs_root() is None

    absent_root = tmp_path / "absent-runs-root"
    monkeypatch.setattr(sys.modules[__name__], "RUNS_ROOT", absent_root)

    with pytest.raises(pytest.skip.Exception) as excinfo:
        _require_runs_root()

    assert str(absent_root) in str(excinfo.value)
