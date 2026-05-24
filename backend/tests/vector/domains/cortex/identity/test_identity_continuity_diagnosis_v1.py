"""Phase S1.1 — identity continuity diagnosis harness tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.identity.anchor_continuity_candidates import (
    RULE_EMAIL_NORM_CONTINUITY_EVIDENCE,
    collect_anchor_continuity_rule_buckets_v1,
    summarize_rule_bucket_maps_v1,
)
from vector.domains.cortex.identity.identity_continuity_diagnosis_v1 import (
    build_identity_continuity_diagnosis_v1,
)
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"diag-{uuid.uuid4().hex[:10]}@example.com", full_name="Diag")
    tenant = Tenant(
        company_name="Diag Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"diag-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_summarize_rule_bucket_maps_counts_cross_entity_buckets() -> None:
    e1, e2 = uuid.uuid4(), uuid.uuid4()
    fake_anchor = object()
    bmap = {
        "shared@example.com": [(e1, 1, fake_anchor), (e2, 2, fake_anchor)],
        "solo@example.com": [(e1, 3, fake_anchor)],
    }
    stats = summarize_rule_bucket_maps_v1(((RULE_EMAIL_NORM_CONTINUITY_EVIDENCE, bmap),))
    email_stats = stats["per_rule"][RULE_EMAIL_NORM_CONTINUITY_EVIDENCE]
    assert email_stats["total_buckets"] == 2
    assert email_stats["buckets_with_ge2_distinct_org_entities"] == 1
    assert email_stats["singleton_buckets"] == 1
    assert email_stats["eligible_cross_entity_pairs"] == 1
    assert stats["by_connector"]["email"]["eligible_cross_entity_pairs"] == 1


@pytest.mark.integration
def test_build_identity_continuity_diagnosis_email_bridge_buckets(
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    bundle_id = "diag-bundle"
    shared_email = "shared.bridge@nexora.dev"
    raw1 = RawIngestionRecord(
        tenant_id=tid,
        connection_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        external_id="diag-a",
        resource_type="slack.message",
        payload_body={
            "user_id": "USLACK_A",
            "user_email": shared_email,
            "display_name": "Alex One",
        },
    )
    raw2 = RawIngestionRecord(
        tenant_id=tid,
        connection_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        external_id="diag-b",
        resource_type="slack.message",
        payload_body={
            "user_id": "USLACK_B",
            "user_email": shared_email,
            "display_name": "Alex Two",
        },
    )
    db_session.add_all([raw1, raw2])
    db_session.flush()
    a1 = CortexCanonicalIdentityAnchor(
        canonical_entity_id=uuid.uuid4(),
        tenant_id=tid,
        bundle_id=bundle_id,
        canonical_object_kind="message",
        provider_identity_hash="dh1",
        provider_identity_json={},
        logical_key_hash="lkh1",
        raw_record_id=int(raw1.id),
        connector="slack",
        phase04_boundary_json={},
        engine_build_ref="test-diagnosis",
    )
    a2 = CortexCanonicalIdentityAnchor(
        canonical_entity_id=uuid.uuid4(),
        tenant_id=tid,
        bundle_id=bundle_id,
        canonical_object_kind="message",
        provider_identity_hash="dh2",
        provider_identity_json={},
        logical_key_hash="lkh2",
        raw_record_id=int(raw2.id),
        connector="slack",
        phase04_boundary_json={},
        engine_build_ref="test-diagnosis",
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    rule_phases, anchors, _raw_by_id = collect_anchor_continuity_rule_buckets_v1(db_session, tenant_id=tid)
    assert len(anchors) == 2
    diagnosis = build_identity_continuity_diagnosis_v1(db_session, tenant_id=tid)
    assert diagnosis["surface_kind"] == "identity_continuity_diagnosis"
    assert diagnosis["anchor_count"] == 2
    assert "slack" in diagnosis["anchor_samples_by_connector"]
    assert len(diagnosis["anchor_samples_by_connector"]["slack"]) <= 10
    sample = diagnosis["anchor_samples_by_connector"]["slack"][0]
    assert "continuity_identity_signals" in sample
    email_rule = diagnosis["bucket_diagnosis"]["per_rule"][RULE_EMAIL_NORM_CONTINUITY_EVIDENCE]
    assert email_rule["buckets_with_ge2_distinct_org_entities"] >= 1
    assert email_rule["eligible_cross_entity_pairs"] >= 1


@pytest.mark.integration
def test_identity_continuity_diagnosis_api(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/pipeline/identity-continuity-diagnosis")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "identity_continuity_diagnosis"
    assert "bucket_diagnosis" in body
    assert "receipt_links" in body
