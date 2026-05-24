"""Evidence-scoped Slack/GitHub fingerprint unlocks cross-entity candidate buckets."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_continuity_candidates import (
    RULE_GITHUB_LOGIN,
    RULE_SLACK_USER_ID,
    summarize_rule_bucket_maps_v1,
    collect_anchor_continuity_rule_buckets_v1,
)
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_evidence_scoped_slack_user_forms_cross_entity_bucket(db_session: Session) -> None:
    slug = f"s1f2-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="S1 F2",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    tid = tenant.id
    shared_uid = "USHARED01"
    raw1 = RawIngestionRecord(
        tenant_id=tid,
        connection_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        external_id="slack-fp-a",
        resource_type="slack.message",
        payload_body={"user_id": shared_uid, "display_name": "Pat"},
    )
    raw2 = RawIngestionRecord(
        tenant_id=tid,
        connection_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        external_id="slack-fp-b",
        resource_type="slack.message",
        payload_body={"user_id": shared_uid, "display_name": "Pat"},
    )
    db_session.add_all([raw1, raw2])
    db_session.flush()
    db_session.add_all(
        [
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=uuid.uuid4(),
                tenant_id=tid,
                bundle_id="fp-bundle",
                canonical_object_kind="message",
                provider_identity_hash="fp1",
                provider_identity_json={},
                logical_key_hash="lk1",
                raw_record_id=int(raw1.id),
                connector="slack",
                phase04_boundary_json={},
                engine_build_ref="test-s1.2",
            ),
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=uuid.uuid4(),
                tenant_id=tid,
                bundle_id="fp-bundle",
                canonical_object_kind="message",
                provider_identity_hash="fp2",
                provider_identity_json={},
                logical_key_hash="lk2",
                raw_record_id=int(raw2.id),
                connector="slack",
                phase04_boundary_json={},
                engine_build_ref="test-s1.2",
            ),
        ]
    )
    db_session.commit()

    rule_phases, _, _ = collect_anchor_continuity_rule_buckets_v1(db_session, tenant_id=tid)
    stats = summarize_rule_bucket_maps_v1(rule_phases)
    slack = stats["per_rule"][RULE_SLACK_USER_ID]
    assert slack["buckets_with_ge2_distinct_org_entities"] >= 1
    assert slack["eligible_cross_entity_pairs"] >= 1


@pytest.mark.integration
def test_evidence_scoped_github_login_forms_cross_entity_bucket(db_session: Session) -> None:
    slug = f"s1f2gh-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="S1 F2 GH",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    tid = tenant.id
    login = "sameauthor"
    raw1 = RawIngestionRecord(
        tenant_id=tid,
        connection_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        external_id="gh-fp-a",
        resource_type="github.pull_request",
        payload_body={"pull_request": {"user": {"login": login}}},
    )
    raw2 = RawIngestionRecord(
        tenant_id=tid,
        connection_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        external_id="gh-fp-b",
        resource_type="github.pull_request",
        payload_body={"pull_request": {"user": {"login": login}}},
    )
    db_session.add_all([raw1, raw2])
    db_session.flush()
    db_session.add_all(
        [
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=uuid.uuid4(),
                tenant_id=tid,
                bundle_id="fp-bundle",
                canonical_object_kind="pull_request",
                provider_identity_hash="gh1",
                provider_identity_json={},
                logical_key_hash="lkgh1",
                raw_record_id=int(raw1.id),
                connector="github",
                phase04_boundary_json={},
                engine_build_ref="test-s1.2",
            ),
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=uuid.uuid4(),
                tenant_id=tid,
                bundle_id="fp-bundle",
                canonical_object_kind="pull_request",
                provider_identity_hash="gh2",
                provider_identity_json={},
                logical_key_hash="lkgh2",
                raw_record_id=int(raw2.id),
                connector="github",
                phase04_boundary_json={},
                engine_build_ref="test-s1.2",
            ),
        ]
    )
    db_session.commit()

    rule_phases, _, _ = collect_anchor_continuity_rule_buckets_v1(db_session, tenant_id=tid)
    stats = summarize_rule_bucket_maps_v1(rule_phases)
    gh = stats["per_rule"][RULE_GITHUB_LOGIN]
    assert gh["buckets_with_ge2_distinct_org_entities"] >= 1
    assert gh["eligible_cross_entity_pairs"] >= 1
