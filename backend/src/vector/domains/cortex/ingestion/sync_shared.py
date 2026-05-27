"""Shared ingestion sync helpers (checkpoint, raw persistence, connections)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from collections.abc import Mapping
from typing import Any, cast

import httpx
from sqlalchemy import Table, case, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.github.errors import GitHubApiError
from vector.domains.cortex.connectors.github.http_client import (
    create_github_installation_access_token,
    list_deployment_statuses_page,
    list_installation_repositories_page,
    list_pull_issue_comments_page,
    list_pull_review_comments_page,
    list_pull_reviews_page,
    list_repo_branches_page,
    list_repo_check_runs_page,
    list_repo_commit_comments_page,
    list_repo_commits_page,
    list_repo_deployments_page,
    list_repo_issues_page,
    list_repo_issue_timeline_page,
    list_repo_pulls_page,
    list_repo_releases_page,
    list_repo_tags_page,
    list_repo_workflow_runs_page,
)
from vector.domains.cortex.connectors.provider_keys import (
    CONNECTION_PROVIDER_CALLS,
    CONNECTION_PROVIDER_GITHUB,
    CONNECTION_PROVIDER_LINEAR,
    CONNECTION_PROVIDER_NOTION,
    CONNECTION_PROVIDER_SLACK,
)
from vector.domains.cortex.ingestion.checkpoint_contract import merge_monotonic_connector_state
from vector.domains.cortex.ingestion.raw_envelope_contract import (
    EnvelopeContractViolation,
    core_envelope_fields,
    validate_raw_payload_for_persistence,
)
from vector.domains.cortex.ingestion.live_idempotency import (
    canonical_payload_hash,
    derive_logical_idempotency_key,
    derive_source_identity_key,
    derive_source_revision_key,
)
from vector.domains.cortex.ingestion.sync_context import SCOPE_DEFAULT, IngestionSyncContext
from vector.domains.cortex.ingestion.temporal_ordering import (
    derive_deletion_observed,
    derive_provider_event_timestamp,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.repositories import calls_connection as calls_repo
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import linear_connection as lin_repo
from vector.infrastructure.db.repositories import notion_connection as notion_repo
from vector.domains.cortex.connectors.slack.channel_ingest import get_saved_ingest_channel_ids
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.observability.ingestion_tasks import (
    PHASE_STEP1,
    PHASE_STEP3,
    PHASE_STEP4,
    PHASE_STEP5,
    log_ingestion_event,
)
from vector.settings import Settings

_logger = logging.getLogger("app")

RUN_RUNNING = "RUNNING"
RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def idem_key(ctx: IngestionSyncContext, run_id: uuid.UUID, base: str) -> str:
    """Stable idempotency suffix for replay (same ``replay_job_id`` → same key across runs)."""
    if ctx.replay_mode and ctx.replay_job_id is not None:
        key = f"{base}:rj:{ctx.replay_job_id}"
    else:
        key = f"{base}:{run_id}"
    return key[:128]


def tag_replay_payload(body: dict[str, Any], ctx: IngestionSyncContext) -> dict[str, Any]:
    if not ctx.replay_mode or ctx.replay_job_id is None:
        return dict(body)
    out = dict(body)
    out["cortex_replay_metadata"] = {
        "replay_job_id": str(ctx.replay_job_id),
        "replay_version": ctx.replay_version,
        "sync_mode": ctx.sync_mode,
    }
    return out


def hash_payload(body: dict[str, Any]) -> str:
    return canonical_payload_hash(body)


def _build_provenance_chain_id(
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    resource_type: str,
    source_identity_key: str,
) -> str:
    return (
        f"{tenant_id}:{connection_id}:{connector}:{resource_type}:{source_identity_key}"[:512]
    )


def _upsert_raw_memory_lineage(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    resource_type: str,
    source_identity_key: str,
    source_revision_key: str,
    payload_hash: str,
    run_id: uuid.UUID,
    replay_job_id: uuid.UUID | None,
    replay_version: int | None,
    raw_id: int,
    fetched_at: datetime,
) -> None:
    lineage_tbl = cast(Table, RawMemoryLineageIndex.__table__)
    provenance_chain_id = _build_provenance_chain_id(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_type=resource_type,
        source_identity_key=source_identity_key,
    )
    ins = pg_insert(lineage_tbl).values(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_type=resource_type,
        source_identity_key=source_identity_key,
        provenance_chain_id=provenance_chain_id,
        first_seen_raw_id=raw_id,
        latest_seen_raw_id=raw_id,
        first_observed_at=fetched_at,
        latest_observed_at=fetched_at,
        latest_source_revision_key=source_revision_key,
        latest_payload_hash=payload_hash,
        latest_run_id=run_id,
        latest_replay_job_id=replay_job_id,
        latest_replay_version=replay_version,
    )
    excluded = ins.excluded
    is_newer_or_equal = excluded.latest_observed_at >= lineage_tbl.c.latest_observed_at
    upd = ins.on_conflict_do_update(
        index_elements=[
            "tenant_id",
            "connection_id",
            "connector",
            "resource_type",
            "source_identity_key",
        ],
        set_={
            "provenance_chain_id": excluded.provenance_chain_id,
            "first_seen_raw_id": case(
                (excluded.first_observed_at <= lineage_tbl.c.first_observed_at, excluded.first_seen_raw_id),
                else_=lineage_tbl.c.first_seen_raw_id,
            ),
            "latest_seen_raw_id": case(
                (is_newer_or_equal, excluded.latest_seen_raw_id),
                else_=lineage_tbl.c.latest_seen_raw_id,
            ),
            "first_observed_at": func.least(lineage_tbl.c.first_observed_at, excluded.first_observed_at),
            "latest_observed_at": func.greatest(lineage_tbl.c.latest_observed_at, excluded.latest_observed_at),
            "latest_source_revision_key": case(
                (is_newer_or_equal, excluded.latest_source_revision_key),
                else_=lineage_tbl.c.latest_source_revision_key,
            ),
            "latest_payload_hash": case(
                (is_newer_or_equal, excluded.latest_payload_hash),
                else_=lineage_tbl.c.latest_payload_hash,
            ),
            "latest_run_id": case(
                (is_newer_or_equal, excluded.latest_run_id),
                else_=lineage_tbl.c.latest_run_id,
            ),
            "latest_replay_job_id": case(
                (is_newer_or_equal, excluded.latest_replay_job_id),
                else_=lineage_tbl.c.latest_replay_job_id,
            ),
            "latest_replay_version": case(
                (is_newer_or_equal, excluded.latest_replay_version),
                else_=lineage_tbl.c.latest_replay_version,
            ),
        },
    )
    session.execute(upd)


def _recompute_supersession_chain(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    resource_type: str,
    source_identity_key: str,
) -> None:
    session.execute(
        text(
            """
            WITH ordered AS (
                SELECT
                    source_revision_key,
                    LAG(source_revision_key) OVER (
                        PARTITION BY tenant_id, connection_id, connector, resource_type, source_identity_key
                        ORDER BY
                            COALESCE(provider_event_timestamp, fetched_at) ASC,
                            source_revision_key ASC,
                            fetched_at ASC,
                            raw_id ASC
                    ) AS prev_revision
                FROM raw_memory_revision_index
                WHERE tenant_id = :tenant_id
                  AND connection_id = :connection_id
                  AND connector = :connector
                  AND resource_type = :resource_type
                  AND source_identity_key = :source_identity_key
            )
            UPDATE raw_memory_revision_index r
            SET supersedes_source_revision_key = o.prev_revision
            FROM ordered o
            WHERE r.tenant_id = :tenant_id
              AND r.connection_id = :connection_id
              AND r.connector = :connector
              AND r.resource_type = :resource_type
              AND r.source_identity_key = :source_identity_key
              AND r.source_revision_key = o.source_revision_key
            """
        ),
        {
            "tenant_id": tenant_id,
            "connection_id": connection_id,
            "connector": connector,
            "resource_type": resource_type,
            "source_identity_key": source_identity_key,
        },
    )


def _upsert_raw_memory_revision(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    resource_type: str,
    source_identity_key: str,
    source_revision_key: str,
    run_id: uuid.UUID,
    replay_job_id: uuid.UUID | None,
    replay_version: int | None,
    raw_id: int,
    fetched_at: datetime,
    payload_body: dict[str, Any],
) -> None:
    revision_tbl = cast(Table, RawMemoryRevisionIndex.__table__)
    provider_event_timestamp = derive_provider_event_timestamp(payload_body)
    is_deleted_observed = derive_deletion_observed(payload_body)
    stmt = (
        pg_insert(revision_tbl)
        .values(
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
            resource_type=resource_type,
            source_identity_key=source_identity_key,
            source_revision_key=source_revision_key,
            raw_id=raw_id,
            provider_event_timestamp=provider_event_timestamp,
            fetched_at=fetched_at,
            supersedes_source_revision_key=None,
            is_deleted_observed=is_deleted_observed,
            run_id=run_id,
            replay_job_id=replay_job_id,
            replay_version=replay_version,
        )
        .on_conflict_do_nothing(
            index_elements=[
                "tenant_id",
                "connection_id",
                "connector",
                "resource_type",
                "source_identity_key",
                "source_revision_key",
            ],
        )
    )
    session.execute(stmt)
    _recompute_supersession_chain(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_type=resource_type,
        source_identity_key=source_identity_key,
    )


def _retention_class_for_resource(resource_type: str) -> str:
    if resource_type in {"calls.transcript", "calls.transcript_segment"}:
        return "audit_long_horizon"
    if resource_type.endswith(".scope_ping") or resource_type in {"scope_ping", "viewer_ping", "linear.viewer_ping"}:
        return "operational_replay"
    return "operational_replay"


def _upsert_raw_memory_archive_catalog(
    session: Session,
    *,
    raw_id: int,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    resource_type: str,
    source_identity_key: str,
    source_revision_key: str,
    payload_hash: str,
) -> None:
    cat_tbl = cast(Table, RawMemoryArchiveCatalog.__table__)
    ins = pg_insert(cat_tbl).values(
        raw_id=raw_id,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_type=resource_type,
        source_identity_key=source_identity_key,
        source_revision_key=source_revision_key,
        payload_hash=payload_hash,
        storage_tier="hot",
        archive_pointer=None,
        archived_at=None,
        retention_class=_retention_class_for_resource(resource_type),
        retention_policy_version=1,
        retain_until=None,
        metadata_json={},
    )
    session.execute(
        ins.on_conflict_do_update(
            index_elements=["raw_id"],
            set_={
                "payload_hash": ins.excluded.payload_hash,
                "source_revision_key": ins.excluded.source_revision_key,
                "retention_class": ins.excluded.retention_class,
            },
        )
    )


def resolve_connection(
    session: Session,
    tenant_id: uuid.UUID,
    connector_id: str,
    *,
    connection_id: uuid.UUID | None = None,
) -> TenantConnection | None:
    base_filters = (
        TenantConnection.tenant_id == tenant_id,
        TenantConnection.provider == connector_id,
        TenantConnection.status == "active",
    )
    if connection_id is not None:
        stmt = select(TenantConnection).where(*base_filters, TenantConnection.id == connection_id)
        return session.scalar(stmt)
    stmt = (
        select(TenantConnection)
        .where(*base_filters)
        .order_by(TenantConnection.created_at.desc(), TenantConnection.id.desc())
    )
    return session.scalar(stmt)


def replace_checkpoint_state(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    state: dict[str, Any],
    scope_key: str = SCOPE_DEFAULT,
) -> None:
    """Write full checkpoint state (used for operator stream reset — not deep-merge patches)."""
    from vector.domains.cortex.ingestion.checkpoint_contract import migrate_checkpoint_state

    normalized, _ = migrate_checkpoint_state(state)
    row = session.get(
        ConnectorSyncState,
        {
            "tenant_id": tenant_id,
            "connection_id": connection_id,
            "connector": connector,
            "scope_key": scope_key,
        },
    )
    if row is None:
        session.add(
            ConnectorSyncState(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=connector,
                scope_key=scope_key,
                state=normalized,
            )
        )
    else:
        row.state = normalized


def upsert_checkpoint(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    patch: dict[str, Any],
    sync_mode: str,
    scope_key: str = SCOPE_DEFAULT,
) -> None:
    # Handle unflushed/pending rows explicitly so repeated sync calls in one session
    # (e.g. replay tests) don't enqueue duplicate PK inserts before flush.
    for pending in session.new:
        if (
            isinstance(pending, ConnectorSyncState)
            and pending.tenant_id == tenant_id
            and pending.connection_id == connection_id
            and pending.connector == connector
            and pending.scope_key == scope_key
        ):
            existing = dict(pending.state) if isinstance(pending.state, dict) else {}
            pending.state = merge_monotonic_connector_state(existing, patch, sync_mode=sync_mode)
            return

    row = session.get(
        ConnectorSyncState,
        {
            "tenant_id": tenant_id,
            "connection_id": connection_id,
            "connector": connector,
            "scope_key": scope_key,
        },
    )
    if row is None:
        session.add(
            ConnectorSyncState(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=connector,
                scope_key=scope_key,
                state=merge_monotonic_connector_state({}, patch, sync_mode=sync_mode),
            )
        )
    else:
        existing = dict(row.state) if isinstance(row.state, dict) else {}
        row.state = merge_monotonic_connector_state(existing, patch, sync_mode=sync_mode)




def append_raw(
    session: Session,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    run_id: uuid.UUID,
    source_trigger: str,
    resource_type: str,
    external_id: str,
    api_endpoint: str,
    query_params: dict[str, Any],
    payload_body: dict[str, Any],
    http_status: int,
    idempotency_key: str,
) -> bool:
    """Persist one raw row.

    Step 15 semantics:
    - Live lane dedupes by logical identity+revision unique key.
    - Replay lane dedupes by (replay_job_id, idempotency_key).
    """
    body = tag_replay_payload(payload_body, ctx)
    try:
        validate_raw_payload_for_persistence(
            connector=connector,
            connection_id=connection_id,
            body=body,
        )
    except EnvelopeContractViolation as exc:
        log_ingestion_event(
            _logger,
            logging.WARNING,
            "raw envelope contract violation",
            task_name="_append_raw",
            phase=PHASE_STEP4,
            outcome="contract_violation",
            tenant_id=str(tenant_id),
            connector=connector,
            error=str(exc),
        )
        raise
    ph = hash_payload(body)
    source_identity_key = derive_source_identity_key(
        connector=connector,
        resource_type=resource_type,
        external_id=external_id[:512],
    )
    source_revision_key = derive_source_revision_key(body)
    logical_key = derive_logical_idempotency_key(
        source_identity_key=source_identity_key,
        source_revision_key=source_revision_key,
    )
    # Step 15 cutover: live lane ignores run-scoped callers and always uses logical key.
    key = logical_key[:128]
    if ctx.replay_mode and ctx.replay_job_id is not None and idempotency_key.strip():
        # Keep explicit replay overrides available for compatibility scripts; live lane never uses this path.
        key = idempotency_key[:128]
    rjid = ctx.replay_job_id if ctx.replay_mode else None
    rv = ctx.replay_version if ctx.replay_mode else None

    raw_tbl = cast(Table, RawIngestionRecord.__table__)
    observed_at = utc_now()
    if ctx.replay_mode and rjid is not None:
        stmt = (
            pg_insert(raw_tbl)
            .values(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=connector,
                resource_type=resource_type,
                external_id=external_id[:512],
                api_endpoint=api_endpoint[:512],
                query_params=query_params,
                payload_body=body,
                payload_hash=ph,
                http_status=http_status,
                fetched_at=observed_at,
                run_id=run_id,
                source_trigger=source_trigger,
                idempotency_key=key,
                source_identity_key=source_identity_key,
                source_revision_key=source_revision_key,
                replay_job_id=rjid,
                replay_version=rv,
            )
            .on_conflict_do_nothing(
                index_elements=["replay_job_id", "idempotency_key"],
                index_where=text("replay_job_id IS NOT NULL"),
            )
            .returning(raw_tbl.c.id)
        )
        # rowcount is unreliable for INSERT … ON CONFLICT DO NOTHING under psycopg; use RETURNING.
        inserted_pk = session.execute(stmt).scalar_one_or_none()
        if inserted_pk is None:
            return False
        _upsert_raw_memory_lineage(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
            resource_type=resource_type,
            source_identity_key=source_identity_key,
            source_revision_key=source_revision_key,
            payload_hash=ph,
            run_id=run_id,
            replay_job_id=rjid,
            replay_version=rv,
            raw_id=int(inserted_pk),
            fetched_at=observed_at,
        )
        _upsert_raw_memory_revision(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
            resource_type=resource_type,
            source_identity_key=source_identity_key,
            source_revision_key=source_revision_key,
            run_id=run_id,
            replay_job_id=rjid,
            replay_version=rv,
            raw_id=int(inserted_pk),
            fetched_at=observed_at,
            payload_body=body,
        )
        _upsert_raw_memory_archive_catalog(
            session,
            raw_id=int(inserted_pk),
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
            resource_type=resource_type,
            source_identity_key=source_identity_key,
            source_revision_key=source_revision_key,
            payload_hash=ph,
        )
        return True

    live_stmt = (
        pg_insert(raw_tbl)
        .values(
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
            resource_type=resource_type,
            external_id=external_id[:512],
            api_endpoint=api_endpoint[:512],
            query_params=query_params,
            payload_body=body,
            payload_hash=ph,
            http_status=http_status,
            fetched_at=observed_at,
            run_id=run_id,
            source_trigger=source_trigger,
            idempotency_key=key,
            source_identity_key=source_identity_key,
            source_revision_key=source_revision_key,
            replay_job_id=None,
            replay_version=None,
        )
        .on_conflict_do_nothing(
            index_elements=[
                "tenant_id",
                "connection_id",
                "connector",
                "resource_type",
                "source_identity_key",
                "source_revision_key",
            ],
            index_where=text("replay_job_id IS NULL"),
        )
        .returning(raw_tbl.c.id)
    )
    inserted_pk = session.execute(live_stmt).scalar_one_or_none()
    if inserted_pk is None:
        return False
    _upsert_raw_memory_lineage(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_type=resource_type,
        source_identity_key=source_identity_key,
        source_revision_key=source_revision_key,
        payload_hash=ph,
        run_id=run_id,
        replay_job_id=None,
        replay_version=None,
        raw_id=int(inserted_pk),
        fetched_at=observed_at,
    )
    _upsert_raw_memory_revision(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_type=resource_type,
        source_identity_key=source_identity_key,
        source_revision_key=source_revision_key,
        run_id=run_id,
        replay_job_id=None,
        replay_version=None,
        raw_id=int(inserted_pk),
        fetched_at=observed_at,
        payload_body=body,
    )
    _upsert_raw_memory_archive_catalog(
        session,
        raw_id=int(inserted_pk),
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_type=resource_type,
        source_identity_key=source_identity_key,
        source_revision_key=source_revision_key,
        payload_hash=ph,
    )
    return True


def read_checkpoint_state(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    scope_key: str,
) -> dict[str, Any]:
    stmt = select(ConnectorSyncState).where(
        ConnectorSyncState.tenant_id == tenant_id,
        ConnectorSyncState.connection_id == connection_id,
        ConnectorSyncState.connector == connector,
        ConnectorSyncState.scope_key == scope_key,
    )
    row = session.scalar(stmt)
    if row is None or not isinstance(row.state, dict):
        return {}
    return dict(row.state)


def checkpoint_streams_for_mode(existing_ckpt: dict[str, Any], sync_mode: str) -> dict[str, Any]:
    """Read stream checkpoint state for a sync mode.

    Supports both legacy top-level ``streams`` and nested
    ``modes.<incremental|backfill>.streams`` checkpoint layouts.
    """
    mode_bucket = "backfill" if sync_mode == "backfill" else "incremental"
    modes = existing_ckpt.get("modes")
    if isinstance(modes, dict):
        mode_state = modes.get(mode_bucket)
        if isinstance(mode_state, dict):
            mode_streams = mode_state.get("streams")
            if isinstance(mode_streams, dict):
                return mode_streams
    legacy_streams = existing_ckpt.get("streams")
    return legacy_streams if isinstance(legacy_streams, dict) else {}

def generic_scope_ping(
    session: Session,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    run_id: uuid.UUID,
    source_trigger: str,
    label: str,
) -> int:
    scope_ck = ctx.checkpoint_scope_key()
    body = {
        **core_envelope_fields(
            connector=connector,
            connection_id=connection_id,
            source_object_type=f"{connector}.connector_health",
            source_object_id=str(connection_id),
        ),
        "scope_ping": True,
        "label": label,
    }
    ins = int(
        append_raw(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type=f"{connector}.scope_ping",
            external_id=str(connection_id),
            api_endpoint=f"internal://{connector}/scope_ping",
            query_params={},
            payload_body=body,
            http_status=200,
            idempotency_key=idem_key(ctx, run_id, f"{connector}:ping"),
        )
    )
    upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": utc_now().isoformat(),
            "ping": True,
            "streams": {
                connector: {
                    "scope_ping": {
                        "cursor_owner": f"{connector}.scope_ping",
                        "last_label": label[:128],
                    }
                }
            },
        },
        sync_mode=ctx.checkpoint_sync_mode,
    )
    return ins
