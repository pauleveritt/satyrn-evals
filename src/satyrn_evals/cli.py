"""Console entry point: satyrn-evals grade, capture, and attempt."""

import argparse
import sys
from pathlib import Path

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptOutcome
from satyrn_evals.capture import capture
from satyrn_evals.capture_record import CaptureOutcome
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, resolve_task
from satyrn_evals.verdict import Verdict

_EXIT_CODES: dict[Verdict, int] = {Verdict.PASS: 0, Verdict.FAIL: 0, Verdict.UNAVAILABLE: 3}


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
            )
            if record.outcome is AttemptOutcome.REFUSED:
                return 3
            return 0 if record.verdict in (Verdict.PASS, Verdict.FAIL) else 3
        args = parser.parse_args(argv)
        if args.command == "grade":
            task_dir = resolve_task(args.task, tasks_root=Path(args.tasks_root))
            receipt = grade(task_dir, Path(args.patch), Path(args.receipt))
            return _EXIT_CODES[receipt.verdict]
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
