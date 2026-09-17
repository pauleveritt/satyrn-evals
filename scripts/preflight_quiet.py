"""Is this machine quiet enough to start a census night?

Three readings, each parsed from a string so the whole module is testable
without a subprocess: the one-minute load against the core count, the busy
processes in a ``ps`` snapshot, and the recent decode rate from the model
server's log. ``certificate`` turns the three into a problems list and a
JSON record of its inputs; the CLI prints it and exits non-zero when the
machine is not quiet.
"""

import argparse
import json
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

DEFAULT_CEILING = 0.5
DEFAULT_CPU_FLOOR = 20.0
DEFAULT_FLOOR_TOK_S = 30.0
DEFAULT_LAST = 20
IGNORE_PREFIXES: tuple[str, ...] = (
    "/sbin/", "/usr/sbin/", "/usr/libexec/", "/System/",
    "/usr/local/bin/omlx-", "omlx-", "/Applications/oMLX.app/",
)
SERVER_LOG = os.path.expanduser("~/.omlx/logs/server.log")


@dataclass(frozen=True, slots=True)
class Process:
    pid: int
    comm: str
    cpu: float


@dataclass(frozen=True, slots=True)
class Rate:
    tok_s: float
    completions: int
    tokens: int
    seconds: float


def load_problem(loadavg: tuple[float, float, float], cores: int, *, ceiling: float) -> str | None:
    one_minute = loadavg[0]
    limit = ceiling * cores
    if one_minute <= limit:
        return None
    return f"load {one_minute:.1f} > {limit:.1f} ({cores} cores)"


def busy_processes(
    ps_stdout: str, *, cpu_floor: float, ignore_prefixes: Sequence[str]
) -> list[Process]:
    busy: list[Process] = []
    for line in ps_stdout.splitlines():
        fields = line.strip().split(maxsplit=2)
        if len(fields) != 3:
            continue
        try:
            pid, cpu = int(fields[0]), float(fields[1])
        except ValueError:
            continue
        comm = fields[2]
        if cpu > cpu_floor and not comm.startswith(tuple(ignore_prefixes)):
            busy.append(Process(pid=pid, comm=comm, cpu=cpu))
    return busy


_COMPLETION = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - omlx\.server - INFO\b.*?"
    r"Chat completion: model=(?P<model>[^,]+), (?P<tokens>\d+) tokens in "
    r"(?P<seconds>[\d.]+)s \((?P<rate>[\d.]+) tok/s\), prompt: (?P<prompt>\d+),"
)


def decode_rate(log_lines: Iterable[str], *, model: str, last: int) -> Rate | None:
    seen: list[tuple[int, float]] = []
    for line in log_lines:
        match = _COMPLETION.search(line)
        if match is not None and match.group("model") == model:
            seen.append((int(match.group("tokens")), float(match.group("seconds"))))
    if len(seen) < last:
        return None
    window = seen[-last:]
    tokens = sum(count for count, _ in window)
    seconds = sum(span for _, span in window)
    return Rate(tok_s=tokens / seconds, completions=len(window), tokens=tokens, seconds=seconds)


@dataclass(frozen=True, slots=True)
class Certificate:
    problems: tuple[str, ...]
    record: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {"problems": list(self.problems), "inputs": self.record}


def certificate(
    load: str | None,
    busy: Sequence[Process],
    rate: Rate | None,
    *,
    floor_tok_s: float,
    model: str,
    last: int,
) -> Certificate:
    problems: list[str] = []
    if load is not None:
        problems.append(load)
    for process in busy:
        problems.append(f"busy: {process.comm} pid {process.pid} at {process.cpu:.1f}% cpu")
    if rate is None:
        problems.append(f"decode: fewer than {last} completions for {model}")
    elif rate.tok_s < floor_tok_s:
        problems.append(
            f"decode {rate.tok_s:.1f} tok/s < {floor_tok_s:.1f} "
            f"over last {rate.completions} completions"
        )
    record: dict[str, object] = {
        "load": load,
        "busy": [{"pid": p.pid, "comm": p.comm, "cpu": p.cpu} for p in busy],
        "decode": None
        if rate is None
        else {
            "tok_s": rate.tok_s,
            "completions": rate.completions,
            "tokens": rate.tokens,
            "seconds": rate.seconds,
        },
        "floor_tok_s": floor_tok_s,
        "model": model,
        "last": last,
    }
    return Certificate(problems=tuple(problems), record=record)


def _read_ps() -> str:
    return subprocess.run(
        ["ps", "-axo", "pid,pcpu,comm"], capture_output=True, text=True, check=True
    ).stdout


def _read_log() -> list[str]:
    try:
        with open(SERVER_LOG, encoding="utf-8", errors="replace") as handle:
            return handle.readlines()
    except OSError:
        return []


def main(
    argv: Sequence[str] | None = None,
    *,
    loadavg: Callable[[], tuple[float, float, float]] = os.getloadavg,
    cores: Callable[[], int] = lambda: os.cpu_count() or 1,
    read_ps: Callable[[], str] = _read_ps,
    read_log: Callable[[], Iterable[str]] = _read_log,
) -> int:
    parser = argparse.ArgumentParser(prog="preflight_quiet.py")
    parser.add_argument("--model", required=True)
    parser.add_argument("--ceiling", type=float, default=DEFAULT_CEILING)
    parser.add_argument("--cpu-floor", type=float, default=DEFAULT_CPU_FLOOR)
    parser.add_argument("--floor-tok-s", type=float, default=DEFAULT_FLOOR_TOK_S)
    parser.add_argument("--last", type=int, default=DEFAULT_LAST)
    args = parser.parse_args(argv)
    result = certificate(
        load_problem(loadavg(), cores(), ceiling=args.ceiling),
        busy_processes(read_ps(), cpu_floor=args.cpu_floor, ignore_prefixes=IGNORE_PREFIXES),
        decode_rate(read_log(), model=args.model, last=args.last),
        floor_tok_s=args.floor_tok_s,
        model=args.model,
        last=args.last,
    )
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 1 if result.problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
