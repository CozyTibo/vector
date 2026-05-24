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
from vector.domains.cortex.identity.link_explorer import list_org_link_explorer_rows
from vector.domains.cortex.identity.org_entities import OrgEntityKind, get_org_entity, org_entity_public_dict
from vector.domains.cortex.pipeline.operator_admin_inspect_chains import search_operator_retrieval_entries_v1
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

PEOPLE_DIRECTORY_SCHEMA_VERSION: Final[int] = 1

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


def _meta(entity: dict[str, Any]) -> dict[str, Any]:
    return dict(entity.get("metadata_json") or {})


def _pick_display_name(handles: list[dict[str, Any]], entity: dict[str, Any]) -> str | None:
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


def _pick_email(handles: list[dict[str, Any]], entity: dict[str, Any]) -> str | None:
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


def _score_entity(entity: dict[str, Any], handles: list[dict[str, Any]]) -> int:
    score = 0
    if _pick_display_name(handles, entity):
        score += 10
    if _pick_email(handles, entity):
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
    clusters: dict[uuid.UUID, set[uuid.UUID]] = {}
    for eid in entity_ids:
        root = uf.find(eid)
        clusters.setdefault(root, set()).add(eid)
    return clusters


def _person_row_from_cluster(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    cluster: set[uuid.UUID],
) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    all_handles: list[dict[str, Any]] = []
    for eid in sorted(cluster, key=str):
        row = get_org_entity(session, tenant_id=tenant_id, org_entity_id=eid)
        if row is None:
            continue
        entity = org_entity_public_dict(row)
        entities.append(entity)
        all_handles.extend(_list_linked_handles_v1(session, tenant_id=tenant_id, entity_id=eid, limit=16))

    if not entities:
        primary_id = sorted(cluster, key=str)[0]
        return {
            "person_id": str(primary_id),
            "entity_ids": [str(x) for x in sorted(cluster, key=str)],
            "display_name": None,
            "email": None,
            "systems": [],
            "linked_account_count": 0,
            "in_auth_graph": False,
            "last_seen_at": None,
            "title": None,
        }

    primary = max(
        entities,
        key=lambda ent: _score_entity(
            ent,
            [h for h in all_handles if str(h.get("handle_id")) == str(ent.get("id"))],
        ),
    )
    primary_id = uuid.UUID(str(primary["id"]))
    handles = _list_linked_handles_v1(session, tenant_id=tenant_id, entity_id=primary_id, limit=32)
    display_name = _pick_display_name(handles, primary)
    email = _pick_email(handles, primary)
    systems = _systems_from_handles(handles, primary)

    auth_edges = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
                CortexOrgLink.revoked_at.is_(None),
                or_(
                    CortexOrgLink.source_entity_id.in_(cluster),
                    CortexOrgLink.target_entity_id.in_(cluster),
                ),
            )
        )
        or 0
    )

    last_seen = None
    for ent in entities:
        ts = ent.get("updated_at")
        if ts and (last_seen is None or ts > last_seen):
            last_seen = ts

    meta = _meta(primary)
    title = meta.get("title") or meta.get("role")
    if isinstance(title, str):
        title = title.strip() or None
    else:
        title = None

    return {
        "person_id": str(primary_id),
        "entity_ids": [str(x) for x in sorted(cluster, key=str)],
        "display_name": display_name,
        "email": email,
        "systems": systems,
        "linked_account_count": len({str(h.get("handle_id")) for h in handles}),
        "in_auth_graph": auth_edges > 0,
        "last_seen_at": last_seen,
        "title": title,
    }


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
    rows, raw_total = _list_human_actor_entities(session, tenant_id=tenant_id, limit=2000, offset=0)
    entity_ids = {row.id for row in rows}
    clusters = _cluster_human_actors(session, tenant_id=tenant_id, entity_ids=entity_ids)

    people = [
        _person_row_from_cluster(session, tenant_id=tenant_id, cluster=cluster)
        for cluster in clusters.values()
    ]
    people.sort(
        key=lambda p: (
            p.get("display_name") is None,
            (p.get("display_name") or "").lower(),
            p.get("person_id") or "",
        )
    )
    page = people[off : off + lim]
    return {
        "surface_kind": "operator_people_directory_v1",
        "schema_version": PEOPLE_DIRECTORY_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "people": page,
        "total": len(people),
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
    linked_ids = _list_linked_entity_ids_v1(session, tenant_id=tenant_id, entity_id=entity_id, limit=64)
    handles = _list_linked_handles_v1(session, tenant_id=tenant_id, entity_id=entity_id, limit=64)
    display_name = _pick_display_name(handles, entity)
    email = _pick_email(handles, entity)
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
            related_people.append(
                {
                    "person_id": oid,
                    "display_name": _pick_display_name(other_handles, other_entity),
                    "email": _pick_email(other_handles, other_entity),
                    "link_type": link.get("link_type"),
                    "rule_id": link.get("rule_id"),
                }
            )

    evidence = build_entity_continuity_evidence_inspection_v1(
        session,
        tenant_id=tenant_id,
        entity_id=entity_id,
        receipt_limit=max(1, min(int(activity_limit), 200)),
    )
    activities: list[dict[str, Any]] = []
    for receipt in evidence.get("evidence_receipts") or []:
        item = _activity_from_receipt(session, receipt)
        if item is not None:
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
