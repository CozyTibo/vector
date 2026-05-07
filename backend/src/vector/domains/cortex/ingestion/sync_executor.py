"""Phase 01 Step 1 — connector sync execution (run + raw persistence + checkpoint)."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.github.errors import GitHubApiError
from vector.domains.cortex.connectors.github.http_client import list_installation_repositories_first_page
from vector.domains.cortex.connectors.provider_keys import (
    CONNECTION_PROVIDER_CALLS,
    CONNECTION_PROVIDER_GITHUB,
    CONNECTION_PROVIDER_LINEAR,
    CONNECTION_PROVIDER_NOTION,
    CONNECTION_PROVIDER_SLACK,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.repositories import calls_connection as calls_repo
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import linear_connection as lin_repo
from vector.infrastructure.db.repositories import notion_connection as notion_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.observability.ingestion_tasks import PHASE_STEP1, log_ingestion_event
from vector.settings import Settings

_logger = logging.getLogger("app")

RUN_RUNNING = "RUNNING"
RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"
SCOPE_DEFAULT = "default"


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _hash_payload(body: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def _resolve_connection(session: Session, tenant_id: uuid.UUID, connector_id: str) -> TenantConnection | None:
    stmt = select(TenantConnection).where(
        TenantConnection.tenant_id == tenant_id,
        TenantConnection.provider == connector_id,
        TenantConnection.status == "active",
    )
    return session.scalar(stmt)


def _upsert_checkpoint(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    patch: dict[str, Any],
) -> None:
    stmt = select(ConnectorSyncState).where(
        ConnectorSyncState.tenant_id == tenant_id,
        ConnectorSyncState.connection_id == connection_id,
        ConnectorSyncState.connector == connector,
        ConnectorSyncState.scope_key == SCOPE_DEFAULT,
    )
    row = session.scalar(stmt)
    if row is None:
        session.add(
            ConnectorSyncState(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=connector,
                scope_key=SCOPE_DEFAULT,
                state=patch,
            )
        )
    else:
        merged = dict(row.state)
        merged.update(patch)
        row.state = merged


def _append_raw(
    session: Session,
    *,
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
) -> None:
    body = dict(payload_body)
    ph = _hash_payload(body)
    session.add(
        RawIngestionRecord(
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
            run_id=run_id,
            source_trigger=source_trigger,
            idempotency_key=idempotency_key[:128],
        )
    )


def _github_sync(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    link = gh_repo.get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        _append_raw(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type="github.sync",
            external_id="missing-github-detail",
            api_endpoint="internal://github/no-detail",
            query_params={},
            payload_body={"reason": "github_connection_detail_missing"},
            http_status=503,
            idempotency_key=f"github:{run_id}:no-detail",
        )
        return 1
    try:
        repos, total = list_installation_repositories_first_page(
            settings,
            link.installation_id,
            per_page=50,
        )
    except GitHubApiError as e:
        _append_raw(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type="github.installation_repositories",
            external_id="fetch_error",
            api_endpoint=f"{settings.github_rest_api_base_url().rstrip('/')}/installation/repositories",
            query_params={"error": True},
            payload_body={"error": str(e)},
            http_status=502,
            idempotency_key=f"github:{run_id}:fetch_error",
        )
        return 1

    n = 0
    for repo in repos:
        rid = repo.get("id")
        rid_s = str(rid) if rid is not None else ""
        fn = repo.get("full_name") or rid_s
        body = {
            "schema_version": 1,
            "connector_type": CONNECTION_PROVIDER_GITHUB,
            "connector_instance_id": str(connection_id),
            "source_object_type": "github.repository",
            "source_object_id": rid_s,
            "payload_hash_basis": "github_rest_repo_record_v1",
            "repository": repo,
        }
        _append_raw(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_GITHUB,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type="github.repository",
            external_id=rid_s or fn[:512],
            api_endpoint=f"{settings.github_rest_api_base_url().rstrip('/')}/installation/repositories",
            query_params={"page_slice": "first"},
            payload_body=body,
            http_status=200,
            idempotency_key=f"github:repo:{rid_s}:{run_id}",
        )
        n += 1

    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_GITHUB,
        patch={
            "last_incremental_at": _utc_now().isoformat(),
            "repos_fetched": n,
            "total_count_hint": total,
        },
    )
    return n


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
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    link = lin_repo.get_linear_connection_for_tenant(session, tenant_id)
    if link is None:
        _append_raw(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_LINEAR,
            run_id=run_id,
            source_trigger=source_trigger,
            resource_type="linear.sync",
            external_id="missing-linear-detail",
            api_endpoint="internal://linear/no-detail",
            query_params={},
            payload_body={"reason": "linear_connection_detail_missing"},
            http_status=503,
            idempotency_key=f"linear:{run_id}:no-detail",
        )
        return 1
    status, payload = _linear_graphql_ping(settings, link.detail.access_token)
    _append_raw(
        session,
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
            "schema_version": 1,
            "connector_type": CONNECTION_PROVIDER_LINEAR,
            "connector_instance_id": str(connection_id),
            "graphql_status": status,
            "response": payload,
        },
        http_status=status if status >= 100 else 500,
        idempotency_key=f"linear:viewer:{run_id}",
    )
    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_LINEAR,
        patch={"last_incremental_at": _utc_now().isoformat(), "last_http_status": status},
    )
    return 1


def _generic_scope_ping(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    run_id: uuid.UUID,
    source_trigger: str,
    label: str,
) -> int:
    body = {
        "schema_version": 1,
        "connector_type": connector,
        "connector_instance_id": str(connection_id),
        "scope_ping": True,
        "label": label,
    }
    _append_raw(
        session,
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
        idempotency_key=f"{connector}:ping:{run_id}",
    )
    _upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        patch={"last_incremental_at": _utc_now().isoformat(), "ping": True},
    )
    return 1


def _slack_sync(
    session: Session,
    _settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return _generic_scope_ping(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_SLACK,
            run_id=run_id,
            source_trigger=source_trigger,
            label="no_slack_detail",
        )
    team = link.detail.team_id or str(link.connection.id)
    return _generic_scope_ping(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_SLACK,
        run_id=run_id,
        source_trigger=source_trigger,
        label=f"team:{team}",
    )


def _notion_sync(
    session: Session,
    _settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        return _generic_scope_ping(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_NOTION,
            run_id=run_id,
            source_trigger=source_trigger,
            label="no_notion_detail",
        )
    ws = link.detail.workspace_id or str(link.connection.id)
    return _generic_scope_ping(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_NOTION,
        run_id=run_id,
        source_trigger=source_trigger,
        label=f"workspace:{ws}",
    )


def _calls_sync(
    session: Session,
    _settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    source_trigger: str,
) -> int:
    link = calls_repo.get_calls_connection_for_tenant(session, tenant_id)
    if link is None:
        return _generic_scope_ping(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_CALLS,
            run_id=run_id,
            source_trigger=source_trigger,
            label="no_calls_detail",
        )
    return _generic_scope_ping(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_CALLS,
        run_id=run_id,
        source_trigger=source_trigger,
        label="calls_connected",
    )


def execute_connector_sync(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connector_id: str,
    source_trigger: str,
) -> dict[str, Any]:
    """Create an ingestion run, fetch normalized snapshots, persist raw rows, update checkpoint."""
    conn = _resolve_connection(session, tenant_id, connector_id)
    if conn is None:
        log_ingestion_event(
            _logger,
            logging.INFO,
            "cortex sync skipped — no active tenant_connection",
            task_name="execute_connector_sync",
            phase=PHASE_STEP1,
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
        phase=PHASE_STEP1,
        outcome="started",
        run_id=str(run_id),
        tenant_id=str(tenant_id),
        connector=connector_id,
        run_status=RUN_RUNNING,
    )

    records_written = 0
    try:
        if connector_id == CONNECTION_PROVIDER_GITHUB:
            records_written = _github_sync(
                session,
                settings,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_LINEAR:
            records_written = _linear_sync(
                session,
                settings,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_SLACK:
            records_written = _slack_sync(
                session,
                settings,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_NOTION:
            records_written = _notion_sync(
                session,
                settings,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_CALLS:
            records_written = _calls_sync(
                session,
                settings,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        else:
            raise ValueError(f"unsupported connector for sync: {connector_id!r}")

        finished = _utc_now()
        run.status = RUN_COMPLETED
        run.finished_at = finished
        run.stats = {"records_written": records_written}
        log_ingestion_event(
            _logger,
            logging.INFO,
            "cortex sync completed",
            task_name="execute_connector_sync",
            phase=PHASE_STEP1,
            outcome="completed",
            run_id=str(run_id),
            tenant_id=str(tenant_id),
            connector=connector_id,
            run_status=RUN_COMPLETED,
            records_written=records_written,
        )
        return {
            "status": "completed",
            "run_id": str(run_id),
            "connector": connector_id,
            "records_written": records_written,
        }
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
            phase=PHASE_STEP1,
            outcome="failed",
            run_id=str(run_id),
            tenant_id=str(tenant_id),
            connector=connector_id,
            run_status=RUN_FAILED,
            error=str(e),
        )
        return {"status": "failed", "run_id": str(run_id), "connector": connector_id, "error": str(e)}
