"""Orchestrate grading: materialize, apply, run the oracle, write the receipt."""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from satyrn_evals import oracle_hook
from satyrn_evals.errors import (
    ApplyError,
    HookError,
    OracleError,
    PatchReadError,
    PatchRejected,
)
from satyrn_evals.manifest import TaskManifest, load_manifest
from satyrn_evals.patch import check_allowlist, parse_patch_paths
from satyrn_evals.receipt import Receipt, patch_digest, write_receipt
from satyrn_evals.verdict import (
    HookResult,
    HookResultData,
    Verdict,
    compute_verdict,
    describe_unavailable,
    load_hook_result,
)


def grade(task_dir: Path, patch_path: Path, receipt_path: Path) -> Receipt:
    """Grade PATCH against TASK, write the receipt, return it.

    Exit-code policy is the CLI's; this returns the artifact, whose
    `verdict` (pass/fail/unavailable) the caller maps to an exit code.
    """
    manifest = load_manifest(task_dir)
    try:
        patch_bytes = patch_path.read_bytes()
    except OSError as e:
        raise PatchReadError(f"cannot read patch: {e}") from e
    patch_text = os.fsdecode(patch_bytes)

    evidence: HookResultData | None = None
    reason = ""
    try:
        paths = parse_patch_paths(patch_text)
        check_allowlist(paths, manifest.source_paths)
        hook = _run_oracle(manifest, task_dir, patch_text)
        verdict = compute_verdict(hook, manifest.expected_test_ids)
        evidence = {
            "executed_test_ids": list(hook.executed_test_ids),
            "outcomes": hook.outcomes,
            "counts": hook.counts,
        }
        if verdict is Verdict.UNAVAILABLE:
            reason = describe_unavailable(hook, manifest.expected_test_ids)
    except (PatchRejected, ApplyError, OracleError, HookError) as e:
        verdict = Verdict.UNAVAILABLE
        reason = str(e)

    receipt = Receipt(
        task=manifest.name,
        patch_digest=patch_digest(patch_bytes),
        verdict=verdict,
        reason=reason,
        evidence=evidence,
    )
    write_receipt(receipt_path, receipt)
    return receipt


def _run_oracle(manifest: TaskManifest, task_dir: Path, patch_text: str) -> HookResult:
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
            raise ApplyError("patch did not apply: " + applied.stderr.decode().strip())
        fd, hook_path = tempfile.mkstemp(prefix="satyrn-hook-", suffix=".json")
        os.close(fd)
        os.unlink(hook_path)  # reserve a unique name; a silent oracle leaves NO file
        env = dict(os.environ)
        env[oracle_hook.RESULT_ENV] = hook_path
        env["PATH"] = (
            str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        )
        run_started = time.time()
        try:
            subprocess.run(manifest.oracle, cwd=work, env=env, capture_output=True)
        except OSError as e:
            raise OracleError(f"oracle failed to start: {e}") from e
        try:
            return load_hook_result(Path(hook_path), run_started)
        finally:
            Path(hook_path).unlink(missing_ok=True)
