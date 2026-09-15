"""Console entry point: satyrn-evals grade, capture, and attempt."""

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

from satyrn_evals.arms import load_arm
from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.capture import capture
from satyrn_evals.capture_record import CaptureOutcome
from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, Isolation
from satyrn_evals.cell_engine import export_engine
from satyrn_evals.cell_preflight import preflight_cell
from satyrn_evals.census import build_arg_parser as build_census_parser
from satyrn_evals.census import run_cli as run_census
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, resolve_task
from satyrn_evals.qualify import qualify
from satyrn_evals.rescore import regrade_attempt, summarize_output
from satyrn_evals.run import run
from satyrn_evals.run_record import (
    RunRecordError,
    attempt_budget,
    check_invocation,
    gate,
    load_run_record,
)
from satyrn_evals.session import run_session
from satyrn_evals.session_grader import SessionGrader
from satyrn_evals.session_manifest import DEFAULT_SESSION_SPEC
from satyrn_evals.session_record import SessionCode
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import DEFAULT_TIMEOUT

_EXIT_CODES: dict[Verdict, int] = {
    Verdict.PASS: 0,
    Verdict.FAIL: 0,
    Verdict.UNAVAILABLE: 3,
}


def positive_finite_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "timeout must be a finite number greater than zero"
        ) from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError(
            "timeout must be a finite number greater than zero"
        )
    return timeout


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--n must be an integer greater than zero"
        ) from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("--n must be an integer greater than zero")
    return number


def _previous_result_committed(record: object) -> bool | None:
    """Whether the record's ``previous_result`` (if any) is a committed path."""
    previous_result = record.previous_result
    if previous_result is None:
        return None
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", previous_result],
            capture_output=True,
        ).returncode
        == 0
    )


def _record_settings(
    run_record: str | None, *, task: str, tasks_root: str, command: list[str], n: int | None = None
) -> tuple[AttemptBudget | None, Isolation]:
    """The budget and profile a run record froze, after the same gate ``launch --check``
    runs and after checking the invocation (task, tree, arm, model, and — for ``run`` —
    ``--n``) is the record's.

    Without a record: no budget, the local profile.
    """
    if run_record is None:
        return None, Isolation.LOCAL
    record = load_run_record(Path(run_record))
    gate(record, previous_result_committed=_previous_result_committed(record))
    check_invocation(
        record, task=task, task_dir=resolve_task(task, tasks_root=Path(tasks_root)), command=command
    )
    if n is not None and n != record.n:
        raise RunRecordError(f"the record asks n={record.n}; --n {n} disagrees")
    return attempt_budget(record), record.isolation


def split_attempt_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split the attempt subcommand's argv (after the 'attempt' token).

    Returns (flags, command): everything before the first '--' is evals'
    own flags; everything after is the attempt command verbatim. An empty
    command means the caller must treat it as a usage error.
    """
    if "--" in argv:
        i = argv.index("--")
        return argv[:i], argv[i + 1 :]
    return argv, []


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv[:1] == ["attempt"]:
            flags, command = split_attempt_argv(argv[1:])
            if not command:
                raise UsageError(
                    "attempt command is required: attempt TASK [flags] -- COMMAND..."
                )
            args = parser.parse_args(["attempt", *flags])
            budget, isolation = _record_settings(
                args.run_record, task=args.task, tasks_root=args.tasks_root, command=command
            )
            record = attempt(
                task=args.task,
                tasks_root=Path(args.tasks_root),
                output=Path(args.output),
                command=command,
                timeout=args.timeout,
                attempt_timeout=args.attempt_timeout,
                max_repeated_calls=args.max_repeated_calls,
                rung=args.rung,
                budget=budget,
                isolation=isolation,
            )
            if record.code is AttemptCode.GRADE_FAILED:
                print(f"satyrn-evals: {record.message}", file=sys.stderr)
            if record.retained_path is not None:
                print(
                    f"satyrn-evals: workspace retained at {record.retained_path}",
                    file=sys.stderr,
                )
                return 3
            if record.outcome is AttemptOutcome.REFUSED:
                return 3
            return 0 if record.verdict in (Verdict.PASS, Verdict.FAIL) else 3
        if argv[:1] == ["run"]:
            flags, command = split_attempt_argv(argv[1:])
            if not command:
                raise UsageError(
                    "run command is required: run TASK [flags] -- COMMAND..."
                )
            args = parser.parse_args(["run", *flags])
            budget, isolation = _record_settings(
                args.run_record, task=args.task, tasks_root=args.tasks_root, command=command, n=args.n
            )
            run(
                task=args.task,
                tasks_root=Path(args.tasks_root),
                output=Path(args.output),
                command=command,
                n=args.n,
                timeout=args.timeout,
                attempt_timeout=args.attempt_timeout,
                max_repeated_calls=args.max_repeated_calls,
                rung=args.rung,
                budget=budget,
                isolation=isolation,
            )
            return 0
        if argv[:1] == ["session"]:
            flags, command = split_attempt_argv(argv[1:])
            if not command:
                raise UsageError(
                    "session adapter is required: session TASK [flags] -- ADAPTER..."
                )
            args = parser.parse_args(["session", *flags])
            record = run_session(
                task=args.task,
                tasks_root=Path(args.tasks_root),
                output=Path(args.output),
                adapter_command=command,
                start_timeout=args.start_timeout,
                step_timeout=args.step_timeout,
                close_timeout=args.close_timeout,
                grader=SessionGrader(
                    task_dir=resolve_task(args.task, tasks_root=Path(args.tasks_root))
                ),
                session_spec=args.session_spec,
            )
            match record.code:
                case (
                    SessionCode.WORKSPACE_FAILED
                    | SessionCode.CLEANUP_FAILED
                    | SessionCode.GRADE_UNAVAILABLE
                ):
                    return 3
                case _:
                    return 0
        args = parser.parse_args(argv)
        if args.command == "census":
            return run_census(args.runs_root, args.json_path)
        if args.command == "launch":
            if args.preflight is not None:
                return _launch_preflight(args)
            if args.check is None:
                print("launch: cells are Phase 2c; use --check or --preflight", file=sys.stderr)
                return UsageError.exit_code
            record = load_run_record(Path(args.check))
            gate(record, previous_result_committed=_previous_result_committed(record))
            print("launch: record accepted")
            return 0
        if args.command == "cell-engine":
            print(export_engine(Path(args.engine_repo), args.commit))
            return 0
        if args.command == "qualify":
            failed = False
            for task in args.tasks:
                for check in qualify(resolve_task(task, tasks_root=Path(args.tasks_root))):
                    print(check.line(task))
                    failed = failed or not check.passed
            return 1 if failed else 0
        if args.command == "grade":
            task_dir = resolve_task(args.task, tasks_root=Path(args.tasks_root))
            receipt = grade(task_dir, Path(args.patch), Path(args.receipt))
            return _EXIT_CODES[receipt.verdict]
        if args.command == "summarize":
            summarize_output(Path(args.output), tasks_root=Path(args.tasks_root))
            return 0
        if args.command == "regrade":
            if (
                regrade_attempt(
                    Path(args.attempt_dir), tasks_root=Path(args.tasks_root)
                )
                is None
            ):
                print(
                    "satyrn-evals: regrade: nothing to grade (refusal record)",
                    file=sys.stderr,
                )
            return 0
        record = capture(
            repo=Path(args.repo),
            fix_sha=args.revert,
            name=args.name,
            contract=args.contract,
            output=Path(args.output),
        )
        return 0 if record.outcome is CaptureOutcome.CAPTURED else 3
    except SatyrnError as e:
        print(f"satyrn-evals: {e}", file=sys.stderr)
        return e.exit_code


def _launch_preflight(args: argparse.Namespace) -> int:
    """The isolated sitting's cell checks; the JSON report goes to stdout, each problem to stderr."""
    record = load_run_record(Path(args.preflight))
    if record.isolation is not Isolation.ISOLATED:
        raise RunRecordError(f"launch --preflight checks the cell user; {args.preflight} is a local record")
    if args.arm is None:
        raise UsageError("launch --preflight needs --arm ARM.json")
    arm = load_arm(Path(args.arm))
    if (arm.arm, arm.model) != (record.arm, record.model):
        raise RunRecordError(
            f"arm file {args.arm} is {arm.arm} on {arm.model}; the record is {record.arm} on {record.model}"
        )
    tasks_root = Path(args.tasks_root)
    report = preflight_cell(
        pinned_pi=arm.pins.pi,
        protected=(Path.cwd(), tasks_root, Path.home()),
        tasks_root=tasks_root,
        hunt_root=None if args.no_hunt else "/",
    )
    problems = list(report.problems)
    if os.environ.get(CELL_PATH_PREFIX_ENV):
        problems.append(f"{CELL_PATH_PREFIX_ENV} is set; it is a test seam, never a sitting's PATH")
    print(json.dumps({"record": args.preflight, "arm": args.arm, "problems": problems, **report.checked}, indent=2))
    for problem in problems:
        print(f"launch preflight FAILED: {problem}", file=sys.stderr)
    return 1 if problems else 0


parser = argparse.ArgumentParser(
    prog="satyrn-evals",
    description="Offline grading and task capture for development tasks.",
)
sub = parser.add_subparsers(dest="command", required=True)

grade_p = sub.add_parser("grade", help="apply PATCH to TASK and record the verdict")
grade_p.add_argument("task", help="bundled task name")
grade_p.add_argument("patch", help="unified diff file")
grade_p.add_argument(
    "--receipt", default="receipt.json", help="receipt path (default: receipt.json)"
)
grade_p.add_argument(
    "--tasks-root",
    default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)

cell_engine_p = sub.add_parser(
    "cell-engine", help="export one engine commit under the cells root for the isolated Engine arm"
)
cell_engine_p.add_argument("--engine-repo", required=True, help="the maintainer's engine checkout")
cell_engine_p.add_argument("--commit", required=True, help="the engine commit the arm runs")

qualify_p = sub.add_parser(
    "qualify", help="offline qualification: fixtures both ways, a live harvest, known-good three times"
)
qualify_p.add_argument("tasks", nargs="+", help="task names")
qualify_p.add_argument(
    "--tasks-root",
    default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)

capture_p = sub.add_parser(
    "capture", help="turn a fixing commit into a task (winnable by construction)"
)
capture_p.add_argument("--revert", required=True, help="the fixing commit SHA")
capture_p.add_argument("--repo", default=".", help="source repository (default: cwd)")
capture_p.add_argument("--name", help="task name (default: slug of the fix subject)")
capture_p.add_argument("--contract", help="task contract (default: fix subject)")
capture_p.add_argument(
    "--output", default="tasks", help="output directory (default: ./tasks)"
)

attempt_p = sub.add_parser(
    "attempt", help="run an attempt command, preserve patch + transcript, grade offline"
)
attempt_p.add_argument("task", help="task name")
attempt_p.add_argument(
    "--tasks-root",
    default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)
attempt_p.add_argument(
    "--attempt-timeout",
    type=positive_finite_timeout,
    default=None,
    help="whole-attempt timeout in seconds (default: off)",
)
attempt_p.add_argument(
    "--output",
    default="attempts",
    help="attempt output directory (default: ./attempts)",
)
attempt_p.add_argument(
    "--rung",
    default=None,
    help="contract rung key from the task manifest (default: the task contract)",
)
attempt_p.add_argument(
    "--max-repeated-calls",
    type=positive_int,
    default=None,
    help="stop a cell after N identical consecutive tool calls (default: off; a spending rule, recorded on the attempt record)",
)
attempt_p.add_argument(
    "--timeout",
    type=positive_finite_timeout,
    default=DEFAULT_TIMEOUT,
    help=f"command timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
)
attempt_p.add_argument(
    "--run-record",
    default=None,
    help="run record JSON whose token_budget and turn_budget stop the cell (default: no budget)",
)

run_p = sub.add_parser("run", help="run an attempt command n times and write a summary")
run_p.add_argument("task", help="task name")
run_p.add_argument(
    "--n", type=positive_int, required=True, help="planned attempts per run"
)
run_p.add_argument(
    "--attempt-timeout",
    type=positive_finite_timeout,
    default=None,
    help="whole-attempt timeout in seconds (default: off)",
)
run_p.add_argument(
    "--tasks-root",
    default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)
run_p.add_argument(
    "--output", default="runs", help="run output directory (default: ./runs)"
)
run_p.add_argument(
    "--rung",
    default=None,
    help="contract rung key from the task manifest (default: the task contract)",
)
run_p.add_argument(
    "--max-repeated-calls",
    type=positive_int,
    default=None,
    help="stop a cell after N identical consecutive tool calls (default: off; a spending rule, recorded on the attempt record)",
)
run_p.add_argument(
    "--timeout",
    type=positive_finite_timeout,
    default=DEFAULT_TIMEOUT,
    help=f"command timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
)
run_p.add_argument(
    "--run-record",
    default=None,
    help="run record JSON whose token_budget and turn_budget stop each cell (default: no budget)",
)

summarize_p = sub.add_parser(
    "summarize", help="rebuild summary.json for a run output directory"
)
summarize_p.add_argument("output", help="run output directory")
summarize_p.add_argument(
    "--tasks-root",
    default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)

regrade_p = sub.add_parser(
    "regrade", help="re-grade a preserved attempt and rewrite its record"
)
regrade_p.add_argument("attempt_dir", help="attempt directory (holds attempt.json)")
regrade_p.add_argument(
    "--tasks-root",
    default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)

session_p = sub.add_parser(
    "session",
    help="send ordered prompts to one conversation, snapshot checkpoints, grade offline",
)
session_p.add_argument("task", help="task name")
session_p.add_argument(
    "--tasks-root",
    default=str(DEFAULT_TASKS_ROOT),
    help="task root (default: bundled tasks)",
)
session_p.add_argument(
    "--output",
    default="sessions",
    help="session output directory (default: ./sessions)",
)
session_p.add_argument(
    "--start-timeout",
    type=positive_finite_timeout,
    default=60.0,
    help="seconds to wait for session_started (default: 60)",
)
session_p.add_argument(
    "--step-timeout",
    type=positive_finite_timeout,
    default=600.0,
    help="seconds to wait for one prompt (default: 600)",
)
session_p.add_argument(
    "--close-timeout",
    type=positive_finite_timeout,
    default=30.0,
    help="seconds for graceful adapter close (default: 30)",
)
session_p.add_argument(
    "--session-spec",
    default=DEFAULT_SESSION_SPEC,
    help=(
        "spec file inside the task directory to load "
        f"(default: {DEFAULT_SESSION_SPEC}; must be a bare *.json filename)"
    ),
)

launch_p = sub.add_parser(
    "launch", help="check a run record, or preflight the cell user for an isolated one (cells are Phase 2c)"
)
launch_p.add_argument("--check", default=None, help="run record JSON path to check")
launch_p.add_argument("--preflight", default=None, help="isolated run record JSON path to preflight the cell for")
launch_p.add_argument("--arm", default=None, help="arm JSON the preflight pins pi against")
launch_p.add_argument("--no-hunt", action="store_true", help="skip the root-anchored find (minutes)")
launch_p.add_argument(
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
)

build_census_parser(sub)
