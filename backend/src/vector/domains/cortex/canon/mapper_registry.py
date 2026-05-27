"""Registry of per-resource_type CanonMapper implementations."""

from __future__ import annotations

from vector.domains.cortex.canon.mapper_types import CanonMapper
from vector.domains.cortex.canon.mappers.github_mapper import GITHUB_MAPPERS
from vector.domains.cortex.canon.mappers.linear_mapper import LINEAR_MAPPERS
from vector.domains.cortex.canon.mappers.notion_mapper import NOTION_MAPPERS
from vector.domains.cortex.canon.mappers.slack_mapper import SLACK_MAPPERS

_ALL: dict[str, CanonMapper] = {}
for group in (SLACK_MAPPERS, GITHUB_MAPPERS, LINEAR_MAPPERS, NOTION_MAPPERS):
    for m in group:
        _ALL[m.resource_type] = m


def mapper_for_resource_type(resource_type: str) -> CanonMapper | None:
    return _ALL.get(resource_type)


def all_mappers() -> list[CanonMapper]:
    return list(_ALL.values())
