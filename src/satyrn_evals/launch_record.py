"""``satyrn-evals launch RECORD --arm ARM.json …``: the gates, then the record's cells.

The spec's launcher gates ("Process"), in order, before any cell:

1. the record loads, and every ``--arm`` file is one of the record's arms on
   the record's model, with a command ``check_invocation`` accepts (task,
   task tree, arm, model) and a rung the task declares;
2. a deciding record (admission, route-proof, campaign) runs with the spec's
   backstop (1,800 s command, 2,100 s deadline), the settings check, the full
   hunt and no test PATH seam (Ruling 7);
3. ``gate``: the record is frozen (tracked, unchanged against ``HEAD``), the
   previous result is committed, n and wall clock are under the cadence cap,
   and a deciding purpose is isolated;
4. under isolation, the cell preflight (``cell_preflight.preflight_cell``) is clean;
5. ``scripts/preflight_settings.py`` exits 0 for every arm (``--cell`` under
   isolation); its provenance block is kept for the drift check.

Between cells the drift probe re-reads the record and arm file bytes, the
task tree digest and the settings provenance; any change stops the night.

Artifacts: the night directory ``RUNS_ROOT/<record stem>/`` (under the
maintainer's home by default, which the cell cannot read) holds ``launch.json``
(the ledger), ``slots/`` and one ``run``-shaped directory per arm whose
``summary.json`` is written once that arm's n cells are finished
(``satyrn-evals summarize`` rebuilds it). The committed result is
``<record>.result.json`` beside the record (Ruling 6).

Exit codes: 0 complete; 1 preflight or settings problem (nothing ran); 2 a
refused record or invocation; 3 an infrastructure stop or a signal; 4 the
wall clock stopped the night early (launch the same record again to resume).
"""

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from satyrn_evals.arms import Arm, build_argv, load_arm
from satyrn_evals.attempt import resolve_contract
from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, CELLS_ROOT, Isolation
from satyrn_evals.cell_preflight import CellPreflight, preflight_cell
from satyrn_evals.errors import SatyrnError
from satyrn_evals.launch import (
    SLOTS_DIR,
    CellProcess,
    LaunchOutcome,
    Slot,
    Status,
    check_night,
    infrastructure_reason,
    launch_cells,
    read_slots,
    slot_path,
    write_atomically,
    write_ledger,
)
from satyrn_evals.launch_cell import (
    ATTEMPT_DEADLINE,
    COMMAND_BACKSTOP,
    popen_cell,
)
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.rescore import (
    _load_cell,
    compute_evidence,
    compute_pathology,
    pathology_context,
)
from satyrn_evals.run_record import (
    DECIDING_PURPOSES,
    RunRecord,
    RunRecordError,
    check_invocation,
    gate,
    load_run_record,
    record_arms,
)
from satyrn_evals.summary import SUMMARY_NAME, compute_summary, write_summary
from satyrn_evals.task_tree import tree_digest

DEFAULT_RUNS_ROOT = Path.home() / "satyrn-runs"
SETTINGS_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "preflight_settings.py"
EXIT_CODES = {Status.COMPLETE: 0, Status.INFRASTRUCTURE: 3, Status.INTERRUPTED: 3, Status.CAPPED: 4}


def _git(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=False)


def git_frozen(path: Path) -> bool:
    """Tracked, and no staged or unstaged change against ``HEAD``."""
    where, name = path.resolve().parent, path.name
    return (
        _git(["ls-files", "--error-unmatch", "--", name], where).returncode == 0
        and _git(["diff", "--quiet", "HEAD", "--", name], where).returncode == 0
    )


def git_committed(path: str) -> bool:
    return _git(["ls-files", "--error-unmatch", "--", path], Path.cwd()).returncode == 0


def git_head() -> str:
    return _git(["rev-parse", "HEAD"], Path.cwd()).stdout.strip()


def settings_provenance(arm_path: Path, cell: bool) -> tuple[int, str]:
    """``preflight_settings.py`` for one arm: its exit code and its provenance JSON."""
    ran = subprocess.run(
        [sys.executable, os.fspath(SETTINGS_SCRIPT), os.fspath(arm_path), *(["--cell"] if cell else [])],
        capture_output=True, text=True, check=False,
    )
    return ran.returncode, ran.stdout if ran.returncode == 0 else ran.stdout + ran.stderr


@dataclass(frozen=True, slots=True)
class LaunchFacts:
    """Everything that spawns or reads git, replaceable by the default tier."""

    frozen: Callable[[Path], bool] = git_frozen
    committed: Callable[[str], bool] = git_committed
    head: Callable[[], str] = git_head
    preflight: Callable[..., CellPreflight] = preflight_cell
    settings: Callable[[Path, bool], tuple[int, str]] = settings_provenance
    spawn_cell: Callable[[Path, Path], CellProcess] = popen_cell


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _arms(record: RunRecord, arm_paths: Sequence[Path]) -> dict[str, tuple[Path, Arm]]:
    loaded = {}
    for path in arm_paths:
        arm = load_arm(path)
        if arm.arm in loaded:
            raise RunRecordError(f"--arm names {arm.arm} twice")
        loaded[arm.arm] = (path, arm)
    if sorted(loaded) != sorted(record_arms(record)):
        raise RunRecordError(f"the record runs {record.arm}; the --arm files are {'+'.join(loaded) or 'none'}")
    for path, arm in loaded.values():
        if arm.model != record.model:
            raise RunRecordError(f"arm file {path} is on {arm.model}; the record is on {record.model}")
    if len({arm.pins.pi for _, arm in loaded.values()}) != 1:
        raise RunRecordError("the arms pin different pi versions; interleaved arms run one pi")
    return loaded


def _tolerated(cells_root: Path = CELLS_ROOT) -> tuple[Path, ...]:
    """The cells-root child a deciding record has already refused the env for (R5).

    ``launch --preflight`` never tolerates: only ``launch_record`` calls
    this. The test PATH seam (``CELL_PATH_PREFIX_ENV``) may name several
    directories separated by ``os.pathsep``; only the first is under
    ``cells_root`` in the fixtures this needs (``cell_scratch``'s
    ``satyrn-test-*`` directory), so its direct child under ``cells_root``
    is the one entry preflight is told to look past.
    """
    prefix = os.environ.get(CELL_PATH_PREFIX_ENV)
    if not prefix:
        return ()
    first = Path(prefix.split(os.pathsep)[0]).resolve()
    root = cells_root.resolve()
    try:
        relative = first.relative_to(root)
    except ValueError:
        return ()
    if not relative.parts:
        return ()
    return (root / relative.parts[0],)


def _arm_results(finished: dict[int, dict], arm: str) -> tuple[list[dict], list[dict]]:
    """This arm's model-outcome results, and its infrastructure results (``slot``/``code``/``attempt_dir``).

    An infrastructure result (``launch.infrastructure_reason``) measured nothing about the model:
    it is not in the denominator for ``finished``/``passes``/``code_counts`` or a summary (spec,
    "Denominators"). It is only moved aside by the *next* launch (``_replace_infrastructure_slots``),
    so a night that stops on one must not commit it into this arm's counts in the meantime.
    """
    all_results = [result for _, result in sorted(finished.items()) if result["arm"] == arm]
    infrastructure = [
        {"slot": result["slot"], "code": result["code"], "attempt_dir": result["attempt_dir"]}
        for result in all_results
        if infrastructure_reason(result) is not None
    ]
    results = [result for result in all_results if infrastructure_reason(result) is None]
    return results, infrastructure


def _arm_counts(finished: dict[int, dict], arms: Sequence[str], n: int) -> dict[str, dict]:
    """The counts ``write_arm_summaries`` reports for every arm, without touching the manifest or a summary.

    Never raises: pure bookkeeping over already-parsed slot records, safe to fall back on when
    the manifest- and summary-computing half of ``write_arm_summaries`` fails.
    """
    report: dict[str, dict] = {}
    for arm in arms:
        results, infrastructure = _arm_results(finished, arm)
        codes: dict[str, int] = {}
        for result in results:
            codes[result["code"]] = codes.get(result["code"], 0) + 1
        report[arm] = {
            "finished": len(results), "n": n, "code_counts": codes,
            "passes": sum(1 for result in results if result["verdict"] == "pass"), "summary": None,
            "infrastructure": infrastructure,
        }
    return report


def write_arm_summaries(night: Path, arms: Sequence[str], n: int, task_dir: Path) -> dict[str, dict]:
    """``summary.json`` for every arm whose n non-infrastructure slots are finished; the counts for every arm."""
    manifest = load_manifest(task_dir)
    overlay, visible_texts = pathology_context(task_dir, manifest)
    finished = read_slots(night)
    report = _arm_counts(finished, arms, n)
    for arm, entry in report.items():
        if entry["finished"] != n:
            continue
        results, _ = _arm_results(finished, arm)
        output = night / arm
        cells = [_load_cell(output / result["attempt_dir"]) for result in results]
        kwargs = dict(task_dir=task_dir, manifest=manifest, overlay=overlay, visible_texts=visible_texts)
        summary = compute_summary(
            cells, oracle_visibility=manifest.oracle_visibility,
            pathology=compute_pathology(output, cells, **kwargs), evidence=compute_evidence(output, cells, **kwargs),
        )
        write_summary(output / SUMMARY_NAME, summary)
        entry["summary"] = os.fspath(output / SUMMARY_NAME)
        entry["contamination"] = summary.contamination
    return report


def launch_record(
    record_path: Path,
    arm_paths: Sequence[Path],
    *,
    tasks_root: Path,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    timeout: float = COMMAND_BACKSTOP,
    attempt_timeout: float = ATTEMPT_DEADLINE,
    hunt: bool = True,
    settings: bool = True,
    grace: float = 60.0,
    poll_interval: float = 1.0,
    facts: LaunchFacts | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    facts = facts or LaunchFacts()
    out, err = out or sys.stdout, err or sys.stderr
    record = load_run_record(record_path)
    arms = _arms(record, arm_paths)
    task_dir = resolve_task(record.task, tasks_root=tasks_root)
    commands = {name: build_argv(arm) for name, (_, arm) in arms.items()}
    for command in commands.values():
        check_invocation(record, task=record.task, task_dir=task_dir, command=command)
    resolve_contract(load_manifest(task_dir), record.rung)
    if record.purpose in DECIDING_PURPOSES:
        seams = [
            name for name, used in (
                ("--no-settings", not settings), ("--no-hunt", not hunt),
                (f"--timeout {timeout:g}", timeout != COMMAND_BACKSTOP),
                (f"--attempt-timeout {attempt_timeout:g}", attempt_timeout != ATTEMPT_DEADLINE),
                (CELL_PATH_PREFIX_ENV, bool(os.environ.get(CELL_PATH_PREFIX_ENV))),
            ) if used
        ]
        if seams:
            raise RunRecordError(f"a {record.purpose} record runs with none of: {', '.join(seams)}")
    previous = None if record.previous_result is None else facts.committed(record.previous_result)
    gate(record, previous_result_committed=previous, record_frozen=facts.frozen(record_path))

    problems: list[str] = []
    checked: dict[str, object] = {}
    if record.isolation is Isolation.ISOLATED:
        report = facts.preflight(
            pinned_pi=next(iter(arms.values()))[1].pins.pi,
            protected=(Path.cwd(), tasks_root, Path.home(), runs_root),
            tasks_root=tasks_root, hunt_root="/" if hunt else None,
            tolerated=_tolerated(),
        )
        problems += report.problems
        checked["preflight"] = report.checked
    baseline_settings: dict[str, str] = {}
    if settings:
        for name, (path, _) in arms.items():
            code, text = facts.settings(path, record.isolation is Isolation.ISOLATED)
            if code != 0:
                problems.append(f"preflight_settings for {name} exited {code}: {text.strip()}")
            baseline_settings[name] = text
        checked["settings"] = {name: json.loads(text) for name, text in baseline_settings.items() if text.startswith("{")}
    if problems:
        for problem in problems:
            print(f"launch FAILED: {problem}", file=err)
        return 1

    night = runs_root / record_path.stem
    identity = {"record_sha256": _sha256(record_path)}
    check_night(night, identity)
    pinned = {record_path: identity["record_sha256"], **{path: _sha256(path) for path, _ in arms.values()}}
    tree = record.task_tree_sha256

    def drift() -> str | None:
        for path, digest in pinned.items():
            if _sha256(path) != digest:
                return f"{path} changed since the launch began"
        if tree_digest(task_dir) != tree:
            return f"the {record.task} task tree no longer matches task_tree_sha256"
        for name, (path, _) in arms.items() if settings else ():
            if facts.settings(path, record.isolation is Isolation.ISOLATED)[1] != baseline_settings[name]:
                return f"the settings provenance for {name} changed"
        return None

    def spawn(slot: Slot) -> CellProcess:
        spec = {
            "slot": slot.index, "arm": slot.arm, "task": record.task, "tasks_root": os.fspath(tasks_root),
            "output": os.fspath(night / slot.arm), "command": commands[slot.arm], "timeout": timeout,
            "attempt_timeout": attempt_timeout, "rung": record.rung, "token_budget": record.token_budget,
            "turn_budget": record.turn_budget, "isolation": record.isolation.value,
            "result": os.fspath(slot_path(night, slot)),
        }
        spec_path = night / SLOTS_DIR / f"{slot.name}.spec.json"
        write_atomically(spec_path, spec)
        return facts.spawn_cell(spec_path, night / SLOTS_DIR / f"{slot.name}.log")

    sitting = {
        "record": os.fspath(record_path), "started": datetime.now(UTC).isoformat(timespec="seconds"),
        "k": record.k, "evals_head": facts.head(), **checked,
    }
    outcome: LaunchOutcome = launch_cells(
        night=night, arms=record_arms(record), n=record.n, k=record.k, max_seconds=record.max_minutes * 60,
        cell_seconds=attempt_timeout, spawn=spawn, drift=drift, grace=grace, poll_interval=poll_interval,
    )
    write_ledger(night, identity=identity, sitting=sitting, outcome=outcome)
    ledger = json.loads((night / "launch.json").read_text(encoding="utf-8"))
    summary_error: str | None = None
    try:
        arms_report: dict[str, dict] | None = write_arm_summaries(night, record_arms(record), record.n, task_dir)
    except (SatyrnError, OSError, ValueError) as error:
        # The ledger is already written; the committed result must land regardless of a summary
        # failure (a corrupt manifest, an unreadable cell directory, a bad JSON write) — an operator
        # script must not see a stale result from the previous sitting.
        summary_error = f"{type(error).__name__}: {error}"
        try:
            arms_report = _arm_counts(read_slots(night), record_arms(record), record.n)
        except Exception:  # noqa: BLE001 - counts are best-effort once the real computation has failed
            arms_report = None
    result = {
        "record": os.fspath(record_path), **identity, "status": outcome.status.value, "reason": outcome.reason, "night": os.fspath(night),
        "task": record.task, "rung": record.rung, "k": record.k, "n": record.n, "purpose": record.purpose,
        "arms": arms_report,
        "cells": [
            {**{key: slot[key] for key in ("slot", "arm", "attempt_dir", "code", "verdict")},
             "infrastructure": infrastructure_reason(slot) is not None}
            for slot in ledger["slots"]
        ],
        "replaced": ledger["replaced"], "sittings": ledger["sittings"],
    }
    if summary_error is not None:
        result["summary_error"] = summary_error
    write_atomically(record_path.with_suffix(".result.json"), result)
    print(json.dumps({"status": result["status"], "reason": result["reason"], "night": result["night"],
                      "result": os.fspath(record_path.with_suffix(".result.json"))}, indent=2), file=out)
    if outcome.status is not Status.COMPLETE:
        print(f"launch stopped ({outcome.status}): {outcome.reason}", file=err)
    if summary_error is not None:
        print(f"launch: writing arm summaries failed: {summary_error}", file=err)
    if summary_error is not None and outcome.status is Status.COMPLETE:
        return 3
    return EXIT_CODES[outcome.status]
