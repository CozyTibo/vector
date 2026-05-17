"""P07-25 — ``org_graph_retrieval`` tenant verification slice + readiness economics."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.normative import PHASE07_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.retrieval.retrieval_readiness_economics import (
    GP07_ECO01_GATE_ID_V1,
    GP07_ECO02_GATE_ID_V1,
    GP07_ECO03_GATE_ID_V1,
    RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1,
    RETRIEVAL_READINESS_ECONOMICS_SCHEMA_VERSION,
    build_retrieval_readiness_economics_receipt_v1,
    compute_retrieval_economics_receipt_hash_v1,
    verify_gp07_eco01_readiness_economics_clean_profile_static,
    verify_gp07_eco02_readiness_economics_hostile_profile_static,
    verify_gp07_eco03_admin_openapi_path_matrix_static,
)
from vector.domains.cortex.retrieval.retrieval_addressing import retrieval_golden_vectors_v1_root
from vector.domains.cortex.retrieval.retrieval_tenant_verification_slice import (
    GP07_TVER01_GATE_ID_V1,
    ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION,
    build_org_graph_retrieval_verification_slice_v1,
    compute_retrieval_verification_slice_hash_v1,
    index_epoch_code_v1,
    validate_org_graph_retrieval_verification_slice_v1,
    verify_gp07_tver01_org_graph_retrieval_slice_golden_static,
    verify_gp07_tver02_admin_openapi_path_matrix_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-verification-harness-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_constants() -> None:
    assert ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION >= 1
    assert RETRIEVAL_READINESS_ECONOMICS_SCHEMA_VERSION >= 1
    assert RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1 == "retrieval_readiness_economics_v1"


def test_all_step25_oracles_pass() -> None:
    assert verify_gp07_tver01_org_graph_retrieval_slice_golden_static()["passed"] is True
    assert verify_gp07_tver01_org_graph_retrieval_slice_golden_static()["id"] == GP07_TVER01_GATE_ID_V1
    assert verify_gp07_tver02_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp07_eco01_readiness_economics_clean_profile_static()["passed"] is True
    assert verify_gp07_eco01_readiness_economics_clean_profile_static()["id"] == GP07_ECO01_GATE_ID_V1
    assert verify_gp07_eco02_readiness_economics_hostile_profile_static()["passed"] is True
    assert verify_gp07_eco02_readiness_economics_hostile_profile_static()["id"] == GP07_ECO02_GATE_ID_V1
    assert verify_gp07_eco03_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp07_eco03_admin_openapi_path_matrix_static()["id"] == GP07_ECO03_GATE_ID_V1


def test_build_org_graph_retrieval_slice() -> None:
    tid = uuid.uuid4()
    body = build_org_graph_retrieval_verification_slice_v1(
        None,
        tenant_id=tid,
        verification_run_id="run-1",
    )
    assert validate_org_graph_retrieval_verification_slice_v1(body) == []
    assert body["tenant_id"] == str(tid)
    assert body["verification_run_id"] == "run-1"
    assert body["retrieval_program_freeze_version"] == PHASE07_PROGRAM_FREEZE_VERSION
    h = compute_retrieval_verification_slice_hash_v1(body)
    assert len(h) == 64
    assert h == compute_retrieval_verification_slice_hash_v1(body)


def test_index_epoch_code_stable() -> None:
    assert index_epoch_code_v1(None) == 0
    assert index_epoch_code_v1("") == 0
    a = index_epoch_code_v1("epoch-a")
    b = index_epoch_code_v1("epoch-a")
    assert a == b
    assert a != index_epoch_code_v1("epoch-b")


def test_readiness_economics_receipts() -> None:
    tid = uuid.uuid4()
    clean = build_retrieval_readiness_economics_receipt_v1(tenant_id=tid, profile="clean")
    assert clean["economics_violations"] == []
    assert clean["tenant_id"] == str(tid)
    hostile = build_retrieval_readiness_economics_receipt_v1(tenant_id=tid, profile="hostile")
    assert hostile["economics_violations"] == ["RETRIEVAL_ECO_GOLDEN_CASE_BUDGET"]
    stats = hostile["economics_stats"]
    h1 = compute_retrieval_economics_receipt_hash_v1(stats)
    assert len(h1) == 64
    assert h1 == compute_retrieval_economics_receipt_hash_v1(stats)


def test_golden_slice_file_present() -> None:
    path = (
        retrieval_golden_vectors_v1_root()
        / "tenant_verification"
        / "org_graph_retrieval_slice_good_v1.json"
    )
    assert path.is_file()


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-verification-harness-spec.md").read_text(
        encoding="utf-8"
    )
    assert "org_graph_retrieval" in text
    assert "G-P07-ECO-01" in text
    assert "G-P07-TVER-01" in text
