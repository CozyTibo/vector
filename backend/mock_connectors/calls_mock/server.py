"""Google Calendar-like mock routes for Calls ingestion."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse


def _encode_cursor(idx: int) -> str:
    return f"page:{max(idx, 0)}"


def _decode_cursor(raw: str | None) -> int:
    if not isinstance(raw, str) or not raw.startswith("page:"):
        return 0
    try:
        return max(0, int(raw.split(":", 1)[1]))
    except ValueError:
        return 0


def _as_calendar_event(event: dict[str, Any]) -> dict[str, Any]:
    transcript = event.get("transcript") if isinstance(event.get("transcript"), dict) else None
    recording = event.get("recording") if isinstance(event.get("recording"), dict) else None
    attendees = []
    for raw in event.get("attendees", []):
        if not isinstance(raw, dict):
            continue
        attendees.append(
            {
                "email": raw.get("email"),
                "displayName": raw.get("display_name"),
                "responseStatus": raw.get("response_status"),
            }
        )
    payload = {
        "kind": "calendar#event",
        "etag": f"\"{event.get('id', 'unknown')}\"",
        "id": event.get("id"),
        "status": event.get("status") or "confirmed",
        "htmlLink": event.get("html_link"),
        "created": event.get("created"),
        "updated": event.get("updated"),
        "summary": event.get("summary"),
        "description": event.get("description"),
        "organizer": {"email": event.get("organizer_email"), "self": True},
        "creator": {"email": event.get("organizer_email")},
        "start": {"dateTime": event.get("start"), "timeZone": "UTC"},
        "end": {"dateTime": event.get("end"), "timeZone": "UTC"},
        "attendees": attendees,
        "conferenceData": {"conferenceId": event.get("id")},
        "extendedProperties": {
            "private": {
                "vector_transcript_json": json.dumps(transcript) if transcript is not None else "",
                "vector_recording_json": json.dumps(recording) if recording is not None else "",
            }
        },
    }
    if isinstance(event.get("recording"), dict):
        rec = event["recording"]
        payload["attachments"] = [
            {
                "fileUrl": rec.get("url"),
                "title": f"Recording {rec.get('recording_id') or payload.get('id')}",
                "mimeType": "video/mp4",
            }
        ]
    return payload


def build_calls_router(get_calls: Callable[[], dict[str, Any]]) -> APIRouter:
    r = APIRouter(prefix="/google-calendar/v3")

    @r.get("/calendars/{calendar_id}/events")
    def list_events(
        calendar_id: str,
        maxResults: int = Query(default=100),  # noqa: N803 - match Google API casing
        pageToken: str | None = Query(default=None),  # noqa: N803
        updatedMin: str | None = Query(default=None),  # noqa: N803
        orderBy: str | None = Query(default=None),  # noqa: N803
        singleEvents: str | None = Query(default=None),  # noqa: N803
    ) -> JSONResponse:
        del orderBy, singleEvents
        calls_payload = get_calls()
        all_events = [ev for ev in calls_payload.get("events", []) if isinstance(ev, dict)]
        all_events.sort(key=lambda ev: str(ev.get("updated") or ""), reverse=True)
        if isinstance(updatedMin, str) and updatedMin.strip():
            all_events = [ev for ev in all_events if str(ev.get("updated") or "") > updatedMin]
        start = _decode_cursor(pageToken)
        size = min(max(int(maxResults), 1), 2500)
        chunk = all_events[start : start + size]
        next_token = _encode_cursor(start + len(chunk)) if start + len(chunk) < len(all_events) else None
        items = [_as_calendar_event(ev) for ev in chunk]
        now = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
        return JSONResponse(
            {
                "kind": "calendar#events",
                "etag": f"\"mock-{calendar_id}\"",
                "summary": calendar_id,
                "description": None,
                "updated": now,
                "timeZone": "UTC",
                "accessRole": "owner",
                "items": items,
                "nextPageToken": next_token,
            }
        )

    return r
