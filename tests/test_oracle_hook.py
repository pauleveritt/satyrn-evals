import json
from collections.abc import Iterator

import pytest

from satyrn_evals import oracle_hook


class FakeReport:
    def __init__(
        self, nodeid: str, when: str = "call", passed=False, failed=False, skipped=False,
        longrepr: str = "",
    ) -> None:
        self.nodeid = nodeid
        self.when = when
        self.passed = passed
        self.failed = failed
        self.skipped = skipped
        self.longrepr = longrepr


@pytest.fixture(autouse=True)
def _clear_reports() -> Iterator[None]:
    oracle_hook._reports.clear()
    oracle_hook._collect_errors.clear()
    yield
    oracle_hook._reports.clear()
    oracle_hook._collect_errors.clear()


def _report(nodeid: str, when: str = "call", passed=False, failed=False, skipped=False) -> FakeReport:
    return FakeReport(nodeid=nodeid, when=when, passed=passed, failed=failed, skipped=skipped)


def test_hook_writes_result_json(tmp_path, monkeypatch) -> None:
    result_path = tmp_path / "hook.json"
    monkeypatch.setenv(oracle_hook.RESULT_ENV, str(result_path))
    oracle_hook.pytest_runtest_logreport(_report("a::t1", "call", passed=True))
    oracle_hook.pytest_runtest_logreport(_report("a::t2", "call", failed=True))
    oracle_hook.pytest_sessionfinish(None, 1)
    data = json.loads(result_path.read_text())
    assert data["executed_test_ids"] == ["a::t1", "a::t2"]
    assert data["outcomes"] == {"a::t1": "passed", "a::t2": "failed"}
    assert data["counts"]["passed"] == 1
    assert data["counts"]["failed"] == 1
    assert data["counts"]["error"] == 0
    assert data["counts"]["skipped"] == 0


def test_hook_records_setup_failure_as_error(tmp_path, monkeypatch) -> None:
    result_path = tmp_path / "hook.json"
    monkeypatch.setenv(oracle_hook.RESULT_ENV, str(result_path))
    oracle_hook.pytest_runtest_logreport(_report("a::t3", "setup", failed=True))
    oracle_hook.pytest_sessionfinish(None, 1)
    data = json.loads(result_path.read_text())
    assert data["outcomes"] == {"a::t3": "error"}


def test_hook_is_inert_without_env(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(oracle_hook.RESULT_ENV, raising=False)
    oracle_hook.pytest_sessionfinish(None, 0)  # must not raise, must not write
    assert not (tmp_path / "hook.json").exists()


def test_hook_records_collection_error(tmp_path, monkeypatch) -> None:
    result_path = tmp_path / "hook.json"
    monkeypatch.setenv(oracle_hook.RESULT_ENV, str(result_path))
    oracle_hook.pytest_collectreport(
        FakeReport("broken_import_test.py", failed=True, longrepr="ModuleNotFoundError: nope")
    )
    oracle_hook.pytest_sessionfinish(None, 2)
    data = json.loads(result_path.read_text())
    assert data["collect_errors"] == ["ModuleNotFoundError: nope"]
    assert data["executed_test_ids"] == []


def test_hook_collect_errors_empty_by_default(tmp_path, monkeypatch) -> None:
    result_path = tmp_path / "hook.json"
    monkeypatch.setenv(oracle_hook.RESULT_ENV, str(result_path))
    oracle_hook.pytest_runtest_logreport(_report("a::t1", passed=True))
    oracle_hook.pytest_sessionfinish(None, 0)
    data = json.loads(result_path.read_text())
    assert data["collect_errors"] == []


def test_hook_ignores_successful_collection_report() -> None:
    oracle_hook.pytest_collectreport(FakeReport("a.py", passed=True))
    assert oracle_hook._collect_errors == []


def test_hook_records_call_and_teardown_skips() -> None:
    oracle_hook.pytest_runtest_logreport(_report("a::call_skip", skipped=True))
    oracle_hook.pytest_runtest_logreport(_report("a::teardown_skip", "teardown", skipped=True))
    oracle_hook.pytest_runtest_logreport(_report("a::setup_pass", "setup", passed=True))
    assert oracle_hook._reports == {
        "a::call_skip": "skipped",
        "a::teardown_skip": "skipped",
    }
