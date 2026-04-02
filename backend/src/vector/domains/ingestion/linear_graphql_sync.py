"""Linear GraphQL polling ingestion (Step 1) — resource-level envelopes only.

Queries mirror common `https://api.linear.app/graphql` patterns: root connections
(`teams`, `users`, `issues`, …) with Relay-style ``first`` / ``after`` pagination.
Each returned node becomes one raw ingestion row for its resource type.

**Incremental polling:** Issues and comments use ``orderBy: updatedAt`` plus a per-connection
watermark in ``connector_sync_state`` (same pattern as GitHub). Re-running sync skips rows at or
below the watermark so Step 1 does not grow with duplicates on every poll. Other Linear types
are still fully paginated each run (small cardinality).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.ingestion.http_fetch import FetchExecutor, FetchFatalError, FetchTransientError
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.repositories import ingestion as ing_repo
from vector.infrastructure.db.repositories import linear_connection as linear_repo
from vector.settings import Settings

_logger = logging.getLogger(__name__)

CONNECTOR = ing_repo.CONNECTOR_LINEAR
SOURCE_POLL = ing_repo.SOURCE_TRIGGER_POLL

API_GRAPHQL = "POST graphql"
PAGE_SIZE = 50

RT_VIEWER = "linear.viewer"
RT_TEAM = "linear.team"
RT_USER = "linear.user"
RT_WORKFLOW_STATE = "linear.workflow_state"
RT_PROJECT = "linear.project"
RT_ISSUE = "linear.issue"
RT_COMMENT = "linear.comment"
RT_ISSUE_RELATION = "linear.issue_relation"
RT_ISSUE_LABEL = "linear.issue_label"
RT_CYCLE = "linear.cycle"
RT_INITIATIVE = "linear.initiative"

QUERY_VIEWER = """
query LinearIngestViewer {
  viewer {
    id
    name
    email
    organization {
      id
      name
    }
  }
}
"""

QUERY_TEAMS = """
query LinearIngestTeams($first: Int!, $after: String) {
  teams(first: $first, after: $after) {
    nodes {
      id
      key
      name
      description
      private
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_USERS = """
query LinearIngestUsers($first: Int!, $after: String) {
  users(first: $first, after: $after) {
    nodes {
      id
      name
      displayName
      email
      avatarUrl
      active
      guest
      admin
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_WORKFLOW_STATES = """
query LinearIngestWorkflowStates($first: Int!, $after: String) {
  workflowStates(first: $first, after: $after) {
    nodes {
      id
      name
      type
      position
      color
      team {
        id
        key
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_PROJECTS = """
query LinearIngestProjects($first: Int!, $after: String) {
  projects(first: $first, after: $after) {
    nodes {
      id
      name
      slug
      description
      summary
      state
      startDate
      targetDate
      lead {
        id
        name
        email
      }
      team {
        id
        key
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_ISSUES = """
query LinearIngestIssues($first: Int!, $after: String, $includeArchived: Boolean) {
  issues(
    first: $first
    after: $after
    includeArchived: $includeArchived
    orderBy: updatedAt
  ) {
    nodes {
      id
      identifier
      title
      description
      priority
      estimate
      createdAt
      updatedAt
      archivedAt
      state {
        id
        name
        type
      }
      team {
        id
        key
        name
      }
      assignee {
        id
        name
        email
        displayName
      }
      creator {
        id
        name
        email
      }
      project {
        id
        name
      }
      parent {
        id
        identifier
        title
        lead {
          id
          name
        }
      }
      labels {
        nodes {
          id
          name
          color
        }
      }
      cycle {
        id
        name
        number
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_COMMENTS = """
query LinearIngestComments($first: Int!, $after: String) {
  comments(first: $first, after: $after, orderBy: updatedAt) {
    nodes {
      id
      body
      createdAt
      updatedAt
      user {
        id
        name
        displayName
        email
      }
      issue {
        id
        identifier
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_ISSUE_RELATIONS = """
query LinearIngestIssueRelations($first: Int!, $after: String) {
  issueRelations(first: $first, after: $after) {
    nodes {
      id
      type
      issue {
        id
        identifier
      }
      relatedIssue {
        id
        identifier
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_ISSUE_LABELS = """
query LinearIngestIssueLabels($first: Int!, $after: String) {
  issueLabels(first: $first, after: $after) {
    nodes {
      id
      name
      color
      team {
        id
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_CYCLES = """
query LinearIngestCycles($first: Int!, $after: String) {
  cycles(first: $first, after: $after) {
    nodes {
      id
      number
      name
      startsAt
      endsAt
      completedAt
      progress
      team {
        id
        key
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

QUERY_INITIATIVES = """
query LinearIngestInitiatives($first: Int!, $after: String) {
  initiatives(first: $first, after: $after) {
    nodes {
      id
      name
      description
      targetDate
      status {
        name
      }
      owner {
        id
        name
        email
      }
      lead {
        id
        name
        email
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


def _post_graphql(
    executor: FetchExecutor,
    settings: Settings,
    token: str,
    query: str,
    variables: dict[str, Any],
    *,
    operation_name: str | None = None,
) -> tuple[int, dict[str, Any]]:
    url = settings.linear_graphql_url()
    payload: dict[str, Any] = {"query": query, "variables": variables}
    if operation_name:
        payload["operationName"] = operation_name
    resp = executor.request(
        "POST",
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json_body=payload,
    )
    if resp.status_code in (401, 403):
        raise FetchFatalError(f"linear graphql auth error http {resp.status_code}")
    try:
        body = resp.json()
    except ValueError:
        raise FetchFatalError(
            f"linear graphql response not json (http {resp.status_code})",
        ) from None
    if not isinstance(body, dict):
        raise FetchFatalError("linear graphql: expected object body")
    return resp.status_code, body


def _raise_if_graphql_errors(body: dict[str, Any]) -> None:
    errs = body.get("errors")
    if errs:
        raise FetchFatalError(f"linear graphql errors: {errs!r}")


def _linear_sync_scope_key(resource_type: str) -> str:
    """One watermark per Linear resource type (matches GitHub per-scope sync state)."""
    return resource_type


def _node_activity_timestamp(node: dict[str, Any]) -> str | None:
    """Prefer updatedAt for incremental polling; fall back to createdAt."""
    for key in ("updatedAt", "createdAt"):
        v = node.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def _nodes_at_path(
    data: dict[str, Any] | None,
    path: tuple[str, ...],
) -> tuple[list[Any], dict[str, Any]]:
    if not isinstance(data, dict):
        return [], {}
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return [], {}
        cur = cur.get(key)
    if not isinstance(cur, dict):
        return [], {}
    raw_nodes = cur.get("nodes")
    nodes = raw_nodes if isinstance(raw_nodes, list) else []
    pi = cur.get("pageInfo")
    page_info = pi if isinstance(pi, dict) else {}
    return nodes, page_info


def _ingest_paginated(
    *,
    executor: FetchExecutor,
    settings: Settings,
    token: str,
    batch: list[dict[str, Any]],
    flush: Callable[[list[dict[str, Any]]], None],
    query: str,
    operation: str,
    path: tuple[str, ...],
    resource_type: str,
    variables_extra: dict[str, Any] | None = None,
    session: Session | None = None,
    tenant_id: uuid.UUID | None = None,
    connection_id: uuid.UUID | None = None,
    use_updated_at_watermark: bool = False,
) -> None:
    """Paginate a root Linear connection into raw rows.

    When ``use_updated_at_watermark`` is True (issues/comments), results must be ordered by
    ``updatedAt`` (see queries). We skip rows already at or before the stored watermark so
    resyncs do not append duplicate Step 1 rows — same idea as GitHub's per-scope watermarks.
    """
    watermark_s: str | None = None
    if use_updated_at_watermark:
        if session is None or tenant_id is None or connection_id is None:
            msg = "Linear watermark ingestion requires session, tenant_id, connection_id"
            raise FetchFatalError(msg)
        st = ing_repo.get_sync_state(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTOR,
            scope_key=_linear_sync_scope_key(resource_type),
        ) or {}
        w = st.get("watermark")
        watermark_s = w if isinstance(w, str) and w else None

    latest_observed: str | None = None
    after: str | None = None
    while True:
        variables: dict[str, Any] = {"first": PAGE_SIZE, "after": after}
        if variables_extra:
            variables.update(variables_extra)
        http_status, body = _post_graphql(
            executor,
            settings,
            token,
            query,
            variables,
            operation_name=operation,
        )
        _raise_if_graphql_errors(body)
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        nodes, page_info = _nodes_at_path(data, path)
        qp = {"operation": operation, **variables}
        dict_nodes = [n for n in nodes if isinstance(n, dict)]

        for n in dict_nodes:
            ts = _node_activity_timestamp(n)
            if ts and (latest_observed is None or ts > latest_observed):
                latest_observed = ts

        page_all_stale = False
        if use_updated_at_watermark and watermark_s is not None and dict_nodes:
            page_all_stale = True
            for n in dict_nodes:
                ts_n = _node_activity_timestamp(n)
                if ts_n is None or ts_n > watermark_s:
                    page_all_stale = False
                    break

        for node in dict_nodes:
            iid = node.get("id")
            if not isinstance(iid, str) or not iid:
                continue
            ts = _node_activity_timestamp(node)
            stale = (
                use_updated_at_watermark
                and watermark_s is not None
                and ts is not None
                and ts <= watermark_s
            )
            if stale:
                continue
            batch.append(
                {
                    "resource_type": resource_type,
                    "external_id": iid,
                    "api_endpoint": API_GRAPHQL,
                    "query_params": qp,
                    "payload_body": node,
                    "http_status": http_status,
                },
            )
            if len(batch) >= 100:
                flush(batch)
        flush(batch)
        if page_all_stale:
            break
        if not page_info.get("hasNextPage"):
            break
        end_c = page_info.get("endCursor")
        if not isinstance(end_c, str) or not end_c:
            break
        after = end_c

    if (
        use_updated_at_watermark
        and session is not None
        and tenant_id is not None
        and connection_id is not None
    ):
        new_wm = latest_observed or watermark_s
        if new_wm:
            ing_repo.upsert_sync_state(
                session,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTOR,
                scope_key=_linear_sync_scope_key(resource_type),
                state={"watermark": new_wm},
            )
            session.commit()


def run_linear_graphql_ingestion_for_tenant(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> IngestionRun:
    """POST GraphQL to Linear; one raw row per resource node (and one for viewer)."""
    link = linear_repo.get_linear_connection_for_tenant(session, tenant_id)
    if link is None:
        raise FetchFatalError("Linear is not connected for this tenant")

    token = link.detail.access_token
    if not token or not str(token).strip():
        raise FetchFatalError("Linear access token is missing")

    run = ing_repo.create_ingestion_run(
        session,
        tenant_id=tenant_id,
        connection_id=link.connection.id,
        connector=CONNECTOR,
        source_trigger=SOURCE_POLL,
    )
    session.commit()

    stats: dict[str, int] = {"records_written": 0}
    executor = FetchExecutor()

    def flush(b: list[dict[str, Any]]) -> None:
        if not b:
            return
        n = ing_repo.insert_raw_records_ignore_conflict(
            session,
            run=run,
            connector=CONNECTOR,
            source_trigger=SOURCE_POLL,
            batch=b,
        )
        stats["records_written"] = stats.get("records_written", 0) + n
        session.commit()
        b.clear()

    batch: list[dict[str, Any]] = []

    try:
        http_status, viewer_body = _post_graphql(
            executor,
            settings,
            token,
            QUERY_VIEWER,
            {},
            operation_name="LinearIngestViewer",
        )
        _raise_if_graphql_errors(viewer_body)
        data = viewer_body.get("data")
        viewer = data.get("viewer") if isinstance(data, dict) else None
        ext = "viewer"
        if isinstance(viewer, dict):
            vid = viewer.get("id")
            if isinstance(vid, str) and vid:
                ext = vid
        batch.append(
            {
                "resource_type": RT_VIEWER,
                "external_id": ext,
                "api_endpoint": API_GRAPHQL,
                "query_params": {"operation": "LinearIngestViewer"},
                "payload_body": viewer_body,
                "http_status": http_status,
            },
        )
        flush(batch)

        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_TEAMS,
            operation="LinearIngestTeams",
            path=("teams",),
            resource_type=RT_TEAM,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_USERS,
            operation="LinearIngestUsers",
            path=("users",),
            resource_type=RT_USER,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_WORKFLOW_STATES,
            operation="LinearIngestWorkflowStates",
            path=("workflowStates",),
            resource_type=RT_WORKFLOW_STATE,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_PROJECTS,
            operation="LinearIngestProjects",
            path=("projects",),
            resource_type=RT_PROJECT,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_INITIATIVES,
            operation="LinearIngestInitiatives",
            path=("initiatives",),
            resource_type=RT_INITIATIVE,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_CYCLES,
            operation="LinearIngestCycles",
            path=("cycles",),
            resource_type=RT_CYCLE,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_ISSUE_LABELS,
            operation="LinearIngestIssueLabels",
            path=("issueLabels",),
            resource_type=RT_ISSUE_LABEL,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_ISSUES,
            operation="LinearIngestIssues",
            path=("issues",),
            resource_type=RT_ISSUE,
            variables_extra={"includeArchived": True},
            session=session,
            tenant_id=run.tenant_id,
            connection_id=run.connection_id,
            use_updated_at_watermark=True,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_COMMENTS,
            operation="LinearIngestComments",
            path=("comments",),
            resource_type=RT_COMMENT,
            session=session,
            tenant_id=run.tenant_id,
            connection_id=run.connection_id,
            use_updated_at_watermark=True,
        )
        _ingest_paginated(
            executor=executor,
            settings=settings,
            token=token,
            batch=batch,
            flush=flush,
            query=QUERY_ISSUE_RELATIONS,
            operation="LinearIngestIssueRelations",
            path=("issueRelations",),
            resource_type=RT_ISSUE_RELATION,
        )

        ing_repo.finish_ingestion_run(
            session,
            run,
            status=ing_repo.RUN_STATUS_SUCCEEDED,
            error_summary=None,
            stats=stats,
        )
        session.commit()
    except FetchFatalError as exc:
        _logger.warning("linear ingestion fatal: %s", exc)
        ing_repo.finish_ingestion_run(
            session,
            run,
            status=ing_repo.RUN_STATUS_FAILED,
            error_summary=str(exc),
            stats=stats,
        )
        session.commit()
    except (FetchTransientError, OSError) as exc:
        _logger.warning("linear ingestion transient: %s", exc)
        ing_repo.finish_ingestion_run(
            session,
            run,
            status=ing_repo.RUN_STATUS_FAILED,
            error_summary=str(exc),
            stats=stats,
        )
        session.commit()
    finally:
        executor.close()

    return run
