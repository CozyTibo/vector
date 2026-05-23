"""Wave S2 — identity continuity promotion, candidates, anchor boundary."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_continuity_candidates import (
    RULE_GITHUB_LOGIN,
    RULE_NOTION_USER_ID,
    RULE_SLACK_USER_ID,
    build_anchor_continuity_candidate_rows,
)
from vector.domains.cortex.identity.candidate_generation import regenerate_link_candidates
from vector.domains.cortex.identity.identity_continuity_candidates_v1 import (
    candidate_endpoint_pair_key_v1,
    max_candidate_edges_for_rule_v1,
)
from vector.domains.cortex.identity.identity_continuity_promotion_v1 import (
    list_promotable_link_candidates_fair_by_rule_v1,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.domains.cortex.identity.identity_anchor_boundary_v1 import (
    repair_anchor_org_entity_boundary_v1,
    snapshot_anchor_entity_boundary_v1,
)
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate


def test_prod_rule_caps_prefer_github_slack_notion() -> None:
    assert max_candidate_edges_for_rule_v1(RULE_GITHUB_LOGIN) >= max_candidate_edges_for_rule_v1(
        "p04.candidate.continuity_fixture_cluster_key_v1"
    )


def test_candidate_endpoint_pair_dedupe_key_symmetric() -> None:
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    k1 = candidate_endpoint_pair_key_v1(
        source_entity_id=e1, target_entity_id=e2, link_type="org.persona_belongs_to_handle"
    )
    k2 = candidate_endpoint_pair_key_v1(
        source_entity_id=e2, target_entity_id=e1, link_type="org.persona_belongs_to_handle"
    )
    assert k1 == k2


@pytest.mark.integration
def test_build_anchor_continuity_respects_per_rule_cap(
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"s2cap-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="S2 Cap",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    entities = []
    for i in range(40):
        entities.append(
            upsert_org_entity(
                db_session,
                tenant_id=tenant.id,
                entity_kind="human_actor",
                identity_material={"cap": i},
                metadata_json={},
            )
        )
    db_session.flush()
    rows = []
    for i in range(len(entities) - 1):
        rows.append(
            {
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(entities[i].id),
                "target_entity_id": str(entities[i + 1].id),
                "evidence_raw_record_ids": [100 + i],
                "rule_id": RULE_SLACK_USER_ID,
            }
        )
    regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="s2.cap.test.v1",
        rows=rows,
    )
    db_session.commit()
    accounting: dict = {}
    built = build_anchor_continuity_candidate_rows(
        db_session,
        tenant_id=tenant.id,
        accounting_out=accounting,
    )
    per_rule = dict(accounting.get("per_rule") or {})
    slack_metrics = per_rule.get(RULE_SLACK_USER_ID) or {}
    assert int(slack_metrics.get("edges_emitted") or 0) <= max_candidate_edges_for_rule_v1(RULE_SLACK_USER_ID)
    assert len(built) <= int(accounting.get("global_max_candidate_edges") or 2000)


@pytest.mark.integration
def test_fair_promotion_round_robin_by_rule(
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"s2fair-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="S2 Fair",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    e1 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"a": 1},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"b": 2},
        metadata_json={},
    )
    for rule_id in (RULE_SLACK_USER_ID, RULE_GITHUB_LOGIN, RULE_NOTION_USER_ID):
        regenerate_link_candidates(
            db_session,
            tenant_id=tenant.id,
            rule_version=f"s2.fair.{rule_id}.v1",
            rows=[
                {
                    "link_type": "org.persona_belongs_to_handle",
                    "source_entity_id": str(e1.id),
                    "target_entity_id": str(e2.id),
                    "evidence_raw_record_ids": [1],
                    "rule_id": rule_id,
                }
            ],
        )
    db_session.commit()
    picked = list_promotable_link_candidates_fair_by_rule_v1(
        db_session,
        tenant_id=tenant.id,
        limit=3,
    )
    rules = {c.rule_id for c in picked}
    assert len(picked) == 3
    assert RULE_SLACK_USER_ID in rules
    assert RULE_GITHUB_LOGIN in rules
    assert RULE_NOTION_USER_ID in rules


@pytest.mark.integration
def test_anchor_boundary_repair_writes_canonical_entity_id(
    db_session: Session,
) -> None:
    from tests.vector.domains.cortex.identity.test_phase04_step20_anchor_backfill import (
        _seed_tenant_bundle_raw,
    )
    from vector.infrastructure.db.models.cortex_canonical_identity_anchor import (
        CortexCanonicalIdentityAnchor,
    )

    tid, bundle_id, raw_id, eid = _seed_tenant_bundle_raw(db_session)
    anchor = CortexCanonicalIdentityAnchor(
        canonical_entity_id=eid,
        tenant_id=tid,
        bundle_id=bundle_id,
        canonical_object_kind="person",
        provider_identity_hash="sha256:" + "a" * 64,
        provider_identity_json={"login": "s2boundary"},
        logical_key_hash="lk-s2-boundary",
        raw_record_id=raw_id,
        connector="github",
        phase04_boundary_json={},
        engine_build_ref="test-s2-boundary",
    )
    db_session.add(anchor)
    db_session.commit()
    tenant_id = tid
    before = snapshot_anchor_entity_boundary_v1(db_session, tenant_id=tenant_id)
    assert int(before["anchors_missing_org_entity"]) >= 1
    out = repair_anchor_org_entity_boundary_v1(db_session, tenant_id=tenant_id, limit=100)
    db_session.commit()
    after = snapshot_anchor_entity_boundary_v1(db_session, tenant_id=tenant_id)
    assert int(out["entities_touched"]) >= 1
    assert int(after["anchors_missing_org_entity"]) < int(before["anchors_missing_org_entity"])
