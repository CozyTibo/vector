"""Step 1 — FetchActivity: live, bounded raw reads per connector (no merging, no LLM)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from vector.contracts.manager_insights_activity import (
    ConnectorCompletenessStats,
    ConnectorCoverageStats,
    ConnectorFetchResult,
    FetchActivityBundle,
    ManagerInsightConnector,
)
from vector.domains.connectors.github.http_client import (
    GitHubApiError,
    create_github_installation_access_token,
)
from vector.domains.connectors.github.install_flow import github_connector_configured
from vector.domains.connectors.notion.oauth_flow import notion_connector_configured
from vector.domains.connectors.calls.oauth_flow import calls_connector_configured
from vector.domains.manager_insights.data_reliability import default_window, utc_now
from vector.infrastructure.db.repositories import calls_connection as calls_repo
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import linear_connection as linear_repo
from vector.infrastructure.db.repositories import notion_connection as notion_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.settings import Settings

_logger = logging.getLogger(__name__)

_SLACK_API = "https://slack.com/api"
_GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


def _base_result(
    connector: ManagerInsightConnector,
    *,
    window_start: datetime,
    window_end: datetime,
    status: str,
    fetched_at: datetime | None = None,
    errors: list[str] | None = None,
    caps_applied: list[str] | None = None,
    coverage: ConnectorCoverageStats | None = None,
    completeness: ConnectorCompletenessStats | None = None,
    payload: dict[str, Any] | None = None,
) -> ConnectorFetchResult:
    return ConnectorFetchResult(
        connector=connector,
        status=status,  # type: ignore[arg-type]
        fetched_at=fetched_at,
        window_start=window_start,
        window_end=window_end,
        caps_applied=caps_applied or [],
        errors=errors or [],
        coverage=coverage or ConnectorCoverageStats(),
        completeness=completeness or ConnectorCompletenessStats(),
        payload=payload or {},
    )


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _notion_plain_text_from_rich_text(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    chunks: list[str] = []
    for part in value:
        if not isinstance(part, dict):
            continue
        plain = part.get("plain_text")
        if isinstance(plain, str) and plain.strip():
            chunks.append(plain.strip())
    if not chunks:
        return None
    return " ".join(chunks)


def _notion_result_title(row: dict[str, Any]) -> str | None:
    # Databases from search results often carry top-level title rich_text.
    top_level = _notion_plain_text_from_rich_text(row.get("title"))
    if top_level:
        return top_level

    props = row.get("properties")
    if not isinstance(props, dict):
        return None
    # Page entries usually store the title under a user-defined property key
    # with shape: { type: "title", title: [...] }.
    for value in props.values():
        if not isinstance(value, dict):
            continue
        if value.get("type") != "title":
            continue
        txt = _notion_plain_text_from_rich_text(value.get("title"))
        if txt:
            return txt
    return None


def _parse_iso(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _in_window(raw: object, *, window_start: datetime, window_end: datetime) -> bool:
    dt = _parse_iso(raw)
    if dt is None:
        return False
    return window_start <= dt <= window_end


def _fetch_mock_company_dataset(settings: Settings) -> dict[str, Any]:
    base = settings.vector_mock_connector_base_url.rstrip("/")
    url = f"{base}/admin/dataset/full"
    try:
        resp = httpx.get(url, timeout=20.0)
    except httpx.RequestError as e:
        raise RuntimeError(f"mock_dataset_transport:{e}") from e
    if resp.status_code >= 400:
        raise RuntimeError(f"mock_dataset_http_{resp.status_code}")
    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError("mock_dataset_non_json") from e
    if not isinstance(data, dict):
        raise RuntimeError("mock_dataset_unexpected_shape")
    return data


def _mock_slack_result(
    dataset: dict[str, Any],
    *,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    now = utc_now()
    rows = dataset.get("slack_events")
    if not isinstance(rows, list):
        rows = []
    in_window = [r for r in rows if isinstance(r, dict)]
    channel_counts: dict[str, int] = {}
    sampled_messages: list[dict[str, Any]] = []
    for r in in_window:
        channel = str(r.get("channel") or "unknown")
        channel_id = channel
        channel_counts[channel_id] = channel_counts.get(channel_id, 0) + 1
        ts = str(r.get("ts") or "")
        if not ts:
            continue
        sampled_messages.append(
            {
                "channel_id": channel_id,
                "thread_ts": ts,
                "text": str(r.get("text") or ""),
                "user": str(r.get("user_email") or ""),
                "created_at": ts,
                "updated_at": ts,
            }
        )
    sampled_channel_activity = [
        {"channel_id": ch, "message_count": n, "has_more": False}
        for ch, n in sorted(channel_counts.items())
    ]
    return _base_result(
        "slack",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        coverage=ConnectorCoverageStats(
            configured_sources=max(1, len(sampled_channel_activity)),
            successful_sources=max(1, len(sampled_channel_activity)),
            critical_configured_sources=1,
            critical_successful_sources=1,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=max(1, len(sampled_channel_activity)),
            capped_sources=0,
            expected_non_empty_sources=max(1, len(sampled_channel_activity)),
            observed_non_empty_sources=max(1, len(sampled_channel_activity)) if sampled_messages else 0,
        ),
        payload={
            "window_start": _iso(window_start),
            "window_end": _iso(window_end),
            "mock_mode": True,
            "public_and_private_channel_count": len(sampled_channel_activity),
            "sampled_channel_activity": sampled_channel_activity,
            "sampled_channel_messages": sampled_messages[:40],
        },
    )


def _mock_github_result(
    dataset: dict[str, Any],
    *,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    now = utc_now()
    gh = dataset.get("github")
    if not isinstance(gh, dict):
        gh = {}
    repos = gh.get("repos") if isinstance(gh.get("repos"), list) else []
    pulls = gh.get("pull_requests") if isinstance(gh.get("pull_requests"), list) else []
    issues = gh.get("issues") if isinstance(gh.get("issues"), list) else []
    sampled_pulls: list[dict[str, Any]] = []
    sampled_issues: list[dict[str, Any]] = []
    for pr in pulls:
        if not isinstance(pr, dict):
            continue
        updated_at = pr.get("updated_at")
        created_at = pr.get("created_at")
        closed_at = pr.get("closed_at")
        repo = pr.get("_repo_full")
        if not isinstance(repo, str):
            base_repo = pr.get("base")
            if isinstance(base_repo, dict):
                base_repo_repo = base_repo.get("repo")
                if isinstance(base_repo_repo, dict) and isinstance(base_repo_repo.get("full_name"), str):
                    repo = base_repo_repo["full_name"]
        if not isinstance(repo, str):
            continue
        num = pr.get("number")
        if not isinstance(num, int):
            continue
        sampled_pulls.append(
            {
                "repo": repo,
                "number": num,
                "title": pr.get("title") if isinstance(pr.get("title"), str) else None,
                "body": pr.get("body") if isinstance(pr.get("body"), str) else None,
                "state": pr.get("state") if isinstance(pr.get("state"), str) else None,
                "html_url": pr.get("html_url") if isinstance(pr.get("html_url"), str) else None,
                "author": pr.get("user", {}).get("login")
                if isinstance(pr.get("user"), dict) and isinstance(pr.get("user", {}).get("login"), str)
                else None,
                "created_at": created_at if isinstance(created_at, str) else None,
                "updated_at": updated_at if isinstance(updated_at, str) else None,
                "closed_at": closed_at if isinstance(closed_at, str) else None,
            }
        )
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        updated_at = issue.get("updated_at")
        created_at = issue.get("created_at")
        repo = issue.get("repository", {}).get("full_name")
        if not isinstance(repo, str):
            continue
        num = issue.get("number")
        if not isinstance(num, int):
            continue
        sampled_issues.append(
            {
                "repo": repo,
                "number": num,
                "title": issue.get("title") if isinstance(issue.get("title"), str) else None,
                "body": issue.get("body") if isinstance(issue.get("body"), str) else None,
                "state": issue.get("state") if isinstance(issue.get("state"), str) else None,
                "html_url": issue.get("html_url") if isinstance(issue.get("html_url"), str) else None,
                "author": issue.get("user", {}).get("login")
                if isinstance(issue.get("user"), dict)
                and isinstance(issue.get("user", {}).get("login"), str)
                else None,
                "created_at": created_at if isinstance(created_at, str) else None,
                "updated_at": updated_at if isinstance(updated_at, str) else None,
                "closed_at": issue.get("closed_at") if isinstance(issue.get("closed_at"), str) else None,
            }
        )
    sampled_pulls.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    sampled_issues.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return _base_result(
        "github",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        coverage=ConnectorCoverageStats(
            configured_sources=max(1, len(repos) * 2),
            successful_sources=max(1, len(repos) * 2),
            critical_configured_sources=2,
            critical_successful_sources=2,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=max(1, len(repos) * 2),
            capped_sources=0,
            expected_non_empty_sources=max(1, len(repos)),
            observed_non_empty_sources=max(1, len(repos)) if sampled_pulls or sampled_issues else 0,
        ),
        payload={
            "mock_mode": True,
            "repository_page_count": len(repos),
            "total_count": len(repos),
            "sampled_repo_activity": [],
            "sampled_issues": sampled_issues[:30],
            "sampled_pull_requests": sampled_pulls[:30],
        },
    )


def _mock_linear_result(
    dataset: dict[str, Any],
    *,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    now = utc_now()
    linear = dataset.get("linear")
    if not isinstance(linear, dict):
        linear = {}
    issues = linear.get("issues") if isinstance(linear.get("issues"), list) else []
    projects = linear.get("projects") if isinstance(linear.get("projects"), list) else []
    sampled_issues: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        created_at = issue.get("createdAt")
        updated_at = issue.get("updatedAt")
        identifier = issue.get("identifier")
        if not isinstance(identifier, str):
            continue
        sampled_issues.append(
            {
                "id": issue.get("id") if isinstance(issue.get("id"), str) else None,
                "identifier": identifier,
                "title": issue.get("title") if isinstance(issue.get("title"), str) else None,
                "description": issue.get("description") if isinstance(issue.get("description"), str) else None,
                "url": f"https://linear.app/{identifier.lower()}",
                "state_name": issue.get("state", {}).get("name")
                if isinstance(issue.get("state"), dict)
                and isinstance(issue.get("state", {}).get("name"), str)
                else None,
                "project_name": issue.get("project", {}).get("name")
                if isinstance(issue.get("project"), dict)
                and isinstance(issue.get("project", {}).get("name"), str)
                else None,
                "assignee_name": issue.get("assignee", {}).get("name")
                if isinstance(issue.get("assignee"), dict)
                and isinstance(issue.get("assignee", {}).get("name"), str)
                else None,
                "created_at": created_at if isinstance(created_at, str) else None,
                "updated_at": updated_at if isinstance(updated_at, str) else None,
            }
        )
    sampled_issues.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return _base_result(
        "linear",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        coverage=ConnectorCoverageStats(
            configured_sources=2,
            successful_sources=2,
            critical_configured_sources=1,
            critical_successful_sources=1,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=2,
            capped_sources=0,
            expected_non_empty_sources=1,
            observed_non_empty_sources=1 if sampled_issues else 0,
        ),
        payload={
            "mock_mode": True,
            "issues_probe_count": len(sampled_issues),
            "has_more_issues": len(sampled_issues) > 50,
            "projects_probe_count": len(projects),
            "has_more_projects": len(projects) > 20,
            "sampled_issues": sampled_issues[:30],
        },
    )


def _mock_notion_result(
    dataset: dict[str, Any],
    *,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    now = utc_now()
    notion = dataset.get("notion")
    if not isinstance(notion, dict):
        notion = {}
    pages = notion.get("sampled_pages")
    if not isinstance(pages, list):
        pages = []
    filtered = [p for p in pages if isinstance(p, dict)]
    return _base_result(
        "notion",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        coverage=ConnectorCoverageStats(
            configured_sources=2,
            successful_sources=2,
            critical_configured_sources=1,
            critical_successful_sources=1,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=1,
            capped_sources=1 if len(filtered) > 20 else 0,
            expected_non_empty_sources=1,
            observed_non_empty_sources=1 if filtered else 0,
        ),
        payload={
            "mock_mode": True,
            "search_result_count": len(filtered),
            "has_more": bool(notion.get("has_more")),
            "users_me_ok": bool(notion.get("users_me_ok", True)),
            "sampled_pages": filtered[:30],
        },
    )


def _mock_calls_result(
    dataset: dict[str, Any],
    *,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    now = utc_now()
    calls = dataset.get("calls")
    if not isinstance(calls, dict):
        calls = {}
    events = calls.get("sampled_events")
    if not isinstance(events, list):
        events = []
    filtered_events = [e for e in events if isinstance(e, dict)]
    per_calendar: dict[str, dict[str, Any]] = {}
    for e in filtered_events:
        cid = e.get("calendar_id")
        if not isinstance(cid, str):
            continue
        row = per_calendar.setdefault(cid, {"calendar_id": cid, "event_count": 0, "has_more": False})
        row["event_count"] += 1
    sampled_calendar_events = sorted(per_calendar.values(), key=lambda x: str(x["calendar_id"]))
    return _base_result(
        "calls",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        coverage=ConnectorCoverageStats(
            configured_sources=max(1, len(sampled_calendar_events) + 1),
            successful_sources=max(1, len(sampled_calendar_events) + 1),
            critical_configured_sources=1,
            critical_successful_sources=1,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=max(1, len(sampled_calendar_events)),
            capped_sources=0,
            expected_non_empty_sources=max(1, len(sampled_calendar_events)),
            observed_non_empty_sources=max(1, len(sampled_calendar_events)) if filtered_events else 0,
        ),
        payload={
            "mock_mode": True,
            "calendar_count": len(sampled_calendar_events),
            "has_more": False,
            "sampled_calendar_events": sampled_calendar_events,
            "sampled_events": filtered_events[:30],
        },
    )


def _fetch_slack(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return _base_result(
            "slack",
            window_start=window_start,
            window_end=window_end,
            status="not_configured",
            errors=["tenant_not_connected"],
        )
    token = link.detail.bot_access_token
    now = utc_now()
    caps: list[str] = []
    errors: list[str] = []
    payload: dict[str, Any] = {"window_start": _iso(window_start), "window_end": _iso(window_end)}

    try:
        r = httpx.post(
            f"{_SLACK_API}/auth.test",
            data={"token": token},
            timeout=30.0,
        )
    except httpx.RequestError as e:
        _logger.warning("slack auth.test transport error: %s", e)
        return _base_result(
            "slack",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"transport:{e}"],
        )
    try:
        body = r.json()
    except ValueError:
        return _base_result(
            "slack",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"slack_auth_test_non_json_http_{r.status_code}"],
        )
    if not body.get("ok"):
        return _base_result(
            "slack",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[str(body.get("error", "slack_auth_test_failed"))],
            payload={"auth_test": body},
        )
    payload["auth_test"] = {k: v for k, v in body.items() if k not in ("url", "bot_id")}
    coverage_configured = 1
    coverage_successful = 1
    critical_configured = 1
    critical_successful = 1

    channels: list[dict[str, Any]] = []
    try:
        r2 = httpx.post(
            f"{_SLACK_API}/conversations.list",
            data={"token": token, "limit": "100", "types": "public_channel,private_channel"},
            timeout=30.0,
        )
        body2 = r2.json()
        if body2.get("ok"):
            chans = body2.get("channels")
            if isinstance(chans, list):
                channels = [c for c in chans if isinstance(c, dict)]
                payload["public_and_private_channel_count"] = len(channels)
                if body2.get("response_metadata", {}).get("next_cursor"):
                    caps.append("slack_conversations_list_has_more")
            payload["conversations_list_ok"] = True
        else:
            errors.append(f"conversations.list:{body2.get('error')}")
            payload["conversations_list_ok"] = False
    except (httpx.RequestError, ValueError) as e:
        errors.append(f"conversations.list:{e}")
        payload["conversations_list_ok"] = False

    sampled = channels[:5]
    sampled_rows: list[dict[str, Any]] = []
    sampled_messages: list[dict[str, Any]] = []
    history_success = 0
    history_capped = 0
    history_non_empty = 0
    for idx, ch in enumerate(sampled):
        ch_id = ch.get("id")
        if not isinstance(ch_id, str) or not ch_id:
            continue
        coverage_configured += 1
        if idx == 0:
            critical_configured += 1
        try:
            r3 = httpx.post(
                f"{_SLACK_API}/conversations.history",
                data={
                    "token": token,
                    "channel": ch_id,
                    "oldest": str(window_start.timestamp()),
                    "latest": str(window_end.timestamp()),
                    "inclusive": "true",
                    "limit": "50",
                },
                timeout=30.0,
            )
            body3 = r3.json()
        except (httpx.RequestError, ValueError) as e:
            errors.append(f"conversations.history:{ch_id}:{e}")
            continue
        if not body3.get("ok"):
            errors.append(f"conversations.history:{ch_id}:{body3.get('error')}")
            continue
        coverage_successful += 1
        history_success += 1
        if idx == 0:
            critical_successful += 1
        msgs = body3.get("messages")
        msg_count = len(msgs) if isinstance(msgs, list) else 0
        if msg_count > 0:
            history_non_empty += 1
        has_more = bool(body3.get("has_more"))
        if has_more:
            history_capped += 1
            caps.append(f"slack_history_capped:{ch_id}")
        sampled_rows.append({"channel_id": ch_id, "message_count": msg_count, "has_more": has_more})
        if isinstance(msgs, list):
            for m in msgs[:2]:
                if not isinstance(m, dict):
                    continue
                ts = m.get("ts")
                txt = m.get("text")
                if not isinstance(ts, str):
                    continue
                sampled_messages.append(
                    {
                        "channel_id": ch_id,
                        "thread_ts": str(m.get("thread_ts") or ts),
                        "text": txt if isinstance(txt, str) else None,
                        "user": m.get("user") if isinstance(m.get("user"), str) else None,
                        "created_at": datetime.fromtimestamp(float(ts), tz=window_end.tzinfo).isoformat()
                        if ts.replace(".", "", 1).isdigit()
                        else None,
                        "updated_at": datetime.fromtimestamp(float(ts), tz=window_end.tzinfo).isoformat()
                        if ts.replace(".", "", 1).isdigit()
                        else None,
                    }
                )
    payload["sampled_channel_activity"] = sampled_rows
    payload["sampled_channel_messages"] = sampled_messages[:20]

    return _base_result(
        "slack",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        errors=errors,
        caps_applied=caps,
        coverage=ConnectorCoverageStats(
            configured_sources=coverage_configured,
            successful_sources=coverage_successful,
            critical_configured_sources=critical_configured,
            critical_successful_sources=critical_successful,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=history_success,
            capped_sources=history_capped,
            expected_non_empty_sources=len(sampled_rows),
            observed_non_empty_sources=history_non_empty,
        ),
        payload=payload,
    )


def _fetch_github(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    if not github_connector_configured(settings):
        return _base_result(
            "github",
            window_start=window_start,
            window_end=window_end,
            status="global_disabled",
            errors=["github_app_credentials_missing_in_environment"],
        )
    link = gh_repo.get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        return _base_result(
            "github",
            window_start=window_start,
            window_end=window_end,
            status="not_configured",
            errors=["tenant_not_connected"],
        )
    now = utc_now()
    caps: list[str] = []
    errors: list[str] = []
    try:
        inst_token = create_github_installation_access_token(settings, link.installation_id)
    except GitHubApiError as e:
        return _base_result(
            "github",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[str(e)],
        )
    base = settings.github_rest_api_base_url().rstrip("/")
    url = f"{base}/installation/repositories"
    try:
        resp = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {inst_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params={"per_page": 30},
            timeout=30.0,
        )
    except httpx.RequestError as e:
        return _base_result(
            "github",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"transport:{e}"],
        )
    if resp.is_error:
        return _base_result(
            "github",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"github_http_{resp.status_code}"],
        )
    try:
        data = resp.json()
    except ValueError:
        return _base_result(
            "github",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=["github_non_json"],
        )
    repos = data.get("repositories") if isinstance(data, dict) else None
    nrepos = len(repos) if isinstance(repos, list) else 0
    total = data.get("total_count") if isinstance(data, dict) else None
    if isinstance(total, int) and total > nrepos:
        caps.append("github_installation_repositories_capped_at_per_page")
    sampled_repos: list[str] = []
    if isinstance(repos, list):
        for repo in repos[:3]:
            if isinstance(repo, dict) and isinstance(repo.get("full_name"), str):
                sampled_repos.append(repo["full_name"])
    repo_activity: list[dict[str, Any]] = []
    sampled_issues: list[dict[str, Any]] = []
    sampled_pull_requests: list[dict[str, Any]] = []
    source_configured = 1
    source_successful = 1
    critical_configured = 1
    critical_successful = 1
    non_empty = 0
    capped_sources = 0
    expected_non_empty = 0
    for idx, full_name in enumerate(sampled_repos):
        expected_non_empty += 1
        for kind in ("pulls", "issues"):
            source_configured += 1
            if idx == 0:
                critical_configured += 1
            params: dict[str, Any] = {
                "state": "all",
                "per_page": 20,
                "sort": "updated",
                "direction": "desc",
                "since": _iso(window_start),
            }
            endpoint = f"{base}/repos/{full_name}/{kind}"
            try:
                rr = httpx.get(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {inst_token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    params=params,
                    timeout=30.0,
                )
            except httpx.RequestError as e:
                errors.append(f"{kind}:{full_name}:transport:{e}")
                continue
            if rr.status_code >= 400:
                errors.append(f"{kind}:{full_name}:http_{rr.status_code}")
                continue
            try:
                items = rr.json()
            except ValueError:
                errors.append(f"{kind}:{full_name}:non_json")
                continue
            if not isinstance(items, list):
                errors.append(f"{kind}:{full_name}:unexpected_shape")
                continue
            source_successful += 1
            if idx == 0:
                critical_successful += 1
            item_count = len(items)
            if item_count > 0:
                non_empty += 1
            if item_count >= 20:
                capped_sources += 1
                caps.append(f"github_{kind}_capped:{full_name}")
            repo_activity.append({"repo": full_name, "kind": kind, "count": item_count})
            target = sampled_pull_requests if kind == "pulls" else sampled_issues
            for one in items[:5]:
                if not isinstance(one, dict):
                    continue
                num = one.get("number")
                if not isinstance(num, int):
                    continue
                target.append(
                    {
                        "repo": full_name,
                        "number": num,
                        "title": one.get("title") if isinstance(one.get("title"), str) else None,
                        "body": one.get("body") if isinstance(one.get("body"), str) else None,
                        "state": one.get("state") if isinstance(one.get("state"), str) else None,
                        "html_url": one.get("html_url") if isinstance(one.get("html_url"), str) else None,
                        "author": one.get("user", {}).get("login")
                        if isinstance(one.get("user"), dict)
                        and isinstance(one.get("user", {}).get("login"), str)
                        else None,
                        "created_at": one.get("created_at")
                        if isinstance(one.get("created_at"), str)
                        else None,
                        "updated_at": one.get("updated_at")
                        if isinstance(one.get("updated_at"), str)
                        else None,
                        "closed_at": one.get("closed_at")
                        if isinstance(one.get("closed_at"), str)
                        else None,
                    }
                )

    payload = {
        "repository_page_count": nrepos,
        "total_count": total if isinstance(total, int) else None,
        "sampled_repo_activity": repo_activity,
        "sampled_issues": sampled_issues[:30],
        "sampled_pull_requests": sampled_pull_requests[:30],
    }
    return _base_result(
        "github",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        errors=errors,
        caps_applied=caps,
        coverage=ConnectorCoverageStats(
            configured_sources=source_configured,
            successful_sources=source_successful,
            critical_configured_sources=critical_configured,
            critical_successful_sources=critical_successful,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=max(0, source_successful - 1),
            capped_sources=capped_sources,
            expected_non_empty_sources=expected_non_empty,
            observed_non_empty_sources=non_empty,
        ),
        payload=payload,
    )


def _fetch_linear(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    link = linear_repo.get_linear_connection_for_tenant(session, tenant_id)
    if link is None:
        return _base_result(
            "linear",
            window_start=window_start,
            window_end=window_end,
            status="not_configured",
            errors=["tenant_not_connected"],
        )
    now = utc_now()
    query = """
    query ManagerInsightsProbe {
      viewer {
        id
        name
        issues(
          first: 50,
          orderBy: updatedAt,
          filter: { updatedAt: { gte: "%(window_start)s" } }
        ) {
          nodes {
            id
            identifier
            title
            description
            url
            createdAt
            updatedAt
            state { name }
            project { name }
            assignee { name }
          }
          pageInfo { hasNextPage }
        }
        projects(first: 20) {
          nodes { id name }
          pageInfo { hasNextPage }
        }
      }
    }
    """
    query = query % {"window_start": _iso(window_start)}
    try:
        r = httpx.post(
            settings.linear_graphql_url(),
            json={"query": query},
            headers={
                "Authorization": f"Bearer {link.detail.access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    except httpx.RequestError as e:
        return _base_result(
            "linear",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"transport:{e}"],
        )
    if r.status_code >= 400:
        return _base_result(
            "linear",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"linear_http_{r.status_code}"],
        )
    try:
        body = r.json()
    except ValueError:
        return _base_result(
            "linear",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=["linear_non_json"],
        )
    errs = body.get("errors") if isinstance(body, dict) else None
    if errs:
        return _base_result(
            "linear",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"linear_graphql_errors:{errs!s}"],
        )
    data = body.get("data") if isinstance(body, dict) else None
    viewer = data.get("viewer") if isinstance(data, dict) else None
    issues: dict[str, Any] = {}
    if isinstance(viewer, dict):
        raw_issues = viewer.get("issues")
        issues = raw_issues if isinstance(raw_issues, dict) else {}
    nodes = issues.get("nodes") if isinstance(issues, dict) else None
    n = len(nodes) if isinstance(nodes, list) else 0
    page_info = issues.get("pageInfo") if isinstance(issues, dict) else None
    has_next = bool(isinstance(page_info, dict) and page_info.get("hasNextPage"))
    projects: dict[str, Any] = {}
    if isinstance(viewer, dict):
        raw_projects = viewer.get("projects")
        projects = raw_projects if isinstance(raw_projects, dict) else {}
    project_nodes = projects.get("nodes") if isinstance(projects, dict) else None
    n_projects = len(project_nodes) if isinstance(project_nodes, list) else 0
    projects_page = projects.get("pageInfo") if isinstance(projects, dict) else None
    projects_has_next = bool(isinstance(projects_page, dict) and projects_page.get("hasNextPage"))
    caps: list[str] = []
    if has_next:
        caps.append("linear_issues_probe_capped_at_50")
    if projects_has_next:
        caps.append("linear_projects_probe_capped_at_20")
    sampled_issues: list[dict[str, Any]] = []
    if isinstance(nodes, list):
        for one in nodes[:30]:
            if not isinstance(one, dict):
                continue
            sampled_issues.append(
                {
                    "id": one.get("id") if isinstance(one.get("id"), str) else None,
                    "identifier": one.get("identifier")
                    if isinstance(one.get("identifier"), str)
                    else None,
                    "title": one.get("title") if isinstance(one.get("title"), str) else None,
                    "description": one.get("description")
                    if isinstance(one.get("description"), str)
                    else None,
                    "url": one.get("url") if isinstance(one.get("url"), str) else None,
                    "state_name": one.get("state", {}).get("name")
                    if isinstance(one.get("state"), dict)
                    and isinstance(one.get("state", {}).get("name"), str)
                    else None,
                    "project_name": one.get("project", {}).get("name")
                    if isinstance(one.get("project"), dict)
                    and isinstance(one.get("project", {}).get("name"), str)
                    else None,
                    "assignee_name": one.get("assignee", {}).get("name")
                    if isinstance(one.get("assignee"), dict)
                    and isinstance(one.get("assignee", {}).get("name"), str)
                    else None,
                    "created_at": one.get("createdAt")
                    if isinstance(one.get("createdAt"), str)
                    else None,
                    "updated_at": one.get("updatedAt")
                    if isinstance(one.get("updatedAt"), str)
                    else None,
                }
            )
    payload = {
        "issues_probe_count": n,
        "has_more_issues": has_next,
        "projects_probe_count": n_projects,
        "has_more_projects": projects_has_next,
        "sampled_issues": sampled_issues,
    }
    return _base_result(
        "linear",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        caps_applied=caps,
        coverage=ConnectorCoverageStats(
            configured_sources=2,
            successful_sources=2,
            critical_configured_sources=1,
            critical_successful_sources=1,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=2,
            capped_sources=(1 if has_next else 0) + (1 if projects_has_next else 0),
            expected_non_empty_sources=1,
            observed_non_empty_sources=1 if n > 0 else 0,
        ),
        payload=payload,
    )


def _fetch_notion(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    if not notion_connector_configured(settings):
        return _base_result(
            "notion",
            window_start=window_start,
            window_end=window_end,
            status="global_disabled",
            errors=["notion_oauth_credentials_missing_in_environment"],
        )
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        return _base_result(
            "notion",
            window_start=window_start,
            window_end=window_end,
            status="not_configured",
            errors=["tenant_not_connected"],
        )
    now = utc_now()
    errors: list[str] = []
    headers = {
        "Authorization": f"Bearer {link.detail.access_token}",
        "Notion-Version": settings.notion_version,
        "Content-Type": "application/json",
    }
    try:
        r = httpx.post(
            f"{settings.notion_api_base_url().rstrip('/')}/search",
            headers=headers,
            json={
                "page_size": 20,
                "sort": {"direction": "descending", "timestamp": "last_edited_time"},
            },
            timeout=30.0,
        )
    except httpx.RequestError as e:
        return _base_result(
            "notion",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"transport:{e}"],
        )
    if r.status_code >= 400:
        err_snippet = ""
        try:
            err_body = r.json()
            if isinstance(err_body, dict):
                msg = err_body.get("message")
                if isinstance(msg, str):
                    err_snippet = msg[:200]
        except ValueError:
            err_snippet = r.text[:200]
        return _base_result(
            "notion",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"notion_http_{r.status_code}" + (f":{err_snippet}" if err_snippet else "")],
        )
    try:
        body = r.json()
    except ValueError:
        return _base_result(
            "notion",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=["notion_non_json"],
        )
    results = body.get("results") if isinstance(body, dict) else None
    rows = results if isinstance(results, list) else []
    # Keep strict window semantics in-code: count only items edited inside the window.
    in_window = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        edited = row.get("last_edited_time")
        if not isinstance(edited, str):
            continue
        try:
            edited_dt = datetime.fromisoformat(edited.replace("Z", "+00:00"))
        except ValueError:
            continue
        if window_start <= edited_dt <= window_end:
            in_window += 1
    n_results = in_window
    sampled_pages: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows[:30]:
            if not isinstance(row, dict):
                continue
            page_id = row.get("id")
            if not isinstance(page_id, str):
                continue
            title = _notion_result_title(row)
            sampled_pages.append(
                {
                    "id": page_id,
                    "url": row.get("url") if isinstance(row.get("url"), str) else None,
                    "title": title,
                    "owner": row.get("last_edited_by", {}).get("name")
                    if isinstance(row.get("last_edited_by"), dict)
                    and isinstance(row.get("last_edited_by", {}).get("name"), str)
                    else (
                        row.get("last_edited_by", {}).get("id")
                        if isinstance(row.get("last_edited_by"), dict)
                        and isinstance(row.get("last_edited_by", {}).get("id"), str)
                        else None
                    ),
                    "last_edited_time": row.get("last_edited_time")
                    if isinstance(row.get("last_edited_time"), str)
                    else None,
                    "snippet": title,
                }
            )
    has_more = bool(body.get("has_more")) if isinstance(body, dict) else False
    caps: list[str] = []
    if has_more:
        caps.append("notion_search_probe_capped_at_20")
    me_ok = False
    try:
        r2 = httpx.get(
            f"{settings.notion_api_base_url().rstrip('/')}/users/me",
            headers=headers,
            timeout=30.0,
        )
        if r2.status_code < 400:
            me_ok = True
        else:
            errors.append(f"notion_users_me_http_{r2.status_code}")
    except httpx.RequestError as e:
        errors.append(f"notion_users_me_transport:{e}")
    return _base_result(
        "notion",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        errors=errors,
        caps_applied=caps,
        coverage=ConnectorCoverageStats(
            configured_sources=2,
            successful_sources=1 + (1 if me_ok else 0),
            critical_configured_sources=1,
            critical_successful_sources=1,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=1,
            capped_sources=1 if has_more else 0,
            expected_non_empty_sources=1,
            observed_non_empty_sources=1 if n_results > 0 else 0,
        ),
        payload={
            "search_result_count": n_results,
            "has_more": has_more,
            "users_me_ok": me_ok,
            "sampled_pages": sampled_pages,
        },
    )


def _fetch_calls(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    window_start: datetime,
    window_end: datetime,
) -> ConnectorFetchResult:
    if not calls_connector_configured(settings):
        return _base_result(
            "calls",
            window_start=window_start,
            window_end=window_end,
            status="global_disabled",
            errors=["google_oauth_credentials_missing_in_environment"],
        )
    link = calls_repo.get_calls_connection_for_tenant(session, tenant_id)
    if link is None:
        return _base_result(
            "calls",
            window_start=window_start,
            window_end=window_end,
            status="not_configured",
            errors=["tenant_not_connected"],
        )
    now = utc_now()
    headers = {"Authorization": f"Bearer {link.detail.access_token}"}
    try:
        r = httpx.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            headers=headers,
            params={"maxResults": 20},
            timeout=30.0,
        )
    except httpx.RequestError as e:
        return _base_result(
            "calls",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"transport:{e}"],
        )
    if r.status_code >= 400:
        return _base_result(
            "calls",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=[f"calls_calendar_http_{r.status_code}"],
        )
    try:
        body = r.json()
    except ValueError:
        return _base_result(
            "calls",
            window_start=window_start,
            window_end=window_end,
            status="error",
            fetched_at=now,
            errors=["calls_calendar_non_json"],
        )
    items = body.get("items") if isinstance(body, dict) else None
    calendars = items if isinstance(items, list) else []
    n_items = len(calendars)
    next_page = body.get("nextPageToken") if isinstance(body, dict) else None
    caps: list[str] = []
    if isinstance(next_page, str) and next_page:
        caps.append("calls_calendar_list_capped_at_20")
    sampled = []
    sampled_events: list[dict[str, Any]] = []
    events_success = 0
    events_non_empty = 0
    events_capped = 0
    errors: list[str] = []
    configured_sources = 1
    successful_sources = 1
    critical_configured = 1
    critical_successful = 1
    for cal in calendars[:3]:
        if not isinstance(cal, dict):
            continue
        cal_id = cal.get("id")
        if not isinstance(cal_id, str) or not cal_id:
            continue
        configured_sources += 1
        try:
            r2 = httpx.get(
                f"{_GOOGLE_CALENDAR_API}/calendars/{cal_id}/events",
                headers=headers,
                params={
                    "timeMin": _iso(window_start),
                    "timeMax": _iso(window_end),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 50,
                },
                timeout=30.0,
            )
        except httpx.RequestError as e:
            errors.append(f"events:{cal_id}:transport:{e}")
            continue
        if r2.status_code >= 400:
            errors.append(f"events:{cal_id}:http_{r2.status_code}")
            continue
        try:
            body2 = r2.json()
        except ValueError:
            errors.append(f"events:{cal_id}:non_json")
            continue
        successful_sources += 1
        events_success += 1
        evs = body2.get("items")
        count = len(evs) if isinstance(evs, list) else 0
        if count > 0:
            events_non_empty += 1
        has_more = bool(body2.get("nextPageToken"))
        if has_more:
            events_capped += 1
            caps.append(f"calls_events_capped:{cal_id}")
        sampled.append({"calendar_id": cal_id, "event_count": count, "has_more": has_more})
        if isinstance(evs, list):
            for ev in evs[:5]:
                if not isinstance(ev, dict):
                    continue
                eid = ev.get("id")
                if not isinstance(eid, str):
                    continue
                start = ev.get("start")
                end = ev.get("end")
                sampled_events.append(
                    {
                        "calendar_id": cal_id,
                        "id": eid,
                        "summary": ev.get("summary") if isinstance(ev.get("summary"), str) else None,
                        "description": ev.get("description")
                        if isinstance(ev.get("description"), str)
                        else None,
                        "status": ev.get("status") if isinstance(ev.get("status"), str) else None,
                        "html_link": ev.get("htmlLink") if isinstance(ev.get("htmlLink"), str) else None,
                        "organizer_email": ev.get("organizer", {}).get("email")
                        if isinstance(ev.get("organizer"), dict)
                        and isinstance(ev.get("organizer", {}).get("email"), str)
                        else None,
                        "created": ev.get("created") if isinstance(ev.get("created"), str) else None,
                        "updated": ev.get("updated") if isinstance(ev.get("updated"), str) else None,
                        "end": end.get("dateTime")
                        if isinstance(end, dict) and isinstance(end.get("dateTime"), str)
                        else None,
                        "start": start.get("dateTime")
                        if isinstance(start, dict) and isinstance(start.get("dateTime"), str)
                        else None,
                    }
                )
    return _base_result(
        "calls",
        window_start=window_start,
        window_end=window_end,
        status="ok",
        fetched_at=now,
        errors=errors,
        caps_applied=caps,
        coverage=ConnectorCoverageStats(
            configured_sources=configured_sources,
            successful_sources=successful_sources,
            critical_configured_sources=critical_configured,
            critical_successful_sources=critical_successful,
        ),
        completeness=ConnectorCompletenessStats(
            successful_sources=events_success,
            capped_sources=events_capped,
            expected_non_empty_sources=len(sampled),
            observed_non_empty_sources=events_non_empty,
        ),
        payload={
            "calendar_count": n_items,
            "has_more": bool(next_page),
            "sampled_calendar_events": sampled,
            "sampled_events": sampled_events[:30],
        },
    )


def run_fetch_activity_bundle(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    window_days: int = 30,
    as_of: datetime | None = None,
) -> FetchActivityBundle:
    """Execute Step 1 for one tenant (tenant-level connector model only)."""

    window_start, window_end = default_window(window_days=window_days, as_of=as_of)
    if getattr(settings, "vector_use_mock_connectors", False):
        try:
            dataset = _fetch_mock_company_dataset(settings)
            connectors: dict[str, ConnectorFetchResult] = {
                "slack": _mock_slack_result(dataset, window_start=window_start, window_end=window_end),
                "github": _mock_github_result(dataset, window_start=window_start, window_end=window_end),
                "linear": _mock_linear_result(dataset, window_start=window_start, window_end=window_end),
                "notion": _mock_notion_result(dataset, window_start=window_start, window_end=window_end),
                "calls": _mock_calls_result(dataset, window_start=window_start, window_end=window_end),
            }
        except RuntimeError as e:
            err = str(e)
            connectors = {
                connector: _base_result(
                    connector,  # type: ignore[arg-type]
                    window_start=window_start,
                    window_end=window_end,
                    status="error",
                    fetched_at=utc_now(),
                    errors=[err],
                    payload={"mock_mode": True},
                )
                for connector in ("slack", "github", "linear", "notion", "calls")
            }
        return FetchActivityBundle(
            run_id=uuid.uuid4(),
            tenant_id=tenant_id,
            window_days=window_days,
            connectors=connectors,
        )

    connectors: dict[str, ConnectorFetchResult] = {
        "slack": _fetch_slack(
            session,
            tenant_id=tenant_id,
            window_start=window_start,
            window_end=window_end,
        ),
        "github": _fetch_github(
            session,
            settings,
            tenant_id=tenant_id,
            window_start=window_start,
            window_end=window_end,
        ),
        "linear": _fetch_linear(
            session,
            settings,
            tenant_id=tenant_id,
            window_start=window_start,
            window_end=window_end,
        ),
        "notion": _fetch_notion(
            session,
            settings,
            tenant_id=tenant_id,
            window_start=window_start,
            window_end=window_end,
        ),
        "calls": _fetch_calls(
            session,
            settings,
            tenant_id=tenant_id,
            window_start=window_start,
            window_end=window_end,
        ),
    }

    return FetchActivityBundle(
        run_id=uuid.uuid4(),
        tenant_id=tenant_id,
        window_days=window_days,
        connectors=connectors,
    )
