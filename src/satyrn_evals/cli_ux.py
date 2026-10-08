"""The simple front door: scaffold a project with `init`, then (next steps)
`doctor`, `run`, and `report`.

The expert commands keep their existing argparse surface and are reached
unchanged; this module is the new, click-based surface that a project which
merely *depends on* satyrn-evals uses. It is introduced incrementally, so today
only `init` lives here and `cli.main` routes the new verbs to it.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import click
import yaml

from satyrn_evals import prereqs
from satyrn_evals.errors import SatyrnError
from satyrn_evals.launch_record import launch_record
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run_record import load_run_record, new_record, write_new_record

#: The verbs this module owns; `cli.main` routes these before argparse sees them.
UX_COMMANDS = frozenset({"init", "doctor", "run"})

CONFIG_NAME = "satyrn.yaml"
EXAMPLE_TASK = "format_number"
DEFAULT_ARM = "baseline"
DEFAULT_MODEL = "unsloth/ornith-ai/Ornith-1.5-9B-GGUF"
DEFAULT_BACKEND = "openai"
DEFAULT_PI_VERSION = "0.85.1"
BACKENDS = ("openai", "omlx", "ollama")
BASELINE_TOOLS = ["read", "bash", "edit", "write"]


class InitError(click.ClickException):
    """A refusal that should print as a user-facing error, not a traceback."""


def server_model_of(model: str) -> str:
    """The bare id a server lists for a `provider/model` address.

    `unsloth/ornith-ai/Ornith-1.5-9B-GGUF` becomes `ornith-ai/Ornith-1.5-9B-GGUF`;
    a bare id with no provider prefix is unchanged.
    """
    return model.split("/", 1)[1] if "/" in model else model


def config_text(*, task: str, tasks_root: str, arm: str, model: str, backend: str) -> str:
    """The `satyrn.yaml` a later `run` reads: task, arm, model, and budgets."""
    data = {
        "task": task,
        "tasks-root": tasks_root,
        "arm": arm,
        "model": model,
        "backend": backend,
        "run": {
            "n": 1,
            "k": 1,
            "purpose": "development",
            "token-budget": 32000,
            "turn-budget": 48,
            "max-minutes": 60,
        },
    }
    return yaml.safe_dump(data, sort_keys=False)


def arm_text(*, model: str, backend: str, pi_version: str) -> str:
    """A starter Baseline arm file for the configured model and backend."""
    data = {
        "arm": "baseline",
        "settings_verified_by": "scripts/preflight_settings.py",
        "backend": backend,
        "argv": ["satyrn-evals-attempt-pi"],
        "tools": BASELINE_TOOLS,
        "model": model,
        "server_model": server_model_of(model),
        "pins": {"pi": pi_version, "engine_commit": None, "digests": {}},
    }
    return json.dumps(data, indent=2) + "\n"


def _existing(target: Path, *, force: bool) -> None:
    if target.exists() and not force:
        raise InitError(f"{target} already exists; pass --force to overwrite")


def find_config(start: Path | None = None) -> Path | None:
    """The nearest `satyrn.yaml` at or above `start` (default: the cwd), or None."""
    here = (start or Path.cwd()).resolve()
    for parent in (here, *here.parents):
        candidate = parent / CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def _required(config: dict[str, object], key: str) -> str:
    """The config's string value for `key`, or a refusal naming what is missing."""
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise InitError(f"satyrn.yaml is missing {key!r}")
    return value


def load_config(path: Path | None = None) -> dict[str, object]:
    """The run config as a mapping; `{}` when there is none or it is not an object."""
    if path is not None and not path.is_file():
        raise InitError(f"{path} does not exist")
    resolved = path if path is not None else find_config()
    if resolved is None:
        return {}
    data = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def scaffold(
    dest: Path,
    *,
    task: str = EXAMPLE_TASK,
    arm: str = DEFAULT_ARM,
    model: str = DEFAULT_MODEL,
    backend: str = DEFAULT_BACKEND,
    pi_version: str = DEFAULT_PI_VERSION,
    force: bool = False,
) -> list[Path]:
    """Write the config, copy the example task, and write the arm.

    Refuses to touch anything that already exists unless `force`. Returns the
    paths written, in the order they were created.
    """
    source = DEFAULT_TASKS_ROOT / task
    if not source.is_dir():
        raise InitError(f"no bundled example task {task!r}")
    config = dest / CONFIG_NAME
    task_dest = dest / "eval-tasks" / task
    arm_dest = dest / "arms" / f"{arm}.json"
    _existing(config, force=force)
    _existing(task_dest, force=force)
    _existing(arm_dest, force=force)
    dest.mkdir(parents=True, exist_ok=True)
    if task_dest.exists():
        shutil.rmtree(task_dest)
    shutil.copytree(source, task_dest)
    config.write_text(
        config_text(task=task, tasks_root="eval-tasks", arm=arm, model=model, backend=backend),
        encoding="utf-8",
    )
    arm_dest.parent.mkdir(parents=True, exist_ok=True)
    arm_dest.write_text(arm_text(model=model, backend=backend, pi_version=pi_version), encoding="utf-8")
    return [config, task_dest, arm_dest]


@click.group()
def cli() -> None:
    """Run evals in your own project.

    \b
    init     scaffold satyrn.yaml, an example task, and a starter arm here
    doctor   check this machine and the configured backend
    run      write the configured record and launch its cells
    """


@cli.command()
@click.argument("dest", type=click.Path(path_type=Path), default=Path(), required=False)
@click.option("--task", default=EXAMPLE_TASK, show_default=True, help="bundled example task to copy")
@click.option("--arm", default=DEFAULT_ARM, show_default=True, help="arm name for the starter arm file")
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="provider/model address the arm serves")
@click.option("--backend", type=click.Choice(BACKENDS), default=DEFAULT_BACKEND, show_default=True)
@click.option("--pi-version", default=DEFAULT_PI_VERSION, show_default=True, help="pinned pi version the arm records")
@click.option("--force", is_flag=True, help="overwrite files that already exist")
def init(
    dest: Path,
    task: str,
    arm: str,
    model: str,
    backend: str,
    pi_version: str,
    force: bool,
) -> None:
    """Scaffold satyrn.yaml, an example task, and a starter arm in DEST."""
    for path in scaffold(
        dest,
        task=task,
        arm=arm,
        model=model,
        backend=backend,
        pi_version=pi_version,
        force=force,
    ):
        click.echo(f"wrote {path}")
    click.echo("next: edit satyrn.yaml, then run `satyrn-evals doctor`")


@cli.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="satyrn.yaml to read (default: the nearest one above the cwd)",
)
@click.option("--check-servers", is_flag=True, help="also probe the model server named in the config (network)")
def doctor(config_path: Path | None, check_servers: bool) -> int:
    """Check this machine and the configured backend before spending a budget."""
    config = load_config(config_path)
    results = list(prereqs.run_prereqs(check_servers=False))
    if check_servers:
        model = str(config.get("model") or os.environ.get("SATYRN_MODEL", ""))
        if model:
            results.append(
                ("model server", prereqs.server_reachable(model), f"start the backend and serve {model}")
            )
        else:
            results.append(("model server", (False, "no model configured"), "set model: in satyrn.yaml"))
    click.echo(prereqs.render_report(results))
    missing, _ = prereqs.summarize(results)
    raise SystemExit(0 if missing == 0 else 1)


@cli.command(name="run")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="satyrn.yaml to read (default: the nearest one above the cwd)",
)
@click.option("--dry-run", is_flag=True, help="write and validate the record, but do not spend a budget")
@click.option("--no-settings", is_flag=True, help="skip preflight_settings (development records only)")
def run_command(config_path: Path | None, dry_run: bool, no_settings: bool) -> None:
    """Run the eval described by satyrn.yaml: write its record, then launch its cells."""
    path = config_path if config_path is not None else find_config()
    if path is None:
        raise InitError("no satyrn.yaml found; run `satyrn-evals init` first")
    config = load_config(path)
    base = path.parent
    task = _required(config, "task")
    tasks_root = base / str(config.get("tasks-root", "eval-tasks"))
    arm_name = str(config.get("arm", DEFAULT_ARM))
    arm_path = base / "arms" / f"{arm_name}.json"
    if not arm_path.is_file():
        raise InitError(f"{arm_path} is missing; run `satyrn-evals init` or fix arm: in satyrn.yaml")
    model = _required(config, "model")
    run_cfg = config.get("run")
    run_cfg = run_cfg if isinstance(run_cfg, dict) else {}
    record_path = base / str(config.get("record", f"records/{task}.json"))
    if not record_path.is_file():
        rung = str(config.get("rung", "contract"))
        body = new_record(
            task=task,
            tasks_root=tasks_root,
            arm=arm_name,
            model=model,
            n=int(run_cfg.get("n", 1)),
            k=int(run_cfg.get("k", 1)),
            rung=None if rung == "contract" else rung,
            purpose=str(run_cfg.get("purpose", "development")),
            mode=str(run_cfg.get("mode", "attended")),
            max_minutes=int(run_cfg.get("max-minutes", 60)),
            token_budget=int(run_cfg.get("token-budget", 32000)),
            turn_budget=int(run_cfg.get("turn-budget", 48)),
            previous_result=None,
            authority=None,
            decision_rule=None,
            backend=str(config.get("backend", DEFAULT_BACKEND)),
        )
        write_new_record(record_path, body)
        click.echo(f"wrote {record_path}; commit it, unchanged, before launch")
    record = load_run_record(record_path)
    if dry_run:
        click.echo(
            f"record accepted: task {record.task}, arm {record.arm}, model {record.model}, "
            f"n={record.n}, k={record.k}"
        )
        return
    try:
        code = launch_record(record_path, [arm_path], tasks_root=tasks_root, settings=not no_settings)
    except SatyrnError as exc:
        raise click.ClickException(str(exc)) from exc
    raise SystemExit(code)


def run(argv: list[str]) -> int:
    """Dispatch a UX verb through click, returning an exit code.

    `standalone_mode=False` keeps click from calling `sys.exit`, so a command
    that returns an int owns its exit code and `cli.main` returns it. Each way
    click raises is mapped back to the code the legacy dispatcher would return.
    """
    try:
        cli.main(argv, standalone_mode=False)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except click.exceptions.Exit as exc:
        return exc.exit_code
    except click.exceptions.Abort:
        return 130
    return 0
