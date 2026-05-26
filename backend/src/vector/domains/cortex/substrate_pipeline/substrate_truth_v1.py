"""Wave 0 — single authoritative substrate truth aggregate (read-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final, Literal

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.dual_lane_lease import (
    build_canonical_lane_detail_v1,
    build_execution_lane_detail_v1,
)
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_DIRTY, LEASE_STATUS_STALLED
from vector.domains.cortex.execution.worker_queue_roles_v1 import (
    CELERY_INGESTION_QUEUES_V1,
    CELERY_SUBSTRATE_QUEUES_V1,
)
from vector.domains.cortex.identity.continuity_rebuild import substrate_counts
from vector.domains.cortex.identity.identity_substrate_health_v1 import (
    evaluate_identity_substrate_health_v1,
)
from vector.domains.cortex.identity.identity_substrate_repair_v1 import (
    DETAIL_KEY_IDENTITY_SUBSTRATE_REPAIR_V1,
    load_identity_substrate_repair_state_v1,
)
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    DETAIL_KEY_GRAPH_DENSITY_PROMOTION_SCHEDULE_V1,
)
from vector.domains.cortex.substrate_pipeline.substrate_contract_v1 import (
    build_graph_substrate_v1,
    build_ingest_handoff_v1,
)
from vector.settings import Settings, get_settings

SUBSTRATE_TRUTH_SCHEMA_VERSION: Final[int] = 1
SUBSTRATE_TRUTH_SURFACE_KIND: Final[str] = "substrate_truth_v1"

ISOLATED_PCT_RED_MAX_V1: Final[float] = 90.0
PROMOTION_RULES_HEALTHY_MIN_V1: Final[int] = 3
PROMOTION_RULES_DEGRADED_MIN_V1: Final[int] = 2

SubstrateOverallStatusV1 = Literal["HEALTHY", "DEGRADED", "BROKEN", "STALLED"]


def _queue_ownership_reference_v1() -> dict[str, Any]:
    return {
        "ingestion_queues": list(CELERY_INGESTION_QUEUES_V1),
        "substrate_queues": list(CELERY_SUBSTRATE_QUEUES_V1),
        "ingestion_tasks": [
            "vector.cortex.ingestion.run_sync",
            "vector.cortex.ingestion.run_sync_replay",
            "vector.cortex.ingestion.scheduler_tick",
        ],
        "substrate_tasks": [
            "vector.cortex.execution.run_slice",
            "vector.cortex.convergence.sweep",
        ],
        "dirty_owner": "mark_dirty_and_enqueue_convergence_v1",
        "repair_owner": "run_identity_substrate_repair_slice_v1",
        "promotion_owner": "run_graph_density_promotion_pass_v1",
        "graph_export_owner": "run_graph_projection_export_for_pipeline_v1",
        "runbook": "DOCS/cortex/substrate_queue_runbook.md",
    }


def _runtime_flags_v1(settings: Settings) -> dict[str, Any]:
    return {
        "cortex_post_ingestion_substrate_refresh_enabled": bool(
            settings.cortex_post_ingestion_substrate_refresh_enabled
        ),
        "cortex_execution_event_triggers_enabled": bool(settings.cortex_execution_event_triggers_enabled),
        "cortex_execution_dual_lane_enabled": bool(settings.cortex_execution_dual_lane_enabled),
        "cortex_dual_lane_run_execution_on_topology_wait": bool(
            settings.cortex_dual_lane_run_execution_on_topology_wait
        ),
    }


def _last_slice_summary_v1(lease_detail: dict[str, Any]) -> dict[str, Any] | None:
    repair = lease_detail.get(DETAIL_KEY_IDENTITY_SUBSTRATE_REPAIR_V1)
    promotion = lease_detail.get(DETAIL_KEY_GRAPH_DENSITY_PROMOTION_SCHEDULE_V1)
    if not isinstance(repair, dict) and not isinstance(promotion, dict):
        outcome = lease_detail.get("last_phase_outcome")
        if outcome is None:
            return None
        return {
            "last_phase_outcome": outcome,
            "last_phase_id": lease_detail.get("last_phase_id"),
            "last_phase_receipt_hash": lease_detail.get("last_phase_receipt_hash"),
        }
    summary: dict[str, Any] = {}
    if isinstance(repair, dict):
        summary["repair"] = {
            "anchor_offset": repair.get("anchor_offset"),
            "anchor_backfill_exhausted": repair.get("anchor_backfill_exhausted"),
            "anchors_total": repair.get("anchors_total"),
            "last_slice_entities_upserted": repair.get("last_slice_entities_upserted"),
            "updated_at": repair.get("updated_at"),
        }
    if isinstance(promotion, dict):
        summary["promotion_schedule"] = {
            "scheduled": promotion.get("scheduled"),
            "path": promotion.get("path"),
            "trigger": promotion.get("trigger"),
            "updated_at": promotion.get("updated_at"),
        }
    if lease_detail.get("last_phase_outcome"):
        summary["last_phase_outcome"] = lease_detail.get("last_phase_outcome")
    return summary or None


def _compute_overall_status_v1(
    *,
    lease_status: str | None,
    identity_status: str,
    isolated_pct: float,
    promotion_rule_count: int,
    canonical_lane_status: str | None,
) -> tuple[SubstrateOverallStatusV1, list[str]]:
    red_rules: list[str] = []
    if lease_status == LEASE_STATUS_STALLED:
        red_rules.append("lease_stalled")
        return "STALLED", red_rules

    if identity_status == "broken":
        red_rules.append("identity_substrate_broken")
        return "BROKEN", red_rules

    if isolated_pct > ISOLATED_PCT_RED_MAX_V1:
        red_rules.append("graph_isolated_pct_above_90")
    if promotion_rule_count < PROMOTION_RULES_DEGRADED_MIN_V1:
        red_rules.append("promotion_rule_diversity_below_2")
    if identity_status == "degraded":
        red_rules.append("identity_substrate_degraded")
    if canonical_lane_status == "WAITING":
        red_rules.append("canonical_lane_waiting")

    if red_rules:
        return "DEGRADED", red_rules
    if promotion_rule_count < PROMOTION_RULES_HEALTHY_MIN_V1:
        return "DEGRADED", ["cross_tool_continuity_below_3_rules"]
    return "HEALTHY", []


def _operator_guidance_v1(
    *,
    overall_status: SubstrateOverallStatusV1,
    red_rules: list[str],
    runtime_flags: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    if not runtime_flags.get("cortex_post_ingestion_substrate_refresh_enabled"):
        lines.append("Post-ingest substrate refresh is disabled — live ingest will not enqueue convergence.")
    if not runtime_flags.get("cortex_execution_event_triggers_enabled"):
        lines.append("Execution event triggers are disabled — post-ingest handoff may not mark dirty.")
    if overall_status == "STALLED":
        lines.append("Lease is STALLED — inspect block_reason and last_error on Runtime before repair.")
    elif overall_status == "BROKEN":
        lines.append("Identity substrate is BROKEN — use Repair (reset cursor + mark dirty), not replay jobs.")
    elif overall_status == "DEGRADED":
        lines.append("Substrate is DEGRADED — trust red_rules, not phase COMPLETED or edge_count KPIs.")
    else:
        lines.append("Substrate coherence signals are healthy — still verify graph isolation % over time.")
    if "graph_isolated_pct_above_90" in red_rules:
        lines.append("Over 90% of entities lack authoritative edges — graph export is not people continuity.")
    if "promotion_rule_diversity_below_2" in red_rules:
        lines.append("Fewer than 2 promotion rules active — cross-tool identity merge is not happening.")
    return lines


def build_substrate_truth_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    include_connected_components: bool = True,
) -> dict[str, Any]:
    """Assemble authoritative substrate truth from lease + health + graph metrics (read-only)."""
    cfg = settings or get_settings()
    captured_at = datetime.now(UTC)
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    canonical_lane = build_canonical_lane_detail_v1(session, tenant_id=tenant_id, lease=lease)
    execution_lane = build_execution_lane_detail_v1(session, tenant_id=tenant_id, lease=lease)
    identity_health = evaluate_identity_substrate_health_v1(session, tenant_id=tenant_id)
    repair_state = load_identity_substrate_repair_state_v1(lease)
    counts = substrate_counts(session, tenant_id=tenant_id)
    graph_substrate = build_graph_substrate_v1(
        session,
        tenant_id=tenant_id,
        include_connected_components=include_connected_components,
    )

    isolated_pct = float(graph_substrate.get("isolated_pct") or 0.0)
    promotion_rule_count = int(graph_substrate.get("promotion_rule_count") or 0)
    identity_status = str(identity_health.get("status") or "healthy")

    overall_status, red_rules = _compute_overall_status_v1(
        lease_status=str(lease.status) if lease is not None else None,
        identity_status=identity_status,
        isolated_pct=isolated_pct,
        promotion_rule_count=promotion_rule_count,
        canonical_lane_status=str(canonical_lane.get("lane_status") or ""),
    )

    runtime_flags = _runtime_flags_v1(cfg)
    obligation_epoch = int(lease.obligation_epoch) if lease is not None else None
    is_dirty = lease.status == LEASE_STATUS_DIRTY if lease is not None else False
    motion = {
        "lease_status": lease.status if lease is not None else None,
        "fsm_state": lease.fsm_state if lease is not None else None,
        "phase_cursor": lease.phase_cursor if lease is not None else None,
        "obligation_epoch": obligation_epoch,
        "target_epoch": int(lease.target_epoch) if lease is not None else None,
        "block_reason_code": lease.block_reason_code if lease is not None else None,
        "is_dirty": is_dirty,
        "updated_at": lease.updated_at.isoformat() if lease and lease.updated_at else None,
        "last_canonical_outcome": detail.get("last_canonical_outcome"),
        "convergence_health": detail.get("convergence_health"),
    }
    ingest_handoff = build_ingest_handoff_v1(
        dirty_enqueued=is_dirty,
        obligation_epoch=obligation_epoch,
        reason=detail.get("last_dirty_reason") if isinstance(detail.get("last_dirty_reason"), str) else None,
    )

    identity_panel = {
        "health": identity_health,
        "counts": counts,
        "repair": repair_state,
        "distinct_authoritative_promotion_rules": promotion_rule_count,
        "identity_healthy": identity_status == "healthy" and promotion_rule_count >= PROMOTION_RULES_DEGRADED_MIN_V1,
        "graph_healthy": isolated_pct <= ISOLATED_PCT_RED_MAX_V1 and promotion_rule_count >= PROMOTION_RULES_DEGRADED_MIN_V1,
    }

    guidance = _operator_guidance_v1(
        overall_status=overall_status,
        red_rules=red_rules,
        runtime_flags=runtime_flags,
    )

    return {
        "surface_kind": SUBSTRATE_TRUTH_SURFACE_KIND,
        "schema_version": SUBSTRATE_TRUTH_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "captured_at_utc": captured_at.isoformat(),
        "overall_status": overall_status,
        "red_rules": red_rules,
        "motion": motion,
        "canonical": canonical_lane,
        "execution": execution_lane,
        "identity": identity_panel,
        "graph_substrate": graph_substrate,
        "graph": graph_substrate,
        "ingest_handoff": ingest_handoff,
        "runtime_flags": runtime_flags,
        "queue_ownership": _queue_ownership_reference_v1(),
        "last_slice": _last_slice_summary_v1(detail),
        "operator_guidance": guidance,
        "primary_truth_contract": "substrate_truth_v1",
        "deprecated_for_substrate_health": [
            "identity_control_plane_v1 link counts alone",
            "pipeline_run completed status",
            "phase_04 edge_count",
            "org_link_replay_job progress",
        ],
    }
