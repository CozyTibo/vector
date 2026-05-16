"""P06-34 — ``org_graph_reasoning`` tenant verification slice + readiness economics."""

from __future__ import annotations

import uuid

from vector.domains.cortex.reasoning.normative import PHASE06_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.reasoning.reasoning_readiness_economics import (
    REASONING_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1,
    REASONING_READINESS_ECONOMICS_CONTRACT_V1,
    REASONING_READINESS_ECONOMICS_SCHEMA_VERSION,
    build_reasoning_readiness_economics_receipt_v1,
    compute_reasoning_economics_receipt_hash_v1,
    verify_gp06_rreco01_readiness_economics_clean_profile_static,
    verify_gp06_rreco02_readiness_economics_hostile_profile_static,
    verify_gp06_rreco03_admin_openapi_path_matrix_static,
)
from vector.domains.cortex.reasoning.reasoning_tenant_verification_slice import (
    ORG_GRAPH_REASONING_VERIFICATION_SLICE_SCHEMA_VERSION,
    REASONING_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1,
    build_org_graph_reasoning_verification_slice_v1,
    compute_reasoning_verification_slice_hash_v1,
    validate_org_graph_reasoning_verification_slice_v1,
    verify_gp06_rtvs01_org_graph_reasoning_slice_golden_static,
    verify_gp06_rtvs02_admin_openapi_path_matrix_static,
)


def test_constants() -> None:
    assert ORG_GRAPH_REASONING_VERIFICATION_SLICE_SCHEMA_VERSION >= 1
    assert REASONING_READINESS_ECONOMICS_SCHEMA_VERSION >= 1
    assert REASONING_READINESS_ECONOMICS_CONTRACT_V1 == "reasoning_readiness_economics_v1"
    assert REASONING_TENANT_VERIFICATION_SLICE_ADMIN_OPENAPI_PATHS_V1[0].endswith(
        "reasoning/tenant-verification-slice"
    )
    assert REASONING_READINESS_ECONOMICS_ADMIN_OPENAPI_PATHS_V1[0].endswith(
        "reasoning/readiness-economics"
    )


def test_all_step34_oracles_pass() -> None:
    assert verify_gp06_rtvs01_org_graph_reasoning_slice_golden_static()["passed"] is True
    assert verify_gp06_rtvs02_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp06_rreco01_readiness_economics_clean_profile_static()["passed"] is True
    assert verify_gp06_rreco02_readiness_economics_hostile_profile_static()["passed"] is True
    assert verify_gp06_rreco03_admin_openapi_path_matrix_static()["passed"] is True


def test_build_org_graph_reasoning_slice() -> None:
    tid = uuid.uuid4()
    body = build_org_graph_reasoning_verification_slice_v1(
        None,
        tenant_id=tid,
        verification_run_id="run-1",
    )
    assert validate_org_graph_reasoning_verification_slice_v1(body) == []
    assert body["tenant_id"] == str(tid)
    assert body["verification_run_id"] == "run-1"
    assert body["phase06_program_freeze_version"] == PHASE06_PROGRAM_FREEZE_VERSION
    h = compute_reasoning_verification_slice_hash_v1(body)
    assert len(h) == 64
    assert h == compute_reasoning_verification_slice_hash_v1(body)


def test_readiness_economics_receipts() -> None:
    tid = uuid.uuid4()
    clean = build_reasoning_readiness_economics_receipt_v1(tenant_id=tid, profile="clean")
    assert clean["economics_violations"] == []
    assert clean["tenant_id"] == str(tid)
    hostile = build_reasoning_readiness_economics_receipt_v1(tenant_id=tid, profile="hostile")
    assert hostile["economics_violations"] == ["REASONING_ECO_GOLDEN_CASE_BUDGET"]
    stats = hostile["economics_stats"]
    h1 = compute_reasoning_economics_receipt_hash_v1(stats)
    assert len(h1) == 64
    assert h1 == compute_reasoning_economics_receipt_hash_v1(stats)
