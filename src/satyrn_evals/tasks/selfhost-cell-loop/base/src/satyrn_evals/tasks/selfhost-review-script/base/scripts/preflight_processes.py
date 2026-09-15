#!/usr/bin/env python3
"""Identify only measurement-shaped Pi/Engine processes for preflight."""

import argparse
import shlex
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Process:
    pid: int
    ppid: int
    command: str

    @property
    def argv(self) -> list[str]:
        try:
            return shlex.split(self.command)
        except ValueError:
            return self.command.split()


def parse_snapshot(text: str) -> dict[int, Process]:
    processes: dict[int, Process] = {}
    for line in text.splitlines():
        fields = line.strip().split(maxsplit=2)
        if len(fields) != 3:
            continue
        try:
            pid, ppid = int(fields[0]), int(fields[1])
        except ValueError:
            continue
        processes[pid] = Process(pid, ppid, fields[2])
    return processes


def _is_engine(process: Process) -> bool:
    argv = process.argv
    return any(token.rsplit("/", 1)[-1] == "satyrn-engine" for token in argv) and (
        "attempt" in argv
    )


def _is_measurement_pi(process: Process, model: str) -> bool:
    argv = process.argv
    if not any(token.rsplit("/", 1)[-1] == "pi" for token in argv):
        return False
    if "--print" not in argv or "--mode" not in argv:
        return False
    mode = argv[argv.index("--mode") + 1] if argv.index("--mode") + 1 < len(argv) else ""
    if mode != "json":
        return False
    if "--model" not in argv:
        return False
    model_index = argv.index("--model") + 1
    return model_index < len(argv) and argv[model_index] == model


def _has_engine_ancestor(process: Process, processes: dict[int, Process]) -> bool:
    seen: set[int] = set()
    parent = process.ppid
    while parent not in seen and parent in processes:
        seen.add(parent)
        candidate = processes[parent]
        if _is_engine(candidate):
            return True
        parent = candidate.ppid
    return False


def measurement_processes(snapshot: str, model: str) -> list[str]:
    """Return details for eval-shaped processes, ignoring IDE Pi sessions."""
    processes = parse_snapshot(snapshot)
    found: list[str] = []
    for process in processes.values():
        if _is_engine(process) or _is_measurement_pi(process, model) or (
            _has_engine_ancestor(process, processes)
            and any(token.rsplit("/", 1)[-1] == "pi" for token in process.argv)
        ):
            found.append(f"pid={process.pid} ppid={process.ppid} cmd={process.command}")
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    print("\n".join(measurement_processes(sys.stdin.read(), args.model)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
