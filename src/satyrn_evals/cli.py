"""Console entry point: satyrn-evals grade TASK PATCH [--receipt PATH]."""

import argparse
import sys
from pathlib import Path

from satyrn_evals.errors import SatyrnError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import resolve_task
from satyrn_evals.verdict import Verdict

_EXIT_CODES: dict[Verdict, int] = {Verdict.PASS: 0, Verdict.FAIL: 0, Verdict.UNAVAILABLE: 3}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="satyrn-evals", description="Offline grading for development tasks.")
    sub = parser.add_subparsers(dest="command", required=True)
    grade_p = sub.add_parser("grade", help="apply PATCH to TASK and record the verdict")
    grade_p.add_argument("task", help="bundled task name")
    grade_p.add_argument("patch", help="unified diff file")
    grade_p.add_argument("--receipt", default="receipt.json", help="receipt path (default: receipt.json)")
    args: argparse.Namespace = parser.parse_args(argv)
    try:
        task_dir = resolve_task(args.task)
        receipt = grade(task_dir, Path(args.patch), Path(args.receipt))
        return _EXIT_CODES[receipt.verdict]
    except SatyrnError as e:
        print(f"satyrn-evals: {e}", file=sys.stderr)
        return e.exit_code
