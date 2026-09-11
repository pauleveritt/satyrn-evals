#!/usr/bin/env python3
"""Publish the V3 Track B gate: every inventory claim one final status.

Pure over the frozen inventory. ``render_gate`` turns ``closeout_rows`` into
the enumerated gate table — a status for every entry — and ``main`` writes
``docs/current/phase-v-track-b-gate.md`` and registers the page in the hidden
toctree. No model, no network, no subprocess. The gate originates no figure;
it only settles each inventory record.

The hand-written sections (``## Reopen decisions`` and ``## Carrier review``)
live below a marker line and are preserved across regeneration; only the
generated table and carrier-lag line are rewritten.
"""

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from satyrn_evals.claim_closeout import CloseoutRow, carrier_lag, closeout_rows

DEFAULT_OUTPUT = Path("docs/current/phase-v-track-b-gate.md")
INDEX = Path("docs/current/index.md")
TOCTREE_ENTRY = "phase-v-track-b-gate"
TOCTREE_ANCHOR = "phase-v-claim-inventory\n"
#: Everything from this marker to EOF is hand-written and preserved.
MARKER = "<!-- hand-written below; do not regenerate -->"
_HANDWRITTEN_HEADERS = ("## Reopen decisions", "## Carrier review")


def render_gate(rows: Sequence[CloseoutRow]) -> str:
    """The enumerated inventory as a Markdown table plus a status summary.

    A ``not_derivable`` row renders its named missing artifact; a row with no
    missing artifact renders ``—``. The summary is computed from the rows,
    never hard-coded, so a status change cannot drift from the table.
    """
    counts = Counter(row.status for row in rows)
    lines = [
        "# Phase V — Track B gate",
        "",
        "Every inventory claim carries exactly one final status, and no carrier "
        "lags its source. The table below is the enumerated inventory — a status "
        "for every entry — that Track B opens on.",
        "",
        "| claim_id | level | status | missing |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.claim_id} | {row.level} | {row.status} | "
            f"{row.missing or '—'} |"
        )
    summary = (
        f"**Status:** {counts['confirmed']} confirmed, {counts['corrected']} "
        f"corrected, {counts['not_derivable']} not_derivable, "
        f"{counts['claim_measure_mismatch']} claim_measure_mismatch, "
        f"of {len(rows)} records."
    )
    lines.extend(("", summary))
    return "\n".join(lines) + "\n"


def render_carrier_lag(lag: Sequence[str]) -> str:
    """The carrier-lag check as a section, or the explicit none.

    A lagging carrier is a hard failure for the gate; an empty list is the
    pass state and is stated, never left implicit.
    """
    if not lag:
        return "\n**Carrier lag:** none.\n"
    body = "\n".join(f"- {cite}" for cite in lag)
    return f"\n**Carrier lag (hard failure):**\n{body}\n"


def _ensure_toctree_entry(index: Path, entry: str) -> None:
    text = index.read_text(encoding="utf-8")
    if f"\n{entry}\n" in text:
        return
    if TOCTREE_ANCHOR not in text:
        raise RuntimeError(f"toctree anchor missing from {index}")
    index.write_text(
        text.replace(TOCTREE_ANCHOR, TOCTREE_ANCHOR + entry + "\n", 1),
        encoding="utf-8",
    )


def _handwritten_suffix(existing: str) -> str | None:
    """The marker-and-after suffix, or None when the marker is absent."""
    idx = existing.find(MARKER)
    if idx == -1:
        return None
    return existing[idx:]


def _has_handwritten(existing: str) -> bool:
    return any(header in existing for header in _HANDWRITTEN_HEADERS)


def _write_gate(output: Path, generated: str, *, force: bool) -> None:
    """Write the generated body, preserving the hand-written suffix.

    With the marker present, everything after it is kept verbatim. When the
    hand-written sections exist without the marker, refuse to clobber them
    unless ``force`` is set.
    """
    if output.exists() and not force:
        existing = output.read_text(encoding="utf-8")
        suffix = _handwritten_suffix(existing)
        if suffix is not None:
            output.write_text(
                generated.rstrip("\n") + "\n\n" + suffix,
                encoding="utf-8",
            )
            return
        if _has_handwritten(existing):
            raise RuntimeError(
                f"{output} has hand-written sections without the {MARKER!r} "
                "marker; pass --force to overwrite them"
            )
    output.write_text(generated, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite hand-written sections instead of preserving them",
    )
    args = parser.parse_args(argv)

    lag = carrier_lag()
    generated = render_gate(closeout_rows()) + render_carrier_lag(lag)
    if args.check:
        print(generated)
        return 1 if lag else 0
    _write_gate(args.output, generated, force=args.force)
    _ensure_toctree_entry(args.index, TOCTREE_ENTRY)
    print(f"wrote {args.output}")
    return 1 if lag else 0


if __name__ == "__main__":
    raise SystemExit(main())
