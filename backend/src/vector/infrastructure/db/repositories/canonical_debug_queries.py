"""Read-only queries for /debug/canonical."""

from __future__ import annotations

import uuid
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.canonical import (
    Actor,
    ActorExternalIdentity,
    Artifact,
    ArtifactKind,
    CurrentMapping,
    ExternalReference,
    MappingEvent,
    RelationKind,
    Relationship,
)


@dataclass(frozen=True)
class RowsPage:
    total: int
    items: Sequence[Any]


def list_actors(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
    q: str | None,
) -> RowsPage:
    stmt = select(Actor).where(Actor.tenant_id == tenant_id)
    if q and q.strip():
        pat = f"%{q.strip()}%"
        stmt = stmt.where(Actor.display_name.ilike(pat))
    count_q = select(func.count()).select_from(stmt.subquery())
    total = int(session.scalar(count_q) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(Actor.created_at.desc()).limit(limit).offset(offset),
        ).all(),
    )
    return RowsPage(total=total, items=rows)


def list_artifacts(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_kind_id: int | None,
    limit: int,
    offset: int,
    q: str | None,
) -> RowsPage:
    stmt = select(Artifact).where(Artifact.tenant_id == tenant_id)
    if artifact_kind_id is not None:
        stmt = stmt.where(Artifact.artifact_kind_id == artifact_kind_id)
    if q and q.strip():
        pat = f"%{q.strip()}%"
        stmt = stmt.where(or_(Artifact.title.ilike(pat), Artifact.summary.ilike(pat)))
    count_q = select(func.count()).select_from(stmt.subquery())
    total = int(session.scalar(count_q) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(Artifact.last_observed_at.desc().nullslast()).limit(limit).offset(offset),
        ).all(),
    )
    return RowsPage(total=total, items=rows)


def list_relationships(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    current_only: bool,
    limit: int,
    offset: int,
) -> RowsPage:
    stmt = select(Relationship).where(Relationship.tenant_id == tenant_id)
    if current_only:
        stmt = stmt.where(Relationship.valid_to.is_(None))
    count_q = select(func.count()).select_from(stmt.subquery())
    total = int(session.scalar(count_q) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(Relationship.valid_from.desc()).limit(limit).offset(offset),
        ).all(),
    )
    return RowsPage(total=total, items=rows)


def list_external_references(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
) -> RowsPage:
    stmt = select(ExternalReference).where(ExternalReference.tenant_id == tenant_id)
    count_q = select(func.count()).select_from(stmt.subquery())
    total = int(session.scalar(count_q) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(ExternalReference.external_key.asc()).limit(limit).offset(offset),
        ).all(),
    )
    return RowsPage(total=total, items=rows)


def list_mapping_events(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    external_reference_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> RowsPage:
    stmt = select(MappingEvent).where(MappingEvent.tenant_id == tenant_id)
    if external_reference_id is not None:
        stmt = stmt.where(MappingEvent.external_reference_id == external_reference_id)
    count_q = select(func.count()).select_from(stmt.subquery())
    total = int(session.scalar(count_q) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(MappingEvent.id.desc()).limit(limit).offset(offset),
        ).all(),
    )
    return RowsPage(total=total, items=rows)


def _kind_name_map(session: Session) -> dict[int, str]:
    # Use `select(Entity)` — `scalars(select(a, b))` only yields the first column per row.
    rows = session.scalars(select(ArtifactKind)).all()
    return {int(k.id): str(k.name) for k in rows}


def _relation_name_map(session: Session) -> dict[int, str]:
    rows = session.scalars(select(RelationKind)).all()
    return {int(k.id): str(k.name) for k in rows}


_MSG_PREVIEW_MAX = 120


def _artifact_endpoint_label(art: Artifact, kinds: dict[int, str], uid: uuid.UUID) -> str:
    """Human-oriented label for debug APIs (matches frontend execution-graph wording)."""
    kind_name = kinds.get(art.artifact_kind_id, "?")
    if kind_name == "revision":
        sha = (art.title or "").strip()
        msg = (art.summary or "").strip()
        first = msg.split("\n", 1)[0].strip() if msg else ""
        if len(first) > _MSG_PREVIEW_MAX:
            first = first[: _MSG_PREVIEW_MAX - 1] + "…"
        if sha and first:
            return f"commit {sha} — {first}"
        if sha:
            return f"commit {sha}"
        return str(uid)
    if kind_name == "repository":
        fn = (art.title or "").strip()
        return f"repo {fn}" if fn else f"repository:{uid}"
    if kind_name == "changeset":
        t = (art.title or "").strip()
        return f"PR — {t}" if t else f"changeset:{uid}"
    if kind_name == "trackable_unit":
        t = (art.title or "").strip()
        return f"issue — {t}" if t else f"issue:{uid}"
    return (art.title or "").strip() or f"{kind_name}:{uid}"


def _endpoint_label(
    session: Session,
    tenant_id: uuid.UUID,
    typ: str,
    uid: uuid.UUID,
    kinds: dict[int, str],
) -> str:
    if typ == "actor":
        a = session.get(Actor, uid)
        return (a.display_name or str(uid)) if a and a.tenant_id == tenant_id else str(uid)
    art = session.get(Artifact, uid)
    if art is None or art.tenant_id != tenant_id:
        return str(uid)
    return _artifact_endpoint_label(art, kinds, uid)


def _rel_summary(
    session: Session,
    tenant_id: uuid.UUID,
    r: Relationship,
    rk: dict[int, str],
    kinds: dict[int, str],
) -> dict[str, Any]:
    sub_l = _endpoint_label(session, tenant_id, r.subject_type, r.subject_id, kinds)
    obj_l = _endpoint_label(session, tenant_id, r.object_type, r.object_id, kinds)
    return {
        "id": str(r.id),
        "relation_kind": rk.get(r.relation_kind_id, str(r.relation_kind_id)),
        "subject": {"type": r.subject_type, "id": str(r.subject_id), "label": sub_l},
        "object": {"type": r.object_type, "id": str(r.object_id), "label": obj_l},
        "valid_from": r.valid_from.isoformat(),
        "valid_to": r.valid_to.isoformat() if r.valid_to else None,
    }


def actor_detail(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> dict[str, Any] | None:
    a = session.get(Actor, actor_id)
    if a is None or a.tenant_id != tenant_id:
        return None
    rk = _relation_name_map(session)
    kinds = _kind_name_map(session)
    rels = list(
        session.scalars(
            select(Relationship).where(
                Relationship.tenant_id == tenant_id,
                Relationship.valid_to.is_(None),
                or_(
                    and_(Relationship.subject_type == "actor", Relationship.subject_id == actor_id),
                    and_(Relationship.object_type == "actor", Relationship.object_id == actor_id),
                ),
            ),
        ).all(),
    )
    identities = list(
        session.scalars(
            select(ActorExternalIdentity).where(
                ActorExternalIdentity.tenant_id == tenant_id,
                ActorExternalIdentity.actor_id == actor_id,
            ),
        ).all(),
    )
    return {
        "actor": {
            "id": str(a.id),
            "kind": a.kind,
            "display_name": a.display_name,
            "created_at": a.created_at.isoformat(),
        },
        "external_identities": [
            {
                "id": str(e.id),
                "connector": e.connector,
                "external_id": e.external_id,
                "last_observed_at": e.last_observed_at.isoformat() if e.last_observed_at else None,
            }
            for e in identities
        ],
        "relationships": [_rel_summary(session, tenant_id, r, rk, kinds) for r in rels],
    }


def artifact_detail(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_id: uuid.UUID,
) -> dict[str, Any] | None:
    a = session.get(Artifact, artifact_id)
    if a is None or a.tenant_id != tenant_id:
        return None
    kinds = _kind_name_map(session)
    rk = _relation_name_map(session)
    rels = list(
        session.scalars(
            select(Relationship).where(
                Relationship.tenant_id == tenant_id,
                Relationship.valid_to.is_(None),
                or_(
                    and_(
                        Relationship.subject_type == "artifact",
                        Relationship.subject_id == artifact_id,
                    ),
                    and_(
                        Relationship.object_type == "artifact",
                        Relationship.object_id == artifact_id,
                    ),
                ),
            ),
        ).all(),
    )
    xref_rows = list(
        session.scalars(
            select(ExternalReference)
            .join(
                CurrentMapping,
                ExternalReference.id == CurrentMapping.external_reference_id,
            )
            .where(
                CurrentMapping.tenant_id == tenant_id,
                CurrentMapping.artifact_id == artifact_id,
            )
            .limit(50),
        ).all(),
    )
    return {
        "artifact": {
            "id": str(a.id),
            "artifact_kind": kinds.get(a.artifact_kind_id, str(a.artifact_kind_id)),
            "artifact_kind_id": a.artifact_kind_id,
            "title": a.title,
            "summary": a.summary,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "last_observed_at": a.last_observed_at.isoformat() if a.last_observed_at else None,
        },
        "relationships": [_rel_summary(session, tenant_id, r, rk, kinds) for r in rels],
        "external_references": [
            {
                "id": str(x.id),
                "external_key": x.external_key,
                "connector": x.connector,
                "last_raw_record_id": x.last_raw_record_id,
            }
            for x in xref_rows
        ],
    }


def relationship_detail(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    relationship_id: uuid.UUID,
) -> dict[str, Any] | None:
    r = session.get(Relationship, relationship_id)
    if r is None or r.tenant_id != tenant_id:
        return None
    rk = _relation_name_map(session)
    kinds = _kind_name_map(session)
    return {
        "relationship": {
            "id": str(r.id),
            "relation_kind": rk.get(r.relation_kind_id, str(r.relation_kind_id)),
            "source": r.source,
            "evidence_ref": r.evidence_ref,
            "valid_from": r.valid_from.isoformat(),
            "valid_to": r.valid_to.isoformat() if r.valid_to else None,
        },
        "subject": _endpoint_label(session, tenant_id, r.subject_type, r.subject_id, kinds),
        "object": _endpoint_label(session, tenant_id, r.object_type, r.object_id, kinds),
    }


def external_reference_detail(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    xref_id: uuid.UUID,
) -> dict[str, Any] | None:
    x = session.get(ExternalReference, xref_id)
    if x is None or x.tenant_id != tenant_id:
        return None
    cm = session.get(CurrentMapping, xref_id)
    evs = list(
        session.scalars(
            select(MappingEvent)
            .where(MappingEvent.external_reference_id == xref_id)
            .order_by(MappingEvent.id.desc())
            .limit(50),
        ).all(),
    )
    return {
        "external_reference": {
            "id": str(x.id),
            "connector": x.connector,
            "external_key": x.external_key,
            "resource_type": x.resource_type,
        },
        "current_mapping": {
            "artifact_id": str(cm.artifact_id) if cm and cm.artifact_id else None,
            "actor_id": str(cm.actor_id) if cm and cm.actor_id else None,
        }
        if cm
        else None,
        "recent_mapping_events": [
            {
                "id": e.id,
                "rule_version": e.rule_version,
                "effective_at": e.effective_at.isoformat(),
                "payload_hash": e.payload_hash,
            }
            for e in evs
        ],
    }


def build_subgraph(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    anchor_type: str,
    anchor_id: uuid.UUID,
    depth: int,
    max_nodes: int,
    current_only: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool, str | None]:
    if anchor_type not in {"artifact", "actor"}:
        msg = "bad anchor type"
        raise ValueError(msg)
    if anchor_type == "artifact":
        art = session.get(Artifact, anchor_id)
        if art is None or art.tenant_id != tenant_id:
            return [], [], False, "anchor not found"
    else:
        act = session.get(Actor, anchor_id)
        if act is None or act.tenant_id != tenant_id:
            return [], [], False, "anchor not found"

    kinds = _kind_name_map(session)
    rk = _relation_name_map(session)

    NodeKey = tuple[str, uuid.UUID]
    q: deque[tuple[NodeKey, int]] = deque([((anchor_type, anchor_id), 0)])
    seen: set[NodeKey] = {(anchor_type, anchor_id)}
    edges_out: list[Relationship] = []
    truncated = False
    reason: str | None = None

    while q:
        node, d = q.popleft()
        if d >= depth:
            continue
        nt, nid = node
        stmt = select(Relationship).where(Relationship.tenant_id == tenant_id)
        if current_only:
            stmt = stmt.where(Relationship.valid_to.is_(None))
        stmt = stmt.where(
            or_(
                and_(Relationship.subject_type == nt, Relationship.subject_id == nid),
                and_(Relationship.object_type == nt, Relationship.object_id == nid),
            ),
        )
        for r in session.scalars(stmt).all():
            edges_out.append(r)
            if r.subject_type == nt and r.subject_id == nid:
                other: NodeKey = (r.object_type, r.object_id)
            else:
                other = (r.subject_type, r.subject_id)
            if other in seen:
                continue
            if len(seen) >= max_nodes:
                truncated = True
                reason = "max_nodes"
                break
            seen.add(other)
            q.append((other, d + 1))
        if truncated:
            break

    nodes_payload: list[dict[str, Any]] = []
    for nt2, uid2 in seen:
        if nt2 == "actor":
            act = session.get(Actor, uid2)
            nodes_payload.append(
                {
                    "id": str(uid2),
                    "node_type": "actor",
                    "actor_kind": act.kind if act else None,
                    "label": act.display_name if act else None,
                    "artifact_kind": None,
                    "status": None,
                    "last_observed_at": None,
                },
            )
        else:
            art = session.get(Artifact, uid2)
            nodes_payload.append(
                {
                    "id": str(uid2),
                    "node_type": "artifact",
                    "artifact_kind": kinds.get(art.artifact_kind_id, "?") if art else None,
                    "label": _artifact_endpoint_label(art, kinds, uid2) if art else None,
                    "actor_kind": None,
                    "status": art.status if art else None,
                    "last_observed_at": art.last_observed_at if art else None,
                },
            )

    edge_payload: list[dict[str, Any]] = []
    for r in edges_out:
        edge_payload.append(
            {
                "id": str(r.id),
                "source_id": str(r.subject_id),
                "target_id": str(r.object_id),
                "relation_kind": rk.get(r.relation_kind_id, str(r.relation_kind_id)),
                "directed": True,
                "valid_from": r.valid_from,
                "valid_to": r.valid_to,
            },
        )

    return nodes_payload, edge_payload, truncated, reason
