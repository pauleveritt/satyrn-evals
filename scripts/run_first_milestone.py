#!/usr/bin/env python3
"""Run the one checked-in synthetic first-milestone batch.

This is deliberately not a scheduler or recipe framework. It accepts only the
one fixture recipe, makes its two predeclared cells, and delegates each cell to
the existing ``run --n 1`` implementation before tallying retained evidence.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Literal, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from interleave import build_order, materialize  # noqa: E402
from tally import TallyRefused, tally  # noqa: E402

from satyrn_evals.attempt_record import load_attempt_record  # noqa: E402
from satyrn_evals.errors import SatyrnError  # noqa: E402
from satyrn_evals.rescore import regrade_attempt, summarize_output  # noqa: E402
from satyrn_evals.run import run  # noqa: E402
from satyrn_evals.summary import SUMMARY_NAME  # noqa: E402

RECIPE = ROOT / "recipes" / "first-milestone-depth3-r3.fixture.json"
TASKS_ROOT = ROOT / "src" / "satyrn_evals" / "tasks"
STATE_NAME = "state.json"
RESULT_NAME = "result.json"
type RouteStatus = Literal["running", "complete", "recovery-needed"]


class RouteError(RuntimeError):
    """The retained route needs review before it can continue."""


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _recipe() -> dict:
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    if recipe.get("version") != 1 or recipe.get("n") != 2:
        raise RouteError(
            "the checked-in fixture recipe must be version 1 with two cells"
        )
    return recipe


def _contract_digest(recipe: dict) -> str:
    manifest = json.loads(
        (TASKS_ROOT / recipe["task"] / "manifest.json").read_text(encoding="utf-8")
    )
    return hashlib.sha256(manifest["contracts"][recipe["rung"]].encode()).hexdigest()


def _command(recipe: dict) -> list[str]:
    fixture = recipe["fixture"]
    return [
        sys.executable,
        str(ROOT / fixture["executor"]),
        "--patch",
        str(ROOT / fixture["patch"]),
        "--model",
        fixture["model"],
    ]


def _schedule(recipe: dict) -> dict:
    command = _command(recipe)
    fixture = recipe["fixture"]
    order = build_order(seed=recipe["seed"], per_arm={"fixture": recipe["n"]})
    return {
        "version": 2,
        "seed": recipe["seed"],
        "task": recipe["task"],
        "rung": recipe["rung"],
        "contract_digest": _contract_digest(recipe),
        "configuration_digest": _digest({"recipe": recipe, "command": command}),
        "limits": {**recipe["limits"], "attempt_timeout_seconds": None},
        "model": fixture["model"],
        "server_model": fixture["model"],
        "cells": [
            {
                "index": index,
                "arm": arm,
                "dir": f"cell-{index:03d}-{arm}",
                "command": command,
            }
            for index, arm in enumerate(order)
        ],
    }


def _write_state(output: Path, *, status: RouteStatus, events: list[dict]) -> None:
    path = output / STATE_NAME
    temporary = output / f".{STATE_NAME}.tmp"
    temporary.write_text(
        json.dumps({"version": 1, "status": status, "events": events}, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_state(output: Path) -> tuple[RouteStatus, list[dict]]:
    data = json.loads((output / STATE_NAME).read_text(encoding="utf-8"))
    status = cast(RouteStatus, data["status"])
    if status not in {"running", "complete", "recovery-needed"}:
        raise RouteError("state has an unknown status")
    return status, list(data["events"])


def _completed(cell: dict, output: Path, schedule: dict) -> bool:
    path = output / cell["dir"] / SUMMARY_NAME
    if not path.is_file():
        return False
    try:
        # Validate and rebuild the cached summary from the retained records,
        # receipts, and transcripts before trusting it for a resume decision.
        summary = summarize_output(path.parent, tasks_root=TASKS_ROOT)
    except Exception:
        return False
    for attempt_dir in summary.cells:
        try:
            record = load_attempt_record(path.parent / attempt_dir / "attempt.json")
            if record.timeout != schedule["limits"]["command_timeout_seconds"]:
                return False
            if record.attempt_timeout != schedule["limits"].get(
                "attempt_timeout_seconds"
            ):
                return False
            if record.receipt_path is None or record.verdict is None:
                return False
            receipt = json.loads(
                (path.parent / attempt_dir / record.receipt_path).read_text(
                    encoding="utf-8"
                )
            )
            if receipt.get("patch_digest") != record.patch_digest:
                return False
            if receipt.get("verdict") != record.verdict.value:
                return False
            for artifact, digest in (
                (record.patch_path, record.patch_digest),
                (record.transcript_path, record.transcript_digest),
            ):
                if artifact is None or digest is None:
                    return False
                if (
                    hashlib.sha256(
                        (path.parent / attempt_dir / artifact).read_bytes()
                    ).hexdigest()
                    != digest
                ):
                    return False
        except OSError, ValueError, json.JSONDecodeError:
            return False
    return (
        summary.n == 1
        and summary.task == schedule["task"]
        and summary.rung == schedule["rung"]
        and summary.contract_digest == schedule["contract_digest"]
        and summary.command[: len(cell["command"])] == cell["command"]
        and len(summary.cells) == 1
    )


def _has_event(events: list[dict], event: str, cell: str) -> bool:
    return any(
        item.get("event") == event and item.get("cell") == cell for item in events
    )


def _refuse_replacement(
    output: Path, events: list[dict], cell: dict, detail: str
) -> None:
    events.append({"event": "recovery-needed", "cell": cell["dir"], "error": detail})
    _write_state(output, status="recovery-needed", events=events)
    raise RouteError(f"route needs review: {cell['dir']}: {detail}")


def _rebuild_result(output: Path, schedule: dict) -> None:
    """Rebuild each cell summary from retained artifacts, then tally it."""
    for cell in schedule["cells"]:
        summarize_output(output / cell["dir"], tasks_root=TASKS_ROOT)
    try:
        result = tally(output / "schedule.json", output).to_wire()
    except TallyRefused as error:
        raise RouteError(f"scheduled tally refused: {error}") from error
    (output / RESULT_NAME).write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


def initialize(output: Path) -> dict:
    """Write schedule and initial state before a cell can launch."""
    recipe = _recipe()
    schedule = _schedule(recipe)
    materialize(schedule, output)
    _write_state(output, status="running", events=[{"event": "initialized"}])
    return schedule


def execute(output: Path, *, resume: bool = False) -> None:
    """Complete or resume the exact scheduled fixture cells."""
    if resume:
        status, events = _load_state(output)
        if status == "recovery-needed":
            raise RouteError("route needs review after an interrupted cell")
        schedule = json.loads((output / "schedule.json").read_text(encoding="utf-8"))
        expected = _schedule(_recipe())
        if (
            schedule.get("configuration_digest") != expected["configuration_digest"]
            or schedule.get("limits") != expected["limits"]
            or schedule.get("contract_digest") != expected["contract_digest"]
        ):
            raise RouteError(
                "frozen schedule does not match the checked-in fixture configuration"
            )
    else:
        if output.exists():
            raise RouteError(f"output already exists: {output}; use --resume")
        schedule = initialize(output)
        _status, events = _load_state(output)
    for cell in schedule["cells"]:
        if _completed(cell, output, schedule):
            events.append({"event": "skipped-complete", "cell": cell["dir"]})
            _write_state(output, status="running", events=events)
            continue
        cell_root = output / cell["dir"]
        if _has_event(events, "launching", cell["dir"]) or any(cell_root.iterdir()):
            _refuse_replacement(
                output, events, cell, "incomplete or mismatched retained cell"
            )
        events.append({"event": "launching", "cell": cell["dir"]})
        _write_state(output, status="running", events=events)
        try:
            run(
                task=schedule["task"],
                tasks_root=TASKS_ROOT,
                output=output / cell["dir"],
                command=cell["command"],
                n=1,
                timeout=schedule["limits"]["command_timeout_seconds"],
                attempt_timeout=schedule["limits"].get("attempt_timeout_seconds"),
                rung=schedule["rung"],
            )
        except BaseException as error:
            events.append(
                {
                    "event": "recovery-needed",
                    "cell": cell["dir"],
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            _write_state(output, status="recovery-needed", events=events)
            raise
        events.append({"event": "completed", "cell": cell["dir"]})
        _write_state(output, status="running", events=events)
    _rebuild_result(output, schedule)
    _write_state(output, status="complete", events=events + [{"event": "complete"}])


def regrade(output: Path) -> None:
    """Re-grade scheduled retained attempts without launching an executor."""
    schedule = json.loads((output / "schedule.json").read_text(encoding="utf-8"))
    unavailable: SatyrnError | None = None
    for cell in schedule["cells"]:
        summary = json.loads(
            (output / cell["dir"] / SUMMARY_NAME).read_text(encoding="utf-8")
        )
        for attempt_dir in summary["cells"]:
            attempt_path = output / cell["dir"] / attempt_dir
            try:
                regrade_attempt(attempt_path, tasks_root=TASKS_ROOT)
            except SatyrnError as error:
                if not _completed_unavailable(attempt_path):
                    raise
                unavailable = error
    _rebuild_result(output, schedule)
    if unavailable is not None:
        raise unavailable


def _completed_unavailable(attempt_path: Path) -> bool:
    """Whether a regrade error left a self-consistent unavailable result."""
    try:
        record = load_attempt_record(attempt_path / "attempt.json")
        if record.verdict is None or record.verdict.value != "unavailable":
            return False
        if record.receipt_path is None:
            return False
        receipt = json.loads(
            (attempt_path / record.receipt_path).read_text(encoding="utf-8")
        )
    except OSError, ValueError, json.JSONDecodeError:
        return False
    return (
        receipt.get("patch_digest") == record.patch_digest
        and receipt.get("verdict") == record.verdict.value
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--regrade", action="store_true")
    args = parser.parse_args(argv)
    if args.regrade:
        regrade(args.output)
    else:
        execute(args.output, resume=args.resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
