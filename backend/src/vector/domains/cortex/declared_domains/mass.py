"""Declared domain mass weights per entity type."""

from __future__ import annotations

MASS_BY_ENTITY_TYPE: dict[str, int] = {
    "work_item": 10,
    "message": 3,
    "document": 5,
    "pull_request": 8,
    "commit": 2,
    "comment": 1,
}


def mass_for_entity_type(entity_type: str) -> int:
    return MASS_BY_ENTITY_TYPE.get(entity_type, 1)
