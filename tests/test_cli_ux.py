"""The simple front door: `init` and its dispatch through the legacy CLI.

Everything here is offline: `scaffold` writes files into `tmp_path`, and the
click paths are driven through `CliRunner`; no model, no network, no subprocess.
"""

import json
from pathlib import Path

import click
import pytest
import yaml
from click.testing import CliRunner

from satyrn_evals import cli as cli_module
from satyrn_evals import cli_ux
from satyrn_evals.arms import load_arm
from satyrn_evals.errors import SatyrnError

# --- the pieces -------------------------------------------------------------


def test_server_model_strips_the_provider_prefix() -> None:
    assert cli_ux.server_model_of("unsloth/ornith-ai/Ornith-1.5-9B-GGUF") == "ornith-ai/Ornith-1.5-9B-GGUF"
    assert cli_ux.server_model_of("Ornith-1.5-9B-GGUF") == "Ornith-1.5-9B-GGUF"


def test_config_text_round_trips_the_choices() -> None:
    text = cli_ux.config_text(
        task="format_number",
        tasks_root="eval-tasks",
        arm="baseline",
        model="unsloth/ornith-ai/Ornith-1.5-9B-GGUF",
        backend="openai",
    )
    data = yaml.safe_load(text)
    assert data["task"] == "format_number"
    assert data["tasks-root"] == "eval-tasks"
    assert data["arm"] == "baseline"
    assert data["model"] == "unsloth/ornith-ai/Ornith-1.5-9B-GGUF"
    assert data["backend"] == "openai"
    assert data["run"] == {
        "n": 1,
        "k": 1,
        "purpose": "development",
        "token-budget": 32000,
        "turn-budget": 48,
        "max-minutes": 60,
    }


def test_arm_text_loads_and_addresses_its_server_model(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(
        cli_ux.arm_text(
            model="unsloth/ornith-ai/Ornith-1.5-9B-GGUF",
            backend="openai",
            pi_version="0.85.1",
        ),
        encoding="utf-8",
    )
    arm = load_arm(path)
    assert arm.arm == "baseline"
    assert arm.model == "unsloth/ornith-ai/Ornith-1.5-9B-GGUF"
    assert arm.server_model == "ornith-ai/Ornith-1.5-9B-GGUF"
    assert arm.backend == "openai"


# --- scaffold ---------------------------------------------------------------


def test_scaffold_writes_config_task_and_arm(tmp_path: Path) -> None:
    dest = tmp_path / "project"
    written = cli_ux.scaffold(dest)
    assert written == [
        dest / "satyrn.yaml",
        dest / "eval-tasks" / "format_number",
        dest / "arms" / "baseline.json",
    ]
    assert (dest / "satyrn.yaml").is_file()
    assert (dest / "eval-tasks" / "format_number" / "manifest.json").is_file()
    assert (dest / "arms" / "baseline.json").is_file()


def test_scaffold_refuses_an_existing_config(tmp_path: Path) -> None:
    (tmp_path / "satyrn.yaml").write_text("existing", encoding="utf-8")
    with pytest.raises(cli_ux.InitError, match="already exists"):
        cli_ux.scaffold(tmp_path)


def test_scaffold_refuses_an_existing_task(tmp_path: Path) -> None:
    (tmp_path / "eval-tasks" / "format_number").mkdir(parents=True)
    with pytest.raises(cli_ux.InitError, match="eval-tasks"):
        cli_ux.scaffold(tmp_path)


def test_scaffold_refuses_an_existing_arm(tmp_path: Path) -> None:
    (tmp_path / "arms").mkdir()
    (tmp_path / "arms" / "baseline.json").write_text("{}", encoding="utf-8")
    with pytest.raises(cli_ux.InitError, match="baseline.json"):
        cli_ux.scaffold(tmp_path)


def test_scaffold_force_overwrites_what_exists(tmp_path: Path) -> None:
    (tmp_path / "satyrn.yaml").write_text("old", encoding="utf-8")
    stale = tmp_path / "eval-tasks" / "format_number" / "stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")
    (tmp_path / "arms").mkdir()
    (tmp_path / "arms" / "baseline.json").write_text("{}", encoding="utf-8")

    cli_ux.scaffold(tmp_path, force=True)

    assert not stale.exists()
    assert yaml.safe_load((tmp_path / "satyrn.yaml").read_text())["task"] == "format_number"
    assert json.loads((tmp_path / "arms" / "baseline.json").read_text())["model"]


def test_scaffold_refuses_a_task_that_is_not_bundled(tmp_path: Path) -> None:
    with pytest.raises(cli_ux.InitError, match="no bundled example task"):
        cli_ux.scaffold(tmp_path, task="not_a_task")


# --- the click surface ------------------------------------------------------


def test_init_command_reports_what_it_wrote(tmp_path: Path) -> None:
    result = CliRunner().invoke(cli_ux.cli, ["init", str(tmp_path / "project")])
    assert result.exit_code == 0
    assert "wrote" in result.output
    assert "next: edit satyrn.yaml" in result.output


def test_init_command_reports_a_refusal(tmp_path: Path) -> None:
    (tmp_path / "satyrn.yaml").write_text("existing", encoding="utf-8")
    result = CliRunner().invoke(cli_ux.cli, ["init", str(tmp_path)])
    assert result.exit_code == 1
    assert "already exists" in result.output


# --- the dispatch -----------------------------------------------------------


def test_run_returns_zero_on_success(tmp_path: Path) -> None:
    assert cli_ux.run(["init", str(tmp_path / "project")]) == 0


def test_run_returns_the_click_exception_code(tmp_path: Path) -> None:
    assert cli_ux.run(["init", "--task", "not_a_task", str(tmp_path)]) == 1


def test_run_returns_on_help() -> None:
    assert cli_ux.run(["init", "--help"]) == 0


def test_run_maps_an_abort_to_130(monkeypatch: pytest.MonkeyPatch) -> None:
    def abort(*_args: object, **_kwargs: object) -> None:
        raise click.exceptions.Abort

    monkeypatch.setattr(cli_ux.cli, "main", abort)
    assert cli_ux.run(["init"]) == 130


def test_main_routes_a_ux_command_before_argparse(tmp_path: Path) -> None:
    assert cli_module.main(["init", str(tmp_path / "project")]) == 0
    assert (tmp_path / "project" / "satyrn.yaml").is_file()


# --- config discovery -------------------------------------------------------


def test_find_config_walks_up_from_the_start(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    (tmp_path / "satyrn.yaml").write_text("task: t\n", encoding="utf-8")
    assert cli_ux.find_config(deep) == tmp_path / "satyrn.yaml"
    assert cli_ux.find_config(tmp_path) == tmp_path / "satyrn.yaml"


def test_find_config_is_none_when_absent(tmp_path: Path) -> None:
    assert cli_ux.find_config(tmp_path) is None


def test_load_config_reads_an_explicit_path(tmp_path: Path) -> None:
    path = tmp_path / "satyrn.yaml"
    path.write_text("task: format_number\nmodel: m/1\n", encoding="utf-8")
    assert cli_ux.load_config(path) == {"task": "format_number", "model": "m/1"}


def test_load_config_is_empty_without_a_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli_ux.load_config() == {}


def test_load_config_is_empty_when_the_file_is_not_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "satyrn.yaml"
    path.write_text("- not\n- a mapping\n", encoding="utf-8")
    assert cli_ux.load_config(path) == {}


def test_load_config_refuses_a_missing_explicit_path(tmp_path: Path) -> None:
    with pytest.raises(cli_ux.InitError, match="does not exist"):
        cli_ux.load_config(tmp_path / "absent.yaml")


# --- doctor -----------------------------------------------------------------


def _ok_prereqs(check_servers: bool) -> list[tuple[str, tuple[bool, str], str]]:
    return [("git", (True, "/usr/bin/git"), "install git")]


def test_doctor_passes_when_prereqs_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_ux.prereqs, "run_prereqs", _ok_prereqs)
    result = CliRunner().invoke(cli_ux.cli, ["doctor"])
    assert result.exit_code == 0
    assert "All 1 prerequisites are met." in result.output


def test_doctor_fails_when_a_prerequisite_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli_ux.prereqs,
        "run_prereqs",
        lambda check_servers: [("git", (False, "is not on PATH"), "install git")],
    )
    result = CliRunner().invoke(cli_ux.cli, ["doctor"])
    assert result.exit_code == 1
    assert "install git" in result.output


def test_doctor_check_servers_probes_the_configured_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_ux.prereqs, "run_prereqs", _ok_prereqs)
    seen: list[str] = []

    def reach(model: str) -> tuple[bool, str]:
        seen.append(model)
        return True, model

    monkeypatch.setattr(cli_ux.prereqs, "server_reachable", reach)
    config = tmp_path / "satyrn.yaml"
    config.write_text("model: unsloth/ornith-ai/Ornith-1.5-9B-GGUF\n", encoding="utf-8")
    result = CliRunner().invoke(cli_ux.cli, ["doctor", "--check-servers", "--config", str(config)])
    assert result.exit_code == 0
    assert seen == ["unsloth/ornith-ai/Ornith-1.5-9B-GGUF"]


def test_doctor_check_servers_refuses_without_a_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_ux.prereqs, "run_prereqs", _ok_prereqs)
    monkeypatch.delenv("SATYRN_MODEL", raising=False)
    config = tmp_path / "satyrn.yaml"
    config.write_text("task: format_number\n", encoding="utf-8")
    result = CliRunner().invoke(cli_ux.cli, ["doctor", "--check-servers", "--config", str(config)])
    assert result.exit_code == 1
    assert "no model configured" in result.output


def test_doctor_check_servers_fails_when_the_server_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_ux.prereqs, "run_prereqs", _ok_prereqs)
    monkeypatch.setattr(cli_ux.prereqs, "server_reachable", lambda model: (False, "unreachable"))
    monkeypatch.setenv("SATYRN_MODEL", "unsloth/ornith-ai/Ornith-1.5-9B-GGUF")
    result = CliRunner().invoke(cli_ux.cli, ["doctor", "--check-servers"])
    assert result.exit_code == 1
    assert "unreachable" in result.output


def test_main_routes_doctor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_ux.prereqs, "run_prereqs", _ok_prereqs)
    assert cli_module.main(["doctor"]) == 0


# --- run --------------------------------------------------------------------


def test_run_dry_run_writes_and_accepts_the_record(tmp_path: Path) -> None:
    cli_ux.scaffold(tmp_path)
    result = CliRunner().invoke(cli_ux.cli, ["run", "--dry-run", "--config", str(tmp_path / "satyrn.yaml")])
    assert result.exit_code == 0
    assert "record accepted" in result.output
    assert (tmp_path / "records" / "format_number.json").is_file()


def test_run_reuses_an_existing_record(tmp_path: Path) -> None:
    cli_ux.scaffold(tmp_path)
    args = ["run", "--dry-run", "--config", str(tmp_path / "satyrn.yaml")]
    assert CliRunner().invoke(cli_ux.cli, args).exit_code == 0
    result = CliRunner().invoke(cli_ux.cli, args)
    assert result.exit_code == 0
    assert "wrote" not in result.output


def test_run_refuses_without_a_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli_ux.cli, ["run", "--dry-run"])
    assert result.exit_code == 1
    assert "no satyrn.yaml" in result.output


def test_run_refuses_when_a_required_key_is_missing(tmp_path: Path) -> None:
    cli_ux.scaffold(tmp_path)
    (tmp_path / "satyrn.yaml").write_text("model: unsloth/ornith-ai/Ornith-1.5-9B-GGUF\n", encoding="utf-8")
    result = CliRunner().invoke(cli_ux.cli, ["run", "--dry-run", "--config", str(tmp_path / "satyrn.yaml")])
    assert result.exit_code == 1
    assert "missing 'task'" in result.output


def test_run_refuses_when_the_arm_file_is_missing(tmp_path: Path) -> None:
    cli_ux.scaffold(tmp_path)
    (tmp_path / "arms" / "baseline.json").unlink()
    result = CliRunner().invoke(cli_ux.cli, ["run", "--dry-run", "--config", str(tmp_path / "satyrn.yaml")])
    assert result.exit_code == 1
    assert "is missing" in result.output


def test_run_launches_and_returns_the_launcher_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli_ux.scaffold(tmp_path)
    seen: dict[str, object] = {}

    def fake(record_path: Path, arm_paths: list[Path], *, tasks_root: Path, settings: bool) -> int:
        seen["record"], seen["arms"], seen["settings"] = record_path, arm_paths, settings
        return 3

    monkeypatch.setattr(cli_ux, "launch_record", fake)
    result = CliRunner().invoke(cli_ux.cli, ["run", "--config", str(tmp_path / "satyrn.yaml")])
    assert result.exit_code == 3
    assert seen["record"] == tmp_path / "records" / "format_number.json"
    assert seen["arms"] == [tmp_path / "arms" / "baseline.json"]
    assert seen["settings"] is True


def test_run_maps_a_launcher_refusal_to_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli_ux.scaffold(tmp_path)

    def refuse(*_args: object, **_kwargs: object) -> int:
        raise SatyrnError("the run record is not frozen: commit it, unchanged, before launch")

    monkeypatch.setattr(cli_ux, "launch_record", refuse)
    result = CliRunner().invoke(cli_ux.cli, ["run", "--config", str(tmp_path / "satyrn.yaml")])
    assert result.exit_code == 1
    assert "not frozen" in result.output


def test_main_routes_run(tmp_path: Path) -> None:
    assert cli_module.main(["run", "--dry-run", "--config", str(_scaffolded(tmp_path))]) == 0


def _scaffolded(tmp_path: Path) -> Path:
    cli_ux.scaffold(tmp_path)
    return tmp_path / "satyrn.yaml"


# --- report -----------------------------------------------------------------

_RESULT = {
    "task": "format_number",
    "rung": None,
    "purpose": "development",
    "status": "complete",
    "reason": None,
    "cells": [{"slot": 0}],
    "arms": {
        "baseline": {
            "finished": 1,
            "passes": 1,
            "code_counts": {"OK": 1, "BUDGET_EXCEEDED": 0},
            "contamination": {"flagged": 0},
        }
    },
}


def test_render_result_lists_the_arms_and_counts() -> None:
    text = cli_ux.render_result(_RESULT)
    assert "task:     format_number" in text
    assert "rung:     contract" in text
    assert "arm baseline: 1/1 passed (OK=1)" in text


def test_render_result_survives_a_partial_result() -> None:
    text = cli_ux.render_result({"status": "stopped", "reason": "infrastructure"})
    assert "status:   stopped (infrastructure)" in text
    assert "cells:    0" in text
    assert "arm " not in text


def test_report_renders_an_explicit_record(tmp_path: Path) -> None:
    record = tmp_path / "records" / "t.json"
    record.parent.mkdir(parents=True)
    record.write_text("{}", encoding="utf-8")
    record.with_suffix(".result.json").write_text(json.dumps(_RESULT), encoding="utf-8")
    result = CliRunner().invoke(cli_ux.cli, ["report", str(record)])
    assert result.exit_code == 0
    assert "arm baseline: 1/1 passed" in result.output


def test_report_uses_the_config_record(tmp_path: Path) -> None:
    cli_ux.scaffold(tmp_path)
    record = tmp_path / "records" / "format_number.json"
    record.parent.mkdir(parents=True)
    record.write_text("{}", encoding="utf-8")
    record.with_suffix(".result.json").write_text(json.dumps(_RESULT), encoding="utf-8")
    result = CliRunner().invoke(cli_ux.cli, ["report", "--config", str(tmp_path / "satyrn.yaml")])
    assert result.exit_code == 0
    assert "format_number" in result.output


def test_report_refuses_without_a_result(tmp_path: Path) -> None:
    record = tmp_path / "r.json"
    record.write_text("{}", encoding="utf-8")
    result = CliRunner().invoke(cli_ux.cli, ["report", str(record)])
    assert result.exit_code == 1
    assert "no result" in result.output


def test_report_refuses_without_a_config_or_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli_ux.cli, ["report"])
    assert result.exit_code == 1
    assert "no satyrn.yaml" in result.output


def test_main_routes_report(tmp_path: Path) -> None:
    record = tmp_path / "r.json"
    record.write_text("{}", encoding="utf-8")
    record.with_suffix(".result.json").write_text(json.dumps(_RESULT), encoding="utf-8")
    assert cli_module.main(["report", str(record)]) == 0

