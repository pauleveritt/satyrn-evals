"""session.json: a session task's ordered public prompts and grader-only selections.

The file stays inside the protected task package; its path is never sent
to the adapter (2026-09-01 spec, Task layout). Ordinary tasks have no
``session.json``; this loader is called only for session tasks.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from satyrn_evals.errors import SessionSpecError
from satyrn_evals.manifest import TaskManifest

type StepKind = Literal["feature", "review"]

_SAFE_ID = re.compile(r"[A-Za-z0-9._-]+\Z")

_KEYS = {"version", "steps", "base_preservation_selectors"}
_STEP_KEYS = {"id", "kind", "prompt", "new_feature_selectors"}

DEFAULT_SESSION_SPEC: str = "session.json"


@dataclass(frozen=True, slots=True)
class SessionStep:
    """One ordered prompt; ``feature`` steps add cumulative hidden selectors."""

    id: str
    kind: StepKind
    prompt: str
    new_feature_selectors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SessionSpec:
    steps: tuple[SessionStep, ...]
    base_preservation_selectors: tuple[str, ...]


def _parse_step(raw: object) -> SessionStep:
    if not isinstance(raw, dict) or set(raw) != _STEP_KEYS:
        raise SessionSpecError(
            "session step must hold exactly id, kind, prompt, new_feature_selectors"
        )
    id_ = raw["id"]
    kind = raw["kind"]
    prompt = raw["prompt"]
    sels = raw["new_feature_selectors"]
    if not isinstance(id_, str) or not _SAFE_ID.fullmatch(id_):
        raise SessionSpecError(f"step id must be a filesystem-safe token: {id_!r}")
    if kind not in ("feature", "review") or not isinstance(kind, str):
        raise SessionSpecError(f"step kind must be 'feature' or 'review': {kind!r}")
    if not isinstance(prompt, str) or not prompt.strip():
        raise SessionSpecError(f"step {id_!r} has an empty prompt")
    if not isinstance(sels, list) or not all(isinstance(s, str) and s for s in sels):
        raise SessionSpecError("new_feature_selectors must be non-empty strings")
    sels_tuple = tuple(sels)
    if kind == "feature" and not sels_tuple:
        raise SessionSpecError("a feature step must add at least one new selector")
    if kind == "review" and sels_tuple:
        raise SessionSpecError("a review step must add no new selectors")
    return SessionStep(
        id=id_, kind=kind, prompt=prompt, new_feature_selectors=sels_tuple
    )


def _check_spec_name(spec_name: str) -> None:
    """Refuse anything but a bare ``*.json`` filename.

    This is a **lexical** guard on the name, and that is the whole of its
    claim: it rejects an absolute path, a ``..`` segment, a separator, and a
    non-``.json`` suffix. It does **not** establish containment. A bare
    filename inside ``task_dir`` that is a symlink pointing outside still
    resolves and is read, because nothing here resolves the real path.

    That exposure is not new — the single-argument form had it for
    ``session.json`` itself — and hardening it would mean resolving and
    containment-checking, which is a different change with its own failure
    modes on legitimate symlinked checkouts. Recorded rather than silently
    implied: a caller who needs containment must add it.

    Four independent checks, each with its own message, so a disabled check
    is visible in which refusal (if any) still fires rather than being
    masked by a neighboring one.
    """
    if not spec_name.endswith(".json"):
        raise SessionSpecError(
            f"--session-spec must name a .json file: {spec_name!r}"
        )
    path = Path(spec_name)
    if path.is_absolute():
        raise SessionSpecError(
            f"--session-spec must not be an absolute path: {spec_name!r}"
        )
    if ".." in path.parts:
        raise SessionSpecError(
            f"--session-spec must not traverse directories: {spec_name!r}"
        )
    if path.name != spec_name:
        raise SessionSpecError(
            f"--session-spec must be a bare filename, not a path: {spec_name!r}"
        )


def load_session_spec(
    task_dir: Path, spec_name: str = DEFAULT_SESSION_SPEC
) -> SessionSpec:
    """Load and validate ``spec_name`` (default ``session.json``) below ``task_dir``."""
    _check_spec_name(spec_name)
    path = task_dir / spec_name
    try:
        data = json.loads(path.read_text())
    except OSError as e:
        raise SessionSpecError(f"cannot read {spec_name}: {e}") from e
    except json.JSONDecodeError as e:
        raise SessionSpecError(f"malformed {spec_name}: {e}") from e
    if not isinstance(data, dict) or set(data) != _KEYS:
        raise SessionSpecError(
            f"unknown or missing keys in {spec_name}: expected "
            "version, steps, base_preservation_selectors"
        )
    if data["version"] != 1:
        raise SessionSpecError("session.json version must be 1")
    raw_steps = data["steps"]
    if not isinstance(raw_steps, list) or len(raw_steps) < 2:
        raise SessionSpecError("session.json declares fewer than two steps")
    pres = data["base_preservation_selectors"]
    if not isinstance(pres, list) or not all(
        isinstance(s, str) and s for s in pres
    ):
        raise SessionSpecError(
            "base_preservation_selectors must be a list of non-empty strings"
        )
    steps = tuple(_parse_step(raw) for raw in raw_steps)
    seen_ids: set[str] = set()
    seen_selectors: set[str] = set()
    for step in steps:
        if step.id in seen_ids:
            raise SessionSpecError(f"duplicate id: {step.id}")
        seen_ids.add(step.id)
        for sel in step.new_feature_selectors:
            if sel in seen_selectors:
                raise SessionSpecError(f"duplicate feature selector: {sel}")
            seen_selectors.add(sel)
    return SessionSpec(
        steps=steps, base_preservation_selectors=tuple(pres)
    )


def assert_no_overlay_names(
    spec: SessionSpec, manifest: TaskManifest, task_dir: Path
) -> None:
    """Refuse a session whose prompts name a hidden overlay path.

    Exact, case-sensitive substring check — a tripwire for the mistake
    that actually happened (a prompt naming the grader), not a proof of
    ignorance; a paraphrase passes. Visible tasks (no overlay) are skipped,
    so the guard fires only for tasks that declared ``oracle_visibility``
    ``hidden`` alongside a ``grader_overlay``.

    ``_overlay_declared_names`` is imported lazily to keep
    ``session_manifest`` free of a module-import cycle with
    ``satyrn_evals.manifest``'s consumers; ``TaskManifest`` is annotation-only.
    """
    if manifest.oracle_visibility != "hidden" or manifest.grader_overlay is None:
        return
    from satyrn_evals.manifest import _overlay_declared_names

    names = _overlay_declared_names(task_dir, manifest.grader_overlay)
    for step in spec.steps:
        for name in names:
            if name in step.prompt:
                raise SessionSpecError(
                    f"prompt {step.id!r} names grader-only path: {name}"
                )
