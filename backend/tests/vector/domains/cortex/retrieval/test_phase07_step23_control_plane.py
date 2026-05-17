"""P07-23 — retrieval admin control plane catalog (**G-P07-CP-01**)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_control_plane import (
    GP07_CP01_GATE_ID_V1,
    PHASE07_RETRIEVAL_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_ADMIN_OPENAPI_PATHS_V1,
    RETRIEVAL_CONTROL_PLANE_SURFACES_V1,
    RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1,
    RETRIEVAL_RBAC_PERMISSION_QUERY_V1,
    RETRIEVAL_RBAC_PERMISSION_READ_V1,
    build_retrieval_control_plane_surface_checklist_v1,
    build_retrieval_control_plane_v1,
    build_retrieval_rbac_matrix_v1,
    list_retrieval_query_audit_trail_v1,
    retrieval_admin_openapi_path_v1,
    verify_gp07_cp01_retrieval_control_plane_rbac_static,
    verify_retrieval_control_plane_surface_registry_static,
)
from vector.domains.cortex.retrieval.retrieval_observability import (
    persist_retrieval_query_audit_v1,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-admin-control-plane-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION >= 1


def test_sixteen_surfaces_defined() -> None:
    assert len(RETRIEVAL_CONTROL_PLANE_SURFACES_V1) == 16
    checklist = build_retrieval_control_plane_surface_checklist_v1()
    assert len(checklist) == 16
    assert sum(1 for s in checklist if s["wired_at_closure"]) == 16


def test_gp07_cp01_static_gates() -> None:
    assert verify_retrieval_control_plane_surface_registry_static()["passed"] is True
    out = verify_gp07_cp01_retrieval_control_plane_rbac_static()
    assert out["passed"] is True
    assert out["id"] == GP07_CP01_GATE_ID_V1


def test_openapi_matrix_file_exists() -> None:
    path = retrieval_admin_openapi_path_v1()
    assert path.is_file()
    assert "/control-plane" in "".join(RETRIEVAL_ADMIN_OPENAPI_PATHS_V1)
    assert "/audit" in "".join(RETRIEVAL_ADMIN_OPENAPI_PATHS_V1)


def test_rbac_matrix_permissions() -> None:
    rb = build_retrieval_rbac_matrix_v1()
    assert RETRIEVAL_RBAC_PERMISSION_QUERY_V1 in rb["permissions"]
    assert RETRIEVAL_RBAC_PERMISSION_READ_V1 in rb["permissions"]
    assert RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1 in rb["permissions"]


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (
        root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-admin-control-plane-spec.md"
    ).read_text(encoding="utf-8")
    assert "Control plane aggregate" in text
    assert "cortex.retrieval.query" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7cp-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 CP")
    tenant = Tenant(
        company_name="P7CP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7cp-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_control_plane_aggregate(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    doc = build_retrieval_control_plane_v1(db_session, tenant_id=tenant_id)
    assert doc["surfaces_total"] == 16
    assert doc["surfaces_wired_count"] == 16
    assert doc["gate_id"] == GP07_CP01_GATE_ID_V1
    assert "workload_histogram" in doc
    assert "health_strip" in doc


@pytest.mark.integration
def test_audit_trail_after_query(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch=epoch,
    )
    db_session.commit()
    execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "causal_chain",
            "intent": "inspect",
            "addressing": {"retrieval_lookup_id": row.retrieval_lookup_id},
            "replay_pins": {
                "index_epoch": epoch,
                "tcre_policy_bundle_digest": "sha256:policy-stub",
                "octs_engine_build_ref": "build-stub",
            },
            "expected_replay_identity": replay,
            "selection_policy": {"max_hits": 50},
        },
    )
    db_session.commit()
    trail = list_retrieval_query_audit_trail_v1(db_session, tenant_id=tenant_id, limit=10)
    assert len(trail) >= 1
    assert trail[0]["workload_class"] == "causal_chain"


@pytest.mark.integration
def test_persist_audit_direct(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    persist_retrieval_query_audit_v1(
        db_session,
        tenant_id=tenant_id,
        envelope={"workload_class": "lineage_explorer", "intent": "inspect", "execution_partition": "authoritative"},
        result={
            "retrieval_legality_class": "retrieval_replay_safe",
            "retrieval_query_replay_identity": "sha256:" + "e" * 64,
            "hits": [],
            "omissions": [],
            "retrieval_query_receipt": {"receipt_digest": "sha256:" + "f" * 64},
        },
        duration_ms=3,
    )
    db_session.commit()
    hist = build_retrieval_control_plane_v1(db_session, tenant_id=tenant_id)
    assert hist["workload_histogram"].get("lineage_explorer", 0) >= 1
