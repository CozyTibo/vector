"""Phase 08 Step 16 — synthesis artifact lineage."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.artifact_lineage_graph import persist_lineage_edge_v1
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.retrieval.retrieval_query_engine import index_tcre_chain_for_retrieval_v1
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    build_synthesis_intelligence_artifact_v1,
)
from vector.domains.cortex.synthesis.synthesis_bounded_caps import SD_LINEAGE_GAP_V1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_lineage import (
    GP08_LIN01_GATE_ID_V1,
    SD_LINEAGE_GAP_V1 as LINEAGE_SD,
    SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1,
    build_synthesis_artifact_lineage_chain_v1,
    list_synthesis_lineage_gap_sd_rows_v1,
    persist_synthesis_artifact_lineage_edges_v1,
    verify_gp08_lin01_synthesis_lineage_law_static,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8lin-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Lin User")
    tenant = Tenant(
        company_name="P8LIN",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8lin-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _retrieval_ingress(*, lookup_id: str, replay: str) -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: replay,
        "retrieval_evidence_hits": [{"retrieval_lookup_id": lookup_id, "evidence_legality_class": "replay_safe"}],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
        "tcre_binding_envelope": {"bind_state": "bound", "schema_version": 1},
    }


def _minimal_envelope(tenant_id: uuid.UUID) -> dict[str, object]:
    return {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
    }


@pytest.mark.parametrize("verifier", [verify_gp08_lin01_synthesis_lineage_law_static])
def test_gp08_lin01_static_gate(verifier: Callable[[], dict[str, Any]]) -> None:
    out = verifier()
    assert out["id"] == GP08_LIN01_GATE_ID_V1
    assert out["passed"] is True


def test_sd_lineage_gap_in_registry() -> None:
    assert SD_LINEAGE_GAP_V1 == LINEAGE_SD


def test_lineage_gap_rows_on_truncation() -> None:
    rows = list_synthesis_lineage_gap_sd_rows_v1(truncated=True)
    assert rows[0]["sd_code"] == LINEAGE_SD
    assert rows[0]["upstream_rd"] == "RD-LINEAGE-GAP"


def test_persist_and_build_lineage_chain(db_session: Session) -> None:
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
    artifact_id = str(uuid.uuid4())
    ingress = _retrieval_ingress(lookup_id=lookup_id, replay=replay)
    kinds = persist_synthesis_artifact_lineage_edges_v1(
        db_session,
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        retrieval_ingress=ingress,
        retrieval_subqueries=[{PHASE07_REPLAY_IDENTITY_FIELD_V1: replay}],
    )
    assert "synthesis_derived_from" in kinds
    assert "synthesis_indexes" in kinds
    chain = build_synthesis_artifact_lineage_chain_v1(
        db_session,
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        max_hops=32,
    )
    assert chain["terminal"]["kind"] == SYNTHESIS_TERMINAL_ARTIFACT_KIND_V1
    assert chain["terminal"]["ref"] == artifact_id
    assert chain["lineage_chain_digest"]


def test_apply_lineage_updates_artifact_digest(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    artifact_id = str(uuid.uuid4())
    ingress = _retrieval_ingress(lookup_id="sha256:" + "a" * 64, replay="rqid:lin")
    body = build_synthesis_intelligence_artifact_v1(
        session=db_session,
        tenant_id=tenant_id,
        job_id=uuid.uuid4(),
        envelope={"synthesis_workload_class": "degradation_brief", "synthesis_intent": "inspect", "execution_partition": "authoritative"},
        synthesis_legality_class="synthesis_degraded",
        synthesis_job_replay_identity="sha256:" + "b" * 64,
        synthesis_legality_posture={},
        retrieval_ingress=ingress,
        retrieval_subqueries=[{PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:lin"}],
        claims=[],
        synthesis_citation_envelope={"citations": [], "citation_count": 0},
        synthesis_omission_rows=[],
        synthesis_degradation_rollup={},
        llm_trace_refs=[],
        evidence_scope_summary={},
        artifact_id=uuid.UUID(artifact_id),
    )
    digest_with_lineage = body["lineage_chain_digest"]
    assert digest_with_lineage
    assert digest_with_lineage.startswith("sha256:") or len(digest_with_lineage) == 64


def test_orchestrator_artifact_lineage_digest(db_session: Session) -> None:
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
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {
        "retrieval_response": _retrieval_ingress(lookup_id=lookup_id, replay=replay),
    }
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    art_row = db_session.get(CortexSynthesisArtifact, uuid.UUID(str(out["artifact_id"])))
    assert art_row is not None
    digest = art_row.body_json["lineage_chain_digest"]
    assert digest
    assert digest.startswith("sha256:") or len(digest) == 64
