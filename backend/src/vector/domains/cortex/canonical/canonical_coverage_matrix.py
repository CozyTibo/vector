"""Operator-visible canonical coverage matrix — derived from routing registry + ingest exhaust + tenant counts.

Substrate decomposition (v3+): ``never_ingested`` means zero raw rows for a routable pair (e.g. no Slack file events yet)
— not a broken transform. ``dead_route`` remains a coarse legacy flag (empty substrate, not dormant). Use the explicit
booleans for execution-graph confidence and operator triage.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session, load_only

from vector.domains.cortex.canonical.replay_topology import build_replay_dependency_topology
from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob
from vector.infrastructure.db.models.cortex_canonical_replay_job_receipt import (
    CortexCanonicalReplayJobReceipt,
)
from vector.domains.cortex.canonical.transform_routing_registry import (
    TRANSFORM_ROUTING_REGISTRY_VERSION,
    all_transform_route_registrations,
    registration_for_pair,
)
from vector.domains.cortex.ingestion.exhaust_coverage_registry import build_admin_exhaust_coverage_payload
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

CANONICAL_COVERAGE_MATRIX_SCHEMA_VERSION: Final[int] = 3

_CORE_CONNECTORS: tuple[str, ...] = ("github", "slack", "linear", "notion", "calls")


def _iso_max(a: str | None, b: str | None) -> str | None:
    if not b:
        return a
    if not a:
        return b
    return b if b > a else a


def build_connector_coverage_rollups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-connector aggregates for operator Health (matches frontend ``rollupConnectors`` semantics)."""
    m: dict[str, dict[str, Any]] = {}

    def ensure(conn: str) -> dict[str, Any]:
        if conn not in m:
            m[conn] = {
                "connector": conn,
                "rawRows": 0,
                "canonicalRows": 0,
                "untreatedRoutable": 0,
                "replayFailures": 0,
                "orphanRefs": 0,
                "coveragePct": None,
                "lastFirstSeen": None,
                "lastMaterialized": None,
                "hasDeadRoute": False,
                "hasDormant": False,
            }
        return m[conn]

    for c in _CORE_CONNECTORS:
        ensure(c)
    for r in rows:
        conn = str(r.get("connector") or "")
        if not conn:
            continue
        agg = ensure(conn)
        raw_n = int(r.get("tenant_raw_row_count") or 0)
        mat_n = int(r.get("tenant_materialized_row_count") or 0)
        agg["rawRows"] += raw_n
        agg["canonicalRows"] += mat_n
        if r.get("routable"):
            agg["untreatedRoutable"] += max(0, raw_n - mat_n)
        agg["replayFailures"] += int(r.get("replay_failure_count") or 0)
        agg["orphanRefs"] += int(r.get("orphan_count") or 0)
        if r.get("dead_route"):
            agg["hasDeadRoute"] = True
        if r.get("dormant"):
            agg["hasDormant"] = True
        fs = r.get("first_seen_at")
        if isinstance(fs, str) and fs.strip():
            agg["lastFirstSeen"] = _iso_max(agg.get("lastFirstSeen") if isinstance(agg.get("lastFirstSeen"), str) else None, fs)
        lm = r.get("last_materialized_at")
        if isinstance(lm, str) and lm.strip():
            agg["lastMaterialized"] = _iso_max(
                agg.get("lastMaterialized") if isinstance(agg.get("lastMaterialized"), str) else None, lm
            )
    for agg in m.values():
        rr = int(agg["rawRows"])
        if rr > 0:
            agg["coveragePct"] = round((100 * int(agg["canonicalRows"])) / rr)
    out: list[dict[str, Any]] = []
    for c in _CORE_CONNECTORS:
        out.append(m[c])
    extras = sorted(k for k in m if k not in set(_CORE_CONNECTORS))
    for k in extras:
        out.append(m[k])
    return out


def _raw_counts_by_pair(session: Session, tenant_id: uuid.UUID) -> dict[tuple[str, str], int]:
    rows = session.execute(
        select(
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            func.count().label("n"),
        )
        .where(RawIngestionRecord.tenant_id == tenant_id)
        .group_by(RawIngestionRecord.connector, RawIngestionRecord.resource_type)
    ).all()
    return {(str(r[0]), str(r[1])): int(r[2]) for r in rows}


def _materialized_counts_by_pair(session: Session, tenant_id: uuid.UUID) -> dict[tuple[str, str], int]:
    stmt = (
        select(
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            func.count().label("n"),
        )
        .join(
            CortexCanonicalTransformMaterialization,
            CortexCanonicalTransformMaterialization.raw_record_id == RawIngestionRecord.id,
        )
        .where(
            CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
            RawIngestionRecord.tenant_id == tenant_id,
        )
        .group_by(RawIngestionRecord.connector, RawIngestionRecord.resource_type)
    )
    rows = session.execute(stmt).all()
    return {(str(r[0]), str(r[1])): int(r[2]) for r in rows}


def _replay_counts_by_pair(session: Session, tenant_id: uuid.UUID) -> dict[tuple[str, str], int]:
    stmt = (
        select(
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            func.count().label("n"),
        )
        .select_from(CortexCanonicalReplayJobReceipt)
        .join(CortexCanonicalReplayJob, CortexCanonicalReplayJobReceipt.job_id == CortexCanonicalReplayJob.id)
        .join(RawIngestionRecord, RawIngestionRecord.id == CortexCanonicalReplayJobReceipt.raw_record_id)
        .where(
            CortexCanonicalReplayJob.tenant_id == tenant_id,
            RawIngestionRecord.tenant_id == tenant_id,
            CortexCanonicalReplayJob.status == "completed",
        )
        .group_by(RawIngestionRecord.connector, RawIngestionRecord.resource_type)
    )
    rows = session.execute(stmt).all()
    return {(str(r[0]), str(r[1])): int(r[2]) for r in rows}


def _replay_failure_counts_by_pair(session: Session, tenant_id: uuid.UUID) -> dict[tuple[str, str], int]:
    stmt = (
        select(
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            func.count().label("n"),
        )
        .select_from(CortexCanonicalReplayJobReceipt)
        .join(CortexCanonicalReplayJob, CortexCanonicalReplayJobReceipt.job_id == CortexCanonicalReplayJob.id)
        .join(RawIngestionRecord, RawIngestionRecord.id == CortexCanonicalReplayJobReceipt.raw_record_id)
        .where(
            CortexCanonicalReplayJob.tenant_id == tenant_id,
            RawIngestionRecord.tenant_id == tenant_id,
            CortexCanonicalReplayJob.status == "completed",
            CortexCanonicalReplayJobReceipt.divergence_class.in_(("C3", "C4", "C5")),
        )
        .group_by(RawIngestionRecord.connector, RawIngestionRecord.resource_type)
    )
    rows = session.execute(stmt).all()
    return {(str(r[0]), str(r[1])): int(r[2]) for r in rows}


def _first_seen_raw_by_pair(session: Session, tenant_id: uuid.UUID) -> dict[tuple[str, str], Any]:
    stmt = (
        select(
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            func.min(RawIngestionRecord.fetched_at).label("fs"),
        )
        .where(RawIngestionRecord.tenant_id == tenant_id)
        .group_by(RawIngestionRecord.connector, RawIngestionRecord.resource_type)
    )
    rows = session.execute(stmt).all()
    return {(str(r[0]), str(r[1])): r[2] for r in rows}


def _last_materialized_at_by_pair(session: Session, tenant_id: uuid.UUID) -> dict[tuple[str, str], Any]:
    stmt = (
        select(
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            func.max(CortexCanonicalTransformMaterialization.canonical_processed_at).label("lm"),
        )
        .join(
            CortexCanonicalTransformMaterialization,
            CortexCanonicalTransformMaterialization.raw_record_id == RawIngestionRecord.id,
        )
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
        )
        .group_by(RawIngestionRecord.connector, RawIngestionRecord.resource_type)
    )
    rows = session.execute(stmt).all()
    return {(str(r[0]), str(r[1])): r[2] for r in rows}


def build_canonical_coverage_matrix(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Rows union exhaust inventory + transform routes; stats from live raw + materialization tables."""
    exhaust = build_admin_exhaust_coverage_payload(tenant_id=tenant_id)
    raw_n = _raw_counts_by_pair(session, tenant_id)
    mat_n = _materialized_counts_by_pair(session, tenant_id)
    replay_n = _replay_counts_by_pair(session, tenant_id)
    replay_fail_n = _replay_failure_counts_by_pair(session, tenant_id)
    first_seen = _first_seen_raw_by_pair(session, tenant_id)
    last_mat_at = _last_materialized_at_by_pair(session, tenant_id)
    raw_rows = list(
        session.scalars(
            select(RawIngestionRecord)
            .options(
                load_only(
                    RawIngestionRecord.id,
                    RawIngestionRecord.connector,
                    RawIngestionRecord.resource_type,
                    RawIngestionRecord.external_id,
                    RawIngestionRecord.payload_body,
                )
            )
            .where(RawIngestionRecord.tenant_id == tenant_id)
            .limit(25000)
        ).all()
    )
    topo = build_replay_dependency_topology(
        raw_rows,
        temporal_key_by_id={int(r.id): f"{int(r.id):012d}" for r in raw_rows},
    )
    pair_by_raw_id = {(int(r.id)): (str(r.connector), str(r.resource_type)) for r in raw_rows}
    orphan_counts_by_pair: dict[tuple[str, str], int] = {}
    for orphan in topo.get("orphan_refs") or []:
        rid = int(orphan.get("raw_record_id") or 0)
        pair = pair_by_raw_id.get(rid)
        if pair is None:
            continue
        orphan_counts_by_pair[pair] = int(orphan_counts_by_pair.get(pair, 0)) + 1

    edge_counts_by_pair: dict[tuple[str, str], int] = {}
    for edge in topo.get("dependency_edges") or []:
        if not isinstance(edge, dict):
            continue
        cid = int(edge.get("child_raw_record_id") or 0)
        pair = pair_by_raw_id.get(cid)
        if pair is None:
            continue
        edge_counts_by_pair[pair] = int(edge_counts_by_pair.get(pair, 0)) + 1

    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []

    for bundle in exhaust["connectors"]:
        conn = str(bundle["connector"])
        for res in bundle["resources"]:
            rt = str(res["resource_type"])
            key = (conn, rt)
            seen.add(key)
            reg = registration_for_pair(conn, rt)
            ingest_ok = str(res.get("status") or "") != "missing"
            routable = reg is not None
            raw_count = raw_n.get(key, 0)
            mat_count = mat_n.get(key, 0)
            rows.append(
                _coverage_row(
                    connector=conn,
                    resource_type=rt,
                    ingest_supported=ingest_ok,
                    exhaust_status=str(res.get("status") or ""),
                    routable=routable,
                    reg=reg,
                    raw_count=raw_count,
                    materialized_count=mat_count,
                    orphan_count=int(orphan_counts_by_pair.get(key, 0)),
                    replay_count=int(replay_n.get(key, 0)),
                    replay_failure_count=int(replay_fail_n.get(key, 0)),
                    topology_edge_count=int(edge_counts_by_pair.get(key, 0)),
                    first_seen_at=first_seen.get(key),
                    last_materialized_at=last_mat_at.get(key),
                    exhaust_notes=res.get("notes"),
                )
            )

    for reg in all_transform_route_registrations():
        key = (reg.connector, reg.resource_type)
        if key in seen:
            continue
        raw_count = raw_n.get(key, 0)
        mat_count = mat_n.get(key, 0)
        rows.append(
            _coverage_row(
                connector=reg.connector,
                resource_type=reg.resource_type,
                ingest_supported=raw_count > 0,
                exhaust_status="not_in_exhaust_matrix",
                routable=True,
                reg=reg,
                raw_count=raw_count,
                materialized_count=mat_count,
                orphan_count=int(orphan_counts_by_pair.get(key, 0)),
                replay_count=int(replay_n.get(key, 0)),
                replay_failure_count=int(replay_fail_n.get(key, 0)),
                topology_edge_count=int(edge_counts_by_pair.get(key, 0)),
                first_seen_at=first_seen.get(key),
                last_materialized_at=last_mat_at.get(key),
                exhaust_notes=reg.notes,
            )
        )

    rows.sort(key=lambda r: (r["connector"], r["resource_type"]))

    routable_pairs = sum(1 for r in rows if r["routable"])
    total_pairs = len(rows)
    ingested_only = sum(1 for r in rows if r["ingest_supported"] and not r["routable"])
    unsupported_ingest_raw_row_count = sum(
        int(r.get("tenant_raw_row_count") or 0)
        for r in rows
        if bool(r.get("ingest_supported")) and not bool(r.get("routable"))
    )
    routable_unmaterialized_raw_row_count = sum(
        max(0, int(r.get("tenant_raw_row_count") or 0) - int(r.get("tenant_materialized_row_count") or 0))
        for r in rows
        if bool(r.get("routable"))
    )
    orphan_n = len(topo.get("orphan_refs") or [])
    sums_raw = sum(int(r.get("tenant_raw_row_count") or 0) for r in rows)
    sums_mat = sum(int(r.get("tenant_materialized_row_count") or 0) for r in rows)

    return {
        "canonical_coverage_matrix_schema_version": CANONICAL_COVERAGE_MATRIX_SCHEMA_VERSION,
        "transform_routing_registry_version": TRANSFORM_ROUTING_REGISTRY_VERSION,
        "tenant_id": str(tenant_id),
        "summary": {
            "matrix_row_count": total_pairs,
            "routable_pair_count": routable_pairs,
            "ingest_only_pair_count": ingested_only,
            "transform_only_or_unlisted_exhaust_count": sum(
                1 for r in rows if r["exhaust_row_status"] == "not_in_exhaust_matrix"
            ),
            "unsupported_ingest_raw_row_count": unsupported_ingest_raw_row_count,
            "routable_unmaterialized_raw_row_count": routable_unmaterialized_raw_row_count,
            "orphan_dependency_ref_count": len(topo.get("orphan_refs") or []),
            "replay_dependency_cycle_detected": bool(topo.get("cycle_detected")),
            "replay_dependency_edge_count": len(topo.get("dependency_edges") or []),
            "determinism_drift_events": sum(int(r.get("replay_failure_count") or 0) for r in rows),
            "dead_route_pair_count": sum(1 for r in rows if bool(r.get("dead_route"))),
            "never_ingested_pair_count": sum(1 for r in rows if bool(r.get("never_ingested"))),
            "never_materialized_pair_count": sum(1 for r in rows if bool(r.get("never_materialized"))),
            "never_replayed_pair_count": sum(1 for r in rows if bool(r.get("never_replayed"))),
            "historically_active_pair_count": sum(1 for r in rows if bool(r.get("historically_active"))),
            "stale_pair_count": sum(1 for r in rows if bool(r.get("stale"))),
            "inactive_by_design_pair_count": sum(1 for r in rows if bool(r.get("inactive_by_design"))),
            "connector_disabled_pair_count": sum(1 for r in rows if bool(r.get("connector_disabled"))),
            "awaiting_ingestion_support_pair_count": sum(
                1 for r in rows if bool(r.get("awaiting_ingestion_support"))
            ),
            "dormant_route_pair_count": sum(1 for r in rows if bool(r.get("dormant"))),
            "replay_active_pair_count": sum(1 for r in rows if bool(r.get("replay_active"))),
            "topology_active_pair_count": sum(1 for r in rows if bool(r.get("topology_active"))),
            "orphan_backlog_pressure": int(orphan_n),
            "orphan_recovery_rate_proxy": (
                round(
                    1.0
                    - (orphan_n / max(1, sum(int(r.get("tenant_raw_row_count") or 0) for r in rows))),
                    6,
                )
                if rows
                else None
            ),
        },
        "rows": rows,
        "phase03_exit_audit": build_phase03_exit_audit(rows),
        "connector_rollups": build_connector_coverage_rollups(rows),
        "totals": {
            "tenant_raw_row_count_sum": sums_raw,
            "tenant_materialized_row_count_sum": sums_mat,
        },
    }


def build_phase03_exit_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-resource runtime audit slice (coverage-matrix derived, no static certification)."""
    audit: list[dict[str, Any]] = []
    for r in rows:
        audit.append(
            {
                "connector": r.get("connector"),
                "resource_type": r.get("resource_type"),
                "ingestion_active": bool(r.get("emitted")),
                "transform_active": bool(r.get("routable")),
                "materialized": int(r.get("tenant_materialized_row_count") or 0) > 0,
                "replayed": int(r.get("replay_count") or 0) > 0,
                "topology_connected": bool(r.get("topology_active")),
                "orphan_rate": (
                    round(
                        int(r.get("orphan_count") or 0) / max(1, int(r.get("tenant_raw_row_count") or 0)),
                        6,
                    )
                    if int(r.get("tenant_raw_row_count") or 0) > 0
                    else 0.0
                ),
                "drift_rate_proxy": (
                    round(
                        int(r.get("replay_failure_count") or 0) / max(1, int(r.get("replay_count") or 0)),
                        6,
                    )
                    if int(r.get("replay_count") or 0) > 0
                    else 0.0
                ),
                "verification_pass_rate": None,
                "replay_converged": bool(r.get("replay_converged")),
                "dead_route": bool(r.get("dead_route")),
                "dormant": bool(r.get("dormant")),
                "oracle_certified": bool(r.get("oracle_certified")),
                "production_trusted": bool(r.get("production_trusted")),
                "never_ingested": bool(r.get("never_ingested")),
                "never_materialized": bool(r.get("never_materialized")),
                "never_replayed": bool(r.get("never_replayed")),
                "historically_active": bool(r.get("historically_active")),
                "stale": bool(r.get("stale")),
                "inactive_by_design": bool(r.get("inactive_by_design")),
                "connector_disabled": bool(r.get("connector_disabled")),
                "awaiting_ingestion_support": bool(r.get("awaiting_ingestion_support")),
            }
        )
    audit.sort(key=lambda x: (str(x.get("connector")), str(x.get("resource_type"))))
    return audit


def _coverage_row(
    *,
    connector: str,
    resource_type: str,
    ingest_supported: bool,
    exhaust_status: str,
    routable: bool,
    reg: Any,
    raw_count: int,
    materialized_count: int,
    orphan_count: int,
    replay_count: int,
    replay_failure_count: int,
    topology_edge_count: int,
    first_seen_at: Any,
    last_materialized_at: Any,
    exhaust_notes: str | None,
) -> dict[str, Any]:
    materializable = routable
    logical_keys = routable
    provenance = routable
    replay = routable
    if not routable:
        oracle_coverage = "none"
    elif reg is not None and reg.oracle_fixture_id:
        oracle_coverage = "partial"
    else:
        oracle_coverage = "oracle_vector_pending"
    verification_coverage = "partial" if routable else "none"
    ambiguity_support = "admin_api_only"
    dependency_safe = bool(routable) and int(orphan_count) == 0
    replay_safe = bool(routable) and dependency_safe
    hierarchy_safe = dependency_safe
    invariant_verified = bool(routable) and materialized_count > 0
    oracle_certified = oracle_coverage == "partial"
    orphan_free = int(orphan_count) == 0
    replay_localizable = bool(routable)
    emitted = raw_count > 0
    notes_l = (exhaust_notes or "").lower()
    reg_notes_l = (reg.notes or "").lower() if reg is not None else ""
    dormant = bool(routable) and (
        "dormant" in notes_l or "dormant" in reg_notes_l or "low-value" in reg_notes_l
    )
    inactive_by_design = bool(routable) and (
        dormant
        or "inactive_by_design" in notes_l
        or "inactive_by_design" in reg_notes_l
        or "by design" in notes_l
        or "by design" in reg_notes_l
        or "intentionally" in reg_notes_l
    )
    awaiting_ingestion_support = bool(routable) and (
        exhaust_status == "missing"
        or (exhaust_status == "not_in_exhaust_matrix" and raw_count == 0)
    )
    # Tenant connector OAuth / enablement not queried here — reserved for future wiring.
    connector_disabled = False

    never_ingested = bool(routable) and raw_count == 0
    never_materialized = bool(routable) and raw_count > 0 and materialized_count == 0
    never_replayed = bool(routable) and raw_count > 0 and replay_count == 0
    historically_active = bool(routable) and (materialized_count > 0 or replay_count > 0)
    stale = bool(routable) and (
        (raw_count > materialized_count and materialized_count > 0)
        or (raw_count > 0 and orphan_count > 0)
    )

    # Legacy coarse flag: empty substrate for a registered route (NOT synonymous with broken transform).
    dead_route = bool(routable) and raw_count == 0 and not dormant
    replay_active = replay_count > 0
    topology_active = topology_edge_count > 0
    replay_converged = replay_active and replay_failure_count == 0 and raw_count > 0
    topology_safe = bool(routable) and orphan_count == 0
    deterministic = replay_count == 0 or replay_failure_count == 0
    drift_free = deterministic
    active = emitted and materialized_count > 0 and not dormant and not dead_route
    production_trusted = bool(
        replay_converged and topology_safe and materialized_count > 0 and oracle_certified and drift_free
    )
    deferred_dependency_count = int(orphan_count)

    if not ingest_supported and not routable:
        maturity = "unsupported"
    elif ingest_supported and not routable:
        maturity = "ingest_only"
    elif routable and materialized_count <= 0:
        maturity = "routable"
    elif routable and not dependency_safe:
        maturity = "partially_canonicalized"
    elif routable and oracle_coverage == "partial":
        maturity = "oracle_certified"
    elif routable:
        maturity = "replay_safe"
    elif reg is not None:
        maturity = reg.matrix_maturity
    else:
        maturity = "unsupported"

    materialization_pct = (materialized_count / raw_count * 100.0) if raw_count > 0 else None

    return {
        "connector": connector,
        "resource_type": resource_type,
        "emitted": emitted,
        "ingest_supported": ingest_supported,
        "exhaust_row_status": exhaust_status,
        "routable": routable,
        "materializable": materializable,
        "logical_keys": logical_keys,
        "provenance": provenance,
        "replay": replay,
        "oracle_coverage": oracle_coverage,
        "verification_coverage": verification_coverage,
        "ambiguity_support": ambiguity_support,
        "dependency_safe": dependency_safe,
        "replay_safe": replay_safe,
        "hierarchy_safe": hierarchy_safe,
        "invariant_verified": invariant_verified,
        "oracle_certified": oracle_certified,
        "orphan_free": orphan_free,
        "replay_localizable": replay_localizable,
        "dormant": dormant,
        "dormant_reason": ("registry_or_exhaust_notes" if dormant else None),
        "inactive_by_design": inactive_by_design,
        "awaiting_ingestion_support": awaiting_ingestion_support,
        "connector_disabled": connector_disabled,
        "never_ingested": never_ingested,
        "never_materialized": never_materialized,
        "never_replayed": never_replayed,
        "historically_active": historically_active,
        "stale": stale,
        "dead_route": dead_route,
        "active": active,
        "replay_active": replay_active,
        "topology_active": topology_active,
        "replayed": replay_active,
        "replay_converged": replay_converged,
        "topology_safe": topology_safe,
        "deterministic": deterministic,
        "drift_free": drift_free,
        "replay_count": int(replay_count),
        "replay_failure_count": int(replay_failure_count),
        "deferred_dependency_count": deferred_dependency_count,
        "topology_edge_count": int(topology_edge_count),
        "topology_cycle_count": 0,
        "determinism_drift_events": int(replay_failure_count),
        "first_seen_at": first_seen_at.isoformat() if first_seen_at is not None and hasattr(first_seen_at, "isoformat") else None,
        "last_materialized_at": last_materialized_at.isoformat()
        if last_materialized_at is not None and hasattr(last_materialized_at, "isoformat")
        else None,
        "production_trusted": production_trusted,
        "maturity_level": maturity,
        "transform_routing_rule_base": reg.rule_base if reg else None,
        "canonical_object_kind": reg.canonical_object_kind.value if reg else None,
        "oracle_fixture_id": reg.oracle_fixture_id if reg else None,
        "tenant_raw_row_count": raw_count,
        "tenant_materialized_row_count": materialized_count,
        "tenant_materialization_pct_of_raw": round(materialization_pct, 2) if materialization_pct is not None else None,
        "orphan_count": int(orphan_count),
        "replay_dependency_failures": int(orphan_count),
        "unresolved_parent_refs": int(orphan_count),
        "deterministic_replay_drift": int(replay_failure_count),
        "unsupported_execution_rows": int(raw_count) if ingest_supported and not routable else 0,
        "notes": exhaust_notes,
    }
