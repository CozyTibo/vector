"""Admin entry points for Execution Surfaces HTTP layer."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution_surfaces.activity import list_observation_activity
from vector.domains.cortex.execution_surfaces.domains import (
    get_domain_surface_detail,
    list_domains_for_surface,
)
from vector.domains.cortex.execution_surfaces.overview import build_overview
from vector.domains.cortex.execution_surfaces.people import (
    get_person_surface_detail,
    list_people_for_surface,
)
from vector.domains.cortex.execution_surfaces.work import get_work_artifact_detail, list_work_artifacts


def build_execution_surfaces_overview(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    activity_min_events: int,
    momentum_min_baseline: int,
) -> dict[str, Any]:
    return build_overview(
        session,
        tenant_id,
        activity_min_events=activity_min_events,
        momentum_min_baseline=momentum_min_baseline,
    )


def list_execution_surface_domains(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    sort: str,
    lifecycle: str | None,
    activity_min_events: int,
    momentum_min_baseline: int,
    offset: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    return list_domains_for_surface(
        session,
        tenant_id,
        sort=sort,
        lifecycle=lifecycle,
        activity_min_events=activity_min_events,
        momentum_min_baseline=momentum_min_baseline,
        offset=offset,
        limit=limit,
    )


def get_execution_surface_domain(
    session: Session,
    tenant_id: uuid.UUID,
    domain_id: uuid.UUID,
) -> dict[str, Any] | None:
    return get_domain_surface_detail(session, tenant_id, domain_id)


def list_execution_surface_people(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    offset: int,
    limit: int,
    search: str | None,
) -> tuple[list[dict[str, Any]], int]:
    return list_people_for_surface(session, tenant_id, offset=offset, limit=limit, search=search)


def get_execution_surface_person(
    session: Session,
    tenant_id: uuid.UUID,
    identity_id: uuid.UUID,
) -> dict[str, Any] | None:
    return get_person_surface_detail(session, tenant_id, identity_id)


def list_execution_surface_work(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    entity_type: str | None,
    connector: str | None,
    domain_id: uuid.UUID | None,
    offset: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    return list_work_artifacts(
        session,
        tenant_id,
        entity_type=entity_type,
        connector=connector,
        domain_id=domain_id,
        offset=offset,
        limit=limit,
    )


def get_execution_surface_work(
    session: Session,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
) -> dict[str, Any] | None:
    return get_work_artifact_detail(session, tenant_id, canon_entity_id)


def list_execution_surface_activity(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    identity_id: uuid.UUID | None,
    domain_id: uuid.UUID | None,
    entity_type: str | None,
    hours: int,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    items, total, meta = list_observation_activity(
        session,
        tenant_id,
        identity_id=identity_id,
        domain_id=domain_id,
        entity_type=entity_type,
        hours=hours,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total_count": total,
        "offset": offset,
        "limit": limit,
        **meta,
    }
