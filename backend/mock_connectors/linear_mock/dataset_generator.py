"""Linear GraphQL response builders (local mock).

Dispatches on ``operationName`` (preferred) so ingestion can mirror production
``https://api.linear.app/graphql`` operation names and field shapes.
"""

from __future__ import annotations

from typing import Any


def viewer_org(linear: dict[str, Any]) -> dict[str, Any]:
    v = linear["viewer"]
    org = linear["organization"]
    return {
        "data": {
            "viewer": {
                "id": v["id"],
                "name": v["name"],
                "email": v.get("email"),
                "organization": {"id": org["id"], "name": org["name"]},
            },
        },
    }


def viewer_ping(linear: dict[str, Any], _variables: dict[str, Any] | None) -> dict[str, Any]:
    """Matches ``query ViewerPing { viewer { id name } }`` (sync_executor health probe)."""
    v = linear["viewer"]
    return {"data": {"viewer": {"id": v["id"], "name": v["name"]}}}


def _public(obj: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in obj.items() if not k.startswith("_") and k != "issueId"}


def _page(
    items: list[dict[str, Any]],
    variables: dict[str, Any] | None,
    *,
    cap: int = 100,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    first = 50
    after: str | None = None
    if isinstance(variables, dict):
        f = variables.get("first")
        if isinstance(f, int) and f > 0:
            first = min(f, cap)
        a = variables.get("after")
        if isinstance(a, str):
            after = a or None
    start = 0
    if after:
        for i, it in enumerate(items):
            if it.get("id") == after:
                start = i + 1
                break
    page = items[start : start + first]
    has_next = start + first < len(items)
    end_cursor = page[-1]["id"] if page and has_next else None
    return page, {"hasNextPage": has_next, "endCursor": end_cursor}


def _connection(
    items: list[dict[str, Any]],
    variables: dict[str, Any] | None,
    *,
    strip: bool = True,
    cap: int = 100,
) -> dict[str, Any]:
    page, pi = _page(items, variables, cap=cap)
    nodes = [_public(x) if strip else x for x in page]
    return {"nodes": nodes, "pageInfo": pi}


def op_teams(linear: dict[str, Any], variables: dict[str, Any] | None) -> dict[str, Any]:
    return {"data": {"teams": _connection(linear["teams"], variables)}}


def op_users(linear: dict[str, Any], variables: dict[str, Any] | None) -> dict[str, Any]:
    return {"data": {"users": _connection(linear["users"], variables)}}


def op_workflow_states(
    linear: dict[str, Any], variables: dict[str, Any] | None
) -> dict[str, Any]:
    return {"data": {"workflowStates": _connection(linear["workflowStates"], variables)}}


def op_projects(linear: dict[str, Any], variables: dict[str, Any] | None) -> dict[str, Any]:
    return {"data": {"projects": _connection(linear["projects"], variables)}}


def _by_updated_desc(item: dict[str, Any]) -> str:
    """Match Linear ``orderBy: updatedAt`` (newest first) for watermark / pagination tests."""
    return str(item.get("updatedAt") or item.get("createdAt") or "")


def op_issues(linear: dict[str, Any], variables: dict[str, Any] | None) -> dict[str, Any]:
    """Root ``issues`` connection (same pagination style as api.linear.app)."""
    items = sorted(linear["issues"], key=_by_updated_desc, reverse=True)
    return {"data": {"issues": _connection(items, variables)}}


def op_comments(linear: dict[str, Any], variables: dict[str, Any] | None) -> dict[str, Any]:
    items = sorted(linear["comments"], key=_by_updated_desc, reverse=True)
    return {"data": {"comments": _connection(items, variables)}}


def op_issue_relations(
    linear: dict[str, Any], variables: dict[str, Any] | None
) -> dict[str, Any]:
    return {"data": {"issueRelations": _connection(linear["issueRelations"], variables)}}


def op_issue_labels(
    linear: dict[str, Any], variables: dict[str, Any] | None
) -> dict[str, Any]:
    return {"data": {"issueLabels": _connection(linear["labels"], variables)}}


def op_cycles(linear: dict[str, Any], variables: dict[str, Any] | None) -> dict[str, Any]:
    return {"data": {"cycles": _connection(linear["cycles"], variables)}}


def op_initiatives(linear: dict[str, Any], variables: dict[str, Any] | None) -> dict[str, Any]:
    return {"data": {"initiatives": _connection(linear["initiatives"], variables)}}


def op_project_updates(linear: dict[str, Any], variables: dict[str, Any] | None) -> dict[str, Any]:
    items = list(linear.get("projectUpdates") or [])
    items = sorted(items, key=_by_updated_desc, reverse=True)
    return {"data": {"projectUpdates": _connection(items, variables)}}


# Legacy: viewer-scoped issues (older ingestion); still supported without operationName.
def viewer_issues_connection(
    linear: dict[str, Any], variables: dict[str, Any] | None
) -> dict[str, Any]:
    page, pi = _page(linear["issues"], variables)
    nodes = [_public(i) for i in page]
    return {
        "data": {
            "viewer": {
                "issues": {
                    "nodes": nodes,
                    "pageInfo": pi,
                },
            },
        },
    }


def issues_connection(linear: dict[str, Any], *, first: int, after: str | None) -> dict[str, Any]:
    variables = {"first": first, "after": after}
    return op_issues(linear, variables)


_OPERATION_HANDLERS: dict[str, Any] = {
    "ViewerPing": viewer_ping,
    "LinearIngestViewer": lambda lin, v: viewer_org(lin),
    "LinearIngestTeams": op_teams,
    "LinearIngestUsers": op_users,
    "LinearIngestWorkflowStates": op_workflow_states,
    "LinearIngestProjects": op_projects,
    "LinearIngestIssues": op_issues,
    "LinearIngestComments": op_comments,
    "LinearIngestIssueRelations": op_issue_relations,
    "LinearIngestIssueLabels": op_issue_labels,
    "LinearIngestCycles": op_cycles,
    "LinearIngestInitiatives": op_initiatives,
    "LinearIngestProjectUpdates": op_project_updates,
}


def handle_graphql(linear: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /linear/graphql JSON body (``query``, ``variables``, ``operationName``)."""
    op = body.get("operationName")
    variables = body.get("variables") if isinstance(body.get("variables"), dict) else {}
    if isinstance(op, str) and op in _OPERATION_HANDLERS:
        return _OPERATION_HANDLERS[op](linear, variables)

    q = (body.get("query") or "").replace("\n", " ").strip()
    # Ping sends query-only body (no operationName): query ViewerPing { viewer { id name } }
    if "ViewerPing" in q:
        return viewer_ping(linear, variables)
    if "viewer" in q and "issues" in q.lower():
        return viewer_issues_connection(linear, variables)
    if "viewer" in q and "organization" in q:
        return viewer_org(linear)
    if "issues" in q.lower():
        return issues_connection(linear, first=50, after=None)
    return {"data": {"viewer": linear["viewer"]}}
