"""Phase 0 identity actor signal inventory."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.signals import extract_actor_signal
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def build_actor_signal_inventory(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 5000,
) -> dict[str, Any]:
    """Summarize available identity signals across canon actor entities."""
    limit = max(1, min(int(limit), 20000))
    rows = list(
        session.execute(
            select(CanonEntity, CanonEntitySource, RawIngestionRecord)
            .join(CanonEntitySource, CanonEntitySource.canon_entity_id == CanonEntity.id)
            .join(RawIngestionRecord, RawIngestionRecord.id == CanonEntitySource.raw_id)
            .where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_type == "actor",
                CanonEntitySource.is_latest.is_(True),
            )
            .order_by(CanonEntity.materialized_at.desc())
            .limit(limit),
        ).all(),
    )
    by_connector: dict[str, dict[str, int]] = {}
    total = 0
    with_email = 0
    with_handle = 0
    with_name = 0
    with_bot = 0
    with_avatar = 0
    for entity, src, raw in rows:
        payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
        signal = extract_actor_signal(
            canon_entity_id=entity.id,
            connector=entity.connector,
            connection_id=entity.connection_id,
            entity_key=entity.entity_key,
            external_id=src.external_id,
            source_revision_key=src.source_revision_key,
            payload_body=payload,
        )
        total += 1
        c = by_connector.setdefault(
            entity.connector,
            {
                "connector": entity.connector,
                "actors": 0,
                "with_email": 0,
                "with_handle": 0,
                "with_name": 0,
                "bot_or_service": 0,
                "with_avatar": 0,
            },
        )
        c["actors"] += 1
        if signal.emails:
            with_email += 1
            c["with_email"] += 1
        if signal.handles:
            with_handle += 1
            c["with_handle"] += 1
        if signal.display_names:
            with_name += 1
            c["with_name"] += 1
        if signal.is_bot is True:
            with_bot += 1
            c["bot_or_service"] += 1
        if signal.avatar_url:
            with_avatar += 1
            c["with_avatar"] += 1
    connectors = list(by_connector.values())
    connectors.sort(key=lambda r: (-r["actors"], str(r["connector"])))

    def _rate(n: int) -> float | None:
        if total <= 0:
            return None
        return round(100.0 * float(n) / float(total), 1)

    return {
        "tenant_id": str(tenant_id),
        "sampled_actors": total,
        "sample_limit": limit,
        "email_coverage_pct": _rate(with_email),
        "handle_coverage_pct": _rate(with_handle),
        "display_name_coverage_pct": _rate(with_name),
        "bot_detection_pct": _rate(with_bot),
        "avatar_coverage_pct": _rate(with_avatar),
        "connectors": connectors,
    }

