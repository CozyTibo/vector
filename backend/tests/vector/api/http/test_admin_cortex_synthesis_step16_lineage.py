"""Phase 08 Step 16 — admin synthesis lineage HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.lineage.artifact_lineage_graph import persist_lineage_edge_v1
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.retrieval.retrieval_query_engine import index_tcre_chain_for_retrieval_v1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_lineage import GP08_LIN01_GATE_ID_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8linadm-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Lin Adm")
    tenant = Tenant(
        company_name="P8LINADM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8linadm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_catalog_lineage_law_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/lineage-law",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == GP08_LIN01_GATE_ID_V1
    assert body["terminal_artifact_kind"] == "synthesis_intelligence"


def test_admin_artifact_detail_includes_lineage_panel(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain_id = f"chain-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain_id,
        replay_identity=replay,
        traversal_epoch=epoch,
    )
    lookup_id = str(row.retrieval_lookup_id)
    persist_lineage_edge_v1(
        db_session,
        tenant_id=tenant_id,
        from_artifact_kind="tcre_chain",
        from_artifact_ref=chain_id,
        to_artifact_kind="retrieval_index",
        to_artifact_ref=lookup_id,
        edge_kind="tcre_binds_index",
        replay_identity=replay,
    )
    db_session.flush()
    body = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
        "pinned_retrieval_receipt": {
            "retrieval_response": {
                "retrieval_legality_class": "retrieval_replay_safe",
                PHASE07_REPLAY_IDENTITY_FIELD_V1: replay,
                "retrieval_evidence_hits": [{"retrieval_lookup_id": lookup_id}],
                "retrieval_omission_rows": [],
                "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
                "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
                "tcre_binding_envelope": {"bind_state": "bound", "schema_version": 1},
            },
        },
    }
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    db_session.commit()
    artifact_id = out["artifact_id"]
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/artifacts/{artifact_id}",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    detail = r.json()
    panel = detail["lineage_panel"]
    assert panel["surface_kind"] == "synthesis_lineage_panel"
    assert panel["artifact_id"] == artifact_id
    artifact_digest = detail["synthesis_intelligence_artifact"]["lineage_chain_digest"]
    assert panel["lineage_chain_digest"] == artifact_digest
    assert artifact_digest
