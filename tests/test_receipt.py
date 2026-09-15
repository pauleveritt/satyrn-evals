import json

import pytest

import satyrn_evals.receipt as receipt_module
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
        task="t",
        patch_digest="d",
        verdict=Verdict.UNAVAILABLE,
        reason="boom",
        evidence=None,
    )
    write_receipt(path, receipt)
    data = json.loads(path.read_text())
    assert data["verdict"] == "unavailable"
    assert data["evidence"] is None


def test_receipt_publication_does_not_replace_prior_evidence_on_failure(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "receipt.json"
    prior = '{"verdict": "pass"}\n'
    path.write_text(prior)
    monkeypatch.setattr(
        receipt_module.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("disk failure")),
    )

    with pytest.raises(OSError, match="disk failure"):
        write_receipt(path, Receipt("t", "d", Verdict.FAIL, "", None))

    assert path.read_text() == prior
    assert list(tmp_path.glob(".receipt.json.*.tmp")) == []


def test_visible_receipt_has_no_contamination_key(tmp_path) -> None:
    receipt = Receipt("t", "d", Verdict.PASS, "", None)
    path = tmp_path / "receipt.json"
    write_receipt(path, receipt)
    assert "contamination" not in json.loads(path.read_text())


def test_hidden_receipt_round_trips_contamination(tmp_path) -> None:
    finding = {
        "visibility": "hidden",
        "checks": [
            {"check": "grader_content_in_patch", "outcome": "clean", "evidence": []}
        ],
    }
    receipt = Receipt("t", "d", Verdict.PASS, "", None, contamination=finding)
    path = tmp_path / "receipt.json"
    write_receipt(path, receipt)
    assert json.loads(path.read_text())["contamination"] == finding


def test_receipt_omits_resolved_versions_when_none(tmp_path) -> None:
    receipt = Receipt("t", "d", Verdict.PASS, "ok", None)  # defaults None
    path = tmp_path / "receipt.json"
    write_receipt(path, receipt)
    assert "resolved_versions" not in json.loads(path.read_text())


def test_receipt_serializes_resolved_versions_when_present(tmp_path) -> None:
    receipt = Receipt(
        "t", "d", Verdict.PASS, "ok", None, resolved_versions={"fastapi": "0.115.10"}
    )
    path = tmp_path / "receipt.json"
    write_receipt(path, receipt)
    data = json.loads(path.read_text())
    assert data["resolved_versions"] == {"fastapi": "0.115.10"}


def test_receipt_omits_ignored_paths_when_none_were_dropped(tmp_path) -> None:
    path = tmp_path / "receipt.json"
    write_receipt(path, Receipt("t", "d", Verdict.PASS, "ok", None))
    assert "ignored_paths" not in json.loads(path.read_text())


def test_receipt_lists_the_ignored_paths_it_dropped(tmp_path) -> None:
    path = tmp_path / "receipt.json"
    write_receipt(path, Receipt("t", "d", Verdict.PASS, "ok", None, ignored_paths=("PROVENANCE.md",)))
    assert json.loads(path.read_text())["ignored_paths"] == ["PROVENANCE.md"]
