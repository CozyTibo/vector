"""Collect scannable text fields from raw payloads for graph reference/mention extractors."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.graph.extractors.patterns import MAX_TEXT_SCAN_CHARS


def _append_text(blobs: list[tuple[str, str]], path: str, value: object) -> None:
    if isinstance(value, str) and value.strip():
        blobs.append((path, value[:MAX_TEXT_SCAN_CHARS]))


def _rich_text_plain(properties: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for prop in properties.values():
        if not isinstance(prop, dict):
            continue
        rich = prop.get("rich_text") or prop.get("title")
        if not isinstance(rich, list):
            continue
        for block in rich:
            if isinstance(block, dict):
                plain = block.get("plain_text") or block.get("text", {}).get("content")
                if isinstance(plain, str) and plain.strip():
                    out.append(plain.strip())
    return out


def _rich_text_list(value: object) -> list[str]:
    out: list[str] = []
    if not isinstance(value, list):
        return out
    for block in value:
        if isinstance(block, dict):
            plain = block.get("plain_text") or block.get("text", {}).get("content")
            if isinstance(plain, str) and plain.strip():
                out.append(plain.strip())
    return out


def collect_scannable_text(
    payload: dict[str, Any],
    *,
    entity_type: str,
    connector: str,
    resource_type: str,
) -> list[tuple[str, str]]:
    """Return (field_path, text) pairs for cross-tool reference and mention scanning."""
    blobs: list[tuple[str, str]] = []

    if entity_type == "message":
        for key in ("message", "comment", "reply", "review"):
            segment = payload.get(key)
            if isinstance(segment, dict):
                for field in ("text", "body"):
                    _append_text(blobs, f"{key}.{field}", segment.get(field))

    if entity_type == "document" and connector == "notion":
        for key in ("page", "database_row", "block"):
            segment = payload.get(key)
            if not isinstance(segment, dict):
                continue
            _append_text(blobs, f"{key}.url", segment.get("url"))
            props = segment.get("properties")
            if isinstance(props, dict):
                for i, plain in enumerate(_rich_text_plain(props)):
                    _append_text(blobs, f"{key}.properties.{i}", plain)
            block_type = segment.get("type")
            if isinstance(block_type, str):
                content = segment.get(block_type)
                if isinstance(content, dict):
                    for i, plain in enumerate(_rich_text_list(content.get("rich_text"))):
                        _append_text(blobs, f"{key}.{block_type}.{i}", plain)

    if entity_type == "work_item" and connector == "notion":
        for key in ("row", "database_row"):
            segment = payload.get(key)
            if not isinstance(segment, dict):
                continue
            _append_text(blobs, f"{key}.url", segment.get("url"))
            props = segment.get("properties")
            if isinstance(props, dict):
                for i, plain in enumerate(_rich_text_plain(props)):
                    _append_text(blobs, f"{key}.properties.{i}", plain)

    if entity_type == "work_item":
        for key in ("issue",):
            segment = payload.get(key)
            if isinstance(segment, dict):
                for field in ("title", "description", "body"):
                    _append_text(blobs, f"{key}.{field}", segment.get(field))
        if connector == "linear" and resource_type == "linear.issue":
            segment = payload.get("issue")
            if isinstance(segment, dict):
                ident = segment.get("identifier")
                if isinstance(ident, str):
                    _append_text(blobs, "issue.identifier", ident)

    if entity_type == "pull_request":
        segment = payload.get("pull_request")
        if isinstance(segment, dict):
            for field in ("title", "body"):
                _append_text(blobs, f"pull_request.{field}", segment.get(field))

    if entity_type == "commit":
        segment = payload.get("commit")
        if isinstance(segment, dict):
            _append_text(blobs, "commit.message", segment.get("message"))

    # Legacy / shared envelope keys used by phase 1
    for key in ("pull_request", "issue", "comment", "message", "commit"):
        if key in ("message", "comment") and entity_type == "message":
            continue
        segment = payload.get(key)
        if isinstance(segment, dict):
            for field in ("body", "title", "message"):
                _append_text(blobs, f"{key}.{field}", segment.get(field))

    closing = payload.get("closing_issues")
    if isinstance(closing, list):
        for item in closing:
            if isinstance(item, dict):
                num = item.get("number")
                if isinstance(num, int):
                    _append_text(blobs, "closing_issues", f"#{num}")

    return blobs
