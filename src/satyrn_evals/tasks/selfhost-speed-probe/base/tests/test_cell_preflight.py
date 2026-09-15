"""The isolated sitting's cell preflight, driven by a scripted runner: nothing spawns."""

import json
import pwd
import subprocess
from pathlib import Path

import pytest

from satyrn_evals import cell_preflight
from satyrn_evals import cli as cli_module
from satyrn_evals.cell import CELL_PATH_PREFIX_ENV
from satyrn_evals.cell_preflight import (
    CellPreflight,
    hunt_argv,
    hunt_names,
    preflight_cell,
    stale_cell_processes,
)
from satyrn_evals.cli import main
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

CELL_UID = 560
REPO = Path(__file__).resolve().parent.parent


def test_the_hunt_names_carry_every_bundled_hidden_suite_but_not_its_helpers() -> None:
    names = hunt_names(DEFAULT_TASKS_ROOT)
    assert {"satyrn_evals", "known-good.patch", "known-broken.patch", "test_acceptance.py"} <= set(names)
    assert "test_phase1_home.py" in names  # agentclinic-complaint-lifecycle's hidden suite
    assert "_seed.py" not in names


def test_the_hunt_is_one_root_anchored_find() -> None:
    assert hunt_argv(["a", "b"]) == ["/usr/bin/find", "/", "-xdev", "(", "-name", "a", "-o", "-name", "b", ")", "-print"]


def test_a_leftover_cell_process_is_stale_and_an_os_agent_is_not() -> None:
    ps = (
        "  101 560 /usr/libexec/lsd\n"
        "  102 560 /System/Library/Frameworks/x\n"
        "  103 560 /usr/bin/find / -name x\n"
        "  104 501 /bin/zsh\n"
    )
    assert stale_cell_processes(ps, CELL_UID) == ["103 /usr/bin/find / -name x"]
    assert stale_cell_processes("  101 560 /usr/libexec/lsd\n", CELL_UID) == []


class _Runner:
    """Answers the preflight's commands from a script; records nothing spawns."""

    def __init__(self, *, sudo: int = 0, ps: str = "", readable: str = "", version: str = "0.85.1\n", hits: str = "") -> None:
        self.sudo, self.ps, self.readable, self.version, self.hits = sudo, ps, readable, version, hits

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        text = kwargs.get("text", False)
        if argv[:1] == ["/bin/ps"]:
            out = self.ps
        elif "/usr/bin/true" in argv:
            return subprocess.CompletedProcess(argv, self.sudo, b"", b"sudo: a password is required")
        elif "pi" in argv and "--version" in argv:
            out = self.version
        elif "/usr/bin/find" in argv:
            out = self.hits
        else:
            out = self.readable
        return subprocess.CompletedProcess(argv, 0, out if text else out.encode(), "")


@pytest.fixture(autouse=True)
def _cell_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("satyrn_evals.cell.CELLS_ROOT", tmp_path)
    monkeypatch.setattr(pwd, "getpwnam", lambda name: type("P", (), {"pw_uid": CELL_UID})())


def _preflight(runner: _Runner, hunt_root: str | None = "/") -> CellPreflight:
    return preflight_cell(pinned_pi="0.85.1", protected=(REPO,), hunt_root=hunt_root, run=runner)


def test_a_clean_cell_has_no_problems() -> None:
    report = _preflight(_Runner(ps="  101 560 /usr/libexec/lsd\n"))
    assert report.problems == []
    assert report.checked["pi_version"] == "0.85.1"


def test_each_cell_problem_is_named() -> None:
    report = _preflight(
        _Runner(ps="  103 560 /bin/bash -c sleep 9\n", readable=f"{REPO}\n", version="0.84.4\n", hits="/private/tmp/x/known-good.patch\n")
    )
    assert report.problems == [
        "a cell process is still running: 103 /bin/bash -c sleep 9",
        f"the cell can read {REPO}",
        "the cell's pi --version is 0.84.4, the arm pins 0.85.1",
        "the cell can find /private/tmp/x/known-good.patch",
    ]


def test_skipping_the_hunt_runs_no_find() -> None:
    report = _preflight(_Runner(hits="/private/tmp/x/known-good.patch\n"), hunt_root=None)
    assert report.problems == [] and report.checked["hunt_hits"] == []


def test_a_cell_user_that_is_not_set_up_is_the_only_problem() -> None:
    report = _preflight(_Runner(sudo=1))
    assert len(report.problems) == 1 and "a password is required" in report.problems[0]


# --- launch --preflight -------------------------------------------------------

RECORD = {
    "version": 1, "task": "agentclinic-repair-misleading-locus", "task_tree_sha256": "a" * 64,
    "arm": "baseline", "model": "omlx/Ornith-1.5-9B-MLX-8bit", "condition": "cold", "n": 4,
    "mode": "attended", "max_minutes": 60, "stop_rule": "infrastructure", "decision_rule": "fisher",
    "previous_result": None, "token_budget": 32000, "turn_budget": 48,
    "isolation": "isolated", "purpose": "admission",
}
ARM = REPO / "arms" / "baseline-ornith15-9b.json"


def _record(tmp_path: Path, **over: object) -> str:
    path = tmp_path / "record.json"
    path.write_text(json.dumps({**RECORD, **over}))
    return str(path)


def test_preflight_refuses_a_local_record(tmp_path: Path) -> None:
    assert main(["launch", "--preflight", _record(tmp_path, isolation="local", purpose="development"), "--arm", str(ARM)]) == 2


def test_preflight_refuses_an_arm_the_record_does_not_name(tmp_path: Path) -> None:
    assert main(["launch", "--preflight", _record(tmp_path, model="omlx/other"), "--arm", str(ARM)]) == 2


def test_preflight_passes_a_clean_cell_and_prints_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}

    def clean(**kwargs: object) -> CellPreflight:
        seen.update(kwargs)
        return CellPreflight([], {"pi_version": "0.85.1"})

    monkeypatch.setattr(cli_module, "preflight_cell", clean)
    assert main(["launch", "--preflight", _record(tmp_path), "--arm", str(ARM), "--no-hunt"]) == 0
    assert json.loads(capsys.readouterr().out)["problems"] == []
    assert seen["pinned_pi"] == "0.85.1" and seen["hunt_root"] is None


def test_preflight_fails_on_a_cell_problem_or_the_test_path_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "preflight_cell", lambda **kw: CellPreflight(["the cell can read /x"], {}))
    assert main(["launch", "--preflight", _record(tmp_path), "--arm", str(ARM)]) == 1
    assert "launch preflight FAILED: the cell can read /x" in capsys.readouterr().err
    monkeypatch.setattr(cli_module, "preflight_cell", lambda **kw: CellPreflight([], {}))
    monkeypatch.setenv(CELL_PATH_PREFIX_ENV, "/fake/bin")
    assert main(["launch", "--preflight", _record(tmp_path), "--arm", str(ARM)]) == 1


def test_the_preflight_module_names_its_runner_default() -> None:
    assert cell_preflight.preflight_cell.__kwdefaults__["run"] is subprocess.run
