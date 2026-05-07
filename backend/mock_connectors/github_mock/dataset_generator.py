"""GitHub REST view helpers (local mock only)."""

from __future__ import annotations

from typing import Any


def installation_repositories_payload(
    gh: dict[str, Any], *, page: int, per_page: int
) -> dict[str, Any]:
    repos = gh["repos"]
    start = (page - 1) * per_page
    chunk = repos[start : start + per_page]
    return {"total_count": len(repos), "repositories": [_public_repo(r) for r in chunk]}


def _public_repo(r: dict[str, Any]) -> dict[str, Any]:
    """Shape expected by GitHub REST (subset used by projections)."""
    owner = r["owner"]
    return {
        "id": r["id"],
        "node_id": r["node_id"],
        "name": r["name"],
        "full_name": r["full_name"],
        "private": r["private"],
        "owner": owner,
        "html_url": r["html_url"],
        "description": r["description"],
        "fork": r["fork"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
        "pushed_at": r["pushed_at"],
        "default_branch": r["default_branch"],
        "archived": r["archived"],
        "disabled": r["disabled"],
    }


def _pulls_filtered(gh: dict[str, Any], owner: str, repo: str) -> list[dict[str, Any]]:
    full = f"{owner}/{repo}"
    prs = [p for p in gh["pull_requests"] if p["base"]["repo"]["full_name"] == full]
    prs.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return prs


def pulls_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    prs = _pulls_filtered(gh, owner, repo)
    total = len(prs)
    start = (page - 1) * per_page
    chunk = [_strip_internal(p) for p in prs[start : start + per_page]]
    return chunk, total


def _strip_internal(p: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in p.items() if not k.startswith("_")}


def pull_commits_for_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    pr_number: int,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    key = f"{full}#{pr_number}"
    rows = gh["pr_commits"].get(key, [])
    total = len(rows)
    start = (page - 1) * per_page
    return rows[start : start + per_page], total


def issues_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    items = [i for i in gh["issues"] if i["repository"]["full_name"] == full]
    total = len(items)
    start = (page - 1) * per_page
    return items[start : start + per_page], total


def commits_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
    sha: str | None,
) -> tuple[list[dict[str, Any]], int]:
    del sha  # mock ignores sha filter for pagination totals (same as list)
    full = f"{owner}/{repo}"
    rows = [c for c in gh["commits"] if c.get("_repo") == full]
    total = len(rows)
    start = (page - 1) * per_page
    out: list[dict[str, Any]] = []
    for c in rows[start : start + per_page]:
        out.append({k: v for k, v in c.items() if not str(k).startswith("_")})
    return out, total


def issue_comments_for_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    issue_number: int,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    issue_url = f"https://github.com/{full}/issues/{issue_number}"
    rows = [c for c in gh.get("issue_comments", []) if c.get("issue_url") == issue_url]
    rows.sort(key=lambda c: str(c.get("updated_at", "")), reverse=True)
    total = len(rows)
    start = (page - 1) * per_page
    return rows[start : start + per_page], total


def pull_reviews_for_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    pr_number: int,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    rows = [
        {k: v for k, v in r.items() if not str(k).startswith("_")}
        for r in gh.get("pull_request_reviews", [])
        if r.get("_repo_full") == full and int(r.get("_pr_num", -1)) == pr_number
    ]
    rows.sort(key=lambda r: str(r.get("submitted_at", "")), reverse=True)
    total = len(rows)
    start = (page - 1) * per_page
    return rows[start : start + per_page], total
