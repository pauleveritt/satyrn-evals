"""Verdict receipt: the durable artifact grading produces and re-scoring reads."""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from satyrn_evals.verdict import HookResultData, Verdict


@dataclass(frozen=True, slots=True)
class Receipt:
    task: str
    patch_digest: str
    verdict: Verdict
    reason: str
    evidence: HookResultData | None
    contamination: dict | None = None
    resolved_versions: dict[str, str] | None = None


def patch_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json_atomically(path: Path, data: object) -> None:
    """Replace ``path`` only after its complete JSON payload is written.

    Attempt records and receipts are paired evidence.  A deadline can observe
    the narrow interval between their publications, so neither writer may
    expose a half-written JSON object to recovery or regrading.
    """
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_receipt(path: Path, receipt: Receipt) -> None:
    data = asdict(receipt)
    if receipt.contamination is None:
        data.pop("contamination")
    if receipt.resolved_versions is None:
        data.pop("resolved_versions")
    write_json_atomically(path, data)
