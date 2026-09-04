"""The session executor: one conversation against one evolving checkout.

Evals owns the transitions (2026-09-01 spec): prompt sent → terminal
event or timeout → reap if not settled → snapshot full status and
cumulative patch → classify scope → write artifacts durably → next
prompt, graceful close, or session stop. Raw adapter lines are spooled
before any parsing; counts derive from retained events only; the record
is written for every session that starts, including adapter-error,
timeout, and cleanup-failure terminations.
"""

import contextlib
import dataclasses
import hashlib
import json
import os
import shutil
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from satyrn_evals.adapter_process import (
    AdapterCleanupError,
    AdapterProcess,
    AdapterTimeout,
)
from satyrn_evals.errors import ProtocolError, SatyrnError, UsageError
from satyrn_evals.manifest import TaskManifest, load_manifest, resolve_task
from satyrn_evals.overlay import OverlaySpec, load_overlay
from satyrn_evals.patch import within_source
from satyrn_evals.session_manifest import SessionSpec, load_session_spec
from satyrn_evals.session_patch import build_cumulative_patch
from satyrn_evals.session_protocol import (
    EventLine,
    SessionStarted,
    StepFinished,
    parse_session_line,
    serialize_close,
    serialize_prompt,
)
from satyrn_evals.session_record import (
    SessionCode,
    SessionRecord,
    StepRecord,
    write_session_record,
)
from satyrn_evals.workspace import (
    SessionWorkspace,
    WorkspacePrepareError,
    WorkspaceReleaseError,
    prepare_session_workspace,
    release_session_workspace,
    snapshot_tree,
)

if TYPE_CHECKING:
    from satyrn_evals.session_grader import SessionGrader

_TRANSCRIPT_NAME = "transcript.jsonl"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def session_dir_name(task: str, when: datetime) -> str:
    return f"{task}-session-{when.strftime('%Y%m%d-%H%M%S-%f')}"


def _fsync_file(path: Path) -> None:
    with open(path, "rb") as f:
        os.fsync(f.fileno())


def _spool(transcript_path: Path, raw: str) -> None:
    with open(transcript_path, "a", encoding="utf-8") as f:
        f.write(raw + "\n")
        f.flush()
        os.fsync(f.fileno())


class _Stop(Exception):
    """Internal: the sequence stopped; carries the session code and reason."""

    def __init__(self, code: SessionCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _snapshot(workspace: SessionWorkspace, path: Path) -> None:
    entries = snapshot_tree(workspace.worktree)
    path.write_text(json.dumps([asdict(e) for e in entries], default=str) + "\n")
    _fsync_file(path)


def _capture_checkpoint(
    workspace: SessionWorkspace, session_dir: Path, spec_step, transcript_path: Path,
    index: int, outcome: str, prompt_digest: str,
    turn_count: int, tool_count: int, context_events: int,
    source_paths: tuple[str, ...],
) -> StepRecord:
    capture = build_cumulative_patch(workspace.worktree, workspace.base_sha)
    patch_path = session_dir / "checkpoints" / f"{index:02d}-{spec_step.id}.patch"
    patch_path.parent.mkdir(exist_ok=True)
    patch_path.write_text(capture.patch_text, encoding="utf-8")
    _fsync_file(patch_path)
    patch_bytes = len(capture.patch_text.encode("utf-8"))
    patch_digest = _digest(capture.patch_text)
    snapshot_path = session_dir / "snapshots" / f"{index:02d}-{spec_step.id}.json"
    snapshot_path.parent.mkdir(exist_ok=True)
    _snapshot(workspace, snapshot_path)
    snapshot_digest = _digest(snapshot_path.read_text(encoding="utf-8"))
    transcript_digest = None
    transcript_bytes: int | None = None
    if transcript_path.exists():
        prefix = transcript_path.read_bytes()
        transcript_bytes = len(prefix)
        transcript_digest = _digest(prefix.decode("utf-8", "surrogateescape"))
    return StepRecord(
        step_id=spec_step.id,
        prompt_digest=prompt_digest,
        outcome=outcome,
        patch_path=os.fspath(patch_path.relative_to(session_dir)),
        patch_digest=patch_digest,
        patch_bytes=patch_bytes,
        snapshot_path=os.fspath(snapshot_path.relative_to(session_dir)),
        snapshot_digest=snapshot_digest,
        transcript_prefix_path=os.fspath(transcript_path.relative_to(session_dir)),
        transcript_prefix_digest=transcript_digest,
        transcript_prefix_bytes=transcript_bytes,
        scope_violations=tuple(
            sorted(
                path
                for path in capture.changed_paths
                if not within_source(path, source_paths)
            )
        ),
        turn_count=turn_count,
        tool_count=tool_count,
        context_events=context_events,
    )


def run_session(
    *,
    task: str,
    tasks_root: Path,
    output: Path,
    adapter_command: list[str],
    start_timeout: float = 60.0,
    step_timeout: float = 600.0,
    close_timeout: float = 30.0,
    grader: SessionGrader | None = None,
) -> SessionRecord:
    """Run one session against TASK and return the durable record."""
    task_dir = resolve_task(task, tasks_root)
    manifest = load_manifest(task_dir)
    spec = load_session_spec(task_dir)
    overlay = load_overlay(task_dir, manifest)
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=True)
    session_dir = output / session_dir_name(manifest.name, datetime.now(UTC))
    session_dir.mkdir()
    try:
        workspace = prepare_session_workspace(
            base=task_dir / "base",
            protected_paths=(task_dir, output, Path.cwd()),
        )
    except WorkspacePrepareError as exc:
        record = SessionRecord(
            version=1,
            task=manifest.name,
            adapter_command=tuple(adapter_command),
            base_commit="",
            code=SessionCode.WORKSPACE_FAILED,
            message=str(exc),
            provenance=dict(manifest.provenance) if manifest.provenance else {},
        )
        write_session_record(session_dir / "session-record.json", record)
        return record
    record: SessionRecord | None = None
    try:
        record = _drive(
            manifest=manifest,
            spec=spec,
            overlay=overlay,
            workspace=workspace,
            session_dir=session_dir,
            transcript_path=session_dir / _TRANSCRIPT_NAME,
            adapter_command=list(adapter_command),
            start_timeout=start_timeout,
            step_timeout=step_timeout,
            close_timeout=close_timeout,
            grader=grader,
        )
    except UsageError:
        # start refusal: usage writes nothing; the finally below releases
        raise
    except SatyrnError as exc:
        # a failure _drive did not convert (defensive): the started
        # session still leaves a record (review finding 4)
        record = _record(
            manifest, list(adapter_command), workspace,
            SessionCode.ADAPTER_ERROR, None, None, str(exc), [],
        )
    finally:
        try:
            release_session_workspace(workspace)
        except WorkspaceReleaseError as exc:
            if record is None:
                raise
            record = dataclasses.replace(
                record,
                code=SessionCode.CLEANUP_FAILED,
                retained_path=exc.retained_path,
                message=f"{record.message or record.code.value}; {exc}; "
                f"retained at {exc.retained_path}",
            )
    assert record is not None
    write_session_record(session_dir / "session-record.json", record)
    return record


def _record(
    manifest: TaskManifest, adapter_command: list[str], workspace: SessionWorkspace,
    code: SessionCode, conversation_id: str | None, terminal_step: str | None,
    message: str | None, checkpoints: list[StepRecord],
) -> SessionRecord:
    return SessionRecord(
        version=1,
        task=manifest.name,
        adapter_command=tuple(adapter_command),
        base_commit=workspace.base_sha,
        code=code,
        conversation_id=conversation_id,
        terminal_step=terminal_step,
        message=message,
        provenance=dict(manifest.provenance) if manifest.provenance else {},
        steps=tuple(checkpoints),
    )


def _drive(
    *, manifest: TaskManifest, spec: SessionSpec, overlay: OverlaySpec,
    workspace: SessionWorkspace, session_dir: Path, transcript_path: Path,
    adapter_command: list[str], start_timeout: float, step_timeout: float,
    close_timeout: float, grader: SessionGrader | None,
) -> SessionRecord:
    checkpoints: list[StepRecord] = []
    conversation_id: str | None = None
    terminal_step: str | None = None
    code = SessionCode.COMPLETE
    message: str | None = None
    cleanup_error: AdapterCleanupError | None = None
    adapter: AdapterProcess | None = None
    try:
        try:
            adapter = AdapterProcess.start(
                adapter_command,
                cwd=workspace.worktree,
                stderr_path=session_dir / "adapter-stderr.log",
            )
        except OSError as exc:
            shutil.rmtree(session_dir, ignore_errors=True)
            raise UsageError(f"adapter cannot start: {exc}") from exc
        try:
            raw = adapter.read_line(start_timeout)
            if raw is None:
                raise _Stop(
                    SessionCode.ADAPTER_ERROR,
                    "adapter exited before session_started",
                )
            _spool(transcript_path, raw)
            first = parse_session_line(raw)
            if not isinstance(first, SessionStarted):
                raise _Stop(
                    SessionCode.PROTOCOL_ERROR,
                    "first adapter message was not session_started",
                )
            conversation_id = first.conversation_id

            stopped = False
            for spec_step in spec.steps:
                terminal_step = spec_step.id
                adapter.send_line(serialize_prompt(spec_step.id, spec_step.prompt))
                prompt_digest = _digest(spec_step.prompt)
                turn_count = tool_count = context_events = 0
                outcome = ""
                stop: _Stop | None = None
                while True:
                    try:
                        raw = adapter.read_line(step_timeout)
                    except AdapterTimeout as exc:
                        # reap first, then snapshot: no late descendant may
                        # mutate a patch after its digest is recorded.
                        adapter.terminate_and_reap(step_timeout)
                        stop = _Stop(
                            SessionCode.STEP_TIMEOUT,
                            f"step {spec_step.id} exceeded {step_timeout:g}s: {exc}",
                        )
                        break
                    if raw is None:
                        adapter.terminate_and_reap(step_timeout)
                        stop = _Stop(
                            SessionCode.ADAPTER_ERROR,
                            f"adapter exited during step {spec_step.id}",
                        )
                        break
                    _spool(transcript_path, raw)
                    try:
                        line = parse_session_line(raw)
                    except ProtocolError as exc:
                        stop = _Stop(SessionCode.PROTOCOL_ERROR, str(exc))
                        break
                    match line:
                        case EventLine(
                            step_id=step_id, conversation_id=event_cid, kind=kind
                        ):
                            if event_cid != conversation_id:
                                stop = _Stop(
                                    SessionCode.PROTOCOL_ERROR,
                                    f"event identity changed at step "
                                    f"{spec_step.id}",
                                )
                                break
                            if step_id != spec_step.id:
                                stop = _Stop(
                                    SessionCode.PROTOCOL_ERROR,
                                    f"event for step {step_id!r} "
                                    f"during {spec_step.id!r}",
                                )
                                break
                            match kind:
                                case "turn_end":
                                    turn_count += 1
                                case "tool_end":
                                    tool_count += 1
                                case "context_compacted":
                                    context_events += 1
                                case "context_reset":
                                    # design:230 — a context reset is a
                                    # protocol failure, not a countable
                                    # event: stop the sequence (the reset
                                    # line is already spooled above).
                                    stop = _Stop(
                                        SessionCode.PROTOCOL_ERROR,
                                        f"context reset during step "
                                        f"{spec_step.id} is a protocol "
                                        f"failure",
                                    )
                                    break
                                case _:
                                    pass
                        case StepFinished() as finished:
                            if finished.step_id != spec_step.id:
                                stop = _Stop(
                                    SessionCode.PROTOCOL_ERROR,
                                    f"terminal for step {finished.step_id!r} "
                                    f"during {spec_step.id!r}",
                                )
                                break
                            if finished.conversation_id != conversation_id:
                                stop = _Stop(
                                    SessionCode.PROTOCOL_ERROR,
                                    f"conversation identity changed at "
                                    f"step {spec_step.id}",
                                )
                                break
                            outcome = finished.outcome
                            break
                        case _:
                            stop = _Stop(
                                SessionCode.PROTOCOL_ERROR,
                                f"unexpected message during step {spec_step.id}",
                            )
                            break
                if outcome != "settled" and stop is None:
                    # non-settled terminal: reap first, then snapshot.
                    adapter.terminate_and_reap(step_timeout)
                # capture before cleanup, on every path (BRIEF rule 3)
                checkpoints.append(
                    _capture_checkpoint(
                        workspace, session_dir, spec_step, transcript_path,
                        len(checkpoints) + 1, outcome, prompt_digest,
                        turn_count, tool_count, context_events,
                        manifest.source_paths,
                    )
                )
                if stop is not None:
                    raise stop
                if outcome != "settled":
                    match outcome:
                        case "output-limit":
                            code, message = (
                                SessionCode.OUTPUT_LIMIT,
                                "adapter reported output-limit",
                            )
                        case _:
                            code, message = (
                                SessionCode.ADAPTER_ERROR,
                                "adapter reported agent-error",
                            )
                    stopped = True
                    break
            if not stopped:
                adapter.send_line(serialize_close())
                close_deadline = time.monotonic() + close_timeout
                while True:
                    remaining = close_deadline - time.monotonic()
                    try:
                        raw = adapter.read_line(max(remaining, 0.01))
                    except AdapterTimeout as exc:
                        adapter.terminate_and_reap(close_timeout)
                        code, message = (
                            SessionCode.ADAPTER_ERROR,
                            f"close timed out: {exc}",
                        )
                        break
                    if raw is None:
                        rc = adapter.wait(max(close_deadline - time.monotonic(), 0.01))
                        if rc != 0:
                            code, message = (
                                SessionCode.ADAPTER_ERROR,
                                f"adapter exited {rc} on close",
                            )
                        break
                    _spool(transcript_path, raw)
                    try:
                        parse_session_line(raw)
                    except ProtocolError as exc:
                        code, message = SessionCode.PROTOCOL_ERROR, str(exc)
                        break
                    code, message = (
                        SessionCode.ADAPTER_ERROR,
                        "adapter sent output after close",
                    )
                    break
        except _Stop as stop:
            code, message = stop.code, stop.message
        except ProtocolError as exc:
            code, message = SessionCode.PROTOCOL_ERROR, str(exc)
        except SatyrnError as exc:
            # a broken adapter channel (e.g. closed stdin) after the
            # session started: the record is still written, with every
            # checkpoint captured so far (review finding 4).
            code, message = SessionCode.ADAPTER_ERROR, str(exc)
    finally:
        # the False arm (adapter None under the start-refusal unwind) is
        # exercised by test_missing_adapter_is_a_start_refusal, but the
        # merged subprocess run cannot attribute that arc — verified by
        # the gate failing without this directive
        if adapter is not None:  # pragma: no branch
            with contextlib.suppress(OSError):
                adapter.close_stdin()
            try:
                adapter.terminate_and_reap(close_timeout)
            except AdapterCleanupError as exc:
                cleanup_error = exc
    if cleanup_error is not None:
        return _record(
            manifest, adapter_command, workspace,
            SessionCode.CLEANUP_FAILED, conversation_id, terminal_step,
            str(cleanup_error), checkpoints,
        )
    if code is SessionCode.COMPLETE and any(
        step.scope_violations for step in checkpoints
    ):
        code = SessionCode.SCOPE_VIOLATION
    record = _record(
        manifest, adapter_command, workspace, code, conversation_id,
        terminal_step, message, checkpoints,
    )
    if grader is not None:
        record = grader.grade_record(record, spec, overlay, session_dir)
    return record
