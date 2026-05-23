"""Wave S1 — graph truth dedupe, idempotent ledger, promotion scheduling."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.link_ledger import append_authoritative_org_link
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    PROMOTION_TRIGGER_AFTER_PHASE_04_V1,
    PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1,
    count_promotable_link_candidates_v1,
    evaluate_promotion_backlog_schedule_v1,
)
from vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1 import (
    snapshot_authoritative_link_topology_v1,
)


def test_snapshot_topology_dup_factor_unit() -> None:
    """Dup factor math is consistent when unique pairs are known."""
    auth_edge_rows = 10
    unique_auth_pairs = 2
    dup = round(auth_edge_rows / unique_auth_pairs, 3)
    assert dup == 5.0


@pytest.mark.integration
def test_append_authoritative_org_link_idempotent_same_pair(
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"s1dedupe-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="S1 Dedupe",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    src = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"s1": "a"},
        metadata_json={},
    )
    dst = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"s1": "b"},
        metadata_json={},
    )
    first = append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=src.id,
        target_entity_id=dst.id,
        evidence_raw_record_ids=[1],
    )
    second = append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=src.id,
        target_entity_id=dst.id,
        evidence_raw_record_ids=[2],
    )
    db_session.commit()
    assert first.id == second.id
    topo = snapshot_authoritative_link_topology_v1(db_session, tenant_id=tenant.id)
    assert topo["auth_edge_rows"] == 1
    assert topo["unique_auth_pairs"] == 1
    assert topo["dup_factor"] == 1.0


def _empty_tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"s1sched-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="S1 Schedule",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.mark.integration
def test_evaluate_promotion_after_phase_04_requires_promotable(db_session: Session) -> None:
    tenant = _empty_tenant(db_session)
    out = evaluate_promotion_backlog_schedule_v1(
        db_session,
        tenant_id=tenant.id,
        trigger=PROMOTION_TRIGGER_AFTER_PHASE_04_V1,
    )
    assert out["should_schedule"] is (count_promotable_link_candidates_v1(db_session, tenant_id=tenant.id) > 0)


@pytest.mark.integration
def test_evaluate_promotion_backlog_uses_promotable_not_unpromoted_only(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant = _empty_tenant(db_session)
    monkeypatch.setenv("CORTEX_GRAPH_DENSITY_PROMOTION_BACKLOG_THRESHOLD", "0")
    out = evaluate_promotion_backlog_schedule_v1(
        db_session,
        tenant_id=tenant.id,
        trigger=PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1,
    )
    assert out["should_schedule"] is False
    assert out["schedule_reason"] == "no_promotable_candidates"
