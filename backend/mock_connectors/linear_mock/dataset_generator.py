"""Linear GraphQL response builders (local mock)."""

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


def issues_connection(linear: dict[str, Any], *, first: int, after: str | None) -> dict[str, Any]:
    """Cursor-paginated `issues` (simplified)."""
    items = linear["issues"]
    start = 0
    if after:
        for i, it in enumerate(items):
            if it["id"] == after:
                start = i + 1
                break
    page = items[start : start + first]
    nodes = [_issue_node(i) for i in page]
    next_cursor = page[-1]["id"] if page and start + first < len(items) else None
    return {
        "data": {
            "issues": {
                "nodes": nodes,
                "pageInfo": {
                    "hasNextPage": next_cursor is not None,
                    "endCursor": next_cursor,
                },
            },
        },
    }


def _issue_node(issue: dict[str, Any]) -> dict[str, Any]:
    """Public issue shape (strip internal keys)."""
    return {k: v for k, v in issue.items() if not k.startswith("_")}


def handle_graphql(
    linear: dict[str, Any], query: str, _variables: dict[str, Any] | None
) -> dict[str, Any]:
    q = query.replace("\n", " ").strip()
    if "viewer" in q and "organization" in q:
        return viewer_org(linear)
    if "issues" in q.lower():
        return issues_connection(linear, first=50, after=None)
    return {"data": {"viewer": linear["viewer"]}}
