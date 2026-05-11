"""Deterministic canonical → org-entity kind mapping (Phase 04 continuity substrate).

Normative: ``phase-04-org-entity-and-handle-doctrine.md`` — closed org kinds; no semantic inference.
Uses explicit (``connector``, ``canonical_object_kind``) tables plus conservative fallbacks.
"""

from __future__ import annotations

import re
from typing import Final

from vector.domains.cortex.identity.org_entities import OrgEntityKind

# Optional (connector, canonical_kind) overrides — kept minimal so bot/service heuristics win on ``person``.
_CONNECTOR_KIND_OVERRIDES: Final[dict[tuple[str, str], str]] = {}

# Canonical object kind (Phase 03 ``CanonicalObjectKind`` string) → org entity kind.
_CANONICAL_KIND_MAP: Final[dict[str, str]] = {
    "person": OrgEntityKind.HUMAN_ACTOR.value,
    "team": OrgEntityKind.TEAM.value,
    "workspace": OrgEntityKind.WORKSPACE.value,
    "account_installation": OrgEntityKind.SERVICE_ACCOUNT.value,
    "repository": OrgEntityKind.REPOSITORY_ASSET.value,
    "pull_request": OrgEntityKind.REPOSITORY_ASSET.value,
    "issue": OrgEntityKind.REPOSITORY_ASSET.value,
    "workflow_run": OrgEntityKind.REPOSITORY_ASSET.value,
    "deployment": OrgEntityKind.REPOSITORY_ASSET.value,
    "project": OrgEntityKind.INITIATIVE.value,
    "initiative": OrgEntityKind.INITIATIVE.value,
    "cycle": OrgEntityKind.INITIATIVE.value,
    "message": OrgEntityKind.COORDINATION_THREAD.value,
    "thread": OrgEntityKind.COORDINATION_THREAD.value,
    "conversation": OrgEntityKind.COORDINATION_THREAD.value,
    "channel": OrgEntityKind.COORDINATION_THREAD.value,
    "meeting": OrgEntityKind.COORDINATION_THREAD.value,
    "transcript": OrgEntityKind.COORDINATION_THREAD.value,
    "transcript_segment": OrgEntityKind.COORDINATION_THREAD.value,
    "document": OrgEntityKind.COORDINATION_THREAD.value,
    "page": OrgEntityKind.COORDINATION_THREAD.value,
    "database_row": OrgEntityKind.INITIATIVE.value,
    "canonical_event": OrgEntityKind.COORDINATION_THREAD.value,
    "execution_check": OrgEntityKind.COORDINATION_THREAD.value,
    "recording": OrgEntityKind.COORDINATION_THREAD.value,
    "relationship_edge": OrgEntityKind.COORDINATION_THREAD.value,
    "canonical_reference": OrgEntityKind.COORDINATION_THREAD.value,
    "state_snapshot": OrgEntityKind.UNKNOWN_PLACEHOLDER.value,
    "timeline_mutation": OrgEntityKind.COORDINATION_THREAD.value,
}

_BOT_LOGIN: Final[re.Pattern[str]] = re.compile(r"(bot\]|\[bot|dependabot|renovate|nexora-ci)", re.I)


def resolve_org_entity_kind_for_anchor(
    *,
    connector: str,
    canonical_object_kind: str,
    resource_type: str | None = None,
    provider_login: str | None = None,
) -> tuple[str, str]:
    """Return ``(entity_kind, mapping_rule_id)``.

    ``mapping_rule_id`` is a stable audit token (not a DB FK).
    """
    c = (connector or "").strip().lower()
    k = (canonical_object_kind or "").strip().lower()
    rt = (resource_type or "").strip().lower()

    if k == "person" and provider_login and _BOT_LOGIN.search(provider_login):
        return OrgEntityKind.SERVICE_ACCOUNT.value, "registry:person_bot_login_heuristic"

    if "bot" in rt and k == "person":
        return OrgEntityKind.SERVICE_ACCOUNT.value, "registry:resource_type_bot_suffix"

    ov = _CONNECTOR_KIND_OVERRIDES.get((c, k))
    if ov is not None:
        return ov, f"registry:connector_kind:{c}:{k}"

    mapped = _CANONICAL_KIND_MAP.get(k)
    if mapped is not None:
        return mapped, f"registry:canonical_kind:{k}"

    return OrgEntityKind.UNKNOWN_PLACEHOLDER.value, "registry:fallback:unknown_placeholder"


def public_mapping_registry_snapshot() -> dict[str, Any]:
    """Operator-visible snapshot of the in-code registry (deterministic, versionable)."""
    return {
        "entity_kind_mapping_schema_version": 1,
        "connector_kind_overrides": [f"{a}:{b}->{v}" for (a, b), v in sorted(_CONNECTOR_KIND_OVERRIDES.items())],
        "canonical_kind_map_keys": sorted(_CANONICAL_KIND_MAP.keys()),
    }
