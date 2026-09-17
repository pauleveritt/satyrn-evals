"""The probe's numbers from recorded-format oMLX log lines; the driver against a fake server. No network."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from speed_probe import (  # noqa: E402
    CONCURRENCY,
    CONTEXT_SIZES,
    analyze,
    choose_k,
    decode_by_size,
    filler,
    main,
    nearest_size,
    parse_line,
    run,
    total_throughput,
)

MODEL = "Ornith-1.5-9B-MLX-8bit"
#: Verbatim from ~/.omlx/logs/server.log, 2026-09-14.
RECORDED = (
    "2026-09-14 09:51:27,151 - omlx.server - INFO - [-] - Chat completion: model=Ornith-1.5-9B-MLX-8bit, "
    "758 tokens in 30.62s (27.3 tok/s), prompt: 44644, finish_reason=stop, max_tokens=32000, request_max_tokens=32000"
)
T0 = 1_800_000_000.0


def _line(ended: float, tokens: int, seconds: float, rate: float, prompt: int, model: str = MODEL) -> str:
    stamp = datetime.fromtimestamp(ended).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    return (
        f"{stamp} - omlx.server - INFO - [-] - Chat completion: model={model}, {tokens} tokens in {seconds}s "
        f"({rate} tok/s), prompt: {prompt}, finish_reason=stop, max_tokens=512, request_max_tokens=512"
    )


def test_a_recorded_completion_line_parses() -> None:
    completion = parse_line(RECORDED)
    assert completion is not None
    assert (completion.model, completion.tokens, completion.seconds, completion.rate, completion.prompt) == (MODEL, 758, 30.62, 27.3, 44644)
    assert completion.started == pytest.approx(completion.ended - 30.62)


@pytest.mark.parametrize(
    "line",
    [
        "2026-09-13 02:00:48,606 - omlx.scheduler - INFO - [-] - Cache phase timings: boundary_capture_extract=26.9ms/1294",
        "",
        "Chat completion: model=x, 1 tokens in 1s (1 tok/s), prompt: 1,",
    ],
)
def test_every_other_line_is_not_a_completion(line: str) -> None:
    assert parse_line(line) is None


def test_a_prompt_counts_for_the_nearest_size_within_a_quarter() -> None:
    assert nearest_size(21_000) == 20_000
    assert nearest_size(160_000 * 0.76) == 160_000
    assert nearest_size(60_000) is None


def test_decode_rate_is_the_median_per_size() -> None:
    lines = [_line(T0 + i, 100, 3.0, rate, prompt) for i, (rate, prompt) in enumerate([(50.0, 5_100), (48.0, 4_900), (52.0, 5_000), (30.0, 81_000)])]
    completions = [c for c in map(parse_line, lines) if c is not None]
    assert decode_by_size(completions) == {5_000: 50.0, 80_000: 30.0}


def test_total_throughput_spans_first_start_to_last_end() -> None:
    completions = [c for c in (parse_line(_line(T0 + 10, 400, 10.0, 40.0, 5_000)), parse_line(_line(T0 + 12, 400, 10.0, 40.0, 5_000))) if c]
    assert total_throughput(completions) == pytest.approx(800 / 12)
    with pytest.raises(ValueError, match="no completions"):
        total_throughput([])


@pytest.mark.parametrize(
    ("throughput", "k"),
    [({1: 40.0, 2: 59.9, 3: 59.0}, 1), ({1: 40.0, 2: 60.0, 3: 59.0}, 2), ({1: 40.0, 2: 70.0, 3: 90.0}, 3), ({1: 40.0, 2: 50.0, 3: 61.0}, 3)],
)
def test_k_is_the_largest_concurrency_at_one_and_a_half_times_single_stream(throughput: dict[int, float], k: int) -> None:
    assert choose_k(throughput) == k


def test_k_needs_the_single_stream_measure() -> None:
    with pytest.raises(ValueError, match="k = 1"):
        choose_k({2: 80.0})


def _plan_and_log() -> tuple[dict, list[str]]:
    lines, context = [], []
    for index, size in enumerate(CONTEXT_SIZES):
        start = T0 + index * 100
        lines.append(_line(start + 50, 512, 40.0, 50.0 - index * 5, size + 37))
        context.append({"size": size, "start": start, "end": start + 99})
    concurrency = []
    for index, k in enumerate(CONCURRENCY):
        start = T0 + 1000 + index * 1000
        for stream in range(k):
            lines.append(_line(start + 100, 1000, 100.0, 45.0, 5_000 + stream))
        lines.append(_line(start + 100, 999, 1.0, 45.0, 5_000, model="gemma-4-12B-it-MLX-8bit"))
        concurrency.append({"k": k, "start": start, "end": start + 999})
    lines.insert(3, "2026-09-14 00:00:00,000 - omlx.scheduler - INFO - [-] - noise")
    return {"model": MODEL, "context": context, "concurrency": concurrency}, lines


def test_the_analysis_reports_decode_by_size_throughput_by_k_and_k() -> None:
    plan, lines = _plan_and_log()
    report = analyze(plan, lines)
    assert report["decode_tok_s_by_prompt"] == {"5000": 50.0, "20000": 45.0, "40000": 40.0, "80000": 35.0, "160000": 30.0}
    assert report["missing_sizes"] == []
    assert report["total_tok_s_by_k"] == {"1": 10.0, "2": 20.0, "3": 30.0}
    assert report["k"] == 3


def test_the_analyze_command_reads_the_plan_and_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plan, lines = _plan_and_log()
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    (tmp_path / "server.log").write_text("\n".join(lines) + "\n")
    assert main(["analyze", "--plan", str(tmp_path / "plan.json"), "--log", str(tmp_path / "server.log")]) == 0
    assert json.loads(capsys.readouterr().out)["k"] == 3


def test_the_analyze_command_refuses_a_phase_with_no_completions(tmp_path: Path) -> None:
    plan, lines = _plan_and_log()
    plan["concurrency"][0]["start"] = plan["concurrency"][0]["end"] = 0.0
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    (tmp_path / "server.log").write_text("\n".join(lines))
    assert main(["analyze", "--plan", str(tmp_path / "plan.json"), "--log", str(tmp_path / "server.log")]) == 2


# --- F9/R13: per-phase counts, and a lost stream must not be silent ---


def test_the_analysis_reports_per_phase_completion_counts() -> None:
    plan, lines = _plan_and_log()
    report = analyze(plan, lines)
    assert report["context_completions_by_size"] == {
        "5000": 1, "20000": 1, "40000": 1, "80000": 1, "160000": 1,
    }
    assert report["concurrency_completions_by_k"] == {"1": 1, "2": 2, "3": 3}


def test_the_filler_approximates_the_requested_size() -> None:
    assert 19_000 * 4 <= len(filler(20_000)) <= 20_000 * 4


class _FakeServer:
    def __init__(self) -> None:
        self.bodies: list[dict] = []

    def __call__(self, request: object, timeout: float) -> object:
        self.bodies.append(json.loads(request.data))  # type: ignore[attr-defined]
        time.sleep(0.005)
        server = self

        class _Response:
            def __enter__(self) -> _Response:
                return self

            def __exit__(self, *exc: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"n": len(server.bodies)}).encode()

        return _Response()


def test_the_driver_times_every_phase_and_streams_model_messages_and_max_tokens() -> None:
    server = _FakeServer()
    plan = run("http://fake/v1", MODEL, streams_seconds=0.05, max_tokens=64, opener=server)
    assert [phase["size"] for phase in plan["context"]] == list(CONTEXT_SIZES)
    assert [phase["k"] for phase in plan["concurrency"]] == list(CONCURRENCY)
    assert all(phase["start"] < phase["end"] for phase in [*plan["context"], *plan["concurrency"]])
    assert {tuple(sorted(body)) for body in server.bodies} == {("max_tokens", "messages", "model", "stream")}
    assert all(body["stream"] is True for body in server.bodies)
    assert len(server.bodies) >= len(CONTEXT_SIZES) + sum(CONCURRENCY)
    assert all(phase["requests"] == 1 and phase["errors"] == 0 for phase in plan["context"])
    assert all(phase["errors"] == 0 for phase in plan["concurrency"])
    assert all(phase["requests"] >= phase["k"] for phase in plan["concurrency"])


class _FailingOpener:
    """Succeeds every context request, then fails every concurrency request."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request: object, timeout: float) -> object:
        self.calls += 1
        if self.calls > len(CONTEXT_SIZES):
            raise OSError("connection reset")

        class _Response:
            def __enter__(self) -> _Response:
                return self

            def __exit__(self, *exc: object) -> None:
                return None

            def read(self) -> bytes:
                return b"{}"

        return _Response()


def test_a_lost_stream_is_counted_as_an_error_not_silently_dropped() -> None:
    plan = run("http://fake/v1", MODEL, streams_seconds=0.02, max_tokens=8, opener=_FailingOpener())
    assert all(phase["errors"] == 0 and phase["requests"] == 1 for phase in plan["context"])
    assert all(phase["errors"] > 0 for phase in plan["concurrency"])
    assert all(phase["requests"] == 0 for phase in plan["concurrency"])


def test_main_run_exits_non_zero_when_the_plan_reports_a_stream_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import speed_probe

    monkeypatch.setattr(
        speed_probe,
        "run",
        lambda *a, **k: {
            "model": MODEL, "base_url": "x",
            "context": [{"size": 5000, "start": 0, "end": 1, "requests": 1, "errors": 0}],
            "concurrency": [{"k": 1, "start": 0, "end": 1, "requests": 2, "errors": 1}],
        },
    )
    plan_path = tmp_path / "plan.json"
    assert main(["run", "--model", MODEL, "--plan", str(plan_path)]) == 2
    assert json.loads(plan_path.read_text())["concurrency"][0]["errors"] == 1


def test_main_run_exits_zero_when_every_phase_is_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import speed_probe

    monkeypatch.setattr(
        speed_probe,
        "run",
        lambda *a, **k: {
            "model": MODEL, "base_url": "x",
            "context": [{"size": 5000, "start": 0, "end": 1, "requests": 1, "errors": 0}],
            "concurrency": [{"k": 1, "start": 0, "end": 1, "requests": 3, "errors": 0}],
        },
    )
    plan_path = tmp_path / "plan.json"
    assert main(["run", "--model", MODEL, "--plan", str(plan_path)]) == 0
