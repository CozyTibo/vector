"""Declared domain pass execution."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.declared_container_registry import (
    ATTR_DECLARED_CONTAINER_EXTERNAL_ID,
    ATTR_DECLARED_CONTAINER_KIND,
    DIRECT_MEMBER_ENTITY_TYPES,
    member_attrs_match_container,
)
from vector.domains.cortex.declared_domains.expand import refresh_domain_memberships
from vector.domains.cortex.declared_domains.extractor_version import effective_declared_domain_extractor_version
from vector.domains.cortex.declared_domains.pass_run_ops import RUN_COMPLETED, RUN_FAILED, RUN_RUNNING
from vector.domains.cortex.declared_domains.stats import recompute_domain_stats
from vector.domains.cortex.graph.materialize import tenant_has_canon_backlog
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_dirty_queue import DeclaredDomainDirtyQueue
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.declared_domain_pass_run import DeclaredDomainPassRun
from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue

_logger = logging.getLogger("app")


def tenant_has_graph_backlog(session: Session, tenant_id: uuid.UUID) -> bool:
    pending = session.scalar(
        select(func.count())
        .select_from(GraphDirtyQueue)
        .where(
            GraphDirtyQueue.tenant_id == tenant_id,
            GraphDirtyQueue.processed_at.is_(None),
        ),
    )
    return int(pending or 0) > 0


def sync_domains_from_seeds(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    extractor_version: int,
) -> int:
    """Upsert declared_domains rows for all canon seeds in tenant."""
    seeds = session.scalars(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.attrs_json[ATTR_DECLARED_CONTAINER_KIND].astext.isnot(None),
        ),
    ).all()
    now = utc_now()
    upserted = 0
    for seed in seeds:
        attrs = seed.attrs_json if isinstance(seed.attrs_json, dict) else {}
        kind = attrs.get(ATTR_DECLARED_CONTAINER_KIND)
        if not isinstance(kind, str) or not kind:
            continue
        latest_source = session.scalar(
            select(CanonEntitySource)
            .where(CanonEntitySource.canon_entity_id == seed.id, CanonEntitySource.is_latest.is_(True))
            .limit(1),
        )
        resource_type = latest_source.resource_type if latest_source is not None else seed.connector
        domain = session.scalar(
            select(DeclaredDomain).where(DeclaredDomain.seed_canon_entity_id == seed.id),
        )
        if domain is None:
            domain = DeclaredDomain(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                display_name=seed.display_label,
                declared_container_kind=kind,
                seed_canon_entity_id=seed.id,
                seed_connector=seed.connector,
                seed_resource_type=resource_type,
                extractor_version=extractor_version,
                first_observed_at=seed.materialized_at or now,
                last_activity_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(domain)
            upserted += 1
        else:
            domain.display_name = seed.display_label
            domain.declared_container_kind = kind
            domain.seed_connector = seed.connector
            domain.seed_resource_type = resource_type
            domain.extractor_version = extractor_version
            domain.updated_at = now
    session.flush()
    return upserted


def _domains_for_dirty_entity(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> set[uuid.UUID]:
    domain_ids: set[uuid.UUID] = set()
    attrs = entity.attrs_json if isinstance(entity.attrs_json, dict) else {}
    if attrs.get(ATTR_DECLARED_CONTAINER_KIND):
        domain = session.scalar(
            select(DeclaredDomain.id).where(
                DeclaredDomain.tenant_id == tenant_id,
                DeclaredDomain.seed_canon_entity_id == entity.id,
            ),
        )
        if domain is not None:
            domain_ids.add(domain)

    memberships = session.scalars(
        select(DeclaredDomainMembership.declared_domain_id).where(
            DeclaredDomainMembership.tenant_id == tenant_id,
            DeclaredDomainMembership.canon_entity_id == entity.id,
            DeclaredDomainMembership.status == STATUS_ACTIVE,
        ),
    ).all()
    domain_ids.update(memberships)

    if entity.entity_type in DIRECT_MEMBER_ENTITY_TYPES:
        for domain in session.scalars(
            select(DeclaredDomain).where(DeclaredDomain.tenant_id == tenant_id),
        ).all():
            seed = session.get(CanonEntity, domain.seed_canon_entity_id)
            if seed is None:
                continue
            seed_attrs = seed.attrs_json if isinstance(seed.attrs_json, dict) else {}
            ext = seed_attrs.get(ATTR_DECLARED_CONTAINER_EXTERNAL_ID)
            if isinstance(ext, str) and member_attrs_match_container(
                attrs,
                container_kind=domain.declared_container_kind,
                container_external_id=ext,
            ):
                domain_ids.add(domain.id)
    return domain_ids


def _refresh_domain(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    domain_id: uuid.UUID,
    extractor_version: int,
    expansion_max_depth: int,
    graph_expansion_enabled: bool,
    momentum_min_baseline: int,
) -> dict[str, Any]:
    domain = session.get(DeclaredDomain, domain_id)
    if domain is None or domain.tenant_id != tenant_id:
        return {"status": "missing"}
    seed = session.get(CanonEntity, domain.seed_canon_entity_id)
    if seed is None:
        return {"status": "seed_missing"}
    expansion = refresh_domain_memberships(
        session,
        tenant_id=tenant_id,
        domain=domain,
        seed_entity=seed,
        extractor_version=extractor_version,
        expansion_max_depth=expansion_max_depth,
        graph_expansion_enabled=graph_expansion_enabled,
    )
    recompute_domain_stats(
        session,
        tenant_id=tenant_id,
        domain=domain,
        expansion_level=str(expansion.get("expansion_level", "direct")),
        momentum_min_baseline=momentum_min_baseline,
    )
    return {"status": "refreshed", **expansion}


def _fetch_dirty_batch(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    batch_limit: int,
    max_attempts: int,
) -> list[DeclaredDomainDirtyQueue]:
    cap = max(1, min(batch_limit, 5000))
    attempt_cap = max(1, max_attempts)
    return list(
        session.scalars(
            select(DeclaredDomainDirtyQueue)
            .where(
                DeclaredDomainDirtyQueue.tenant_id == tenant_id,
                DeclaredDomainDirtyQueue.processed_at.is_(None),
                DeclaredDomainDirtyQueue.attempts < attempt_cap,
            )
            .order_by(DeclaredDomainDirtyQueue.enqueued_at.asc())
            .limit(cap),
        ).all(),
    )


def execute_declared_domain_pass_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str,
    batch_limit: int,
    max_attempts: int = 5,
    extractor_version: int | None = None,
    drain: bool | None = None,
    expansion_max_depth: int = 2,
    momentum_min_baseline: int = 5,
) -> dict[str, Any]:
    if drain is None:
        drain = source_trigger == "manual_admin"
    resolved_extractor = effective_declared_domain_extractor_version(extractor_version)
    graph_expansion_enabled = not tenant_has_graph_backlog(session, tenant_id)

    run = DeclaredDomainPassRun(
        tenant_id=tenant_id,
        source_trigger=source_trigger,
        status=RUN_RUNNING,
        started_at=utc_now(),
    )
    session.add(run)
    session.flush()

    stats: dict[str, int] = {
        "processed": 0,
        "domains_synced": 0,
        "domains_refreshed": 0,
        "errors": 0,
    }
    max_iterations = 100 if drain else 1
    try:
        stats["domains_synced"] = sync_domains_from_seeds(
            session,
            tenant_id=tenant_id,
            extractor_version=resolved_extractor,
        )
        touched_domains: set[uuid.UUID] = set()
        for _ in range(max_iterations):
            items = _fetch_dirty_batch(
                session,
                tenant_id=tenant_id,
                batch_limit=batch_limit,
                max_attempts=max_attempts,
            )
            if not items:
                break
            for item in items:
                stats["processed"] += 1
                entity = session.get(CanonEntity, item.canon_entity_id)
                if entity is None or entity.tenant_id != tenant_id:
                    item.processed_at = utc_now()
                    item.last_error = "entity_missing"
                    continue
                try:
                    touched_domains.update(
                        _domains_for_dirty_entity(
                            session,
                            tenant_id=tenant_id,
                            entity=entity,
                        ),
                    )
                    item.processed_at = utc_now()
                    item.last_error = None
                except Exception as exc:
                    stats["errors"] += 1
                    item.attempts += 1
                    item.last_error = str(exc)[:1000]
                    _logger.exception(
                        "declared domain dirty entity failed tenant=%s entity=%s",
                        tenant_id,
                        item.canon_entity_id,
                    )
            if not drain:
                break

        if not touched_domains:
            all_domains = session.scalars(
                select(DeclaredDomain.id).where(DeclaredDomain.tenant_id == tenant_id),
            ).all()
            touched_domains = set(all_domains)

        for domain_id in touched_domains:
            try:
                out = _refresh_domain(
                    session,
                    tenant_id=tenant_id,
                    domain_id=domain_id,
                    extractor_version=resolved_extractor,
                    expansion_max_depth=expansion_max_depth,
                    graph_expansion_enabled=graph_expansion_enabled,
                    momentum_min_baseline=momentum_min_baseline,
                )
                if out.get("status") == "refreshed":
                    stats["domains_refreshed"] += 1
            except Exception:
                stats["errors"] += 1
                _logger.exception(
                    "declared domain refresh failed tenant=%s domain=%s",
                    tenant_id,
                    domain_id,
                )

        run.status = RUN_COMPLETED
        run.finished_at = utc_now()
        run.stats = {**stats, "graph_expansion_enabled": int(graph_expansion_enabled)}
        session.flush()
        return {"status": "completed", "run_id": str(run.id), "stats": run.stats}
    except Exception as exc:
        run.status = RUN_FAILED
        run.finished_at = utc_now()
        run.error_summary = str(exc)[:2000]
        run.stats = stats
        session.flush()
        raise


def enqueue_all_seeds_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    reason: str,
) -> int:
    from vector.domains.cortex.declared_domains.enqueue import enqueue_declared_domain_entity

    count = 0
    seeds = session.scalars(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.attrs_json[ATTR_DECLARED_CONTAINER_KIND].astext.isnot(None),
        ),
    ).all()
    for seed in seeds:
        enqueue_declared_domain_entity(
            session,
            tenant_id=tenant_id,
            canon_entity_id=seed.id,
            reason=reason,
        )
        count += 1
    return count


MANUAL_DECLARED_DOMAIN_REBUILD_CONFIRMATION = "REBUILD DECLARED DOMAINS"


def prepare_declared_domain_rebuild_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """Clear declared-domain projection tables and enqueue seeds + member entities."""
    from sqlalchemy import delete

    from vector.domains.cortex.declared_domains.enqueue import (
        REASON_EXTRACTOR_BUMP,
        REASON_MEMBER_MATERIALIZED,
        enqueue_declared_domain_entity,
    )

    session.execute(
        delete(DeclaredDomainMembership).where(DeclaredDomainMembership.tenant_id == tenant_id),
    )
    session.execute(delete(DeclaredDomainStats).where(DeclaredDomainStats.tenant_id == tenant_id))
    session.execute(delete(DeclaredDomain).where(DeclaredDomain.tenant_id == tenant_id))
    session.execute(
        delete(DeclaredDomainDirtyQueue).where(DeclaredDomainDirtyQueue.tenant_id == tenant_id),
    )
    seeds_enqueued = enqueue_all_seeds_for_tenant(
        session,
        tenant_id=tenant_id,
        reason=REASON_EXTRACTOR_BUMP,
    )
    members_enqueued = 0
    for entity in session.scalars(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.entity_type.in_(tuple(sorted(DIRECT_MEMBER_ENTITY_TYPES))),
        ),
    ).all():
        enqueue_declared_domain_entity(
            session,
            tenant_id=tenant_id,
            canon_entity_id=entity.id,
            reason=REASON_MEMBER_MATERIALIZED,
        )
        members_enqueued += 1
    return {
        "seeds_enqueued": seeds_enqueued,
        "members_enqueued": members_enqueued,
    }
