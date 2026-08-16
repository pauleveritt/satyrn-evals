import json

from satyrn_evals.receipt import Receipt, patch_digest, write_receipt
from satyrn_evals.verdict import HookResultData, Verdict


def test_patch_digest_is_sha256() -> None:
    assert (
        patch_digest(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_write_receipt_roundtrip(tmp_path) -> None:
    path = tmp_path / "r.json"
    evidence: HookResultData = {
        "executed_test_ids": ["a::t1"],
        "outcomes": {"a::t1": "passed"},
        "counts": {"passed": 1, "failed": 0, "error": 0, "skipped": 0},
    }
    receipt = Receipt(
        task="t",
        patch_digest="d",
        verdict=Verdict.PASS,
        reason="",
        evidence=evidence,
    )
    write_receipt(path, receipt)
    data = json.loads(path.read_text())
    assert data["task"] == "t"
    assert data["patch_digest"] == "d"
    assert data["verdict"] == "pass"
    assert data["reason"] == ""
    assert data["evidence"]["counts"]["passed"] == 1


def test_write_receipt_unavailable(tmp_path) -> None:
    path = tmp_path / "u.json"
    receipt = Receipt(
        task="t", patch_digest="d", verdict=Verdict.UNAVAILABLE, reason="boom", evidence=None
    )
    write_receipt(path, receipt)
    data = json.loads(path.read_text())
    assert data["verdict"] == "unavailable"
    assert data["evidence"] is None
