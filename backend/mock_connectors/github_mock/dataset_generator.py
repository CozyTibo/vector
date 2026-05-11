"""GitHub REST view helpers (local mock only)."""

from __future__ import annotations

import hashlib
from typing import Any


def _page_slice(items: list[dict[str, Any]], *, page: int, per_page: int) -> tuple[list[dict[str, Any]], int]:
    total = len(items)
    start = max(page - 1, 0) * max(per_page, 1)
    return items[start : start + max(per_page, 1)], total


def _repository_object_for_repo(gh: dict[str, Any], owner: str, repo_name: str) -> dict[str, Any]:
    """Subset of GitHub ``repository`` on workflow runs / check runs — transform requires ``id`` or ``full_name``."""
    full = f"{owner}/{repo_name}"
    for r in gh.get("repos", []) or []:
        if not isinstance(r, dict) or str(r.get("full_name")) != full:
            continue
        rid = r.get("id")
        name = str(r.get("name") or repo_name)
        out: dict[str, Any] = {"name": name, "full_name": full}
        if isinstance(rid, int):
            out["id"] = rid
        elif isinstance(rid, str) and rid.strip().isdigit():
            out["id"] = int(rid.strip())
        nid = r.get("node_id")
        if isinstance(nid, str) and nid.strip():
            out["node_id"] = nid.strip()
        return out
    return {"full_name": full, "name": repo_name.split("/")[-1] if "/" in repo_name else repo_name}


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


def releases_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    rows = [
        {k: v for k, v in r.items() if not str(k).startswith("_")}
        for r in gh.get("releases", [])
        if isinstance(r, dict) and str((r.get("repository") or {}).get("full_name", "")) == full
    ]
    rows.sort(
        key=lambda r: str(r.get("published_at") or r.get("created_at") or ""),
        reverse=True,
    )
    return _page_slice(rows, page=page, per_page=per_page)


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


def commit_comments_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    """Repo-wide commit comments (`GET /repos/{owner}/{repo}/comments`)."""
    full = f"{owner}/{repo}"
    api_base = f"https://api.github.com/repos/{owner}/{repo}"
    html_base = f"https://github.com/{owner}/{repo}"
    rows = [c for c in gh.get("commits", []) if c.get("_repo") == full]
    comments: list[dict[str, Any]] = []
    for commit in rows:
        sha = commit.get("sha")
        if not isinstance(sha, str) or not sha.strip():
            continue
        digest = hashlib.sha256(f"{full}:{sha}".encode()).hexdigest()
        cid = 70_000_000 + (int(digest[:8], 16) % 10_000_000)
        commit_inner = commit.get("commit") if isinstance(commit.get("commit"), dict) else {}
        committer = commit_inner.get("committer") if isinstance(commit_inner.get("committer"), dict) else {}
        author_inner = commit_inner.get("author") if isinstance(commit_inner.get("author"), dict) else {}
        created = committer.get("date") or author_inner.get("date")
        user_obj = commit.get("author") if isinstance(commit.get("author"), dict) else None
        if user_obj is None:
            user_obj = {"login": "octocat", "id": 1, "node_id": "U_1", "type": "User"}
        comments.append(
            {
                "url": f"{api_base}/comments/{cid}",
                "html_url": f"{html_base}/commit/{sha}#commitcomment-{cid}",
                "id": cid,
                "node_id": f"CC_{digest[:12]}",
                "body": f"Mock repo commit comment for `{sha[:7]}`.",
                "path": None,
                "position": None,
                "line": None,
                "commit_id": sha,
                "user": user_obj,
                "created_at": created,
                "updated_at": created,
                "author_association": "MEMBER",
            }
        )
    comments.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return _page_slice(comments, page=page, per_page=per_page)


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


def pull_review_comments_for_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    pr_number: int,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    src_reviews = [
        r
        for r in gh.get("pull_request_reviews", [])
        if r.get("_repo_full") == full and int(r.get("_pr_num", -1)) == pr_number
    ]
    comments: list[dict[str, Any]] = []
    for idx, review in enumerate(src_reviews):
        rid = review.get("id")
        review_id = int(rid) if isinstance(rid, int) else 10_000 + idx
        comments.append(
            {
                "id": review_id * 10 + 1,
                "node_id": f"PRRC_{review_id}_1",
                "pull_request_review_id": review_id,
                "path": "README.md",
                "position": 1,
                "commit_id": review.get("commit_id"),
                "body": review.get("body") or "Looks good from review thread context.",
                "user": review.get("user"),
                "created_at": review.get("submitted_at"),
                "updated_at": review.get("submitted_at"),
            }
        )
    comments.sort(key=lambda r: str(r.get("updated_at", "")), reverse=True)
    return _page_slice(comments, page=page, per_page=per_page)


def check_runs_for_ref_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    ref: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    api_base = f"https://api.github.com/repos/{owner}/{repo}"
    html_base = f"https://github.com/{owner}/{repo}"
    rows = [c for c in gh.get("commits", []) if c.get("_repo") == full]
    if isinstance(ref, str) and ref.strip():
        rows = [c for c in rows if c.get("sha") == ref or ref in {"main", "master"}]
    repo_obj = _repository_object_for_repo(gh, owner, repo)
    out: list[dict[str, Any]] = []
    for idx, commit in enumerate(rows):
        sha = commit.get("sha")
        sha_str = sha if isinstance(sha, str) else ""
        cr_id = 30_000 + idx
        suite_id = 60_000 + idx
        started = commit.get("commit", {}).get("author", {}).get("date")
        completed = commit.get("commit", {}).get("committer", {}).get("date")
        suite_obj: dict[str, Any] = {
            "id": suite_id,
            "node_id": f"CS_{suite_id}",
            "head_branch": "main",
            "head_sha": sha_str,
            "status": "completed",
            "conclusion": "success",
            "url": f"{api_base}/check-suites/{suite_id}",
            "before": None,
            "after": sha_str,
            "pull_requests": [],
            "repository": dict(repo_obj),
        }
        out.append(
            {
                "id": cr_id,
                "node_id": f"CR_{cr_id}",
                "name": "ci / unit-tests",
                "head_sha": sha_str,
                "external_id": f"mock-check-{sha_str[:7] or idx}",
                "status": "completed",
                "conclusion": "success",
                "started_at": started,
                "completed_at": completed,
                "url": f"{api_base}/check-runs/{cr_id}",
                "html_url": f"{html_base}/commit/{sha_str}/checks/{cr_id}",
                "details_url": f"{html_base}/actions/runs/{cr_id}",
                "output": {"title": "mock", "summary": "pass", "text": None, "annotations_count": 0, "annotations_url": ""},
                "repository": dict(repo_obj),
                "check_suite": suite_obj,
                "app": {"id": 15368, "slug": "github-actions", "owner": {"login": "github", "id": 9919}, "name": "GitHub Actions"},
                "pull_requests": [],
            }
        )
    out.sort(key=lambda r: str(r.get("completed_at", "")), reverse=True)
    return _page_slice(out, page=page, per_page=per_page)


def workflow_runs_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    api_base = f"https://api.github.com/repos/{owner}/{repo}"
    html_base = f"https://github.com/{owner}/{repo}"
    rows = [c for c in gh.get("commits", []) if c.get("_repo") == full]
    repo_obj = _repository_object_for_repo(gh, owner, repo)
    out: list[dict[str, Any]] = []
    for idx, commit in enumerate(rows):
        sha = commit.get("sha")
        sha_str = sha if isinstance(sha, str) else ""
        run_id = 40_000 + idx
        suite_id = 60_000 + idx
        created = commit.get("commit", {}).get("author", {}).get("date")
        updated = commit.get("commit", {}).get("committer", {}).get("date")
        out.append(
            {
                "id": run_id,
                "node_id": f"WR_{run_id}",
                "name": "CI",
                "path": ".github/workflows/ci.yml",
                "display_title": "CI",
                "run_number": idx + 1,
                "event": "pull_request",
                "status": "completed",
                "conclusion": "success",
                "workflow_id": 12345,
                "check_suite_id": suite_id,
                "check_suite_node_id": f"CS_{suite_id}",
                "head_branch": "main",
                "head_sha": sha_str,
                "run_attempt": 1,
                "created_at": created,
                "updated_at": updated,
                "url": f"{api_base}/actions/runs/{run_id}",
                "html_url": f"{html_base}/actions/runs/{run_id}",
                "pull_requests": [],
                "repository": dict(repo_obj),
            }
        )
    out.sort(key=lambda r: str(r.get("updated_at", "")), reverse=True)
    return _page_slice(out, page=page, per_page=per_page)


def deployments_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    rows = [c for c in gh.get("commits", []) if c.get("_repo") == full][:50]
    out: list[dict[str, Any]] = []
    for idx, commit in enumerate(rows):
        out.append(
            {
                "id": 50_000 + idx,
                "sha": commit.get("sha"),
                "ref": "main",
                "task": "deploy",
                "environment": "production" if idx % 3 == 0 else "staging",
                "created_at": commit.get("commit", {}).get("author", {}).get("date"),
                "updated_at": commit.get("commit", {}).get("committer", {}).get("date"),
            }
        )
    out.sort(key=lambda r: str(r.get("updated_at", "")), reverse=True)
    return _page_slice(out, page=page, per_page=per_page)


def deployment_statuses_for_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    deployment_id: int,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    deployments, _ = deployments_for_repo_with_total(gh, owner, repo, page=1, per_page=500)
    dep = next((d for d in deployments if int(d.get("id", -1)) == deployment_id), None)
    if dep is None:
        return [], 0
    status_rows = [
        {
            "id": deployment_id * 10 + 1,
            "state": "in_progress",
            "description": "Deployment started",
            "created_at": dep.get("created_at"),
            "updated_at": dep.get("created_at"),
        },
        {
            "id": deployment_id * 10 + 2,
            "state": "success",
            "description": "Deployment finished",
            "created_at": dep.get("updated_at"),
            "updated_at": dep.get("updated_at"),
        },
    ]
    return _page_slice(status_rows, page=page, per_page=per_page)


def branches_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    rows = [c for c in gh.get("commits", []) if c.get("_repo") == full]
    sha = rows[0].get("sha") if rows else "0000000"
    branches = [
        {"name": "main", "commit": {"sha": sha}},
        {"name": "develop", "commit": {"sha": sha}},
    ]
    return _page_slice(branches, page=page, per_page=per_page)


def tags_for_repo_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    full = f"{owner}/{repo}"
    rows = [c for c in gh.get("commits", []) if c.get("_repo") == full]
    tags: list[dict[str, Any]] = []
    for idx, commit in enumerate(rows[:8]):
        tags.append({"name": f"v1.{idx}.0", "commit": {"sha": commit.get("sha"), "url": "https://api.github.com"}})
    return _page_slice(tags, page=page, per_page=per_page)


def issue_timeline_for_with_total(
    gh: dict[str, Any],
    owner: str,
    repo: str,
    issue_number: int,
    *,
    page: int,
    per_page: int,
) -> tuple[list[dict[str, Any]], int]:
    """Synthetic issue/PR timeline events keyed by ``owner/repo#issue_number``."""
    full = f"{owner}/{repo}"
    key = f"{full}#{issue_number}"
    timelines = gh.get("issue_timelines")
    rows: list[dict[str, Any]] = []
    if isinstance(timelines, dict):
        raw = timelines.get(key)
        if isinstance(raw, list):
            rows = [x for x in raw if isinstance(x, dict)]
    return _page_slice(rows, page=page, per_page=per_page)
