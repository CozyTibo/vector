"""P085-11 — Lawful edge promotion automation (**G-P085-PROMO-01**)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.candidate_generation import regenerate_link_candidates
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.domains.cortex.identity.org_link_replay_runtime import (
    execute_org_link_replay_job,
)
from vector.domains.cortex.operational_runtime.cesp_promotion_gate import (
    verify_gp085_promotion_gate_static,
)
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    CESP_LAWFUL_PROMOTION_POLICY_REF_V1,
    GP085_PROMO01_GATE_ID_V1,
    ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1,
    build_graph_density_promotion_catalog_v1,
    count_unpromoted_link_candidates_v1,
    evaluate_promotion_backlog_schedule_v1,
    run_graph_density_promotion_pass_v1,
    schedule_graph_density_pass_v1,
    verify_gp085_promo01_static,
)


def test_promotion_catalog() -> None:
    cat = build_graph_density_promotion_catalog_v1()
    assert cat["primary_gate_id"] == GP085_PROMO01_GATE_ID_V1
    assert cat["promotion_policy_ref"] == CESP_LAWFUL_PROMOTION_POLICY_REF_V1
    assert cat["org_link_job_kind"] == ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1


def test_verify_gp085_promo01_static_passes() -> None:
    assert verify_gp085_promo01_static()["passed"] is True
    assert verify_gp085_promotion_gate_static()["passed"] is True


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085promo-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Promo Tenant",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _seed_candidate(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
) -> uuid.UUID:
    e1 = upsert_org_entity(
        db_session,
        tenant_id=tenant_id,
        entity_kind="human_actor",
        identity_material={"k": "a"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant_id,
        entity_kind="human_actor",
        identity_material={"k": "b"},
        metadata_json={},
    )
    out = regenerate_link_candidates(
        db_session,
        tenant_id=tenant_id,
        rule_version="p085.promo.test.v1",
        rows=[
            {
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(e1.id),
                "target_entity_id": str(e2.id),
                "evidence_raw_record_ids": [42],
                "rule_id": None,
            }
        ],
    )
    assert out["candidate_set_sha256"]
    return tenant_id


@pytest.mark.integration
def test_run_graph_density_promotion_pass_promotes_with_receipt(
    db_session: Session,
    tenant: Any,
) -> None:
    _seed_candidate(db_session, tenant_id=tenant.id)
    assert count_unpromoted_link_candidates_v1(db_session, tenant_id=tenant.id) == 1

    out = run_graph_density_promotion_pass_v1(db_session, tenant_id=tenant.id)
    db_session.commit()

    assert out["promoted_count"] == 1
    assert out["gate_id"] == GP085_PROMO01_GATE_ID_V1
    assert out["promotion_policy_ref"] == CESP_LAWFUL_PROMOTION_POLICY_REF_V1
    assert out.get("org_link_replay_job_id")
    assert count_unpromoted_link_candidates_v1(db_session, tenant_id=tenant.id) == 0


@pytest.mark.integration
def test_execute_org_link_replay_lawful_edge_promotion_lane(
    db_session: Session,
    tenant: Any,
) -> None:
    _seed_candidate(db_session, tenant_id=tenant.id)
    job = execute_org_link_replay_job(
        db_session,
        tenant_id=tenant.id,
        job_kind="lawful_edge_promotion",
        scope_json={"trigger": "manual"},
    )
    db_session.commit()
    assert job.status == "completed"
    assert int((job.summary_json or {}).get("promoted_count") or 0) == 1


@pytest.mark.integration
def test_evaluate_and_schedule_backlog(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_candidate(db_session, tenant_id=tenant.id)
    monkeypatch.setenv("CORTEX_GRAPH_DENSITY_PROMOTION_BACKLOG_THRESHOLD", "0")

    eval_out = evaluate_promotion_backlog_schedule_v1(db_session, tenant_id=tenant.id)
    assert eval_out["should_schedule"] is True

    sched = schedule_graph_density_pass_v1(
        tenant_id=tenant.id,
        trigger="backlog_threshold",
        force=True,
        session=db_session,
    )
    assert sched["scheduled"] is True
    assert sched["path"] == "inline_execution_slice"
    assert "pass" in sched


@pytest.mark.integration
def test_idempotent_promotion_pass_skips_already_promoted(
    db_session: Session,
    tenant: Any,
) -> None:
    _seed_candidate(db_session, tenant_id=tenant.id)
    first = run_graph_density_promotion_pass_v1(db_session, tenant_id=tenant.id)
    second = run_graph_density_promotion_pass_v1(db_session, tenant_id=tenant.id)
    db_session.commit()
    assert first["promoted_count"] == 1
    assert second["promoted_count"] == 0
