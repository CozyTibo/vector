"""Phase 01 — notion connector sync."""

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

from vector.domains.cortex.ingestion.stream_checkpoint import ensure_stream_introduced_at
from vector.domains.cortex.ingestion.sync_shared import (
    append_raw,
    checkpoint_streams_for_mode,
    generic_scope_ping,
    hash_payload,
    idem_key,
    read_checkpoint_state,
    tag_replay_payload,
    upsert_checkpoint,
    utc_now,
)

def run_notion_connector_sync(
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
    existing_ckpt = read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_NOTION,
        scope_key=scope_ck,
    )
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        return generic_scope_ping(
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

    streams_existing = checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
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
        return append_raw(
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
            idempotency_key=idem_key(ctx, run_id, f"notion:{resource_type}:{external_id}"),
        )

    users_state = _state_map(notion_existing, "users")
    user_cursor_raw = users_state.get("next_cursor")
    user_cursor = user_cursor_raw if isinstance(user_cursor_raw, str) and user_cursor_raw.strip() else None
    user_rows = 0
    user_pages = 0
    users_complete = False
    for _ in range(8):
        params: dict[str, Any] = {"page_size": min(settings.cortex_notion_search_page_size, 100)}
        if user_cursor:
            params["start_cursor"] = user_cursor
        try:
            resp = httpx.get(
                f"{notion_base}/users",
                headers=_notion_headers(token),
                params=params,
                timeout=60.0,
            )
            if resp.is_error:
                raise _NotionSyncApiError(f"notion users http {resp.status_code}")
            users_payload = resp.json()
        except (_NotionSyncApiError, httpx.HTTPError, ValueError):
            break
        if not isinstance(users_payload, dict):
            break
        user_pages += 1
        results = users_payload.get("results")
        if isinstance(results, list):
            for u in results:
                if not isinstance(u, dict):
                    continue
                uid = u.get("id")
                if not isinstance(uid, str) or not uid:
                    continue
                if _append_notion_row(
                    resource_type="notion.user",
                    external_id=uid,
                    api_endpoint=f"{notion_base}/users",
                    query_params={"start_cursor": user_cursor},
                    source_object_type="notion.user",
                    payload_key="user",
                    payload_value=u,
                ):
                    n_ins += 1
                    user_rows += 1
        has_more = bool(users_payload.get("has_more"))
        next_c = users_payload.get("next_cursor")
        user_cursor = next_c if isinstance(next_c, str) and next_c.strip() else None
        if not has_more or not user_cursor:
            users_complete = True
            break
        if time.monotonic() - start_t >= settings.cortex_notion_time_budget_seconds:
            break
    users_patch = ensure_stream_introduced_at(
        {
            "cursor_owner": "notion.user",
            "next_cursor": user_cursor,
            "pages_fetched_last_run": user_pages,
            "rows_seen_last_run": user_rows,
            "backfill_complete": bool(ctx.backfill_lane and users_complete),
            "last_ok_at": utc_now().isoformat(),
        },
    )

    databases_discovered: set[str] = set()
    pages_discovered: set[str] = set()
    database_patch_map: dict[str, Any] = {}
    block_parent_patch_map: dict[str, Any] = {}

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
                    ctx.checkpoint_sync_mode == "incremental"
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
                        ctx.checkpoint_sync_mode == "incremental"
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
    if append_raw(
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
        idempotency_key=idem_key(ctx, run_id, f"notion:scope_ping:{ws}"),
    ):
        n_ins += 1

    upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_NOTION,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": utc_now().isoformat(),
            "notion_search_results_written": search_rows,
            "notion_pages_written": page_rows,
            "notion_databases_written": database_rows,
            "notion_database_rows_written": database_row_rows,
            "notion_blocks_written": block_rows,
            "streams": {
                "notion": {
                    "users": users_patch,
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
        sync_mode=ctx.checkpoint_sync_mode,
    )
    return n_ins


