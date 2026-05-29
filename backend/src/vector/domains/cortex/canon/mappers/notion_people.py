"""Deterministic Notion people-property parsing for assignee refs."""

from __future__ import annotations

# Kanban-style column names we treat as execution assignee (normalized lowercase).
NOTION_ASSIGNEE_PROPERTY_NAMES = frozenset(
    {
        "assignee",
        "assigned to",
        "assigned",
        "owner",
    },
)


def _norm_property_name(name: str) -> str:
    return name.strip().lower()


def _is_assignee_property_name(name: str) -> bool:
    norm = _norm_property_name(name)
    if norm in NOTION_ASSIGNEE_PROPERTY_NAMES:
        return True
    # Compound owner columns (e.g. Fizzer "Product owner") without matching unrelated people fields.
    return norm.endswith(" owner")


def _properties_from_notion_segment(segment: dict) -> dict:
    props = segment.get("properties")
    return props if isinstance(props, dict) else {}


def iter_notion_people_assignments(properties: dict) -> list[tuple[str, str]]:
    """Return (property_name, notion_user_id) in stable order."""
    out: list[tuple[str, str]] = []
    if not isinstance(properties, dict):
        return out
    for prop_name in sorted(properties.keys()):
        if not _is_assignee_property_name(str(prop_name)):
            continue
        prop = properties[prop_name]
        if not isinstance(prop, dict) or prop.get("type") != "people":
            continue
        people = prop.get("people")
        if not isinstance(people, list):
            continue
        user_ids: list[str] = []
        for person in people:
            if not isinstance(person, dict):
                continue
            pid = person.get("id")
            if isinstance(pid, str) and pid.strip():
                user_ids.append(pid.strip())
        for uid in sorted(user_ids):
            out.append((str(prop_name), uid))
    return out


def primary_notion_assignee_user_id(segment: dict) -> str | None:
    pairs = iter_notion_people_assignments(_properties_from_notion_segment(segment))
    return pairs[0][1] if pairs else None


def notion_payload_segment(payload: dict, preferred_key: str) -> dict | None:
    """Resolve the embedded Notion object for a canon/graph payload."""
    keys = [preferred_key]
    if preferred_key == "database_row":
        keys.append("row")
    elif preferred_key == "row":
        keys.append("database_row")
    for key in keys:
        segment = payload.get(key)
        if isinstance(segment, dict):
            return segment
    return None


def notion_segment_properties(payload: dict) -> dict:
    """Properties dict from a notion.page / database_row / row payload segment."""
    for key in ("database_row", "row", "page", "block"):
        segment = payload.get(key)
        if isinstance(segment, dict):
            props = _properties_from_notion_segment(segment)
            if props:
                return props
    return {}
