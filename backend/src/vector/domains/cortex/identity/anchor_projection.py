"""Shared anchor → org-entity projection helpers (Phase 04 P04-20 substrate).

Keeps fingerprint material + deterministic org ids aligned across backfill and candidate engines.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from vector.domains.cortex.identity.entity_kind_mapping import resolve_org_entity_kind_for_anchor
from vector.domains.cortex.identity.identity_primitive_projection import (
    extract_identity_primitives,
    org_entity_id_for_identity_primitive,
    raw_has_declared_continuity_fixture,
)
from vector.domains.cortex.identity.org_entities import deterministic_org_entity_id, identity_key_fingerprint
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

ANCHOR_BACKFILL_LANE: Final[str] = "canonical_identity_anchor_v1"

# Canonical anchors that **are** org-identity objects (legacy lane without connector primitives).
_LEGACY_ORG_HANDLE_IDENTITY_NATIVE_KINDS: Final[frozenset[str]] = frozenset(
    {"person", "team", "account_installation"},
)


def legacy_org_handle_lane_eligible(
    *,
    canonical_object_kind: str | None,
    raw: RawIngestionRecord | None,
) -> bool:
    """Whether a zero-primitive anchor may mint a legacy-lane org handle.

    Work-object anchors (``message``, ``repository``, …) must not explode into repository_asset /
    coordination_thread handles; they only produce org rows via identity primitives unless the raw
    row carries an explicit ``continuity_fixture`` block (fixtures / operator harness).
    """
    k = (canonical_object_kind or "").strip().lower()
    if k in _LEGACY_ORG_HANDLE_IDENTITY_NATIVE_KINDS:
        return True
    return raw_has_declared_continuity_fixture(raw)


def identity_material_for_anchor_backfill(anchor: CortexCanonicalIdentityAnchor) -> dict[str, Any]:
    """Stable identity material for org entity fingerprint (lane + anchor identity)."""
    return {
        "lane": ANCHOR_BACKFILL_LANE,
        "canonical_entity_id": str(anchor.canonical_entity_id),
        "provider_identity_hash": str(anchor.provider_identity_hash or "").strip(),
    }


def _payload_dict(raw: RawIngestionRecord | None) -> dict[str, Any]:
    if raw is None:
        return {}
    p = raw.payload_body
    return dict(p) if isinstance(p, dict) else {}


def provider_login_for_kind_resolution(anchor: CortexCanonicalIdentityAnchor, raw: RawIngestionRecord | None) -> str | None:
    """Deterministic login hint for service-account vs human (no semantic inference)."""
    prof = dict(anchor.provider_identity_json or {})
    payload = _payload_dict(raw)
    for path in (
        ("sender", "login"),
        ("user", "login"),
        ("author", "login"),
    ):
        cur: Any = payload
        ok = True
        for p in path:
            if not isinstance(cur, dict):
                ok = False
                break
            cur = cur.get(p)
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip().lower()
    v = prof.get("login") or prof.get("github_login") or prof.get("user_login")
    if isinstance(v, str) and v.strip():
        return v.strip().lower()
    return None


def org_entity_id_for_anchor_row(
    *,
    tenant_id: uuid.UUID,
    anchor: CortexCanonicalIdentityAnchor,
    raw: RawIngestionRecord | None,
) -> uuid.UUID:
    """Representative org handle id for one anchor (first primitive; must align with primitive backfill).

    Continuity candidate generation buckets **per primitive**; callers that still need a single id
    (e.g. legacy drill-down) use the lexicographically first extracted primitive for this anchor.
    """
    projs = extract_identity_primitives(anchor=anchor, raw=raw)
    if projs:
        return org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=projs[0])
    material = identity_material_for_anchor_backfill(anchor)
    login = provider_login_for_kind_resolution(anchor, raw)
    kind, _rule = resolve_org_entity_kind_for_anchor(
        connector=anchor.connector,
        canonical_object_kind=anchor.canonical_object_kind,
        resource_type=raw.resource_type if raw else None,
        provider_login=login,
    )
    fp = identity_key_fingerprint(material)
    return deterministic_org_entity_id(tenant_id=tenant_id, entity_kind=kind, fingerprint=fp)
