"""Execute a claimed cortex_pass."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant, process_dirty_queue_batch
from vector.domains.cortex.identity.materialize import execute_identity_pass_for_tenant
from vector.domains.cortex.identity.resolver_version import effective_identity_resolver_version
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.domains.cortex.runtime.claim import extend_pass_lease_v1
from vector.domains.cortex.runtime.pass_types import (
    CANON_PASS,
    IDENTITY_PASS,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
)
from vector.infrastructure.db.models.cortex_pass import CortexPass
from vector.settings import Settings

_LOGGER = logging.getLogger(__name__)


def _run_canon_pass(session: Session, settings: Settings, row: CortexPass) -> dict[str, Any]:
    batch = settings.cortex_canon_batch_raw_limit
    out = execute_canon_pass_for_tenant(
        session,
        tenant_id=row.tenant_id,
        source_trigger=row.source_trigger,
        batch_limit=batch,
    )
    dirty_stats = process_dirty_queue_batch(session, tenant_id=row.tenant_id, batch_limit=batch)
    out["dirty_queue"] = dirty_stats
    return out


def _run_identity_pass(session: Session, settings: Settings, row: CortexPass) -> dict[str, Any]:
    batch = settings.cortex_identity_batch_actor_limit
    resolver_version = effective_identity_resolver_version(settings.cortex_identity_resolver_version)
    payload = row.payload_json if isinstance(row.payload_json, dict) else {}
    drain = bool(payload.get("drain"))
    return execute_identity_pass_for_tenant(
        session,
        tenant_id=row.tenant_id,
        source_trigger=row.source_trigger,
        batch_limit=batch,
        max_attempts=settings.cortex_identity_max_attempts,
        periodic_rescan_limit=settings.cortex_identity_periodic_rescan_limit,
        resolver_version=resolver_version,
        drain=drain if drain else None,
    )


def execute_claimed_pass_v1(
    session: Session,
    settings: Settings,
    row: CortexPass,
    *,
    lease_ttl_seconds: int,
) -> dict[str, Any]:
    extend_pass_lease_v1(session, row, lease_ttl_seconds=lease_ttl_seconds)
    if row.pass_type == CANON_PASS:
        stats = _run_canon_pass(session, settings, row)
    elif row.pass_type == IDENTITY_PASS:
        stats = _run_identity_pass(session, settings, row)
    else:
        msg = f"unsupported_pass_type:{row.pass_type}"
        raise ValueError(msg)
    return stats


def complete_pass_v1(session: Session, row: CortexPass, *, stats: dict[str, Any]) -> None:
    row.status = STATUS_COMPLETED
    row.finished_at = utc_now()
    row.stats_json = stats
    row.locked_by = None
    row.locked_until = None
    row.error_summary = None
    session.flush()


def fail_pass_v1(
    session: Session,
    row: CortexPass,
    *,
    error_summary: str,
    retry_delay_seconds: int,
) -> None:
    row.error_summary = error_summary[:2000]
    row.stats_json = row.stats_json or {}
    if row.attempt_count >= row.max_attempts:
        row.status = STATUS_FAILED
        row.finished_at = utc_now()
        row.locked_by = None
        row.locked_until = None
    else:
        row.status = STATUS_PENDING
        row.scheduled_at = utc_now() + timedelta(seconds=max(30, retry_delay_seconds))
        row.locked_by = None
        row.locked_until = None
    session.flush()
