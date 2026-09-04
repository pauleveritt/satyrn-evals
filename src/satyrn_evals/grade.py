"""Orchestrate grading: materialize, apply, run the oracle, write the receipt."""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import satyrn_evals
from satyrn_evals import oracle_hook
from satyrn_evals.contamination import evidence_dict, scan_patch
from satyrn_evals.errors import (
    ApplyError,
    HookError,
    OracleError,
    PatchReadError,
    PatchRejected,
)
from satyrn_evals.manifest import TaskManifest, load_manifest
from satyrn_evals.overlay import OverlaySpec, load_overlay, materialize_overlay
from satyrn_evals.patch import check_allowlist, parse_patch_paths
from satyrn_evals.receipt import Receipt, patch_digest, write_receipt
from satyrn_evals.taskenv import has_locked_project, parse_freeze
from satyrn_evals.verdict import (
    HookResult,
    HookResultData,
    Verdict,
    compute_verdict,
    describe_unavailable,
    load_hook_result,
)


def grade(
    task_dir: Path,
    patch_path: Path,
    receipt_path: Path,
    *,
    overlay: OverlaySpec | None = None,
    selectors: tuple[str, ...] = (),
    expected: tuple[str, ...] | None = None,
    enforce_allowlist: bool = True,
) -> Receipt:
    """Grade PATCH against TASK, write the receipt, return it.

    Exit-code policy is the CLI's; this returns the artifact, whose
    `verdict` (pass/fail/unavailable) the caller maps to an exit code.

    ``overlay`` materializes grader-only files after the patch applies and
    before the oracle runs; ``selectors`` are appended to the oracle argv
    (node ids); ``expected`` overrides ``manifest.expected_test_ids`` as
    the verdict's target set. Defaults preserve ordinary grading exactly.

    When ``overlay`` is ``None`` and the manifest declares a hidden oracle,
    grade loads the overlay itself, runs the contamination detector over
    the patch, and annotates the receipt with the finding. In that auto path
    the run is closed: ``selectors`` narrows to ``manifest.expected_test_ids``
    so only the expected node ids execute and verdicts stay meaningful
    (hidden overlay tests do not leak into a bare grade). ``expected`` still
    defaults to ``manifest.expected_test_ids``. Explicit-overlay callers (the
    session grader) get no annotation here — session findings land on the
    session record (P4). Detection never changes a verdict or an exit code.
    """
    manifest = load_manifest(task_dir)
    auto_overlay = overlay is None and manifest.oracle_visibility == "hidden"
    if auto_overlay:
        overlay = load_overlay(task_dir, manifest)
        selectors = manifest.expected_test_ids
    try:
        patch_bytes = patch_path.read_bytes()
    except OSError as e:
        raise PatchReadError(f"cannot read patch: {e}") from e
    patch_text = os.fsdecode(patch_bytes)

    evidence: HookResultData | None = None
    reason = ""
    resolved_versions: dict[str, str] | None = None
    try:
        paths = parse_patch_paths(patch_text)
        if enforce_allowlist:
            check_allowlist(paths, manifest.source_paths)
        hook, resolved_versions = _run_oracle(
            manifest, task_dir, patch_text, overlay=overlay, selectors=selectors
        )
        verdict = compute_verdict(
            hook,
            expected if expected is not None else manifest.expected_test_ids,
        )
        evidence = {
            "executed_test_ids": list(hook.executed_test_ids),
            "outcomes": hook.outcomes,
            "counts": hook.counts,
        }
        if verdict is Verdict.UNAVAILABLE:
            reason = describe_unavailable(
                hook,
                expected if expected is not None else manifest.expected_test_ids,
            )
    except (PatchRejected, ApplyError, OracleError, HookError) as e:
        verdict = Verdict.UNAVAILABLE
        reason = str(e)

    contamination: dict | None = None
    if auto_overlay:
        base_root = task_dir / "base"
        visible_texts = (
            [
                path.read_text(encoding="utf-8", errors="replace")
                for path in sorted(base_root.rglob("*"))
                if path.is_file()
            ]
            if base_root.is_dir()
            else []
        )
        result = scan_patch(patch_text, overlay, visible_texts=visible_texts)
        contamination = {
            "visibility": "hidden",
            "checks": [
                {
                    "check": result.check,
                    "outcome": result.outcome,
                    "evidence": [evidence_dict(item) for item in result.evidence],
                }
            ],
        }

    receipt = Receipt(
        task=manifest.name,
        patch_digest=patch_digest(patch_bytes),
        verdict=verdict,
        reason=reason,
        evidence=evidence,
        contamination=contamination,
        resolved_versions=resolved_versions,
    )
    write_receipt(receipt_path, receipt)
    return receipt


def _materialize_project_env(work: Path, tmp: Path, base: Path) -> Path | None:
    """Relocated project env at tmp/project-env, uv sync --locked in work.

    Returns the env root when the base is a locked uv project (pyproject.toml
    + uv.lock); None keeps the ambient path unchanged. The env lives OUTSIDE
    the graded tree (``UV_PROJECT_ENVIRONMENT``), so materialization never
    pollutes the tree the oracle grades or the patch evidence.
    """
    if not has_locked_project(base):
        return None
    env_root = tmp / "project-env"
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = os.fspath(env_root)
    try:
        subprocess.run(
            ["uv", "sync", "--locked"],
            cwd=work, env=env, capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as e:
        raise OracleError(f"cannot materialize task environment: {e}") from e
    return env_root


def _run_oracle(
    manifest: TaskManifest,
    task_dir: Path,
    patch_text: str,
    *,
    overlay: OverlaySpec | None = None,
    selectors: tuple[str, ...] = (),
) -> tuple[HookResult, dict[str, str] | None]:
    """Run the oracle and return (hook result, resolved-version attestation).

    The attestation is None for ambient (stdlib/vendored) tasks; for a
    dependency-bearing task it is the full ``uv pip freeze`` of the
    materialized env grade actually executed — attested, never parsed from
    the lock.
    """
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(task_dir / "base", work, symlinks=True)
        try:
            subprocess.run(
                ["git", "init", "-q"], cwd=work, check=True, capture_output=True
            )
        except (OSError, subprocess.CalledProcessError) as e:
            raise ApplyError(f"cannot run git: {e}") from e
        applied = subprocess.run(
            ["git", "apply", "-"],
            input=os.fsencode(patch_text),
            cwd=work,
            capture_output=True,
        )
        if applied.returncode != 0:
            raise ApplyError(
                "patch did not apply: " + os.fsdecode(applied.stderr).strip()
            )
        if overlay is not None:
            materialize_overlay(overlay, work)
        fd, hook_path = tempfile.mkstemp(prefix="satyrn-hook-", suffix=".json")
        os.close(fd)
        os.unlink(hook_path)  # reserve a unique name; a silent oracle leaves NO file
        env_root = _materialize_project_env(work, Path(tmp), task_dir / "base")
        env = dict(os.environ)
        env[oracle_hook.RESULT_ENV] = hook_path
        if env_root is not None:
            env["PATH"] = os.fspath(env_root / "bin") + os.pathsep + env.get("PATH", "")
            env["PYTHONPATH"] = os.fspath(
                Path(satyrn_evals.__file__).resolve().parent.parent
            )
            env["PYTHONDONTWRITEBYTECODE"] = "1"
        else:
            env["PATH"] = (
                str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
            )
        run_started = time.time()
        try:
            subprocess.run(
                [*manifest.oracle, *selectors], cwd=work, env=env, capture_output=True
            )
        except OSError as e:
            raise OracleError(f"oracle failed to start: {e}") from e
        frozen: dict[str, str] | None = None
        if env_root is not None:
            try:
                freeze = subprocess.run(
                    ["uv", "pip", "freeze", "--python", os.fspath(env_root / "bin" / "python")],
                    capture_output=True, check=True, text=True,
                )
            except (OSError, subprocess.CalledProcessError) as e:
                raise OracleError(f"cannot attest task environment: {e}") from e
            frozen = parse_freeze(freeze.stdout)
        try:
            return load_hook_result(Path(hook_path), run_started), frozen
        finally:
            Path(hook_path).unlink(missing_ok=True)
