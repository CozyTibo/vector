"""Phase 0 step 0.4 (P0-B) — evaluate and record phase 05 completion proof (CONT-INV-01/02)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_FAILED,
)
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import (
    CortexOctsDurableWalkRecord,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import (
    CortexTenantConvergenceLease,
)

CONT_INV_01_GATE = "CONT-INV-01"
CONT_INV_02_GATE = "CONT-INV-02"
P0_B_STEP = "0.4_phase05_autonomous_proof"


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def evaluate_p0_b_phase05_proof_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Return P0-B proof payload for one tenant (optionally scoped to a pipeline run)."""
    lease = session.get(CortexTenantConvergenceLease, tenant_id)
    run: CortexSubstratePipelineRun | None = None
    if pipeline_run_id is not None:
        run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    elif lease is not None and lease.pipeline_run_id is not None:
        run = session.get(CortexSubstratePipelineRun, lease.pipeline_run_id)

    phase05: CortexSubstratePhaseRun | None = None
    phase04: CortexSubstratePhaseRun | None = None
    if run is not None:
        phase05 = get_phase_run_v1(
            session,
            pipeline_run_id=run.id,
            phase_id=PHASE_05_TRAVERSAL,
        )
        phase04 = get_phase_run_v1(
            session,
            pipeline_run_id=run.id,
            phase_id=PHASE_04_GRAPH,
        )

    p05_out = dict(phase05.output_json or {}) if phase05 is not None else {}
    receipt = dict(p05_out.get("substrate_phase_receipt") or {})
    walks_persisted = int(p05_out.get("walks_persisted") or p05_out.get("walks_scheduled") or 0)

    phase04_completed_at = _parse_ts(phase04.completed_at if phase04 else None)

    walk_rows = list(
        session.scalars(
            select(CortexOctsDurableWalkRecord)
            .where(CortexOctsDurableWalkRecord.tenant_id == tenant_id)
            .order_by(CortexOctsDurableWalkRecord.created_at.desc())
            .limit(500)
        ).all()
    )
    walks_after_phase04 = 0
    newest_walk_at: datetime | None = None
    if phase04_completed_at is not None:
        for row in walk_rows:
            created = _parse_ts(row.created_at)
            if created is None:
                continue
            if created > phase04_completed_at:
                walks_after_phase04 += 1
            if newest_walk_at is None or (created and created > newest_walk_at):
                newest_walk_at = created

    schema_error = False
    if phase05 is not None:
        err = (phase05.error_detail or "") + (lease.last_error if lease and lease.last_error else "")
        schema_error = "octs-walk-policy-v1.schema.json" in err or "Could not locate DOCS/cortex" in err

    phase05_completed = phase05 is not None and phase05.status == PHASE_STATUS_COMPLETED
    phase05_failed = phase05 is not None and phase05.status == PHASE_STATUS_FAILED
    lease_error_clear = lease is None or not (lease.last_error or "").strip()

    checks = {
        "phase_05_status_completed": phase05_completed,
        "walks_persisted_gt_0": walks_persisted > 0 or walks_after_phase04 > 0,
        "walks_after_phase_04_completed_at": walks_after_phase04 > 0,
        "lease_last_error_null": lease_error_clear,
        "no_schema_path_error": not schema_error,
        "cont_inv_02_schema_resolvable": not schema_error,
    }
    p0_b_pass = all(checks.values())

    return {
        "gate": P0_B_STEP,
        "cont_inv_01": CONT_INV_01_GATE,
        "cont_inv_02": CONT_INV_02_GATE,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(run.id) if run else None,
        "pipeline_run_status": run.status if run else None,
        "phase_04_completed_at": phase04.completed_at.isoformat() if phase04 and phase04.completed_at else None,
        "phase_05": (
            {
                "status": phase05.status,
                "started_at": phase05.started_at.isoformat() if phase05.started_at else None,
                "completed_at": phase05.completed_at.isoformat() if phase05.completed_at else None,
                "error_detail": (phase05.error_detail or "")[:500] or None,
                "walks_persisted": walks_persisted,
                "receipt_outcome": receipt.get("outcome"),
            }
            if phase05
            else None
        ),
        "lease": (
            {
                "status": lease.status,
                "fsm_state": lease.fsm_state,
                "phase_cursor": lease.phase_cursor,
                "last_error": (lease.last_error or "")[:500] or None,
            }
            if lease
            else None
        ),
        "walks": {
            "total_count": len(walk_rows),
            "after_phase_04_count": walks_after_phase04,
            "newest_created_at": newest_walk_at.isoformat() if newest_walk_at else None,
        },
        "checks": checks,
        "p0_b_pass": p0_b_pass,
    }
