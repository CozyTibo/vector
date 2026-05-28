"""Shared fixtures for identity matching scenario tests (Fizzer-shaped tenants)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant
from vector.domains.cortex.identity.materialize import execute_identity_pass_for_tenant
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_shared import append_raw
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User


@dataclass(frozen=True)
class NotionActorSpec:
    external_id: str
    name: str
    email: str | None = None


@dataclass(frozen=True)
class SlackActorSpec:
    external_id: str
    login: str
    real_name: str
    profile_email: str | None = None


def seed_fizzer_actors(
    db_session: Session,
    *,
    notion: tuple[NotionActorSpec, ...] = (),
    slack: tuple[SlackActorSpec, ...] = (),
    email_domain: str = "fizzer.com",
) -> uuid.UUID:
    """Ingest raw Notion/Slack actor rows for a single tenant."""
    user = User(email=f"match-{uuid.uuid4().hex[:8]}@{email_domain}", full_name="Match test")
    tenant = Tenant(
        company_name="Match Test Co",
        primary_email=user.email,
        email_domain=email_domain,
        slug=f"match-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))

    connections: dict[str, TenantConnection] = {}
    if notion:
        connections["notion"] = TenantConnection(
            tenant_id=tenant.id,
            provider="notion",
            status="active",
            connected_by_user_id=user.id,
        )
    if slack:
        connections["slack"] = TenantConnection(
            tenant_id=tenant.id,
            provider="slack",
            status="active",
            connected_by_user_id=user.id,
        )
    db_session.add_all(connections.values())
    db_session.flush()

    now = datetime.now(UTC)
    runs: dict[str, IngestionRun] = {}
    for provider, conn in connections.items():
        runs[provider] = IngestionRun(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connection_id=conn.id,
            connector=provider,
            status="COMPLETED",
            source_trigger="test",
            sync_mode="incremental",
            replay_mode=False,
            replay_version=1,
            started_at=now,
        )
    db_session.add_all(runs.values())
    db_session.flush()

    ctx = IngestionSyncContext.live_incremental()
    if notion:
        notion_conn = connections["notion"]
        notion_run = runs["notion"]
    if slack:
        slack_conn = connections["slack"]
        slack_run = runs["slack"]
    for actor in notion:
        body: dict[str, Any] = {
            **core_envelope_fields(
                connector="notion",
                connection_id=notion_conn.id,
                source_object_type="notion.user",
                source_object_id=actor.external_id,
            ),
            "user": {
                "id": actor.external_id,
                "name": actor.name,
                "type": "person",
            },
        }
        if actor.email:
            body["user"]["person"] = {"email": actor.email}
        append_raw(
            db_session,
            ctx=ctx,
            tenant_id=tenant.id,
            connection_id=notion_conn.id,
            connector="notion",
            run_id=notion_run.id,
            source_trigger="test",
            resource_type="notion.user",
            external_id=actor.external_id,
            api_endpoint="https://api.notion.com/v1/users",
            query_params={},
            payload_body=body,
            http_status=200,
            idempotency_key=f"match:notion:{actor.external_id}",
        )

    for actor in slack:
        profile: dict[str, Any] = {"real_name": actor.real_name}
        if actor.profile_email:
            profile["email"] = actor.profile_email
        append_raw(
            db_session,
            ctx=ctx,
            tenant_id=tenant.id,
            connection_id=slack_conn.id,
            connector="slack",
            run_id=slack_run.id,
            source_trigger="test",
            resource_type="slack.user",
            external_id=actor.external_id,
            api_endpoint="https://slack.test/users.list",
            query_params={},
            payload_body={
                **core_envelope_fields(
                    connector="slack",
                    connection_id=slack_conn.id,
                    source_object_type="slack.user",
                    source_object_id=actor.external_id,
                ),
                "member": {
                    "id": actor.external_id,
                    "name": actor.login,
                    "is_bot": False,
                    "profile": profile,
                },
            },
            http_status=200,
            idempotency_key=f"match:slack:{actor.external_id}",
        )

    db_session.commit()
    return tenant.id


def run_full_identity_pass(db_session: Session, tenant_id: uuid.UUID) -> None:
    execute_canon_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=500)
    db_session.commit()
    execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=500,
        periodic_rescan_limit=500,
    )
    db_session.commit()


def canon_labels_for_identity(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    identity_id: uuid.UUID,
) -> list[str]:
    rows = list(
        db_session.execute(
            select(CanonEntity.display_label)
            .join(IdentityAccount, IdentityAccount.canon_entity_id == CanonEntity.id)
            .where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.identity_entity_id == identity_id,
                IdentityAccount.unlinked_at.is_(None),
            ),
        ).all(),
    )
    return [str(label) for (label,) in rows]


def identity_id_for_email(db_session: Session, *, tenant_id: uuid.UUID, email: str) -> uuid.UUID | None:
    return db_session.scalar(
        select(IdentityEntity.id).where(
            IdentityEntity.tenant_id == tenant_id,
            IdentityEntity.primary_email == email,
            IdentityEntity.status == "active",
        ),
    )


def identity_id_for_canon_label_substring(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    substring: str,
) -> uuid.UUID | None:
    row = db_session.execute(
        select(IdentityAccount.identity_entity_id, CanonEntity.display_label)
        .join(CanonEntity, CanonEntity.id == IdentityAccount.canon_entity_id)
        .where(
            IdentityAccount.tenant_id == tenant_id,
            IdentityAccount.unlinked_at.is_(None),
        ),
    ).all()
    needle = substring.lower()
    hits = {identity_id for identity_id, label in row if needle in (label or "").lower()}
    if len(hits) == 1:
        return next(iter(hits))
    return None


def assert_same_identity(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    label_substrings: tuple[str, ...],
) -> uuid.UUID:
    ids: list[uuid.UUID] = []
    for part in label_substrings:
        iid = identity_id_for_canon_label_substring(db_session, tenant_id=tenant_id, substring=part)
        assert iid is not None, f"no identity for canon label containing {part!r}"
        ids.append(iid)
    assert len(set(ids)) == 1, f"expected one identity for {label_substrings}, got {ids}"
    return ids[0]


def assert_separate_identities(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    left_label: str,
    right_label: str,
) -> None:
    left_id = identity_id_for_canon_label_substring(db_session, tenant_id=tenant_id, substring=left_label)
    right_id = identity_id_for_canon_label_substring(db_session, tenant_id=tenant_id, substring=right_label)
    assert left_id is not None, f"missing identity for {left_label!r}"
    assert right_id is not None, f"missing identity for {right_label!r}"
    assert left_id != right_id, f"{left_label!r} and {right_label!r} must not share an identity"
