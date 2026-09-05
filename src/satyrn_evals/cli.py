"""Console entry point: satyrn-evals grade, capture, and attempt."""

import argparse
import math
import sys
from pathlib import Path

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
from satyrn_evals.capture import capture
from satyrn_evals.capture_record import CaptureOutcome
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, resolve_task
from satyrn_evals.rescore import regrade_attempt, summarize_output
from satyrn_evals.run import run
from satyrn_evals.session import run_session
from satyrn_evals.session_grader import SessionGrader
from satyrn_evals.session_record import SessionCode
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import DEFAULT_TIMEOUT

_EXIT_CODES: dict[Verdict, int] = {Verdict.PASS: 0, Verdict.FAIL: 0, Verdict.UNAVAILABLE: 3}


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
            record = attempt(
                task=args.task,
                tasks_root=Path(args.tasks_root),
                output=Path(args.output),
                command=command,
                timeout=args.timeout,
            )
            if record.code is AttemptCode.GRADE_FAILED:
                print(f"satyrn-evals: {record.message}", file=sys.stderr)
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
            run(
                task=args.task,
                tasks_root=Path(args.tasks_root),
                output=Path(args.output),
                command=command,
                n=args.n,
                timeout=args.timeout,
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
        if args.command == "grade":
            task_dir = resolve_task(args.task, tasks_root=Path(args.tasks_root))
            receipt = grade(task_dir, Path(args.patch), Path(args.receipt))
            return _EXIT_CODES[receipt.verdict]
        if args.command == "summarize":
            summarize_output(
                Path(args.output), tasks_root=Path(args.tasks_root)
            )
            return 0
        if args.command == "regrade":
            if regrade_attempt(
                Path(args.attempt_dir), tasks_root=Path(args.tasks_root)
            ) is None:
                print(
                    "satyrn-evals: regrade: nothing to grade "
                    "(refusal record)",
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
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
)

capture_p = sub.add_parser(
    "capture", help="turn a fixing commit into a task (winnable by construction)"
)
capture_p.add_argument("--revert", required=True, help="the fixing commit SHA")
capture_p.add_argument("--repo", default=".", help="source repository (default: cwd)")
capture_p.add_argument("--name", help="task name (default: slug of the fix subject)")
capture_p.add_argument("--contract", help="task contract (default: fix subject)")
capture_p.add_argument("--output", default="tasks", help="output directory (default: ./tasks)")

attempt_p = sub.add_parser(
    "attempt", help="run an attempt command, preserve patch + transcript, grade offline"
)
attempt_p.add_argument("task", help="task name")
attempt_p.add_argument(
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
)
attempt_p.add_argument(
    "--output", default="attempts", help="attempt output directory (default: ./attempts)"
)
attempt_p.add_argument(
    "--timeout",
    type=positive_finite_timeout,
    default=DEFAULT_TIMEOUT,
    help=f"command timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
)

run_p = sub.add_parser(
    "run", help="run an attempt command n times and write a summary"
)
run_p.add_argument("task", help="task name")
run_p.add_argument(
    "--n", type=positive_int, default=8, help="attempts per run (default: 8)"
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
    "--timeout",
    type=positive_finite_timeout,
    default=DEFAULT_TIMEOUT,
    help=f"command timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
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
regrade_p.add_argument(
    "attempt_dir", help="attempt directory (holds attempt.json)"
)
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
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
)
session_p.add_argument(
    "--output", default="sessions", help="session output directory (default: ./sessions)"
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
