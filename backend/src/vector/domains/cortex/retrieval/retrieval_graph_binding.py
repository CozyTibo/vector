"""Phase 07 P07-17 — graph / identity / canonical bindings.

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md`` §Graph.
**RET-GRAPH-01** authoritative partition law; **RET-GRAPH-02** entity/link mat addressing;
**RET-GRAPH-03** candidate → ``evidence_candidate_only``.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_addressing import (
    build_org_entity_ref_body_v1,
    build_org_link_ref_body_v1,
)
from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_GRAPH_ORPHAN_V1
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    materialize_retrieval_index_entry_v1,
)
from vector.domains.cortex.retrieval.retrieval_ingress import (
    RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1,
    classify_org_link_authority_for_retrieval_v1,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import derive_retrieval_lookup_id_v1
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink

PHASE07_RETRIEVAL_GRAPH_BINDING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_GRAPH01_GATE_ID_V1: Final[str] = "G-P07-GRAPH-01"

RETRIEVAL_GRAPH_BINDING_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md"
)

RET_GRAPH01_RULE_ID_V1: Final[str] = "RET-GRAPH-01"

RET_GRAPH02_RULE_ID_V1: Final[str] = "RET-GRAPH-02"

RET_GRAPH03_RULE_ID_V1: Final[str] = "RET-GRAPH-03"

_GRAPH_SCOPED_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {
        "ownership_continuity",
        "dependency_propagation",
        "continuity_topology",
        "escalation",
    }
)

_GRAPH_SCOPE_QUERY_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "entity_by_id",
        "link_by_id",
        "tenant_authoritative_link_inventory",
        "orphan_probe",
    }
)

_GRAPH_ADDRESSING_REF_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "org_entity_id",
        "org_link_id",
    }
)

_RETRIEVAL_GRAPH_ORPHAN_DETECTED_TOTAL_V1: int = 0

_RETRIEVAL_GRAPH_BIND_FAILURES_TOTAL_V1: int = 0


class RetrievalGraphBindingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_retrieval_graph_orphan_detected_total_v1() -> int:
    return _RETRIEVAL_GRAPH_ORPHAN_DETECTED_TOTAL_V1


def get_retrieval_graph_bind_failures_total_v1() -> int:
    return _RETRIEVAL_GRAPH_BIND_FAILURES_TOTAL_V1


def record_retrieval_graph_orphan_detected_v1(
    *,
    tenant_id: str,
    reason: str,
    ref_kind: str | None = None,
    ref_value: str | None = None,
) -> dict[str, Any]:
    global _RETRIEVAL_GRAPH_ORPHAN_DETECTED_TOTAL_V1
    _RETRIEVAL_GRAPH_ORPHAN_DETECTED_TOTAL_V1 += 1
    return {
        "event": "retrieval_graph_orphan_detected",
        "tenant_id": tenant_id,
        "reason": reason,
        "ref_kind": ref_kind,
        "ref_value": ref_value,
    }


def record_retrieval_graph_bind_failure_v1(
    *,
    tenant_id: str,
    reason: str,
    ref_kind: str | None = None,
) -> dict[str, Any]:
    global _RETRIEVAL_GRAPH_BIND_FAILURES_TOTAL_V1
    _RETRIEVAL_GRAPH_BIND_FAILURES_TOTAL_V1 += 1
    return {
        "event": "retrieval_graph_bind_failure",
        "tenant_id": tenant_id,
        "reason": reason,
        "ref_kind": ref_kind,
    }


def map_graph_ref_to_retrieval_lookup_id_v1(
    *,
    ref_kind: str,
    ref_value: str,
    replay_identity: str,
) -> str:
    """**RET-GRAPH-02** — Phase 04 entity/link ids → ``retrieval_lookup_id``."""
    kind = str(ref_kind).strip()
    value = str(ref_value).strip()
    if not value:
        raise RetrievalGraphBindingError("graph_ref_value_required")
    if kind == "org_entity_id":
        return derive_retrieval_lookup_id_v1(
            index_kind="org_entity",
            index_key=f"org_entity:{value}",
            replay_identity=replay_identity,
        )
    if kind == "org_link_id":
        return derive_retrieval_lookup_id_v1(
            index_kind="org_link",
            index_key=f"org_link:{value}",
            replay_identity=replay_identity,
        )
    raise RetrievalGraphBindingError("graph_ref_kind_unknown", detail={"ref_kind": kind})


def build_graph_handoff_entry_v1(
    *,
    ref_kind: str,
    ref_value: str,
    replay_identity: str,
    link_authority: str | None = None,
    evidence_legality_class: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "ref_kind": ref_kind,
        "ref_value": ref_value,
        "retrieval_lookup_id": map_graph_ref_to_retrieval_lookup_id_v1(
            ref_kind=ref_kind,
            ref_value=ref_value,
            replay_identity=replay_identity,
        ),
    }
    if ref_kind == "org_entity_id":
        entry["org_entity_ref"] = build_org_entity_ref_body_v1(org_entity_id=ref_value)
    if ref_kind == "org_link_id":
        entry["org_link_ref"] = build_org_link_ref_body_v1(org_link_id=ref_value)
    if link_authority:
        entry["link_authority"] = link_authority
    if evidence_legality_class:
        entry["evidence_legality_class"] = evidence_legality_class
    return entry


def load_org_entity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    org_entity_id: uuid.UUID | str,
) -> CortexOrgEntity | None:
    try:
        eid = org_entity_id if isinstance(org_entity_id, uuid.UUID) else uuid.UUID(str(org_entity_id))
    except (ValueError, TypeError) as exc:
        raise RetrievalGraphBindingError("invalid_org_entity_id", detail={"org_entity_id": str(org_entity_id)}) from exc
    row = session.get(CortexOrgEntity, eid)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def load_org_link_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    org_link_id: uuid.UUID | str,
) -> CortexOrgLink | None:
    try:
        lid = org_link_id if isinstance(org_link_id, uuid.UUID) else uuid.UUID(str(org_link_id))
    except (ValueError, TypeError) as exc:
        raise RetrievalGraphBindingError("invalid_org_link_id", detail={"org_link_id": str(org_link_id)}) from exc
    row = session.get(CortexOrgLink, lid)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def is_org_entity_orphan_v1(entity: CortexOrgEntity | None) -> bool:
    if entity is None:
        return True
    if entity.tombstoned_at is not None:
        return True
    if str(entity.lifecycle_state) not in ("active",):
        return True
    return False


def is_org_link_orphan_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    link: CortexOrgLink | None,
) -> bool:
    if link is None:
        return True
    if link.revoked_at is not None:
        return True
    src = load_org_entity_v1(session, tenant_id=tenant_id, org_entity_id=link.source_entity_id)
    tgt = load_org_entity_v1(session, tenant_id=tenant_id, org_entity_id=link.target_entity_id)
    return is_org_entity_orphan_v1(src) or is_org_entity_orphan_v1(tgt)


def build_rd_graph_orphan_omission_row_v1(
    *,
    upstream_trigger: str = "orphan_artifacts",
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "retrieval_omission_class": RETRIEVAL_RD_GRAPH_ORPHAN_V1,
        "upstream_trigger": upstream_trigger,
        "detail": dict(detail or {}),
    }


def list_export_sequence_pin_violations_v1(
    *,
    replay_pins: Mapping[str, Any],
    temporal_scope: Mapping[str, Any] | None,
    workload_class: str,
) -> list[dict[str, Any]]:
    wl = str(workload_class)
    if wl not in _GRAPH_SCOPED_WORKLOADS_V1:
        return []
    pinned = replay_pins.get("export_sequence")
    if pinned is None and temporal_scope:
        pinned = temporal_scope.get("export_sequence")
    if pinned is None or str(pinned).strip() == "":
        return [
            build_rd_graph_orphan_omission_row_v1(
                upstream_trigger="export_sequence_pin_missing",
                detail={"workload_class": wl},
            )
        ]
    return []


def list_graph_orphan_omissions_v1(
    *,
    upstream_triggers: Mapping[str, Any] | None,
    entity_orphan: bool,
    link_orphan: bool,
    bind_required: bool,
) -> list[dict[str, Any]]:
    triggers = dict(upstream_triggers or {})
    if triggers.get("orphan_artifacts"):
        return [build_rd_graph_orphan_omission_row_v1()]
    out: list[dict[str, Any]] = []
    if bind_required and entity_orphan:
        out.append(
            build_rd_graph_orphan_omission_row_v1(
                upstream_trigger="org_entity_orphan",
                detail={"orphan": True},
            )
        )
    if bind_required and link_orphan:
        out.append(
            build_rd_graph_orphan_omission_row_v1(
                upstream_trigger="org_link_orphan",
                detail={"orphan": True},
            )
        )
    return out


def apply_candidate_link_legality_to_hits_v1(
    hits: list[dict[str, Any]],
    *,
    evidence_legality_class: str,
) -> list[dict[str, Any]]:
    """**RET-GRAPH-03** — candidate authoritative links never promote to authoritative evidence."""
    out: list[dict[str, Any]] = []
    for hit in hits:
        h = dict(hit)
        h["evidence_legality_class"] = evidence_legality_class
        prov = dict(h.get("provenance") or {})
        prov["link_authority_classification"] = evidence_legality_class
        h["provenance"] = prov
        out.append(h)
    return out


def query_graph_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    scope_kind: str,
    org_entity_id: str | None = None,
    org_link_id: str | None = None,
) -> dict[str, Any]:
    """Graph scope queries for admin debugger (**done when** registry defined)."""
    kind = str(scope_kind).strip()
    if kind not in _GRAPH_SCOPE_QUERY_KINDS_V1:
        raise RetrievalGraphBindingError("graph_scope_kind_unknown", detail={"scope_kind": kind})
    if kind == "entity_by_id":
        if not org_entity_id:
            raise RetrievalGraphBindingError("org_entity_id_required")
        ent = load_org_entity_v1(session, tenant_id=tenant_id, org_entity_id=org_entity_id)
        return {
            "scope_kind": kind,
            "entity_found": ent is not None,
            "orphan": is_org_entity_orphan_v1(ent),
        }
    if kind == "link_by_id":
        if not org_link_id:
            raise RetrievalGraphBindingError("org_link_id_required")
        link = load_org_link_v1(session, tenant_id=tenant_id, org_link_id=org_link_id)
        return {
            "scope_kind": kind,
            "link_found": link is not None,
            "orphan": is_org_link_orphan_v1(session, tenant_id=tenant_id, link=link),
            "link_authority": str(link.link_authority) if link else None,
        }
    if kind == "tenant_authoritative_link_inventory":
        rows = session.scalars(
            select(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
                CortexOrgLink.revoked_at.is_(None),
            )
            .order_by(CortexOrgLink.id.asc())
            .limit(500)
        ).all()
        return {"scope_kind": kind, "authoritative_link_count": len(rows)}
    orphan_entities = 0
    for ent in session.scalars(
        select(CortexOrgEntity).where(CortexOrgEntity.tenant_id == tenant_id).limit(1000)
    ).all():
        if is_org_entity_orphan_v1(ent):
            orphan_entities += 1
    orphan_links = 0
    for link in session.scalars(
        select(CortexOrgLink).where(CortexOrgLink.tenant_id == tenant_id).limit(1000)
    ).all():
        if is_org_link_orphan_v1(session, tenant_id=tenant_id, link=link):
            orphan_links += 1
    return {
        "scope_kind": kind,
        "orphan_entity_count": orphan_entities,
        "orphan_link_count": orphan_links,
    }


def build_graph_handoff_lookup_map_v1(
    *,
    entity: CortexOrgEntity | None,
    link: CortexOrgLink | None,
    replay_identity: str,
    execution_partition: str,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    by_entity: dict[str, dict[str, Any]] = {}
    by_link: dict[str, dict[str, Any]] = {}
    if entity is not None:
        eid = str(entity.id)
        entry = build_graph_handoff_entry_v1(
            ref_kind="org_entity_id",
            ref_value=eid,
            replay_identity=replay_identity,
            evidence_legality_class="evidence_authoritative"
            if not is_org_entity_orphan_v1(entity)
            else "evidence_unverifiable",
        )
        by_entity[eid] = entry
        entries.append(entry)
    if link is not None:
        lid = str(link.id)
        legality = classify_org_link_authority_for_retrieval_v1(
            str(link.link_authority),
            execution_partition=execution_partition,
        )
        entry = build_graph_handoff_entry_v1(
            ref_kind="org_link_id",
            ref_value=lid,
            replay_identity=replay_identity,
            link_authority=str(link.link_authority),
            evidence_legality_class=legality,
        )
        by_link[lid] = entry
        entries.append(entry)
    return {
        "schema_version": PHASE07_RETRIEVAL_GRAPH_BINDING_RUNTIME_SCHEMA_VERSION,
        "handoff_ref_kinds": sorted(_GRAPH_ADDRESSING_REF_KINDS_V1),
        "lookup_entries": entries,
        "by_org_entity_id": by_entity,
        "by_org_link_id": by_link,
        "graph_scope_queries": sorted(_GRAPH_SCOPE_QUERY_KINDS_V1),
        "lookup_map_digest": hash_reasoning_canonical_json_sha256_v1(
            {
                "entries": sorted(
                    (e["ref_kind"], e["ref_value"], e["retrieval_lookup_id"]) for e in entries
                )
            }
        ),
    }


def materialize_retrieval_index_from_graph_ref_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    ref_kind: str,
    ref_value: str,
    replay_identity: str,
    index_epoch: str,
    execution_partition: str = "authoritative",
    auto_publish: bool = True,
    omission_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize one index row for org entity or link addressing."""
    lookup_map = build_graph_handoff_lookup_map_v1(
        entity=load_org_entity_v1(session, tenant_id=tenant_id, org_entity_id=ref_value)
        if ref_kind == "org_entity_id"
        else None,
        link=load_org_link_v1(session, tenant_id=tenant_id, org_link_id=ref_value)
        if ref_kind == "org_link_id"
        else None,
        replay_identity=replay_identity,
        execution_partition=execution_partition,
    )
    entry = (lookup_map.get("by_org_entity_id") or {}).get(ref_value) or (
        lookup_map.get("by_org_link_id") or {}
    ).get(ref_value)
    if not entry:
        raise RetrievalGraphBindingError("graph_handoff_entry_missing")
    index_kind = "org_entity" if ref_kind == "org_entity_id" else "org_link"
    row = materialize_retrieval_index_entry_v1(
        session,
        tenant_id=tenant_id,
        replay_identity=replay_identity,
        index_epoch=index_epoch,
        index_kind=index_kind,
        index_key=f"{index_kind}:{ref_value}",
        chronology_legality_class="strict",
        causal_legality_class="verified",
        artifact_ref={ref_kind: ref_value},
        omission_summary=dict(omission_summary or {}),
        auto_publish=auto_publish,
    )
    return {"retrieval_index_entry": row, "lookup_map": lookup_map, "handoff_entry": entry}


def _graph_refs_from_envelope_v1(
    envelope: Mapping[str, Any],
    pins: Mapping[str, Any],
) -> tuple[str | None, str | None]:
    addressing = envelope.get("addressing")
    entity_id: str | None = None
    link_id: str | None = None
    if isinstance(addressing, dict):
        entity_id = addressing.get("org_entity_id")
        if entity_id is not None:
            entity_id = str(entity_id).strip() or None
        link_id = addressing.get("org_link_id")
        if link_id is not None:
            link_id = str(link_id).strip() or None
    return entity_id, link_id


def apply_retrieval_graph_binding_to_query_v1(
    *,
    session: Session,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    workload_class: str,
    execution_partition: str,
    hits: list[dict[str, Any]],
    omissions: list[dict[str, Any]],
    replay_pins: Mapping[str, Any],
    temporal_scope: Mapping[str, Any] | None,
    row: Any,
) -> dict[str, Any]:
    """Bind Phase 04 graph artifacts; ``RD-GRAPH-ORPHAN`` + ``evidence_candidate_only`` law."""
    wl = str(workload_class)
    entity_id_raw, link_id_raw = _graph_refs_from_envelope_v1(envelope, replay_pins)
    bind_required = wl in _GRAPH_SCOPED_WORKLOADS_V1 or bool(entity_id_raw or link_id_raw)
    replay_id = str(
        replay_pins.get("replay_identity")
        or replay_pins.get("retrieval_replay_identity")
        or getattr(row, "replay_identity", "")
        or ""
    ).strip()

    entity: CortexOrgEntity | None = None
    link: CortexOrgLink | None = None
    if entity_id_raw:
        try:
            entity = load_org_entity_v1(session, tenant_id=tenant_id, org_entity_id=entity_id_raw)
        except RetrievalGraphBindingError:
            entity = None
        if entity is None:
            record_retrieval_graph_bind_failure_v1(
                tenant_id=str(tenant_id), reason="entity_not_found", ref_kind="org_entity_id"
            )
    if link_id_raw:
        try:
            link = load_org_link_v1(session, tenant_id=tenant_id, org_link_id=link_id_raw)
        except RetrievalGraphBindingError:
            link = None
        if link is None:
            record_retrieval_graph_bind_failure_v1(
                tenant_id=str(tenant_id), reason="link_not_found", ref_kind="org_link_id"
            )

    entity_orphan = bind_required and bool(entity_id_raw) and is_org_entity_orphan_v1(entity)
    link_orphan = bind_required and bool(link_id_raw) and is_org_link_orphan_v1(
        session, tenant_id=tenant_id, link=link
    )
    if entity_orphan or link_orphan:
        record_retrieval_graph_orphan_detected_v1(
            tenant_id=str(tenant_id),
            reason="orphan_entity" if entity_orphan else "orphan_link",
            ref_kind="org_entity_id" if entity_orphan else "org_link_id",
            ref_value=entity_id_raw or link_id_raw,
        )

    out_omissions = list(omissions)
    out_omissions.extend(
        list_graph_orphan_omissions_v1(
            upstream_triggers=envelope.get("upstream_triggers")
            if isinstance(envelope.get("upstream_triggers"), dict)
            else None,
            entity_orphan=entity_orphan,
            link_orphan=link_orphan,
            bind_required=bind_required,
        )
    )
    out_omissions.extend(
        list_export_sequence_pin_violations_v1(
            replay_pins=replay_pins,
            temporal_scope=temporal_scope,
            workload_class=wl,
        )
    )

    binding_envelope: dict[str, Any] = {
        "schema_version": PHASE07_RETRIEVAL_GRAPH_BINDING_RUNTIME_SCHEMA_VERSION,
        "bind_state": "skipped",
        "org_entity_id": entity_id_raw,
        "org_link_id": link_id_raw,
        "graph_scope_queries": sorted(_GRAPH_SCOPE_QUERY_KINDS_V1),
    }
    graph_scope: dict[str, Any] = {}
    out_hits = list(hits)

    candidate_only = False
    if link is not None:
        legality = classify_org_link_authority_for_retrieval_v1(
            str(link.link_authority),
            execution_partition=execution_partition,
        )
        candidate_only = legality == RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1

    if replay_id and (entity is not None or link is not None) and not entity_orphan and not link_orphan:
        lookup_map = build_graph_handoff_lookup_map_v1(
            entity=entity,
            link=link,
            replay_identity=replay_id,
            execution_partition=execution_partition,
        )
        binding_envelope = {**lookup_map, "bind_state": "bound"}
        graph_scope = {
            "entity_kind": str(entity.entity_kind) if entity else None,
            "link_type": str(link.link_type) if link else None,
            "link_authority": str(link.link_authority) if link else None,
        }
        if candidate_only and execution_partition.strip().lower() == "authoritative":
            out_hits = apply_candidate_link_legality_to_hits_v1(
                out_hits,
                evidence_legality_class=RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1,
            )
        for hit in out_hits:
            prov = dict(hit.get("provenance") or {})
            if entity is not None:
                prov["org_entity_id"] = str(entity.id)
            if link is not None:
                prov["org_link_id"] = str(link.id)
                prov["link_authority"] = str(link.link_authority)
            prov["graph_binding_state"] = "bound"
            hit["provenance"] = prov
    elif bind_required and (entity_id_raw or link_id_raw) and (entity is None or link is None):
        binding_envelope["bind_state"] = "failed"
    elif entity_orphan or link_orphan:
        binding_envelope["bind_state"] = "orphan"
    elif candidate_only:
        binding_envelope["bind_state"] = "candidate_only"

    return {
        "hits": out_hits,
        "omissions": out_omissions,
        "graph_binding_envelope": binding_envelope,
        "graph_scope": graph_scope,
    }


def build_retrieval_graph_binding_catalog_v1() -> dict[str, Any]:
    """Admin graph scope debugger catalog."""
    return {
        "retrieval_graph_binding_runtime_schema_version": (
            PHASE07_RETRIEVAL_GRAPH_BINDING_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_GRAPH01_GATE_ID_V1,
        "spec_ref": RETRIEVAL_GRAPH_BINDING_SPEC_REF_V1,
        "rules": [
            {
                "id": RET_GRAPH01_RULE_ID_V1,
                "text": "Authoritative partition reads authoritative org links only as authoritative evidence",
            },
            {
                "id": RET_GRAPH02_RULE_ID_V1,
                "text": "org_entity_id and org_link_id map to deterministic retrieval_lookup_id",
            },
            {
                "id": RET_GRAPH03_RULE_ID_V1,
                "text": "Candidate links → evidence_candidate_only or RD-GRAPH-ORPHAN omission",
            },
        ],
        "graph_scope_query_kinds": sorted(_GRAPH_SCOPE_QUERY_KINDS_V1),
        "graph_scoped_workloads": sorted(_GRAPH_SCOPED_WORKLOADS_V1),
        "graph_addressing_ref_kinds": sorted(_GRAPH_ADDRESSING_REF_KINDS_V1),
        "rd_graph_orphan_code": RETRIEVAL_RD_GRAPH_ORPHAN_V1,
        "observability": {
            "orphan_metric": "retrieval_graph_orphan_detected_total",
            "bind_failure_metric": "retrieval_graph_bind_failures_total",
        },
    }


def _graph_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_GRAPH01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_graph01_entity_link_addressing_static() -> dict[str, Any]:
    """**G-P07-GRAPH-01** — entity/link mat addressing + orphan + candidate law."""
    errors: list[str] = []
    if len(_GRAPH_SCOPE_QUERY_KINDS_V1) < 4:
        errors.append("graph_scope_query_kind_count")
    replay = "replay-graph-static"
    eid = "00000000-0000-4000-8000-000000000099"
    lid = "00000000-0000-4000-8000-000000000088"
    le = map_graph_ref_to_retrieval_lookup_id_v1(
        ref_kind="org_entity_id", ref_value=eid, replay_identity=replay
    )
    ll = map_graph_ref_to_retrieval_lookup_id_v1(
        ref_kind="org_link_id", ref_value=lid, replay_identity=replay
    )
    if not le.startswith("sha256:") or le == ll:
        errors.append("lookup_id_shape_or_collision")
    ent_body = build_org_entity_ref_body_v1(org_entity_id=eid)
    if ent_body.get("org_entity_id") != eid:
        errors.append("org_entity_ref_body")
    cand = classify_org_link_authority_for_retrieval_v1(
        "candidate", execution_partition="authoritative"
    )
    if cand != RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1:
        errors.append("candidate_classification")
    orphan_rows = list_graph_orphan_omissions_v1(
        upstream_triggers={"orphan_artifacts": True},
        entity_orphan=False,
        link_orphan=False,
        bind_required=False,
    )
    if not orphan_rows or orphan_rows[0].get("retrieval_omission_class") != RETRIEVAL_RD_GRAPH_ORPHAN_V1:
        errors.append("rd_graph_orphan_upstream")
    pin_rows = list_export_sequence_pin_violations_v1(
        replay_pins={}, temporal_scope=None, workload_class="ownership_continuity"
    )
    if not pin_rows:
        errors.append("export_sequence_pin_expected")
    hits = apply_candidate_link_legality_to_hits_v1(
        [{"provenance": {}}], evidence_legality_class=RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1
    )
    if hits[0].get("evidence_legality_class") != RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1:
        errors.append("candidate_hit_legality")
    cat = build_retrieval_graph_binding_catalog_v1()
    if cat["gate_id"] != GP07_GRAPH01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _graph_meta("gp07_graph01_entity_link_addressing", errors)
