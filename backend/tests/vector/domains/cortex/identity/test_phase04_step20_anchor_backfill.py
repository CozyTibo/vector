"""P04-20 — canonical anchor → org handle backfill + G-P04-BF-01 + admin HTTP."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from sqlalchemy import func, or_, select

from vector.domains.cortex.identity.anchor_projection import ANCHOR_BACKFILL_LANE
from vector.domains.cortex.identity.backfill import (
    ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
    compute_anchor_backfill_set_sha256,
    run_anchor_handle_backfill,
    verify_gp04_bf01_no_authoritative_links_on_backfill_handles,
)
from vector.domains.cortex.identity.identity_primitive_projection import IDENTITY_PRIMITIVE_LANE
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant_connection import TenantConnection


def _seed_tenant_bundle_raw(
    db: Session, *, payload_body: dict[str, Any] | None = None
) -> tuple[uuid.UUID, str, int, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p420-{uuid.uuid4().hex[:8]}@example.com", full_name="P420")
    tenant = Tenant(
        company_name="P420 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p420-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    bundle_id = f"bundle.p420.anchor.{uuid.uuid4().hex[:8]}"
    db.add(
        CortexMappingBundle(
            bundle_id=bundle_id,
            lifecycle_state="approved",
            manifest_hash="sha256:" + "a" * 64,
            owner_team="cortex-platform",
            title="P420 anchor bundle",
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
    raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        resource_type="slack.message",
        external_id=f"msg-{uuid.uuid4().hex[:8]}",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body=payload_body
        if payload_body is not None
        else {"text": "x", "user_id": "UBACKFILL01", "channel": "C1", "ts": "1.0"},
        payload_hash="hash-" + uuid.uuid4().hex[:16],
        http_status=200,
        fetched_at=datetime.now(tz=UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-" + uuid.uuid4().hex[:12],
        source_identity_key="slack:slack.message:test",
        source_revision_key="rev-1",
    )
    db.add(raw)
    db.flush()
    return tenant.id, bundle_id, int(raw.id), uuid.uuid4()


def _count_active_backfill_lane_org_entities(db: Session, tenant_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.tombstoned_at.is_(None),
                or_(
                    CortexOrgEntity.metadata_json["anchor_backfill_lane"].astext == ANCHOR_BACKFILL_LANE,
                    CortexOrgEntity.metadata_json["anchor_backfill_lane"].astext == IDENTITY_PRIMITIVE_LANE,
                ),
            )
        )
        or 0
    )


def test_compute_anchor_backfill_set_sha256_stable(db_session: Session) -> None:
    tid, bundle_id, raw_id, eid = _seed_tenant_bundle_raw(db_session)
    a1 = CortexCanonicalIdentityAnchor(
        canonical_entity_id=eid,
        tenant_id=tid,
        bundle_id=bundle_id,
        canonical_object_kind="person",
        provider_identity_hash="h1",
        provider_identity_json={"k": 1},
        logical_key_hash="lk1",
        raw_record_id=raw_id,
        connector="slack",
        phase04_boundary_json={},
        engine_build_ref="test-anchor",
    )
    db_session.add(a1)
    db_session.commit()
    anchors = [a1]
    assert len(compute_anchor_backfill_set_sha256(anchors)) == 64
    assert compute_anchor_backfill_set_sha256(anchors) == compute_anchor_backfill_set_sha256(list(reversed(anchors)))


def test_backfill_then_bf01_gate(db_session: Session) -> None:
    tid, bundle_id, raw_id, eid = _seed_tenant_bundle_raw(db_session)
    a1 = CortexCanonicalIdentityAnchor(
        canonical_entity_id=eid,
        tenant_id=tid,
        bundle_id=bundle_id,
        canonical_object_kind="person",
        provider_identity_hash="h1",
        provider_identity_json={"k": 1},
        logical_key_hash="lk1",
        raw_record_id=raw_id,
        connector="slack",
        phase04_boundary_json={},
        engine_build_ref="test-anchor",
    )
    db_session.add(a1)
    db_session.commit()

    out = run_anchor_handle_backfill(db_session, tenant_id=tid, dry_run=False, anchor_limit=100)
    db_session.commit()
    assert out["anchors_scanned"] == 1
    assert out["entities_upserted"] == 1
    assert out["run_id"]

    g = verify_gp04_bf01_no_authoritative_links_on_backfill_handles(db_session, tenant_id=tid)
    assert g["passed"] is True
    assert g["id"] == "G-P04-BF-01"

    full = run_canonical_verification(db_session, tenant_id=tid, persist=False)
    bf = next(x for x in full["gates"] if x["id"] == "G-P04-BF-01")
    assert bf["passed"] is True
    eco = next(x for x in full["gates"] if x["id"] == "G-P04-ECO-01")
    assert eco["severity"] == "warn_only"
    assert eco["passed"] is True


def test_backfill_skips_work_object_without_primitives_or_fixture(db_session: Session) -> None:
    tid, bundle_id, raw_id, eid = _seed_tenant_bundle_raw(
        db_session,
        payload_body={"text": "only", "channel": "C1", "ts": "1.0"},
    )
    db_session.add(
        CortexCanonicalIdentityAnchor(
            canonical_entity_id=eid,
            tenant_id=tid,
            bundle_id=bundle_id,
            canonical_object_kind="message",
            provider_identity_hash="h-skip",
            provider_identity_json={},
            logical_key_hash="lk-skip",
            raw_record_id=raw_id,
            connector="slack",
            phase04_boundary_json={},
            engine_build_ref="test-anchor",
        )
    )
    db_session.commit()
    out = run_anchor_handle_backfill(db_session, tenant_id=tid, dry_run=False, anchor_limit=100)
    db_session.commit()
    assert out["entities_upserted"] == 0
    assert out["anchors_skipped_work_object_no_primitive"] == 1


def test_backfill_tombstones_legacy_lane_when_primitive_materializes(db_session: Session) -> None:
    tid, bundle_id, raw_id, eid = _seed_tenant_bundle_raw(
        db_session,
        payload_body={"text": "only", "channel": "C1", "ts": "1.0"},
    )
    db_session.add(
        CortexCanonicalIdentityAnchor(
            canonical_entity_id=eid,
            tenant_id=tid,
            bundle_id=bundle_id,
            canonical_object_kind="person",
            provider_identity_hash="h-tomb",
            provider_identity_json={},
            logical_key_hash="lk-tomb",
            raw_record_id=raw_id,
            connector="slack",
            phase04_boundary_json={},
            engine_build_ref="test-anchor",
        )
    )
    db_session.commit()

    out1 = run_anchor_handle_backfill(db_session, tenant_id=tid, dry_run=False, anchor_limit=100)
    db_session.commit()
    assert out1["legacy_lane_org_entities_tombstoned"] == 0
    assert out1["entities_upserted"] == 1
    assert _count_active_backfill_lane_org_entities(db_session, tid) == 1

    raw = db_session.get(RawIngestionRecord, raw_id)
    assert raw is not None
    raw.payload_body = {**dict(raw.payload_body or {}), "user_id": "UBACKFILL02"}
    db_session.add(raw)
    db_session.commit()

    out2 = run_anchor_handle_backfill(db_session, tenant_id=tid, dry_run=False, anchor_limit=100)
    db_session.commit()
    assert out2["legacy_lane_org_entities_tombstoned"] == 1
    assert out2["entities_upserted"] == 1
    assert _count_active_backfill_lane_org_entities(db_session, tid) == 1

    legacy_tombed = int(
        db_session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tid,
                CortexOrgEntity.tombstoned_at.isnot(None),
                CortexOrgEntity.metadata_json["anchor_backfill_lane"].astext == ANCHOR_BACKFILL_LANE,
            )
        )
        or 0
    )
    assert legacy_tombed == 1


@pytest.mark.integration
def test_admin_backfill_routes(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, bundle_id, raw_id, eid = _seed_tenant_bundle_raw(db_session)
    db_session.add(
        CortexCanonicalIdentityAnchor(
            canonical_entity_id=eid,
            tenant_id=tid,
            bundle_id=bundle_id,
            canonical_object_kind="person",
            provider_identity_hash="h-admin",
            provider_identity_json={},
            logical_key_hash="lk-ad",
            raw_record_id=raw_id,
            connector="slack",
            phase04_boundary_json={},
            engine_build_ref="test-anchor",
        )
    )
    db_session.commit()

    post = client.post(
        f"/admin/tenants/{tid}/cortex/debug/identity/backfill/from-canonical-anchors",
        auth=("admin", "integration-admin-password"),
        json={"dry_run": True, "anchor_limit": 50},
    )
    assert post.status_code == 200
    body = post.json()
    assert body["org_identity_backfill_schema_version"] == ORG_IDENTITY_BACKFILL_SCHEMA_VERSION
    assert body["anchors_scanned"] == 1

    post2 = client.post(
        f"/admin/tenants/{tid}/cortex/debug/identity/backfill/from-canonical-anchors",
        auth=("admin", "integration-admin-password"),
        json={"dry_run": False, "anchor_limit": 50},
    )
    assert post2.status_code == 200

    lst = client.get(
        f"/admin/tenants/{tid}/cortex/identity/backfill/runs",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    data = lst.json()
    assert data["runs"]
    assert data["runs"][0]["anchors_scanned"] == 1

    ent = client.get(f"/admin/tenants/{tid}/cortex/identity/entities", auth=("admin", "integration-admin-password"))
    assert ent.status_code == 200
    rows = ent.json()["entities"]
    assert rows
    assert any(r.get("metadata_json", {}).get("anchor_backfill_lane") == IDENTITY_PRIMITIVE_LANE for r in rows)
