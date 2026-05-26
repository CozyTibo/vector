"""Operator people directory routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.identity.continuity_rebuild import (
    REBUILD_IDENTITIES_CONFIRM_PHRASE,
    enqueue_rebuild_identities_from_anchors_v1,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration

ADMIN_AUTH = ("admin", "integration-admin-password")


@pytest.fixture(autouse=True)
def _admin_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"people-{uuid.uuid4().hex[:10]}@example.com", full_name="People Test")
    tenant = Tenant(
        company_name="People Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"people-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _seed_connection_and_run(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    connector: str = "slack",
) -> tuple[uuid.UUID, uuid.UUID]:
    user = db_session.scalars(
        select(User).join(TenantMembership).where(TenantMembership.tenant_id == tenant_id)
    ).first()
    conn = TenantConnection(
        tenant_id=tenant_id,
        provider=connector,
        status="active",
        connected_by_user_id=user.id if user else uuid.uuid4(),
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        connection_id=conn.id,
        connector=connector,
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(tz=UTC),
    )
    db_session.add(run)
    db_session.flush()
    return conn.id, run.id


def _raw_row(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    resource_type: str,
    external_id: str,
    payload_body: dict,
    connector: str = "slack",
) -> RawIngestionRecord:
    conn_id, run_id = _seed_connection_and_run(db_session, tenant_id=tenant_id, connector=connector)
    row = RawIngestionRecord(
        tenant_id=tenant_id,
        connection_id=conn_id,
        connector=connector,
        resource_type=resource_type,
        external_id=external_id,
        api_endpoint="https://example.com/api",
        query_params={},
        payload_body=payload_body,
        payload_hash=f"ph-{uuid.uuid4().hex[:12]}",
        http_status=200,
        fetched_at=datetime.now(tz=UTC),
        run_id=run_id,
        source_trigger="manual_admin",
        idempotency_key=f"idem-{external_id}-{uuid.uuid4().hex[:6]}",
        source_identity_key=f"{connector}:{resource_type}:{external_id}",
        source_revision_key="rev-1",
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_operator_people_directory_empty(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people", auth=ADMIN_AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_people_directory_v1"
    assert body["people"] == []
    assert body["total"] == 0


def test_operator_people_directory_unions_same_email_without_link(
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity

    tid = _tenant(db_session)
    shared_email = "maximilien@fizzer.com"
    entities = [
        CortexOrgEntity(
            id=uuid.uuid4(),
            tenant_id=tid,
            entity_kind="human_actor",
            lifecycle_state="active",
            identity_key_fingerprint=f"{i}" * 64,
            metadata_json={
                "projection_kind": "email_identity" if i == 0 else "github_user",
                "email_norm": shared_email,
                "display_name": "Maximilien",
            },
            engine_build_ref="test",
        )
        for i in range(3)
    ]
    db_session.add_all(entities)
    db_session.commit()

    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people", auth=ADMIN_AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["people"][0]["display_name"] == "Maximilien"
    assert body["people"][0]["email"] == shared_email
    assert body["people"][0]["linked_account_count"] == 3
    assert body["people"][0]["cluster_size"] == 3
    assert body["people"][0]["connector_id_count"] >= 1
    assert body["people"][0]["is_singleton_cluster"] is False


def test_operator_people_directory_with_auth_graph_link(
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
    from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink

    tid = _tenant(db_session)
    e1 = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tid,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="a" * 64,
        metadata_json={"projection_kind": "github_user", "github_login": "octocat"},
        engine_build_ref="test",
    )
    e2 = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tid,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="b" * 64,
        metadata_json={"projection_kind": "slack_user", "slack_user_id": "U123"},
        engine_build_ref="test",
    )
    link = CortexOrgLink(
        id=uuid.uuid4(),
        tenant_id=tid,
        link_type="org.test_link",
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        evidence_raw_record_ids=[1],
        rule_id=None,
        confidence_class="test",
        link_authority="authoritative",
        link_class="authoritative",
        metadata_json={},
        engine_build_ref="test",
    )
    db_session.add_all([e1, e2, link])
    db_session.commit()

    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people", auth=ADMIN_AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert len(body["people"]) == 1
    person = body["people"][0]
    assert person["in_auth_graph"] is True
    assert person["linked_account_count"] == 2


def test_operator_person_profile_not_found(client: TestClient, db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    missing = uuid.uuid4()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people/{missing}", auth=ADMIN_AUTH)
    assert res.status_code == 404
    assert res.json()["detail"] == "person_not_found"


def test_operator_people_directory_labels_notion_user_without_email(
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity

    tid = _tenant(db_session)
    notion_id = "abc12345-6789-0000-0000-000000000001"
    entity = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tid,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="n" * 64,
        metadata_json={"projection_kind": "notion_user", "notion_user_id": notion_id},
        engine_build_ref="test",
    )
    db_session.add(entity)
    db_session.commit()

    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people", auth=ADMIN_AUTH)
    assert res.status_code == 200
    person = res.json()["people"][0]
    assert person["display_name"] is not None
    assert "Notion user" in person["display_name"]
    assert person["email"] is None
    assert "Notion" in person["systems"]


def test_operator_people_directory_labels_slack_user_from_roster(
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity

    tid = _tenant(db_session)
    _raw_row(
        db_session,
        tenant_id=tid,
        resource_type="slack.user",
        external_id="U123",
        payload_body={
            "member": {
                "id": "U123",
                "name": "alex",
                "profile": {"display_name": "Alex Chen", "email": "alex@example.com"},
            }
        },
    )
    entity = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tid,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="s" * 64,
        metadata_json={"projection_kind": "slack_user", "slack_user_id": "U123"},
        engine_build_ref="test",
    )
    db_session.add(entity)
    db_session.commit()

    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people", auth=ADMIN_AUTH)
    assert res.status_code == 200
    person = res.json()["people"][0]
    assert person["display_name"] == "Alex Chen"
    assert person["email"] == "alex@example.com"
    assert "Slack" in person["systems"]


def test_operator_people_directory_labels_notion_user_from_page_refs(
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity

    tid = _tenant(db_session)
    notion_id = "notion-user-ada"
    _raw_row(
        db_session,
        tenant_id=tid,
        connector="notion",
        resource_type="notion.page",
        external_id="page-1",
        payload_body={
            "page": {
                "created_by": {
                    "object": "user",
                    "id": notion_id,
                    "name": "Ada Lovelace",
                    "person": {"email": "ada@example.com"},
                }
            }
        },
    )
    entity = CortexOrgEntity(
        id=uuid.uuid4(),
        tenant_id=tid,
        entity_kind="human_actor",
        lifecycle_state="active",
        identity_key_fingerprint="p" * 64,
        metadata_json={"projection_kind": "notion_user", "notion_user_id": notion_id},
        engine_build_ref="test",
    )
    db_session.add(entity)
    db_session.commit()

    res = client.get(f"/admin/tenants/{tid}/cortex/operator/people", auth=ADMIN_AUTH)
    assert res.status_code == 200
    person = res.json()["people"][0]
    assert person["display_name"] == "Ada Lovelace"
    assert person["email"] == "ada@example.com"


@patch(
    "vector.domains.cortex.pipeline.operator_admin_actions.operator_rebuild_identities_v1",
)
def test_operator_rebuild_identities_reset_and_dirty(
    mock_rebuild: MagicMock,
    client: TestClient,
    db_session: Session,
) -> None:
    mock_rebuild.return_value = {
        "no_replay_job": True,
        "enqueued": False,
        "same_repair_as_phase_03": True,
        "convergence_dispatch": {"scheduled": True},
    }
    tid = _tenant(db_session)
    db_session.commit()

    res = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={
            "action": "rebuild_identities",
            "confirmation": REBUILD_IDENTITIES_CONFIRM_PHRASE,
        },
        auth=ADMIN_AUTH,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["action"] == "rebuild_identities"
    assert body["result"]["no_replay_job"] is True
    mock_rebuild.assert_called_once()


@patch(
    "vector.domains.cortex.execution.convergence_dispatch.mark_dirty_and_enqueue_convergence_v1",
    return_value={"scheduled": True, "path": "convergence_lease"},
)
@patch(
    "vector.domains.cortex.identity.identity_substrate_operator_v1.reset_identity_substrate_repair_state_v1",
    return_value={"anchor_offset": 0},
)
@patch(
    "vector.domains.cortex.identity.identity_substrate_operator_v1.substrate_counts",
    return_value={"identity_anchors": 10},
)
def test_enqueue_rebuild_identities_collapsed_to_reset_and_dirty(
    _mock_counts: MagicMock,
    _mock_reset: MagicMock,
    mock_convergence: MagicMock,
    db_session: Session,
) -> None:
    """Wave 2: public enqueue helper delegates to reset + mark dirty (no Celery replay job)."""
    tid = _tenant(db_session)

    out = enqueue_rebuild_identities_from_anchors_v1(db_session, tenant_id=tid)

    assert out["no_replay_job"] is True
    mock_convergence.assert_called_once()
    assert mock_convergence.call_args.kwargs["reason"] == "operator:rebuild_identities"
