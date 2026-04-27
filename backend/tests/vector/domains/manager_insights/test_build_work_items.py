"""Tests for Step 2 normalization (raw payloads -> WorkItems)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from vector.contracts.manager_insights_activity import ConnectorFetchResult, FetchActivityBundle
from vector.domains.manager_insights.build_work_items import build_work_items


def _fetch(connector: str, payload: dict) -> ConnectorFetchResult:
    end = datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC)
    return ConnectorFetchResult(
        connector=connector,  # type: ignore[arg-type]
        status="ok",
        fetched_at=end,
        window_start=end - timedelta(days=30),
        window_end=end,
        payload=payload,
    )


def test_build_work_items_maps_all_sources() -> None:
    bundle = FetchActivityBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        connectors={
            "slack": _fetch(
                "slack",
                {
                    "sampled_channel_messages": [
                        {
                            "channel_id": "C1",
                            "thread_ts": "1745752862.001900",
                            "text": "Need to fix manager insight reliability.",
                            "user": "U1",
                            "created_at": "2026-04-27T10:00:00Z",
                            "updated_at": "2026-04-27T10:05:00Z",
                        }
                    ]
                },
            ),
            "github": _fetch(
                "github",
                {
                    "sampled_pull_requests": [
                        {
                            "repo": "angelcorp/vector",
                            "number": 42,
                            "title": "Add work item normalization",
                            "state": "open",
                            "html_url": "https://github.com/angelcorp/vector/pull/42",
                            "created_at": "2026-04-26T09:00:00Z",
                            "updated_at": "2026-04-27T09:00:00Z",
                        }
                    ],
                    "sampled_issues": [],
                },
            ),
            "linear": _fetch(
                "linear",
                {
                    "sampled_issues": [
                        {
                            "id": "lin_1",
                            "identifier": "ENG-9",
                            "title": "Debug reliability tiers",
                            "state_name": "In Progress",
                            "updated_at": "2026-04-27T08:00:00Z",
                        }
                    ]
                },
            ),
            "notion": _fetch(
                "notion",
                {
                    "sampled_pages": [
                        {
                            "id": "page_1",
                            "url": "https://notion.so/page_1",
                            "title": "Manager insights plan",
                            "owner": "Tibo",
                            "last_edited_time": "2026-04-27T07:00:00Z",
                        }
                    ]
                },
            ),
            "calls": _fetch(
                "calls",
                {
                    "sampled_events": [
                        {
                            "calendar_id": "primary",
                            "id": "ev1",
                            "summary": "Weekly sync",
                            "status": "confirmed",
                            "html_link": "https://calendar.google.com/event?eid=ev1",
                            "created": "2026-04-27T06:00:00Z",
                            "updated": "2026-04-27T06:30:00Z",
                            "end": "2026-04-27T07:00:00Z",
                        }
                    ]
                },
            ),
        },
    )
    out = build_work_items(bundle)
    assert out.run_id == bundle.run_id
    assert len(out.items) == 5
    ids = [x.id for x in out.items]
    assert ids == sorted(ids)
    assert any(i.startswith("slack:message:") for i in ids)
    assert any(i.startswith("github:pr:") for i in ids)
    assert any(i.startswith("linear:issue:") for i in ids)
    assert any(i.startswith("notion:page:") for i in ids)
    assert any(i.startswith("calls:event:") for i in ids)
    notion = next(x for x in out.items if x.id.startswith("notion:page:"))
    assert notion.owner == "Tibo"
