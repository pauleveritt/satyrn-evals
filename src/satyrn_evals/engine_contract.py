"""Render the Engine contract from a task manifest plus the selected rung.

V11a spec §6. Today's ``engine-contract.yaml`` is hand-authored and shipped
for two tasks only; the six AgentClinic tasks have none, and the V8 smoke
used a hand-authored file that differed from the manifest by a token and
narrowed ``writable_paths`` to ``[app.py]``. Generating the file makes the
text the model sees the text on record.

The rendered bytes live at a deterministic path keyed by their own SHA-256
under the run's output root. A fresh per-attempt path would change the
recorded command, and ``compute_summary`` refuses mixed commands, so a batch
would not summarize (proposal correction 8).

Scalars are rendered with ``json.dumps``: a JSON string is a valid YAML 1.2
double-quoted scalar, so an arbitrary contract text — colons, quotes,
newlines — round-trips through ``yaml.safe_load`` with no dependency here.
"""

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from satyrn_evals.manifest import TaskManifest

# One directory per output root, holding every rendered contract a run used.
CONTRACTS_DIRNAME = "engine-contracts"

type WritablePaths = tuple[str, ...]


def writable_paths(task_dir: Path, source_paths: Sequence[str]) -> WritablePaths:
    """``writable_paths`` patterns derived from a manifest's ``source_paths``.

    A **file** entry stays exact. A **directory** entry becomes an fnmatch
    pattern over its descendants (``templates`` -> ``templates/*``), which
    ``fnmatch`` matches at any depth because its ``*`` spans ``/``.

    An entry with nothing at that path in ``base/`` stays exact: it is a
    creation target (``agentclinic-repair-framing-2`` declares ``models.py``
    and its base deletes the file), never a directory pattern.
    """
    base = task_dir / "base"
    return tuple(
        f"{entry}/*" if (base / entry).is_dir() else entry for entry in source_paths
    )


def contract_id(task: str, rung: str | None, digest: str) -> str:
    """A contract id that is stable for (task, rung, contract digest).

    ``<task>@<rung>+<digest prefix>``; the default contract is labelled
    ``contract``, the manifest field's own name. The label is an authoring
    claim and could collide with a rung literally named ``contract`` — the
    digest, not the label, is what pins the bytes.
    """
    return f"{task}@{rung if rung is not None else 'contract'}+{digest[:12]}"


def render_engine_contract(
    task_dir: Path,
    manifest: TaskManifest,
    *,
    rung: str | None,
    contract_text: str,
) -> bytes:
    """The Engine contract bytes for one task at one rung.

    Both ``id`` and ``task`` are emitted: Engine requires ``id`` as well as
    ``task`` (proposal correction 14). A manifest with no ``source_paths``
    has nothing writable and cannot be delivered against, so it is refused
    rather than rendered empty.
    """
    if not manifest.source_paths:
        raise ValueError(
            f"task {manifest.name} declares no source_paths; "
            "an Engine contract needs at least one writable path"
        )
    digest = hashlib.sha256(contract_text.encode("utf-8")).hexdigest()
    lines = [
        f"id: {json.dumps(contract_id(manifest.name, rung, digest))}",
        f"task: {json.dumps(contract_text)}",
        "writable_paths:",
    ]
    lines += [
        f"  - {json.dumps(pattern)}"
        for pattern in writable_paths(task_dir, manifest.source_paths)
    ]
    # `test_command` is emitted only when the task declares a public suite.
    # Absent, the Engine registers no `run_tests` tool and its pi argv is
    # byte-identical to what it was before satyrn-engine E7 -- so a task
    # that has not opted in is not silently given a new tool surface.
    if manifest.public_suite:
        lines.append("test_command:")
        lines += [f"  - {json.dumps(token)}" for token in manifest.public_suite]
    return ("\n".join(lines) + "\n").encode("utf-8")


def engine_contract_path(output: Path, rendered: bytes) -> Path:
    """The deterministic, digest-keyed path the rendered bytes live at."""
    digest = hashlib.sha256(rendered).hexdigest()
    return output / CONTRACTS_DIRNAME / f"{digest}.yaml"


def write_engine_contract(output: Path, rendered: bytes) -> Path:
    """Write the rendered bytes once, idempotently, and return their path.

    The path is stable across the cells of a run, so every cell records the
    same command and the batch summarizes (proposal correction 8). A second
    write of identical bytes is a no-op, so concurrent cells never race on
    content.
    """
    path = engine_contract_path(output, rendered)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_bytes(rendered)
    return path
