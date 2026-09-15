"""Tell an infrastructure failure apart from a model-side one.

A cell whose inference substrate failed underneath it measured nothing.
Counting it as a refusal understates the arm, which is what voided the
first V11c mini-probe: a GPU out-of-memory scored as ``NO_PATCH``.

**Both shapes look identical in the obvious fields.** A runtime fault and
a genuine context exhaustion each end the cell with
``stopReason: "error"`` and ``totalTokens: 0``, so neither can be the
rule -- three screens were tried on 2026-09-05 and two over-fired
(`'"stopReason":"error"'` hit the exhaustion cell; `'"totalTokens":0'`
matched all twelve cells including four passes). The ``errorMessage`` is
the only field carrying the cause.

**The rule.** It asks the question HTTP already answers: *did the server
reply, and did it blame the request or itself?*

* **4xx — the server answered and blamed the request.** It was reached and
  rejected the input on its own terms (a context overflow is the case on
  record). Model-side; stays in the denominator.
* **5xx — the server answered and blamed itself.** A provider or runtime
  failure. pi agrees: its own retry layer treats 500/502/503/504 and
  "overloaded" as *transient provider errors* and retries them, so a 5xx
  reaching the terminal turn is a substrate failure that survived pi's
  retries. Infrastructure.
* **No status at all** — a fault raised inside the stream, which is how
  the recorded GPU out-of-memory arrives. Infrastructure.
* **A stop reason pi rendered itself** (``Provider finish_reason: ...``,
  e.g. ``content_filter``) is a model-side outcome with no status.

An earlier draft keyed on the literal ``"400: "`` prefix. That was a
pattern match on pi's punctuation, not a classification: pi emits
``"<status>: <body>"`` only when the provider returns a structured error
body, and renders ``"<status> <message>"`` otherwise — so the same
context overflow from a server that returns a bare string would have been
called infrastructure. The status number is the signal; the separator is
not.

**It leans toward reporting.** An errored turn with no cause given is
called infrastructure. Under report-never-drop that over-call is visible
for the maintainer to overturn, whereas the behaviour it replaces --
infrastructure silently counted as ``NO_PATCH`` -- is invisible. The cost
is stated: a model-side failure arriving without a status code inflates
apparent infrastructure trouble rather than hiding a refusal.

**Absent evidence is never a finding.** An empty, unparseable, or
terminal-turn-less transcript yields ``None`` -- V10's "unmeasured, never
zero" discipline, which four silent-zero incidents paid for.

Read from the preserved transcript, never from an exit code
(`BRIEF.md` rule 4).
"""

import json
import re

#: A leading HTTP status, however pi separated it from the body: it emits
#: ``"<status>: <body>"`` when the provider returned a structured error
#: object and ``"<status> <message>"`` when it did not. Both are the
#: server answering; only the number carries meaning.
_LEADING_STATUS = re.compile(r"^\s*(\d{3})\b")

#: pi's own rendering of a model-side stop reason, which carries no status.
_PROVIDER_STOP = re.compile(r"^\s*Provider finish_reason\s*:", re.IGNORECASE)

#: pi's own declaration that the turn ended in an error (`pi_session.py`).
#: ``length`` (output cap) and ``stop`` are model-side and never faults.
_ERROR_STOPS = frozenset({"error"})


def infrastructure_failure(transcript_text: str) -> str | None:
    """The substrate fault that ended this attempt, or ``None``.

    Returns the ``errorMessage`` when the terminal turn failed for a
    reason the model server did not answer for; ``None`` when the cell
    ended normally, hit its own output cap, was rejected by the server on
    its own terms, or when the transcript says nothing either way.
    """
    terminal = _terminal_message(transcript_text)
    if terminal is None:
        return None
    if terminal.get("stopReason") not in _ERROR_STOPS:
        return None
    error = terminal.get("errorMessage")
    if not isinstance(error, str) or not error.strip():
        return "the terminal turn errored without naming a cause"
    if _PROVIDER_STOP.match(error):
        return None  # a model-side stop reason pi rendered itself
    if (status := _LEADING_STATUS.match(error)) is not None:
        # 4xx: the server blamed the request. 5xx: it blamed itself, and
        # pi already retried it as a transient provider error.
        return None if status.group(1).startswith("4") else error.strip()
    return error.strip()


def _terminal_message(text: str) -> dict | None:
    """The last ``turn_end`` message, or None if there is not one to read."""
    terminal: dict | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # a live transcript can carry a partial or noisy line
        if not isinstance(event, dict) or event.get("type") != "turn_end":
            continue
        message = event.get("message")
        if isinstance(message, dict):
            terminal = message
    return terminal
