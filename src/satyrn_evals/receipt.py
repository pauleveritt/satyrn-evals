"""Verdict receipt: the durable artifact grading produces and re-scoring reads."""

import hashlib
import json
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


def patch_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_receipt(path: Path, receipt: Receipt) -> None:
    data = asdict(receipt)
    if receipt.contamination is None:
        del data["contamination"]
    path.write_text(json.dumps(data, indent=2) + "\n")
