"""Paginated identity substrate repair — owned by phase 03 / convergence (no separate orchestrator)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_tenant_convergence_lease import (
        CortexTenantConvergenceLease,
    )

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.identity.anchor_continuity_candidates import run_anchor_continuity_candidate_regeneration
from vector.domains.cortex.identity.backfill import run_anchor_handle_backfill
from vector.domains.cortex.identity.continuity_rebuild import (
    build_identity_substrate_projection_receipt_v1,
    substrate_counts,
)
from vector.domains.cortex.identity.identity_substrate_health_v1 import (
    evaluate_identity_substrate_health_v1,
    identity_substrate_repair_owed_v1,
)
from vector.domains.cortex.operational_runtime.graph_density import count_distinct_graph_candidate_pairs_v1
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    PROMOTION_TRIGGER_AFTER_PHASE_04_V1,
    schedule_graph_density_pass_v1,
)
from vector.settings import Settings, get_settings

IDENTITY_SUBSTRATE_REPAIR_SCHEMA_VERSION: Final[int] = 1
DETAIL_KEY_IDENTITY_SUBSTRATE_REPAIR_V1: Final[str] = "identity_substrate_repair_v1"


def _repair_settings(cfg: Settings | None = None) -> Settings:
    return cfg or get_settings()


def identity_repair_anchor_batch_size_v1(cfg: Settings | None = None) -> int:
    settings = _repair_settings(cfg)
    raw = int(getattr(settings, "cortex_identity_repair_anchor_batch_size", 5_000) or 5_000)
    return max(500, min(raw, 10_000))


def load_identity_substrate_repair_state_v1(
    lease: "CortexTenantConvergenceLease | None",
) -> dict[str, Any]:
    if lease is None:
        return {"anchor_offset": 0, "anchor_backfill_exhausted": False}
    detail = dict(lease.detail_json or {})
    raw = detail.get(DETAIL_KEY_IDENTITY_SUBSTRATE_REPAIR_V1)
    state = dict(raw) if isinstance(raw, dict) else {}
    return {
        "anchor_offset": max(0, int(state.get("anchor_offset") or 0)),
        "anchor_backfill_exhausted": bool(state.get("anchor_backfill_exhausted")),
        "anchors_total": int(state.get("anchors_total") or 0),
        "last_slice_entities_upserted": int(state.get("last_slice_entities_upserted") or 0),
    }


def persist_identity_substrate_repair_state_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    state: dict[str, Any],
) -> None:
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is None:
        return
    detail = dict(lease.detail_json or {})
    detail[DETAIL_KEY_IDENTITY_SUBSTRATE_REPAIR_V1] = {
        **state,
        "schema_version": IDENTITY_SUBSTRATE_REPAIR_SCHEMA_VERSION,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    lease.detail_json = detail
    session.flush()


def reset_identity_substrate_repair_state_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    anchors_total: int,
) -> dict[str, Any]:
    state = {
        "anchor_offset": 0,
        "anchor_backfill_exhausted": False,
        "anchors_total": anchors_total,
        "last_slice_entities_upserted": 0,
    }
    persist_identity_substrate_repair_state_v1(session, tenant_id=tenant_id, state=state)
    return state


def run_identity_substrate_repair_slice_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    substrate_trigger: str,
    cfg: Settings | None = None,
) -> dict[str, Any]:
    """One convergence-owned repair slice: paginated backfill, regen at exhaustion, inline promotion."""
    settings = _repair_settings(cfg)
    health_before = evaluate_identity_substrate_health_v1(session, tenant_id=tenant_id)
    counts_before = substrate_counts(session, tenant_id=tenant_id)
    anchors_total = int(counts_before.get("identity_anchors") or 0)
    pairs_before = count_distinct_graph_candidate_pairs_v1(session, tenant_id=tenant_id)

    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    state = load_identity_substrate_repair_state_v1(lease)
    if int(state.get("anchors_total") or 0) != anchors_total:
        state = reset_identity_substrate_repair_state_v1(
            session, tenant_id=tenant_id, anchors_total=anchors_total
        )
    if health_before.get("status") == "broken" and int(counts_before.get("org_entities_active") or 0) == 0:
        state["anchor_offset"] = 0
        state["anchor_backfill_exhausted"] = False

    batch = identity_repair_anchor_batch_size_v1(settings)
    offset = int(state.get("anchor_offset") or 0)

    backfill = run_anchor_handle_backfill(
        session,
        tenant_id=tenant_id,
        dry_run=False,
        anchor_limit=batch,
        anchor_offset=offset,
        skip_candidate_regen=True,
    )
    scanned = int(backfill.get("anchors_scanned") or 0)
    entities_upserted = int(backfill.get("entities_upserted") or 0)
    new_offset = offset + scanned
    exhausted = scanned == 0 or new_offset >= anchors_total
    state["anchor_offset"] = new_offset
    state["anchor_backfill_exhausted"] = exhausted
    state["anchors_total"] = anchors_total
    state["last_slice_entities_upserted"] = entities_upserted
    persist_identity_substrate_repair_state_v1(session, tenant_id=tenant_id, state=state)

    candidate_regen: dict[str, Any] | None = None
    run_regen = exhausted or (
        entities_upserted > 0 and int(counts_before.get("org_link_candidates") or 0) == 0
    )
    if run_regen and not exhausted:
        run_regen = entities_upserted > 0
    if run_regen:
        candidate_regen = run_anchor_continuity_candidate_regeneration(session, tenant_id=tenant_id)
        session.flush()

    substrate = {
        **backfill,
        "candidate_regeneration": candidate_regen,
        "identity_continuity_substrate_pipeline": "v1",
        "identity_substrate_repair": {
            "schema_version": IDENTITY_SUBSTRATE_REPAIR_SCHEMA_VERSION,
            "anchor_offset_before": offset,
            "anchor_offset_after": new_offset,
            "anchor_backfill_exhausted": exhausted,
            "anchors_total": anchors_total,
            "entities_upserted": entities_upserted,
            "candidate_regen_ran": candidate_regen is not None,
        },
    }

    pairs_after = count_distinct_graph_candidate_pairs_v1(session, tenant_id=tenant_id)
    distinct_candidate_pairs_delta = pairs_after - pairs_before

    promotion: dict[str, Any] | None = None
    if entities_upserted > 0 or (candidate_regen and int(candidate_regen.get("candidate_count") or 0) > 0):
        promotion = schedule_graph_density_pass_v1(
            tenant_id=tenant_id,
            trigger=PROMOTION_TRIGGER_AFTER_PHASE_04_V1,
            force=identity_substrate_repair_owed_v1(health_before),
            session=session,
        )

    audit = build_identity_substrate_projection_receipt_v1(
        session,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        substrate=substrate,
        substrate_trigger=substrate_trigger,
        counts_before=counts_before,
        distinct_candidate_pairs_delta=distinct_candidate_pairs_delta,
        promotion_pass=promotion,
    )
    slice_receipt = audit.get("substrate_slice_receipt_v1")
    health_after = evaluate_identity_substrate_health_v1(session, tenant_id=tenant_id)

    return {
        "identity_continuity_substrate": substrate,
        "identity_substrate_audit": audit,
        "substrate_slice_receipt_v1": slice_receipt,
        "identity_substrate_health_before": health_before,
        "identity_substrate_health_after": health_after,
        "graph_density_promotion": promotion,
        "anchor_limit_applied": batch,
        "counts_before": counts_before,
        "counts_after": audit.get("counts_after"),
        "distinct_candidate_pairs_delta": distinct_candidate_pairs_delta,
    }


def run_identity_substrate_repair_until_exhausted_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    substrate_trigger: str,
    max_slices: int = 12,
    cfg: Settings | None = None,
) -> dict[str, Any]:
    """Operator / recovery path: run repair slices until anchor scan exhausts (bounded)."""
    slices: list[dict[str, Any]] = []
    last: dict[str, Any] = {}
    for _ in range(max(1, min(int(max_slices), 50))):
        last = run_identity_substrate_repair_slice_v1(
            session,
            tenant_id=tenant_id,
            bundle_id=bundle_id,
            substrate_trigger=substrate_trigger,
            cfg=cfg,
        )
        slices.append(last)
        repair = (last.get("identity_continuity_substrate") or {}).get("identity_substrate_repair") or {}
        if repair.get("anchor_backfill_exhausted"):
            break
        if int(repair.get("entities_upserted") or 0) == 0 and int(repair.get("anchor_offset_after") or 0) == int(
            repair.get("anchor_offset_before") or 0
        ):
            break
    return {
        "surface_kind": "identity_substrate_repair_until_exhausted_v1",
        "tenant_id": str(tenant_id),
        "slices_run": len(slices),
        "last_slice": last,
        "counts_after": (last.get("counts_after") if last else None),
        "identity_substrate_health_after": last.get("identity_substrate_health_after"),
    }
