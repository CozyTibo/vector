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
}


@dataclass(frozen=True, slots=True)
class DeclaredContainerSource:
    """Maps a canon resource_type to a provider-agnostic declared container kind."""

    kind: str


# V1: Linear initiative + project only. Notion.database is intentionally absent (§7.1.1).
DECLARED_CONTAINER_SOURCES: Final[dict[str, DeclaredContainerSource]] = {
    "linear.initiative": DeclaredContainerSource(kind="initiative"),
    "linear.project": DeclaredContainerSource(kind="project"),
}


def declared_container_kind_for_resource_type(resource_type: str) -> str | None:
    spec = DECLARED_CONTAINER_SOURCES.get(resource_type)
    return spec.kind if spec is not None else None


def apply_declared_container_attrs(
    *,
    resource_type: str,
    attrs_json: dict,
    external_id: str,
) -> None:
    """Set declared container fields on canon attrs when resource is a qualified seed."""
    kind = declared_container_kind_for_resource_type(resource_type)
    if kind is None:
        attrs_json.pop(ATTR_DECLARED_CONTAINER_KIND, None)
        attrs_json.pop(ATTR_DECLARED_CONTAINER_EXTERNAL_ID, None)
        return
    attrs_json[ATTR_DECLARED_CONTAINER_KIND] = kind
    attrs_json[ATTR_DECLARED_CONTAINER_EXTERNAL_ID] = external_id


def work_item_matches_container(
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
