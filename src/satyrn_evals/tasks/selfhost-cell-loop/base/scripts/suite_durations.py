"""Public-suite and grade durations per release-one candidate task, no model.

The Phase 1 plan freezes the engine's per-command bounds (bash `timeout`
default 120 s, clamp 300 s) and its self-test bound (runner.py, 120 s)
against these numbers. `fits` is the rule; `measure` produces the numbers;
`--write` commits them. Task trees on probe branches are read with
`git archive`, never checked out.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "scripts" / "suite_durations.json"
RUNS = 3
DEFAULT_SECONDS = 120
CLAMP_SECONDS = 300
RUNNER_SECONDS = 120   # satyrn-engine runner.py DEFAULT_TEST_TIMEOUT_SECONDS
MARGIN = 2.0


@dataclass(frozen=True, slots=True)
class Candidate:
    task: str
    branch: str

    @property
    def tree_path(self) -> str:
        return f"src/satyrn_evals/tasks/{self.task}"


CANDIDATES: tuple[Candidate, ...] = (
    Candidate("agentclinic-repair-misleading-locus", "release-one"),
    Candidate("agentclinic-complaint-lifecycle", "release-one"),
    Candidate("agentclinic-repair-depth-2", "worktree-ornith-ceiling-probe"),
    Candidate("agentclinic-repair-depth-3", "worktree-ornith-ceiling-probe"),
    Candidate("selfhost-docs-linter", "worktree-selfhost-headroom-probe"),
    Candidate("selfhost-guard-prefixes", "worktree-selfhost-headroom-probe"),
    Candidate("selfhost-run-record-gate", "worktree-selfhost-headroom-probe"),
)


@dataclass(frozen=True, slots=True)
class Measurement:
    task: str
    branch: str
    commit: str
    public_suite: list[str] | None
    public_seconds: list[float]
    public_exits: list[int]
    grade_seconds: list[float]
    grade_verdicts: list[str]


def fits(measured_max_seconds: float | None, *, default_seconds: int, clamp_seconds: int,
         runner_seconds: int, margin: float) -> list[str]:
    """Name every way the frozen bounds fail to cover the longest suite. Pure."""
    if measured_max_seconds is None:
        return ["no candidate with a public suite was measured"]
    failures: list[str] = []
    needed = measured_max_seconds * margin
    if default_seconds < needed:
        failures.append(f"default {default_seconds} s < {needed} s ({measured_max_seconds} s x {margin})")
    if clamp_seconds < 2 * default_seconds:
        failures.append(f"clamp {clamp_seconds} s < {2 * default_seconds} s (2 x default)")
    if runner_seconds < needed:
        failures.append(f"runner {runner_seconds} s < {needed} s ({measured_max_seconds} s x {margin})")
    return failures


def longest_public(rows: dict[str, dict]) -> float | None:
    measured = [max(row["public_seconds"]) for row in rows.values() if row["public_suite"] and row["public_seconds"]]
    return max(measured) if measured else None


def materialize(candidate: Candidate, scratch: Path) -> tuple[Path, str]:
    commit = subprocess.run(["git", "rev-parse", f"{candidate.branch}^{{commit}}"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout.strip()
    task_dir = scratch / candidate.task
    task_dir.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", f"{candidate.branch}:{candidate.tree_path}"],
                             cwd=ROOT, check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(task_dir)], input=archive, check=True)
    return task_dir, commit


def _timed_public_run(task_dir: Path, public_suite: list[str], scratch: Path) -> tuple[float, int]:
    work = scratch / "public"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(task_dir / "base", work, symlinks=True)
    subprocess.run(["git", "init", "-q"], cwd=work, check=True)
    subprocess.run(["git", "apply", str(task_dir / "fixtures" / "known-good.patch")], cwd=work, check=True)
    started = time.monotonic()
    completed = subprocess.run(public_suite, cwd=work, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return round(time.monotonic() - started, 1), completed.returncode


def measure(candidate: Candidate, scratch: Path) -> Measurement:
    from satyrn_evals.grade import grade
    from satyrn_evals.manifest import load_manifest

    task_dir, commit = materialize(candidate, scratch)
    manifest = load_manifest(task_dir)
    public_suite = list(manifest.public_suite) or None
    public_seconds: list[float] = []
    public_exits: list[int] = []
    if public_suite:
        for _ in range(RUNS):
            seconds, code = _timed_public_run(task_dir, public_suite, scratch)
            public_seconds.append(seconds)
            public_exits.append(code)
    grade_seconds: list[float] = []
    verdicts: list[str] = []
    for index in range(RUNS):
        receipt = scratch / f"receipt-{index}.json"
        started = time.monotonic()
        try:
            result = grade(task_dir, task_dir / "fixtures" / "known-good.patch", receipt)
        except Exception as exc:  # one task's grader must not abort --write; the error is the record (m10)
            grade_seconds.append(round(time.monotonic() - started, 1))
            verdicts.append(f"grade_error: {type(exc).__name__}: {exc}")
            continue
        grade_seconds.append(round(time.monotonic() - started, 1))
        verdicts.append(str(result.verdict))
    return Measurement(candidate.task, candidate.branch, commit, public_suite,
                       public_seconds, public_exits, grade_seconds, verdicts)


def main(argv: list[str]) -> int:
    if argv != ["--write"]:
        print("usage: suite_durations.py --write", file=sys.stderr)
        return 2
    measurements: list[Measurement] = []
    with tempfile.TemporaryDirectory(prefix="suite-durations-") as scratch:
        for candidate in CANDIDATES:
            measurement = measure(candidate, Path(scratch) / candidate.task)
            measurements.append(measurement)
            print(f"{candidate.task}: public {measurement.public_seconds} exits {measurement.public_exits} "
                  f"grade {measurement.grade_seconds} {measurement.grade_verdicts}")
    rows = {m.task: asdict(m) for m in measurements}
    longest = longest_public(rows)
    failures = fits(longest, default_seconds=DEFAULT_SECONDS, clamp_seconds=CLAMP_SECONDS,
                    runner_seconds=RUNNER_SECONDS, margin=MARGIN)
    failures += [f"{m.task}: public suite exited {m.public_exits} on known-good"
                 for m in measurements if any(code != 0 for code in m.public_exits)]
    body = {
        "version": 1,
        "machine": "the maintainer's batch machine; seconds never compare across machines",
        "recompute": "uv run python scripts/suite_durations.py --write",
        "margin": MARGIN,
        "frozen": {"default_seconds": DEFAULT_SECONDS, "clamp_seconds": CLAMP_SECONDS, "runner_seconds": RUNNER_SECONDS},
        "longest_public_seconds": longest,
        "fit_failures": failures,
        "tasks": rows,
    }
    OUTPUT.write_text(json.dumps(body, indent=2) + "\n")
    print(OUTPUT)
    for failure in failures:
        print(f"fit failure: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
