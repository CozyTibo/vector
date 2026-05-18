"""Phase 08 Step 15 — retrieval/TCRE binding copy on artifacts."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.phase_boundaries import SD_UPSTREAM_RD_V1
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    build_synthesis_intelligence_artifact_v1,
    compute_synthesis_artifact_digest_v1,
)
from vector.domains.cortex.synthesis.synthesis_bindings import (
    GP08_BIND01_GATE_ID_V1,
    build_degradation_propagation_chain_v1,
    build_retrieval_binding_envelope_v1,
    build_synthesis_binding_bundle_v1,
    copy_tcre_binding_envelope_v1,
    list_tcre_binding_gap_sd_rows_v1,
    verify_gp08_bind01_copy_only_static,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8bnd-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Bnd User")
    tenant = Tenant(
        company_name="P8BND",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8bnd-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _retrieval_ingress_with_tcre(*, bind_state: str = "bound") -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        "chronology_legality_class": "chronology_bounded",
        "causal_legality_class": "causal_partial",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-bind",
        "retrieval_omission_rows": [{"retrieval_omission_class": "RD-TCRE-GAP"}],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
        "tcre_binding_envelope": {
            "schema_version": 1,
            "bind_state": bind_state,
            "tcre_reconstruction_job_id": "job-1",
        },
        "retrieval_evidence_hits": [],
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


@pytest.mark.parametrize("verifier", [verify_gp08_bind01_copy_only_static])
def test_gp08_bind01_static_gate(verifier: Callable[[], dict[str, Any]]) -> None:
    out = verifier()
    assert out["id"] == GP08_BIND01_GATE_ID_V1
    assert out["passed"] is True


def test_copy_tcre_envelope_is_shallow_copy() -> None:
    ingress = _retrieval_ingress_with_tcre(bind_state="bound")
    copied = copy_tcre_binding_envelope_v1(ingress)
    assert copied["bind_state"] == "bound"
    copied["bind_state"] = "mutated"
    assert ingress["tcre_binding_envelope"]["bind_state"] == "bound"


def test_retrieval_binding_copies_legality_without_upgrade() -> None:
    ingress = _retrieval_ingress_with_tcre()
    rb = build_retrieval_binding_envelope_v1(
        retrieval_ingress=ingress,
        retrieval_subqueries=[{PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-bind"}],
    )
    assert rb["retrieval_legality_class"] == "retrieval_replay_safe"
    assert rb["chronology_legality_class"] == "chronology_bounded"
    assert rb["causal_legality_class"] == "causal_partial"


def test_degradation_propagation_chain_maps_rd_to_sd() -> None:
    ingress = _retrieval_ingress_with_tcre()
    chain = build_degradation_propagation_chain_v1(
        retrieval_ingress=ingress,
        synthesis_omission_rows=[],
    )
    assert any(row["rd_code"] == "RD-TCRE-GAP" and row["sd_code"] == SD_UPSTREAM_RD_V1 for row in chain)


def test_tcre_bind_failure_emits_sd_upstream_rd() -> None:
    ingress = _retrieval_ingress_with_tcre(bind_state="failed")
    tcre = copy_tcre_binding_envelope_v1(ingress)
    rows = list_tcre_binding_gap_sd_rows_v1(tcre)
    assert rows[0]["sd_code"] == SD_UPSTREAM_RD_V1


def test_artifact_digest_includes_bindings() -> None:
    ingress = _retrieval_ingress_with_tcre()
    tid = uuid.UUID(int=0)
    body = build_synthesis_intelligence_artifact_v1(
        tenant_id=tid,
        job_id=uuid.uuid4(),
        envelope={
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        synthesis_legality_class="synthesis_degraded",
        synthesis_job_replay_identity="sha256:" + "a" * 64,
        synthesis_legality_posture={},
        retrieval_ingress=ingress,
        retrieval_subqueries=[{PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-bind"}],
        claims=[],
        synthesis_citation_envelope={"citations": [], "citation_count": 0},
        synthesis_omission_rows=[],
        synthesis_degradation_rollup={},
        llm_trace_refs=[],
        evidence_scope_summary={},
    )
    assert body.get("retrieval_binding_envelope")
    assert body.get("tcre_binding_envelope")
    assert body.get("degradation_propagation_chain")
    without = dict(body)
    without.pop("retrieval_binding_envelope", None)
    without.pop("tcre_binding_envelope", None)
    without.pop("degradation_propagation_chain", None)
    without["artifact_digest"] = compute_synthesis_artifact_digest_v1(without)
    assert body["artifact_digest"] != without["artifact_digest"]


def test_orchestrator_artifact_has_binding_envelopes(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _retrieval_ingress_with_tcre()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    row = db_session.get(CortexSynthesisArtifact, uuid.UUID(str(out["artifact_id"])))
    assert row is not None
    art = row.body_json
    assert art["retrieval_binding_envelope"]["retrieval_legality_class"] == "retrieval_replay_safe"
    assert art["tcre_binding_envelope"]["bind_state"] == "bound"
    assert art["degradation_propagation_chain"]


def test_binding_bundle_deterministic() -> None:
    ingress = _retrieval_ingress_with_tcre()
    sub = [{PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-bind"}]
    a = build_synthesis_binding_bundle_v1(retrieval_ingress=ingress, retrieval_subqueries=sub)
    b = build_synthesis_binding_bundle_v1(retrieval_ingress=ingress, retrieval_subqueries=sub)
    assert a == b
