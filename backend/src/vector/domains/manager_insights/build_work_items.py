"""Step 2 — deterministic normalization from Step 1 payloads to WorkItems."""

from __future__ import annotations

import uuid
import zlib
from datetime import datetime
from typing import Any

from vector.contracts.manager_insights_activity import FetchActivityBundle, WorkItem, WorkItemBundle
from vector.domains.manager_insights.actor_resolve import ActorResolveFn


def _dt(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _summary(text: str | None, *, max_len: int = 240) -> str | None:
    if not text:
        return None
    s = " ".join(text.split())
    if not s:
        return None
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rstrip() + "..."


def _slack_user_external_id(row: dict[str, Any]) -> str | None:
    su = row.get("slack_user_id")
    if isinstance(su, str) and su.strip():
        return su.strip()
    u = row.get("user")
    if isinstance(u, str) and u.strip():
        if u.startswith("U") or u.startswith("W"):
            return u.strip()
        if "@" in u:
            return f"U_MOCK_{zlib.crc32(u.lower().encode()):08X}"
    email = row.get("user_email")
    if isinstance(email, str) and "@" in email:
        el = email.strip().lower()
        return f"U_MOCK_{zlib.crc32(el.encode()):08X}"
    return None


def _dual_write(
    resolve: ActorResolveFn | None,
    connector: str,
    *,
    owner_external_id: str | None,
    participant_external_ids: list[str | None],
    participants: list[str],
) -> tuple[uuid.UUID | None, list[uuid.UUID | None]]:
    if resolve is None:
        return None, []
    owner_actor_id = resolve(connector, owner_external_id) if owner_external_id else None
    out: list[uuid.UUID | None] = []
    for i, _p in enumerate(participants):
        ext = participant_external_ids[i] if i < len(participant_external_ids) else None
        out.append(resolve(connector, ext) if ext else None)
    return owner_actor_id, out


def _build_slack_items(payload: dict[str, Any], resolve: ActorResolveFn | None) -> list[WorkItem]:
    rows = payload.get("sampled_channel_messages")
    if not isinstance(rows, list):
        return []
    out: list[WorkItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        channel_id = row.get("channel_id")
        thread_ts = row.get("thread_ts")
        if not isinstance(channel_id, str) or not isinstance(thread_ts, str):
            continue
        title = f"Slack thread in {channel_id}"
        text = row.get("text") if isinstance(row.get("text"), str) else None
        participants = [row["user"]] if isinstance(row.get("user"), str) else []
        slack_uid = _slack_user_external_id(row)
        p_ext = [slack_uid if slack_uid else None for _ in participants]
        owner_actor_id, participant_actor_ids = _dual_write(
            resolve,
            "slack",
            owner_external_id=None,
            participant_external_ids=p_ext,
            participants=participants,
        )
        out.append(
            WorkItem(
                id=f"slack:message:{channel_id}:{thread_ts}",
                source="slack",
                type="message_thread",
                title=title,
                summary=_summary(text),
                status="open",
                created_at=_dt(row.get("created_at")),
                updated_at=_dt(row.get("updated_at")),
                participants=participants,
                owner_actor_id=owner_actor_id,
                participant_actor_ids=participant_actor_ids,
                source_ref={"channel_id": channel_id, "thread_ts": thread_ts},
            )
        )
    return out


def _build_github_items(payload: dict[str, Any], resolve: ActorResolveFn | None) -> list[WorkItem]:
    out: list[WorkItem] = []
    for key, item_type in (("sampled_pull_requests", "pull_request"), ("sampled_issues", "issue")):
        rows = payload.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            repo = row.get("repo")
            number = row.get("number")
            if not isinstance(repo, str) or not isinstance(number, int):
                continue
            rid = f"github:{'pr' if item_type == 'pull_request' else 'issue'}:{repo}:{number}"
            author_id = row.get("author_id")
            ext_owner = (
                str(author_id).strip()
                if isinstance(author_id, (int, str)) and str(author_id).strip()
                else None
            )
            owner_actor_id, participant_actor_ids = _dual_write(
                resolve,
                "github",
                owner_external_id=ext_owner,
                participant_external_ids=[],
                participants=[],
            )
            out.append(
                WorkItem(
                    id=rid,
                    source="github",
                    type=item_type,  # type: ignore[arg-type]
                    title=row.get("title") if isinstance(row.get("title"), str) else f"{repo} #{number}",
                    summary=_summary(row.get("body") if isinstance(row.get("body"), str) else None),
                    status=row.get("state") if isinstance(row.get("state"), str) else None,
                    url=row.get("html_url") if isinstance(row.get("html_url"), str) else None,
                    project=repo,
                    owner=row.get("author") if isinstance(row.get("author"), str) else None,
                    created_at=_dt(row.get("created_at")),
                    updated_at=_dt(row.get("updated_at")),
                    closed_at=_dt(row.get("closed_at")),
                    owner_actor_id=owner_actor_id,
                    participant_actor_ids=participant_actor_ids,
                    source_ref={"repo": repo, "number": str(number)},
                )
            )
    return out


def _build_linear_items(payload: dict[str, Any], resolve: ActorResolveFn | None) -> list[WorkItem]:
    rows = payload.get("sampled_issues")
    if not isinstance(rows, list):
        return []
    out: list[WorkItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = row.get("identifier")
        issue_id = row.get("id")
        if not isinstance(ident, str) and not isinstance(issue_id, str):
            continue
        key = ident if isinstance(ident, str) else str(issue_id)
        assignee_id = row.get("assignee_id")
        ext_owner = str(assignee_id).strip() if isinstance(assignee_id, str) and assignee_id.strip() else None
        owner_actor_id, participant_actor_ids = _dual_write(
            resolve,
            "linear",
            owner_external_id=ext_owner,
            participant_external_ids=[],
            participants=[],
        )
        out.append(
            WorkItem(
                id=f"linear:issue:{key}",
                source="linear",
                type="issue",
                title=row.get("title") if isinstance(row.get("title"), str) else key,
                summary=_summary(row.get("description") if isinstance(row.get("description"), str) else None),
                status=row.get("state_name") if isinstance(row.get("state_name"), str) else None,
                url=row.get("url") if isinstance(row.get("url"), str) else None,
                project=row.get("project_name") if isinstance(row.get("project_name"), str) else None,
                owner=row.get("assignee_name") if isinstance(row.get("assignee_name"), str) else None,
                created_at=_dt(row.get("created_at")),
                updated_at=_dt(row.get("updated_at")),
                owner_actor_id=owner_actor_id,
                participant_actor_ids=participant_actor_ids,
                source_ref={"identifier": key},
            )
        )
    return out


def _build_notion_items(payload: dict[str, Any], resolve: ActorResolveFn | None) -> list[WorkItem]:
    rows = payload.get("sampled_pages")
    if not isinstance(rows, list):
        return []
    out: list[WorkItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        page_id = row.get("id")
        if not isinstance(page_id, str):
            continue
        last_edited_by_id = row.get("last_edited_by_id")
        ext_owner = (
            str(last_edited_by_id).strip()
            if isinstance(last_edited_by_id, str) and last_edited_by_id.strip()
            else None
        )
        owner_actor_id, participant_actor_ids = _dual_write(
            resolve,
            "notion",
            owner_external_id=ext_owner,
            participant_external_ids=[],
            participants=[],
        )
        out.append(
            WorkItem(
                id=f"notion:page:{page_id}",
                source="notion",
                type="document",
                title=row.get("title") if isinstance(row.get("title"), str) else "Untitled Notion page",
                summary=_summary(row.get("snippet") if isinstance(row.get("snippet"), str) else None),
                status="active",
                url=row.get("url") if isinstance(row.get("url"), str) else None,
                owner=row.get("owner") if isinstance(row.get("owner"), str) else None,
                updated_at=_dt(row.get("last_edited_time")),
                owner_actor_id=owner_actor_id,
                participant_actor_ids=participant_actor_ids,
                source_ref={"page_id": page_id},
            )
        )
    return out


def _build_calls_items(payload: dict[str, Any], resolve: ActorResolveFn | None) -> list[WorkItem]:
    rows = payload.get("sampled_events")
    if not isinstance(rows, list):
        return []
    out: list[WorkItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        event_id = row.get("id")
        calendar_id = row.get("calendar_id")
        if not isinstance(event_id, str) or not isinstance(calendar_id, str):
            continue
        org_id = row.get("organizer_id")
        ext_owner = str(org_id).strip() if isinstance(org_id, str) and org_id.strip() else None
        owner_actor_id, participant_actor_ids = _dual_write(
            resolve,
            "calls",
            owner_external_id=ext_owner,
            participant_external_ids=[],
            participants=[],
        )
        out.append(
            WorkItem(
                id=f"calls:event:{calendar_id}:{event_id}",
                source="calls",
                type="call",
                title=row.get("summary") if isinstance(row.get("summary"), str) else "Calendar event",
                summary=_summary(row.get("description") if isinstance(row.get("description"), str) else None),
                status=row.get("status") if isinstance(row.get("status"), str) else None,
                url=row.get("html_link") if isinstance(row.get("html_link"), str) else None,
                project="calls",
                owner=row.get("organizer_email")
                if isinstance(row.get("organizer_email"), str)
                else None,
                created_at=_dt(row.get("created")),
                updated_at=_dt(row.get("updated")),
                closed_at=_dt(row.get("end")),
                owner_actor_id=owner_actor_id,
                participant_actor_ids=participant_actor_ids,
                source_ref={"calendar_id": calendar_id, "event_id": event_id},
            )
        )
    return out


def build_work_items(
    bundle: FetchActivityBundle,
    *,
    resolve_actor: ActorResolveFn | None = None,
) -> WorkItemBundle:
    """Normalize Step 1 connector payloads into deterministic WorkItems."""
    items: list[WorkItem] = []
    connectors = bundle.connectors
    if "slack" in connectors:
        items.extend(_build_slack_items(connectors["slack"].payload, resolve_actor))
    if "github" in connectors:
        items.extend(_build_github_items(connectors["github"].payload, resolve_actor))
    if "linear" in connectors:
        items.extend(_build_linear_items(connectors["linear"].payload, resolve_actor))
    if "notion" in connectors:
        items.extend(_build_notion_items(connectors["notion"].payload, resolve_actor))
    if "calls" in connectors:
        items.extend(_build_calls_items(connectors["calls"].payload, resolve_actor))

    # deterministic order for downstream reproducibility
    items.sort(key=lambda x: x.id)
    return WorkItemBundle(
        run_id=bundle.run_id,
        tenant_id=bundle.tenant_id,
        window_days=bundle.window_days,
        items=items,
    )
