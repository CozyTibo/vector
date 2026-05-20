"""Phase 01 Step 1–3 — connector sync execution (run + raw persistence + checkpoint + replay)."""

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


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _idem_key(ctx: IngestionSyncContext, run_id: uuid.UUID, base: str) -> str:
    """Stable idempotency suffix for replay (same ``replay_job_id`` → same key across runs)."""
    if ctx.replay_mode and ctx.replay_job_id is not None:
        key = f"{base}:rj:{ctx.replay_job_id}"
    else:
        key = f"{base}:{run_id}"
    return key[:128]


def _tag_replay_payload(body: dict[str, Any], ctx: IngestionSyncContext) -> dict[str, Any]:
    if not ctx.replay_mode or ctx.replay_job_id is None:
        return dict(body)
    out = dict(body)
    out["cortex_replay_metadata"] = {
        "replay_job_id": str(ctx.replay_job_id),
        "replay_version": ctx.replay_version,
        "sync_mode": ctx.sync_mode,
    }
    return out


def _hash_payload(body: dict[str, Any]) -> str:
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


def _resolve_connection(
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


def _upsert_checkpoint(
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


def ensure_github_workflow_run_repository_metadata(
    run: Mapping[str, Any],
    *,
    installation_repository: Mapping[str, Any],
    repository_full_name: str,
) -> dict[str, Any]:
    """Merge durable repository identity onto a workflow run dict before raw persistence.

    GitHub's ``GET /repos/{owner}/{repo}/actions/runs`` list payload sometimes omits the nested
    ``repository`` object (or returns it without ``id`` / ``full_name``). The sync loop already
    holds the authoritative installation repository record for ``repository_full_name`` — merge
    that truth so canonical materialization has stable ``repository_provider_id`` inputs without
    inventing identifiers: values come from the installation ``repositories`` payload or the
    known ``owner/repo`` pair for this fetch.
    """
    wr = dict(run)
    api_repo = wr.get("repository")
    merged: dict[str, Any] = dict(api_repo) if isinstance(api_repo, dict) else {}
    inst = dict(installation_repository) if isinstance(installation_repository, dict) else {}
    fn = repository_full_name.strip()

    fn_ok = isinstance(merged.get("full_name"), str) and "/" in merged["full_name"].strip()
    if not fn_ok and "/" in fn:
        merged["full_name"] = fn

    rid = merged.get("id")
    has_numeric_id = isinstance(rid, int) or (isinstance(rid, str) and rid.strip().isdigit())
    if not has_numeric_id:
        inst_id = inst.get("id")
        if isinstance(inst_id, int):
            merged["id"] = inst_id
        elif isinstance(inst_id, str) and inst_id.strip().isdigit():
            merged["id"] = int(inst_id.strip())

    if not isinstance(merged.get("name"), str) or not merged["name"].strip():
        if "/" in fn:
            merged["name"] = fn.split("/", 1)[1].strip()
        elif fn:
            merged["name"] = fn

    own = merged.get("owner")
    if not isinstance(own, dict) or not isinstance(own.get("login"), str) or not str(own.get("login", "")).strip():
        inst_owner = inst.get("owner")
        if isinstance(inst_owner, dict) and isinstance(inst_owner.get("login"), str):
            merged["owner"] = dict(inst_owner)
        elif "/" in fn:
            merged["owner"] = {"login": fn.split("/", 1)[0].strip()}

    wr["repository"] = merged
    return wr


def _append_raw(
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
    body = _tag_replay_payload(payload_body, ctx)
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
    ph = _hash_payload(body)
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
    observed_at = _utc_now()
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


def _calls_transcript_segment_sort_key(seg: dict[str, Any]) -> tuple[Any, ...]:
    for k in ("segment_index", "ord", "index", "idx"):
        v = seg.get(k)
        if isinstance(v, int):
            return (0, v, "")
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            return (0, int(v.strip()), "")
    for k in ("start_ms", "offset_ms", "offset", "startOffset", "start_time_ms", "start"):
        v = seg.get(k)
        if isinstance(v, (int, float)):
            return (1, float(v), k)
        if isinstance(v, str) and v.strip():
            try:
                return (1, float(v.strip()), k)
            except ValueError:
                pass
    txt = seg.get("text") if isinstance(seg.get("text"), str) else seg.get("body")
    return (2, str(txt or ""), "")


def _github_sync(
    session: Session,
    settings: Settings,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    scope_ck = ctx.checkpoint_scope_key()
    existing_ckpt = _read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_GITHUB,
        scope_key=scope_ck,
    )
    link = gh_repo.get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        ins = int(
            _append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_GITHUB,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="github.sync",
                external_id="missing-github-detail",
                api_endpoint="internal://github/no-detail",
                query_params={},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.connection",
                        source_object_id="github_connection_detail_missing",
                    ),
                    "ingestion_error": {"code": "github_connection_detail_missing"},
                },
                http_status=503,
                idempotency_key=_idem_key(ctx, run_id, "github:no-detail"),
            )
        )
        _upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            scope_key=scope_ck,
            patch={
                "last_incremental_at": _utc_now().isoformat(),
                "repos_fetched": 0,
                "streams": {
                    "github": {
                        "installation_repositories": {
                            "cursor_owner": "github.installation_repositories",
                            "last_status": "missing_connection_detail",
                        }
                    }
                },
            },
            sync_mode=ctx.sync_mode,
        )
        return ins
    try:
        token = create_github_installation_access_token(settings, link.installation_id)
    except GitHubApiError as e:
        ins = int(
            _append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_GITHUB,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="github.installation_repositories",
                external_id="fetch_error",
                api_endpoint=f"{settings.github_rest_api_base_url().rstrip('/')}/installation/repositories",
                query_params={"error": True},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.installation_repositories",
                        source_object_id="fetch_error",
                    ),
                    "ingestion_error": {"code": "github_api_error", "message": str(e)},
                },
                http_status=502,
                idempotency_key=_idem_key(ctx, run_id, "github:fetch_error"),
            )
        )
        _upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            scope_key=scope_ck,
            patch={
                "last_incremental_at": _utc_now().isoformat(),
                "repos_fetched": 0,
                "streams": {
                    "github": {
                        "installation_repositories": {
                            "cursor_owner": "github.installation_repositories",
                            "last_status": "token_fetch_error",
                        }
                    }
                },
            },
            sync_mode=ctx.sync_mode,
        )
        return ins

    n_ins = 0
    collected: list[tuple[str, str, dict[str, Any]]] = []
    total_hint: int | None = None
    pages_fetched = 0
    per_page = 100
    max_pages = settings.cortex_github_installation_repos_max_pages
    page = 1
    try:
        while page <= max_pages:
            repos, page_total = list_installation_repositories_page(
                settings,
                token,
                page=page,
                per_page=per_page,
            )
            if total_hint is None and page_total is not None:
                total_hint = page_total
            if not repos:
                break
            for repo in repos:
                rid = repo.get("id")
                rid_s = str(rid) if rid is not None else ""
                fn = repo.get("full_name") or rid_s
                body = {
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.repository",
                        source_object_id=rid_s or fn[:512],
                    ),
                    "payload_hash_basis": "github_rest_repo_record_v1",
                    "repository": repo,
                }
                base = f"github:repo:{rid_s}" if rid_s else f"github:repo:{fn[:200]}"
                if _append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_GITHUB,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="github.repository",
                    external_id=rid_s or fn[:512],
                    api_endpoint=f"{settings.github_rest_api_base_url().rstrip('/')}/installation/repositories",
                    query_params={"page": page, "per_page": per_page},
                    payload_body=body,
                    http_status=200,
                    idempotency_key=_idem_key(ctx, run_id, base),
                ):
                    n_ins += 1
                if isinstance(fn, str) and "/" in fn.strip():
                    collected.append((rid_s, fn.strip(), repo))
            pages_fetched += 1
            if len(repos) < per_page:
                break
            page += 1
    except GitHubApiError as e:
        ins = int(
            _append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_GITHUB,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="github.installation_repositories",
                external_id=f"page_{page}_error",
                api_endpoint=f"{settings.github_rest_api_base_url().rstrip('/')}/installation/repositories",
                query_params={"page": page, "error": True},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_GITHUB,
                        connection_id=connection_id,
                        source_object_type="github.installation_repositories",
                        source_object_id=f"page_{page}_error",
                    ),
                    "ingestion_error": {"code": "github_api_error", "message": str(e)},
                },
                http_status=502,
                idempotency_key=_idem_key(ctx, run_id, f"github:page_error:{page}"),
            )
        )
        _upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            scope_key=scope_ck,
            patch={
                "last_incremental_at": _utc_now().isoformat(),
                "repos_fetched": n_ins,
                "github_installation_repos_pages": pages_fetched,
                "total_count_hint": total_hint,
                "streams": {
                    "github": {
                        "installation_repositories": {
                            "cursor_owner": "github.installation_repositories",
                            "last_page": pages_fetched,
                        }
                    }
                },
            },
            sync_mode=ctx.sync_mode,
        )
        return ins

    streams_existing = _checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    github_existing = (
        streams_existing.get("github")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("github"), dict)
        else {}
    )
    repos_existing = (
        github_existing.get("repos")
        if isinstance(github_existing, dict) and isinstance(github_existing.get("repos"), dict)
        else {}
    )
    repo_ring_raw = github_existing.get("repo_ring_index") if isinstance(github_existing, dict) else 0
    try:
        repo_ring_index = int(repo_ring_raw)
    except (TypeError, ValueError):
        repo_ring_index = 0

    selected_repos, next_repo_ring_index = _pick_github_repos_round_robin(
        collected,
        ring_index=repo_ring_index,
        count=settings.cortex_github_pr_fetch_max_repos,
    )
    gh_base = settings.github_rest_api_base_url().rstrip("/")
    pr_per_repo = settings.cortex_github_prs_per_repo
    pr_rows = 0
    review_rows = 0
    review_comment_rows = 0
    issue_comment_rows = 0
    commit_rows = 0
    check_run_rows = 0
    workflow_rows = 0
    deployment_rows = 0
    deployment_status_rows = 0
    branch_rows = 0
    tag_rows = 0
    check_suite_rows = 0
    release_rows = 0
    issue_rows = 0
    commit_comment_rows = 0
    review_thread_rows = 0
    issue_timeline_rows = 0
    pr_timeline_rows = 0
    budget_exhausted = False
    start_t = time.monotonic()
    repo_patch_map: dict[str, Any] = {}

    for _rid_s, fn, _repo in selected_repos:
        parts = fn.split("/", 1)
        if len(parts) != 2:
            continue
        owner, repo_name = parts[0], parts[1]
        existing_repo = repos_existing.get(fn) if isinstance(repos_existing, dict) else None
        if not isinstance(existing_repo, dict):
            existing_repo = {}

        repo_pr_rows = 0
        repo_review_rows = 0
        repo_review_comment_rows = 0
        repo_issue_comment_rows = 0
        repo_commit_rows = 0
        repo_check_rows = 0
        repo_workflow_rows = 0
        repo_deploy_rows = 0
        repo_deploy_status_rows = 0
        repo_branch_rows = 0
        repo_tag_rows = 0
        repo_check_suite_rows = 0
        repo_release_rows = 0
        repo_issue_rows = 0
        repo_commit_comment_rows = 0
        repo_review_thread_rows = 0
        repo_issue_timeline_rows = 0
        repo_pr_timeline_rows = 0
        emitted_check_suite_ids: set[int] = set()

        pull_state = existing_repo.get("pull_requests") if isinstance(existing_repo.get("pull_requests"), dict) else {}
        pulls_next_page_raw = pull_state.get("next_page", 1)
        try:
            pulls_next_page = max(1, int(pulls_next_page_raw))
        except (TypeError, ValueError):
            pulls_next_page = 1
        current_pulls_page = pulls_next_page
        pull_heads: list[tuple[int, str]] = []
        pulls_complete = False
        pull_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_prs_max_pages_per_repo):
                pulls = list_repo_pulls_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=current_pulls_page,
                    per_page=pr_per_repo,
                    state="all",
                )
                pull_pages_fetched += 1
                for pr in pulls:
                    num = pr.get("number")
                    if not isinstance(num, int):
                        continue
                    pr_ext = f"{fn}#{num}"[:512]
                    pr_body = {
                        **core_envelope_fields(
                            connector=CONNECTION_PROVIDER_GITHUB,
                            connection_id=connection_id,
                            source_object_type="github.pull_request",
                            source_object_id=pr_ext,
                        ),
                        "pull_request": pr,
                        "paging": {"page": current_pulls_page, "mode": ctx.sync_mode},
                    }
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.pull_request",
                        external_id=pr_ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/pulls",
                        query_params={"state": "all", "per_page": pr_per_repo, "page": current_pulls_page},
                        payload_body=pr_body,
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:pr:{pr_ext}"),
                    ):
                        n_ins += 1
                        pr_rows += 1
                        repo_pr_rows += 1
                    head = pr.get("head")
                    if isinstance(head, dict):
                        sha = head.get("sha")
                        if isinstance(sha, str) and sha:
                            pull_heads.append((num, sha))

                    # PR reviews
                    try:
                        for review_page in range(1, settings.cortex_github_reviews_max_pages_per_pr + 1):
                            reviews = list_pull_reviews_page(
                                settings,
                                token,
                                owner=owner,
                                repo=repo_name,
                                pull_number=num,
                                page=review_page,
                            )
                            for review in reviews:
                                rid = review.get("id")
                                if rid is None:
                                    continue
                                ext = f"{pr_ext}:review:{rid}"[:512]
                                if _append_raw(
                                    session,
                                    ctx=ctx,
                                    tenant_id=tenant_id,
                                    connection_id=connection_id,
                                    connector=CONNECTION_PROVIDER_GITHUB,
                                    run_id=run_id,
                                    source_trigger=source_trigger,
                                    resource_type="github.pull_request_review",
                                    external_id=ext,
                                    api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/pulls/{num}/reviews",
                                    query_params={"page": review_page},
                                    payload_body={
                                        **core_envelope_fields(
                                            connector=CONNECTION_PROVIDER_GITHUB,
                                            connection_id=connection_id,
                                            source_object_type="github.pull_request_review",
                                            source_object_id=ext,
                                        ),
                                        "pull_request_number": num,
                                        "github_pull_request_id": pr.get("id"),
                                        "review": review,
                                    },
                                    http_status=200,
                                    idempotency_key=_idem_key(ctx, run_id, f"github:pr_review:{ext}"),
                                ):
                                    n_ins += 1
                                    review_rows += 1
                                    repo_review_rows += 1
                            if len(reviews) < 100:
                                break
                    except GitHubApiError:
                        pass

                    # PR review comments (+ deterministic review thread roots)
                    try:
                        all_review_comments: list[dict[str, Any]] = []
                        for rc_page in range(1, settings.cortex_github_review_comments_max_pages_per_pr + 1):
                            review_comments = list_pull_review_comments_page(
                                settings,
                                token,
                                owner=owner,
                                repo=repo_name,
                                pull_number=num,
                                page=rc_page,
                            )
                            all_review_comments.extend([x for x in review_comments if isinstance(x, dict)])
                            if len(review_comments) < 100:
                                break

                        by_id: dict[int, dict[str, Any]] = {}
                        for rc in all_review_comments:
                            raw_id = rc.get("id")
                            nid: int | None
                            if isinstance(raw_id, int):
                                nid = raw_id
                            elif isinstance(raw_id, str) and raw_id.strip().isdigit():
                                nid = int(raw_id.strip())
                            else:
                                nid = None
                            if nid is not None:
                                by_id[nid] = rc

                        def _review_comment_root_id(comment_id: int) -> int:
                            seen: set[int] = set()
                            cur: int | None = comment_id
                            while cur is not None:
                                if cur in seen:
                                    return cur
                                seen.add(cur)
                                c = by_id.get(cur)
                                if c is None:
                                    return cur
                                parent_raw = c.get("in_reply_to_id")
                                if parent_raw is None:
                                    return cur
                                if isinstance(parent_raw, int):
                                    cur = parent_raw
                                elif isinstance(parent_raw, str) and parent_raw.strip().isdigit():
                                    cur = int(parent_raw.strip())
                                else:
                                    return cur
                            return comment_id

                        thread_roots = {
                            _review_comment_root_id(nid)
                            for nid in by_id
                        }
                        for root_id in sorted(thread_roots):
                            rt_ext = f"{pr_ext}:review_thread:{root_id}"[:512]
                            if _append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_GITHUB,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="github.review_thread",
                                external_id=rt_ext,
                                api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/pulls/{num}/comments",
                                query_params={"thread_roots": len(thread_roots)},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        connection_id=connection_id,
                                        source_object_type="github.review_thread",
                                        source_object_id=rt_ext,
                                    ),
                                    "pull_request_number": num,
                                    "thread_id": root_id,
                                },
                                http_status=200,
                                idempotency_key=_idem_key(ctx, run_id, f"github:review_thread:{rt_ext}"),
                            ):
                                n_ins += 1
                                review_thread_rows += 1
                                repo_review_thread_rows += 1

                        for rc in all_review_comments:
                            cid = rc.get("id")
                            if cid is None:
                                continue
                            ext = f"{pr_ext}:review_comment:{cid}"[:512]
                            if _append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_GITHUB,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="github.pull_request_review_comment",
                                external_id=ext,
                                api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/pulls/{num}/comments",
                                query_params={},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        connection_id=connection_id,
                                        source_object_type="github.pull_request_review_comment",
                                        source_object_id=ext,
                                    ),
                                    "pull_request_number": num,
                                    "comment": rc,
                                },
                                http_status=200,
                                idempotency_key=_idem_key(ctx, run_id, f"github:pr_review_comment:{ext}"),
                            ):
                                n_ins += 1
                                review_comment_rows += 1
                                repo_review_comment_rows += 1
                    except GitHubApiError:
                        pass

                    # PR issue comments
                    try:
                        for ic_page in range(1, settings.cortex_github_issue_comments_max_pages_per_pr + 1):
                            issue_comments = list_pull_issue_comments_page(
                                settings,
                                token,
                                owner=owner,
                                repo=repo_name,
                                pull_number=num,
                                page=ic_page,
                            )
                            for ic in issue_comments:
                                cid = ic.get("id")
                                if cid is None:
                                    continue
                                ext = f"{pr_ext}:issue_comment:{cid}"[:512]
                                if _append_raw(
                                    session,
                                    ctx=ctx,
                                    tenant_id=tenant_id,
                                    connection_id=connection_id,
                                    connector=CONNECTION_PROVIDER_GITHUB,
                                    run_id=run_id,
                                    source_trigger=source_trigger,
                                    resource_type="github.issue_comment",
                                    external_id=ext,
                                    api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/issues/{num}/comments",
                                    query_params={"page": ic_page},
                                    payload_body={
                                        **core_envelope_fields(
                                            connector=CONNECTION_PROVIDER_GITHUB,
                                            connection_id=connection_id,
                                            source_object_type="github.issue_comment",
                                            source_object_id=ext,
                                        ),
                                        "pull_request_number": num,
                                        "comment": ic,
                                    },
                                    http_status=200,
                                    idempotency_key=_idem_key(ctx, run_id, f"github:issue_comment:{ext}"),
                                ):
                                    n_ins += 1
                                    issue_comment_rows += 1
                                    repo_issue_comment_rows += 1
                            if len(issue_comments) < 100:
                                break
                    except GitHubApiError:
                        pass

                    # PR timeline (REST `/issues/{n}/timeline` — issue number equals PR number)
                    pr_gid = pr.get("id")
                    if isinstance(pr_gid, int) and isinstance(num, int):
                        try:
                            for tl_page in range(1, settings.cortex_github_timeline_max_pages_per_issue_or_pr + 1):
                                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                                    budget_exhausted = True
                                    break
                                timeline = list_repo_issue_timeline_page(
                                    settings,
                                    token,
                                    owner=owner,
                                    repo=repo_name,
                                    issue_number=num,
                                    page=tl_page,
                                )
                                for te in timeline:
                                    if not isinstance(te, dict):
                                        continue
                                    te_id = te.get("id")
                                    if te_id is None:
                                        continue
                                    tl_ext = f"{pr_ext}:timeline_event:{te_id}"[:512]
                                    ts = te.get("created_at")
                                    ts_str = ts if isinstance(ts, str) else None
                                    if _append_raw(
                                        session,
                                        ctx=ctx,
                                        tenant_id=tenant_id,
                                        connection_id=connection_id,
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        run_id=run_id,
                                        source_trigger=source_trigger,
                                        resource_type="github.pull_request_timeline_event",
                                        external_id=tl_ext,
                                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/issues/{num}/timeline",
                                        query_params={"page": tl_page},
                                        payload_body={
                                            **core_envelope_fields(
                                                connector=CONNECTION_PROVIDER_GITHUB,
                                                connection_id=connection_id,
                                                source_object_type="github.pull_request_timeline_event",
                                                source_object_id=tl_ext,
                                            ),
                                            "id": te_id,
                                            "repository_full_name": fn,
                                            "pull_request_external_ref": pr_ext,
                                            "pull_request_number": num,
                                            "github_pull_request_id": pr_gid,
                                            "timeline_event": te,
                                            "provider_event_timestamp": ts_str,
                                        },
                                        http_status=200,
                                        idempotency_key=_idem_key(ctx, run_id, f"github:pr_timeline:{tl_ext}"),
                                    ):
                                        n_ins += 1
                                        pr_timeline_rows += 1
                                        repo_pr_timeline_rows += 1
                                if len(timeline) < 100:
                                    break
                        except GitHubApiError:
                            pass

                if len(pulls) < pr_per_repo:
                    pulls_complete = True
                    current_pulls_page = 1
                    break
                current_pulls_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Commits
        commit_state = existing_repo.get("commits") if isinstance(existing_repo.get("commits"), dict) else {}
        commit_page_raw = commit_state.get("next_page", 1)
        try:
            commit_page = max(1, int(commit_page_raw))
        except (TypeError, ValueError):
            commit_page = 1
        commits_complete = False
        commit_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_commits_max_pages_per_repo):
                commits = list_repo_commits_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=commit_page,
                )
                commit_pages_fetched += 1
                for commit in commits:
                    sha = commit.get("sha")
                    if not isinstance(sha, str) or not sha:
                        continue
                    ext = f"{fn}:{sha}"[:512]
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.commit",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/commits",
                        query_params={"page": commit_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.commit",
                                source_object_id=ext,
                            ),
                            "commit": commit,
                        },
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:commit:{ext}"),
                    ):
                        n_ins += 1
                        commit_rows += 1
                        repo_commit_rows += 1
                if len(commits) < 100:
                    commits_complete = True
                    commit_page = 1
                    break
                commit_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Check runs for PR heads
        for pr_num, sha in pull_heads:
            try:
                for check_page in range(1, settings.cortex_github_check_runs_max_pages_per_pr + 1):
                    check_runs, _ = list_repo_check_runs_page(
                        settings,
                        token,
                        owner=owner,
                        repo=repo_name,
                        ref=sha,
                        page=check_page,
                    )
                    for cr in check_runs:
                        cid = cr.get("id")
                        if cid is None:
                            continue
                        ext = f"{fn}:{sha}:check:{cid}"[:512]
                        if _append_raw(
                            session,
                            ctx=ctx,
                            tenant_id=tenant_id,
                            connection_id=connection_id,
                            connector=CONNECTION_PROVIDER_GITHUB,
                            run_id=run_id,
                            source_trigger=source_trigger,
                            resource_type="github.check_run",
                            external_id=ext,
                            api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/commits/{sha}/check-runs",
                            query_params={"page": check_page, "pull_number": pr_num},
                            payload_body={
                                **core_envelope_fields(
                                    connector=CONNECTION_PROVIDER_GITHUB,
                                    connection_id=connection_id,
                                    source_object_type="github.check_run",
                                    source_object_id=ext,
                                ),
                                "pull_request_number": pr_num,
                                "head_sha": sha,
                                "check_run": cr,
                            },
                            http_status=200,
                            idempotency_key=_idem_key(ctx, run_id, f"github:check_run:{ext}"),
                        ):
                            n_ins += 1
                            check_run_rows += 1
                            repo_check_rows += 1
                        suite_obj = cr.get("check_suite") if isinstance(cr.get("check_suite"), dict) else {}
                        suite_raw = suite_obj.get("id")
                        suite_id: int | None
                        if isinstance(suite_raw, int):
                            suite_id = suite_raw
                        elif isinstance(suite_raw, str) and suite_raw.strip().isdigit():
                            suite_id = int(suite_raw.strip())
                        else:
                            suite_id = None
                        if suite_id is not None and suite_id not in emitted_check_suite_ids:
                            emitted_check_suite_ids.add(suite_id)
                            suite_payload = dict(suite_obj)
                            if not isinstance(suite_payload.get("repository"), dict):
                                suite_payload["repository"] = {"full_name": fn}
                            suite_ext = f"{fn}:check_suite:{suite_id}"[:512]
                            if _append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_GITHUB,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="github.check_suite",
                                external_id=suite_ext,
                                api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/commits/{sha}/check-runs",
                                query_params={"suite": suite_id},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        connection_id=connection_id,
                                        source_object_type="github.check_suite",
                                        source_object_id=suite_ext,
                                    ),
                                    "check_suite": suite_payload,
                                },
                                http_status=200,
                                idempotency_key=_idem_key(ctx, run_id, f"github:check_suite:{suite_ext}"),
                            ):
                                n_ins += 1
                                check_suite_rows += 1
                                repo_check_suite_rows += 1
                    if len(check_runs) < 100:
                        break
            except GitHubApiError:
                continue

        # Workflows
        workflow_state = (
            existing_repo.get("workflow_runs")
            if isinstance(existing_repo.get("workflow_runs"), dict)
            else {}
        )
        workflow_page_raw = workflow_state.get("next_page", 1)
        try:
            workflow_page = max(1, int(workflow_page_raw))
        except (TypeError, ValueError):
            workflow_page = 1
        workflow_complete = False
        workflow_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_workflow_runs_max_pages_per_repo):
                runs, _ = list_repo_workflow_runs_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=workflow_page,
                )
                workflow_pages_fetched += 1
                for run in runs:
                    rid = run.get("id")
                    if rid is None:
                        continue
                    ext = f"{fn}:workflow_run:{rid}"[:512]
                    run_for_raw = ensure_github_workflow_run_repository_metadata(
                        run,
                        installation_repository=_repo,
                        repository_full_name=fn,
                    )
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.workflow_run",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/actions/runs",
                        query_params={"page": workflow_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.workflow_run",
                                source_object_id=ext,
                            ),
                            "workflow_run": run_for_raw,
                        },
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:workflow_run:{ext}"),
                    ):
                        n_ins += 1
                        workflow_rows += 1
                        repo_workflow_rows += 1
                if len(runs) < 100:
                    workflow_complete = True
                    workflow_page = 1
                    break
                workflow_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Deployments + statuses
        deployment_state = (
            existing_repo.get("deployments")
            if isinstance(existing_repo.get("deployments"), dict)
            else {}
        )
        deployment_page_raw = deployment_state.get("next_page", 1)
        try:
            deployment_page = max(1, int(deployment_page_raw))
        except (TypeError, ValueError):
            deployment_page = 1
        deployment_complete = False
        deployment_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_deployments_max_pages_per_repo):
                deployments = list_repo_deployments_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=deployment_page,
                )
                deployment_pages_fetched += 1
                for dep in deployments:
                    did = dep.get("id")
                    if not isinstance(did, int):
                        continue
                    dep_ext = f"{fn}:deployment:{did}"[:512]
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.deployment",
                        external_id=dep_ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/deployments",
                        query_params={"page": deployment_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.deployment",
                                source_object_id=dep_ext,
                            ),
                            "deployment": dep,
                        },
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:deployment:{dep_ext}"),
                    ):
                        n_ins += 1
                        deployment_rows += 1
                        repo_deploy_rows += 1
                    try:
                        for dstat_page in range(
                            1, settings.cortex_github_deployment_statuses_max_pages_per_deployment + 1
                        ):
                            statuses = list_deployment_statuses_page(
                                settings,
                                token,
                                owner=owner,
                                repo=repo_name,
                                deployment_id=did,
                                page=dstat_page,
                            )
                            for st in statuses:
                                sid = st.get("id")
                                if sid is None:
                                    continue
                                ext = f"{dep_ext}:status:{sid}"[:512]
                                if _append_raw(
                                    session,
                                    ctx=ctx,
                                    tenant_id=tenant_id,
                                    connection_id=connection_id,
                                    connector=CONNECTION_PROVIDER_GITHUB,
                                    run_id=run_id,
                                    source_trigger=source_trigger,
                                    resource_type="github.deployment_status",
                                    external_id=ext,
                                    api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/deployments/{did}/statuses",
                                    query_params={"page": dstat_page},
                                    payload_body={
                                        **core_envelope_fields(
                                            connector=CONNECTION_PROVIDER_GITHUB,
                                            connection_id=connection_id,
                                            source_object_type="github.deployment_status",
                                            source_object_id=ext,
                                        ),
                                        "deployment_id": did,
                                        "status": st,
                                    },
                                    http_status=200,
                                    idempotency_key=_idem_key(ctx, run_id, f"github:deployment_status:{ext}"),
                                ):
                                    n_ins += 1
                                    deployment_status_rows += 1
                                    repo_deploy_status_rows += 1
                            if len(statuses) < 100:
                                break
                    except GitHubApiError:
                        pass
                if len(deployments) < 100:
                    deployment_complete = True
                    deployment_page = 1
                    break
                deployment_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Branches
        branch_state = existing_repo.get("branches") if isinstance(existing_repo.get("branches"), dict) else {}
        branch_page_raw = branch_state.get("next_page", 1)
        try:
            branch_page = max(1, int(branch_page_raw))
        except (TypeError, ValueError):
            branch_page = 1
        branch_complete = False
        branch_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_branches_max_pages_per_repo):
                branches = list_repo_branches_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=branch_page,
                )
                branch_pages_fetched += 1
                for br in branches:
                    nm = br.get("name")
                    if not isinstance(nm, str) or not nm:
                        continue
                    ext = f"{fn}:branch:{nm}"[:512]
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.branch",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/branches",
                        query_params={"page": branch_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.branch",
                                source_object_id=ext,
                            ),
                            "branch": br,
                        },
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:branch:{ext}"),
                    ):
                        n_ins += 1
                        branch_rows += 1
                        repo_branch_rows += 1
                if len(branches) < 100:
                    branch_complete = True
                    branch_page = 1
                    break
                branch_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Tags
        tag_state = existing_repo.get("tags") if isinstance(existing_repo.get("tags"), dict) else {}
        tag_page_raw = tag_state.get("next_page", 1)
        try:
            tag_page = max(1, int(tag_page_raw))
        except (TypeError, ValueError):
            tag_page = 1
        tag_complete = False
        tag_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_tags_max_pages_per_repo):
                tags = list_repo_tags_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=tag_page,
                )
                tag_pages_fetched += 1
                for tag in tags:
                    nm = tag.get("name")
                    if not isinstance(nm, str) or not nm:
                        continue
                    ext = f"{fn}:tag:{nm}"[:512]
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.tag",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/tags",
                        query_params={"page": tag_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.tag",
                                source_object_id=ext,
                            ),
                            "tag": tag,
                        },
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:tag:{ext}"),
                    ):
                        n_ins += 1
                        tag_rows += 1
                        repo_tag_rows += 1
                if len(tags) < 100:
                    tag_complete = True
                    tag_page = 1
                    break
                tag_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Repo-wide commit comments (distinct from PR review comments)
        cc_state = (
            existing_repo.get("commit_comments")
            if isinstance(existing_repo.get("commit_comments"), dict)
            else {}
        )
        cc_page_raw = cc_state.get("next_page", 1)
        try:
            cc_page = max(1, int(cc_page_raw))
        except (TypeError, ValueError):
            cc_page = 1
        cc_complete = False
        cc_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_commit_comments_max_pages_per_repo):
                cc_items = list_repo_commit_comments_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=cc_page,
                )
                cc_pages_fetched += 1
                for cc in cc_items:
                    cid = cc.get("id")
                    if cid is None:
                        continue
                    sha = cc.get("commit_id")
                    if not isinstance(sha, str) or not sha:
                        continue
                    ext = f"{fn}:commit_comment:{cid}"[:512]
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.commit_comment",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/comments",
                        query_params={"page": cc_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.commit_comment",
                                source_object_id=ext,
                            ),
                            "commit_sha": sha,
                            "comment": cc,
                        },
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:commit_comment:{ext}"),
                    ):
                        n_ins += 1
                        commit_comment_rows += 1
                        repo_commit_comment_rows += 1
                if len(cc_items) < 100:
                    cc_complete = True
                    cc_page = 1
                    break
                cc_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # GitHub issues (REST `/issues`; skips pull requests surfaced in that listing)
        iss_state = existing_repo.get("issues") if isinstance(existing_repo.get("issues"), dict) else {}
        iss_page_raw = iss_state.get("next_page", 1)
        try:
            iss_page = max(1, int(iss_page_raw))
        except (TypeError, ValueError):
            iss_page = 1
        iss_complete = False
        iss_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_issues_max_pages_per_repo):
                iss_items = list_repo_issues_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=iss_page,
                )
                iss_pages_fetched += 1
                for issue_row in iss_items:
                    if not isinstance(issue_row, dict):
                        continue
                    if isinstance(issue_row.get("pull_request"), dict):
                        continue
                    iid = issue_row.get("id")
                    if iid is None:
                        continue
                    ext = f"{fn}:issue:{iid}"[:512]
                    issue_body = dict(issue_row)
                    if not isinstance(issue_body.get("repository"), dict):
                        issue_body["repository"] = {"full_name": fn}
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.issue",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/issues",
                        query_params={"page": iss_page, "state": "all"},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.issue",
                                source_object_id=ext,
                            ),
                            "issue": issue_body,
                        },
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:issue:{ext}"),
                    ):
                        n_ins += 1
                        issue_rows += 1
                        repo_issue_rows += 1
                    inum = issue_row.get("number")
                    if isinstance(inum, int) and isinstance(iid, int):
                        try:
                            for tl_page in range(1, settings.cortex_github_timeline_max_pages_per_issue_or_pr + 1):
                                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                                    budget_exhausted = True
                                    break
                                timeline = list_repo_issue_timeline_page(
                                    settings,
                                    token,
                                    owner=owner,
                                    repo=repo_name,
                                    issue_number=inum,
                                    page=tl_page,
                                )
                                for te in timeline:
                                    if not isinstance(te, dict):
                                        continue
                                    te_id = te.get("id")
                                    if te_id is None:
                                        continue
                                    tl_ext = f"{fn}:issue:{iid}:timeline_event:{te_id}"[:512]
                                    ts = te.get("created_at")
                                    ts_str = ts if isinstance(ts, str) else None
                                    if _append_raw(
                                        session,
                                        ctx=ctx,
                                        tenant_id=tenant_id,
                                        connection_id=connection_id,
                                        connector=CONNECTION_PROVIDER_GITHUB,
                                        run_id=run_id,
                                        source_trigger=source_trigger,
                                        resource_type="github.issue_timeline_event",
                                        external_id=tl_ext,
                                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/issues/{inum}/timeline",
                                        query_params={"page": tl_page},
                                        payload_body={
                                            **core_envelope_fields(
                                                connector=CONNECTION_PROVIDER_GITHUB,
                                                connection_id=connection_id,
                                                source_object_type="github.issue_timeline_event",
                                                source_object_id=tl_ext,
                                            ),
                                            "id": te_id,
                                            "repository_full_name": fn,
                                            "issue_number": inum,
                                            "github_issue_id": iid,
                                            "timeline_event": te,
                                            "provider_event_timestamp": ts_str,
                                        },
                                        http_status=200,
                                        idempotency_key=_idem_key(ctx, run_id, f"github:issue_timeline:{tl_ext}"),
                                    ):
                                        n_ins += 1
                                        issue_timeline_rows += 1
                                        repo_issue_timeline_rows += 1
                                if len(timeline) < 100:
                                    break
                        except GitHubApiError:
                            pass
                if len(iss_items) < 100:
                    iss_complete = True
                    iss_page = 1
                    break
                iss_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        # Releases (mapped to deployment semantics in canonical transform)
        rel_state = existing_repo.get("releases") if isinstance(existing_repo.get("releases"), dict) else {}
        rel_page_raw = rel_state.get("next_page", 1)
        try:
            rel_page = max(1, int(rel_page_raw))
        except (TypeError, ValueError):
            rel_page = 1
        rel_complete = False
        rel_pages_fetched = 0
        try:
            for _ in range(settings.cortex_github_releases_max_pages_per_repo):
                rel_items = list_repo_releases_page(
                    settings,
                    token,
                    owner=owner,
                    repo=repo_name,
                    page=rel_page,
                )
                rel_pages_fetched += 1
                for rel in rel_items:
                    rid = rel.get("id")
                    if rid is None:
                        continue
                    ext = f"{fn}:release:{rid}"[:512]
                    rel_body = dict(rel)
                    if not isinstance(rel_body.get("repository"), dict):
                        rel_body["repository"] = {"full_name": fn}
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_GITHUB,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="github.release",
                        external_id=ext,
                        api_endpoint=f"{gh_base}/repos/{owner}/{repo_name}/releases",
                        query_params={"page": rel_page},
                        payload_body={
                            **core_envelope_fields(
                                connector=CONNECTION_PROVIDER_GITHUB,
                                connection_id=connection_id,
                                source_object_type="github.release",
                                source_object_id=ext,
                            ),
                            "release": rel_body,
                        },
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"github:release:{ext}"),
                    ):
                        n_ins += 1
                        release_rows += 1
                        repo_release_rows += 1
                if len(rel_items) < 100:
                    rel_complete = True
                    rel_page = 1
                    break
                rel_page += 1
                if time.monotonic() - start_t >= settings.cortex_github_repo_time_budget_seconds:
                    budget_exhausted = True
                    break
        except GitHubApiError:
            pass

        repo_patch_map[fn] = {
            "cursor_owner": "github.repository",
            "pull_requests": {
                "cursor_owner": "github.pull_request",
                "next_page": current_pulls_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and pulls_complete),
                "pages_fetched_last_run": pull_pages_fetched,
                "rows_seen_last_run": repo_pr_rows,
            },
            "reviews": {
                "cursor_owner": "github.pull_request_review",
                "rows_seen_last_run": repo_review_rows,
            },
            "review_comments": {
                "cursor_owner": "github.pull_request_review_comment",
                "rows_seen_last_run": repo_review_comment_rows,
            },
            "issue_comments": {
                "cursor_owner": "github.issue_comment",
                "rows_seen_last_run": repo_issue_comment_rows,
            },
            "commits": {
                "cursor_owner": "github.commit",
                "next_page": commit_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and commits_complete),
                "pages_fetched_last_run": commit_pages_fetched,
                "rows_seen_last_run": repo_commit_rows,
            },
            "check_runs": {
                "cursor_owner": "github.check_run",
                "rows_seen_last_run": repo_check_rows,
            },
            "workflow_runs": {
                "cursor_owner": "github.workflow_run",
                "next_page": workflow_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and workflow_complete),
                "pages_fetched_last_run": workflow_pages_fetched,
                "rows_seen_last_run": repo_workflow_rows,
            },
            "deployments": {
                "cursor_owner": "github.deployment",
                "next_page": deployment_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and deployment_complete),
                "pages_fetched_last_run": deployment_pages_fetched,
                "rows_seen_last_run": repo_deploy_rows,
                "status_rows_seen_last_run": repo_deploy_status_rows,
            },
            "branches": {
                "cursor_owner": "github.branch",
                "next_page": branch_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and branch_complete),
                "pages_fetched_last_run": branch_pages_fetched,
                "rows_seen_last_run": repo_branch_rows,
            },
            "tags": {
                "cursor_owner": "github.tag",
                "next_page": tag_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and tag_complete),
                "pages_fetched_last_run": tag_pages_fetched,
                "rows_seen_last_run": repo_tag_rows,
            },
            "check_suites": {
                "cursor_owner": "github.check_suite",
                "rows_seen_last_run": repo_check_suite_rows,
            },
            "commit_comments": {
                "cursor_owner": "github.commit_comment",
                "next_page": cc_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and cc_complete),
                "pages_fetched_last_run": cc_pages_fetched,
                "rows_seen_last_run": repo_commit_comment_rows,
            },
            "releases": {
                "cursor_owner": "github.release",
                "next_page": rel_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and rel_complete),
                "pages_fetched_last_run": rel_pages_fetched,
                "rows_seen_last_run": repo_release_rows,
            },
            "issues": {
                "cursor_owner": "github.issue",
                "next_page": iss_page,
                "backfill_complete": bool(ctx.sync_mode == "backfill" and iss_complete),
                "pages_fetched_last_run": iss_pages_fetched,
                "rows_seen_last_run": repo_issue_rows,
            },
            "review_threads": {
                "cursor_owner": "github.review_thread",
                "rows_seen_last_run": repo_review_thread_rows,
            },
            "issue_timeline_events": {
                "cursor_owner": "github.issue_timeline_event",
                "rows_seen_last_run": repo_issue_timeline_rows,
            },
            "pull_request_timeline_events": {
                "cursor_owner": "github.pull_request_timeline_event",
                "rows_seen_last_run": repo_pr_timeline_rows,
            },
            "last_sync_mode": ctx.sync_mode,
        }
        if budget_exhausted:
            break

    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_GITHUB,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": _utc_now().isoformat(),
            "repos_fetched": n_ins,
            "github_installation_repos_pages": pages_fetched,
            "github_pull_requests_written": pr_rows,
            "github_reviews_written": review_rows,
            "github_review_comments_written": review_comment_rows,
            "github_issue_comments_written": issue_comment_rows,
            "github_commits_written": commit_rows,
            "github_check_runs_written": check_run_rows,
            "github_workflow_runs_written": workflow_rows,
            "github_deployments_written": deployment_rows,
            "github_deployment_statuses_written": deployment_status_rows,
            "github_branches_written": branch_rows,
            "github_tags_written": tag_rows,
            "github_check_suites_written": check_suite_rows,
            "github_commit_comments_written": commit_comment_rows,
            "github_releases_written": release_rows,
            "github_issues_written": issue_rows,
            "github_review_threads_written": review_thread_rows,
            "github_issue_timeline_events_written": issue_timeline_rows,
            "github_pull_request_timeline_events_written": pr_timeline_rows,
            "total_count_hint": total_hint,
            "streams": {
                "github": {
                    "installation_repositories": {
                        "cursor_owner": "github.installation_repositories",
                        "last_page": pages_fetched,
                    },
                    "pull_requests": {
                        "cursor_owner": "github.pull_request",
                        "repos_processed": len(selected_repos),
                        "rows_written": pr_rows,
                    },
                    "pull_request_reviews": {"cursor_owner": "github.pull_request_review", "rows_written": review_rows},
                    "pull_request_review_comments": {
                        "cursor_owner": "github.pull_request_review_comment",
                        "rows_written": review_comment_rows,
                    },
                    "issue_comments": {"cursor_owner": "github.issue_comment", "rows_written": issue_comment_rows},
                    "commits": {"cursor_owner": "github.commit", "rows_written": commit_rows},
                    "check_runs": {"cursor_owner": "github.check_run", "rows_written": check_run_rows},
                    "workflow_runs": {"cursor_owner": "github.workflow_run", "rows_written": workflow_rows},
                    "deployments": {"cursor_owner": "github.deployment", "rows_written": deployment_rows},
                    "deployment_statuses": {
                        "cursor_owner": "github.deployment_status",
                        "rows_written": deployment_status_rows,
                    },
                    "branches": {"cursor_owner": "github.branch", "rows_written": branch_rows},
                    "tags": {"cursor_owner": "github.tag", "rows_written": tag_rows},
                    "check_suites": {"cursor_owner": "github.check_suite", "rows_written": check_suite_rows},
                    "commit_comments": {"cursor_owner": "github.commit_comment", "rows_written": commit_comment_rows},
                    "releases": {"cursor_owner": "github.release", "rows_written": release_rows},
                    "issues": {"cursor_owner": "github.issue", "rows_written": issue_rows},
                    "review_threads": {"cursor_owner": "github.review_thread", "rows_written": review_thread_rows},
                    "issue_timeline_events": {
                        "cursor_owner": "github.issue_timeline_event",
                        "rows_written": issue_timeline_rows,
                    },
                    "pull_request_timeline_events": {
                        "cursor_owner": "github.pull_request_timeline_event",
                        "rows_written": pr_timeline_rows,
                    },
                    "repos": repo_patch_map,
                    "repo_ring_index": next_repo_ring_index,
                    "resume_required": budget_exhausted,
                    "time_budget_seconds": settings.cortex_github_repo_time_budget_seconds,
                }
            },
        },
        sync_mode=ctx.sync_mode,
    )
    return n_ins


LINEAR_ISSUES_QUERY = """
query LinearIngestIssues($first: Int!, $after: String) {
  issues(first: $first, after: $after) {
    nodes {
      id
      identifier
      title
      url
      createdAt
      updatedAt
      state { name }
      priority
      project { id name }
      cycle { id name }
      labels { nodes { id name color } }
      attachments { nodes { id title url } }
      metadata
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


LINEAR_COMMENTS_QUERY = """
query LinearIngestComments($first: Int!, $after: String) {
  comments(first: $first, after: $after) {
    nodes {
      id
      body
      createdAt
      updatedAt
      issue { id identifier }
      user { id name }
      parent { id }
      metadata
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


LINEAR_PROJECT_UPDATES_QUERY = """
query LinearIngestProjectUpdates($first: Int!, $after: String) {
  projectUpdates(first: $first, after: $after) {
    nodes {
      id
      body
      createdAt
      updatedAt
      url
      project { id name }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


LINEAR_PROJECTS_QUERY = """
query LinearIngestProjects($first: Int!, $after: String) {
  projects(first: $first, after: $after) {
    nodes {
      id
      name
      slug
      summary
      state
      startDate
      targetDate
      team { id name }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


LINEAR_CYCLES_QUERY = """
query LinearIngestCycles($first: Int!, $after: String) {
  cycles(first: $first, after: $after) {
    nodes {
      id
      name
      number
      startsAt
      endsAt
      completedAt
      progress
      team { id name }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


LINEAR_RELATIONS_QUERY = """
query LinearIngestIssueRelations($first: Int!, $after: String) {
  issueRelations(first: $first, after: $after) {
    nodes {
      id
      type
      issue { id identifier }
      relatedIssue { id identifier }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


LINEAR_LABELS_QUERY = """
query LinearIngestIssueLabels($first: Int!, $after: String) {
  issueLabels(first: $first, after: $after) {
    nodes {
      id
      name
      color
      team { id name }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


LINEAR_INITIATIVES_QUERY = """
query LinearIngestInitiatives($first: Int!, $after: String) {
  initiatives(first: $first, after: $after) {
    nodes {
      id
      name
      description
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def _linear_graphql_connection_page(
    settings: Settings,
    access_token: str,
    *,
    operation_name: str,
    query: str,
    root_field: str,
    first: int,
    after: str | None,
) -> tuple[int, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Fetch one GraphQL connection page (nodes + pageInfo)."""
    try:
        r = httpx.post(
            settings.linear_graphql_url(),
            json={
                "operationName": operation_name,
                "query": query,
                "variables": {"first": first, "after": after},
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
    except httpx.RequestError as e:
        return 0, {"error": str(e)}, [], {"hasNextPage": False, "endCursor": None}
    try:
        js = r.json()
    except ValueError:
        return r.status_code, {"text": (r.text or "")[:4000]}, [], {"hasNextPage": False, "endCursor": None}
    if not isinstance(js, dict):
        return r.status_code, {"error": "invalid_json_shape"}, [], {"hasNextPage": False, "endCursor": None}
    if js.get("errors"):
        return (
            r.status_code if r.status_code >= 100 else 400,
            {"errors": js["errors"]},
            [],
            {"hasNextPage": False, "endCursor": None},
        )
    data = js.get("data")
    nodes: list[dict[str, Any]] = []
    page_info: dict[str, Any] = {"hasNextPage": False, "endCursor": None}
    if isinstance(data, dict):
        conn_block = data.get(root_field)
        if isinstance(conn_block, dict):
            raw_nodes = conn_block.get("nodes")
            if isinstance(raw_nodes, list):
                nodes = [x for x in raw_nodes if isinstance(x, dict)]
            raw_page_info = conn_block.get("pageInfo")
            if isinstance(raw_page_info, dict):
                has_next = bool(raw_page_info.get("hasNextPage"))
                end_cursor = raw_page_info.get("endCursor")
                page_info = {
                    "hasNextPage": has_next,
                    "endCursor": end_cursor if isinstance(end_cursor, str) and end_cursor else None,
                }
    return r.status_code, js, nodes, page_info


def _linear_graphql_ping(
    settings: Settings,
    access_token: str,
) -> tuple[int, dict[str, Any]]:
    query = "query ViewerPing { viewer { id name } }"
    try:
        r = httpx.post(
            settings.linear_graphql_url(),
            json={"query": query},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
    except httpx.RequestError as e:
        return 0, {"error": str(e)}
    try:
        js = r.json()
    except ValueError:
        return r.status_code, {"text": (r.text or "")[:4000]}
    return r.status_code, js


def _linear_sync(
    session: Session,
    settings: Settings,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    scope_ck = ctx.checkpoint_scope_key()
    existing_ckpt = _read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_LINEAR,
        scope_key=scope_ck,
    )
    link = lin_repo.get_linear_connection_for_tenant(session, tenant_id)
    if link is None:
        ins = int(
            _append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_LINEAR,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="linear.sync",
                external_id="missing-linear-detail",
                api_endpoint="internal://linear/no-detail",
                query_params={},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_LINEAR,
                        connection_id=connection_id,
                        source_object_type="linear.connection",
                        source_object_id="linear_connection_detail_missing",
                    ),
                    "ingestion_error": {"code": "linear_connection_detail_missing"},
                },
                http_status=503,
                idempotency_key=_idem_key(ctx, run_id, "linear:no-detail"),
            )
        )
        _upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_LINEAR,
            scope_key=scope_ck,
            patch={
                "last_incremental_at": _utc_now().isoformat(),
                "streams": {
                    "linear": {
                        "issues": {
                            "cursor_owner": "linear.issue",
                            "last_status": "missing_connection_detail",
                        }
                    }
                },
            },
            sync_mode=ctx.sync_mode,
        )
        return ins
    token = link.detail.access_token
    n_ins = 0
    streams_existing = _checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    linear_existing = (
        streams_existing.get("linear")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("linear"), dict)
        else {}
    )

    def _stream_state(name: str) -> dict[str, Any]:
        s = linear_existing.get(name) if isinstance(linear_existing, dict) else None
        return s if isinstance(s, dict) else {}

    issue_state = _stream_state("issues")
    issue_watermark = issue_state.get("issues_updated_at_watermark")
    if not isinstance(issue_watermark, str) or not issue_watermark.strip():
        issue_watermark = None
    issue_cursor_raw = issue_state.get("next_cursor")
    issue_cursor = issue_cursor_raw if isinstance(issue_cursor_raw, str) and issue_cursor_raw.strip() else None
    issue_rows = 0
    attachment_rows = 0
    activity_rows = 0
    issue_pages = 0
    latest_issue_updated_at = issue_watermark
    issues_backfill_complete = False
    budget_exhausted = False
    start_t = time.monotonic()
    last_issues_status = 0
    payload_issues: dict[str, Any] = {}

    def _node_seq(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            nodes = value.get("nodes")
            if isinstance(nodes, list):
                return [x for x in nodes if isinstance(x, dict)]
        return []

    def _maybe_iso_max(current: str | None, candidate: str | None) -> str | None:
        if not isinstance(candidate, str) or not candidate.strip():
            return current
        if current is None or candidate > current:
            return candidate
        return current

    for _ in range(settings.cortex_linear_issues_max_pages_per_sync):
        st_issues, payload_issues, issue_nodes, page_info = _linear_graphql_connection_page(
            settings,
            token,
            operation_name="LinearIngestIssues",
            query=LINEAR_ISSUES_QUERY,
            root_field="issues",
            first=settings.cortex_linear_issues_first,
            after=issue_cursor,
        )
        last_issues_status = st_issues
        issue_pages += 1
        for node in issue_nodes:
            updated_at = node.get("updatedAt")
            if isinstance(updated_at, str):
                latest_issue_updated_at = _maybe_iso_max(latest_issue_updated_at, updated_at)
            if (
                ctx.sync_mode == "incremental"
                and isinstance(issue_watermark, str)
                and isinstance(updated_at, str)
                and updated_at <= issue_watermark
            ):
                continue
            iid = node.get("id")
            ident = node.get("identifier")
            ext = str(iid or ident or "")[:512] or "unknown"
            body = {
                **core_envelope_fields(
                    connector=CONNECTION_PROVIDER_LINEAR,
                    connection_id=connection_id,
                    source_object_type="linear.issue",
                    source_object_id=ext,
                ),
                "issue": node,
            }
            if _append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_LINEAR,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="linear.issue",
                external_id=ext,
                api_endpoint=settings.linear_graphql_url()[:512],
                query_params={"operationName": "LinearIngestIssues", "after": issue_cursor},
                payload_body=body,
                http_status=st_issues if st_issues >= 100 else 200,
                idempotency_key=_idem_key(ctx, run_id, f"linear:issue:{ext}"),
            ):
                n_ins += 1
                issue_rows += 1

            for idx, attachment in enumerate(_node_seq(node.get("attachments"))):
                aid = attachment.get("id")
                a_ext = f"{ext}:attachment:{aid if isinstance(aid, str) else idx}"[:512]
                if _append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_LINEAR,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="linear.issue_attachment",
                    external_id=a_ext,
                    api_endpoint=settings.linear_graphql_url()[:512],
                    query_params={"operationName": "LinearIngestIssues"},
                    payload_body={
                        **core_envelope_fields(
                            connector=CONNECTION_PROVIDER_LINEAR,
                            connection_id=connection_id,
                            source_object_type="linear.issue_attachment",
                            source_object_id=a_ext,
                        ),
                        "issue_id": iid,
                        "attachment": attachment,
                    },
                    http_status=st_issues if st_issues >= 100 else 200,
                    idempotency_key=_idem_key(ctx, run_id, f"linear:attachment:{a_ext}"),
                ):
                    n_ins += 1
                    attachment_rows += 1

            activity_items = _node_seq(node.get("history")) or _node_seq(node.get("activityHistory"))
            for idx, event in enumerate(activity_items):
                aid = event.get("id")
                a_ext = f"{ext}:activity:{aid if isinstance(aid, str) else idx}"[:512]
                if _append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_LINEAR,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="linear.activity_history",
                    external_id=a_ext,
                    api_endpoint=settings.linear_graphql_url()[:512],
                    query_params={"operationName": "LinearIngestIssues"},
                    payload_body={
                        **core_envelope_fields(
                            connector=CONNECTION_PROVIDER_LINEAR,
                            connection_id=connection_id,
                            source_object_type="linear.activity_history",
                            source_object_id=a_ext,
                        ),
                        "issue_id": iid,
                        "event": event,
                    },
                    http_status=st_issues if st_issues >= 100 else 200,
                    idempotency_key=_idem_key(ctx, run_id, f"linear:activity:{a_ext}"),
                ):
                    n_ins += 1
                    activity_rows += 1

        next_cursor = page_info.get("endCursor") if isinstance(page_info, dict) else None
        has_next = bool(page_info.get("hasNextPage")) if isinstance(page_info, dict) else False
        issue_cursor = next_cursor if isinstance(next_cursor, str) and next_cursor else None
        if not has_next:
            issues_backfill_complete = True
            break
        if time.monotonic() - start_t >= settings.cortex_linear_time_budget_seconds:
            budget_exhausted = True
            break

    linear_comment_thread_rows = 0
    comment_state = _stream_state("comments")
    comment_cursor_raw = comment_state.get("next_cursor")
    comment_cursor = comment_cursor_raw if isinstance(comment_cursor_raw, str) and comment_cursor_raw.strip() else None
    comment_rows = 0
    comment_pages = 0
    comments_backfill_complete = False
    for _ in range(settings.cortex_linear_comments_max_pages_per_sync):
        if budget_exhausted:
            break
        st_comments, _payload_comments, comment_nodes, page_info_c = _linear_graphql_connection_page(
            settings,
            token,
            operation_name="LinearIngestComments",
            query=LINEAR_COMMENTS_QUERY,
            root_field="comments",
            first=settings.cortex_linear_stream_first,
            after=comment_cursor,
        )
        comment_pages += 1
        for idx, node in enumerate(comment_nodes):
            nid = node.get("id")
            ext = str(nid if isinstance(nid, str) else f"comments:{idx}")[:512] or "unknown"
            if _append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_LINEAR,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="linear.comment",
                external_id=ext,
                api_endpoint=settings.linear_graphql_url()[:512],
                query_params={"operationName": "LinearIngestComments", "after": comment_cursor},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_LINEAR,
                        connection_id=connection_id,
                        source_object_type="linear.comment",
                        source_object_id=ext,
                    ),
                    "comment": node,
                },
                http_status=st_comments if st_comments >= 100 else 200,
                idempotency_key=_idem_key(ctx, run_id, f"linear:comments:{ext}"),
            ):
                n_ins += 1
                comment_rows += 1
            parent = node.get("parent") if isinstance(node.get("parent"), dict) else None
            pid = parent.get("id") if isinstance(parent, dict) else None
            if (not isinstance(pid, str) or not pid.strip()) and isinstance(nid, str) and nid.strip():
                t_ext = f"{nid.strip()}:thread"[:512]
                if _append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_LINEAR,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="linear.comment_thread",
                    external_id=t_ext,
                    api_endpoint=settings.linear_graphql_url()[:512],
                    query_params={"operationName": "LinearIngestComments", "after": comment_cursor},
                    payload_body={
                        **core_envelope_fields(
                            connector=CONNECTION_PROVIDER_LINEAR,
                            connection_id=connection_id,
                            source_object_type="linear.comment_thread",
                            source_object_id=t_ext,
                        ),
                        "id": nid.strip(),
                        "thread_id": nid.strip(),
                        "issue": node.get("issue"),
                        "anchor_comment": node,
                    },
                    http_status=st_comments if st_comments >= 100 else 200,
                    idempotency_key=_idem_key(ctx, run_id, f"linear:comment_thread:{t_ext}"),
                ):
                    n_ins += 1
                    linear_comment_thread_rows += 1
        next_c = page_info_c.get("endCursor") if isinstance(page_info_c, dict) else None
        has_next_c = bool(page_info_c.get("hasNextPage")) if isinstance(page_info_c, dict) else False
        comment_cursor = next_c if isinstance(next_c, str) and next_c else None
        if not has_next_c:
            comments_backfill_complete = True
            break
        if time.monotonic() - start_t >= settings.cortex_linear_time_budget_seconds:
            budget_exhausted = True
            break

    stream_specs: list[tuple[str, str, str, str, str, int]] = [
        (
            "projects",
            "LinearIngestProjects",
            "projects",
            LINEAR_PROJECTS_QUERY,
            "linear.project",
            settings.cortex_linear_projects_max_pages_per_sync,
        ),
        (
            "cycles",
            "LinearIngestCycles",
            "cycles",
            LINEAR_CYCLES_QUERY,
            "linear.cycle",
            settings.cortex_linear_cycles_max_pages_per_sync,
        ),
        (
            "issue_relations",
            "LinearIngestIssueRelations",
            "issueRelations",
            LINEAR_RELATIONS_QUERY,
            "linear.issue_relation",
            settings.cortex_linear_issue_relations_max_pages_per_sync,
        ),
        (
            "issue_labels",
            "LinearIngestIssueLabels",
            "issueLabels",
            LINEAR_LABELS_QUERY,
            "linear.issue_label",
            settings.cortex_linear_issue_labels_max_pages_per_sync,
        ),
        (
            "initiatives",
            "LinearIngestInitiatives",
            "initiatives",
            LINEAR_INITIATIVES_QUERY,
            "linear.initiative",
            settings.cortex_linear_initiatives_max_pages_per_sync,
        ),
        (
            "project_updates",
            "LinearIngestProjectUpdates",
            "projectUpdates",
            LINEAR_PROJECT_UPDATES_QUERY,
            "linear.project_update",
            settings.cortex_linear_project_updates_max_pages_per_sync,
        ),
    ]
    stream_patch: dict[str, Any] = {
        "comments": {
            "cursor_owner": "linear.comment",
            "next_cursor": comment_cursor,
            "pages_fetched_last_run": comment_pages,
            "rows_seen_last_run": comment_rows,
            "comment_thread_rows_seen_last_run": linear_comment_thread_rows,
            "backfill_complete": bool(ctx.sync_mode == "backfill" and comments_backfill_complete),
        }
    }
    stream_counts: dict[str, int] = {"linear.comment": comment_rows, "linear.comment_thread": linear_comment_thread_rows}
    for stream_key, op_name, root_field, query, resource_type, max_pages in stream_specs:
        if budget_exhausted:
            break
        state = _stream_state(stream_key)
        cursor_raw = state.get("next_cursor")
        cursor = cursor_raw if isinstance(cursor_raw, str) and cursor_raw.strip() else None
        rows = 0
        pages_fetched = 0
        complete = False
        for _ in range(max_pages):
            status_stream, _payload_stream, nodes, page_info = _linear_graphql_connection_page(
                settings,
                token,
                operation_name=op_name,
                query=query,
                root_field=root_field,
                first=settings.cortex_linear_stream_first,
                after=cursor,
            )
            pages_fetched += 1
            for idx, node in enumerate(nodes):
                nid = node.get("id")
                ext = str(nid if isinstance(nid, str) else f"{stream_key}:{idx}")[:512] or "unknown"
                if _append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_LINEAR,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type=resource_type,
                    external_id=ext,
                    api_endpoint=settings.linear_graphql_url()[:512],
                    query_params={"operationName": op_name, "after": cursor},
                    payload_body={
                        **core_envelope_fields(
                            connector=CONNECTION_PROVIDER_LINEAR,
                            connection_id=connection_id,
                            source_object_type=resource_type,
                            source_object_id=ext,
                        ),
                        stream_key[:-1] if stream_key.endswith("s") else stream_key: node,
                    },
                    http_status=status_stream if status_stream >= 100 else 200,
                    idempotency_key=_idem_key(ctx, run_id, f"linear:{stream_key}:{ext}"),
                ):
                    n_ins += 1
                    rows += 1
            next_cursor = page_info.get("endCursor") if isinstance(page_info, dict) else None
            has_next = bool(page_info.get("hasNextPage")) if isinstance(page_info, dict) else False
            cursor = next_cursor if isinstance(next_cursor, str) and next_cursor else None
            if not has_next:
                complete = True
                break
            if time.monotonic() - start_t >= settings.cortex_linear_time_budget_seconds:
                budget_exhausted = True
                break
        stream_counts[resource_type] = rows
        stream_patch[stream_key] = {
            "cursor_owner": resource_type,
            "next_cursor": cursor,
            "pages_fetched_last_run": pages_fetched,
            "rows_seen_last_run": rows,
            "backfill_complete": bool(ctx.sync_mode == "backfill" and complete),
        }

    status, payload = _linear_graphql_ping(settings, token)
    ins = int(
        _append_raw(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_LINEAR,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type="linear.viewer_ping",
            external_id="viewer_snapshot",
            api_endpoint=settings.linear_graphql_url()[:512],
            query_params={},
            payload_body={
                **core_envelope_fields(
                    connector=CONNECTION_PROVIDER_LINEAR,
                    connection_id=connection_id,
                    source_object_type="linear.graphql_snapshot",
                    source_object_id="viewer",
                ),
                "graphql_status": status,
                "response": payload,
                "issues_snapshot_status": last_issues_status,
                "issues_graphql": payload_issues,
            },
            http_status=status if status >= 100 else 500,
            idempotency_key=_idem_key(ctx, run_id, "linear:viewer"),
        )
    )
    n_ins += ins
    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_LINEAR,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": _utc_now().isoformat(),
            "last_http_status": status,
            "linear_issues_fetched": issue_rows,
            "linear_comments_written": stream_counts.get("linear.comment", 0),
            "linear_comment_threads_written": stream_counts.get("linear.comment_thread", 0),
            "linear_project_updates_written": stream_counts.get("linear.project_update", 0),
            "linear_projects_written": stream_counts.get("linear.project", 0),
            "linear_cycles_written": stream_counts.get("linear.cycle", 0),
            "linear_issue_relations_written": stream_counts.get("linear.issue_relation", 0),
            "linear_issue_labels_written": stream_counts.get("linear.issue_label", 0),
            "linear_initiatives_written": stream_counts.get("linear.initiative", 0),
            "linear_issue_attachments_written": attachment_rows,
            "linear_activity_history_written": activity_rows,
            "streams": {
                "linear": {
                    "issues": {
                        "cursor_owner": "linear.issue",
                        "issues_fetched": issue_rows,
                        "next_cursor": issue_cursor,
                        "pages_fetched_last_run": issue_pages,
                        "issues_updated_at_watermark": latest_issue_updated_at,
                        "backfill_complete": bool(ctx.sync_mode == "backfill" and issues_backfill_complete),
                    },
                    "comments": stream_patch.get("comments", {"cursor_owner": "linear.comment"}),
                    "projects": stream_patch.get("projects", {"cursor_owner": "linear.project"}),
                    "cycles": stream_patch.get("cycles", {"cursor_owner": "linear.cycle"}),
                    "issue_relations": stream_patch.get(
                        "issue_relations", {"cursor_owner": "linear.issue_relation"}
                    ),
                    "issue_labels": stream_patch.get("issue_labels", {"cursor_owner": "linear.issue_label"}),
                    "initiatives": stream_patch.get("initiatives", {"cursor_owner": "linear.initiative"}),
                    "issue_attachments": {
                        "cursor_owner": "linear.issue_attachment",
                        "rows_seen_last_run": attachment_rows,
                    },
                    "activity_history": {
                        "cursor_owner": "linear.activity_history",
                        "rows_seen_last_run": activity_rows,
                    },
                    "viewer_ping": {
                        "cursor_owner": "linear.viewer_ping",
                        "last_status": status,
                    },
                    "resume_required": budget_exhausted,
                    "time_budget_seconds": settings.cortex_linear_time_budget_seconds,
                }
            },
        },
        sync_mode=ctx.sync_mode,
    )
    return n_ins


def _generic_scope_ping(
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
        _append_raw(
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
            idempotency_key=_idem_key(ctx, run_id, f"{connector}:ping"),
        )
    )
    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": _utc_now().isoformat(),
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
        sync_mode=ctx.sync_mode,
    )
    return ins


def _read_checkpoint_state(
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


def _checkpoint_streams_for_mode(existing_ckpt: dict[str, Any], sync_mode: str) -> dict[str, Any]:
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


def _slack_ts_value(ts: str) -> float:
    try:
        return float(ts)
    except ValueError:
        return 0.0


def _slack_channel_history_sync_mode(
    *,
    ctx_sync_mode: str,
    channel_id: str,
    ingest_channel_ids: set[str],
    existing_history: dict[str, Any] | None,
) -> str:
    """Keep admin-selected channels in backfill until history.backfill_complete is true."""
    if ctx_sync_mode == "backfill":
        return "backfill"
    history = existing_history if isinstance(existing_history, dict) else {}
    if ingest_channel_ids and channel_id not in ingest_channel_ids:
        return "incremental"
    if history.get("backfill_complete") is True:
        return "incremental"
    return "backfill"


def _slack_history_time_bounds(
    *,
    sync_mode: str,
    existing_history: dict[str, Any] | None,
    history_cursor: str | None,
    backfill_oldest_ts: str,
) -> tuple[str | None, str | None]:
    """Return (oldest, latest) for conversations.history when cursor is absent."""
    history = existing_history if isinstance(existing_history, dict) else {}
    if sync_mode == "incremental":
        last_seen = history.get("last_message_ts")
        if isinstance(last_seen, str) and last_seen.strip():
            return last_seen.strip(), None
        return None, None
    if backfill_oldest_ts.strip():
        return backfill_oldest_ts.strip(), None
    if history_cursor:
        return None, None
    last_seen = history.get("last_message_ts")
    if isinstance(last_seen, str) and last_seen.strip():
        return None, last_seen.strip()
    return None, None


def _pick_slack_channels_round_robin(
    channels: list[dict[str, Any]],
    *,
    ring_index: int,
    count: int,
) -> tuple[list[dict[str, Any]], int]:
    if count <= 0 or not channels:
        return [], 0
    ordered = sorted(
        [c for c in channels if isinstance(c.get("id"), str)],
        key=lambda c: str(c.get("id")),
    )
    if not ordered:
        return [], 0
    start = max(0, ring_index) % len(ordered)
    out: list[dict[str, Any]] = []
    idx = start
    for _ in range(min(count, len(ordered))):
        out.append(ordered[idx])
        idx = (idx + 1) % len(ordered)
    return out, idx


def _pick_github_repos_round_robin(
    repos: list[tuple[str, str, dict[str, Any]]],
    *,
    ring_index: int,
    count: int,
) -> tuple[list[tuple[str, str, dict[str, Any]]], int]:
    if count <= 0 or not repos:
        return [], 0
    ordered = sorted(repos, key=lambda item: item[1])
    start = max(0, ring_index) % len(ordered)
    out: list[tuple[str, str, dict[str, Any]]] = []
    idx = start
    for _ in range(min(count, len(ordered))):
        out.append(ordered[idx])
        idx = (idx + 1) % len(ordered)
    return out, idx


def _slack_sync(
    session: Session,
    settings: Settings,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    scope_ck = ctx.checkpoint_scope_key()
    existing_ckpt = _read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_SLACK,
        scope_key=scope_ck,
    )
    link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return _generic_scope_ping(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_SLACK,
            run_id=run_id,
            source_trigger=source_trigger,
            label="no_slack_detail",
        )
    token = link.detail.bot_access_token
    from vector.domains.cortex.connectors.slack.errors import SlackWebApiError
    from vector.domains.cortex.connectors.slack.ingestion_api import (
        iter_conversations_list_pages,
        iter_conversations_history_pages,
        iter_conversations_replies_pages,
        iter_users_list_pages,
    )

    n_ins = 0
    user_pages = 0
    user_members = 0
    channel_pages = 0
    channel_rows = 0
    message_rows = 0
    reply_rows = 0
    reaction_rows = 0
    file_rows = 0
    thread_pages = 0
    thread_rows = 0
    threads_processed = 0
    budget_exhausted = False
    slack_api_base = "https://slack.com/api"
    if settings.vector_use_mock_connectors and settings.notion_api_base_url().endswith("/admin/dataset/full"):
        slack_api_base = f"{settings.vector_mock_connector_base_url.rstrip('/')}/slack/api"
    start_t = time.monotonic()

    streams_existing = _checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    slack_existing = (
        streams_existing.get("slack")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("slack"), dict)
        else {}
    )
    channels_existing = (
        slack_existing.get("channels")
        if isinstance(slack_existing, dict) and isinstance(slack_existing.get("channels"), dict)
        else {}
    )
    ring_index_raw = slack_existing.get("channel_ring_index") if isinstance(slack_existing, dict) else 0
    try:
        ring_index = int(ring_index_raw)
    except (TypeError, ValueError):
        ring_index = 0

    channel_patch_map: dict[str, Any] = (
        dict(channels_existing) if isinstance(channels_existing, dict) else {}
    )
    try:
        for members in iter_users_list_pages(
            token,
            api_base=slack_api_base,
            max_pages=settings.cortex_slack_users_max_pages,
        ):
            user_pages += 1
            for m in members:
                uid = m.get("id")
                if not isinstance(uid, str) or not uid:
                    continue
                user_members += 1
                body = {
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_SLACK,
                        connection_id=connection_id,
                        source_object_type="slack.user",
                        source_object_id=uid,
                    ),
                    "member": m,
                }
                if _append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_SLACK,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="slack.user",
                    external_id=uid,
                    api_endpoint=f"{slack_api_base}/users.list",
                    query_params={"source": "users.list"},
                    payload_body=body,
                    http_status=200,
                    idempotency_key=_idem_key(ctx, run_id, f"slack:user:{uid}"),
                ):
                    n_ins += 1

        all_channels: list[dict[str, Any]] = []
        for chans in iter_conversations_list_pages(
            token,
            api_base=slack_api_base,
            types=settings.cortex_slack_conversation_types,
            max_pages=settings.cortex_slack_conversations_max_pages,
        ):
            channel_pages += 1
            all_channels.extend(chans)
            for c in chans:
                cid = c.get("id")
                if not isinstance(cid, str) or not cid:
                    continue
                channel_rows += 1
                body = {
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_SLACK,
                        connection_id=connection_id,
                        source_object_type="slack.conversation",
                        source_object_id=cid,
                    ),
                    "channel": c,
                }
                if _append_raw(
                    session,
                    ctx=ctx,
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    connector=CONNECTION_PROVIDER_SLACK,
                    run_id=run_id,
                    source_trigger=source_trigger,
                    resource_type="slack.conversation",
                    external_id=cid,
                    api_endpoint=f"{slack_api_base}/conversations.list",
                    query_params={"source": "conversations.list"},
                    payload_body=body,
                    http_status=200,
                    idempotency_key=_idem_key(ctx, run_id, f"slack:channel:{cid}"),
                ):
                    n_ins += 1

        ingest_channel_ids = set(get_saved_ingest_channel_ids(link.detail))
        if ingest_channel_ids:
            candidates = [
                c
                for c in all_channels
                if isinstance(c.get("id"), str)
                and str(c["id"]) in ingest_channel_ids
                and c.get("is_archived") is not True
            ]
        else:
            candidates = [
                c
                for c in all_channels
                if isinstance(c.get("id"), str)
                and c.get("is_member") is not False
                and c.get("is_archived") is not True
            ]
        if ingest_channel_ids:
            listed_ids = {
                str(c["id"]) for c in candidates if isinstance(c.get("id"), str) and str(c["id"]).strip()
            }
            for missing_id in sorted(ingest_channel_ids):
                if missing_id in listed_ids:
                    continue
                try:
                    from vector.domains.cortex.connectors.slack.ingestion_api import conversations_info

                    ch_info = conversations_info(token, channel=missing_id, api_base=slack_api_base)
                    if ch_info.get("is_archived") is not True:
                        candidates.append(ch_info)
                        listed_ids.add(missing_id)
                except SlackWebApiError:
                    candidates.append(
                        {
                            "id": missing_id,
                            "is_archived": False,
                            "is_private": False,
                            "is_member": True,
                        }
                    )
                    listed_ids.add(missing_id)

        selected_channels, next_ring_index = _pick_slack_channels_round_robin(
            candidates,
            ring_index=ring_index,
            count=settings.cortex_slack_history_channels_per_sync,
        )
        for c in selected_channels:
            cid = str(c["id"])
            existing_channel = channel_patch_map.get(cid)
            if not isinstance(existing_channel, dict):
                existing_channel = (
                    channels_existing.get(cid) if isinstance(channels_existing, dict) else None
                )
            existing_history = (
                existing_channel.get("history")
                if isinstance(existing_channel, dict) and isinstance(existing_channel.get("history"), dict)
                else {}
            )
            sync_mode = _slack_channel_history_sync_mode(
                ctx_sync_mode=ctx.sync_mode,
                channel_id=cid,
                ingest_channel_ids=ingest_channel_ids,
                existing_history=existing_history,
            )
            history_cursor = existing_history.get("next_cursor")
            if not isinstance(history_cursor, str) or not history_cursor.strip():
                history_cursor = None
            oldest, latest = _slack_history_time_bounds(
                sync_mode=sync_mode,
                existing_history=existing_history,
                history_cursor=history_cursor,
                backfill_oldest_ts=settings.cortex_slack_backfill_oldest_ts,
            )

            channel_message_rows = 0
            channel_reply_rows = 0
            channel_reaction_rows = 0
            channel_file_rows = 0
            channel_thread_pages = 0
            history_pages = 0
            latest_message_ts = (
                oldest
                if isinstance(oldest, str)
                else (
                    existing_history.get("last_message_ts")
                    if isinstance(existing_history.get("last_message_ts"), str)
                    else None
                )
            )
            next_history_cursor: str | None = history_cursor
            thread_roots: list[str] = []
            thread_seen: set[str] = set()

            for page in iter_conversations_history_pages(
                token,
                api_base=slack_api_base,
                channel=cid,
                limit=settings.cortex_slack_conversations_history_limit,
                max_pages=settings.cortex_slack_history_max_pages_per_channel,
                cursor=history_cursor,
                oldest=oldest,
                latest=latest,
            ):
                history_pages += 1
                page_cursor = page.get("next_cursor")
                next_history_cursor = page_cursor if isinstance(page_cursor, str) and page_cursor else None
                page_messages = page.get("messages")
                msgs = [m for m in page_messages if isinstance(m, dict)] if isinstance(page_messages, list) else []
                for msg in msgs:
                    ts = msg.get("ts")
                    if not isinstance(ts, str):
                        continue
                    ext = f"{cid}:{ts}"[:512]
                    if latest_message_ts is None or _slack_ts_value(ts) > _slack_ts_value(latest_message_ts):
                        latest_message_ts = ts
                    body = {
                        **core_envelope_fields(
                            connector=CONNECTION_PROVIDER_SLACK,
                            connection_id=connection_id,
                            source_object_type="slack.message",
                            source_object_id=ext,
                        ),
                        "channel_id": cid,
                        "message": msg,
                        "paging": {"next_cursor": next_history_cursor, "mode": sync_mode},
                    }
                    message_rows += 1
                    channel_message_rows += 1
                    if _append_raw(
                        session,
                        ctx=ctx,
                        tenant_id=tenant_id,
                        connection_id=connection_id,
                        connector=CONNECTION_PROVIDER_SLACK,
                        run_id=run_id,
                        source_trigger=source_trigger,
                        resource_type="slack.message",
                        external_id=ext,
                        api_endpoint=f"{slack_api_base}/conversations.history",
                        query_params={"channel": cid, "mode": sync_mode},
                        payload_body=body,
                        http_status=200,
                        idempotency_key=_idem_key(ctx, run_id, f"slack:msg:{cid}:{ts}"),
                    ):
                        n_ins += 1

                    rc = msg.get("reply_count")
                    thread_ts = msg.get("thread_ts")
                    if isinstance(rc, int) and rc > 0 and isinstance(thread_ts, str) and thread_ts == ts:
                        if thread_ts not in thread_seen:
                            thread_seen.add(thread_ts)
                            thread_roots.append(thread_ts)
                            thr_ext = f"{cid}:{thread_ts}"[:512]
                            if _append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_SLACK,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="slack.thread",
                                external_id=thr_ext,
                                api_endpoint=f"{slack_api_base}/conversations.history",
                                query_params={"channel": cid, "thread_ts": thread_ts},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_SLACK,
                                        connection_id=connection_id,
                                        source_object_type="slack.thread",
                                        source_object_id=thr_ext,
                                    ),
                                    "channel": cid,
                                    "thread_ts": thread_ts,
                                    "root_message_ts": ts,
                                },
                                http_status=200,
                                idempotency_key=_idem_key(ctx, run_id, f"slack:thread:{thr_ext}"),
                            ):
                                n_ins += 1
                                thread_rows += 1

                    reactions = msg.get("reactions")
                    if isinstance(reactions, list):
                        for reaction in reactions:
                            if not isinstance(reaction, dict):
                                continue
                            name = reaction.get("name")
                            if not isinstance(name, str) or not name.strip():
                                continue
                            reaction_ext = f"{cid}:{ts}:{name.strip()}"[:512]
                            reaction_rows += 1
                            channel_reaction_rows += 1
                            if _append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_SLACK,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="slack.reaction",
                                external_id=reaction_ext,
                                api_endpoint=f"{slack_api_base}/conversations.history",
                                query_params={"channel": cid, "message_ts": ts},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_SLACK,
                                        connection_id=connection_id,
                                        source_object_type="slack.reaction",
                                        source_object_id=reaction_ext,
                                    ),
                                    "channel_id": cid,
                                    "message_ts": ts,
                                    "reaction": reaction,
                                },
                                http_status=200,
                                idempotency_key=_idem_key(ctx, run_id, f"slack:reaction:{reaction_ext}"),
                            ):
                                n_ins += 1

                    files = msg.get("files")
                    msg_thread_ts = msg.get("thread_ts")
                    if isinstance(files, list):
                        for f in files:
                            if not isinstance(f, dict):
                                continue
                            fid = f.get("id")
                            if not isinstance(fid, str) or not fid.strip():
                                continue
                            file_ext = f"{cid}:{fid.strip()}"[:512]
                            file_rows += 1
                            channel_file_rows += 1
                            if _append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_SLACK,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="slack.file",
                                external_id=file_ext,
                                api_endpoint=f"{slack_api_base}/conversations.history",
                                query_params={"channel": cid, "message_ts": ts},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_SLACK,
                                        connection_id=connection_id,
                                        source_object_type="slack.file",
                                        source_object_id=file_ext,
                                    ),
                                    "channel_id": cid,
                                    "message_ts": ts,
                                    "thread_ts": msg_thread_ts
                                    if isinstance(msg_thread_ts, str) and msg_thread_ts.strip()
                                    else None,
                                    "file": f,
                                },
                                http_status=200,
                                idempotency_key=_idem_key(ctx, run_id, f"slack:file:{file_ext}"),
                            ):
                                n_ins += 1

                if not next_history_cursor:
                    break
                if time.monotonic() - start_t >= settings.cortex_slack_channel_time_budget_seconds:
                    budget_exhausted = True
                    break

            channel_patch_map[cid] = {
                "cursor_owner": "slack.message",
                "history": {
                    "last_message_ts": latest_message_ts,
                    "next_cursor": next_history_cursor,
                    "backfill_complete": bool(not next_history_cursor),
                    "pages_fetched_last_run": history_pages,
                },
                "threads": (
                    existing_channel.get("threads")
                    if isinstance(existing_channel, dict) and isinstance(existing_channel.get("threads"), dict)
                    else {}
                ),
                "last_sync_mode": sync_mode,
                "message_rows_last_run": channel_message_rows,
                "reply_rows_last_run": channel_reply_rows,
                "reaction_rows_last_run": channel_reaction_rows,
                "file_rows_last_run": channel_file_rows,
                "thread_pages_last_run": channel_thread_pages,
            }

            existing_threads = (
                channel_patch_map[cid].get("threads")
                if isinstance(channel_patch_map.get(cid), dict)
                else {}
            )
            if not isinstance(existing_threads, dict):
                existing_threads = {}
            thread_patch: dict[str, Any] = dict(existing_threads)
            for thread_ts in thread_roots:
                if threads_processed >= settings.cortex_slack_threads_per_sync:
                    break
                threads_processed += 1
                existing_thread = (
                    existing_threads.get(thread_ts)
                    if isinstance(existing_threads, dict) and isinstance(existing_threads.get(thread_ts), dict)
                    else {}
                )
                replies_cursor = existing_thread.get("next_cursor")
                if not isinstance(replies_cursor, str) or not replies_cursor.strip():
                    replies_cursor = None
                replies_oldest: str | None = None
                if sync_mode == "incremental":
                    last_reply_ts = existing_thread.get("last_reply_ts")
                    if isinstance(last_reply_ts, str) and last_reply_ts.strip():
                        replies_oldest = last_reply_ts.strip()
                next_replies_cursor: str | None = replies_cursor
                latest_reply_ts = (
                    replies_oldest
                    if isinstance(replies_oldest, str)
                    else (
                        existing_thread.get("last_reply_ts")
                        if isinstance(existing_thread.get("last_reply_ts"), str)
                        else None
                    )
                )
                per_thread_pages = 0
                try:
                    for rep_page in iter_conversations_replies_pages(
                        token,
                        api_base=slack_api_base,
                        channel=cid,
                        thread_ts=thread_ts,
                        limit=settings.cortex_slack_conversations_history_limit,
                        max_pages=settings.cortex_slack_replies_max_pages_per_thread,
                        cursor=replies_cursor,
                        oldest=replies_oldest,
                    ):
                        per_thread_pages += 1
                        thread_pages += 1
                        channel_thread_pages += 1
                        page_cursor = rep_page.get("next_cursor")
                        next_replies_cursor = page_cursor if isinstance(page_cursor, str) and page_cursor else None
                        rep_msgs = rep_page.get("messages")
                        rows = [m for m in rep_msgs if isinstance(m, dict)] if isinstance(rep_msgs, list) else []
                        for reply in rows:
                            rts = reply.get("ts")
                            if not isinstance(rts, str) or rts == thread_ts:
                                continue
                            reply_ext = f"{cid}:{thread_ts}:{rts}"[:512]
                            if latest_reply_ts is None or _slack_ts_value(rts) > _slack_ts_value(latest_reply_ts):
                                latest_reply_ts = rts
                            reply_rows += 1
                            channel_reply_rows += 1
                            if _append_raw(
                                session,
                                ctx=ctx,
                                tenant_id=tenant_id,
                                connection_id=connection_id,
                                connector=CONNECTION_PROVIDER_SLACK,
                                run_id=run_id,
                                source_trigger=source_trigger,
                                resource_type="slack.message_reply",
                                external_id=reply_ext,
                                api_endpoint=f"{slack_api_base}/conversations.replies",
                                query_params={"channel": cid, "thread_ts": thread_ts, "mode": sync_mode},
                                payload_body={
                                    **core_envelope_fields(
                                        connector=CONNECTION_PROVIDER_SLACK,
                                        connection_id=connection_id,
                                        source_object_type="slack.message_reply",
                                        source_object_id=reply_ext,
                                    ),
                                    "channel_id": cid,
                                    "thread_ts": thread_ts,
                                    "reply": reply,
                                    "paging": {"next_cursor": next_replies_cursor, "mode": sync_mode},
                                },
                                http_status=200,
                                idempotency_key=_idem_key(ctx, run_id, f"slack:reply:{reply_ext}"),
                            ):
                                n_ins += 1
                        if not next_replies_cursor:
                            break
                        if time.monotonic() - start_t >= settings.cortex_slack_channel_time_budget_seconds:
                            budget_exhausted = True
                            break
                except SlackWebApiError as reply_exc:
                    _logger.warning(
                        "slack thread replies skipped",
                        extra={"channel_id": cid, "thread_ts": thread_ts, "error": str(reply_exc)},
                    )
                    thread_patch[thread_ts] = {
                        "cursor_owner": "slack.message_reply",
                        "last_sync_error": str(reply_exc),
                    }
                    continue

                thread_patch[thread_ts] = {
                    "cursor_owner": "slack.message_reply",
                    "last_reply_ts": latest_reply_ts,
                    "next_cursor": next_replies_cursor,
                    "backfill_complete": bool(not next_replies_cursor),
                    "pages_fetched_last_run": per_thread_pages,
                }
                if budget_exhausted:
                    break

            if isinstance(channel_patch_map.get(cid), dict):
                channel_patch_map[cid]["threads"] = thread_patch
                channel_patch_map[cid]["reply_rows_last_run"] = channel_reply_rows
                channel_patch_map[cid]["thread_pages_last_run"] = channel_thread_pages
            if budget_exhausted:
                break

    except SlackWebApiError as e:
        err_ins = int(
            _append_raw(
                session,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTION_PROVIDER_SLACK,
                run_id=run_id,
                source_trigger=source_trigger,
                resource_type="slack.api_error",
                external_id="slack_web_api",
                api_endpoint=f"{slack_api_base}/ingestion_error",
                query_params={"error": True},
                payload_body={
                    **core_envelope_fields(
                        connector=CONNECTION_PROVIDER_SLACK,
                        connection_id=connection_id,
                        source_object_type="slack.api_error",
                        source_object_id="slack_web_api",
                    ),
                    "error": str(e),
                },
                http_status=502,
                idempotency_key=_idem_key(ctx, run_id, "slack:api_error"),
            )
        )
        n_ins += err_ins

    chosen_types = [
        t.strip()
        for t in settings.cortex_slack_conversation_types.split(",")
        if isinstance(t, str) and t.strip()
    ]
    if not chosen_types:
        chosen_types = ["public_channel", "private_channel"]

    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_SLACK,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": _utc_now().isoformat(),
            "slack_user_pages": user_pages,
            "slack_user_members_seen": user_members,
            "slack_conversation_pages": channel_pages,
            "slack_conversations_seen": channel_rows,
            "slack_messages_seen": message_rows,
            "slack_message_replies_seen": reply_rows,
            "slack_threads_seen": thread_rows,
            "slack_reactions_seen": reaction_rows,
            "slack_files_seen": file_rows,
            "streams": {
                "slack": {
                    "users": {
                        "cursor_owner": "slack.user",
                        "pages_fetched": user_pages,
                    },
                    "conversations": {
                        "cursor_owner": "slack.conversation",
                        "pages_fetched": channel_pages,
                    },
                    "messages": {
                        "cursor_owner": "slack.message",
                        "rows_seen": message_rows,
                    },
                    "message_replies": {
                        "cursor_owner": "slack.message_reply",
                        "rows_seen": reply_rows,
                        "thread_pages_seen": thread_pages,
                    },
                    "threads": {
                        "cursor_owner": "slack.thread",
                        "rows_seen": thread_rows,
                    },
                    "reactions": {
                        "cursor_owner": "slack.reaction",
                        "rows_seen": reaction_rows,
                    },
                    "files": {
                        "cursor_owner": "slack.file",
                        "rows_seen": file_rows,
                    },
                    "channels": channel_patch_map,
                    "channel_ring_index": next_ring_index if "next_ring_index" in locals() else ring_index,
                    "conversation_types": chosen_types,
                    "resume_required": budget_exhausted,
                    "time_budget_seconds": settings.cortex_slack_channel_time_budget_seconds,
                }
            },
        },
        sync_mode=ctx.sync_mode,
    )
    return n_ins


def _notion_sync(
    session: Session,
    settings: Settings,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    class _NotionSyncApiError(RuntimeError):
        pass

    def _notion_headers(token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Notion-Version": settings.notion_version,
            "Content-Type": "application/json",
        }

    def _notion_post(path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{settings.notion_api_base_url().rstrip('/')}/{path.lstrip('/')}"
        try:
            resp = httpx.post(url, headers=_notion_headers(token), json=payload, timeout=60.0)
        except httpx.HTTPError as e:
            raise _NotionSyncApiError(f"notion request failed ({path}): {e}") from e
        if resp.is_error:
            raise _NotionSyncApiError(f"notion {path} http {resp.status_code}: {(resp.text or '')[:300]}")
        try:
            data = resp.json()
        except ValueError:
            raise _NotionSyncApiError(f"notion {path} returned non-json")
        if not isinstance(data, dict):
            raise _NotionSyncApiError(f"notion {path} invalid json shape")
        return data

    def _notion_get(path: str, token: str) -> dict[str, Any]:
        url = f"{settings.notion_api_base_url().rstrip('/')}/{path.lstrip('/')}"
        try:
            resp = httpx.get(url, headers=_notion_headers(token), timeout=60.0)
        except httpx.HTTPError as e:
            raise _NotionSyncApiError(f"notion request failed ({path}): {e}") from e
        if resp.is_error:
            raise _NotionSyncApiError(f"notion {path} http {resp.status_code}: {(resp.text or '')[:300]}")
        try:
            data = resp.json()
        except ValueError:
            raise _NotionSyncApiError(f"notion {path} returned non-json")
        if not isinstance(data, dict):
            raise _NotionSyncApiError(f"notion {path} invalid json shape")
        return data

    def _extract_last_edited(value: dict[str, Any]) -> str | None:
        ts = value.get("last_edited_time")
        if isinstance(ts, str) and ts.strip():
            return ts
        return None

    def _iso_max(current: str | None, candidate: str | None) -> str | None:
        if not isinstance(candidate, str) or not candidate.strip():
            return current
        if current is None or candidate > current:
            return candidate
        return current

    def _mock_notion_payload() -> dict[str, Any]:
        base = settings.vector_mock_connector_base_url.rstrip("/")
        try:
            resp = httpx.get(f"{base}/admin/dataset/full", timeout=30.0)
            resp.raise_for_status()
            js = resp.json()
        except Exception as e:
            raise _NotionSyncApiError(f"mock notion dataset fetch failed: {e}") from e
        if not isinstance(js, dict):
            raise _NotionSyncApiError("mock notion dataset shape invalid")
        notion = js.get("notion")
        if not isinstance(notion, dict):
            raise _NotionSyncApiError("mock notion dataset missing notion key")
        return notion

    def _state_map(root: dict[str, Any], key: str) -> dict[str, Any]:
        val = root.get(key)
        return val if isinstance(val, dict) else {}

    scope_ck = ctx.checkpoint_scope_key()
    existing_ckpt = _read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_NOTION,
        scope_key=scope_ck,
    )
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        return _generic_scope_ping(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_NOTION,
            run_id=run_id,
            source_trigger=source_trigger,
            label="no_notion_detail",
        )
    token = link.detail.access_token
    notion_base = settings.notion_api_base_url().rstrip("/")
    n_ins = 0
    search_rows = 0
    page_rows = 0
    database_rows = 0
    database_row_rows = 0
    block_rows = 0
    search_pages = 0
    db_query_pages = 0
    block_pages = 0
    budget_exhausted = False
    start_t = time.monotonic()

    streams_existing = _checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    notion_existing = (
        streams_existing.get("notion")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("notion"), dict)
        else {}
    )
    search_existing = _state_map(notion_existing, "search")
    db_rows_existing = _state_map(notion_existing, "database_rows")
    db_existing_map = _state_map(db_rows_existing, "databases")
    blocks_existing = _state_map(notion_existing, "blocks")
    block_parents_existing = _state_map(blocks_existing, "parents")

    search_cursor_raw = search_existing.get("next_cursor")
    search_cursor = search_cursor_raw if isinstance(search_cursor_raw, str) and search_cursor_raw.strip() else None
    search_watermark_raw = search_existing.get("last_edited_watermark")
    search_watermark = (
        search_watermark_raw if isinstance(search_watermark_raw, str) and search_watermark_raw.strip() else None
    )
    latest_edited = search_watermark

    databases_discovered: set[str] = set()
    pages_discovered: set[str] = set()
    database_patch_map: dict[str, Any] = {}
    block_parent_patch_map: dict[str, Any] = {}

    def _append_notion_row(
        *,
        resource_type: str,
        external_id: str,
        api_endpoint: str,
        query_params: dict[str, Any],
        source_object_type: str,
        payload_key: str,
        payload_value: dict[str, Any],
    ) -> bool:
        return _append_raw(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_NOTION,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type=resource_type,
            external_id=external_id[:512],
            api_endpoint=api_endpoint[:512],
            query_params=query_params,
            payload_body={
                **core_envelope_fields(
                    connector=CONNECTION_PROVIDER_NOTION,
                    connection_id=connection_id,
                    source_object_type=source_object_type,
                    source_object_id=external_id[:512],
                ),
                payload_key: payload_value,
            },
            http_status=200,
            idempotency_key=_idem_key(ctx, run_id, f"notion:{resource_type}:{external_id}"),
        )

    if settings.vector_use_mock_connectors:
        notion_payload = _mock_notion_payload()
        sampled_pages = [p for p in notion_payload.get("sampled_pages", []) if isinstance(p, dict)]
        start_idx = 0
        if search_cursor is not None and search_cursor.startswith("mock:"):
            try:
                start_idx = max(0, int(search_cursor.split(":", 1)[1]))
            except ValueError:
                start_idx = 0
        page_size = settings.cortex_notion_search_page_size
        cursor_idx = start_idx
        for _ in range(settings.cortex_notion_search_max_pages_per_sync):
            chunk = sampled_pages[cursor_idx : cursor_idx + page_size]
            if not chunk:
                search_cursor = None
                break
            search_pages += 1
            for item in chunk:
                rid = item.get("id")
                if not isinstance(rid, str) or not rid:
                    continue
                last_edited = _extract_last_edited(item)
                latest_edited = _iso_max(latest_edited, last_edited)
                if (
                    ctx.sync_mode == "incremental"
                    and isinstance(search_watermark, str)
                    and isinstance(last_edited, str)
                    and last_edited <= search_watermark
                ):
                    continue
                if _append_notion_row(
                    resource_type="notion.search_result",
                    external_id=rid,
                    api_endpoint=f"{settings.vector_mock_connector_base_url.rstrip('/')}/admin/dataset/full",
                    query_params={"source": "mock_dataset_search", "offset": cursor_idx},
                    source_object_type="notion.search_result",
                    payload_key="result",
                    payload_value=item,
                ):
                    n_ins += 1
                    search_rows += 1
                if _append_notion_row(
                    resource_type="notion.page",
                    external_id=rid,
                    api_endpoint=f"{settings.vector_mock_connector_base_url.rstrip('/')}/admin/dataset/full",
                    query_params={"source": "mock_dataset_page"},
                    source_object_type="notion.page",
                    payload_key="page",
                    payload_value=item,
                ):
                    n_ins += 1
                    page_rows += 1
                pages_discovered.add(rid)
            cursor_idx += len(chunk)
            search_cursor = f"mock:{cursor_idx}" if cursor_idx < len(sampled_pages) else None
            if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
                budget_exhausted = True
                break

        db_map = notion_payload.get("databases")
        db_ids = sorted(db_map.keys()) if isinstance(db_map, dict) else []
        rows_by_db: dict[str, int] = {}
        for row in notion_payload.get("database_rows", []):
            if not isinstance(row, dict):
                continue
            dbid = row.get("database_id")
            if isinstance(dbid, str) and dbid.strip():
                rows_by_db[dbid] = rows_by_db.get(dbid, 0) + 1
        if db_ids:
            db_ids = sorted(db_ids, key=lambda x: (-rows_by_db.get(x, 0), x))
        db_ids = db_ids[: settings.cortex_notion_databases_per_sync]
        for dbid in db_ids:
            if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
                budget_exhausted = True
                break
            db_obj = db_map.get(dbid) if isinstance(db_map, dict) else None
            if not isinstance(db_obj, dict):
                continue
            databases_discovered.add(dbid)
            if _append_notion_row(
                resource_type="notion.database",
                external_id=dbid,
                api_endpoint=f"{settings.vector_mock_connector_base_url.rstrip('/')}/admin/dataset/full",
                query_params={"source": "mock_dataset_database"},
                source_object_type="notion.database",
                payload_key="database",
                payload_value={"id": dbid, **db_obj},
            ):
                n_ins += 1
                database_rows += 1

            rows = [r for r in notion_payload.get("database_rows", []) if isinstance(r, dict) and r.get("database_id") == dbid]
            db_state = _state_map(db_existing_map, dbid)
            db_cursor_raw = db_state.get("next_cursor")
            db_start = 0
            if isinstance(db_cursor_raw, str) and db_cursor_raw.startswith("mock:"):
                try:
                    db_start = max(0, int(db_cursor_raw.split(":", 1)[1]))
                except ValueError:
                    db_start = 0
            row_page_size = settings.cortex_notion_database_query_page_size
            row_cursor = db_start
            pages_for_db = 0
            rows_for_db = 0
            for _ in range(settings.cortex_notion_database_query_max_pages_per_database):
                row_chunk = rows[row_cursor : row_cursor + row_page_size]
                if not row_chunk:
                    break
                pages_for_db += 1
                db_query_pages += 1
                for row in row_chunk:
                    row_id = row.get("id")
                    if not isinstance(row_id, str) or not row_id:
                        continue
                    if _append_notion_row(
                        resource_type="notion.database_row",
                        external_id=row_id,
                        api_endpoint=f"{settings.vector_mock_connector_base_url.rstrip('/')}/admin/dataset/full",
                        query_params={"database_id": dbid, "source": "mock_dataset_database_rows"},
                        source_object_type="notion.database_row",
                        payload_key="row",
                        payload_value=row,
                    ):
                        n_ins += 1
                        database_row_rows += 1
                        rows_for_db += 1
                    pages_discovered.add(row_id)
                row_cursor += len(row_chunk)
                if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
                    budget_exhausted = True
                    break
            database_patch_map[dbid] = {
                "cursor_owner": "notion.database_row",
                "next_cursor": f"mock:{row_cursor}" if row_cursor < len(rows) else None,
                "pages_fetched_last_run": pages_for_db,
                "rows_seen_last_run": rows_for_db,
            }

        blocks = [b for b in notion_payload.get("blocks", []) if isinstance(b, dict)]
        blocks_by_parent: dict[str, list[dict[str, Any]]] = {}
        for block in blocks:
            parent_id = block.get("parent_id")
            if not isinstance(parent_id, str) or not parent_id.strip():
                continue
            blocks_by_parent.setdefault(parent_id.strip(), []).append(block)
        parent_queue = list(sorted(set(pages_discovered) | set(db_ids)))
        visited_parents: set[str] = set()
        while parent_queue and len(visited_parents) < settings.cortex_notion_blocks_parents_per_sync:
            parent_id = parent_queue.pop(0)
            if parent_id in visited_parents:
                continue
            visited_parents.add(parent_id)
            parent_blocks = blocks_by_parent.get(parent_id, [])
            rows_for_parent = 0
            for block in parent_blocks:
                bid = block.get("id")
                if not isinstance(bid, str) or not bid.strip():
                    continue
                if _append_notion_row(
                    resource_type="notion.block",
                    external_id=bid,
                    api_endpoint=f"{settings.vector_mock_connector_base_url.rstrip('/')}/admin/dataset/full",
                    query_params={"parent_id": parent_id, "source": "mock_dataset_blocks"},
                    source_object_type="notion.block",
                    payload_key="block",
                    payload_value={"parent_id": parent_id, **block},
                ):
                    n_ins += 1
                    block_rows += 1
                    rows_for_parent += 1
                if block.get("has_children") is True:
                    parent_queue.append(bid)
            block_pages += 1
            block_parent_patch_map[parent_id] = {
                "cursor_owner": "notion.block",
                "next_cursor": None,
                "pages_fetched_last_run": 1,
                "rows_seen_last_run": rows_for_parent,
            }
    else:
        try:
            for _ in range(settings.cortex_notion_search_max_pages_per_sync):
                body: dict[str, Any] = {
                    "page_size": min(settings.cortex_notion_search_page_size, 100),
                    "sort": {"timestamp": "last_edited_time", "direction": "descending"},
                }
                if search_cursor:
                    body["start_cursor"] = search_cursor
                search_resp = _notion_post("/search", token, body)
                results = (
                    [r for r in search_resp.get("results", []) if isinstance(r, dict)]
                    if isinstance(search_resp.get("results"), list)
                    else []
                )
                search_pages += 1
                for result in results:
                    rid = result.get("id")
                    if not isinstance(rid, str) or not rid:
                        continue
                    last_edited = _extract_last_edited(result)
                    latest_edited = _iso_max(latest_edited, last_edited)
                    if (
                        ctx.sync_mode == "incremental"
                        and isinstance(search_watermark, str)
                        and isinstance(last_edited, str)
                        and last_edited <= search_watermark
                    ):
                        continue
                    if _append_notion_row(
                        resource_type="notion.search_result",
                        external_id=rid,
                        api_endpoint=f"{notion_base}/search",
                        query_params={"start_cursor": search_cursor or "", "page_size": body["page_size"]},
                        source_object_type="notion.search_result",
                        payload_key="result",
                        payload_value=result,
                    ):
                        n_ins += 1
                        search_rows += 1

                    obj_t = result.get("object")
                    if obj_t == "page":
                        pages_discovered.add(rid)
                        if _append_notion_row(
                            resource_type="notion.page",
                            external_id=rid,
                            api_endpoint=f"{notion_base}/pages/{rid}",
                            query_params={"source": "search"},
                            source_object_type="notion.page",
                            payload_key="page",
                            payload_value=result,
                        ):
                            n_ins += 1
                            page_rows += 1
                    elif obj_t == "database":
                        databases_discovered.add(rid)
                has_more = bool(search_resp.get("has_more"))
                next_cursor_raw = search_resp.get("next_cursor")
                search_cursor = next_cursor_raw if isinstance(next_cursor_raw, str) and next_cursor_raw else None
                if not has_more:
                    search_cursor = None
                    break
                if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
                    budget_exhausted = True
                    break
        except _NotionSyncApiError as e:
            _logger.warning("notion search failed: %s", e)

        db_ids = sorted(databases_discovered)[: settings.cortex_notion_databases_per_sync]
        for dbid in db_ids:
            if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
                budget_exhausted = True
                break
            db_obj: dict[str, Any] | None = None
            try:
                db_obj = _notion_get(f"/databases/{dbid}", token)
            except _NotionSyncApiError:
                db_obj = None
            if db_obj is not None:
                if _append_notion_row(
                    resource_type="notion.database",
                    external_id=dbid,
                    api_endpoint=f"{notion_base}/databases/{dbid}",
                    query_params={},
                    source_object_type="notion.database",
                    payload_key="database",
                    payload_value=db_obj,
                ):
                    n_ins += 1
                    database_rows += 1

            db_state = _state_map(db_existing_map, dbid)
            db_cursor_raw = db_state.get("next_cursor")
            db_cursor = db_cursor_raw if isinstance(db_cursor_raw, str) and db_cursor_raw.strip() else None
            db_rows_for_db = 0
            db_pages_for_db = 0
            try:
                for _ in range(settings.cortex_notion_database_query_max_pages_per_database):
                    payload: dict[str, Any] = {
                        "page_size": min(settings.cortex_notion_database_query_page_size, 100)
                    }
                    if db_cursor:
                        payload["start_cursor"] = db_cursor
                    query_resp = _notion_post(f"/databases/{dbid}/query", token, payload)
                    db_rows = (
                        [r for r in query_resp.get("results", []) if isinstance(r, dict)]
                        if isinstance(query_resp.get("results"), list)
                        else []
                    )
                    db_pages_for_db += 1
                    db_query_pages += 1
                    for row in db_rows:
                        row_id = row.get("id")
                        if not isinstance(row_id, str) or not row_id:
                            continue
                        pages_discovered.add(row_id)
                        if _append_notion_row(
                            resource_type="notion.database_row",
                            external_id=row_id,
                            api_endpoint=f"{notion_base}/databases/{dbid}/query",
                            query_params={"start_cursor": db_cursor or ""},
                            source_object_type="notion.database_row",
                            payload_key="row",
                            payload_value=row,
                        ):
                            n_ins += 1
                            database_row_rows += 1
                            db_rows_for_db += 1
                    has_more = bool(query_resp.get("has_more"))
                    next_cursor_raw = query_resp.get("next_cursor")
                    db_cursor = next_cursor_raw if isinstance(next_cursor_raw, str) and next_cursor_raw else None
                    if not has_more:
                        db_cursor = None
                        break
                    if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
                        budget_exhausted = True
                        break
            except _NotionSyncApiError:
                pass
            database_patch_map[dbid] = {
                "cursor_owner": "notion.database_row",
                "next_cursor": db_cursor,
                "pages_fetched_last_run": db_pages_for_db,
                "rows_seen_last_run": db_rows_for_db,
            }

        parent_queue = list(sorted(pages_discovered))
        visited_parents: set[str] = set()
        while parent_queue and len(visited_parents) < settings.cortex_notion_blocks_parents_per_sync:
            if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
                budget_exhausted = True
                break
            parent_id = parent_queue.pop(0)
            if parent_id in visited_parents:
                continue
            visited_parents.add(parent_id)
            parent_state = _state_map(block_parents_existing, parent_id)
            block_cursor_raw = parent_state.get("next_cursor")
            block_cursor = block_cursor_raw if isinstance(block_cursor_raw, str) and block_cursor_raw.strip() else None
            rows_for_parent = 0
            pages_for_parent = 0
            for _ in range(settings.cortex_notion_blocks_max_pages_per_parent):
                try:
                    body = {"page_size": min(settings.cortex_notion_blocks_page_size, 100)}
                    if block_cursor:
                        body["start_cursor"] = block_cursor
                    block_resp = _notion_get(
                        f"/blocks/{parent_id}/children"
                        + (f"?page_size={body['page_size']}&start_cursor={block_cursor}" if block_cursor else f"?page_size={body['page_size']}"),
                        token,
                    )
                except _NotionSyncApiError:
                    break
                blocks = (
                    [b for b in block_resp.get("results", []) if isinstance(b, dict)]
                    if isinstance(block_resp.get("results"), list)
                    else []
                )
                pages_for_parent += 1
                block_pages += 1
                for block in blocks:
                    bid = block.get("id")
                    if not isinstance(bid, str) or not bid:
                        continue
                    if _append_notion_row(
                        resource_type="notion.block",
                        external_id=bid,
                        api_endpoint=f"{notion_base}/blocks/{parent_id}/children",
                        query_params={"start_cursor": block_cursor or "", "parent_id": parent_id},
                        source_object_type="notion.block",
                        payload_key="block",
                        payload_value={"parent_id": parent_id, **block},
                    ):
                        n_ins += 1
                        block_rows += 1
                        rows_for_parent += 1
                    if block.get("has_children") is True:
                        parent_queue.append(bid)
                has_more = bool(block_resp.get("has_more"))
                next_cursor_raw = block_resp.get("next_cursor")
                block_cursor = next_cursor_raw if isinstance(next_cursor_raw, str) and next_cursor_raw else None
                if not has_more:
                    block_cursor = None
                    break
                if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
                    budget_exhausted = True
                    break
            block_parent_patch_map[parent_id] = {
                "cursor_owner": "notion.block",
                "next_cursor": block_cursor,
                "pages_fetched_last_run": pages_for_parent,
                "rows_seen_last_run": rows_for_parent,
            }

    ws = link.detail.workspace_id or str(link.connection.id)
    ping_status, ping_payload = 200, {"workspace": ws}
    if _append_raw(
        session,
        ctx=ctx,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_NOTION,
        run_id=run_id,
        source_trigger=source_trigger,
        resource_type="notion.scope_ping",
        external_id=str(ws)[:512],
        api_endpoint=f"{notion_base}/search",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector=CONNECTION_PROVIDER_NOTION,
                connection_id=connection_id,
                source_object_type="notion.scope_ping",
                source_object_id=str(ws)[:512],
            ),
            "workspace_id": link.detail.workspace_id,
            "workspace_name": link.detail.workspace_name,
            "connectivity": ping_payload,
        },
        http_status=ping_status if ping_status >= 100 else 200,
        idempotency_key=_idem_key(ctx, run_id, f"notion:scope_ping:{ws}"),
    ):
        n_ins += 1

    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_NOTION,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": _utc_now().isoformat(),
            "notion_search_results_written": search_rows,
            "notion_pages_written": page_rows,
            "notion_databases_written": database_rows,
            "notion_database_rows_written": database_row_rows,
            "notion_blocks_written": block_rows,
            "streams": {
                "notion": {
                    "search": {
                        "cursor_owner": "notion.search_result",
                        "next_cursor": search_cursor,
                        "pages_fetched_last_run": search_pages,
                        "rows_seen_last_run": search_rows,
                        "last_edited_watermark": latest_edited,
                    },
                    "pages": {"cursor_owner": "notion.page", "rows_seen_last_run": page_rows},
                    "databases": {"cursor_owner": "notion.database", "rows_seen_last_run": database_rows},
                    "database_rows": {
                        "cursor_owner": "notion.database_row",
                        "rows_seen_last_run": database_row_rows,
                        "pages_fetched_last_run": db_query_pages,
                        "databases": database_patch_map,
                    },
                    "blocks": {
                        "cursor_owner": "notion.block",
                        "rows_seen_last_run": block_rows,
                        "pages_fetched_last_run": block_pages,
                        "parents": block_parent_patch_map,
                    },
                    "scope_ping": {
                        "cursor_owner": "notion.scope_ping",
                        "workspace": ws,
                    },
                    "resume_required": budget_exhausted,
                    "time_budget_seconds": settings.cortex_notion_time_budget_seconds,
                }
            },
        },
        sync_mode=ctx.sync_mode,
    )
    return n_ins


def _calls_sync(
    session: Session,
    settings: Settings,
    *,
    ctx: IngestionSyncContext,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    class _CallsSyncApiError(RuntimeError):
        pass

    def _calls_get_json(url: str, headers: dict[str, str], params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            resp = httpx.get(url, headers=headers, params=params, timeout=60.0)
        except httpx.HTTPError as e:
            raise _CallsSyncApiError(f"calls request failed: {e}") from e
        if resp.status_code >= 400:
            raise _CallsSyncApiError(f"calls http {resp.status_code}: {(resp.text or '')[:300]}")
        try:
            payload = resp.json()
        except ValueError:
            raise _CallsSyncApiError("calls endpoint returned non-json")
        if not isinstance(payload, dict):
            raise _CallsSyncApiError("calls endpoint returned invalid json shape")
        return payload

    def _event_updated_at(event: dict[str, Any]) -> str | None:
        for key in ("updated", "updated_at", "last_modified", "start"):
            val = event.get(key)
            if isinstance(val, str) and val.strip():
                return val
        return None

    def _iso_max(current: str | None, candidate: str | None) -> str | None:
        if not isinstance(candidate, str) or not candidate.strip():
            return current
        if current is None or candidate > current:
            return candidate
        return current

    def _state_map(root: dict[str, Any], key: str) -> dict[str, Any]:
        val = root.get(key)
        return val if isinstance(val, dict) else {}

    def _append_calls_row(
        *,
        resource_type: str,
        external_id: str,
        api_endpoint: str,
        query_params: dict[str, Any],
        source_object_type: str,
        payload_key: str,
        payload_value: dict[str, Any],
    ) -> bool:
        return _append_raw(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_CALLS,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type=resource_type,
            external_id=external_id[:512],
            api_endpoint=api_endpoint[:512],
            query_params=query_params,
            payload_body={
                **core_envelope_fields(
                    connector=CONNECTION_PROVIDER_CALLS,
                    connection_id=connection_id,
                    source_object_type=source_object_type,
                    source_object_id=external_id[:512],
                ),
                payload_key: payload_value,
            },
            http_status=200,
            idempotency_key=_idem_key(ctx, run_id, f"calls:{resource_type}:{external_id}"),
        )

    def _ingest_event(event: dict[str, Any], *, endpoint: str, query_params: dict[str, Any]) -> tuple[int, int, int, int, int]:
        inserted = 0
        participants_written = 0
        transcripts_written = 0
        transcript_segments_written = 0
        recordings_written = 0

        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            return (0, 0, 0, 0, 0)

        if _append_calls_row(
            resource_type="calls.meeting",
            external_id=event_id,
            api_endpoint=endpoint,
            query_params=query_params,
            source_object_type="calls.meeting",
            payload_key="meeting",
            payload_value=event,
        ):
            inserted += 1

        attendees = event.get("attendees")
        if isinstance(attendees, list):
            for idx, attendee in enumerate(attendees):
                if not isinstance(attendee, dict):
                    continue
                raw_email = attendee.get("email")
                email = raw_email.strip().lower() if isinstance(raw_email, str) and raw_email.strip() else f"idx-{idx}"
                participant_external_id = f"{event_id}:{email}"[:512]
                participant_payload = {"meeting_id": event_id, "participant": attendee}
                if _append_calls_row(
                    resource_type="calls.participant",
                    external_id=participant_external_id,
                    api_endpoint=endpoint,
                    query_params=query_params,
                    source_object_type="calls.participant",
                    payload_key="participant_record",
                    payload_value=participant_payload,
                ):
                    inserted += 1
                    participants_written += 1

        transcript = event.get("transcript")
        if not isinstance(transcript, dict):
            ext_props = event.get("extendedProperties")
            private_props = ext_props.get("private") if isinstance(ext_props, dict) else None
            raw = private_props.get("vector_transcript_json") if isinstance(private_props, dict) else None
            if isinstance(raw, str) and raw.strip():
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        transcript = parsed
                except ValueError:
                    transcript = None
        if isinstance(transcript, dict):
            transcript_external_id = f"{event_id}:transcript"
            tid = transcript_external_id
            segments = transcript.get("segments")
            seg_list = [s for s in segments if isinstance(s, dict)] if isinstance(segments, list) else []
            seg_sorted = sorted(seg_list, key=_calls_transcript_segment_sort_key)
            transcript_enriched = {**transcript, "segments": seg_sorted}
            transcript_payload = {
                "meeting_id": event_id,
                "transcript_id": tid,
                "segment_count": len(seg_sorted),
                "transcript": transcript_enriched,
            }
            if _append_calls_row(
                resource_type="calls.transcript",
                external_id=transcript_external_id,
                api_endpoint=endpoint,
                query_params=query_params,
                source_object_type="calls.transcript",
                payload_key="transcript_record",
                payload_value=transcript_payload,
            ):
                inserted += 1
                transcripts_written += 1
            if seg_sorted:
                for s_idx, seg in enumerate(seg_sorted):
                    seg_external_id = f"{event_id}:seg:{s_idx}"
                    seg_payload = {
                        "meeting_id": event_id,
                        "transcript_id": tid,
                        "segment_index": s_idx,
                        "segment": seg,
                    }
                    if _append_calls_row(
                        resource_type="calls.transcript_segment",
                        external_id=seg_external_id,
                        api_endpoint=endpoint,
                        query_params=query_params,
                        source_object_type="calls.transcript_segment",
                        payload_key="segment_record",
                        payload_value=seg_payload,
                    ):
                        inserted += 1
                        transcript_segments_written += 1

        recording = event.get("recording")
        if not isinstance(recording, dict):
            ext_props = event.get("extendedProperties")
            private_props = ext_props.get("private") if isinstance(ext_props, dict) else None
            raw = private_props.get("vector_recording_json") if isinstance(private_props, dict) else None
            if isinstance(raw, str) and raw.strip():
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        recording = parsed
                except ValueError:
                    recording = None
        if isinstance(recording, dict):
            rec_id = recording.get("recording_id")
            rec_suffix = rec_id if isinstance(rec_id, str) and rec_id.strip() else "recording"
            recording_external_id = f"{event_id}:{rec_suffix}"[:512]
            recording_payload = {"meeting_id": event_id, "recording": recording}
            if _append_calls_row(
                resource_type="calls.recording",
                external_id=recording_external_id,
                api_endpoint=endpoint,
                query_params=query_params,
                source_object_type="calls.recording",
                payload_key="recording_record",
                payload_value=recording_payload,
            ):
                inserted += 1
                recordings_written += 1

        return (
            inserted,
            participants_written,
            transcripts_written,
            transcript_segments_written,
            recordings_written,
        )

    scope_ck = ctx.checkpoint_scope_key()
    existing_ckpt = _read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_CALLS,
        scope_key=scope_ck,
    )
    link = calls_repo.get_calls_connection_for_tenant(session, tenant_id)
    if link is None:
        return _generic_scope_ping(
            session,
            ctx=ctx,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_CALLS,
            run_id=run_id,
            source_trigger=source_trigger,
            label="no_calls_detail",
        )
    token = link.detail.access_token
    n_ins = 0
    meetings_written = 0
    participants_written = 0
    transcripts_written = 0
    transcript_segments_written = 0
    recordings_written = 0
    pages_fetched = 0
    budget_exhausted = False
    start_t = time.monotonic()

    streams_existing = _checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
    calls_existing = (
        streams_existing.get("calls")
        if isinstance(streams_existing, dict) and isinstance(streams_existing.get("calls"), dict)
        else {}
    )
    events_existing = _state_map(calls_existing, "events")
    next_cursor_raw = events_existing.get("next_cursor")
    next_cursor = next_cursor_raw if isinstance(next_cursor_raw, str) and next_cursor_raw.strip() else None
    watermark_raw = events_existing.get("updated_watermark")
    updated_watermark = watermark_raw if isinstance(watermark_raw, str) and watermark_raw.strip() else None
    max_seen_updated = updated_watermark

    headers = {} if settings.vector_use_mock_connectors else {"Authorization": f"Bearer {token}"}
    calendar_base = settings.calls_google_calendar_events_base_url().rstrip("/")
    calendar_id = "primary"
    page_token = next_cursor
    for _ in range(settings.cortex_calls_events_max_pages_per_sync):
        params: dict[str, Any] = {
            "singleEvents": "true",
            "maxResults": settings.cortex_calls_events_page_size,
            "orderBy": "updated",
        }
        if isinstance(page_token, str) and page_token:
            params["pageToken"] = page_token
        if ctx.sync_mode == "incremental" and isinstance(updated_watermark, str) and updated_watermark:
            params["updatedMin"] = updated_watermark

        endpoint = f"{calendar_base}/calendars/{calendar_id}/events"
        data = _calls_get_json(endpoint, headers=headers, params=params)
        page_items = [ev for ev in data.get("items", []) if isinstance(ev, dict)]
        pages_fetched += 1
        for event in page_items:
            event_updated = _event_updated_at(event)
            max_seen_updated = _iso_max(max_seen_updated, event_updated)
            inserted, p_cnt, t_cnt, s_cnt, r_cnt = _ingest_event(
                event,
                endpoint=endpoint,
                query_params={"pageToken": page_token or "", "updatedMin": params.get("updatedMin", "")},
            )
            if inserted > 0:
                meetings_written += 1
            n_ins += inserted
            participants_written += p_cnt
            transcripts_written += t_cnt
            transcript_segments_written += s_cnt
            recordings_written += r_cnt
        raw_next = data.get("nextPageToken")
        page_token = raw_next if isinstance(raw_next, str) and raw_next else None
        next_cursor = page_token
        if page_token is None:
            break
        if time.monotonic() - start_t >= settings.cortex_calls_time_budget_seconds:
            budget_exhausted = True
            break

    provider_label = link.detail.provider_email or link.detail.provider_user_id or "calls_connected"
    if _append_raw(
        session,
        ctx=ctx,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_CALLS,
        run_id=run_id,
        source_trigger=source_trigger,
        resource_type="calls.scope_ping",
        external_id=str(link.connection.id),
        api_endpoint="internal://calls/scope_ping",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector=CONNECTION_PROVIDER_CALLS,
                connection_id=connection_id,
                source_object_type="calls.scope_ping",
                source_object_id=str(link.connection.id),
            ),
            "provider_user_id": link.detail.provider_user_id,
            "provider_email": link.detail.provider_email,
            "connectivity": {"label": provider_label},
        },
        http_status=200,
        idempotency_key=_idem_key(ctx, run_id, f"calls:scope_ping:{link.connection.id}"),
    ):
        n_ins += 1

    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_CALLS,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": _utc_now().isoformat(),
            "calls_meetings_written": meetings_written,
            "calls_participants_written": participants_written,
            "calls_transcripts_written": transcripts_written,
            "calls_transcript_segments_written": transcript_segments_written,
            "calls_recordings_written": recordings_written,
            "streams": {
                "calls": {
                    "events": {
                        "cursor_owner": "calls.meeting",
                        "next_cursor": next_cursor,
                        "pages_fetched_last_run": pages_fetched,
                        "rows_seen_last_run": meetings_written,
                        "updated_watermark": max_seen_updated,
                    },
                    "participants": {
                        "cursor_owner": "calls.participant",
                        "rows_seen_last_run": participants_written,
                    },
                    "transcripts": {
                        "cursor_owner": "calls.transcript",
                        "rows_seen_last_run": transcripts_written,
                    },
                    "transcript_segments": {
                        "cursor_owner": "calls.transcript_segment",
                        "rows_seen_last_run": transcript_segments_written,
                    },
                    "recordings": {
                        "cursor_owner": "calls.recording",
                        "rows_seen_last_run": recordings_written,
                    },
                    "scope_ping": {
                        "cursor_owner": "calls.scope_ping",
                        "provider_email": link.detail.provider_email,
                    },
                    "resume_required": budget_exhausted,
                    "time_budget_seconds": settings.cortex_calls_time_budget_seconds,
                }
            },
        },
        sync_mode=ctx.sync_mode,
    )
    return n_ins


def execute_connector_sync(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connector_id: str,
    source_trigger: str,
    ingestion_sync_context: IngestionSyncContext | None = None,
    connection_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Create an ingestion run, fetch normalized snapshots, persist raw rows, update checkpoint."""
    ctx = ingestion_sync_context or IngestionSyncContext.live_incremental()
    ctx.validate()

    conn = _resolve_connection(
        session,
        tenant_id,
        connector_id,
        connection_id=connection_id,
    )
    phase = PHASE_STEP3 if ctx.replay_mode else PHASE_STEP1
    if conn is None:
        log_ingestion_event(
            _logger,
            logging.INFO,
            "cortex sync skipped — no active tenant_connection",
            task_name="execute_connector_sync",
            phase=phase,
            outcome="skipped",
            tenant_id=str(tenant_id),
            connector=connector_id,
        )
        return {"status": "skipped", "reason": "no_connection", "connector": connector_id}

    run_id = uuid.uuid4()
    started = _utc_now()
    run = IngestionRun(
        id=run_id,
        tenant_id=tenant_id,
        connection_id=conn.id,
        connector=connector_id,
        source_trigger=source_trigger,
        sync_mode=ctx.sync_mode,
        replay_mode=ctx.replay_mode,
        replay_job_id=ctx.replay_job_id,
        replay_version=ctx.replay_version,
        status=RUN_RUNNING,
        started_at=started,
    )
    session.add(run)
    session.flush()

    log_ingestion_event(
        _logger,
        logging.INFO,
        "cortex sync started",
        task_name="execute_connector_sync",
        phase=phase,
        outcome="started",
        run_id=str(run_id),
        tenant_id=str(tenant_id),
        connector=connector_id,
        run_status=RUN_RUNNING,
        replay_job_id=str(ctx.replay_job_id) if ctx.replay_job_id else "",
        sync_mode=ctx.sync_mode,
    )

    records_written = 0
    try:
        if connector_id == CONNECTION_PROVIDER_GITHUB:
            records_written = _github_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_LINEAR:
            records_written = _linear_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_SLACK:
            records_written = _slack_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_NOTION:
            records_written = _notion_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_CALLS:
            records_written = _calls_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        else:
            raise ValueError(f"unsupported connector for sync: {connector_id!r}")

        finished = _utc_now()
        # Defense-in-depth: always materialize/update the scoped checkpoint row at run
        # completion so live/replay scope isolation is observable even if a connector
        # branch produced zero records or skipped its detailed checkpoint patch path.
        _upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=conn.id,
            connector=connector_id,
            scope_key=ctx.checkpoint_scope_key(),
            patch={"last_incremental_at": finished.isoformat()},
            sync_mode=ctx.sync_mode,
        )
        run.status = RUN_COMPLETED
        run.finished_at = finished
        run.stats = {
            "records_written": records_written,
            "sync_mode": ctx.sync_mode,
            "checkpoint_scope": ctx.checkpoint_scope_key(),
        }
        # Ensure new raw/checkpoint rows are materialized even when caller uses a
        # non-autoflush session and immediately queries in the same transaction.
        session.flush()
        log_ingestion_event(
            _logger,
            logging.INFO,
            "cortex sync completed",
            task_name="execute_connector_sync",
            phase=phase,
            outcome="completed",
            run_id=str(run_id),
            tenant_id=str(tenant_id),
            connector=connector_id,
            run_status=RUN_COMPLETED,
            records_written=records_written,
        )
        vrep: dict[str, Any] | None = None
        if settings.cortex_ingestion_verify_after_sync:
            from vector.domains.cortex.ingestion import verification as ingestion_verification

            vrep = ingestion_verification.verify_ingestion_run(session, run_id)
            if not vrep["passed"]:
                log_ingestion_event(
                    _logger,
                    logging.WARNING,
                    "cortex sync verification reported issues",
                    task_name="execute_connector_sync",
                    phase=PHASE_STEP5,
                    outcome="verification_failed",
                    run_id=str(run_id),
                    tenant_id=str(tenant_id),
                    connector=connector_id,
                )
        out: dict[str, Any] = {
            "status": "completed",
            "run_id": str(run_id),
            "connector": connector_id,
            "records_written": records_written,
            "sync_mode": ctx.sync_mode,
            "checkpoint_scope": ctx.checkpoint_scope_key(),
        }
        if ctx.replay_job_id is not None:
            out["replay_job_id"] = str(ctx.replay_job_id)
            out["replay_version"] = ctx.replay_version
        if vrep is not None:
            out["verification"] = vrep
        return out
    except Exception as e:
        _logger.exception("cortex sync failed")
        run.status = RUN_FAILED
        run.finished_at = _utc_now()
        run.error_summary = str(e)[:8000]
        log_ingestion_event(
            _logger,
            logging.ERROR,
            "cortex sync failed",
            task_name="execute_connector_sync",
            phase=phase,
            outcome="failed",
            run_id=str(run_id),
            tenant_id=str(tenant_id),
            connector=connector_id,
            run_status=RUN_FAILED,
            error=str(e),
        )
        return {
            "status": "failed",
            "run_id": str(run_id),
            "connector": connector_id,
            "error": str(e),
        }
