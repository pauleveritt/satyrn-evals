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
