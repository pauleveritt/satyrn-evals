"""Roadmap row 2c: records run through the launcher under isolation, against a fake ``pi``.

Real launcher, real cell processes, real sudo, git and harness; ``pi`` is
`fake_pi_build.py` run as the cell user. Records are written with
``record new`` and committed in a scratch repository, so the frozen gate is
the real one. Every record here is ``purpose: development`` (the only purpose
the test PATH seam and ``--no-settings`` are allowed for). No model runs.
"""

import http.server
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from integration.cell_support import cell_process_alive
from integration.test_attempt import (
    _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
)
from integration.test_isolated_arms import _cell_pi  # type: ignore[missing-import]
from satyrn_evals.arms import load_arm
from satyrn_evals.attempt_engine import RECEIPT_NAME
from satyrn_evals.cell import CELLS_ROOT
from satyrn_evals.cell_engine import export_engine
from satyrn_evals.cli import main
from satyrn_evals.launch import LEDGER_NAME
from satyrn_evals.model_server import model_server_problems
from satyrn_evals.summary import SUMMARY_NAME

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
ENGINE_ARM = Path(__file__).resolve().parents[2] / "arms" / "engine-ornith15-9b.json"
ENTRY = "import sys; from satyrn_evals.cli import main; sys.exit(main())"


def _git(repo: Path, *argv: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *argv], cwd=repo, check=True, capture_output=True)


def _frozen_record(
    tmp_path: Path, name: str, *, arm: str, n: int, k: int, max_minutes: int = 60, model: str = "omlx/fixture",
    command_backstop_s: int | None = None,
) -> Path:
    repo = tmp_path / "records"
    if not (repo / ".git").exists():
        repo.mkdir()
        _git(repo, "init", "-q")
    path = repo / f"{name}.json"
    argv = [
        "record", "new", "--output", str(path), "--task", "calc-build", "--tasks-root", str(TASKS), "--arm", arm,
        "--rung", "contract", "--n", str(n), "--k", str(k), "--purpose", "development",
        "--max-minutes", str(max_minutes), "--model", model,
    ]
    if command_backstop_s is not None:
        argv += ["--command-backstop", str(command_backstop_s)]
    assert main(argv) == 0
    _git(repo, "add", path.name)
    _git(repo, "commit", "-qm", name)
    return path


def _arm_file(tmp_path: Path, name: str, argv: list[str]) -> Path:
    body = {
        "arm": name, "argv": argv, "tools": ["read", "bash", "edit", "write"], "model": "omlx/fixture",
        "server_model": "fixture",
        "pins": {"pi": "0.85.1", "engine_commit": None, "digests": {}},
    }
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(body))
    return path


def _engine_arm(tmp_path: Path, export: Path, *, model: str | None = None) -> Path:
    """The committed Engine arm, byte for byte but for its export path (a scratch export of the same commit)
    and, for a record interleaved with the fixture Baseline, its model."""
    body = json.loads(ENGINE_ARM.read_text())
    repo = body["argv"].index("--engine-repo") + 1
    body["argv"][repo] = os.fspath(export)
    if model is not None:
        body["model"], body["server_model"] = model, model.split("/", 1)[1]
    path = tmp_path / "engine.json"
    path.write_text(json.dumps(body))
    return path


def _pinned_export(cell_scratch: Path) -> Path:
    commit = load_arm(ENGINE_ARM).pins.engine_commit
    assert commit is not None
    return export_engine(_engine_repo(), commit, root=cell_scratch)


def _baseline_arm(tmp_path: Path) -> Path:
    return _arm_file(tmp_path, "baseline", [sys.executable, "-m", "satyrn_evals.attempt_pi"])


def _launch(record: Path, arms: list[Path], runs: Path, *extra: str) -> int:
    argv = ["launch", str(record), "--tasks-root", str(TASKS), "--runs-root", str(runs), "--no-hunt", "--no-settings"]
    for arm in arms:
        argv += ["--arm", str(arm)]
    return main([*argv, "--timeout", "120", "--attempt-timeout", "300", *extra])


def _attempt_dirs() -> set[str]:
    return {p.name for p in CELLS_ROOT.iterdir() if p.name.startswith("satyrn-attempt-")}


def _result(record: Path) -> dict:
    return json.loads(record.with_suffix(".result.json").read_text())


def test_a_fake_completes_a_k2_interleaved_record_under_isolation_through_the_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "write")  # the Engine arm's deliver commits; Baseline's harvest takes the files
    engine = _engine_arm(tmp_path, _pinned_export(cell_scratch), model="omlx/fixture")
    record = _frozen_record(tmp_path, "interleaved", arm="baseline+engine", n=2, k=2)
    before = _attempt_dirs()
    assert _launch(record, [_baseline_arm(tmp_path), engine], tmp_path / "runs") == 0
    result = _result(record)
    assert result["status"] == "complete" and result["k"] == 2
    assert [(c["slot"], c["arm"]) for c in result["cells"]] == [(0, "baseline"), (1, "engine"), (2, "baseline"), (3, "engine")]
    for arm in ("baseline", "engine"):
        assert result["arms"][arm]["passes"] == 2 and result["arms"][arm]["code_counts"] == {"OK": 2}
        summary = json.loads((tmp_path / "runs" / "interleaved" / arm / SUMMARY_NAME).read_text())
        assert summary["n"] == 2 and summary["verdict_counts"]["pass"] == 2
    assert _attempt_dirs() <= before


def test_the_committed_engine_arm_completes_a_route_proof_shaped_record_under_isolation_through_the_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    """Phase 3's route-proof cell against a fake: one Engine cell, k = 1, the committed arm on the record's model,
    its export checked against its pins, the receipt kept. ``development`` only because the fake ``pi`` is a seam."""
    _cell_pi(cell_scratch, monkeypatch, "write")
    engine = _engine_arm(tmp_path, _pinned_export(cell_scratch))
    record = _frozen_record(tmp_path, "route-proof", arm="engine", n=1, k=1, model="omlx/Ornith-1.5-9B-MLX-8bit")
    before = _attempt_dirs()
    assert _launch(record, [engine], tmp_path / "runs") == 0
    result = _result(record)
    assert result["status"] == "complete" and [(c["arm"], c["code"], c["verdict"]) for c in result["cells"]] == [
        ("engine", "OK", "pass")
    ]
    receipt = json.loads((tmp_path / "runs" / "route-proof" / "engine" / result["cells"][0]["attempt_dir"] / RECEIPT_NAME).read_text())
    assert (receipt["code"], receipt["validation"]) == ("OK", "passed")
    assert set(receipt["guard_firings"]) >= {"scope_refused", "symbol_preserved", "command_bounded"}
    ledger = json.loads((tmp_path / "runs" / "route-proof" / LEDGER_NAME).read_text())
    assert ledger["sittings"][0]["preflight"]["tolerated"] == [os.fspath(cell_scratch)]
    assert _attempt_dirs() <= before


def test_a_night_the_wall_clock_stops_resumes_without_rerunning_a_finished_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "commit")
    record = _frozen_record(tmp_path, "resume", arm="baseline", n=2, k=1, max_minutes=6, command_backstop_s=60)
    arms, runs = [_baseline_arm(tmp_path)], tmp_path / "runs"
    # A 359 s deadline leaves the six-minute record room for exactly one cell: once the first
    # cell has taken any time at all, the second 359 s cell no longer fits in the 360 s wall clock.
    assert _launch(record, arms, runs, "--attempt-timeout", "359") == 4
    first = _result(record)
    assert first["status"] == "capped" and [c["slot"] for c in first["cells"]] == [0]
    assert _launch(record, arms, runs, "--attempt-timeout", "359") == 0
    second = _result(record)
    assert second["status"] == "complete" and [c["slot"] for c in second["cells"]] == [0, 1]
    assert second["cells"][0]["attempt_dir"] == first["cells"][0]["attempt_dir"]
    assert [s["status"] for s in second["sittings"]] == ["capped", "complete"]
    assert json.loads((runs / "resume" / "baseline" / SUMMARY_NAME).read_text())["n"] == 2


def test_an_unreachable_server_stops_the_night_and_the_next_launch_replaces_that_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "unreachable")
    record = _frozen_record(tmp_path, "infra", arm="baseline", n=2, k=1)
    arms, runs = [_baseline_arm(tmp_path)], tmp_path / "runs"
    assert _launch(record, arms, runs) == 3
    stopped = _result(record)
    assert stopped["status"] == "infrastructure"
    assert stopped["reason"].startswith("slot 00 (baseline): MODEL_ERROR") and "Connection error." in stopped["reason"]
    assert [c["slot"] for c in stopped["cells"]] == [0]  # slot 1 never started
    (cell_scratch / "bin" / "pi").write_text((cell_scratch / "bin" / "pi").read_text().replace("unreachable", "commit"))
    assert _launch(record, arms, runs) == 0
    resumed = _result(record)
    assert resumed["status"] == "complete" and [c["code"] for c in resumed["cells"]] == ["OK", "OK"]
    assert [r["code"] for r in resumed["replaced"]] == ["MODEL_ERROR"]
    assert resumed["replaced"][0]["attempt_dir"] != resumed["cells"][0]["attempt_dir"]


def test_the_launcher_refuses_a_record_that_is_not_committed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "commit")
    record = _frozen_record(tmp_path, "edited", arm="baseline", n=1, k=1)
    record.write_text(record.read_text().replace('"n": 1', '"n": 2'))
    assert _launch(record, [_baseline_arm(tmp_path)], tmp_path / "runs") == 2
    assert not (tmp_path / "runs" / "edited").exists()


def test_sigterm_stops_the_launcher_and_its_running_cell_leaves_no_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    pidfile = _cell_pi(cell_scratch, monkeypatch, "trickle")
    record = _frozen_record(tmp_path, "signal", arm="baseline", n=2, k=1)
    runs = tmp_path / "runs"
    before = _attempt_dirs()
    launcher = subprocess.Popen([
        sys.executable, "-c", ENTRY, "launch", str(record), "--tasks-root", str(TASKS), "--runs-root", str(runs),
        "--no-hunt", "--no-settings", "--arm", str(_baseline_arm(tmp_path)), "--timeout", "120", "--attempt-timeout", "300",
    ])
    try:
        stop = time.monotonic() + 60
        while not pidfile.exists() and time.monotonic() < stop:
            time.sleep(0.2)
        assert pidfile.exists(), "the fake pi never started"
        launcher.send_signal(signal.SIGTERM)
        assert launcher.wait(timeout=90) == 3
    finally:
        if launcher.poll() is None:
            launcher.kill()
    pid = int(pidfile.read_text())
    stop = time.monotonic() + 15
    while cell_process_alive(pid) and time.monotonic() < stop:
        time.sleep(0.1)
    assert not cell_process_alive(pid), f"fake pi {pid} outlived the launcher"
    ledger = json.loads((runs / "signal" / LEDGER_NAME).read_text())
    assert ledger["status"] == "interrupted" and "SignalAbort: SIGTERM" in ledger["reason"]
    assert ledger["slots"] == []
    assert _attempt_dirs() <= before


# --- model_server_problems: a real local stub, both directions -------------


class _ModelsHandler(http.server.BaseHTTPRequestHandler):
    """Answers ``GET /v1/models`` with whatever ``server_class.served`` names."""

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's naming
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"data": [{"id": self.server.served}]}).encode()  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # quiet: this is a test fixture, not a server under test
        pass


def test_model_server_problems_against_a_real_local_stub_http_server() -> None:
    """Both directions, against a real socket rather than a faked ``urlopen``: a server that lists
    the model is clean, the same server naming a different model is not, and once it stops
    listening the same URL is unreachable -- the exact port `launch_record`'s default tier never
    dials (`_facts().model_server` fakes this everywhere else)."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _ModelsHandler)
    server.served = "Ornith-1.5-9B-MLX-8bit"  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        assert model_server_problems(base_url, "Ornith-1.5-9B-MLX-8bit") == []
        assert model_server_problems(base_url, "some-other-model") == [
            f"the model server at {base_url} does not serve some-other-model"
        ]
    finally:
        server.shutdown()
        thread.join(timeout=5)
    problems = model_server_problems(base_url, "Ornith-1.5-9B-MLX-8bit", timeout=1.0)
    assert len(problems) == 1 and problems[0].startswith(f"the model server at {base_url} is unreachable:")
