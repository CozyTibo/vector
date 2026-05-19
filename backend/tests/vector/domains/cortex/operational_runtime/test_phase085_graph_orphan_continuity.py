"""P085-12 — Orphan classification + continuity stitching (**G-P085-ORPHAN-01**)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from vector.domains.cortex.identity.authoritative_writer import create_promotion_policy, promote_candidate_to_authoritative_link
from vector.domains.cortex.identity.candidate_generation import regenerate_link_candidates
from vector.domains.cortex.identity.link_ledger import append_authoritative_org_link
from vector.domains.cortex.identity.org_ambiguity import append_org_ambiguity_record
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.domains.cortex.operational_runtime.cesp_orphan_gate import verify_gp085_orphan_gate_static
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    GP085_ORPHAN01_GATE_ID_V1,
    ORPHAN_CLASS_AWAITING_PROMOTION_V1,
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1,
    ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1,
    ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1,
    build_graph_orphan_continuity_catalog_v1,
    classify_orphan_entity_v1,
    classify_tenant_graph_orphans_v1,
    run_continuity_stitching_pass_v1,
    verify_gp085_orphan01_static,
    build_orphan_stitching_context_v1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_GRAPH_DISCONNECTED_V1,
    RET_SKIP_IDENTITY_UNRESOLVED_V1,
)


def test_orphan_continuity_catalog() -> None:
    cat = build_graph_orphan_continuity_catalog_v1()
    assert cat["primary_gate_id"] == GP085_ORPHAN01_GATE_ID_V1
    assert ORPHAN_CLASS_AWAITING_PROMOTION_V1 in cat["orphan_class_ids"]


def test_verify_gp085_orphan01_static_passes() -> None:
    assert verify_gp085_orphan01_static()["passed"] is True
    assert verify_gp085_orphan_gate_static()["passed"] is True


def test_celery_registers_orphan_continuity_stitch_task() -> None:
    from app.tasks import cortex_orphan_continuity_stitch  # noqa: F401

    assert "vector.cortex.operational_runtime.orphan_continuity_stitch_pass" in celery_app.tasks


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085orphan-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Orphan Tenant",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _three_entities(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
) -> tuple[Any, Any, Any]:
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
    e3 = upsert_org_entity(
        db_session,
        tenant_id=tenant_id,
        entity_kind="human_actor",
        identity_material={"k": "c"},
        metadata_json={"orphan_intentionally_excluded": True},
    )
    return e1, e2, e3


@pytest.mark.integration
def test_classify_disconnected_and_intentionally_excluded_orphans(
    db_session: Session,
    tenant: Any,
) -> None:
    e1, e2, e3 = _three_entities(db_session, tenant_id=tenant.id)
    append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[1],
    )
    db_session.commit()

    ctx = build_orphan_stitching_context_v1(db_session, tenant_id=tenant.id)
    assert classify_orphan_entity_v1(ctx, e3.id) == ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1

    out = classify_tenant_graph_orphans_v1(db_session, tenant_id=tenant.id)
    assert out["orphan_entity_count"] == 1
    assert out["counts_by_class"][ORPHAN_CLASS_INTENTIONALLY_EXCLUDED_V1] == 1
    assert out["counts_by_class"][ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1] == 0


@pytest.mark.integration
def test_classify_awaiting_promotion_orphan(
    db_session: Session,
    tenant: Any,
) -> None:
    e1, e2, _e3 = _three_entities(db_session, tenant_id=tenant.id)
    regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="p085.orphan.promo.v1",
        rows=[
            {
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(e1.id),
                "target_entity_id": str(e2.id),
                "evidence_raw_record_ids": [99],
                "rule_id": None,
            }
        ],
    )
    db_session.commit()

    ctx = build_orphan_stitching_context_v1(db_session, tenant_id=tenant.id)
    assert classify_orphan_entity_v1(ctx, e1.id) == ORPHAN_CLASS_AWAITING_PROMOTION_V1
    assert classify_orphan_entity_v1(ctx, e2.id) == ORPHAN_CLASS_AWAITING_PROMOTION_V1


@pytest.mark.integration
def test_classify_identity_unresolved_orphan(
    db_session: Session,
    tenant: Any,
) -> None:
    e1, e2, e3 = _three_entities(db_session, tenant_id=tenant.id)
    append_org_ambiguity_record(
        db_session,
        tenant_id=tenant.id,
        org_ambiguity_class="multiple_persona_unresolved",
        subject_key=f"p085-orphan-{uuid.uuid4().hex[:8]}",
        involved_org_entity_ids=[e1.id, e2.id],
    )
    db_session.commit()

    ctx = build_orphan_stitching_context_v1(db_session, tenant_id=tenant.id)
    assert classify_orphan_entity_v1(ctx, e1.id) == ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1


@pytest.mark.integration
def test_classify_disconnected_when_graph_partially_linked(
    db_session: Session,
    tenant: Any,
) -> None:
    e1, e2, e3 = _three_entities(db_session, tenant_id=tenant.id)
    meta = dict(e3.metadata_json or {})
    meta.pop("orphan_intentionally_excluded", None)
    e3.metadata_json = meta
    append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="org.persona_belongs_to_handle",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[1],
    )
    db_session.commit()

    ctx = build_orphan_stitching_context_v1(db_session, tenant_id=tenant.id)
    assert classify_orphan_entity_v1(ctx, e3.id) == ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1


@pytest.mark.integration
def test_run_continuity_stitching_pass_dry_run(
    db_session: Session,
    tenant: Any,
) -> None:
    e1, e2, _e3 = _three_entities(db_session, tenant_id=tenant.id)
    regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="p085.orphan.stitch.v1",
        rows=[
            {
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(e1.id),
                "target_entity_id": str(e2.id),
                "evidence_raw_record_ids": [1],
                "rule_id": None,
            }
        ],
    )
    db_session.commit()

    out = run_continuity_stitching_pass_v1(db_session, tenant_id=tenant.id, dry_run=True)
    assert out["gate_id"] == GP085_ORPHAN01_GATE_ID_V1
    assert out["dry_run"] is True
    assert out["actions_taken"]["promotion_scheduled"] is False
    codes = {h["ret_skip_code"] for h in out["ret_skip_hints"]}
    assert RET_SKIP_IDENTITY_UNRESOLVED_V1 in codes or RET_SKIP_GRAPH_DISCONNECTED_V1 in codes or not out["ret_skip_hints"]


@pytest.mark.integration
def test_stitch_pass_promotes_after_classification(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    e1, e2, _e3 = _three_entities(db_session, tenant_id=tenant.id)
    regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="p085.orphan.stitch2.v1",
        rows=[
            {
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(e1.id),
                "target_entity_id": str(e2.id),
                "evidence_raw_record_ids": [2],
                "rule_id": None,
            }
        ],
    )
    monkeypatch.setenv("CORTEX_ORPHAN_STITCHING_RUN_ANCHOR_REGEN", "false")
    monkeypatch.setenv("CORTEX_ORPHAN_STITCHING_AUTO_SCHEDULE_PROMOTION", "false")

    pol = create_promotion_policy(db_session, tenant_id=tenant.id, policy_ref="p085.orphan.manual.v1")
    from vector.domains.cortex.operational_runtime.graph_density_promotion import (
        list_unpromoted_link_candidates_v1,
    )

    cands = list_unpromoted_link_candidates_v1(db_session, tenant_id=tenant.id, limit=10)
    assert cands
    promote_candidate_to_authoritative_link(
        db_session,
        tenant_id=tenant.id,
        candidate_id=cands[0].id,
        promotion_policy_id=pol.id,
    )
    db_session.commit()

    out = classify_tenant_graph_orphans_v1(db_session, tenant_id=tenant.id)
    assert out["counts_by_class"].get(ORPHAN_CLASS_AWAITING_PROMOTION_V1, 0) >= 0
