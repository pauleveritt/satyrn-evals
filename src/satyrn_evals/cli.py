"""Console entry point: satyrn-evals grade, capture, and attempt."""

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

from satyrn_evals.arms import load_arm
from satyrn_evals.attempt import attempt, resolve_contract
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
from satyrn_evals.budget import AttemptBudget, LineBudget
from satyrn_evals.capture import capture
from satyrn_evals.capture_record import CaptureOutcome
from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, Isolation
from satyrn_evals.cell_engine import arm_export, arm_export_problems, export_engine
from satyrn_evals.cell_preflight import preflight_cell
from satyrn_evals.census import build_arg_parser as build_census_parser
from satyrn_evals.census import run_cli as run_census
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.launch_record import (
    DEFAULT_RUNS_ROOT,
    launch_record,
    model_server_checks,
)
from satyrn_evals.line_grade import (
    LINE_GRADE_NEEDS_REVIEW_EXIT_CODE,
    default_out_path,
    grade_night,
    refuse_project_grade_root,
    render_summary,
    write_report,
)
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest, resolve_task
from satyrn_evals.qualify import qualify
from satyrn_evals.rescore import regrade_attempt, summarize_output
from satyrn_evals.run import run
from satyrn_evals.run_record import (
    DEFAULT_COMMAND_BACKSTOP_S,
    K_VALUES,
    PURPOSES,
    RunRecordError,
    attempt_budget,
    check_invocation,
    gate,
    load_run_record,
    new_record,
    record_arms,
    write_new_record,
)
from satyrn_evals.run_record import (
    line_budget as record_line_budget,
)
from satyrn_evals.session import run_session
from satyrn_evals.session_grader import SessionGrader
from satyrn_evals.session_manifest import DEFAULT_SESSION_SPEC
from satyrn_evals.session_record import SessionCode
from satyrn_evals.task_selftest import engine_self_test, task_self_test
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
) -> tuple[AttemptBudget | None, Isolation, LineBudget | None]:
    """The budget, profile, and declared line a run record froze, after the same
    gate ``launch --check`` runs and after checking the invocation (task, tree,
    arm, model, and — for ``run`` — ``--n``) is the record's.

    Without a record: no budget, the local profile, no declared line. With a
    record, the declared line (if any) is extracted the same way
    ``launch_cell.run_cell`` builds one from a launch spec: via
    ``run_record.line_budget``, never reimplemented here.
    """
    if run_record is None:
        return None, Isolation.LOCAL, None
    record = load_run_record(Path(run_record))
    gate(record, previous_result_committed=_previous_result_committed(record))
    check_invocation(
        record, task=task, task_dir=resolve_task(task, tasks_root=Path(tasks_root)), command=command
    )
    if n is not None and n != record.n:
        raise RunRecordError(f"the record asks n={record.n}; --n {n} disagrees")
    return attempt_budget(record), record.isolation, record_line_budget(record)


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
            budget, isolation, line_budget = _record_settings(
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
                line_budget=line_budget,
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
            budget, isolation, line_budget = _record_settings(
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
                line_budget=line_budget,
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
            if args.record is not None:
                if args.check is not None:
                    raise UsageError("launch takes RECORD or --check RECORD, not both")
                return launch_record(
                    Path(args.record), [Path(path) for path in args.arm or []], tasks_root=Path(args.tasks_root),
                    runs_root=Path(args.runs_root), timeout=args.timeout, attempt_timeout=args.attempt_timeout,
                    hunt=not args.no_hunt, settings=not args.no_settings,
                )
            if args.check is None:
                print("launch: RECORD --arm ARM.json, --check RECORD, or --preflight RECORD --arm ARM.json", file=sys.stderr)
                return UsageError.exit_code
            record = load_run_record(Path(args.check))
            gate(record, previous_result_committed=_previous_result_committed(record))
            print("launch: record accepted")
            return 0
        if args.command == "record":
            return _record_new(args)
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
        if args.command == "grade-line":
            grade_root = Path(args.grade_root)
            refuse_project_grade_root(grade_root)
            grade_root.mkdir(parents=True, exist_ok=True)
            night = Path(args.night)
            run_record = load_run_record(Path(args.record))
            tasks_root = Path(args.tasks_root) if args.tasks_root is not None else None
            report = grade_night(night, run_record, grade_root, tasks_root=tasks_root)
            out_path = Path(args.out) if args.out is not None else default_out_path(grade_root, night)
            write_report(report, out_path)
            print(render_summary(report))
            # N5: a broken-record row (unclassified code, or a BUDGET_EXCEEDED
            # cell that never crossed a declared line) must not exit clean --
            # the full report is written and printed above either way, and
            # this is the only signal a human needs to look at it directly.
            if any(row.line_unavailable_reason is not None for row in report.rows):
                return LINE_GRADE_NEEDS_REVIEW_EXIT_CODE
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
    """The isolated sitting's cell checks, for every arm the record runs; the JSON report goes to stdout, each problem to stderr."""
    record = load_run_record(Path(args.preflight))
    if record.isolation is not Isolation.ISOLATED:
        raise RunRecordError(f"launch --preflight checks the cell user; {args.preflight} is a local record")
    if not args.arm:
        raise UsageError("launch --preflight needs --arm ARM.json, one per arm the record runs")
    names = record_arms(record)
    loaded: dict[str, object] = {}
    for arm_path in args.arm:
        arm = load_arm(Path(arm_path))
        if arm.arm in loaded:
            raise RunRecordError(f"--arm names {arm.arm} twice")
        if arm.model != record.model:
            raise RunRecordError(
                f"arm file {arm_path} is {arm.arm} on {arm.model}; the record is {record.arm} on {record.model}"
            )
        loaded[arm.arm] = arm
    if sorted(loaded) != sorted(names):
        raise RunRecordError(
            f"the record runs {record.arm}; the --arm files are {'+'.join(sorted(loaded)) or 'none'}"
        )
    # Canonical, record-declared order: the order of --arm flags on the command
    # line must not matter to what gets checked or how it is keyed below.
    arms = [loaded[name] for name in names]
    tasks_root = Path(args.tasks_root)
    report = preflight_cell(
        pinned_pi=arms[0].pins.pi,
        protected=(Path.cwd(), tasks_root, Path.home()),
        tasks_root=tasks_root,
        hunt_root=None if args.no_hunt else "/",
    )
    problems = list(report.problems)
    pins = {arm.pins.pi for arm in arms}
    if len(pins) != 1:
        problems.append(f"the arms pin different pi versions: {', '.join(sorted(pins))}")
    for name, arm in zip(names, arms, strict=True):
        problems += [f"{name}: {problem}" for problem in arm_export_problems(arm)]
    checked: dict[str, object] = dict(report.checked)
    # The task's own self-test, and the Engine's derived self-test, on the base
    # and the known-good state: the check the void night lacked, run here for
    # every arm the record runs so the operator can preflight every record
    # before the night (this path does not gate the record's chain, so all
    # three records can be checked up front).
    task_dir = resolve_task(record.task, tasks_root=tasks_root)
    manifest = load_manifest(task_dir)
    _, contract_text = resolve_contract(manifest, record.rung)
    task_check = task_self_test(task_dir, manifest)
    problems += [f"task self-test: {problem}" for problem in task_check.problems]
    checked["task_self_test"] = task_check.checked
    for name, arm in zip(names, arms, strict=True):
        export = arm_export(arm)
        if export is None:
            continue
        engine_check = engine_self_test(
            task_dir, manifest,
            engine=("uv", "run", "--no-sync", "--project", os.fspath(export), "satyrn-engine"),
            request=contract_text, token_budget=record.token_budget, turn_budget=record.turn_budget,
        )
        problems += [f"{name} engine self-test: {problem}" for problem in engine_check.problems]
        checked[f"{name}_engine_self_test"] = engine_check.checked
    if not os.environ.get(CELL_PATH_PREFIX_ENV):
        # Same check, same skip rule as `launch_record`'s: a real preflight run
        # never carries the test PATH seam (flagged just below when it does),
        # so this only ever skips there, never for a record this path accepts.
        server_problems, checked["model_server"] = model_server_checks(arms, record.isolation)
        problems += server_problems
    if os.environ.get(CELL_PATH_PREFIX_ENV):
        problems.append(f"{CELL_PATH_PREFIX_ENV} is set; it is a test seam, never a sitting's PATH")
    print(json.dumps({"record": args.preflight, "arm": args.arm, "problems": problems, **checked}, indent=2))
    for problem in problems:
        print(f"launch preflight FAILED: {problem}", file=sys.stderr)
    return 1 if problems else 0


def _record_new(args: argparse.Namespace) -> int:
    """Write one run record from flags, read it back through the loader and gate, print its path."""
    body = new_record(
        task=args.task, tasks_root=Path(args.tasks_root), arm=args.arm, model=args.model, n=args.n, k=args.k,
        rung=None if args.rung == "contract" else args.rung, purpose=args.purpose, isolation=args.isolation,
        mode=args.mode, max_minutes=args.max_minutes, command_backstop_s=args.command_backstop,
        token_budget=args.token_budget,
        turn_budget=args.turn_budget, previous_result=args.previous_result, authority=args.authority,
        decision_rule=args.decision_rule,
        line_token_budget=args.line_token_budget, line_turn_budget=args.line_turn_budget,
    )
    write_new_record(Path(args.output), body)
    print(f"record: wrote {args.output} (task_tree_sha256 {body['task_tree_sha256']}); commit it before launch")
    return 0


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

grade_line_p = sub.add_parser(
    "grade-line",
    help=(
        "grade a night's harvested declared-line patches offline, per completed cell; "
        f"exits {LINE_GRADE_NEEDS_REVIEW_EXIT_CODE} (after writing the full report) when any "
        "cell is a broken record needing a human look"
    ),
)
grade_line_p.add_argument("night", help="night output directory (holds slots/ and one directory per arm)")
grade_line_p.add_argument("--record", required=True, help="the run record the night was launched from")
grade_line_p.add_argument(
    "--grade-root",
    required=True,
    help="scratch root for offline grading; must not sit under a Python project",
)
grade_line_p.add_argument(
    "--out",
    default=None,
    help="write the JSON report here (default: <grade-root>/grade-line-<night>.json)",
)
grade_line_p.add_argument(
    "--tasks-root",
    default=None,
    help="task root for the offline grade (default: bundled tasks)",
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
    "launch", help="run a frozen record's cells; or check a record, or preflight the cell user for one"
)
launch_p.add_argument("record", nargs="?", default=None, help="frozen run record JSON whose cells to run")
launch_p.add_argument("--check", default=None, help="run record JSON path to check")
launch_p.add_argument("--preflight", default=None, help="isolated run record JSON path to preflight the cell for")
launch_p.add_argument("--arm", action="append", default=None, help="arm JSON, once per arm the record runs")
launch_p.add_argument("--no-hunt", action="store_true", help="skip the root-anchored find (development records only)")
launch_p.add_argument("--no-settings", action="store_true", help="skip preflight_settings (development records only)")
launch_p.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="where the night directory lives")
launch_p.add_argument(
    "--timeout", type=positive_finite_timeout, default=None,
    help="override the record's command_backstop_s, seconds (development records only)",
)
launch_p.add_argument(
    "--attempt-timeout", type=positive_finite_timeout, default=None,
    help="override the record's attempt deadline, seconds (development records only)",
)
launch_p.add_argument(
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
)

record_p = sub.add_parser("record", help="write a run record the launcher accepts")
record_sub = record_p.add_subparsers(dest="record_command", required=True)
record_new_p = record_sub.add_parser("new", help="write a new run record from flags; never overwrites")
record_new_p.add_argument("--output", required=True, help="record path to create (e.g. records/NAME.json)")
record_new_p.add_argument("--task", required=True, help="task name")
record_new_p.add_argument("--arm", required=True, help="arm, or arms joined by + to interleave (baseline+engine)")
record_new_p.add_argument(
    "--rung", required=True,
    help="contract rung key from the task manifest (R1, R1-plan), or contract for its default text",
)
record_new_p.add_argument("--n", type=positive_int, required=True, help="cells per arm")
record_new_p.add_argument("--k", type=int, choices=K_VALUES, required=True, help="cells at a time")
record_new_p.add_argument("--purpose", required=True, choices=sorted(PURPOSES))
record_new_p.add_argument("--isolation", default="isolated", choices=["isolated", "local"])
record_new_p.add_argument("--model", default="omlx/Ornith-1.5-9B-MLX-8bit")
record_new_p.add_argument("--mode", default="attended", choices=["attended", "batch"])
record_new_p.add_argument("--max-minutes", type=positive_int, default=60)
record_new_p.add_argument(
    "--command-backstop", type=positive_int, default=DEFAULT_COMMAND_BACKSTOP_S,
    help="per-attempt-command wall-clock backstop, seconds",
)
record_new_p.add_argument("--token-budget", type=positive_int, default=32000)
record_new_p.add_argument("--turn-budget", type=positive_int, default=48)
record_new_p.add_argument(
    "--line-token-budget", type=positive_int, default=None,
    help="declared line: output tokens, strictly below --token-budget (requires --line-turn-budget too)",
)
record_new_p.add_argument(
    "--line-turn-budget", type=positive_int, default=None,
    help="declared line: turns, strictly below --turn-budget (requires --line-token-budget too)",
)
record_new_p.add_argument("--previous-result", default=None, help="the committed result this record follows")
record_new_p.add_argument("--authority", default=None, help="who authorized this spend, and when")
record_new_p.add_argument("--decision-rule", default=None, help="required unless purpose is admission or development")
record_new_p.add_argument(
    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
)

build_census_parser(sub)
