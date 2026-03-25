"""ORM / value helpers for JSON responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import inspect as sa_inspect


def jsonable_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    return v


def orm_to_dict(obj: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in sa_inspect(obj).mapper.column_attrs:
        key = col.key
        out[key] = jsonable_value(getattr(obj, key))
    return out
