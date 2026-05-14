"""P05-10 — hop receipt doctrine (**G-P05-HR-01**, **G-P05-HR-02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.hop_receipt_contract import (
    HR_RUNTIME_SCHEMA_VERSION,
    HopReceiptContractError,
    extract_evidence_envelope_v1,
    octs_hop_receipt_fixture_dir,
    recomputed_edge_fingerprint_from_receipt_v1,
    validate_hop_receipt_list_contract_v1,
    validate_hop_receipt_list_for_hash_body_v1,
    verify_gp05_hr01_fingerprint_recompute_from_envelope_static,
    verify_gp05_hr02_dangling_org_link_rejected_static,
)
from vector.domains.cortex.traversal.walk_result_contract import (
    validate_walk_result_hash_body_contract_v1,
)


def test_hr_runtime_schema_version() -> None:
    assert HR_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_hr01_static_passes() -> None:
    out = verify_gp05_hr01_fingerprint_recompute_from_envelope_static()
    assert out["id"] == "G-P05-HR-01"
    assert out["passed"] is True


def test_verify_gp05_hr02_static_passes() -> None:
    out = verify_gp05_hr02_dangling_org_link_rejected_static()
    assert out["id"] == "G-P05-HR-02"
    assert out["passed"] is True


def test_fixture_dir() -> None:
    d = octs_hop_receipt_fixture_dir()
    assert (d / "hop_receipt_observed_good_v1.json").is_file()


def test_recomputed_fingerprint_matches_fixture() -> None:
    path = octs_hop_receipt_fixture_dir() / "hop_receipt_observed_good_v1.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert recomputed_edge_fingerprint_from_receipt_v1(rec) == (
        "sha256:5a43fea3b0d7248b5fd351e686cf0433fdc7fd146ecf511eecc74f509fb378ab"
    )


def test_hr02_rejects_same_fingerprint_two_sequences_without_revisit() -> None:
    path = octs_hop_receipt_fixture_dir() / "hop_receipt_observed_good_v1.json"
    base = json.loads(path.read_text(encoding="utf-8"))
    r0 = json.loads(json.dumps(base))
    r1 = json.loads(json.dumps(base))
    r1["hop_sequence"] = 1
    with pytest.raises(HopReceiptContractError, match="HR-02"):
        validate_hop_receipt_list_contract_v1(
            [r0, r1],
            pinned_org_link_ids=None,
            allow_dangling_evidence_refs=True,
            allow_revisit_vertices=False,
        )


def test_hr02_allows_same_fingerprint_two_sequences_when_revisit_allowed() -> None:
    path = octs_hop_receipt_fixture_dir() / "hop_receipt_observed_good_v1.json"
    base = json.loads(path.read_text(encoding="utf-8"))
    r0 = json.loads(json.dumps(base))
    r1 = json.loads(json.dumps(base))
    r1["hop_sequence"] = 1
    validate_hop_receipt_list_contract_v1(
        [r0, r1],
        pinned_org_link_ids=None,
        allow_dangling_evidence_refs=True,
        allow_revisit_vertices=True,
    )


def test_extract_envelope_nested() -> None:
    path = octs_hop_receipt_fixture_dir() / "hop_receipt_observed_good_v1.json"
    rec = json.loads(path.read_text(encoding="utf-8"))
    env = extract_evidence_envelope_v1(rec)
    assert env is not None
    assert env["org_link_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def test_hash_body_with_hop_receipts_passes_contract() -> None:
    """``validate_walk_result_hash_body_contract_v1`` delegates hop validation (**P05-10**)."""
    path = octs_hop_receipt_fixture_dir() / "hop_receipt_observed_good_v1.json"
    hop = json.loads(path.read_text(encoding="utf-8"))
    body = {
        "octs_schema_version": 1,
        "temporal_anchor": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "export_id": "00000000-0000-0000-0000-000000000002",
            "export_sequence": 1,
            "projection_content_hash": (
                "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            ),
            "snapshot_unix_ns": {"unix_ns": 1},
            "graph_as_of_unix_ns": {"unix_ns": 1},
        },
        "policy_hash": "sha256:" + "b" * 64,
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "termination_reason": "budget_exhausted",
        "hop_receipts": [hop],
        "execution_path_contains_derived": False,
        "path_edge_fingerprints_ordered": [
            "sha256:5a43fea3b0d7248b5fd351e686cf0433fdc7fd146ecf511eecc74f509fb378ab",
        ],
    }
    validate_walk_result_hash_body_contract_v1(body)


def test_validate_hop_receipt_list_for_hash_body_skips_dangling() -> None:
    path = octs_hop_receipt_fixture_dir() / "hop_receipt_dangling_bundle_v1.json"
    bundle = json.loads(path.read_text(encoding="utf-8"))
    dangling = bundle["dangling_receipt"]
    validate_hop_receipt_list_for_hash_body_v1([dangling])
