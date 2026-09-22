"""Decode rate read from the oMLX server log. Default tier: synthetic log text, no filesystem.

The log does not name the cell (Ruling 7), so these rules answer "how fast did
tokens come out of the machine while this cell ran", never "how fast was this
cell's own stream". Every rule has a firing row and a silent row.
"""

from datetime import datetime

from satyrn_evals.census_decode import (
    NO_COMPLETIONS,
    NO_DECODE_SECONDS,
    decode_rate,
    parse_completions,
    span_overlap,
)

LINE = (
    "2026-09-16 12:41:44,035 - omlx.server - INFO - [-] - Chat completion: "
    "model=Ornith-1.5-9B-MLX-8bit, {tok} tokens in {sec}s ({rate} tok/s), "
    "prompt: {prompt}, finish_reason=tool_calls, max_tokens=16000, request_max_tokens=16000"
)


def _line(ts: str, tok: int, sec: float, prompt: int = 1702) -> str:
    rate = round(tok / sec, 1) if sec else 0.0
    body = LINE.format(tok=tok, sec=sec, rate=rate, prompt=prompt)
    return ts + body[len("2026-09-16 12:41:44,035") :]


def _epoch(ts: str) -> float:
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f").astimezone().timestamp()


def test_a_completion_line_parses_into_tokens_seconds_and_the_local_instant() -> None:
    (one,) = parse_completions(_line("2026-09-16 12:41:44,035", 102, 4.11))
    assert (one.tokens, one.seconds, one.prompt, one.max_tokens) == (102, 4.11, 1702, 16000)
    assert one.ended == _epoch("2026-09-16 12:41:44,035")
    assert one.started == one.ended - 4.11


def test_a_line_for_another_model_is_not_a_completion() -> None:
    other = _line("2026-09-16 12:41:44,035", 102, 4.11).replace("Ornith-1.5-9B-MLX-8bit", "Some-Other-7B")
    assert parse_completions(other) == []


def test_a_line_that_is_not_a_completion_is_skipped() -> None:
    assert parse_completions("2026-09-16 12:41:44,035 - omlx.scheduler - INFO - [-] - Cache phase timings: x\n") == []


def test_the_rate_is_token_weighted_not_a_per_completion_mean() -> None:
    """Ruling 8: 1,900 tokens in 30 decode seconds is 63.3 tok/s, though the
    per-completion median is 90."""
    text = "\n".join(
        [
            _line("2026-09-16 12:00:10,000", 100, 10.0),
            _line("2026-09-16 12:00:30,000", 900, 10.0),
            _line("2026-09-16 12:00:50,000", 900, 10.0),
        ]
    )
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert reading.completions == 3
    assert round(reading.tok_s, 1) == 63.3
    assert reading.median_tok_s == 90.0
    assert reading.reason is None


def test_a_completion_that_began_before_the_span_is_not_attributed() -> None:
    text = _line("2026-09-16 12:00:05,000", 100, 10.0)   # started 11:59:55
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert (reading.tok_s, reading.completions, reading.reason) == (None, 0, NO_COMPLETIONS)


def test_a_completion_that_ended_after_the_span_is_not_attributed() -> None:
    text = _line("2026-09-16 12:01:05,000", 100, 10.0)
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert (reading.tok_s, reading.completions, reading.reason) == (None, 0, NO_COMPLETIONS)


def test_attributed_completions_with_no_decode_seconds_are_a_stated_reason() -> None:
    """Ruling 10: a null rate always says why."""
    text = _line("2026-09-16 12:00:30,000", 0, 0.0)
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert reading.completions == 1
    assert (reading.tok_s, reading.median_tok_s, reading.reason) == (None, None, NO_DECODE_SECONDS)


def test_span_overlap_counts_the_nights_concurrent_cells_including_this_one() -> None:
    spans = [(0.0, 100.0), (50.0, 150.0), (140.0, 200.0)]
    assert span_overlap(spans, 0.0, 100.0) == 2
    assert span_overlap(spans, 50.0, 150.0) == 3


def test_a_cell_that_shared_the_machine_with_nobody_overlaps_only_itself() -> None:
    assert span_overlap([(0.0, 100.0)], 0.0, 100.0) == 1


def test_a_zero_second_completion_does_not_inflate_the_rate() -> None:
    """S5-6: a completion reporting zero decode seconds must not add its tokens
    to the numerator while contributing nothing to the denominator -- that
    inflates tok_s for the whole span."""
    text = "\n".join(
        [
            _line("2026-09-16 12:00:10,000", 100, 10.0),
            _line("2026-09-16 12:00:20,000", 5000, 0.0),
        ]
    )
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert reading.completions == 2
    assert reading.tok_s == 10.0


def test_a_completion_with_real_seconds_is_unaffected_by_the_zero_second_fix() -> None:
    """The sibling: when nothing reports zero seconds, the rate is unchanged."""
    text = "\n".join(
        [
            _line("2026-09-16 12:00:10,000", 100, 10.0),
            _line("2026-09-16 12:00:30,000", 100, 10.0),
        ]
    )
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert reading.tok_s == 10.0
