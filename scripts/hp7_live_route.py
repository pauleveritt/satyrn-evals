#!/usr/bin/env python3
"""HP7's one authorized live run: the packet route, composed with HP3
chained isolation, against a real `pi` process.

Instrument, not production code -- like `run_first_milestone.py`, this
accepts no recipe, makes the one frozen run
`docs/current/hp7-live-route-proof-pre-run-record.md` declares, and
reports what it retained. Every value below is the record's own frozen
table, not re-derived or re-decided here: `n = 1`, not extendable after
reading this run's result.

Preconditions 3 (environment), 4 (live completion) and 5 (machine quiet)
were checked by hand before this script existed and are not repeated
here as code -- they are one-shot checks the record itself names, not a
reusable gate. This script starts from precondition 1's own remaining
gap: no run against a real Pi process has happened yet.

Generalized 2026-09-10 for
`docs/current/te4-route-proof-pre-run-record.md`: `--task` and
`--task-tree-sha256` default to HP7's own frozen values, so every prior
invocation (HP7, the TE2/HP8 screen's Engine attempts) behaves exactly
as before. A caller naming a different task must also name that task's
own frozen digest -- there is no default drift check across tasks.
"""

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from satyrn_evals.adapters.engine_delivery import (  # noqa: E402
    engine_command_implementer,
    init_engine_repo,
)
from satyrn_evals.chain_record import (  # noqa: E402
    check_chain,
    decisions_from_record,
    load_chain_record,
    run_and_record_engine_chain,
)
from satyrn_evals.live_grading import live_session_grader  # noqa: E402
from satyrn_evals.manifest import load_manifest, resolve_task  # noqa: E402
from satyrn_evals.session_manifest import load_session_spec  # noqa: E402

#: HP7's own frozen task and digest, kept as the default so every existing
#: invocation is unaffected by the 2026-09-10 generalization below.
TASK_NAME = "agentclinic-session-phased"
FROZEN_TASK_TREE_SHA256 = (
    "1af60a147bcf6459fab39f2f94f75ba96968ae0dbfe1312ee52858d6b1053951"
)
#: Frozen in the pre-run record's "Run parameters" table.
TURN_BUDGET = 20
TOOL_CALL_BUDGET = 30
DELIVER_TIMEOUT_SECONDS = 600.0
SELF_TEST_TIMEOUT_SECONDS = 600
#: Frozen in the pre-run record's "The arm" table.
PI_MODEL = "omlx/gemma-4-12B-it-MLX-8bit"
PI_TOOLS = "read,write,edit"
SIBLING_ENGINE_BIN = (
    Path.home() / "projects/pauleveritt/satyrn-engine/.venv/bin/satyrn-engine"
)


def _implementer_argv() -> list[str]:
    return [
        "satyrn-evals-implementer-pi",
        "--model", PI_MODEL,
        "--tools", PI_TOOLS,
        "--timeout", str(SELF_TEST_TIMEOUT_SECONDS),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, required=True,
        help="Directory to hold the repo, harness, grading workspace and "
        "retained chain.json -- must not already exist.",
    )
    parser.add_argument(
        "--satyrn-engine-bin", type=Path, default=SIBLING_ENGINE_BIN,
    )
    parser.add_argument(
        "--task", default=TASK_NAME,
        help="Task name to resolve under src/satyrn_evals/tasks/. "
        "Defaults to HP7's own frozen task.",
    )
    parser.add_argument(
        "--task-tree-sha256", default=FROZEN_TASK_TREE_SHA256,
        help="Expected task tree digest; the run refuses to start if the "
        "actual tree has drifted. Must be supplied together with --task "
        "for any task other than HP7's own.",
    )
    args = parser.parse_args(argv)

    if args.output_dir.exists():
        print(f"refusing to overwrite existing {args.output_dir}", file=sys.stderr)
        return 2
    if not args.satyrn_engine_bin.is_file():
        print(f"satyrn-engine binary not found: {args.satyrn_engine_bin}", file=sys.stderr)
        return 2

    task_dir = resolve_task(args.task)
    manifest = load_manifest(task_dir)
    spec = load_session_spec(task_dir)

    h = hashlib.sha256()
    for p in sorted(task_dir.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(task_dir).as_posix().encode())
            h.update(p.read_bytes())
    actual_tree_sha256 = h.hexdigest()
    if actual_tree_sha256 != args.task_tree_sha256:
        print(
            f"task tree digest drifted: frozen {args.task_tree_sha256}, "
            f"actual {actual_tree_sha256} -- refusing to run under a stale "
            "pre-run record",
            file=sys.stderr,
        )
        return 2

    args.output_dir.mkdir(parents=True)
    repo = args.output_dir / "repo"
    harness_root = args.output_dir / "harness"
    grading_dir = args.output_dir / "grading"
    output_path = args.output_dir / "chain.json"

    print(f"materializing base/ into a real git repo at {repo}")
    initial_commit = init_engine_repo(task_dir / "base", repo)
    print(f"initial commit: {initial_commit}")

    implementer, receipts = engine_command_implementer(
        repo, str(args.satyrn_engine_bin), _implementer_argv(),
        timeout=DELIVER_TIMEOUT_SECONDS, harness_root=harness_root,
    )
    grader = live_session_grader(
        task_dir, manifest, spec, repo, initial_commit, receipts, grading_dir,
    )

    print(f"running the live chain -- n=1, turn_budget={TURN_BUDGET}, "
          f"tool_call_budget={TOOL_CALL_BUDGET}")
    record = run_and_record_engine_chain(
        task_dir, manifest, spec, implementer, receipts, repo, grader,
        output_path, turn_budget=TURN_BUDGET, tool_call_budget=TOOL_CALL_BUDGET,
    )

    print(f"\nretained: {output_path}")
    reloaded = load_chain_record(output_path)
    assert reloaded == record, "retained record does not read back identically"

    print(f"\nphases retained: {len(record.phases)}")
    for phase in record.phases:
        print(
            f"  {phase.step_id}: accepted={phase.accepted!r} "
            f"reason={phase.reason!r} "
            f"implementer_mutations={len(phase.implementer_mutations or ())} "
            f"self_test_ran={phase.self_test_outcome is not None}"
        )
    print(f"\nfinal_decision: {record.final_decision}")

    decisions = decisions_from_record(record)
    print(f"\ndecisions_from_record: {[(d.step_id, d.accepted) for d in decisions]}")

    findings = check_chain(record)
    print(f"\ncheck_chain findings ({len(findings)}):")
    for finding in findings:
        print(f"  {finding.step_id}: {finding.reason}")
    if not findings:
        print("  (none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
