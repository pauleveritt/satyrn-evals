"""Run the attempt seam n times and write a counts-only summary.

Each attempt() writes its own <task>-<stamp> directory under ``output`` and
records the directory's name in the attempt record; run names cells from
that recorded identity, never from a directory listing, so a sibling entry
in the output directory cannot corrupt cell provenance. A hidden oracle
produces a contamination tally beside the verdict counts; a visible oracle
omits it.

Completion contract: ``summary.json`` is written only when all n attempts
complete. If the loop aborts — an exception, Ctrl-C, or a terminating
signal after at least one cell — run writes ``aborted.json``
(requested/completed/error plus the tallies over the completed cells) and
re-raises, so a partial batch is never mistaken for a completed short run.

That contract used to have a hole (V11d F3). ``except BaseException``
catches what Python *raises*, and the default disposition of SIGTERM and
SIGHUP raises nothing: the interpreter dies where it stands. An
interrupted batch therefore left cell directories, no ``summary.json``
and no ``aborted.json`` — indistinguishable, from the artifacts alone,
from a batch that was never started. ``_abort_on_signals`` turns those
two signals into a raised ``SignalAbort`` for the duration of the cell
loop so the existing abort path runs, then restores whatever handlers it
displaced. SIGINT is left alone: it already raises ``KeyboardInterrupt``.
SIGKILL cannot be caught by anything and remains outside this contract.
"""

import json
import signal
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from types import FrameType

from satyrn_evals.attempt import DEFAULT_TIMEOUT, attempt, resolve_contract
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.deadline import validate_attempt_timeout
from satyrn_evals.errors import OverlayError, SatyrnError, UsageError
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.rescore import compute_evidence, compute_pathology, pathology_context
from satyrn_evals.summary import (
    ABORTED_NAME,
    SUMMARY_NAME,
    AttemptCell,
    Summary,
    absent_pathology,
    compute_summary,
    write_summary,
)

type SignalHandler = (
    Callable[[int, FrameType | None], object] | int | signal.Handlers | None
)

ABORT_SIGNALS: tuple[signal.Signals, ...] = (signal.SIGTERM, signal.SIGHUP)


class SignalAbort(BaseException):
    """A terminating signal reached the batch loop (V11d F3).

    ``BaseException`` on purpose: like ``KeyboardInterrupt``, this is not
    a condition any inner ``except Exception`` should be able to swallow
    on its way out. ``str()`` is the signal's name, so the abort record's
    error field names what killed the batch.
    """

    def __init__(self, signum: int) -> None:
        self.signum = signum
        super().__init__(signal.Signals(signum).name)


@contextmanager
def _abort_on_signals() -> Iterator[None]:
    """Raise ``SignalAbort`` on a terminating signal, then restore.

    Restoring matters: ``run`` is a library call, and a test or a caller
    that runs a batch in-process must get its own handlers back.
    """

    def handler(signum: int, frame: FrameType | None) -> None:
        raise SignalAbort(signum)

    displaced: dict[signal.Signals, SignalHandler] = {}
    try:
        for sig in ABORT_SIGNALS:
            displaced[sig] = signal.signal(sig, handler)
        yield
    finally:
        for sig, previous in displaced.items():
            signal.signal(sig, previous)


def _write_aborted(
    output: Path,
    *,
    requested: int,
    cells: list[AttemptCell],
    error: str,
    oracle_visibility: str,
    pathology: dict[str, dict] | None = None,
) -> None:
    """Record an aborted batch; never under the name summary.json.

    The marker carries the requested count, the completed count, the
    error, and — over the completed cells — the same tally a summary
    would carry, including the pathology block when the binder supplied
    it. When the binder failed (pathology is None) the block is omitted
    and the caller's ``error`` already names the binder failure, so the
    marker never fabricates blocks and never hides the primary exception
    (V10 spec §4).
    """
    data: dict[str, object] = {
        "requested": requested,
        "completed": len(cells),
        "error": error,
    }
    if cells:
        # compute_summary requires a block per cell; when the binder
        # failed, absent blocks are only a construction scaffold and the
        # pathology key is dropped from the wire payload below.
        blocks = pathology if pathology is not None else absent_pathology(cells)
        payload = asdict(
            compute_summary(
                cells,
                oracle_visibility=oracle_visibility,
                pathology=blocks,
            )
        )
        if payload["contamination"] is None:
            payload.pop("contamination")
        if payload["attempt_timeout"] is None:
            payload.pop("attempt_timeout")
        if payload["deadline_provenance"] is None:
            payload.pop("deadline_provenance")
        payload.pop("evidence")  # the abort marker is a tally; evidence is the summary's
        if pathology is None:
            payload.pop("pathology")  # binder failed: error names it
        data.update(payload)
    output.mkdir(parents=True, exist_ok=True)
    (output / ABORTED_NAME).write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )


def run(
    *,
    task: str,
    tasks_root: Path,
    output: Path,
    command: list[str],
    n: int,
    timeout: float = DEFAULT_TIMEOUT,
    rung: str | None = None,
    max_repeated_calls: int | None = None,
    attempt_timeout: float | None = None,
    budget: AttemptBudget | None = None,
) -> Summary:
    if n < 1:
        raise UsageError("run requires a positive --n")
    if not command:
        raise UsageError("run command is required: run TASK [flags] -- COMMAND...")
    if attempt_timeout is not None:
        attempt_timeout = validate_attempt_timeout(attempt_timeout)
    task_dir = resolve_task(task, tasks_root=tasks_root)
    manifest = load_manifest(task_dir)
    # An unknown rung must cost no cells: resolve it here, before the first
    # attempt, so the refusal preserves nothing and is fixed by re-running.
    resolve_contract(manifest, rung)
    # Shared pathology context is validated BEFORE the first attempt
    # (V10 spec §4, close-out correction 2026-09-05): a broken overlay
    # refuses the run pre-cell (exit 3, nothing preserved, recoverable by
    # repair + rerun), and the binder runs on this pre-loaded context so
    # no shared-context failure can strand completed cells post-loop
    # (per-cell reads map to absent and never raise). summarize_output
    # keeps loading the overlay itself -- its run is already anchored.
    try:
        overlay, visible_texts = pathology_context(task_dir, manifest)
    except OverlayError as exc:
        raise SatyrnError(f"run: overlay unavailable: {exc}") from exc
    cells: list[AttemptCell] = []
    try:
        with _abort_on_signals():
            for _ in range(n):
                attempt_kwargs: dict[str, object] = dict(
                    task=task,
                    tasks_root=tasks_root,
                    output=output,
                    command=command,
                    timeout=timeout,
                    rung=rung,
                    max_repeated_calls=max_repeated_calls,
                )
                if attempt_timeout is not None:
                    attempt_kwargs["attempt_timeout"] = attempt_timeout
                if budget is not None:
                    attempt_kwargs["budget"] = budget
                record = attempt(**attempt_kwargs)  # type: ignore[arg-type]
                if record.attempt_dir is None:
                    raise RuntimeError(
                        "attempt record does not name its attempt directory"
                    )
                receipt: dict | None = None
                if record.receipt_path is not None:
                    receipt_path = output / record.attempt_dir / record.receipt_path
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                cells.append((record.attempt_dir, record, receipt))
    except BaseException as exc:
        # never lose the tally over completed cells (T1) — but never as a
        # file named summary.json: an aborted batch must not look complete.
        # The pathology binder runs best-effort: a binder failure must not
        # mask the primary abort exception, so it is folded into the
        # marker's error and the block is omitted (V10 spec §4).
        pathology: dict[str, dict] | None = None
        binder_error: str | None = None
        if cells:
            try:
                pathology = compute_pathology(
                    output,
                    cells,
                    task_dir=task_dir,
                    manifest=manifest,
                    overlay=overlay,
                    visible_texts=visible_texts,
                )
            except BaseException as bind_exc:  # never mask the abort
                binder_error = (
                    f"pathology unavailable: {type(bind_exc).__name__}: {bind_exc}"
                )
        _write_aborted(
            output,
            requested=n,
            cells=cells,
            error=(
                f"{type(exc).__name__}: {exc}"
                + (f"; {binder_error}" if binder_error is not None else "")
            ),
            oracle_visibility=manifest.oracle_visibility,
            pathology=pathology,
        )
        raise
    pathology = compute_pathology(
        output,
        cells,
        task_dir=task_dir,
        manifest=manifest,
        overlay=overlay,
        visible_texts=visible_texts,
    )
    evidence = compute_evidence(
        output,
        cells,
        task_dir=task_dir,
        manifest=manifest,
        overlay=overlay,
        visible_texts=visible_texts,
    )
    summary = compute_summary(
        cells,
        oracle_visibility=manifest.oracle_visibility,
        pathology=pathology,
        evidence=evidence,
    )
    output.mkdir(parents=True, exist_ok=True)
    stale = output / ABORTED_NAME
    if stale.exists():
        stale.unlink()  # a completed run replaces any earlier abort marker
    write_summary(output / SUMMARY_NAME, summary)
    return summary
