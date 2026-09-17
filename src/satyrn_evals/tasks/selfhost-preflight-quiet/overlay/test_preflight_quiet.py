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

LOUD_PS = (
    "  PID  %CPU COMM\n"
    "    1   0.4 /sbin/launchd\n"
    "  310  19.9 /usr/bin/ruby\n"
    "  311  20.1 /usr/bin/python3\n"
    "  412  93.1 /usr/local/bin/omlx-server\n"
    "  977  41.7 /Applications/Xcode.app/Contents/MacOS/Xcode\n"
    " 1201   2.0 /usr/sbin/cfprefsd\n"
)

QUIET_PS = "  PID  %CPU COMM\n    1   0.4 /sbin/launchd\n  310  30.0 /usr/bin/python3\n"

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
    STAMP + "Chat completion: model=Ornith-1.5-9B-MLX-8bit-draft, 4000 tokens in 1.00s "
    "(4000.0 tok/s), prompt: 10, finish_reason=stop, max_tokens=16000, request_max_tokens=16000"
)
LOG = [SLOW, FAST]
LOG20 = [SLOW] * 20
MODEL = "Ornith-1.5-9B-MLX-8bit"


def test_load_problem_names_the_one_minute_load_over_the_ceiling() -> None:
    assert load_problem((9.5, 4.0, 2.0), 8, ceiling=0.5) == "load 9.5 > 4.0 (8 cores)"


def test_load_problem_is_quiet_at_the_ceiling() -> None:
    assert load_problem((4.0, 9.9, 9.9), 8, ceiling=0.5) is None


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
        "    1  55.0 /sbin/launchd\n"
        "  201  61.0 /usr/libexec/logd\n"
        "  301  49.0 /System/Library/CoreServices/Finder.app/Contents/MacOS/Finder\n"
        "  700  66.0 /Users/pauleveritt/opt/System/Library/helper\n"
        "  412  93.1 omlx-server\n"
        "  501  88.0 /Applications/oMLX.app/Contents/MacOS/oMLX\n"
        "  977  41.7 /Applications/Xcode.app/Contents/MacOS/Xcode\n"
        " 1201  77.0 /usr/sbin/cfprefsd\n"
    )
    busy = busy_processes(snapshot, cpu_floor=20.0, ignore_prefixes=IGNORE_PREFIXES)
    assert [process.pid for process in busy] == [700, 977]


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
    rate = decode_rate([*LOG, *noise], model=MODEL, last=2)
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
        ["--model", MODEL, "--ceiling", "1.0", "--cpu-floor", "50", "--floor-tok-s", "1", "--last", "2"],
        loadavg=lambda: (5.0, 1.0, 1.0),
        cores=lambda: 8,
        read_ps=lambda: QUIET_PS,
        read_log=lambda: [SLOW, SLOW],
    )
    body = json.loads(capsys.readouterr().out)
    assert code == 0
    assert body["problems"] == []
    assert body["inputs"]["decode"]["completions"] == 2


def test_the_cli_exits_one_and_names_every_problem_on_a_loud_machine(capsys) -> None:
    code = main(
        ["--model", MODEL],
        loadavg=lambda: (9.5, 4.0, 2.0),
        cores=lambda: 8,
        read_ps=lambda: LOUD_PS,
        read_log=lambda: LOG20,
    )
    body = json.loads(capsys.readouterr().out)
    assert code == 1
    assert body["problems"] == [
        "load 9.5 > 4.0 (8 cores)",
        "busy: /usr/bin/python3 pid 311 at 20.1% cpu",
        "busy: /Applications/Xcode.app/Contents/MacOS/Xcode pid 977 at 41.7% cpu",
        "decode 5.0 tok/s < 30.0 over last 20 completions",
    ]
    assert body["inputs"]["decode"]["completions"] == 20
