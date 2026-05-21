"""Phase 04 Step 13 — OrgGraphProjectionV1 export for Phase 05 handoff (P04-13).

Normative: `DOCS/cortex/04-identity/phase-04-graph-boundary-doctrine.md`,
`DOCS/cortex/04-identity/phase-04-graph-projection-export-doctrine.md`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.cortex_org_primitive_instance import CortexOrgPrimitiveInstance

ORG_GRAPH_PROJECTION_SCHEMA_VERSION: Final[int] = 1
ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF: Final[str] = "phase04-step13-org-graph-projection-v1"

_FORBIDDEN_EXPORT_SUBSTRINGS_LOWER: Final[tuple[str, ...]] = (
    "cortex_canonical_transform",
    "canonical_transform_materialization",
    "transform_materialization",
)

_NODE_KINDS: Final[frozenset[str]] = frozenset({"org_entity", "org_primitive"})
_EDGE_KINDS: Final[frozenset[str]] = frozenset({"org_meaning_link"})


def _dt_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat()
    return value.isoformat()


def org_graph_projection_canonical_json_bytes(projection: dict[str, Any]) -> bytes:
    """Deterministic UTF-8 JSON for hashing (inner projection only, no hash field)."""
    payload = {k: v for k, v in projection.items() if k != "stable_hash_sha256"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def org_graph_projection_stable_hash_sha256(projection: dict[str, Any]) -> str:
    return hashlib.sha256(org_graph_projection_canonical_json_bytes(projection)).hexdigest()


def validate_org_graph_projection_v1_shape(projection: dict[str, Any]) -> list[str]:
    """Structural validation errors (empty list => valid)."""
    errors: list[str] = []
    if projection.get("projection_schema_version") != ORG_GRAPH_PROJECTION_SCHEMA_VERSION:
        errors.append("projection_schema_version_must_be_1")
    tid = projection.get("tenant_id")
    if not isinstance(tid, str) or len(tid) < 32:
        errors.append("tenant_id_invalid")
    ref = projection.get("engine_build_ref")
    if not isinstance(ref, str) or not ref.strip():
        errors.append("engine_build_ref_invalid")
    nodes = projection.get("nodes")
    edges = projection.get("edges")
    if not isinstance(nodes, list):
        errors.append("nodes_not_list")
        return errors
    if not isinstance(edges, list):
        errors.append("edges_not_list")
        return errors

    seen_node_ids: set[str] = set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            errors.append(f"node_{i}_not_object")
            continue
        k = n.get("kind")
        if k not in _NODE_KINDS:
            errors.append(f"node_{i}_bad_kind")
        nid = n.get("id")
        if not isinstance(nid, str):
            errors.append(f"node_{i}_id_invalid")
        else:
            if nid in seen_node_ids:
                errors.append(f"duplicate_node_id:{nid}")
            seen_node_ids.add(nid)
        if k == "org_entity":
            for f in ("entity_kind", "identity_key_fingerprint", "lifecycle_state"):
                if f not in n:
                    errors.append(f"node_{i}_missing_{f}")
            if "tombstoned_at" not in n:
                errors.append(f"node_{i}_missing_tombstoned_at")
        elif k == "org_primitive":
            for f in ("org_entity_id", "primitive_kind", "primitive_key", "lifecycle_state"):
                if f not in n:
                    errors.append(f"node_{i}_missing_{f}")

    seen_edge_ids: set[str] = set()
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            errors.append(f"edge_{i}_not_object")
            continue
        if e.get("kind") not in _EDGE_KINDS:
            errors.append(f"edge_{i}_bad_kind")
        eid = e.get("id")
        if not isinstance(eid, str):
            errors.append(f"edge_{i}_id_invalid")
        else:
            if eid in seen_edge_ids:
                errors.append(f"duplicate_edge_id:{eid}")
            seen_edge_ids.add(eid)
        for f in (
            "link_type",
            "source_entity_id",
            "target_entity_id",
            "link_class",
            "link_authority",
            "confidence_class",
            "evidence_raw_record_ids",
            "link_row_stable_id",
        ):
            if f not in e:
                errors.append(f"edge_{i}_missing_{f}")
        ev_ids = e.get("evidence_raw_record_ids")
        if isinstance(ev_ids, list):
            if not all(isinstance(x, int) for x in ev_ids):
                errors.append(f"edge_{i}_evidence_not_ints")
            elif ev_ids != sorted(ev_ids):
                errors.append(f"edge_{i}_evidence_not_sorted")
        elif "evidence_raw_record_ids" in e:
            errors.append(f"edge_{i}_evidence_not_list")
        sid = e.get("link_row_stable_id")
        if sid is not None and (not isinstance(sid, str) or not sid.strip()):
            errors.append(f"edge_{i}_link_row_stable_id_invalid")

    node_ids_in_order = [
        str(n["id"])
        for n in nodes
        if isinstance(n, dict) and isinstance(n.get("id"), str)
    ]
    if sorted(node_ids_in_order) != node_ids_in_order:
        errors.append("nodes_not_sorted_by_id")
    edge_ids_in_order = [
        str(e["id"])
        for e in edges
        if isinstance(e, dict) and isinstance(e.get("id"), str)
    ]
    if sorted(edge_ids_in_order) != edge_ids_in_order:
        errors.append("edges_not_sorted_by_id")

    return errors


def verify_org_graph_export_forbidden_leakage(projection: dict[str, Any]) -> list[str]:
    """Return errors if canonical JSON contains forbidden Phase-03 topology tokens."""
    raw = org_graph_projection_canonical_json_bytes(projection).decode("utf-8").lower()
    return [f"forbidden_token:{t}" for t in _FORBIDDEN_EXPORT_SUBSTRINGS_LOWER if t in raw]


def build_org_graph_projection_v1(
    db: Session, *, tenant_id: uuid.UUID
) -> dict[str, Any]:
    """Build inner OrgGraphProjectionV1 document (no stable_hash_sha256 field)."""
    entities = list(
        db.scalars(
            select(CortexOrgEntity)
            .where(CortexOrgEntity.tenant_id == tenant_id)
            .order_by(CortexOrgEntity.id.asc())
        ).all()
    )
    primitives = list(
        db.scalars(
            select(CortexOrgPrimitiveInstance)
            .where(CortexOrgPrimitiveInstance.tenant_id == tenant_id)
            .order_by(CortexOrgPrimitiveInstance.id.asc())
        ).all()
    )
    links = list(
        db.scalars(
            select(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
            )
            .order_by(CortexOrgLink.id.asc())
        ).all()
    )

    nodes: list[dict[str, Any]] = []
    for ent in entities:
        nodes.append(
            {
                "kind": "org_entity",
                "id": str(ent.id),
                "entity_kind": ent.entity_kind,
                "identity_key_fingerprint": ent.identity_key_fingerprint,
                "lifecycle_state": ent.lifecycle_state,
                "tombstoned_at": _dt_iso(ent.tombstoned_at),
            }
        )
    for pr in primitives:
        nodes.append(
            {
                "kind": "org_primitive",
                "id": str(pr.id),
                "org_entity_id": str(pr.org_entity_id),
                "primitive_kind": pr.primitive_kind,
                "primitive_key": pr.primitive_key,
                "lifecycle_state": pr.lifecycle_state,
            }
        )
    nodes.sort(key=lambda x: str(x["id"]))

    edges: list[dict[str, Any]] = []
    for lk in links:
        ev = [int(x) for x in (lk.evidence_raw_record_ids or [])]
        ev.sort()
        promo = str(lk.promotion_policy_id) if lk.promotion_policy_id else None
        edges.append(
            {
                "kind": "org_meaning_link",
                "id": str(lk.id),
                "link_type": lk.link_type,
                "source_entity_id": str(lk.source_entity_id),
                "target_entity_id": str(lk.target_entity_id),
                "link_class": lk.link_class,
                "link_authority": lk.link_authority,
                "confidence_class": lk.confidence_class,
                "evidence_raw_record_ids": ev,
                "rule_id": lk.rule_id,
                "valid_from": _dt_iso(lk.valid_from),
                "valid_to": _dt_iso(lk.valid_to),
                "revoked_at": _dt_iso(lk.revoked_at),
                "supersedes_link_id": str(lk.supersedes_link_id) if lk.supersedes_link_id else None,
                "promoted_from_candidate_id": (
                    str(lk.promoted_from_candidate_id) if lk.promoted_from_candidate_id else None
                ),
                "promotion_policy_id": promo,
                "link_row_stable_id": str(lk.id),
            }
        )
    edges.sort(key=lambda x: str(x["id"]))

    return {
        "projection_schema_version": ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": nodes,
        "edges": edges,
    }


def build_org_graph_projection_export_document(
    db: Session, *, tenant_id: uuid.UUID
) -> dict[str, Any]:
    """Outer document: inner projection + stable_hash_sha256 (admin / handoff)."""
    inner = build_org_graph_projection_v1(db, tenant_id=tenant_id)
    h = org_graph_projection_stable_hash_sha256(inner)
    return {
        "org_graph_projection_schema_version": ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "projection": inner,
        "stable_hash_sha256": h,
    }


def run_graph_projection_export_for_pipeline_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Single phase-04 transform: direct projection export (no org-link replay job, P1 step 9)."""
    doc = build_org_graph_projection_export_document(db, tenant_id=tenant_id)
    stable = str(doc.get("stable_hash_sha256") or "").strip()
    if not stable:
        msg = "graph_projection_missing_stable_hash"
        raise ValueError(msg)
    inner = doc.get("projection")
    projection = inner if isinstance(inner, dict) else {}
    nodes = projection.get("nodes")
    edges = projection.get("edges")
    node_count = len(nodes) if isinstance(nodes, list) else 0
    edge_count = len(edges) if isinstance(edges, list) else 0
    return {
        "graph_projection_stable_hash_sha256": stable,
        "node_count": node_count,
        "edge_count": edge_count,
        "org_graph_projection_schema_version": doc.get("org_graph_projection_schema_version"),
        "engine_build_ref": doc.get("engine_build_ref"),
    }


PROJECTION_PREVIEW_SCHEMA_VERSION: Final[int] = 1
PROJECTION_PREVIEW_TOP_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "projection_preview_schema_version",
        "projection_schema_version",
        "tenant_id",
        "engine_build_ref",
        "node_counts",
        "edge_counts",
        "edge_class_histogram",
        "projection_hash",
        "generated_at",
        "replay_source",
    }
)


def build_org_graph_projection_preview_metadata(
    db: Session, *, tenant_id: uuid.UUID
) -> dict[str, Any]:
    """§14 / **G-P04-25** — counts + hashes only (no neighbor lists / full edge arrays)."""
    inner = build_org_graph_projection_v1(db, tenant_id=tenant_id)
    nodes = inner.get("nodes") or []
    edges = inner.get("edges") or []
    node_counts: dict[str, int] = {}
    for n in nodes:
        if isinstance(n, dict):
            k = str(n.get("kind") or "unknown")
            node_counts[k] = node_counts.get(k, 0) + 1
    edge_class_histogram: dict[str, int] = {}
    for e in edges:
        if isinstance(e, dict):
            lt = str(e.get("link_type") or "unknown")
            edge_class_histogram[lt] = edge_class_histogram.get(lt, 0) + 1
    h = org_graph_projection_stable_hash_sha256(inner)
    job_rows = list(
        db.scalars(
            select(CortexOrgLinkReplayJob)
            .where(
                CortexOrgLinkReplayJob.tenant_id == tenant_id,
                CortexOrgLinkReplayJob.status == "completed",
            )
            .order_by(CortexOrgLinkReplayJob.completed_at.desc())
            .limit(5)
        ).all()
    )
    replay_ids = [str(j.id) for j in job_rows]
    pinned = [j.pinned_rule_version for j in job_rows if j.pinned_rule_version]
    return {
        "projection_preview_schema_version": PROJECTION_PREVIEW_SCHEMA_VERSION,
        "projection_schema_version": inner.get("projection_schema_version"),
        "tenant_id": str(tenant_id),
        "engine_build_ref": inner.get("engine_build_ref"),
        "node_counts": dict(sorted(node_counts.items())),
        "edge_counts": {
            "total": len(edges),
            "by_class": dict(sorted(edge_class_histogram.items())),
        },
        "edge_class_histogram": dict(sorted(edge_class_histogram.items())),
        "projection_hash": h,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "replay_source": {
            "recent_org_link_replay_job_ids": replay_ids,
            "pinned_rule_versions": pinned[:5],
        },
    }


def verify_gp04_25_projection_preview_shape_static(payload: object) -> dict[str, Any]:
    """Static / tenant helper for **G-P04-25**."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        errors.append("preview_not_object")
        return {
            "id": "G-P04-25-shape",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"errors": errors},
        }
    keys = set(payload.keys())
    if not keys.issubset(PROJECTION_PREVIEW_TOP_LEVEL_KEYS):
        errors.append(f"unexpected_keys:{sorted(keys - PROJECTION_PREVIEW_TOP_LEVEL_KEYS)}")
    for forbidden in ("nodes", "edges", "projection"):
        if forbidden in payload:
            errors.append(f"forbidden_large_field:{forbidden}")
    ec = payload.get("edge_counts")
    if not isinstance(ec, dict):
        errors.append("edge_counts_not_object")
    elif isinstance(ec.get("by_class"), list):
        errors.append("edge_counts_by_class_must_be_map")
    passed = len(errors) == 0
    return {
        "id": "G-P04-25-shape",
        "name": "projection_preview_allowlist",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp04_10_graph_boundary_export_contract_static() -> dict[str, Any]:
    """G-P04-10 — static schema + forbidden-token scan on a minimal valid projection."""
    errors: list[str] = []
    minimal: dict[str, Any] = {
        "projection_schema_version": ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
        "tenant_id": str(uuid.UUID(int=0)),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": str(uuid.UUID(int=1)),
                "entity_kind": "human_actor",
                "identity_key_fingerprint": "fp",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            }
        ],
        "edges": [],
    }
    errors.extend(validate_org_graph_projection_v1_shape(minimal))
    errors.extend(verify_org_graph_export_forbidden_leakage(minimal))
    h1 = org_graph_projection_stable_hash_sha256(minimal)
    h2 = org_graph_projection_stable_hash_sha256(minimal)
    if h1 != h2:
        errors.append("hash_not_idempotent")
    passed = len(errors) == 0
    return {
        "id": "G-P04-10",
        "name": "org_graph_projection_boundary_export_contract",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "sample_hash_prefix": h1[:16] if h1 else ""},
    }


def verify_gp04_exp01_export_hash_determinism_static() -> dict[str, Any]:
    """G-P04-EXP-01 — static slice: fixture projection hashes stable across rebuild."""
    errors: list[str] = []
    inner: dict[str, Any] = {
        "projection_schema_version": ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
        "tenant_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "p04-13-exp01")),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "entity_kind": "team",
                "identity_key_fingerprint": "abc",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            },
            {
                "kind": "org_primitive",
                "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "org_entity_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "primitive_kind": "work_episode",
                "primitive_key": "0" * 64,
                "lifecycle_state": "active",
            },
        ],
        "edges": [
            {
                "kind": "org_meaning_link",
                "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "link_type": "PersonaBelongsToHuman",
                "source_entity_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "target_entity_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "link_class": "authoritative",
                "link_authority": "authoritative",
                "confidence_class": "test",
                "evidence_raw_record_ids": [1, 2, 3],
                "rule_id": None,
                "valid_from": None,
                "valid_to": None,
                "revoked_at": None,
                "supersedes_link_id": None,
                "promoted_from_candidate_id": None,
                "promotion_policy_id": None,
                "link_row_stable_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            }
        ],
    }
    inner["nodes"].sort(key=lambda x: str(x["id"]))
    inner["edges"].sort(key=lambda x: str(x["id"]))
    errors.extend(validate_org_graph_projection_v1_shape(inner))
    if errors:
        pass
    else:
        a = org_graph_projection_stable_hash_sha256(inner)
        b = org_graph_projection_stable_hash_sha256(
            {
                **inner,
                "nodes": sorted(inner["nodes"], key=lambda z: str(z["id"])),
                "edges": sorted(inner["edges"], key=lambda z: str(z["id"])),
            }
        )
        if a != b:
            errors.append("fixture_hash_mismatch")
    passed = len(errors) == 0
    return {"passed": passed, "detail": {"errors": errors}}


def verify_org_graph_projection_twice_same_hash(
    db: Session, *, tenant_id: uuid.UUID
) -> dict[str, Any]:
    """Recompute tenant export twice; hashes must match."""
    a = build_org_graph_projection_export_document(db, tenant_id=tenant_id)
    b = build_org_graph_projection_export_document(db, tenant_id=tenant_id)
    ha = str(a.get("stable_hash_sha256") or "")
    hb = str(b.get("stable_hash_sha256") or "")
    inner_a = a.get("projection")
    inner_b = b.get("projection")
    passed = ha == hb and ha != "" and inner_a == inner_b
    detail: dict[str, Any] = {"hash_a": ha, "hash_b": hb, "inner_equal": inner_a == inner_b}
    if isinstance(inner_a, dict):
        detail["shape_errors"] = validate_org_graph_projection_v1_shape(inner_a)
        detail["leak_errors"] = verify_org_graph_export_forbidden_leakage(inner_a)
    passed = passed and detail.get("shape_errors") == [] and detail.get("leak_errors") == []
    return {"passed": passed, "detail": detail}
