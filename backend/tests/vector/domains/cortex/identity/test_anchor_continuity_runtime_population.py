"""Anchor continuity regen produces candidates + fixture ambiguity (P04 runtime substrate)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_continuity_candidates import (
    ANCHOR_CONTINUITY_RULE_SEMANTIC,
    RULE_EMAIL_NORM_CONTINUITY_EVIDENCE,
    build_anchor_continuity_candidate_rows,
    run_anchor_continuity_candidate_regeneration,
)
from vector.domains.cortex.identity.backfill import run_anchor_handle_backfill
from vector.domains.cortex.identity.identity_primitive_projection import (
    extract_identity_primitives,
    org_entity_id_for_identity_primitive,
)
from vector.domains.cortex.identity.org_ambiguity import list_org_ambiguity_records
from vector.domains.cortex.identity.org_link_replay_runtime import execute_org_link_replay_job
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant_connection import TenantConnection


def _seed_bundle_conn_run(db: Session) -> tuple[uuid.UUID, str, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p04rt-{uuid.uuid4().hex[:8]}@example.com", full_name="P04RT")
    tenant = Tenant(
        company_name="P04RT Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p04rt-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    bundle_id = f"bundle.p04rt.{uuid.uuid4().hex[:8]}"
    db.add(
        CortexMappingBundle(
            bundle_id=bundle_id,
            lifecycle_state="approved",
            manifest_hash="sha256:" + "b" * 64,
            owner_team="cortex-platform",
            title="P04RT bundle",
            notes=None,
        )
    )
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    db.add(conn)
    db.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(tz=UTC),
    )
    db.add(run)
    db.flush()
    return tenant.id, bundle_id, run.id


def _raw_slack(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    external_id: str,
    payload: dict,
) -> int:
    raw = RawIngestionRecord(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector="slack",
        resource_type="slack.message",
        external_id=external_id,
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body=payload,
        payload_hash="ph-" + uuid.uuid4().hex[:16],
        http_status=200,
        fetched_at=datetime.now(tz=UTC),
        run_id=run_id,
        source_trigger="manual_admin",
        idempotency_key="idem-" + external_id,
        source_identity_key=f"slack:slack.message:{external_id}",
        source_revision_key="rev-1",
    )
    db.add(raw)
    db.flush()
    return int(raw.id)


@pytest.fixture()
def tenant_bundle_run(db_session: Session) -> tuple[uuid.UUID, str, uuid.UUID, uuid.UUID]:
    tid, bundle_id, run_id = _seed_bundle_conn_run(db_session)
    conn = db_session.scalars(select(TenantConnection).where(TenantConnection.tenant_id == tid).limit(1)).one()
    return tid, bundle_id, run_id, conn.id


def test_fixture_cluster_emits_candidate_edges(
    db_session: Session, tenant_bundle_run: tuple[uuid.UUID, str, uuid.UUID, uuid.UUID]
) -> None:
    tid, bundle_id, run_id, conn_id = tenant_bundle_run
    cluster = "p04_test_cluster_fixture_only"
    rid1 = _raw_slack(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        run_id=run_id,
        external_id="ext-a",
        payload={
            "channel": "#x",
            "ts": "2025-01-01T00:00:01Z",
            "metadata": {"continuity_fixture": {"cluster_key": cluster}},
        },
    )
    rid2 = _raw_slack(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        run_id=run_id,
        external_id="ext-b",
        payload={
            "channel": "#x",
            "ts": "2025-01-01T00:00:02Z",
            "metadata": {"continuity_fixture": {"cluster_key": cluster}},
        },
    )
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    db_session.add_all(
        [
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=e1,
                tenant_id=tid,
                bundle_id=bundle_id,
                canonical_object_kind="message",
                provider_identity_hash="h-a",
                provider_identity_json={},
                logical_key_hash="lk-a",
                raw_record_id=rid1,
                connector="slack",
                phase04_boundary_json={},
                engine_build_ref="test-anchor",
            ),
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=e2,
                tenant_id=tid,
                bundle_id=bundle_id,
                canonical_object_kind="message",
                provider_identity_hash="h-b",
                provider_identity_json={},
                logical_key_hash="lk-b",
                raw_record_id=rid2,
                connector="slack",
                phase04_boundary_json={},
                engine_build_ref="test-anchor",
            ),
        ]
    )
    db_session.commit()

    out = run_anchor_handle_backfill(db_session, tenant_id=tid, dry_run=False, anchor_limit=100)
    db_session.commit()
    reg = out.get("candidate_regeneration") or {}
    assert int(reg.get("candidate_count") or 0) >= 1
    assert reg.get("anchor_evidence_input_sha256")
    assert len(reg.get("anchor_evidence_input_sha256")) == 64


def test_fixture_ambiguity_cohort_recorded(
    db_session: Session, tenant_bundle_run: tuple[uuid.UUID, str, uuid.UUID, uuid.UUID]
) -> None:
    tid, bundle_id, run_id, conn_id = tenant_bundle_run
    cohort = "p04_test_ambiguity_cohort"
    rid1 = _raw_slack(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        run_id=run_id,
        external_id="amb-1",
        payload={
            "channel": "#y",
            "ts": "2025-02-01T00:00:01Z",
            "metadata": {
                "continuity_fixture": {
                    "ambiguity_cohort_key": cohort,
                    "org_ambiguity_class": "handle_collision_unresolved",
                }
            },
        },
    )
    rid2 = _raw_slack(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        run_id=run_id,
        external_id="amb-2",
        payload={
            "channel": "#y",
            "ts": "2025-02-01T00:00:02Z",
            "metadata": {
                "continuity_fixture": {
                    "ambiguity_cohort_key": cohort,
                    "org_ambiguity_class": "handle_collision_unresolved",
                }
            },
        },
    )
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    db_session.add_all(
        [
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=e1,
                tenant_id=tid,
                bundle_id=bundle_id,
                canonical_object_kind="message",
                provider_identity_hash="ha1",
                provider_identity_json={},
                logical_key_hash="lka1",
                raw_record_id=rid1,
                connector="slack",
                phase04_boundary_json={},
                engine_build_ref="test-anchor",
            ),
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=e2,
                tenant_id=tid,
                bundle_id=bundle_id,
                canonical_object_kind="message",
                provider_identity_hash="ha2",
                provider_identity_json={},
                logical_key_hash="lka2",
                raw_record_id=rid2,
                connector="slack",
                phase04_boundary_json={},
                engine_build_ref="test-anchor",
            ),
        ]
    )
    db_session.commit()
    run_anchor_handle_backfill(db_session, tenant_id=tid, dry_run=False, anchor_limit=100)
    db_session.commit()

    amb = list_org_ambiguity_records(db_session, tenant_id=tid, limit=50, status="open")
    subjects = {r.subject_key for r in amb}
    assert f"fixture_cohort:{cohort}:handle_collision_unresolved" in subjects


def test_replay_job_candidate_regen_uses_anchor_engine(db_session: Session) -> None:
    tid, _, _ = _seed_bundle_conn_run(db_session)
    db_session.commit()
    job = execute_org_link_replay_job(
        db_session,
        tenant_id=tid,
        job_kind="candidate_regen",
        pinned_rule_version=ANCHOR_CONTINUITY_RULE_SEMANTIC,
        dry_run=False,
    )
    db_session.commit()
    assert job.status == "completed"
    assert job.summary_json.get("replay_lane") == "anchor_continuity"
    assert job.summary_json.get("anchor_evidence_input_sha256")


def test_email_norm_continuity_evidence_pairs_distinct_email_display_handles(
    db_session: Session, tenant_bundle_run: tuple[uuid.UUID, str, uuid.UUID, uuid.UUID]
) -> None:
    """Same normalized email across two anchors with different display names → evidence edge, not exact-email triple."""
    tid, bundle_id, run_id, conn_id = tenant_bundle_run
    shared_email = "continuity.shared@nexora.test"
    rid1 = _raw_slack(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        run_id=run_id,
        external_id="email-norm-a",
        payload={
            "channel": "#z",
            "ts": "2025-03-01T00:00:01Z",
            "user_id": "USLACK_A",
            "user_email": shared_email,
            "display_name": "Alex One",
        },
    )
    rid2 = _raw_slack(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        run_id=run_id,
        external_id="email-norm-b",
        payload={
            "channel": "#z",
            "ts": "2025-03-01T00:00:02Z",
            "user_id": "USLACK_B",
            "user_email": shared_email,
            "display_name": "Alex Two",
        },
    )
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    a1 = CortexCanonicalIdentityAnchor(
        canonical_entity_id=e1,
        tenant_id=tid,
        bundle_id=bundle_id,
        canonical_object_kind="message",
        provider_identity_hash="eh1",
        provider_identity_json={},
        logical_key_hash="lkeh1",
        raw_record_id=rid1,
        connector="slack",
        phase04_boundary_json={},
        engine_build_ref="test-anchor",
    )
    a2 = CortexCanonicalIdentityAnchor(
        canonical_entity_id=e2,
        tenant_id=tid,
        bundle_id=bundle_id,
        canonical_object_kind="message",
        provider_identity_hash="eh2",
        provider_identity_json={},
        logical_key_hash="lkeh2",
        raw_record_id=rid2,
        connector="slack",
        phase04_boundary_json={},
        engine_build_ref="test-anchor",
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    r1 = db_session.get(RawIngestionRecord, rid1)
    r2 = db_session.get(RawIngestionRecord, rid2)
    assert r1 is not None and r2 is not None
    ed1 = next(
        org_entity_id_for_identity_primitive(tenant_id=tid, projection=p)
        for p in extract_identity_primitives(anchor=a1, raw=r1)
        if p.projection_kind == "email_display_identity"
    )
    ed2 = next(
        org_entity_id_for_identity_primitive(tenant_id=tid, projection=p)
        for p in extract_identity_primitives(anchor=a2, raw=r2)
        if p.projection_kind == "email_display_identity"
    )
    assert ed1 != ed2

    rows = build_anchor_continuity_candidate_rows(db_session, tenant_id=tid)
    norm_rows = [r for r in rows if r.get("rule_id") == RULE_EMAIL_NORM_CONTINUITY_EVIDENCE]
    assert len(norm_rows) >= 1
    pair = norm_rows[0]
    ends = {pair["source_entity_id"], pair["target_entity_id"]}
    assert ends == {str(ed1), str(ed2)}
    exact_same_pair = [
        r
        for r in rows
        if r.get("rule_id") == "p04.candidate.exact_email_localpart_domain_v1"
        and {r["source_entity_id"], r["target_entity_id"]} == ends
    ]
    assert exact_same_pair == []


def test_email_norm_slack_multiplicity_opens_ambiguity(
    db_session: Session, tenant_bundle_run: tuple[uuid.UUID, str, uuid.UUID, uuid.UUID]
) -> None:
    """Same normalized email with two Slack user ids → informational ambiguity row (no merge)."""
    tid, bundle_id, run_id, conn_id = tenant_bundle_run
    shared = "alex.kim@nexora.dev"
    rid1 = _raw_slack(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        run_id=run_id,
        external_id="slack-norm-amb-a",
        payload={
            "channel": "#z",
            "ts": "2025-04-01T00:00:01Z",
            "user_id": "UALEXKIM99",
            "user_email": shared,
            "display_name": "Alex Kim",
        },
    )
    rid2 = _raw_slack(
        db_session,
        tenant_id=tid,
        connection_id=conn_id,
        run_id=run_id,
        external_id="slack-norm-amb-b",
        payload={
            "channel": "#z",
            "ts": "2025-04-01T00:00:02Z",
            "user_id": "UALEXKIM98",
            "user_email": shared,
            "display_name": "Alex Kim",
        },
    )
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    db_session.add_all(
        [
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=e1,
                tenant_id=tid,
                bundle_id=bundle_id,
                canonical_object_kind="message",
                provider_identity_hash="sk1",
                provider_identity_json={},
                logical_key_hash="lsk1",
                raw_record_id=rid1,
                connector="slack",
                phase04_boundary_json={},
                engine_build_ref="test-anchor",
            ),
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=e2,
                tenant_id=tid,
                bundle_id=bundle_id,
                canonical_object_kind="message",
                provider_identity_hash="sk2",
                provider_identity_json={},
                logical_key_hash="lsk2",
                raw_record_id=rid2,
                connector="slack",
                phase04_boundary_json={},
                engine_build_ref="test-anchor",
            ),
        ]
    )
    db_session.commit()
    run_anchor_handle_backfill(db_session, tenant_id=tid, dry_run=False, anchor_limit=100)
    db_session.commit()
    out = run_anchor_continuity_candidate_regeneration(db_session, tenant_id=tid)
    db_session.commit()
    assert int(out.get("ambiguity_opened_email_norm_slack_multiplicity") or 0) >= 1
    amb = list_org_ambiguity_records(db_session, tenant_id=tid, limit=50, status="open")
    subjects = {r.subject_key for r in amb}
    assert any(s.startswith("email_norm_slack_multiplicity:") for s in subjects)
