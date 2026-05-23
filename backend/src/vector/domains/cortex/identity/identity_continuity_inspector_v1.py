"""Identity continuity inspector — entity search + lineage (Phase G2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.identity_primitive_projection import (
    IdentityPrimitiveProjection,
    _material,
    _norm_email,
    org_entity_id_for_identity_primitive,
)
from vector.domains.cortex.identity.link_explorer import list_org_link_explorer_rows
from vector.domains.cortex.identity.org_ambiguity import list_org_ambiguity_records
from vector.domains.cortex.identity.org_entities import get_org_entity, org_entity_public_dict
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    count_unpromoted_link_candidates_v1,
)
from vector.domains.cortex.substrate_pipeline.semantic_readiness_v1 import (
    _query_identity_continuity_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate

IDENTITY_CONTINUITY_INSPECTOR_SCHEMA_VERSION = 1


def _projection_for_slack_user_id(slack_user_id: str) -> IdentityPrimitiveProjection:
    su = slack_user_id.strip()
    return IdentityPrimitiveProjection(
        projection_kind="slack_user",
        extraction_role="search",
        identity_material=_material(
            projection_kind="slack_user",
            connector="slack",
            extra={"slack_user_id": su},
        ),
    )


def _projection_for_github_login(github_login: str) -> IdentityPrimitiveProjection:
    gl = github_login.strip().lower()
    return IdentityPrimitiveProjection(
        projection_kind="github_user",
        extraction_role="search",
        identity_material=_material(
            projection_kind="github_user",
            connector="github",
            extra={"github_login": gl},
        ),
    )


def _projection_for_notion_user_id(notion_user_id: str) -> IdentityPrimitiveProjection:
    nid = notion_user_id.strip()
    return IdentityPrimitiveProjection(
        projection_kind="notion_user",
        extraction_role="search",
        identity_material=_material(
            projection_kind="notion_user",
            connector="notion",
            extra={"notion_user_id": nid, "evidence_canonical_entity_id": "search"},
        ),
    )


def _projection_for_email(email: str) -> IdentityPrimitiveProjection:
    em = _norm_email(email) or email.strip().lower()
    domain = em.split("@", 1)[1] if "@" in em else ""
    return IdentityPrimitiveProjection(
        projection_kind="email_identity",
        extraction_role="search",
        identity_material=_material(
            projection_kind="email_identity",
            connector="search",
            extra={"email_norm": em, "email_domain": domain, "evidence_canonical_entity_id": "search"},
        ),
    )


def _parse_entity_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value.strip())
    except ValueError:
        return None


def _candidate_skip_reason_v1(session: Session, *, tenant_id: uuid.UUID, candidate: CortexOrgLinkCandidate) -> str:
    promoted = session.scalar(
        select(
            exists(
                select(1).where(
                    CortexOrgLink.tenant_id == tenant_id,
                    CortexOrgLink.promoted_from_candidate_id == candidate.id,
                    CortexOrgLink.revoked_at.is_(None),
                )
            )
        )
    )
    if promoted:
        return "already_promoted"
    active_pair = session.scalar(
        select(
            exists(
                select(1).where(
                    CortexOrgLink.tenant_id == tenant_id,
                    CortexOrgLink.source_entity_id == candidate.source_entity_id,
                    CortexOrgLink.target_entity_id == candidate.target_entity_id,
                    CortexOrgLink.link_type == candidate.link_type,
                    CortexOrgLink.link_authority == "authoritative",
                    CortexOrgLink.revoked_at.is_(None),
                )
            )
        )
    )
    if active_pair:
        return "active_authoritative_pair_exists"
    return "promotable"


def _list_entity_candidates_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
    limit: int = 64,
) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 200))
    rows = list(
        session.scalars(
            select(CortexOrgLinkCandidate)
            .where(
                CortexOrgLinkCandidate.tenant_id == tenant_id,
                or_(
                    CortexOrgLinkCandidate.source_entity_id == entity_id,
                    CortexOrgLinkCandidate.target_entity_id == entity_id,
                ),
            )
            .order_by(CortexOrgLinkCandidate.created_at.desc())
            .limit(lim)
        ).all()
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        skip = _candidate_skip_reason_v1(session, tenant_id=tenant_id, candidate=row)
        out.append(
            {
                "candidate_id": str(row.id),
                "link_type": row.link_type,
                "source_entity_id": str(row.source_entity_id),
                "target_entity_id": str(row.target_entity_id),
                "rule_id": row.rule_id,
                "batch_id": str(row.batch_id),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "evidence_raw_record_ids": list(row.evidence_raw_record_ids or []),
                "skip_reason_code": skip,
                "status": "promotable" if skip == "promotable" else "skipped",
            }
        )
    return out


def _list_entity_promotion_lineage_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
    limit: int = 64,
) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 200))
    links = list(
        session.scalars(
            select(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.promoted_from_candidate_id.is_not(None),
                or_(
                    CortexOrgLink.source_entity_id == entity_id,
                    CortexOrgLink.target_entity_id == entity_id,
                ),
            )
            .order_by(CortexOrgLink.created_at.desc())
            .limit(lim)
        ).all()
    )
    out: list[dict[str, Any]] = []
    for link in links:
        cand = session.get(CortexOrgLinkCandidate, link.promoted_from_candidate_id) if link.promoted_from_candidate_id else None
        out.append(
            {
                "link_id": str(link.id),
                "link_type": link.link_type,
                "source_entity_id": str(link.source_entity_id),
                "target_entity_id": str(link.target_entity_id),
                "rule_id": link.rule_id,
                "promotion_policy_id": str(link.promotion_policy_id) if link.promotion_policy_id else None,
                "promoted_from_candidate_id": str(link.promoted_from_candidate_id)
                if link.promoted_from_candidate_id
                else None,
                "created_at": link.created_at.isoformat() if link.created_at else None,
                "candidate_rule_id": cand.rule_id if cand else None,
                "candidate_batch_id": str(cand.batch_id) if cand else None,
                "evidence_raw_record_ids": list(link.evidence_raw_record_ids or []),
            }
        )
    return out


def _resolved_identities_from_entity(entity: dict[str, Any]) -> list[dict[str, Any]]:
    meta = dict(entity.get("metadata_json") or {})
    pk = str(meta.get("projection_kind") or "")
    out: list[dict[str, Any]] = []
    if pk:
        item: dict[str, Any] = {
            "source_system": meta.get("source_anchor_connector") or meta.get("source_connector") or "unknown",
            "projection_kind": pk,
            "promotion_rule": meta.get("entity_kind_mapping_rule_id"),
            "handle_id": entity.get("id"),
            "created_at": entity.get("created_at"),
            "last_seen_at": entity.get("updated_at"),
            "confidence": "authoritative_entity",
        }
        for key in (
            "slack_user_id",
            "github_login",
            "notion_user_id",
            "email_norm",
            "linear_user_id",
            "canonical_entity_id",
        ):
            if key in meta:
                item[key] = meta[key]
        out.append(item)
    return out


def resolve_continuity_search_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    slack_user_id: str | None = None,
    github_login: str | None = None,
    notion_user_id: str | None = None,
    email: str | None = None,
    entity_id: str | None = None,
    handle_id: str | None = None,
    canonical_entity_id: str | None = None,
) -> dict[str, Any]:
    """Resolve external keys or UUIDs to org entity ids (deterministic primitive projection)."""
    del canonical_entity_id  # reserved for future anchor back-link
    matches: list[dict[str, Any]] = []
    entity_ids: set[uuid.UUID] = set()

    direct_id = entity_id or handle_id
    if direct_id:
        parsed = _parse_entity_uuid(direct_id)
        if parsed is not None:
            row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=parsed)
            if row is not None:
                entity_ids.add(parsed)
                matches.append({"search_key": "entity_id", "value": direct_id, "entity_id": str(parsed), "found": True})
            else:
                matches.append({"search_key": "entity_id", "value": direct_id, "found": False})

    projection_specs: list[tuple[str, str, IdentityPrimitiveProjection]] = []
    if slack_user_id:
        projection_specs.append(("slack_user_id", slack_user_id, _projection_for_slack_user_id(slack_user_id)))
    if github_login:
        projection_specs.append(("github_login", github_login, _projection_for_github_login(github_login)))
    if notion_user_id:
        projection_specs.append(("notion_user_id", notion_user_id, _projection_for_notion_user_id(notion_user_id)))
    if email:
        projection_specs.append(("email", email, _projection_for_email(email)))

    for key, value, projection in projection_specs:
        eid = org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=projection)
        row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=eid)
        found = row is not None
        if found:
            entity_ids.add(eid)
        matches.append(
            {
                "search_key": key,
                "value": value,
                "entity_id": str(eid),
                "projection_kind": projection.projection_kind,
                "found": found,
            }
        )

    entities = []
    for eid in sorted(entity_ids, key=str):
        row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=eid)
        if row is not None:
            entities.append(org_entity_public_dict(row))

    return {
        "surface_kind": "identity_continuity_search",
        "tenant_id": str(tenant_id),
        "matches": matches,
        "entity_ids": [str(x) for x in sorted(entity_ids, key=str)],
        "entities": entities,
    }


def build_identity_continuity_entity_inspector_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict[str, Any]:
    """Entity-scoped identity continuity card with candidates, lineage, and ambiguities."""
    row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=entity_id)
    if row is None:
        raise ValueError("entity_not_found")

    entity = org_entity_public_dict(row)
    auth_links = list_org_link_explorer_rows(
        session, tenant_id=tenant_id, handle_id=entity_id, authoritative_only=True, limit=64
    )
    candidate_links = list_org_link_explorer_rows(
        session, tenant_id=tenant_id, handle_id=entity_id, candidate_only=True, limit=64
    )
    candidates = _list_entity_candidates_v1(session, tenant_id=tenant_id, entity_id=entity_id)
    promotion_lineage = _list_entity_promotion_lineage_v1(session, tenant_id=tenant_id, entity_id=entity_id)

    ambiguities = []
    for r in list_org_ambiguity_records(session, tenant_id=tenant_id, limit=200):
        involved: set[uuid.UUID] = set()
        for x in r.involved_org_entity_ids or []:
            try:
                involved.add(uuid.UUID(str(x)))
            except ValueError:
                continue
        if entity_id not in involved:
            continue
        ambiguities.append(
            {
                "id": str(r.id),
                "ambiguity_class": r.ambiguity_class,
                "status": r.status,
                "involved_org_entity_ids": [str(x) for x in involved],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )

    promotable = [c for c in candidates if c["status"] == "promotable"]
    skipped = [c for c in candidates if c["status"] == "skipped"]

    return {
        "surface_kind": "identity_continuity_entity_inspector",
        "inspector_schema_version": IDENTITY_CONTINUITY_INSPECTOR_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "entity": entity,
        "continuity_status": {
            "lifecycle_state": entity.get("lifecycle_state"),
            "entity_kind": entity.get("entity_kind"),
            "created_at": entity.get("created_at"),
        },
        "resolved_identities": _resolved_identities_from_entity(entity),
        "authoritative_links": auth_links,
        "candidate_explorer_rows": candidate_links,
        "candidates": candidates,
        "promotable_candidates": promotable,
        "skipped_candidates": skipped,
        "promotion_lineage": promotion_lineage,
        "open_ambiguities": ambiguities,
        "evidence_summary": {
            "authoritative_link_count": len(auth_links),
            "candidate_count": len(candidates),
            "promotable_count": len(promotable),
            "skipped_count": len(skipped),
            "promotion_lineage_count": len(promotion_lineage),
            "open_ambiguity_count": len(ambiguities),
        },
    }


def build_identity_continuity_inspector_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant-level identity continuity inspector aggregate."""
    continuity = _query_identity_continuity_v1(session, tenant_id=tenant_id)
    return {
        "surface_kind": "identity_continuity_inspector",
        "inspector_schema_version": IDENTITY_CONTINUITY_INSPECTOR_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "identity_continuity": continuity,
        "unpromoted_candidates": count_unpromoted_link_candidates_v1(session, tenant_id=tenant_id),
    }
