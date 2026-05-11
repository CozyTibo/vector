"""Notion REST-like mock routes (subset used by Cortex ingestion)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse


def _encode_cursor(idx: int) -> str:
    return f"cur:{max(idx, 0)}"


def _decode_cursor(raw: str | None) -> int:
    if not isinstance(raw, str) or not raw.startswith("cur:"):
        return 0
    try:
        return max(0, int(raw.split(":", 1)[1]))
    except ValueError:
        return 0


def _annotations() -> dict[str, Any]:
    """Notion rich-text annotation defaults (Public API rich_text_item schema)."""
    return {
        "bold": False,
        "italic": False,
        "strikethrough": False,
        "underline": False,
        "code": False,
        "color": "default",
    }


def _title_property(title: str) -> dict[str, Any]:
    text_block = {
        "type": "text",
        "text": {"content": title, "link": None},
        "annotations": _annotations(),
        "plain_text": title,
    }
    return {"id": "title", "type": "title", "title": [text_block]}


def _as_page_object(page: dict[str, Any]) -> dict[str, Any]:
    page_id = str(page.get("id") or "")
    title = str(page.get("title") or "Untitled")
    edited = str(page.get("last_edited_time") or "2026-01-01T00:00:00Z")
    return {
        "object": "page",
        "id": page_id,
        "created_time": edited,
        "last_edited_time": edited,
        "archived": False,
        "url": page.get("url") or f"https://www.notion.so/{page_id.replace('-', '')}",
        "parent": {"type": "workspace", "workspace": True},
        "properties": {"Name": _title_property(title)},
    }


def _as_database_object(database_id: str, db: dict[str, Any]) -> dict[str, Any]:
    title = str(db.get("name") or f"Database {database_id[:8]}")
    edited = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    title_txt = {
        "type": "text",
        "text": {"content": title, "link": None},
        "annotations": _annotations(),
        "plain_text": title,
    }
    return {
        "object": "database",
        "id": database_id,
        "created_time": edited,
        "last_edited_time": edited,
        "title": [title_txt],
        "url": f"https://www.notion.so/{database_id.replace('-', '')}",
        "parent": {"type": "workspace", "workspace": True},
        "properties": {},
    }


def _as_database_row_object(row: dict[str, Any]) -> dict[str, Any]:
    props = row.get("properties") if isinstance(row.get("properties"), dict) else {}
    title_val = str(props.get("Name") or row.get("id") or "Row")
    notion_props: dict[str, Any] = {"Name": _title_property(title_val)}
    for k, v in props.items():
        if k == "Name":
            continue
        plain = str(v)
        notion_props[str(k)] = {
            "id": str(k)[:36],
            "type": "rich_text",
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": plain, "link": None},
                    "annotations": _annotations(),
                    "plain_text": plain,
                }
            ],
        }
    dbid = str(row.get("database_id") or "")
    return {
        "object": "page",
        "id": str(row.get("id") or ""),
        "created_time": row.get("created_time"),
        "last_edited_time": row.get("last_edited_time"),
        "archived": bool(row.get("archived")),
        "url": row.get("url"),
        "parent": {"type": "database_id", "database_id": dbid},
        "properties": notion_props,
    }


def _as_block_object(block: dict[str, Any], parent_id: str) -> dict[str, Any]:
    payload = {
        "object": "block",
        "id": str(block.get("id") or ""),
        "type": str(block.get("type") or "paragraph"),
        "has_children": bool(block.get("has_children")),
        "parent": {"type": "block_id", "block_id": parent_id},
    }
    blk_type = payload["type"]
    blk_body = block.get(blk_type)
    if isinstance(blk_body, dict):
        payload[blk_type] = blk_body
    else:
        txt = str(block.get("text") or "")
        payload[blk_type] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": txt, "link": None},
                    "annotations": _annotations(),
                    "plain_text": txt,
                }
            ]
        }
    return payload


def build_notion_router(get_notion: Callable[[], dict[str, Any]]) -> APIRouter:
    r = APIRouter(prefix="/notion/v1")

    @r.post("/search")
    def search(body: dict[str, Any]) -> JSONResponse:
        notion = get_notion()
        raw_pages = [p for p in notion.get("sampled_pages", []) if isinstance(p, dict)]
        raw_db_map = notion.get("databases") if isinstance(notion.get("databases"), dict) else {}
        raw_row_db_ids = {
            str(row.get("database_id"))
            for row in notion.get("database_rows", [])
            if isinstance(row, dict) and isinstance(row.get("database_id"), str)
        }
        database_ids = sorted(set(raw_db_map.keys()) | raw_row_db_ids)
        db_objects = [_as_database_object(dbid, raw_db_map.get(dbid) or {}) for dbid in database_ids]
        merged = [_as_page_object(p) for p in raw_pages] + db_objects
        merged.sort(key=lambda x: str(x.get("last_edited_time", "")), reverse=True)
        page_size_raw = body.get("page_size")
        page_size = min(max(int(page_size_raw), 1), 100) if isinstance(page_size_raw, int) else 100
        start = _decode_cursor(body.get("start_cursor") if isinstance(body, dict) else None)
        chunk = merged[start : start + page_size]
        next_cursor = _encode_cursor(start + len(chunk)) if start + len(chunk) < len(merged) else None
        return JSONResponse(
            {
                "object": "list",
                "results": chunk,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "type": "page_or_data_source",
                "page_or_data_source": {},
            }
        )

    @r.get("/databases/{database_id}")
    def get_database(database_id: str) -> JSONResponse:
        notion = get_notion()
        raw_db_map = notion.get("databases") if isinstance(notion.get("databases"), dict) else {}
        db = raw_db_map.get(database_id) if isinstance(raw_db_map.get(database_id), dict) else {}
        return JSONResponse(_as_database_object(database_id, db))

    @r.post("/databases/{database_id}/query")
    def query_database(database_id: str, body: dict[str, Any]) -> JSONResponse:
        notion = get_notion()
        rows = [
            _as_database_row_object(row)
            for row in notion.get("database_rows", [])
            if isinstance(row, dict) and str(row.get("database_id")) == database_id
        ]
        rows.sort(key=lambda x: str(x.get("last_edited_time", "")), reverse=True)
        page_size_raw = body.get("page_size")
        page_size = min(max(int(page_size_raw), 1), 100) if isinstance(page_size_raw, int) else 100
        start = _decode_cursor(body.get("start_cursor") if isinstance(body, dict) else None)
        chunk = rows[start : start + page_size]
        next_cursor = _encode_cursor(start + len(chunk)) if start + len(chunk) < len(rows) else None
        # Legacy POST /v1/databases/{id}/query (Notion-Version ≤ 2022-06-28): paginated page objects.
        return JSONResponse(
            {"object": "list", "results": chunk, "has_more": next_cursor is not None, "next_cursor": next_cursor}
        )

    @r.get("/blocks/{block_id}/children")
    def block_children(
        block_id: str,
        page_size: int = Query(default=100),
        start_cursor: str | None = Query(default=None),
    ) -> JSONResponse:
        notion = get_notion()
        blocks = [
            _as_block_object(block, block_id)
            for block in notion.get("blocks", [])
            if isinstance(block, dict) and str(block.get("parent_id")) == block_id
        ]
        size = min(max(int(page_size), 1), 100)
        start = _decode_cursor(start_cursor)
        chunk = blocks[start : start + size]
        next_cursor = _encode_cursor(start + len(chunk)) if start + len(chunk) < len(blocks) else None
        return JSONResponse(
            {
                "object": "list",
                "results": chunk,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "type": "block",
                "block": {},
            }
        )

    return r
