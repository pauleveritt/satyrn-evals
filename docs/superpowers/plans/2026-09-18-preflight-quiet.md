# The machine-quiet preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone script that says, with evidence, whether this machine is quiet enough to start a census night.

**Architecture:** One new module, `scripts/preflight_quiet.py`, with a pure API and a thin CLI over it. Three readings — the one-minute load against the core count, the busy processes in a `ps` snapshot, and the recent decode rate from the model server's log — each parsed from a string by a pure function, and one `certificate` that turns the three into a problems list and a JSON record of its inputs. The CLI takes its four readings from injected callables so the whole module is testable without a subprocess, the network, or a loud machine.

**Tech Stack:** Python 3.14, standard library only (`argparse`, `dataclasses`, `json`, `os`, `re`, `subprocess` for the real `ps` reader), pytest.

**Spec:** `docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md` section 2.

## Global Constraints

- Python 3.14, standard library only; no new dependency.
- The acceptance suite runs in the default test tier: no model, no network, **no subprocess**, no real `ps`, no real server log, no reading of the machine's own load. Every input is a string or a number.
- Every refusal has a sibling success: each parser is exercised on a known-good and a known-bad input, and each threshold at its edge and across it.
- `scripts/preflight_quiet.py` is the only source module this work creates.

### Task 1: The machine-quiet preflight

**Files:**
- Create: `scripts/preflight_quiet.py`
- Test: `tests/test_preflight_quiet.py`

**Interfaces:**
- Consumes: nothing; the module stands alone and imports only the standard library.
- Produces: `load_problem(loadavg: tuple[float, float, float], cores: int, *, ceiling: float) -> str | None`; `busy_processes(ps_stdout: str, *, cpu_floor: float, ignore_prefixes: Sequence[str]) -> list[Process]`; `decode_rate(log_lines: Iterable[str], *, model: str, last: int) -> Rate | None`; `certificate(load: str | None, busy: Sequence[Process], rate: Rate | None, *, floor_tok_s: float, model: str, last: int) -> Certificate`; `main(argv: Sequence[str] | None = None, *, loadavg, cores, read_ps, read_log) -> int`; the frozen dataclasses `Process(pid: int, comm: str, cpu: float)`, `Rate(tok_s: float, completions: int, tokens: int, seconds: float)` and `Certificate(problems: tuple[str, ...], record: dict[str, object])` with `Certificate.as_dict()`; and the module constant `IGNORE_PREFIXES`.

- [ ] **Step 1: Write the acceptance suite first, in full**

Write the whole suite before any of the module exists. It imports from `preflight_quiet` with `scripts` on the path, and it drives the CLI through its injected callables rather than through a process, so it obeys the no-subprocess rule of the default tier. Twenty tests: each parser on a known-good and a known-bad input, each threshold at its edge and across it, the ignore list both ways, the token weighting on two completions of unequal length, the fewer-than-N case, the certificate's JSON shape, and both CLI exit codes.

```python
"""The machine-quiet preflight: the acceptance suite, written from the spec.

No network, no subprocess, no real ``ps`` and no real server log: every input
is a string or a number, and the CLI is driven through its injected readers.
"""

import json

import pytest
from preflight_quiet import (
    IGNORE_PREFIXES,
    Process,
    Rate,
    busy_processes,
    certificate,
    decode_rate,
    load_problem,
    main,
)

PS = """\
  PID  %CPU COMM
    1   0.4 /sbin/launchd
  412  93.1 /usr/local/bin/omlx-server
  977  41.7 /Applications/Xcode.app/Contents/MacOS/Xcode
 1201   2.0 /usr/sbin/cfprefsd
"""

QUIET_PS = "  PID  %CPU COMM\n    1   0.4 /sbin/launchd\n"

STAMP = "2026-09-17 21:14:02,004 - omlx.server - INFO - [-] - "
SLOW = (
    STAMP + "Chat completion: model=Ornith-1.5-9B-MLX-8bit, 100 tokens in 20.00s "
    "(5.0 tok/s), prompt: 4000, finish_reason=stop, max_tokens=16000, request_max_tokens=16000"
)
FAST = (
    STAMP + "Chat completion: model=Ornith-1.5-9B-MLX-8bit, 900 tokens in 10.00s "
    "(90.0 tok/s), prompt: 5000, finish_reason=stop, max_tokens=16000, request_max_tokens=16000"
)
OTHER = (
    STAMP + "Chat completion: model=Some-Other-7B, 4000 tokens in 1.00s "
    "(4000.0 tok/s), prompt: 10, finish_reason=stop, max_tokens=16000, request_max_tokens=16000"
)
LOG = [SLOW, FAST]
MODEL = "Ornith-1.5-9B-MLX-8bit"


def test_load_problem_names_the_one_minute_load_over_the_ceiling() -> None:
    assert load_problem((9.5, 4.0, 2.0), 8, ceiling=0.5) == "load 9.5 > 4.0 (8 cores)"


def test_load_problem_is_quiet_at_the_ceiling() -> None:
    assert load_problem((4.0, 4.0, 2.0), 8, ceiling=0.5) is None


def test_busy_processes_reads_a_ps_snapshot_in_order() -> None:
    assert busy_processes(PS, cpu_floor=20.0, ignore_prefixes=()) == [
        Process(pid=412, comm="/usr/local/bin/omlx-server", cpu=93.1),
        Process(pid=977, comm="/Applications/Xcode.app/Contents/MacOS/Xcode", cpu=41.7),
    ]


def test_busy_processes_drops_a_process_whose_comm_starts_with_an_ignored_prefix() -> None:
    busy = busy_processes(PS, cpu_floor=20.0, ignore_prefixes=("/usr/local/bin/omlx-",))
    assert [process.pid for process in busy] == [977]


def test_busy_processes_keeps_a_process_no_ignored_prefix_matches() -> None:
    busy = busy_processes(PS, cpu_floor=20.0, ignore_prefixes=("/usr/sbin/", "/opt/"))
    assert [process.pid for process in busy] == [412, 977]


def test_busy_processes_is_quiet_at_the_cpu_floor() -> None:
    snapshot = "  PID  %CPU COMM\n  310  20.0 /usr/bin/python3\n"
    assert busy_processes(snapshot, cpu_floor=20.0, ignore_prefixes=()) == []


def test_busy_processes_reports_a_process_just_over_the_cpu_floor() -> None:
    snapshot = "  PID  %CPU COMM\n  310  20.1 /usr/bin/python3\n"
    assert busy_processes(snapshot, cpu_floor=20.0, ignore_prefixes=()) == [
        Process(pid=310, comm="/usr/bin/python3", cpu=20.1)
    ]


def test_busy_processes_skips_the_header_and_every_unparsable_line() -> None:
    snapshot = "  PID  %CPU COMM\n\nnot a row\n  310   x.y /usr/bin/python3\n  311  99.0 /usr/bin/yes\n"
    assert [p.pid for p in busy_processes(snapshot, cpu_floor=20.0, ignore_prefixes=())] == [311]


def test_the_default_ignore_prefixes_cover_the_model_server_and_the_system_agents() -> None:
    snapshot = (
        "  PID  %CPU COMM\n"
        "    1   0.4 /sbin/launchd\n"
        "  412  93.1 omlx-server\n"
        "  501  88.0 /Applications/oMLX.app/Contents/MacOS/oMLX\n"
        "  977  41.7 /Applications/Xcode.app/Contents/MacOS/Xcode\n"
        " 1201  77.0 /usr/sbin/cfprefsd\n"
    )
    busy = busy_processes(snapshot, cpu_floor=20.0, ignore_prefixes=IGNORE_PREFIXES)
    assert [process.pid for process in busy] == [977]


def test_decode_rate_is_token_weighted_not_the_mean_of_the_rates() -> None:
    rate = decode_rate(LOG, model=MODEL, last=2)
    assert rate is not None
    assert rate.completions == 2
    assert rate.tokens == 1000
    assert rate.seconds == pytest.approx(30.0)
    assert rate.tok_s == pytest.approx(1000 / 30.0)
    assert rate.tok_s != pytest.approx((5.0 + 90.0) / 2)


def test_decode_rate_reads_only_the_named_models_completions() -> None:
    rate = decode_rate([SLOW, OTHER, FAST], model=MODEL, last=2)
    assert rate is not None
    assert rate.tokens == 1000


def test_decode_rate_is_none_with_fewer_than_last_completions() -> None:
    assert decode_rate(LOG, model=MODEL, last=3) is None


def test_decode_rate_reads_exactly_last_completions() -> None:
    rate = decode_rate([SLOW, SLOW, FAST], model=MODEL, last=2)
    assert rate is not None
    assert rate.completions == 2
    assert rate.tokens == 1000


def test_decode_rate_ignores_lines_that_are_not_completions() -> None:
    noise = [
        "",
        "2026-09-17 21:10:00,000 - omlx.server - INFO - [-] - Loaded model",
        "Chat completion: model=Ornith-1.5-9B-MLX-8bit, 5 tokens in 1.00s (5.0 tok/s), prompt: 1,",
    ]
    rate = decode_rate([*noise, *LOG], model=MODEL, last=2)
    assert rate is not None
    assert rate.tokens == 1000


def test_certificate_is_empty_on_a_quiet_machine_and_records_its_inputs() -> None:
    rate = Rate(tok_s=41.0, completions=20, tokens=8200, seconds=200.0)
    result = certificate(None, [], rate, floor_tok_s=30.0, model=MODEL, last=20)
    assert result.problems == ()
    body = result.as_dict()
    assert body["problems"] == []
    assert body["inputs"]["load"] is None
    assert body["inputs"]["busy"] == []
    assert body["inputs"]["decode"] == {
        "tok_s": 41.0, "completions": 20, "tokens": 8200, "seconds": 200.0
    }
    assert body["inputs"]["floor_tok_s"] == 30.0
    assert body["inputs"]["model"] == MODEL
    assert body["inputs"]["last"] == 20
    assert json.loads(json.dumps(body)) == body


def test_certificate_lists_the_load_the_busy_and_the_slow_decode_in_order() -> None:
    busy = [Process(pid=977, comm="/Applications/Xcode.app/Contents/MacOS/Xcode", cpu=41.7)]
    rate = Rate(tok_s=18.4, completions=20, tokens=3680, seconds=200.0)
    result = certificate(
        "load 9.5 > 4.0 (8 cores)", busy, rate, floor_tok_s=30.0, model=MODEL, last=20
    )
    assert list(result.problems) == [
        "load 9.5 > 4.0 (8 cores)",
        "busy: /Applications/Xcode.app/Contents/MacOS/Xcode pid 977 at 41.7% cpu",
        "decode 18.4 tok/s < 30.0 over last 20 completions",
    ]
    assert result.as_dict()["inputs"]["busy"] == [
        {"pid": 977, "comm": "/Applications/Xcode.app/Contents/MacOS/Xcode", "cpu": 41.7}
    ]


def test_certificate_has_no_decode_problem_at_the_floor() -> None:
    rate = Rate(tok_s=30.0, completions=20, tokens=6000, seconds=200.0)
    result = certificate(None, [], rate, floor_tok_s=30.0, model=MODEL, last=20)
    assert result.problems == ()


def test_certificate_says_when_there_are_too_few_completions() -> None:
    result = certificate(None, [], None, floor_tok_s=30.0, model=MODEL, last=20)
    assert list(result.problems) == [f"decode: fewer than 20 completions for {MODEL}"]
    assert result.as_dict()["inputs"]["decode"] is None


def test_the_cli_prints_the_certificate_and_exits_zero_on_a_quiet_machine(capsys) -> None:
    code = main(
        ["--model", MODEL, "--floor-tok-s", "10", "--last", "2"],
        loadavg=lambda: (1.0, 1.0, 1.0),
        cores=lambda: 8,
        read_ps=lambda: QUIET_PS,
        read_log=lambda: LOG,
    )
    body = json.loads(capsys.readouterr().out)
    assert code == 0
    assert body["problems"] == []
    assert body["inputs"]["decode"]["completions"] == 2


def test_the_cli_exits_one_and_names_every_problem_on_a_loud_machine(capsys) -> None:
    code = main(
        ["--model", MODEL, "--floor-tok-s", "40", "--last", "2"],
        loadavg=lambda: (9.5, 4.0, 2.0),
        cores=lambda: 8,
        read_ps=lambda: PS,
        read_log=lambda: LOG,
    )
    body = json.loads(capsys.readouterr().out)
    assert code == 1
    assert body["problems"] == [
        "load 9.5 > 4.0 (8 cores)",
        "busy: /Applications/Xcode.app/Contents/MacOS/Xcode pid 977 at 41.7% cpu",
        "decode 33.3 tok/s < 40.0 over last 2 completions",
    ]
```

- [ ] **Step 2: Run the suite and watch every test fail**

Run the acceptance suite from the repository root with `scripts` on the path. Expect a collection error — `ModuleNotFoundError: No module named 'preflight_quiet'` — because the module does not exist yet. That failure is the starting point; do not write the module before seeing it.

```bash
PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q
```

- [ ] **Step 3: The load reading**

Create `scripts/preflight_quiet.py` with a module docstring, the three frozen dataclasses, the default constants and `load_problem`. `Process` carries `pid` (int), `comm` (str) and `cpu` (float); `Rate` carries `tok_s` (float), `completions` (int), `tokens` (int) and `seconds` (float); both are frozen and slotted. The defaults are module constants: `DEFAULT_CEILING` is 0.5, `DEFAULT_CPU_FLOOR` is 20.0, `DEFAULT_FLOOR_TOK_S` is 30.0, `DEFAULT_LAST` is 20, and `IGNORE_PREFIXES` is the tuple `("/sbin/", "/usr/sbin/", "/usr/libexec/", "/System/", "/usr/local/bin/omlx-", "omlx-", "/Applications/oMLX.app/")`. `load_problem` takes the three-tuple a load average comes in, the core count, and a keyword-only `ceiling`; it compares only the one-minute figure against `ceiling * cores` and returns `None` when the load is at or below that product — the ceiling itself is quiet — and otherwise the message, with the load and the product each formatted to one decimal place and the bare integer core count in parentheses.

```python
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
```

- [ ] **Step 4: The process snapshot**

Add `busy_processes`. It reads the output of `ps -axo pid,pcpu,comm`: one process per line, the first line a header. Split each line into at most three fields and skip any line that does not yield an integer pid, a float cpu and a non-empty command — that rule disposes of the header, blank lines and anything malformed without a special case for each. A process is busy when its cpu is **strictly greater** than `cpu_floor` and its command starts with none of `ignore_prefixes`; return the busy ones in the order they appeared in the snapshot.

```python
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
```

- [ ] **Step 5: The decode rate**

Add `decode_rate`. oMLX writes one server-log line per completion when it ends, of the shape `2026-09-17 21:14:02,004 - omlx.server - INFO - [-] - Chat completion: model=Ornith-1.5-9B-MLX-8bit, 900 tokens in 10.00s (90.0 tok/s), prompt: 5000, finish_reason=stop, max_tokens=16000, request_max_tokens=16000`. A line is a completion only when it carries both the timestamped `omlx.server - INFO` prefix and that whole `Chat completion: model=..., N tokens in Xs (R tok/s), prompt: P,` shape — a blank line, another logger's line, or a bare `Chat completion:` fragment without the stamp is not one. Keep the completions whose model is exactly `model`, in order. Return `None` when there are fewer than `last` of them; otherwise take the **last** `last` and return a `Rate` whose `tokens` and `seconds` are the sums over them and whose `tok_s` is `sum(tokens) / sum(seconds)`. The rate is token-weighted and never the mean of the per-completion rates: a 32-token completion must not weigh the same as an 8,000-token one, because the question is how fast tokens came out, not how fast the average request was.

```python
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
```

- [ ] **Step 6: The certificate**

Add `Certificate` and `certificate`. `Certificate` is frozen, with `problems` (a tuple of strings, empty when the machine is quiet) and `record` (a dict of the inputs); `as_dict()` returns `{"problems": [...], "inputs": {...}}`, where `inputs` has exactly the keys `load` (the load message or null), `busy` (a list of `{"pid", "comm", "cpu"}` objects in snapshot order), `decode` (null, or exactly `{"tok_s", "completions", "tokens", "seconds"}`), `floor_tok_s`, `model` and `last`, and the whole thing round-trips through `json.dumps`. The problems come in one order: the load message when there is one, then one `busy:` line per busy process with its cpu to one decimal place, then the decode problem. There are two decode problems and they are exclusive: when `rate` is `None` the message says fewer than `last` completions were found for `model`; otherwise, when the rate is **strictly less** than `floor_tok_s`, the message names the rate, the floor and the number of completions, the two rates to one decimal place. A rate exactly at the floor is quiet.

```python
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
```

- [ ] **Step 7: The CLI**

Add `main` and the two real readers. `main(argv=None, *, loadavg, cores, read_ps, read_log)` parses `--model ID` (required), `--ceiling F`, `--cpu-floor F`, `--floor-tok-s F` and `--last N`, whose defaults are the four module constants. It takes its four readings from the keyword-only callables — whose defaults are `os.getloadavg`, the core count, a `ps -axo pid,pcpu,comm` subprocess and a reader of the server log — so the acceptance suite can drive both directions on one machine without spawning anything. It calls the three pure functions, passes `IGNORE_PREFIXES` as the ignore list, prints `certificate(...).as_dict()` as JSON on stdout, and returns 0 when `problems` is empty and 1 when it is not.

```python
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
```

- [ ] **Step 8: Run the acceptance suite and watch it pass**

Run the suite again with `scripts` on the path and expect all twenty to pass, with no test edited to suit the implementation. Then run the repository's own checks — the whole default tier and the linter — and expect them green too.

```bash
PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q
just gates
```

- [ ] **Step 9: Record the provenance and commit**

Add a row for each new file to `PROVENANCE.md` with `uv run python tools/provenance.py new`, then commit the two new files and that row together, with explicit paths.
