"""Phase C step C3 — unified continuity audit snapshot (panel + SQL + phase slices)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    continuity_p0_baseline_path_v1,
    load_continuity_p0_baseline_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase08_empty_scope_truth import (
    snapshot_phase08_empty_scope_truth_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c2_synthesis_scope_caps import (
    snapshot_c2_synthesis_scope_caps_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_deprecation import (
    DEPRECATED_CONTINUITY_PROOF_SCRIPTS_V1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    build_continuity_proof_panel_v1,
    format_continuity_proof_panel_text_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_substrate_sql_snapshot import (
    build_substrate_sql_snapshot_v1,
)

PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION: Final[int] = 1
P0_C3_STEP: Final[str] = "step_c3_continuity_audit_snapshot"
AUDIT_SNAPSHOT_SURFACE_KIND: Final[str] = "continuity_audit_snapshot"


def summarize_p0_baseline_steps_v1(
    *,
    repo_root: Path,
    baseline_date: str | None = None,
) -> dict[str, Any]:
    """Roll up committed P0 baseline step pass flags (read-only)."""
    path = continuity_p0_baseline_path_v1(repo_root=repo_root, date_suffix=baseline_date)
    baseline = load_continuity_p0_baseline_v1(path)
    steps: dict[str, Any] = {}
    for key, record in baseline.items():
        if not key.startswith("step_") or not isinstance(record, dict):
            continue
        pass_key = next((k for k in record if k.endswith("_pass")), None)
        steps[key] = {
            "validated_at": record.get("validated_at"),
            "pass": bool(record.get(pass_key)) if pass_key else None,
            "pass_field": pass_key,
        }
    passed = sum(1 for s in steps.values() if s.get("pass") is True)
    return {
        "baseline_path": str(path),
        "baseline_present": path.is_file(),
        "step_count": len(steps),
        "steps_passed": passed,
        "steps": steps,
    }


def build_continuity_audit_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    window_hours: int = 24,
    ops_log_text: str | None = None,
    wedge_free_ack: bool = False,
    repo_root: Path | None = None,
    baseline_date: str | None = None,
) -> dict[str, Any]:
    """Single ops payload: AA panel + substrate SQL + C1/C2 phase snapshots."""
    panel = build_continuity_proof_panel_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        window_hours=window_hours,
        ops_log_text=ops_log_text,
        wedge_free_ack=wedge_free_ack,
    )
    panel_text = format_continuity_proof_panel_text_v1(panel)
    substrate_sql = build_substrate_sql_snapshot_v1(session, tenant_id=tenant_id)
    phase_snapshots = {
        "c1_phase08_empty_scope_truth": snapshot_phase08_empty_scope_truth_v1(
            session, tenant_id=tenant_id
        ),
        "c2_synthesis_scope_caps": snapshot_c2_synthesis_scope_caps_v1(
            session, tenant_id=tenant_id
        ),
    }
    baseline_rollup = None
    if repo_root is not None:
        baseline_rollup = summarize_p0_baseline_steps_v1(
            repo_root=repo_root,
            baseline_date=baseline_date,
        )

    panel_summary = dict(panel.get("summary") or {})
    return {
        "surface_kind": AUDIT_SNAPSHOT_SURFACE_KIND,
        "step": P0_C3_STEP,
        "phase_c3_schema_version": PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else panel.get("pipeline_run_id"),
        "generated_at": datetime.now(UTC).isoformat(),
        "window_hours": window_hours,
        "panel": panel,
        "panel_text": panel_text,
        "substrate_sql": substrate_sql,
        "phase_snapshots": phase_snapshots,
        "baseline_rollup": baseline_rollup,
        "deprecated_proof_scripts": list(DEPRECATED_CONTINUITY_PROOF_SCRIPTS_V1),
        "canonical_entrypoint": "backend/scripts/continuity_audit_snapshot.py",
        "summary": {
            "panel_fail_count": int(panel_summary.get("fail_count") or 0),
            "panel_pass_count": int(panel_summary.get("pass_count") or 0),
            "m3_autonomously_alive": bool(panel_summary.get("m3_autonomously_alive")),
            "obligation_epoch_gap_ok": substrate_sql.get("obligation_epoch_gap_ok"),
            "retrieval_entries_in_epoch": substrate_sql.get("retrieval_entries_in_published_epoch"),
        },
    }


def format_continuity_audit_snapshot_text_v1(snapshot: dict[str, Any]) -> str:
    """Human-readable operator view (panel + headline SQL metrics)."""
    lines = [
        "=== Cortex Continuity Audit Snapshot (C3) ===",
        f"Tenant: {snapshot.get('tenant_id')}",
        f"Generated: {snapshot.get('generated_at')}",
        f"Canonical: {snapshot.get('canonical_entrypoint')}",
        "",
        str(snapshot.get("panel_text") or ""),
        "",
        "=== Substrate SQL (headline) ===",
    ]
    sql = dict(snapshot.get("substrate_sql") or {})
    lease = dict(sql.get("lease") or {})
    lines.extend(
        [
            f"Lease FSM: {lease.get('fsm_state')} | obligation−target={lease.get('obligation_minus_target')}"
            f" | gap_ok={lease.get('obligation_epoch_gap_ok')}",
            f"Raw/Mat: {sql.get('raw_total')} / {sql.get('mat_total')} (gap={sql.get('raw_minus_mat_admin_gap')})",
            f"Org entities active: {sql.get('org_entities_active')} | auth_links: {sql.get('auth_links')}",
            f"Retrieval entries (published epoch): {sql.get('retrieval_entries_in_published_epoch')}",
            f"Synthesis jobs: {json.dumps(sql.get('synthesis_jobs_by_status') or {}, sort_keys=True)}",
            f"Artifacts published/total: {sql.get('artifacts_published')} / {sql.get('artifacts_total')}",
            "=== end snapshot ===",
        ]
    )
    return "\n".join(lines)
