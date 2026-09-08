#!/usr/bin/env python
"""Measure an attempt's setup/command/grading durations from the filesystem.

Why this exists
----------------
`docs/current/first-smoke-run-record.md` (section "Timing measurement") needs
setup, command, grading, and total durations for the first live smoke, but
`satyrn-evals attempt()`/`run()` record none of these on a normal completion
(BRIEF.md: "Measure setup, command, and grading durations before proposing
infrastructure optimization" -- there is no harness instrumentation to read).
The record's answer is to derive them *externally*, from filesystem evidence
that already exists beside every attempt:

- ``patch.diff`` and ``transcript.txt`` are written by the attempt command
  itself, before grading runs.
- ``receipt.json`` and ``attempt.json`` are written afterward, by grading and
  by the attempt's own bookkeeping.

A wrapper that records a monotonic timestamp on either side of the whole
``satyrn-evals run`` invocation, plus the four files' modification times
in between, can therefore reconstruct an approximate phase decomposition
without touching the harness at all.

The discipline this file is built around
-----------------------------------------
**These are filesystem observations, not instrumented spans.** An mtime is a
coarse, best-effort boundary: it records when a file was last written, not
when a logical phase began or ended, and is truncated to the filesystem's own
timestamp resolution. Every span this module reports is documented as such,
never presented as if it came from real instrumentation.

**Absent is not zero** (the same discipline as ``scripts/token_floor.py``).
A REFUSED attempt -- no ``receipt.json`` (grading never produced a verdict),
or no ``transcript.txt`` (the command never delivered one) -- leaves the
dependent phases MISSING, named with a reason, never reported as `0`.  The
total is still reported: it comes from the wrapper's own clock, not from the
missing artifacts.

**Refuse rather than fabricate a coherent-looking but wrong number.**
Incoherent input (an end before its start, an artifact that predates the
wrapper's own start, a receipt older than the transcript it grades, or any
other span that would come out negative) raises :class:`TimingError` naming
the exact values observed, rather than silently reporting a negative or
clamped duration.

**Preservation and cleanup are a residual, never summed in.** The record is
explicit that the interval from the receipt's mtime to the wrapper's end
(preservation, offline regrade comparison, and cleanup) is reported
separately from setup/command/grading, and must not be added into them --
regrade rewrites ``receipt.json``/``attempt.json`` and destroys the mtimes
this method reads, so that comparison runs on a copy and this residual is
the only honest thing to say about the time around it.

**Do not silently mix clock domains.** ``time.monotonic()`` (used for the
authoritative total, immune to wall-clock adjustments) and file mtimes
(wall-clock, from ``time.time()``'s domain) are different clocks. The run
entry point below captures both explicitly and records which one produced
which figure, rather than comparing them as if they were interchangeable.

**These are filesystem intervals between named artifact events, not
lifecycle phases.** ``phases["setup"]``, ``phases["command"]``, and
``phases["grading"]`` are named for the lifecycle stage each interval was
*designed* to approximate, but a retained cell
(``2026-09-08-first-smoke-123843/cell-000-engine/``
``agentclinic-repair-depth-3-20260908-123925-900511``) shows the boundary
artifacts do not line up with those stages cleanly:

- The engine creates ``transcript.txt`` **after** command startup has
  already begun, so the ``setup`` interval (wrapper start -> transcript
  birth) absorbs part of true command startup, and ``command`` (transcript
  birth -> transcript mtime) understates the real command duration.
- ``patch.diff`` is published **after** the transcript's final write --
  verified on that cell: ``transcript.txt`` mtime ``08:39:55.982429``,
  ``patch.diff`` birth ``08:39:56.004320``, 22 ms later. So the ``grading``
  interval (transcript mtime -> receipt mtime) also contains patch
  publication and other preservation work, not grading alone. The residual
  (receipt mtime -> wrapper end) therefore cannot represent all
  preservation either, since some of it already happened before the
  receipt was written.

Every :class:`TimingResult` therefore carries ``interval_definitions``
(what each ``phases``/``residual`` key literally measures, in artifact-mtime
terms), a ``lifecycle_durations`` marker stating plainly that true setup,
command, grading, and preservation durations are **UNMEASURED** by this
filesystem method, and ``producer_ordering_limitation`` naming the reason
above. The ``phases`` dict keys are kept as-is (not renamed) so existing
callers and tests keep working; the added fields are what make the
distinction between "artifact interval" and "lifecycle phase" explicit
rather than implied by a comment.

Layout assumed
---------------
A "cell directory" (one schedule cell, e.g. ``$RUNS_ROOT/cell-000-engine``)
holds exactly one inner attempt directory named ``<task>-<stamp>`` (see
``satyrn_evals.attempt.attempt_dir_name``), which in turn holds
``patch.diff``, ``transcript.txt``, ``receipt.json``, and ``attempt.json``.
This module is given the *cell* directory and locates that inner directory
itself, exactly as the record describes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA_VERSION = 1

# The four artifacts read, in the order the record names them. Command end is
# transcript.txt's mtime; grading runs transcript.txt -> receipt.json;
# preservation/cleanup is the residual from receipt.json -> wrapper end.
ARTIFACT_NAMES: tuple[str, ...] = (
    "patch.diff",
    "transcript.txt",
    "receipt.json",
    "attempt.json",
)

#: ``attempt.py``'s ``attempt_dir_name``: <task>-<YYYYmmdd-HHMMSS-ffffff>.
#: A real cell also holds ``engine-contracts/``, so the attempt directory is
#: selected by this shape rather than by being the only subdirectory.
_ATTEMPT_DIR_RE = re.compile(r"-\d{8}-\d{6}-\d{6}$")

_MEASUREMENT_SOURCE = (
    "filesystem modification times of patch.diff, transcript.txt, "
    "receipt.json, and attempt.json inside the attempt directory located "
    "under the given cell directory, compared against wrapper start/end "
    "timestamps supplied by the caller"
)
_BOUNDARY_NOTE = (
    "these boundaries are filesystem observations, not instrumented spans, "
    "and are reported with that precision limit rather than as harness "
    "measurements; preservation and cleanup are reported as a residual "
    "(receipt mtime to wrapper end) and are NOT added into setup/command/"
    "grading above"
)
_WALL_CLOCK_TOTAL_SOURCE = (
    "wall-clock wrapper bounds (time.time domain), the same clock domain "
    "as the file mtimes compared above"
)

#: What each ``phases``/``residual`` key literally measures, in terms of the
#: artifact-mtime boundary it spans -- NOT the lifecycle phase its name
#: suggests. Kept as a flat mapping so a caller can print or record the exact
#: boundary alongside the number, rather than trusting the key's English name.
_INTERVAL_DEFINITIONS: dict[str, str] = {
    "setup": (
        "wrapper_start -> transcript.txt birth time (a filesystem interval; "
        "not a measured setup duration -- it absorbs part of true command "
        "startup, since the engine creates transcript.txt after the command "
        "has already begun)"
    ),
    "command": (
        "transcript.txt birth time -> transcript.txt mtime (a filesystem "
        "interval; understates true command duration for the same reason "
        "'setup' overstates it)"
    ),
    "setup_and_command": (
        "wrapper_start -> transcript.txt mtime (a filesystem interval; "
        "combined because this filesystem records no birth time to split it)"
    ),
    "grading": (
        "transcript.txt mtime -> receipt.json mtime (a filesystem interval; "
        "not grading alone -- patch.diff is published after the final "
        "transcript write, so this interval also contains patch publication "
        "and other preservation work that happens before the receipt exists)"
    ),
    "residual": (
        "receipt.json mtime -> wrapper_end (a filesystem interval; cannot "
        "represent all preservation work, since some of it -- e.g. patch "
        "publication -- already happened before receipt.json was written)"
    ),
}

#: True lifecycle-phase durations (as opposed to the filesystem intervals
#: this module actually measures) are never produced by this method. Stated
#: plainly on every result rather than left implicit in a docstring.
_LIFECYCLE_DURATIONS_UNMEASURED = "unmeasured by this filesystem-mtime method"

_PRODUCER_ORDERING_LIMITATION = (
    "the artifact boundaries this module reads do not occur in lifecycle "
    "order: the engine creates transcript.txt AFTER command startup (so "
    "'setup' absorbs part of startup and 'command' understates it), and "
    "patch.diff is published AFTER the transcript's final write -- verified "
    "on a retained cell (2026-09-08-first-smoke-123843/cell-000-engine/"
    "agentclinic-repair-depth-3-20260908-123925-900511): transcript.txt "
    "mtime 08:39:55.982429, patch.diff birth 08:39:56.004320, 22 ms later. "
    "So 'grading' (transcript mtime -> receipt mtime) also contains patch "
    "publication and other preservation work, and the residual (receipt "
    "mtime -> wrapper end) cannot represent all preservation either."
)


class TimingError(RuntimeError):
    """Raised instead of reporting a timing span that was never coherently observed."""


@dataclass(frozen=True, slots=True)
class TimingResult:
    """One cell's derived timing, with everything it could and could not measure."""

    schema_version: int
    cell_dir: str
    attempt_dir: str | None
    wrapper_start: float
    wrapper_end: float
    total_seconds: float
    total_source: str
    phases: dict[str, float]
    missing: dict[str, str]
    residual_seconds: float | None
    residual_missing: str | None
    artifact_mtimes: dict[str, float | None]
    measurement_source: str
    boundary_note: str
    interval_definitions: dict[str, str]
    lifecycle_durations: str
    producer_ordering_limitation: str

    def to_json_dict(self) -> dict:
        return asdict(self)


def _locate_attempt_dir(cell_dir: Path) -> Path | None:
    """The one inner ``<task>-<stamp>`` directory under ``cell_dir``.

    Selection is by ``attempt.py``'s own ``attempt_dir_name`` shape --
    ``<task>-<YYYYmmdd-HHMMSS-ffffff>`` -- not "the only subdirectory". A real
    cell also holds ``engine-contracts/``, the content-addressed rendered
    contracts shared across a batch, so an only-child rule refuses on every
    cell an actual run produces. That defect survived a full synthetic test
    suite and was caught by running this against a retained cell.

    Returns ``None`` when no directory matches -- an attempt that never got as
    far as writing any evidence. Raises when more than one matches: there is no
    basis for guessing which attempt is being timed, so it names what it found
    rather than picking one silently.
    """
    candidates = sorted(
        p for p in cell_dir.iterdir() if p.is_dir() and _ATTEMPT_DIR_RE.search(p.name)
    )
    if not candidates:
        return None
    if len(candidates) > 1:
        names = ", ".join(c.name for c in candidates)
        raise TimingError(
            f"ambiguous cell directory {cell_dir}: {len(candidates)} "
            f"attempt directories found ({names}); expected exactly one "
            "<task>-<stamp> attempt directory"
        )
    return candidates[0]


def _birthtime(path: Path) -> float | None:
    """Creation time, when the filesystem records one.

    APFS and HFS+ expose ``st_birthtime``; most Linux filesystems do not
    surface one through ``stat``. This is the only signal that separates
    setup from the command: an artifact's *mtime* is its **last** write, so
    the transcript's mtime marks where the command ended, never where it
    began. Deriving a command start from the earliest mtime attributes the
    whole command to setup and leaves the command itself at roughly zero --
    verified against a retained cell, where that reading gave setup 46.8 s
    and command 0.0 s for a command that actually ran 46.6 s.

    Absent a birth time the two phases are reported as one combined span
    rather than invented separately.
    """
    stat = path.stat()
    birth = getattr(stat, "st_birthtime", None)
    return float(birth) if birth is not None else None


def measure_timing(
    cell_dir: Path | str,
    *,
    wrapper_start: float,
    wrapper_end: float,
    total_seconds: float | None = None,
    total_source: str | None = None,
    birthtime_reader: Callable[[Path], float | None] = _birthtime,
) -> TimingResult:
    """Derive setup/command/grading/residual durations from the filesystem.

    ``wrapper_start``/``wrapper_end`` must be in the same clock domain as the
    file mtimes being compared (``time.time()``'s domain, not
    ``time.monotonic()``'s) -- they bound setup and the residual, and every
    artifact mtime is checked against them.

    ``total_seconds``/``total_source`` let a caller with a more trustworthy
    clock for duration (e.g. ``time.monotonic()``, immune to wall-clock
    adjustments) supply the authoritative total directly; the wrapper bounds
    are still required and still used for the mtime comparisons, because a
    monotonic reading cannot be compared to a filesystem mtime at all. When
    omitted, the total is ``wrapper_end - wrapper_start``, in the same
    wall-clock domain as everything else this function reports.

    Never runs a subprocess and never reads its own clock: this function
    is pure over its arguments, which is what lets the default test tier
    exercise it without spawning anything.
    """
    if wrapper_end < wrapper_start:
        raise TimingError(
            f"wrapper end ({wrapper_end!r}) precedes wrapper start "
            f"({wrapper_start!r}); the observation window is incoherent"
        )
    if total_seconds is not None and total_seconds < 0:
        raise TimingError(
            f"supplied authoritative total is negative ({total_seconds!r}); refusing"
        )

    cell_path = Path(cell_dir)
    if not cell_path.is_dir():
        raise TimingError(f"no such cell directory: {cell_path}")

    attempt_dir = _locate_attempt_dir(cell_path)

    mtimes: dict[str, float | None] = {}
    if attempt_dir is not None:
        for name in ARTIFACT_NAMES:
            path = attempt_dir / name
            mtimes[name] = path.stat().st_mtime if path.is_file() else None
    else:
        mtimes = dict.fromkeys(ARTIFACT_NAMES, None)

    for name, mtime in mtimes.items():
        if mtime is not None and mtime < wrapper_start:
            raise TimingError(
                f"{name} mtime ({mtime!r}) predates wrapper start "
                f"({wrapper_start!r}); refusing rather than reporting a "
                "negative setup span"
            )

    receipt_mtime = mtimes["receipt.json"]
    transcript_mtime = mtimes["transcript.txt"]
    if (
        receipt_mtime is not None
        and transcript_mtime is not None
        and receipt_mtime < transcript_mtime
    ):
        raise TimingError(
            f"receipt.json mtime ({receipt_mtime!r}) precedes transcript.txt "
            f"mtime ({transcript_mtime!r}); grading cannot have finished "
            "before the command it graded delivered its transcript"
        )
    if receipt_mtime is not None and receipt_mtime > wrapper_end:
        raise TimingError(
            f"receipt.json mtime ({receipt_mtime!r}) is after wrapper end "
            f"({wrapper_end!r}); refusing rather than reporting a negative "
            "residual span"
        )

    existing = {name: m for name, m in mtimes.items() if m is not None}
    earliest_mtime = min(existing.values()) if existing else None

    phases: dict[str, float] = {}
    missing: dict[str, str] = {}

    if attempt_dir is None:
        reason = f"no attempt directory found under {cell_path}"
        missing["setup"] = reason
        missing["command"] = reason
        missing["grading"] = reason
    else:
        transcript_path = attempt_dir / "transcript.txt"
        transcript_birth = (
            birthtime_reader(transcript_path) if transcript_path.is_file() else None
        )
        if transcript_birth is not None and transcript_birth < wrapper_start:
            raise TimingError(
                f"transcript.txt birth time ({transcript_birth!r}) predates "
                f"wrapper start ({wrapper_start!r}); refusing rather than "
                "reporting a negative setup span"
            )
        if (
            transcript_birth is not None
            and transcript_mtime is not None
            and transcript_birth > transcript_mtime
        ):
            raise TimingError(
                f"transcript.txt birth time ({transcript_birth!r}) is after "
                f"its mtime ({transcript_mtime!r}); the command cannot have "
                "started after it finished writing"
            )

        if transcript_mtime is None:
            reason = (
                f"transcript.txt is absent from {attempt_dir.name}; "
                "the command never delivered one (REFUSED attempt)"
            )
            missing["command"] = reason
            if earliest_mtime is None:
                missing["setup"] = (
                    f"no artifacts present in {attempt_dir.name} "
                    f"(expected one of {', '.join(ARTIFACT_NAMES)})"
                )
            else:
                missing["setup"] = (
                    "no transcript, so the setup/command boundary is unknown"
                )
        elif transcript_birth is None:
            combined = (
                "this filesystem records no birth time, so the setup/command "
                "boundary is unobservable; reported as one combined span"
            )
            phases["setup_and_command"] = transcript_mtime - wrapper_start
            missing["setup"] = combined
            missing["command"] = combined
        else:
            phases["setup"] = transcript_birth - wrapper_start
            phases["command"] = transcript_mtime - transcript_birth

        if transcript_mtime is None:
            missing["grading"] = (
                "transcript.txt is absent; grading's window has no start "
                "(REFUSED attempt)"
            )
        elif receipt_mtime is None:
            missing["grading"] = (
                f"receipt.json is absent from {attempt_dir.name}; grading "
                "never produced a verdict (REFUSED attempt)"
            )
        else:
            phases["grading"] = receipt_mtime - transcript_mtime

    residual_seconds: float | None = None
    residual_missing: str | None = None
    if attempt_dir is None:
        residual_missing = f"no attempt directory found under {cell_path}"
    elif receipt_mtime is None:
        residual_missing = (
            "receipt.json is absent; the residual (preservation+cleanup) "
            "window has no start"
        )
    else:
        residual_seconds = wrapper_end - receipt_mtime

    resolved_total = (
        total_seconds if total_seconds is not None else wrapper_end - wrapper_start
    )
    resolved_source = (
        total_source if total_source is not None else _WALL_CLOCK_TOTAL_SOURCE
    )

    return TimingResult(
        schema_version=SCHEMA_VERSION,
        cell_dir=str(cell_path),
        attempt_dir=attempt_dir.name if attempt_dir is not None else None,
        wrapper_start=wrapper_start,
        wrapper_end=wrapper_end,
        total_seconds=resolved_total,
        total_source=resolved_source,
        phases=phases,
        missing=missing,
        residual_seconds=residual_seconds,
        residual_missing=residual_missing,
        artifact_mtimes=mtimes,
        measurement_source=_MEASUREMENT_SOURCE,
        boundary_note=_BOUNDARY_NOTE,
        interval_definitions=dict(_INTERVAL_DEFINITIONS),
        lifecycle_durations=_LIFECYCLE_DURATIONS_UNMEASURED,
        producer_ordering_limitation=_PRODUCER_ORDERING_LIMITATION,
    )


def run_and_measure(
    command: Sequence[str],
    cell_dir: Path | str,
    *,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
) -> TimingResult:
    """Run ``command`` once, timing it, then measure the cell it wrote into.

    Uses ``subprocess.run`` -- exercise this ONLY under
    ``@pytest.mark.integration``, and ONLY against a trivial, model-free
    command (see this repository's constraint against model inference,
    network access, or a live model server: this entry point must never be
    pointed at one).

    ``time.monotonic()`` brackets the call and becomes the authoritative
    total, since it cannot be perturbed by a wall-clock adjustment during a
    long-running attempt. ``time.time()`` is captured separately, right
    alongside it, purely to compare against file mtimes -- the two clocks
    are never conflated into one figure.
    """
    wall_start = time.time()
    mono_start = time.monotonic()
    subprocess.run(list(command), cwd=cwd, env=dict(env) if env is not None else None)
    mono_end = time.monotonic()
    wall_end = time.time()
    return measure_timing(
        cell_dir,
        wrapper_start=wall_start,
        wrapper_end=wall_end,
        total_seconds=mono_end - mono_start,
        total_source=(
            "monotonic wrapper bounds (time.monotonic domain); NOT the same "
            "clock as the wall-clock wrapper_start/wrapper_end above, which "
            "are time.time() readings captured only for the mtime comparisons"
        ),
    )


def _record(result: TimingResult, record_path: Path) -> None:
    record_path.write_text(
        json.dumps(result.to_json_dict(), indent=2) + "\n", encoding="utf-8"
    )


def _print_summary(result: TimingResult) -> None:
    print(f"total: {result.total_seconds:.6f}s ({result.total_source})")
    print(
        "  (figures below are filesystem intervals between named artifacts, "
        f"not instrumented lifecycle phases -- lifecycle durations are "
        f"{result.lifecycle_durations})"
    )
    for phase in ("setup", "command", "grading"):
        if phase in result.phases:
            print(
                f"  {phase}: {result.phases[phase]:.6f}s "
                f"[{result.interval_definitions[phase]}]"
            )
        else:
            print(f"  {phase}: MISSING -- {result.missing[phase]}")
    if "setup_and_command" in result.phases:
        print(
            "  setup_and_command (combined, no birth time available): "
            f"{result.phases['setup_and_command']:.6f}s "
            f"[{result.interval_definitions['setup_and_command']}]"
        )
    if result.residual_seconds is not None:
        print(
            f"  residual (preservation+cleanup, not summed): "
            f"{result.residual_seconds:.6f}s "
            f"[{result.interval_definitions['residual']}]"
        )
    else:
        print(f"  residual: MISSING -- {result.residual_missing}")
    print(f"  limitation: {result.producer_ordering_limitation}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="mode", required=True)

    measure_p = subparsers.add_parser(
        "measure", help="derive timing.json from pre-recorded wrapper bounds"
    )
    measure_p.add_argument("cell_dir", type=Path, help="the schedule cell directory")
    measure_p.add_argument(
        "--start", type=float, required=True, help="wrapper start (time.time domain)"
    )
    measure_p.add_argument(
        "--end", type=float, required=True, help="wrapper end (time.time domain)"
    )
    measure_p.add_argument("--record", type=Path, help="write timing.json here")

    run_p = subparsers.add_parser(
        "run", help="time a trivial command itself, then derive timing.json"
    )
    run_p.add_argument("--cell-dir", type=Path, required=True)
    run_p.add_argument("--record", type=Path, help="write timing.json here")
    run_p.add_argument(
        "command", nargs=argparse.REMAINDER, help="command to run, after --"
    )

    args = parser.parse_args(argv)

    if args.mode == "measure":
        if not args.cell_dir.is_dir():
            print(f"timing: no such cell directory: {args.cell_dir}", file=sys.stderr)
            return 2
        try:
            result = measure_timing(
                args.cell_dir, wrapper_start=args.start, wrapper_end=args.end
            )
        except TimingError as error:
            print(f"timing: {error}", file=sys.stderr)
            return 1
    else:
        command = list(args.command)
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            print("timing: run mode needs a command after --", file=sys.stderr)
            return 2
        try:
            result = run_and_measure(command, args.cell_dir)
        except TimingError as error:
            print(f"timing: {error}", file=sys.stderr)
            return 1

    _print_summary(result)
    if args.record is not None:
        _record(result, args.record)
        print(f"recorded: {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
