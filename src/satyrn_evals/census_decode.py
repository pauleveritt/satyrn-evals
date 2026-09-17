"""Decode rate per cell, read offline from the oMLX server log.

Night-2 design section 3.3: no harness change and no new clock. The server log
records one line per chat completion carrying the wall-clock instant it
finished, the seconds it decoded for and the tokens it produced; a cell's span
is its attempt directory's UTC stamp to `attempt.json`'s mtime. Text in,
numbers out -- the night driver does the globbing and owns the spans.

**The log does not name the cell** (Ruling 7). A completion line has a model, a
size, a duration and a finish reason, and no session, request or cell id. At
k = 3 up to three cell spans overlap, so a completion inside the overlap is
attributed to all three: this module reports *the machine's decode rate while
the cell ran*, which is the contention number the design asks for, and never a
private per-cell stream. `span_overlap` puts the sharing on the row as a number.

Timestamps in the log are naive **local** time (Ruling 9); attempt stamps are
UTC. Both become epoch seconds before anything is compared.

The pattern is `run-2/serverlog.py`'s, unchanged, so the census parses the log
exactly as the committed counterfactual parsed it.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from statistics import median

#: `evidence/2026-09-15-finishing-counterfactual/run-2/serverlog.py`, verbatim.
_COMPLETION = re.compile(
    r"^(?P<ts>\S+ \S+) .*Chat completion: model=(?P<model>[^,]+), (?P<tok>\d+) tokens "
    r"in (?P<sec>[\d.]+)s \((?P<rate>[\d.]+) tok/s\), prompt: (?P<prompt>\d+), "
    r"finish_reason=(?P<fin>\w+), max_tokens=(?P<mt>\d+)"
)

#: The four reasons a `decode_tok_s` is null (Ruling 10). The last two are the
#: driver's: it owns the attempt directory and `attempt.json`.
NO_COMPLETIONS = "no completions in the cell's span"
NO_DECODE_SECONDS = "attributed completions report no decode seconds"
NO_STAMP = "no attempt stamp in the directory name"
NO_ATTEMPT_JSON = "attempt.json is missing or unreadable"


@dataclass(frozen=True, slots=True)
class Completion:
    """One served completion: when it finished, how long it decoded, how much it produced."""

    ended: float
    seconds: float
    tokens: int
    prompt: int
    max_tokens: int

    @property
    def started(self) -> float:
        return self.ended - self.seconds


@dataclass(frozen=True, slots=True)
class DecodeReading:
    """`tok_s` is token-weighted (Ruling 8); `median_tok_s` is the per-completion median,
    carried because `run-2/q3stats.md`'s bins are medians. `reason` is non-null exactly
    when `tok_s` is null."""

    tok_s: float | None
    median_tok_s: float | None
    completions: int
    tokens: int
    seconds: float
    reason: str | None


def parse_completions(text: str, *, model_contains: str = "Ornith-1.5-9B") -> list[Completion]:
    """Every completion line for the census model, in log order."""
    out: list[Completion] = []
    for line in text.splitlines():
        match = _COMPLETION.match(line)
        if match is None or model_contains not in match["model"]:
            continue
        # Naive stamp: this machine's local time, the machine that also wrote
        # the attempt directories (Ruling 9).
        ended = datetime.strptime(match["ts"], "%Y-%m-%d %H:%M:%S,%f").astimezone()
        out.append(
            Completion(
                ended=ended.timestamp(),
                seconds=float(match["sec"]),
                tokens=int(match["tok"]),
                prompt=int(match["prompt"]),
                max_tokens=int(match["mt"]),
            )
        )
    return out


def decode_rate(completions: Sequence[Completion], *, start: float, end: float) -> DecodeReading:
    """The machine's decode rate over the completions wholly inside `[start, end]`.

    A completion counts only when it both began and ended inside the span: a
    completion straddling the boundary decoded partly for some other cell's
    wall clock and would bias the rate with seconds the span did not contain.
    """
    inside = [c for c in completions if start <= c.started and c.ended <= end]
    if not inside:
        return DecodeReading(None, None, 0, 0, 0.0, NO_COMPLETIONS)
    tokens = sum(c.tokens for c in inside)
    seconds = sum(c.seconds for c in inside)
    rates = [c.tokens / c.seconds for c in inside if c.seconds > 0]
    if seconds <= 0 or not rates:
        return DecodeReading(None, None, len(inside), tokens, seconds, NO_DECODE_SECONDS)
    return DecodeReading(
        tok_s=tokens / seconds,
        median_tok_s=median(rates),
        completions=len(inside),
        tokens=tokens,
        seconds=seconds,
        reason=None,
    )


def span_overlap(spans: Sequence[tuple[float, float]], start: float, end: float) -> int:
    """How many of the night's cell spans intersect `[start, end]`, this one included.

    The honest statement of Ruling 7's limit: the log cannot say which cell a
    completion belonged to, so this says how many it could have belonged to.
    """
    return sum(1 for s, e in spans if s < end and start < e)
