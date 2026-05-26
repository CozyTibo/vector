"""Human-friendly people directory and profile surfaces for operator admin."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.continuity_evidence_inspector import (
    build_entity_continuity_evidence_inspection_v1,
)
from vector.domains.cortex.identity.identity_continuity_inspector_v1 import (
    _list_linked_entity_ids_v1,
    _list_linked_handles_v1,
    _resolved_identity_from_entity,
)
from vector.domains.cortex.identity.identity_primitive_projection import (
    _display_name,
    _email_for_rule,
    _notion_user_refs_deterministic,
    github_login_strings_for_continuity,
)
from vector.domains.cortex.identity.link_explorer import list_org_link_explorer_rows
from vector.domains.cortex.identity.org_entities import OrgEntityKind, get_org_entity, org_entity_public_dict
from vector.domains.cortex.pipeline.operator_admin_inspect_chains import search_operator_retrieval_entries_v1
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

PEOPLE_DIRECTORY_SCHEMA_VERSION: Final[int] = 1
_MAX_DIRECTORY_SCAN: Final[int] = 500
_MAX_RAW_LABEL_FETCH: Final[int] = 150
_MAX_SLACK_ROSTER_LOOKUP: Final[int] = 500
_MAX_NOTION_USER_INDEX_SCAN: Final[int] = 2_000

_WORK_KINDS: Final[frozenset[str]] = frozenset(
    {
        "message",
        "pull_request",
        "issue",
        "document",
        "page",
        "thread",
        "workflow_run",
        "deployment",
        "execution_check",
        "meeting",
        "transcript",
        "database_row",
        "canonical_event",
    }
)

_SYSTEM_LABELS: Final[dict[str, str]] = {
    "slack_user": "Slack",
    "github_user": "GitHub",
    "notion_user": "Notion",
    "email_identity": "Email",
    "linear_user": "Linear",
}


class _UnionFind:
    def __init__(self) -> None:
        self._parent: dict[uuid.UUID, uuid.UUID] = {}

    def find(self, node: uuid.UUID) -> uuid.UUID:
        if node not in self._parent:
            self._parent[node] = node
        while self._parent[node] != node:
            self._parent[node] = self._parent[self._parent[node]]
            node = self._parent[node]
        return node

    def union(self, a: uuid.UUID, b: uuid.UUID) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra


def _identity_signal_keys(
    entity: dict[str, Any],
    labels: dict[str, str | None] | None,
) -> list[tuple[str, str]]:
    """Stable cross-handle keys used to collapse one human across evidence-scoped org rows."""
    keys: list[tuple[str, str]] = []
    meta = _meta(entity)
    email = (labels or {}).get("email") or meta.get("email_norm") or meta.get("email")
    if isinstance(email, str) and "@" in email:
        keys.append(("email", email.strip().lower()))
    for field in ("github_login", "slack_user_id", "notion_user_id", "linear_user_id"):
        val = meta.get(field)
        if isinstance(val, str) and val.strip():
            normalized = val.strip().lower() if field == "github_login" else val.strip()
            keys.append((field, normalized))
    return keys


def _union_clusters_by_identity_signals(
    uf: _UnionFind,
    *,
    entity_ids: set[uuid.UUID],
    entities_by_id: dict[uuid.UUID, dict[str, Any]],
    labels_by_entity_id: dict[uuid.UUID, dict[str, str | None]],
) -> None:
    by_key: dict[tuple[str, str], list[uuid.UUID]] = {}
    for eid in entity_ids:
        entity = entities_by_id.get(eid)
        if entity is None:
            continue
        for key in _identity_signal_keys(entity, labels_by_entity_id.get(eid)):
            by_key.setdefault(key, []).append(eid)
    for members in by_key.values():
        if len(members) < 2:
            continue
        head = members[0]
        for eid in members[1:]:
            uf.union(head, eid)


def _query_entity_ids_by_metadata_field_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    field: str,
    value: str,
    limit: int = 500,
) -> set[uuid.UUID]:
    col = CortexOrgEntity.metadata_json[field].astext
    rows = session.scalars(
        select(CortexOrgEntity.id)
        .where(
            CortexOrgEntity.tenant_id == tenant_id,
            CortexOrgEntity.entity_kind == OrgEntityKind.HUMAN_ACTOR.value,
            CortexOrgEntity.tombstoned_at.is_(None),
            col == value,
        )
        .limit(max(1, min(limit, 1000)))
    ).all()
    return set(rows)


def _resolve_people_cluster_entity_ids_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
    signal_lookup_limit: int = 500,
) -> set[uuid.UUID]:
    """All org handles that represent the same reconstructed person as ``entity_id``."""
    cluster: set[uuid.UUID] = set(_list_linked_entity_ids_v1(session, tenant_id=tenant_id, entity_id=entity_id, limit=64))
    cluster.add(entity_id)
    row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=entity_id)
    if row is None:
        return cluster
    entity = org_entity_public_dict(row)
    labels = _batch_entity_identity_labels_v1(
        session,
        tenant_id=tenant_id,
        entities_by_id={entity_id: entity},
    )
    for signal, value in _identity_signal_keys(entity, labels.get(entity_id)):
        if signal == "email":
            cluster |= _query_entity_ids_by_metadata_field_v1(
                session,
                tenant_id=tenant_id,
                field="email_norm",
                value=value,
                limit=signal_lookup_limit,
            )
        elif signal in ("github_login", "slack_user_id", "notion_user_id", "linear_user_id"):
            cluster |= _query_entity_ids_by_metadata_field_v1(
                session,
                tenant_id=tenant_id,
                field=signal,
                value=value,
                limit=signal_lookup_limit,
            )
    return cluster


def _meta(entity: dict[str, Any]) -> dict[str, Any]:
    return dict(entity.get("metadata_json") or {})


def _extract_slack_member_labels(member: dict[str, Any]) -> dict[str, str | None]:
    prof = member.get("profile") if isinstance(member.get("profile"), dict) else {}
    disp = prof.get("display_name_normalized") or prof.get("display_name")
    real = prof.get("real_name")
    legacy = member.get("name")
    label = disp or real or legacy
    display_name: str | None = None
    if isinstance(label, str) and label.strip():
        display_name = label.strip()
    email: str | None = None
    email_raw = prof.get("email")
    if isinstance(email_raw, str) and "@" in email_raw:
        email = email_raw.strip().lower()
    return {"display_name": display_name, "email": email}


def _tool_native_display_name(meta: dict[str, Any]) -> str | None:
    """Human-readable label from org handle metadata when richer labels are unavailable."""
    github = meta.get("github_login")
    if isinstance(github, str) and github.strip():
        return github.strip()
    slack = meta.get("slack_user_id")
    if isinstance(slack, str) and slack.strip():
        return f"Slack {slack.strip()}"
    notion = meta.get("notion_user_id")
    if isinstance(notion, str) and notion.strip():
        short = notion.strip().replace("-", "")[:8]
        return f"Notion user {short}"
    linear = meta.get("linear_user_id")
    if isinstance(linear, str) and linear.strip():
        short = linear.strip().replace("-", "")[:8]
        return f"Linear user {short}"
    pk = str(meta.get("projection_kind") or "")
    label = _SYSTEM_LABELS.get(pk)
    if label:
        return f"{label} handle"
    return None


def _format_display_name(raw: str, *, from_norm: bool = False) -> str:
    text = raw.strip()
    if not text:
        return text
    if from_norm or text == text.lower():
        return text.title()
    return text


def _extract_entity_labels_v1(
    *,
    meta: dict[str, Any],
    raw: RawIngestionRecord | None,
    prof: dict[str, Any],
) -> dict[str, str | None]:
    display_name: str | None = None
    email: str | None = None

    for key in ("display_name", "display_name_norm", "real_name", "name"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            display_name = _format_display_name(val, from_norm=key == "display_name_norm")
            break

    github = meta.get("github_login")
    if isinstance(github, str) and github.strip():
        display_name = display_name or github.strip()

    val = meta.get("email_norm") or meta.get("email")
    if isinstance(val, str) and "@" in val:
        email = val.strip().lower()

    if raw is not None and (display_name is None or email is None):
        payload = _payload_dict(raw)
        if display_name is None:
            dn = _display_name(payload)
            if isinstance(dn, str) and dn.strip():
                display_name = _format_display_name(dn, from_norm=True)
            if display_name is None:
                logins = github_login_strings_for_continuity(payload, prof)
                if logins:
                    display_name = logins[0]
            notion_user_id = meta.get("notion_user_id")
            if display_name is None and isinstance(notion_user_id, str) and notion_user_id.strip():
                for nu in _notion_user_refs_deterministic(payload):
                    if nu.get("notion_user_id") == notion_user_id.strip():
                        nu_name = nu.get("display_name")
                        if isinstance(nu_name, str) and nu_name.strip():
                            display_name = nu_name.strip()
                        if email is None:
                            nu_email = nu.get("email_norm")
                            if isinstance(nu_email, str) and "@" in nu_email:
                                email = nu_email.strip().lower()
                        break
        if email is None:
            em, _ = _email_for_rule(payload, prof)
            if em:
                email = em

    if display_name is None:
        display_name = _tool_native_display_name(meta)
    if display_name is None and email and "@" in email:
        display_name = email.split("@", 1)[0].replace(".", " ").title()

    return {"display_name": display_name, "email": email}


def _entity_needs_raw_enrichment(labels: dict[str, str | None]) -> bool:
    return not labels.get("display_name") or not labels.get("email")


def _metadata_labels_for_entities(
    entities_by_id: dict[uuid.UUID, dict[str, Any]],
) -> dict[uuid.UUID, dict[str, str | None]]:
    return {
        eid: _extract_entity_labels_v1(meta=_meta(entity), raw=None, prof={})
        for eid, entity in entities_by_id.items()
    }


def _enrich_directory_labels_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entities_by_id: dict[uuid.UUID, dict[str, Any]],
    seed_labels: dict[uuid.UUID, dict[str, str | None]],
) -> dict[uuid.UUID, dict[str, str | None]]:
    """Resolve display names and emails from raw anchors before clustering (chunked)."""
    labels = dict(seed_labels)
    max_rounds = max(1, (len(entities_by_id) // _MAX_RAW_LABEL_FETCH) + 1)
    for _ in range(max_rounds):
        needs_enrichment = [
            eid
            for eid in entities_by_id
            if _entity_needs_raw_enrichment(labels.get(eid) or {})
        ]
        if not needs_enrichment:
            break
        chunk_entities = {
            eid: entities_by_id[eid]
            for eid in needs_enrichment[:_MAX_RAW_LABEL_FETCH]
            if eid in entities_by_id
        }
        if not chunk_entities:
            break
        before = {eid: dict(labels.get(eid) or {}) for eid in chunk_entities}
        labels = {
            **labels,
            **_batch_entity_identity_labels_v1(
                session,
                tenant_id=tenant_id,
                entities_by_id=chunk_entities,
                seed_labels=labels,
            ),
        }
        progressed = any(
            (labels.get(eid) or {}).get("email") != before.get(eid, {}).get("email")
            or (labels.get(eid) or {}).get("display_name") != before.get(eid, {}).get("display_name")
            for eid in chunk_entities
        )
        if not progressed:
            break
    return _merge_connector_roster_labels_v1(
        session,
        tenant_id=tenant_id,
        entities_by_id=entities_by_id,
        labels=labels,
    )


def _merge_connector_roster_labels_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entities_by_id: dict[uuid.UUID, dict[str, Any]],
    labels: dict[uuid.UUID, dict[str, str | None]],
) -> dict[uuid.UUID, dict[str, str | None]]:
    """Upgrade labels from connector-native rosters (Slack users.list, Notion page refs)."""
    out = dict(labels)
    slack_ids: set[str] = set()
    notion_ids: set[str] = set()
    for _eid, entity in entities_by_id.items():
        meta = _meta(entity)
        sid = meta.get("slack_user_id")
        if isinstance(sid, str) and sid.strip():
            slack_ids.add(sid.strip())
        nid = meta.get("notion_user_id")
        if isinstance(nid, str) and nid.strip():
            notion_ids.add(nid.strip())

    slack_by_id: dict[str, dict[str, str | None]] = {}
    if slack_ids:
        slack_list = sorted(slack_ids)[:_MAX_SLACK_ROSTER_LOOKUP]
        for row in session.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.resource_type == "slack.user",
                RawIngestionRecord.external_id.in_(slack_list),
            )
        ).all():
            member = (row.payload_body or {}).get("member") if isinstance(row.payload_body, dict) else None
            if isinstance(member, dict):
                slack_by_id[str(row.external_id)] = _extract_slack_member_labels(member)

    notion_by_id: dict[str, dict[str, str | None]] = {}
    if notion_ids:
        for row in session.scalars(
            select(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.resource_type.in_(
                    ("notion.page", "notion.block", "notion.database_row", "notion.database")
                ),
            )
            .order_by(RawIngestionRecord.fetched_at.desc())
            .limit(_MAX_NOTION_USER_INDEX_SCAN)
        ).all():
            payload = row.payload_body if isinstance(row.payload_body, dict) else {}
            for nu in _notion_user_refs_deterministic(payload):
                uid = str(nu.get("notion_user_id") or "")
                if uid not in notion_ids or uid in notion_by_id:
                    continue
                dn = nu.get("display_name")
                em = nu.get("email_norm")
                notion_by_id[uid] = {
                    "display_name": dn if isinstance(dn, str) else None,
                    "email": em if isinstance(em, str) else None,
                }
            if len(notion_by_id) >= len(notion_ids):
                break

    for eid, entity in entities_by_id.items():
        meta = _meta(entity)
        cur = dict(out.get(eid) or _extract_entity_labels_v1(meta=meta, raw=None, prof={}))
        sid = meta.get("slack_user_id")
        if isinstance(sid, str) and sid.strip() in slack_by_id:
            roster = slack_by_id[sid.strip()]
            if roster.get("display_name"):
                cur["display_name"] = roster["display_name"]
            if roster.get("email"):
                cur["email"] = roster["email"]
        nid = meta.get("notion_user_id")
        if isinstance(nid, str) and nid.strip() in notion_by_id:
            roster = notion_by_id[nid.strip()]
            if roster.get("display_name"):
                cur["display_name"] = roster["display_name"]
            if roster.get("email"):
                cur["email"] = roster["email"]
        if not cur.get("display_name"):
            cur["display_name"] = _tool_native_display_name(meta)
        out[eid] = cur
    return out


def _batch_entity_identity_labels_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entities_by_id: dict[uuid.UUID, dict[str, Any]],
    seed_labels: dict[uuid.UUID, dict[str, str | None]] | None = None,
) -> dict[uuid.UUID, dict[str, str | None]]:
    if not entities_by_id:
        return {}

    seeded = dict(seed_labels or {})
    out: dict[uuid.UUID, dict[str, str | None]] = dict(seeded)

    raw_ids: set[int] = set()
    anchor_pairs: set[tuple[int, str]] = set()
    for eid, entity in entities_by_id.items():
        labels = seeded.get(eid) or _extract_entity_labels_v1(meta=_meta(entity), raw=None, prof={})
        out[eid] = labels
        if not _entity_needs_raw_enrichment(labels):
            continue
        meta = _meta(entity)
        raw_id = meta.get("source_anchor_raw_record_id")
        if raw_id is None:
            continue
        try:
            rid = int(raw_id)
        except (TypeError, ValueError):
            continue
        raw_ids.add(rid)
        canon = str(meta.get("canonical_entity_id") or "")
        if canon:
            anchor_pairs.add((rid, canon))

    if not raw_ids:
        return out

    raw_ids_list = sorted(raw_ids)[:_MAX_RAW_LABEL_FETCH]
    raw_by_id: dict[int, RawIngestionRecord] = {}
    for row in session.scalars(
        select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids_list))
    ).all():
        raw_by_id[int(row.id)] = row

    prof_by_anchor: dict[tuple[int, str], dict[str, Any]] = {}
    if anchor_pairs:
        for anchor in session.scalars(
            select(CortexCanonicalIdentityAnchor).where(
                CortexCanonicalIdentityAnchor.tenant_id == tenant_id,
                CortexCanonicalIdentityAnchor.raw_record_id.in_(raw_ids_list),
            )
        ).all():
            key = (int(anchor.raw_record_id), str(anchor.canonical_entity_id))
            if key in anchor_pairs:
                prof_by_anchor[key] = dict(anchor.provider_identity_json or {})

    for eid, entity in entities_by_id.items():
        if not _entity_needs_raw_enrichment(out.get(eid) or {}):
            continue
        meta = _meta(entity)
        raw: RawIngestionRecord | None = None
        prof: dict[str, Any] = {}
        raw_id = meta.get("source_anchor_raw_record_id")
        if raw_id is not None:
            try:
                rid = int(raw_id)
                raw = raw_by_id.get(rid)
                canon = str(meta.get("canonical_entity_id") or "")
                prof = prof_by_anchor.get((rid, canon), {})
            except (TypeError, ValueError):
                pass
        out[eid] = _extract_entity_labels_v1(meta=meta, raw=raw, prof=prof)
    return out


def _pick_display_name(
    handles: list[dict[str, Any]],
    entity: dict[str, Any],
    *,
    labels: dict[str, str | None] | None = None,
) -> str | None:
    if labels and labels.get("display_name"):
        return labels["display_name"]
    for handle in handles:
        for key in ("display_name", "display_name_norm"):
            val = handle.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    meta = _meta(entity)
    for key in ("display_name", "display_name_norm", "real_name", "name"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    github = meta.get("github_login")
    if isinstance(github, str) and github.strip():
        return github.strip()
    slack = meta.get("slack_user_id")
    if isinstance(slack, str) and slack.strip():
        return f"Slack {slack.strip()}"
    email = meta.get("email_norm") or meta.get("email")
    if isinstance(email, str) and "@" in email:
        return email.split("@", 1)[0].replace(".", " ").title()
    return None


def _pick_email(
    handles: list[dict[str, Any]],
    entity: dict[str, Any],
    *,
    labels: dict[str, str | None] | None = None,
) -> str | None:
    if labels and labels.get("email"):
        return labels["email"]
    for handle in handles:
        val = handle.get("email_norm") or handle.get("email")
        if isinstance(val, str) and "@" in val:
            return val.strip().lower()
    meta = _meta(entity)
    val = meta.get("email_norm") or meta.get("email")
    if isinstance(val, str) and "@" in val:
        return val.strip().lower()
    return None


def _systems_from_handles(handles: list[dict[str, Any]], entity: dict[str, Any]) -> list[str]:
    systems: set[str] = set()
    for handle in handles:
        pk = str(handle.get("projection_kind") or "")
        label = _SYSTEM_LABELS.get(pk)
        if label:
            systems.add(label)
        src = str(handle.get("source_system") or "")
        if src and src != "unknown":
            systems.add(src.replace("_", " ").title())
    meta = _meta(entity)
    pk = str(meta.get("projection_kind") or "")
    label = _SYSTEM_LABELS.get(pk)
    if label:
        systems.add(label)
    return sorted(systems)


def _score_entity(
    entity: dict[str, Any],
    handles: list[dict[str, Any]],
    *,
    labels: dict[str, str | None] | None = None,
) -> int:
    score = 0
    if _pick_display_name(handles, entity, labels=labels):
        score += 10
    if _pick_email(handles, entity, labels=labels):
        score += 8
    score += len(handles)
    if entity.get("entity_kind") == OrgEntityKind.HUMAN_ACTOR.value:
        score += 2
    return score


def _list_human_actor_entities(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[CortexOrgEntity], int]:
    base = (
        CortexOrgEntity.tenant_id == tenant_id,
        CortexOrgEntity.entity_kind == OrgEntityKind.HUMAN_ACTOR.value,
        CortexOrgEntity.tombstoned_at.is_(None),
    )
    total = int(session.scalar(select(func.count()).select_from(CortexOrgEntity).where(*base)) or 0)
    rows = list(
        session.scalars(
            select(CortexOrgEntity)
            .where(*base)
            .order_by(CortexOrgEntity.updated_at.desc(), CortexOrgEntity.id.asc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
        ).all()
    )
    return rows, total


def _cluster_human_actors(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_ids: set[uuid.UUID],
    entities_by_id: dict[uuid.UUID, dict[str, Any]] | None = None,
    labels_by_entity_id: dict[uuid.UUID, dict[str, str | None]] | None = None,
) -> dict[uuid.UUID, set[uuid.UUID]]:
    if not entity_ids:
        return {}
    uf = _UnionFind()
    for eid in entity_ids:
        uf.find(eid)
    links = session.scalars(
        select(CortexOrgLink).where(
            CortexOrgLink.tenant_id == tenant_id,
            CortexOrgLink.link_authority == "authoritative",
            CortexOrgLink.revoked_at.is_(None),
            or_(
                CortexOrgLink.source_entity_id.in_(entity_ids),
                CortexOrgLink.target_entity_id.in_(entity_ids),
            ),
        )
    ).all()
    for link in links:
        src, tgt = link.source_entity_id, link.target_entity_id
        if src in entity_ids and tgt in entity_ids:
            uf.union(src, tgt)
    if entities_by_id and labels_by_entity_id:
        _union_clusters_by_identity_signals(
            uf,
            entity_ids=entity_ids,
            entities_by_id=entities_by_id,
            labels_by_entity_id=labels_by_entity_id,
        )
    clusters: dict[uuid.UUID, set[uuid.UUID]] = {}
    for eid in entity_ids:
        root = uf.find(eid)
        clusters.setdefault(root, set()).add(eid)
    return clusters


def _systems_from_entities(entities: list[dict[str, Any]]) -> list[str]:
    systems: set[str] = set()
    for entity in entities:
        resolved = _resolved_identity_from_entity(entity)
        if resolved:
            systems.update(_systems_from_handles([resolved], entity))
    return sorted(systems)


def _person_row_from_cluster_light(
    cluster: set[uuid.UUID],
    entities_by_id: dict[uuid.UUID, dict[str, Any]],
    entity_ids_in_auth_graph: set[uuid.UUID],
    labels_by_entity_id: dict[uuid.UUID, dict[str, str | None]],
) -> dict[str, Any]:
    entities = [entities_by_id[eid] for eid in cluster if eid in entities_by_id]
    if not entities:
        primary_id = sorted(cluster, key=str)[0]
        return {
            "person_id": str(primary_id),
            "entity_ids": [str(x) for x in sorted(cluster, key=str)],
            "display_name": None,
            "email": None,
            "systems": [],
            "linked_account_count": len(cluster),
            "cluster_size": len(cluster),
            "connector_id_count": 0,
            "is_singleton_cluster": len(cluster) <= 1,
            "in_auth_graph": any(eid in entity_ids_in_auth_graph for eid in cluster),
            "last_seen_at": None,
            "title": None,
        }

    primary = max(
        entities,
        key=lambda ent: _score_entity(
            ent,
            [],
            labels=labels_by_entity_id.get(uuid.UUID(str(ent["id"]))),
        ),
    )
    primary_id = uuid.UUID(str(primary["id"]))
    primary_labels = labels_by_entity_id.get(primary_id) or {}
    display_name = _pick_display_name([], primary, labels=primary_labels)
    email = _pick_email([], primary, labels=primary_labels)
    if display_name is None or email is None:
        for ent in entities:
            if ent is primary:
                continue
            ent_labels = labels_by_entity_id.get(uuid.UUID(str(ent["id"]))) or {}
            if display_name is None:
                display_name = _pick_display_name([], ent, labels=ent_labels)
            if email is None:
                email = _pick_email([], ent, labels=ent_labels)

    systems = _systems_from_entities(entities)
    last_seen = None
    for ent in entities:
        ts = ent.get("updated_at")
        if ts and (last_seen is None or ts > last_seen):
            last_seen = ts

    meta = _meta(primary)
    title_raw = meta.get("title") or meta.get("role")
    title = title_raw.strip() if isinstance(title_raw, str) and title_raw.strip() else None

    return {
        "person_id": str(primary_id),
        "entity_ids": [str(x) for x in sorted(cluster, key=str)],
        "display_name": display_name,
        "email": email,
        "systems": systems,
        "linked_account_count": len(cluster),
        "cluster_size": len(cluster),
        "connector_id_count": _connector_id_count_for_cluster(
            cluster,
            entities_by_id=entities_by_id,
            labels_by_entity_id=labels_by_entity_id,
        ),
        "is_singleton_cluster": len(cluster) <= 1,
        "in_auth_graph": any(eid in entity_ids_in_auth_graph for eid in cluster),
        "last_seen_at": last_seen,
        "title": title,
    }


def _entity_ids_in_auth_graph(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_ids: set[uuid.UUID],
) -> set[uuid.UUID]:
    if not entity_ids:
        return set()
    linked: set[uuid.UUID] = set()
    rows = session.execute(
        select(CortexOrgLink.source_entity_id, CortexOrgLink.target_entity_id).where(
            CortexOrgLink.tenant_id == tenant_id,
            CortexOrgLink.link_authority == "authoritative",
            CortexOrgLink.revoked_at.is_(None),
            or_(
                CortexOrgLink.source_entity_id.in_(entity_ids),
                CortexOrgLink.target_entity_id.in_(entity_ids),
            ),
        )
    ).all()
    for src, tgt in rows:
        if src in entity_ids:
            linked.add(src)
        if tgt in entity_ids:
            linked.add(tgt)
    return linked


def _connector_id_count_for_cluster(
    cluster: set[uuid.UUID],
    *,
    entities_by_id: dict[uuid.UUID, dict[str, Any]],
    labels_by_entity_id: dict[uuid.UUID, dict[str, str | None]],
) -> int:
    """Distinct cross-tool identity signals (V9 spot-check: engineer should show ≥2)."""
    keys: set[tuple[str, str]] = set()
    for eid in cluster:
        entity = entities_by_id.get(eid)
        if entity is None:
            continue
        keys.update(_identity_signal_keys(entity, labels_by_entity_id.get(eid)))
    return len(keys)


def _person_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -(int(row.get("linked_account_count") or 0)),
        row.get("display_name") is None,
        (row.get("display_name") or "").lower(),
        str(row.get("last_seen_at") or ""),
        row.get("person_id") or "",
    )


def build_people_directory_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List reconstructed people (human_actor clusters) for operator directory UI."""
    lim = max(1, min(int(limit), 500))
    off = max(0, int(offset))
    scan_limit = min(_MAX_DIRECTORY_SCAN, max(lim + off + 50, 200))
    rows, raw_total = _list_human_actor_entities(
        session, tenant_id=tenant_id, limit=scan_limit, offset=0
    )
    entities_by_id = {row.id: org_entity_public_dict(row) for row in rows}
    entity_ids = set(entities_by_id.keys())
    metadata_labels = _enrich_directory_labels_v1(
        session,
        tenant_id=tenant_id,
        entities_by_id=entities_by_id,
        seed_labels=_metadata_labels_for_entities(entities_by_id),
    )
    clusters = _cluster_human_actors(
        session,
        tenant_id=tenant_id,
        entity_ids=entity_ids,
        entities_by_id=entities_by_id,
        labels_by_entity_id=metadata_labels,
    )
    auth_graph_ids = _entity_ids_in_auth_graph(session, tenant_id=tenant_id, entity_ids=entity_ids)

    cluster_rows: list[tuple[set[uuid.UUID], dict[str, Any]]] = [
        (
            cluster,
            _person_row_from_cluster_light(cluster, entities_by_id, auth_graph_ids, metadata_labels),
        )
        for cluster in clusters.values()
    ]
    cluster_rows.sort(key=lambda item: _person_sort_key(item[1]))
    page_clusters = cluster_rows[off : off + lim]

    page_entity_ids: set[uuid.UUID] = set()
    for cluster, _ in page_clusters:
        page_entity_ids.update(cluster)
    page_entities = {eid: entities_by_id[eid] for eid in page_entity_ids if eid in entities_by_id}
    page_labels = _batch_entity_identity_labels_v1(
        session,
        tenant_id=tenant_id,
        entities_by_id=page_entities,
        seed_labels={eid: metadata_labels[eid] for eid in page_entities if eid in metadata_labels},
    )
    merged_labels = {**metadata_labels, **page_labels}

    people = []
    for cluster, _ in page_clusters:
        row = _person_row_from_cluster_light(cluster, entities_by_id, auth_graph_ids, merged_labels)
        row["cluster_size"] = len(cluster)
        row["connector_id_count"] = _connector_id_count_for_cluster(
            cluster,
            entities_by_id=entities_by_id,
            labels_by_entity_id=merged_labels,
        )
        row["is_singleton_cluster"] = len(cluster) <= 1
        people.append(row)
    people.sort(key=_person_sort_key)
    return {
        "surface_kind": "operator_people_directory_v1",
        "schema_version": PEOPLE_DIRECTORY_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "people": people,
        "total": len(cluster_rows),
        "raw_entity_count": raw_total,
        "limit": lim,
        "offset": off,
        "generated_at_utc": datetime.now(UTC),
    }


def _payload_dict(raw: RawIngestionRecord | None) -> dict[str, Any]:
    if raw is None:
        return {}
    body = raw.payload_body
    return dict(body) if isinstance(body, dict) else {}


def _activity_title(
    *,
    kind: str,
    connector: str,
    payload: dict[str, Any],
    canonical: dict[str, Any],
) -> str:
    if kind == "message":
        msg = payload.get("message") if isinstance(payload.get("message"), dict) else payload
        text = msg.get("text") or msg.get("body") or msg.get("content") or ""
        if isinstance(text, str) and text.strip():
            return text.strip()[:160]
        return "Message"
    if kind == "pull_request":
        pr = payload.get("pull_request") if isinstance(payload.get("pull_request"), dict) else payload
        title = pr.get("title") if isinstance(pr, dict) else None
        if isinstance(title, str) and title.strip():
            return title.strip()[:160]
        return "Pull request"
    if kind == "issue":
        issue = payload.get("issue") if isinstance(payload.get("issue"), dict) else payload
        title = issue.get("title") if isinstance(issue, dict) else None
        if isinstance(title, str) and title.strip():
            return title.strip()[:160]
        return "Issue"
    if kind in ("document", "page"):
        title = payload.get("title") or payload.get("name")
        if isinstance(title, str) and title.strip():
            return title.strip()[:160]
        return kind.replace("_", " ").title()
    if kind == "workflow_run":
        run = payload.get("workflow_run") if isinstance(payload.get("workflow_run"), dict) else payload
        name = run.get("name") if isinstance(run, dict) else None
        if isinstance(name, str) and name.strip():
            return name.strip()[:160]
        return "Workflow run"
    emitted_title = canonical.get("title") or canonical.get("name")
    if isinstance(emitted_title, str) and emitted_title.strip():
        return emitted_title.strip()[:160]
    return f"{connector} {kind.replace('_', ' ')}"


def _activity_from_receipt(
    session: Session,
    receipt: dict[str, Any],
) -> dict[str, Any] | None:
    kind = str(receipt.get("anchor_canonical_object_kind") or "")
    if kind not in _WORK_KINDS and kind != "person":
        return None
    if kind == "person":
        return None
    raw_id = receipt.get("anchor_raw_record_id")
    raw = session.get(RawIngestionRecord, int(raw_id)) if raw_id is not None else None
    payload = _payload_dict(raw)
    canonical = dict(receipt.get("canonical") or {})
    connector = str(receipt.get("anchor_connector") or (raw.connector if raw else "unknown"))
    title = _activity_title(kind=kind, connector=connector, payload=payload, canonical=canonical)
    external_id = raw.external_id if raw else None
    occurred = None
    if raw and raw.ingested_at:
        occurred = raw.ingested_at.isoformat()
    return {
        "activity_id": f"{raw_id}:{kind}",
        "kind": kind,
        "connector": connector,
        "title": title,
        "occurred_at": occurred,
        "raw_record_id": int(raw_id) if raw_id is not None else None,
        "external_id": external_id,
        "resource_type": raw.resource_type if raw else None,
        "canonical_entity_id": receipt.get("anchor_canonical_entity_id"),
    }


def _accounts_from_handles(handles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    for handle in handles:
        pk = str(handle.get("projection_kind") or "unknown")
        label = _SYSTEM_LABELS.get(pk, pk.replace("_", " ").title())
        detail_parts: list[str] = []
        for key, prefix in (
            ("slack_user_id", "Slack"),
            ("github_login", "GitHub"),
            ("notion_user_id", "Notion"),
            ("linear_user_id", "Linear"),
            ("email_norm", ""),
        ):
            val = handle.get(key)
            if isinstance(val, str) and val.strip():
                detail_parts.append(f"{prefix} {val}".strip() if prefix else val)
        accounts.append(
            {
                "system": label,
                "projection_kind": pk,
                "detail": " · ".join(detail_parts) if detail_parts else "—",
                "entity_id": str(handle.get("handle_id") or ""),
                "is_primary": bool(handle.get("is_primary")),
            }
        )
    return accounts


def build_person_profile_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
    activity_limit: int = 80,
) -> dict[str, Any]:
    """Human-friendly profile for one reconstructed person (includes linked cluster)."""
    row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=entity_id)
    if row is None:
        raise ValueError("person_not_found")

    entity = org_entity_public_dict(row)
    linked_ids = _resolve_people_cluster_entity_ids_v1(
        session,
        tenant_id=tenant_id,
        entity_id=entity_id,
    )
    linked_entities_by_id: dict[uuid.UUID, dict[str, Any]] = {}
    for eid in linked_ids:
        linked_row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=eid)
        if linked_row is not None:
            linked_entities_by_id[eid] = org_entity_public_dict(linked_row)
    labels_by_entity_id = _batch_entity_identity_labels_v1(
        session,
        tenant_id=tenant_id,
        entities_by_id=linked_entities_by_id,
    )
    handles: list[dict[str, Any]] = []
    seen_handle_ids: set[str] = set()
    for eid in sorted(linked_ids, key=str):
        ent = linked_entities_by_id.get(eid)
        if ent is None:
            continue
        resolved = _resolved_identity_from_entity(ent)
        if resolved is None:
            continue
        hid = str(resolved.get("handle_id") or eid)
        if hid in seen_handle_ids:
            continue
        seen_handle_ids.add(hid)
        lbl = labels_by_entity_id.get(eid) or {}
        if lbl.get("display_name") and not resolved.get("display_name"):
            resolved["display_name"] = lbl["display_name"]
        if lbl.get("email") and not resolved.get("email_norm"):
            resolved["email_norm"] = lbl["email"]
        resolved["is_primary"] = eid == entity_id
        handles.append(resolved)
    entity_labels = labels_by_entity_id.get(entity_id) or {}
    display_name = _pick_display_name(handles, entity, labels=entity_labels)
    email = _pick_email(handles, entity, labels=entity_labels)
    if display_name is None or email is None:
        for eid in sorted(linked_ids, key=str):
            lbl = labels_by_entity_id.get(eid) or {}
            if display_name is None and lbl.get("display_name"):
                display_name = lbl["display_name"]
            if email is None and lbl.get("email"):
                email = lbl["email"]
    systems = _systems_from_handles(handles, entity)
    accounts = _accounts_from_handles(handles)

    auth_links = list_org_link_explorer_rows(
        session, tenant_id=tenant_id, handle_id=entity_id, authoritative_only=True, limit=48
    )
    related_people: list[dict[str, Any]] = []
    seen_people: set[str] = set()
    for link in auth_links:
        candidates: list[str] = []
        src = link.get("source_handle_id")
        if src:
            candidates.append(str(src))
        if link.get("target_kind") == "org_entity" and link.get("target"):
            candidates.append(str(link["target"]))
        for oid in candidates:
            if oid == str(entity_id):
                continue
            if oid in seen_people or oid in {str(x) for x in linked_ids}:
                continue
            other_row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=uuid.UUID(oid))
            if other_row is None or other_row.entity_kind != OrgEntityKind.HUMAN_ACTOR.value:
                continue
            seen_people.add(oid)
            other_entity = org_entity_public_dict(other_row)
            other_handles = _list_linked_handles_v1(
                session, tenant_id=tenant_id, entity_id=uuid.UUID(oid), limit=8
            )
            other_labels = labels_by_entity_id.get(uuid.UUID(oid))
            if other_labels is None:
                other_labels = _batch_entity_identity_labels_v1(
                    session,
                    tenant_id=tenant_id,
                    entities_by_id={uuid.UUID(oid): other_entity},
                ).get(uuid.UUID(oid))
            related_people.append(
                {
                    "person_id": oid,
                    "display_name": _pick_display_name(other_handles, other_entity, labels=other_labels),
                    "email": _pick_email(other_handles, other_entity, labels=other_labels),
                    "link_type": link.get("link_type"),
                    "rule_id": link.get("rule_id"),
                }
            )

    evidence = build_entity_continuity_evidence_inspection_v1(
        session,
        tenant_id=tenant_id,
        entity_id=entity_id,
        anchor_scan_limit=5_000,
        receipt_limit=max(1, min(int(activity_limit), 200)),
    )
    activities: list[dict[str, Any]] = []
    seen_activity_ids: set[str] = set()
    for receipt in evidence.get("evidence_receipts") or []:
        item = _activity_from_receipt(session, receipt)
        if item is not None and item["activity_id"] not in seen_activity_ids:
            seen_activity_ids.add(item["activity_id"])
            activities.append(item)
    for other_id in sorted(linked_ids - {entity_id}, key=str)[:31]:
        other_evidence = build_entity_continuity_evidence_inspection_v1(
            session,
            tenant_id=tenant_id,
            entity_id=other_id,
            anchor_scan_limit=2_000,
            receipt_limit=max(8, min(int(activity_limit) // 4, 40)),
        )
        for receipt in other_evidence.get("evidence_receipts") or []:
            item = _activity_from_receipt(session, receipt)
            if item is not None and item["activity_id"] not in seen_activity_ids:
                seen_activity_ids.add(item["activity_id"])
                activities.append(item)
    activities.sort(key=lambda a: a.get("occurred_at") or "", reverse=True)

    retrieval: dict[str, Any] | None = None
    try:
        retrieval = search_operator_retrieval_entries_v1(
            session,
            tenant_id=tenant_id,
            entity_id=str(entity_id),
            limit=24,
            offset=0,
        )
    except ValueError:
        retrieval = None

    work_summary: dict[str, int] = {}
    for act in activities:
        k = str(act.get("kind") or "other")
        work_summary[k] = work_summary.get(k, 0) + 1

    meta = _meta(entity)
    title_raw = meta.get("title") or meta.get("role")
    title = title_raw.strip() if isinstance(title_raw, str) and title_raw.strip() else None
    resolved = _resolved_identity_from_entity(entity)

    return {
        "surface_kind": "operator_person_profile_v1",
        "schema_version": PEOPLE_DIRECTORY_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "person_id": str(entity_id),
        "entity_ids": [str(x) for x in sorted(linked_ids, key=str)],
        "display_name": display_name,
        "email": email,
        "title": title,
        "systems": systems,
        "accounts": accounts,
        "primary_identity": resolved,
        "related_people": related_people[:24],
        "authoritative_link_count": len(auth_links),
        "activity": activities[: max(1, min(int(activity_limit), 200))],
        "activity_total": len(activities),
        "work_summary": work_summary,
        "retrieval_entries": (retrieval or {}).get("items") or [],
        "retrieval_total": (retrieval or {}).get("total") or 0,
        "evidence_anchor_count": evidence.get("anchors_related_to_entity"),
        "generated_at_utc": datetime.now(UTC),
    }
