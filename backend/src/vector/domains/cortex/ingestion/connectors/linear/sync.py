"""Phase 01 — linear connector sync."""

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


def linear_graphql_connection_page(
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


def linear_graphql_ping(
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


def run_linear_connector_sync(
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
    existing_ckpt = read_checkpoint_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_LINEAR,
        scope_key=scope_ck,
    )
    link = lin_repo.get_linear_connection_for_tenant(session, tenant_id)
    if link is None:
        ins = int(
            append_raw(
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
                idempotency_key=idem_key(ctx, run_id, "linear:no-detail"),
            )
        )
        upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTION_PROVIDER_LINEAR,
            scope_key=scope_ck,
            patch={
                "last_incremental_at": utc_now().isoformat(),
                "streams": {
                    "linear": {
                        "issues": {
                            "cursor_owner": "linear.issue",
                            "last_status": "missing_connection_detail",
                        }
                    }
                },
            },
            sync_mode=ctx.checkpoint_sync_mode,
        )
        return ins
    token = link.detail.access_token
    n_ins = 0
    streams_existing = checkpoint_streams_for_mode(existing_ckpt, ctx.sync_mode)
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
        st_issues, payload_issues, issue_nodes, page_info = linear_graphql_connection_page(
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
                ctx.checkpoint_sync_mode == "incremental"
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
            if append_raw(
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
                idempotency_key=idem_key(ctx, run_id, f"linear:issue:{ext}"),
            ):
                n_ins += 1
                issue_rows += 1

            for idx, attachment in enumerate(_node_seq(node.get("attachments"))):
                aid = attachment.get("id")
                a_ext = f"{ext}:attachment:{aid if isinstance(aid, str) else idx}"[:512]
                if append_raw(
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
                    idempotency_key=idem_key(ctx, run_id, f"linear:attachment:{a_ext}"),
                ):
                    n_ins += 1
                    attachment_rows += 1

            activity_items = _node_seq(node.get("history")) or _node_seq(node.get("activityHistory"))
            for idx, event in enumerate(activity_items):
                aid = event.get("id")
                a_ext = f"{ext}:activity:{aid if isinstance(aid, str) else idx}"[:512]
                if append_raw(
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
                    idempotency_key=idem_key(ctx, run_id, f"linear:activity:{a_ext}"),
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
        st_comments, _payload_comments, comment_nodes, page_info_c = linear_graphql_connection_page(
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
            if append_raw(
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
                idempotency_key=idem_key(ctx, run_id, f"linear:comments:{ext}"),
            ):
                n_ins += 1
                comment_rows += 1
            parent = node.get("parent") if isinstance(node.get("parent"), dict) else None
            pid = parent.get("id") if isinstance(parent, dict) else None
            if (not isinstance(pid, str) or not pid.strip()) and isinstance(nid, str) and nid.strip():
                t_ext = f"{nid.strip()}:thread"[:512]
                if append_raw(
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
                    idempotency_key=idem_key(ctx, run_id, f"linear:comment_thread:{t_ext}"),
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
            "backfill_complete": bool(ctx.backfill_lane and comments_backfill_complete),
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
            status_stream, _payload_stream, nodes, page_info = linear_graphql_connection_page(
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
                if append_raw(
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
                    idempotency_key=idem_key(ctx, run_id, f"linear:{stream_key}:{ext}"),
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
            "backfill_complete": bool(ctx.backfill_lane and complete),
        }

    status, payload = linear_graphql_ping(settings, token)
    ins = int(
        append_raw(
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
            idempotency_key=idem_key(ctx, run_id, "linear:viewer"),
        )
    )
    n_ins += ins
    upsert_checkpoint(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTION_PROVIDER_LINEAR,
        scope_key=scope_ck,
        patch={
            "last_incremental_at": utc_now().isoformat(),
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
                        "backfill_complete": bool(ctx.backfill_lane and issues_backfill_complete),
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
        sync_mode=ctx.checkpoint_sync_mode,
    )
    return n_ins
