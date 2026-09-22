"""Pytest plugin: writes the hook result JSON the grader trusts.

Loaded with `-p satyrn_evals.oracle_hook` by the task's oracle command.
Inert unless SATYRN_ORACLE_RESULT is set (i.e., only during grading).
"""

import json
import os
from pathlib import Path

from satyrn_evals.verdict import HookResultData, Outcome

RESULT_ENV = "SATYRN_ORACLE_RESULT"

_reports: dict[str, Outcome] = {}
_collect_errors: list[str] = []


def pytest_collectreport(report) -> None:
    if report.failed:
        _collect_errors.append(str(report.longrepr))


def pytest_runtest_logreport(report) -> None:
    match (report.when, report.passed, report.failed, report.skipped):
        case ("call", True, _, _):
            _reports[report.nodeid] = "passed"
        case ("call", _, _, True):
            _reports[report.nodeid] = "skipped"
        case ("call", _, _, _):
            _reports[report.nodeid] = "failed"
        case (_, _, True, _):
            _reports[report.nodeid] = "error"
        case (_, _, _, True):
            _reports[report.nodeid] = "skipped"


def pytest_sessionfinish(session, exitstatus) -> None:
    if not (path := os.environ.get(RESULT_ENV)):
        return
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for outcome in _reports.values():
        counts[outcome] += 1
    data: HookResultData = {
        "executed_test_ids": sorted(_reports),
        "outcomes": dict(_reports),
        "counts": counts,
        "collect_errors": list(_collect_errors),
    }
    Path(path).write_text(json.dumps(data))
