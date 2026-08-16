import json

import pytest

from satyrn_evals import oracle_hook


class FakeReport:
    def __init__(
        self, nodeid: str, when: str, passed=False, failed=False, skipped=False
    ) -> None:
        self.nodeid = nodeid
        self.when = when
        self.passed = passed
        self.failed = failed
        self.skipped = skipped


@pytest.fixture(autouse=True)
def _clear_reports() -> None:
    oracle_hook._reports.clear()
    yield
    oracle_hook._reports.clear()


def _report(nodeid: str, when: str, passed=False, failed=False, skipped=False) -> FakeReport:
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
