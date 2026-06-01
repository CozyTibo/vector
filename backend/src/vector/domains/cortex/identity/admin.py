"""Admin-facing identity read APIs (v1)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_dirty_queue import IdentityDirtyQueue
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.domains.cortex.canon.notion_display_labels import enrich_notion_display_labels
from vector.domains.cortex.identity.materialize import _latest_actor_payload
from vector.domains.cortex.identity.pass_run_ops import abandon_stuck_running_identity_passes
from vector.domains.cortex.identity.signals import extract_actor_signal

MANUAL_IDENTITY_PASS_CONFIRMATION = "RUN IDENTITY RECONCILIATION PASS"
AVATAR_CONNECTOR_PRIORITY: tuple[str, ...] = ("slack", "github", "notion", "linear")


def _avatar_url_from_evidence(evidence: dict[str, Any]) -> str | None:
    raw = evidence.get("avatar_url")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _avatar_url_for_account(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    account: IdentityAccount,
) -> str | None:
    evidence = account.evidence_json if isinstance(account.evidence_json, dict) else {}
    cached = _avatar_url_from_evidence(evidence)
    if cached:
        return cached
    row = _latest_actor_payload(session, tenant_id=tenant_id, canon_entity_id=account.canon_entity_id)
    if row is None:
        return None
    entity, source, raw = row
    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    signal = extract_actor_signal(
        canon_entity_id=entity.id,
        connector=entity.connector,
        connection_id=entity.connection_id,
        entity_key=entity.entity_key,
        external_id=source.external_id,
        source_revision_key=source.source_revision_key,
        payload_body=payload,
    )
    return signal.avatar_url


def pick_identity_avatar_url(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    accounts: list[IdentityAccount],
) -> str | None:
    """Prefer Slack portrait, then GitHub, Notion, Linear."""
    by_connector: dict[str, IdentityAccount] = {}
    for account in accounts:
        if account.connector not in by_connector:
            by_connector[account.connector] = account
    for connector in AVATAR_CONNECTOR_PRIORITY:
        account = by_connector.get(connector)
        if account is None:
            continue
        url = _avatar_url_for_account(session, tenant_id=tenant_id, account=account)
        if url:
            return url
    return None


MANUAL_IDENTITY_REBUILD_CONFIRMATION = "REBUILD IDENTITIES FROM CANON ACTORS"


def build_identity_readiness(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    scheduler: dict[str, Any],
    reconcile_stuck_passes: bool = True,
) -> dict[str, Any]:
    abandoned_stuck = 0
    if reconcile_stuck_passes and scheduler.get("enabled"):
        interval = int(scheduler.get("interval_seconds") or 300)
        abandoned_stuck = abandon_stuck_running_identity_passes(
            session,
            tenant_id=tenant_id,
            interval_seconds=interval,
        )
    actor_count = int(
        session.scalar(
            select(func.count())
            .select_from(CanonEntity)
            .where(CanonEntity.tenant_id == tenant_id, CanonEntity.entity_type == "actor"),
        )
        or 0,
    )
    identity_count = int(
        session.scalar(
            select(func.count())
            .select_from(IdentityEntity)
            .where(IdentityEntity.tenant_id == tenant_id, IdentityEntity.status == "active"),
        )
        or 0,
    )
    inactive_human_count = int(
        session.scalar(
            select(func.count())
            .select_from(IdentityEntity)
            .where(
                IdentityEntity.tenant_id == tenant_id,
                IdentityEntity.status == "active",
                IdentityEntity.kind == "inactive_human",
            ),
        )
        or 0,
    )
    linked_count = int(
        session.scalar(
            select(func.count())
            .select_from(IdentityAccount)
            .where(IdentityAccount.tenant_id == tenant_id, IdentityAccount.unlinked_at.is_(None)),
        )
        or 0,
    )
    unresolved_count = max(0, actor_count - linked_count)
    dirty_queue_depth = int(
        session.scalar(
            select(func.count())
            .select_from(IdentityDirtyQueue)
            .where(
                IdentityDirtyQueue.tenant_id == tenant_id,
                IdentityDirtyQueue.processed_at.is_(None),
            ),
        )
        or 0,
    )
    latest = session.scalar(
        select(IdentityPassRun)
        .where(IdentityPassRun.tenant_id == tenant_id)
        .order_by(IdentityPassRun.started_at.desc())
        .limit(1),
    )
    latest_payload: dict[str, Any] | None = None
    if latest is not None:
        latest_payload = {
            "id": str(latest.id),
            "status": latest.status,
            "source_trigger": latest.source_trigger,
            "started_at": latest.started_at.isoformat(),
            "finished_at": latest.finished_at.isoformat() if latest.finished_at else None,
            "error_summary": latest.error_summary,
            "stats": latest.stats,
        }
    return {
        "tenant_id": str(tenant_id),
        "actor_count": actor_count,
        "identity_count": identity_count,
        "inactive_human_count": inactive_human_count,
        "linked_account_count": linked_count,
        "unresolved_actor_count": unresolved_count,
        "dirty_queue_depth": dirty_queue_depth,
        "latest_pass_run": latest_payload,
        "scheduler": scheduler,
        "abandoned_stuck_running_passes": abandoned_stuck,
    }


def list_recent_identity_pass_runs(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    total = int(session.scalar(select(func.count()).where(IdentityPassRun.tenant_id == tenant_id)) or 0)
    rows = list(
        session.scalars(
            select(IdentityPassRun)
            .where(IdentityPassRun.tenant_id == tenant_id)
            .order_by(IdentityPassRun.started_at.desc())
            .offset(offset)
            .limit(limit),
        ).all(),
    )
    items = [
        {
            "id": str(r.id),
            "status": r.status,
            "source_trigger": r.source_trigger,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "error_summary": r.error_summary,
            "stats": r.stats,
        }
        for r in rows
    ]
    return items, total


def list_identities(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    kind: str | None = None,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    stmt = select(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id, IdentityEntity.status == "active")
    count_stmt = select(func.count()).select_from(IdentityEntity).where(
        IdentityEntity.tenant_id == tenant_id,
        IdentityEntity.status == "active",
    )
    if kind:
        stmt = stmt.where(IdentityEntity.kind == kind)
        count_stmt = count_stmt.where(IdentityEntity.kind == kind)
    if search and search.strip():
        q = f"%{search.strip()}%"
        stmt = stmt.where(or_(IdentityEntity.display_name.ilike(q), IdentityEntity.primary_email.ilike(q)))
        count_stmt = count_stmt.where(or_(IdentityEntity.display_name.ilike(q), IdentityEntity.primary_email.ilike(q)))
    total = int(session.scalar(count_stmt) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(IdentityEntity.resolved_at.desc()).offset(offset).limit(limit),
        ).all(),
    )
    items: list[dict[str, Any]] = []
    for r in rows:
        linked_accounts = list(
            session.scalars(
                select(IdentityAccount)
                .where(
                    IdentityAccount.tenant_id == tenant_id,
                    IdentityAccount.identity_entity_id == r.id,
                    IdentityAccount.unlinked_at.is_(None),
                )
                .order_by(IdentityAccount.linked_at.asc()),
            ).all(),
        )
        connectors = sorted({a.connector for a in linked_accounts})
        avatar_url = pick_identity_avatar_url(session, tenant_id=tenant_id, accounts=linked_accounts)
        items.append(
            {
                "id": str(r.id),
                "kind": r.kind,
                "display_name": r.display_name,
                "primary_email": r.primary_email,
                "resolver_version": r.resolver_version,
                "resolved_at": r.resolved_at.isoformat(),
                "account_count": len(linked_accounts),
                "connectors": connectors,
                "avatar_url": avatar_url,
            },
        )
    return items, total


def get_identity_detail(session: Session, tenant_id: uuid.UUID, identity_id: uuid.UUID) -> dict[str, Any] | None:
    identity = session.scalar(
        select(IdentityEntity).where(
            IdentityEntity.tenant_id == tenant_id,
            IdentityEntity.id == identity_id,
            IdentityEntity.status == "active",
        ),
    )
    if identity is None:
        return None
    accounts = list(
        session.execute(
            select(IdentityAccount, CanonEntity)
            .join(CanonEntity, CanonEntity.id == IdentityAccount.canon_entity_id)
            .where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.identity_entity_id == identity.id,
                IdentityAccount.unlinked_at.is_(None),
            )
            .order_by(IdentityAccount.linked_at.asc()),
        ).all(),
    )
    out_accounts: list[dict[str, Any]] = []
    account_entities = [entity for _, entity in accounts]
    labels = enrich_notion_display_labels(session, account_entities)
    for account, entity in accounts:
        out_accounts.append(
            {
                "identity_account_id": str(account.id),
                "canon_entity_id": str(entity.id),
                "connector": account.connector,
                "connection_id": str(account.connection_id),
                "display_label": labels.get(entity.id, entity.display_label),
                "entity_key": entity.entity_key,
                "link_tier": account.link_tier,
                "link_rule": account.link_rule,
                "confidence": account.confidence,
                "evidence_json": dict(account.evidence_json) if isinstance(account.evidence_json, dict) else {},
                "linked_at": account.linked_at.isoformat(),
            },
        )
    return {
        "id": str(identity.id),
        "kind": identity.kind,
        "display_name": identity.display_name,
        "primary_email": identity.primary_email,
        "resolver_version": identity.resolver_version,
        "resolved_at": identity.resolved_at.isoformat(),
        "accounts": out_accounts,
    }


def list_unresolved_actor_entities(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    base = select(CanonEntity).where(
        CanonEntity.tenant_id == tenant_id,
        CanonEntity.entity_type == "actor",
        ~exists(
            select(IdentityAccount.id).where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.canon_entity_id == CanonEntity.id,
                IdentityAccount.unlinked_at.is_(None),
            ),
        ),
    )
    rows = list(
        session.scalars(base.order_by(CanonEntity.materialized_at.desc()).offset(offset).limit(limit)).all(),
    )
    total = int(session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    labels = enrich_notion_display_labels(session, rows)
    items = [
        {
            "canon_entity_id": str(r.id),
            "connector": r.connector,
            "display_label": labels.get(r.id, r.display_label),
            "entity_key": r.entity_key,
            "materialized_at": r.materialized_at.isoformat(),
        }
        for r in rows
    ]
    return items, total

