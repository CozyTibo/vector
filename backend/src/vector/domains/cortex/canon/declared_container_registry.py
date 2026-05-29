"""Declared work container classification at canon materialize time."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

ATTR_DECLARED_CONTAINER_KIND = "declared_container_kind"
ATTR_DECLARED_CONTAINER_EXTERNAL_ID = "declared_container_external_id"

# Work-item attrs paths used for Level 0 membership (keyed by container kind).
CONTAINER_MEMBERSHIP_ATTR_PATHS: Final[dict[str, tuple[str, ...]]] = {
    "initiative": ("initiative_id",),
    "project": ("project_id",),
    "work_database": ("database_id",),
}

DIRECT_MEMBER_ENTITY_TYPES: Final[frozenset[str]] = frozenset({"work_item", "document"})


@dataclass(frozen=True, slots=True)
class DeclaredContainerSource:
    """Maps a canon resource_type to a provider-agnostic declared container kind."""

    kind: str


# Unconditional seeds at materialize time. Notion.database uses allowlist (notion_work_containers).
DECLARED_CONTAINER_SOURCES: Final[dict[str, DeclaredContainerSource]] = {
    "linear.initiative": DeclaredContainerSource(kind="initiative"),
    "linear.project": DeclaredContainerSource(kind="project"),
}


def declared_container_kind_for_resource_type(resource_type: str) -> str | None:
    """Unconditional registry lookup (Notion excluded — use declared_container_kind_for_materialize)."""
    spec = DECLARED_CONTAINER_SOURCES.get(resource_type)
    return spec.kind if spec is not None else None


def declared_container_kind_for_materialize(
    *,
    resource_type: str,
    external_id: str,
    notion_work_db_allowlist: frozenset[str] | None,
) -> str | None:
    unconditional = declared_container_kind_for_resource_type(resource_type)
    if unconditional is not None:
        return unconditional
    if resource_type == "notion.database" and notion_work_db_allowlist:
        if external_id in notion_work_db_allowlist:
            return "work_database"
    return None


def apply_declared_container_attrs(
    *,
    resource_type: str,
    attrs_json: dict,
    external_id: str,
    notion_work_db_allowlist: frozenset[str] | None = None,
) -> None:
    """Set declared container fields on canon attrs when resource is a qualified seed."""
    kind = declared_container_kind_for_materialize(
        resource_type=resource_type,
        external_id=external_id,
        notion_work_db_allowlist=notion_work_db_allowlist,
    )
    if kind is None:
        attrs_json.pop(ATTR_DECLARED_CONTAINER_KIND, None)
        attrs_json.pop(ATTR_DECLARED_CONTAINER_EXTERNAL_ID, None)
        return
    attrs_json[ATTR_DECLARED_CONTAINER_KIND] = kind
    attrs_json[ATTR_DECLARED_CONTAINER_EXTERNAL_ID] = external_id


def member_attrs_match_container(
    attrs_json: dict,
    *,
    container_kind: str,
    container_external_id: str,
) -> bool:
    paths = CONTAINER_MEMBERSHIP_ATTR_PATHS.get(container_kind, ())
    for path in paths:
        value = attrs_json.get(path)
        if isinstance(value, str) and value == container_external_id:
            return True
    return False


# Backward-compatible alias
work_item_matches_container = member_attrs_match_container
