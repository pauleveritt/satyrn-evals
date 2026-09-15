"""Offline qualification: a task earns a cell only by passing these, with no model.

The spec's three checks ("The self-hosted generator"), applied to every
candidate whatever its source:

1. ``grade`` passes known-good with every expected test executed and fails
   known-broken, both with zero collection errors;
2. a fake attempt that applies known-good, commits part of it and leaves the
   rest uncommitted (`qualify_fake_pi`) goes through the real Baseline
   adapter and harness, is harvested whole -- the same paths as known-good --
   and grades pass;
3. the hidden suite passes GOOD (known-good) three times running.

`judge_fixture` and `judge_harvest` are pure; `qualify` runs the grades and
the attempt, so it spawns and belongs to the integration tier.
"""

import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.qualify_fake_pi import PATCH_ENV
from satyrn_evals.receipt import Receipt
from satyrn_evals.verdict import Verdict

GOOD_RUNS = 3
#: The spec's candidates ("Workloads"), each with the rung it runs at.
CEILING_CANDIDATES: dict[str, str] = {
    "agentclinic-repair-depth-3": "R1",
    "selfhost-run-record-gate": "R1-plan",
    "selfhost-guard-prefixes": "R1-plan",
    "selfhost-review-script": "R1-plan",
}
FLOOR_CANDIDATES: dict[str, str] = {
    "agentclinic-repair-depth-2": "R1",
    "selfhost-docs-linter": "R1-plan",
}


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    passed: bool
    detail: str

    def line(self, task: str) -> str:
        return f"qualify {task}: {self.name} {'ok' if self.passed else 'FAILED'}: {self.detail}"


def judge_fixture(name: str, receipt: Receipt, *, expect: Verdict, expected_ids: tuple[str, ...]) -> Check:
    """One fixture grade against its expectation; collection errors always fail."""
    evidence = receipt.evidence
    if evidence is None:
        return Check(name, False, f"verdict {receipt.verdict} with no oracle evidence: {receipt.reason}")
    errors = evidence.get("counts", {}).get("error", 0) + len(evidence.get("collect_errors", []))
    executed = len(evidence["executed_test_ids"])
    detail = f"verdict {receipt.verdict}, executed {executed} of {len(expected_ids)}, errors {errors}"
    passed = receipt.verdict is expect and errors == 0
    if expect is Verdict.PASS:
        passed = passed and set(evidence["executed_test_ids"]) >= set(expected_ids)
    return Check(name, passed, detail)


def judge_harvest(code: AttemptCode, verdict: Verdict | None, patch_text: str | None, known_good: str) -> Check:
    """The live harvest: whole (the known-good paths) and graded pass."""
    want = sorted(parse_patch_paths(known_good))
    got = sorted(parse_patch_paths(patch_text)) if patch_text else []
    detail = f"code {code}, verdict {verdict}, paths {got} (known-good {want})"
    passed = code is AttemptCode.OK and verdict is Verdict.PASS and got == want
    return Check("live-harvest", passed, detail)


@contextmanager
def _fake_pi_on_path(scratch: Path, patch: Path) -> Iterator[None]:
    bin_dir = scratch / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "pi"
    shim.write_text(f'#!/bin/sh\nexec {sys.executable} -m satyrn_evals.qualify_fake_pi "$@"\n')
    shim.chmod(0o755)
    saved = {name: os.environ.get(name) for name in ("PATH", PATCH_ENV)}
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
    os.environ[PATCH_ENV] = os.fspath(patch)
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def qualify(task_dir: Path, *, scratch: Path | None = None) -> list[Check]:
    """Run every check against ``task_dir``; the scratch directory is removed afterwards."""
    manifest = load_manifest(task_dir)
    expected = manifest.expected_test_ids
    good = task_dir / manifest.fixtures["known_good"]
    broken = task_dir / manifest.fixtures["known_broken"]
    root = Path(tempfile.mkdtemp(prefix="satyrn-qualify-", dir=scratch))
    try:
        checks = [
            judge_fixture(
                f"known-good run {run}",
                grade(task_dir, good, root / f"good-{run}.json"),
                expect=Verdict.PASS,
                expected_ids=expected,
            )
            for run in range(1, GOOD_RUNS + 1)
        ]
        checks.append(
            judge_fixture("known-broken", grade(task_dir, broken, root / "broken.json"), expect=Verdict.FAIL, expected_ids=expected)
        )
        with _fake_pi_on_path(root, good):
            record = attempt(
                task=manifest.name,
                tasks_root=task_dir.parent,
                output=root / "attempts",
                command=[sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/qualify"],
                timeout=600,
            )
        patch = root / "attempts" / record.attempt_dir / "patch.diff" if record.attempt_dir else None
        patch_text = patch.read_text(encoding="utf-8") if patch is not None and patch.is_file() else None
        checks.append(judge_harvest(record.code, record.verdict, patch_text, good.read_text(encoding="utf-8")))
        return checks
    finally:
        shutil.rmtree(root, ignore_errors=True)
