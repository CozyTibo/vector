"""P08-10 — PLAN + RETRIEVE orchestration (``synthesis.synthesis_query_plan``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import (
    GP08_RETRIEVE01_GATE_ID_V1,
    PHASE08_SYNTHESIS_QUERY_PLAN_RUNTIME_SCHEMA_VERSION,
    SD_CAP_RETRIEVAL_V1,
    build_synthesis_retrieval_plan_v1,
    execute_synthesis_retrieval_plan_v1,
    merge_retrieval_responses_v1,
    verify_gp08_retrieve01_merge_responses_static,
    verify_gp08_retrieve01_plan_fanout_static,
    verify_gp08_retrieve01_query_envelope_static,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _repo_root_containing_phase08_arch_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-runtime-architecture.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate phase-08-synthesis-runtime-architecture.md from test parents.")


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8plan-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Plan User")
    tenant = Tenant(
        company_name="P8PLAN",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8plan-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_phase08_query_plan_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_QUERY_PLAN_RUNTIME_SCHEMA_VERSION >= 1


def test_execution_understanding_plan_includes_fanout() -> None:
    env = {
        "synthesis_workload_class": "execution_understanding",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {"retrieval_lookup_id": "sha256:" + "a" * 64},
        "synthesis_policy_pack_id": "SynthesisPolicyPackV1_Default",
    }
    plan = build_synthesis_retrieval_plan_v1(env)
    assert len(plan) == 2
    assert plan[1]["retrieval_workload_class"] == "lineage_explorer"


def test_verify_gp08_retrieve01_static_gates_pass() -> None:
    for fn in (
        verify_gp08_retrieve01_plan_fanout_static,
        verify_gp08_retrieve01_merge_responses_static,
        verify_gp08_retrieve01_query_envelope_static,
    ):
        out = fn()
        assert out["id"] == GP08_RETRIEVE01_GATE_ID_V1
        assert out["passed"] is True


def test_doctrine_runtime_architecture_mentions_retrieve() -> None:
    root = _repo_root_containing_phase08_arch_docs()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-runtime-architecture.md").read_text(
        encoding="utf-8",
    )
    assert "build_synthesis_retrieval_plan_v1" in text
    assert "RETRIEVE" in text


@pytest.mark.integration
def test_execute_retrieval_plan_via_phase07(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch="epoch-p08-10",
    )
    db_session.commit()
    envelope = {
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {
            "retrieval_lookup_id": row.retrieval_lookup_id,
            "expected_replay_identity": replay,
        },
        "retrieval_pins": {
            "index_epoch": "epoch-p08-10",
            "tcre_policy_bundle_digest": "sha256:policy-stub",
            "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        },
        "synthesis_policy_pack_id": "SynthesisPolicyPackV1_Default",
    }
    plan = build_synthesis_retrieval_plan_v1(envelope)
    out = execute_synthesis_retrieval_plan_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        plan=plan,
    )
    assert len(out["retrieval_subqueries"]) >= 1
    assert out["retrieval_subqueries"][0][PHASE07_REPLAY_IDENTITY_FIELD_V1]
    assert out["retrieval_ingress_digest"]


@pytest.mark.integration
def test_orchestrator_live_retrieve_persists_subqueries(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch="epoch-p08-10b",
    )
    body = {
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {
            "retrieval_lookup_id": row.retrieval_lookup_id,
            "expected_replay_identity": replay,
        },
        "retrieval_pins": {
            "index_epoch": "epoch-p08-10b",
            "tcre_policy_bundle_digest": "sha256:policy-stub",
            "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        },
    }
    result = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    retrieve_row = next(r for r in result["execution_trace"] if r["phase"] == "RETRIEVE")
    assert retrieve_row["mode"] == "live_retrieval_plan"
    assert len(result["retrieval_subqueries"]) >= 1
    assert result["retrieval_subqueries"][0]["retrieval_query_receipt_digest"]


def test_cap_truncation_emits_sd_cap_retrieval() -> None:
    env = {
        "synthesis_workload_class": "execution_understanding",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "selection_policy": {"max_retrieval_subqueries": 1},
        "synthesis_policy_pack_id": "SynthesisPolicyPackV1_Default",
    }
    plan = build_synthesis_retrieval_plan_v1(env)
    assert len(plan) == 1
    from vector.domains.cortex.synthesis.synthesis_query_plan import list_synthesis_retrieval_plan_cap_violations_v1

    rows = list_synthesis_retrieval_plan_cap_violations_v1(
        env,
        unconstrained_plan_count=2,
    )
    assert rows[0]["sd_code"] == SD_CAP_RETRIEVAL_V1


def test_merge_retrieval_responses_worst_legality() -> None:
    merged = merge_retrieval_responses_v1(
        [
            {"retrieval_legality_class": "retrieval_replay_safe", PHASE07_REPLAY_IDENTITY_FIELD_V1: "a" * 64},
            {"retrieval_legality_class": "retrieval_partial", PHASE07_REPLAY_IDENTITY_FIELD_V1: "b" * 64},
        ],
    )
    assert merged["retrieval_legality_class"] == "retrieval_partial"
