"""Deterministic Notion database property copying for execution rows."""

from __future__ import annotations

import re
from typing import Any

from vector.domains.cortex.canon.lifecycle_substrate import apply_status_attrs, finalize_execution_attrs


def _property_id(prop: dict[str, Any], fallback_name: str) -> str:
    pid = prop.get("id")
    if isinstance(pid, str) and pid.strip():
        return pid.strip()
    slug = re.sub(r"[^a-z0-9]+", "_", fallback_name.strip().lower()).strip("_")
    return slug or fallback_name


def _copy_status_property(prop: dict[str, Any], attrs: dict[str, Any]) -> None:
    status = prop.get("status")
    if not isinstance(status, dict):
        return
    name = status.get("name")
    sid = status.get("id")
    apply_status_attrs(
        attrs,
        status_name=name.strip() if isinstance(name, str) and name.strip() else None,
        status_id=sid.strip() if isinstance(sid, str) and sid.strip() else None,
    )


def _copy_select_property(prop: dict[str, Any], bucket: dict[str, Any], prop_id: str) -> None:
    select = prop.get("select")
    if not isinstance(select, dict):
        return
    name = select.get("name")
    sid = select.get("id")
    bucket[prop_id] = {
        "name": name if isinstance(name, str) else None,
        "id": sid if isinstance(sid, str) else None,
    }


def _copy_multi_select_property(prop: dict[str, Any], bucket: dict[str, Any], prop_id: str) -> None:
    items = prop.get("multi_select")
    if not isinstance(items, list):
        return
    bucket[prop_id] = [
        {
            "name": item.get("name") if isinstance(item, dict) else None,
            "id": item.get("id") if isinstance(item, dict) else None,
        }
        for item in items
        if isinstance(item, dict)
    ]


def _copy_date_property(prop: dict[str, Any], bucket: dict[str, Any], prop_id: str) -> None:
    date_val = prop.get("date")
    if not isinstance(date_val, dict):
        return
    bucket[prop_id] = {
        "start": date_val.get("start"),
        "end": date_val.get("end"),
        "time_zone": date_val.get("time_zone"),
    }


def _copy_checkbox_property(prop: dict[str, Any], bucket: dict[str, Any], prop_id: str) -> None:
    if "checkbox" in prop:
        bucket[prop_id] = bool(prop.get("checkbox"))


def apply_notion_execution_properties(segment: dict[str, Any], attrs: dict[str, Any]) -> None:
    """Copy typed execution properties from a Notion page/row segment into attrs_json."""
    properties = segment.get("properties")
    if not isinstance(properties, dict):
        finalize_execution_attrs(attrs)
        return

    selects: dict[str, Any] = {}
    multi_selects: dict[str, Any] = {}
    provider_dates: dict[str, Any] = {}
    checkboxes: dict[str, Any] = {}

    for prop_name, prop in sorted(properties.items()):
        if not isinstance(prop, dict):
            continue
        prop_type = prop.get("type")
        prop_id = _property_id(prop, str(prop_name))

        if prop_type == "status":
            _copy_status_property(prop, attrs)
        elif prop_type == "select":
            _copy_select_property(prop, selects, prop_id)
        elif prop_type == "multi_select":
            _copy_multi_select_property(prop, multi_selects, prop_id)
        elif prop_type == "date":
            _copy_date_property(prop, provider_dates, prop_id)
        elif prop_type == "checkbox":
            _copy_checkbox_property(prop, checkboxes, prop_id)

    if selects:
        attrs["selects"] = selects
    if multi_selects:
        attrs["multi_selects"] = multi_selects
    if provider_dates:
        attrs["provider_dates"] = provider_dates
    if checkboxes:
        attrs["checkboxes"] = checkboxes

    finalize_execution_attrs(attrs)
