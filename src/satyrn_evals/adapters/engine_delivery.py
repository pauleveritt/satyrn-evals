"""The engine-composed `Implementer`: drives real `satyrn-engine deliver
--base` calls across phases, one isolated worktree per phase, tracking
the running candidate commit itself. See
`docs/superpowers/specs/2026-09-10-hp3-composition-design.md` for why
this is a separate seam from `route.command_implementer` rather than a
variant of it.
"""

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

from satyrn_evals.errors import RouteError
from satyrn_evals.packet import HandoffPacket, contract_yaml, worker_projection
from satyrn_evals.route import (
    DEFAULT_SELF_TEST_TIMEOUT_SECONDS,
    Implementer,
    ImplementerResult,
    run_self_test,
    self_test_outcome_to_dict,
)


def init_engine_repo(base_dir: Path, repo_dir: Path) -> str:
    """Materialize `base_dir`'s contents into a fresh git repository at
    `repo_dir` and commit them once. Returns that commit's sha -- phase
    1's implicit base, the same "materialize before inference" step
    HP7's own precondition 3 already requires, with one thing added: a
    real git history for `deliver --base` to branch from.
    """
    repo_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base_dir, repo_dir, dirs_exist_ok=True)

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True
        )

    run("init", "--quiet", "--initial-branch=main")
    run("config", "user.name", "satyrn-evals engine seam")
    run("config", "user.email", "engine-seam@example.invalid")
    run("add", "-A")
    run("commit", "--quiet", "-m", "base")
    return run("rev-parse", "HEAD").stdout.strip()


def build_deliver_argv(
    satyrn_engine_bin: str,
    repo: Path,
    contract_path: Path,
    timeout: float,
    *,
    base: str | None,
    implementer_argv: list[str],
) -> list[str]:
    """The `satyrn-engine deliver` CLI invocation for one phase. `base`
    omitted (not passed as an empty string) for phase 1 -- `deliver`'s own
    default is the repo's HEAD, and an empty `--base` would be refused by
    `_nonblank_base` on the engine side rather than silently doing the
    same thing.
    """
    argv = [
        satyrn_engine_bin,
        "deliver",
        "--repo",
        str(repo),
        "--timeout",
        str(timeout),
    ]
    if base is not None:
        argv += ["--base", base]
    argv += [str(contract_path), "--", *implementer_argv]
    return argv


def deliver_result_from_receipt(
    receipt: Mapping[str, object],
) -> ImplementerResult:
    """Map one `deliver` receipt to the implementer's report.

    The engine now runs the contract's own test command and returns
    ``TESTS_FAILED`` for a retained failing candidate; that is still a
    delivered candidate, so it reports ``delivered`` exactly as ``OK``
    does. ``reported_outcome`` stays "were files delivered", never "did
    tests pass" -- the authoritative validation verdict is carried on the
    retained phase record from ``receipt["validation"]``, not here.
    """
    code = receipt.get("code")
    changed = receipt.get("changed_paths")
    if code in ("OK", "TESTS_FAILED") and isinstance(changed, list) and changed:
        return ImplementerResult(
            changed_files=tuple(changed),
            reported_outcome="delivered",
            message=None,
        )
    return ImplementerResult(
        changed_files=(),
        reported_outcome="refused",
        message=str(receipt.get("message") or code),
    )


def _materialize_commit(repo: Path, commit: str, dest: Path) -> None:
    """Extract `commit`'s tree into `dest` without touching `repo`'s own
    checkout -- there isn't one to touch: `deliver` runs each phase in a
    temporary worktree it deletes on success, so no live directory holding
    that phase's files survives past the receipt. `git archive` reads
    straight from the object store, the same reason `engine_evidence.py`
    uses `git show` rather than a live file read.
    """
    archive = subprocess.run(
        ["git", "archive", "--format=tar", commit],
        cwd=repo, capture_output=True, check=True,
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)


def engine_command_implementer(
    repo: Path,
    satyrn_engine_bin: str,
    implementer_argv: list[str],
    *,
    timeout: float,
    harness_root: Path,
    initial_base: str | None = None,
    self_test_timeout: int = DEFAULT_SELF_TEST_TIMEOUT_SECONDS,
) -> tuple[Implementer, list[dict[str, object]]]:
    """Returns `(implementer, receipts)`. `receipts` is appended to, one
    parsed JSON receipt per call, in phase order -- `run_and_record_engine_chain`
    reads it after the chain finishes; nothing about `ImplementerResult`
    itself carries a candidate commit, so this is the side channel that
    does. A delivered candidate (``OK`` or ``TESTS_FAILED``) also carries the
    engine's authoritative ``validation``/``validation_exit``/
    ``validation_output`` fields on the receipt, which the retention layer
    carries into the phase record; the engine owns the verdict. The
    harness-run ``self_test_outcome`` below is retained **only as a
    cross-check** against the same candidate, never as the authority: it
    cannot upgrade or downgrade ``receipt["validation"]``.
    """
    receipts: list[dict[str, object]] = []
    state: dict[str, str | None] = {"base": initial_base}

    def implement(packet: HandoffPacket) -> ImplementerResult:  # pragma: no cover
        # Integration tier only: this spawns a real satyrn-engine process.
        step_id = f"phase-{len(receipts) + 1}"
        # One shared harness_root across the whole chain, matching
        # command_implementer's own invariant -- a fake implementer that
        # tracks its phase via a counter file (fake_implementer.py) relies
        # on harness_dir being the *same* directory on every call. A
        # per-step subdirectory here defeated that: each phase's counter
        # read back "absent", so every phase replayed phase 1's fixture,
        # which happened to be byte-identical to what phase 1 had already
        # committed -- surfacing as a spurious NO_CHANGES on phase 2, not
        # a crash. Filenames are namespaced by step_id instead.
        harness_root.mkdir(parents=True, exist_ok=True)
        contract_path = harness_root / f"{step_id}-contract.yaml"
        contract_path.write_text(contract_yaml(packet, step_id))
        result_path = harness_root / f"{step_id}-result.json"
        packet_path = harness_root / f"{step_id}-packet.json"
        packet_path.write_text(json.dumps(worker_projection(packet)))
        result_path.unlink(missing_ok=True)

        argv = build_deliver_argv(
            satyrn_engine_bin, repo, contract_path, timeout,
            base=state["base"], implementer_argv=implementer_argv,
        )
        env = {
            **os.environ,
            "SATYRN_HANDOFF_PACKET": str(packet_path),
            "SATYRN_IMPLEMENTER_RESULT": str(result_path),
        }
        proc = subprocess.run(argv, capture_output=True, text=True, env=env)
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        if not lines:
            raise RouteError(
                f"satyrn-engine deliver produced no receipt on stdout "
                f"(exit {proc.returncode}); stderr: {proc.stderr}"
            )
        receipt = json.loads(lines[-1])
        receipts.append(receipt)

        if receipt.get("code") in ("OK", "TESTS_FAILED") and receipt.get(
            "changed_paths"
        ):
            state["base"] = receipt.get("candidate_commit")
            if packet.self_test_command:
                # Cross-check, never the authority: the engine's own
                # validation run (``receipt["validation"]``) is the recorded
                # verdict; this second run against a `git archive` of the
                # same candidate is retained only as corroborating evidence.
                with tempfile.TemporaryDirectory(
                    prefix="satyrn-engine-self-test-"
                ) as scratch:
                    candidate_dir = Path(scratch)
                    _materialize_commit(
                        repo, str(receipt["candidate_commit"]), candidate_dir
                    )
                    outcome = run_self_test(
                        packet.self_test_command, candidate_dir, self_test_timeout
                    )
                receipt["self_test_outcome"] = self_test_outcome_to_dict(outcome)
            return deliver_result_from_receipt(receipt)
        return deliver_result_from_receipt(receipt)

    implement.executable_seam = True  # type: ignore[attr-defined]
    return implement, receipts
