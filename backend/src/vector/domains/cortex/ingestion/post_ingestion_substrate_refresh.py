"""After live ingestion: canonical drain, identity substrate refresh, Phase 05 graph projection.

Shared by ``cortex_full_pipeline_rerun`` (flush path) and scheduled incremental sync follow-up.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.transform_runtime import (
    drain_stub_materialize_backlog,
    repair_tenant_materialization_oracle_determinism_drift,
    resolve_default_bundle_id_for_stub_transform,
)
from vector.domains.cortex.identity.continuity_rebuild import (
    finalize_identity_substrate_operator_audit,
    run_identity_handles_and_candidates_refresh,
    substrate_counts,
)
from vector.domains.cortex.identity.org_link_replay_runtime import execute_org_link_replay_job
from vector.domains.cortex.traversal.tenant_verification_slice import (
    build_org_graph_traversal_verification_slice_v1,
    compute_octs_slice_hash_v1,
)
from vector.settings import Settings


def run_post_ingestion_substrate_refresh(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    identity_substrate_trigger: str = "cortex_post_ingestion_refresh",
) -> dict[str, Any]:
    """Drain canonical backlog, repair determinism, refresh identity, run graph export.

    When ``bundle_id`` is omitted, resolves the default transformable bundle for the tenant.
    """
    bid = (bundle_id or "").strip() or None
    if bid is None:
        resolved = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
        if not resolved:
            return {"skipped": True, "reason": "no_transformable_bundle"}
        bid = resolved

    lim_src = batch_limit
    if lim_src is None:
        lim_src = settings.cortex_post_ingestion_canonical_batch_limit
    lim = max(1, min(int(lim_src), 2000))

    canonical_summary = drain_stub_materialize_backlog(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        connector=None,
        resource_type=None,
        batch_limit=lim,
    )
    repair_scan = min(5000, max(200, int(lim) * 4))
    determinism_repair = repair_tenant_materialization_oracle_determinism_drift(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        scan_limit=repair_scan,
        dry_run=False,
    )
    counts_before_identity = substrate_counts(session, tenant_id=tenant_id)
    identity_continuity_substrate = run_identity_handles_and_candidates_refresh(
        session,
        tenant_id=tenant_id,
        dry_run=False,
        anchor_limit=5_000,
    )
    substrate_audit_report, substrate_audit_job_id = finalize_identity_substrate_operator_audit(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        substrate=identity_continuity_substrate,
        substrate_trigger=identity_substrate_trigger,
        counts_before=counts_before_identity,
    )
    projection_job = execute_org_link_replay_job(
        session,
        tenant_id=tenant_id,
        job_kind="graph_projection_export",
    )
    session.flush()
    slice_body = build_org_graph_traversal_verification_slice_v1(
        session,
        tenant_id=tenant_id,
        verification_run_id=None,
    )
    slice_hash = compute_octs_slice_hash_v1(slice_body)
    proj_summary = dict(projection_job.summary_json or {})
    return {
        "tenant_id": str(tenant_id),
        "bundle_id": bid,
        "canonical_summary": canonical_summary,
        "determinism_repair": determinism_repair,
        "identity_continuity_substrate": identity_continuity_substrate,
        "identity_substrate_audit": substrate_audit_report,
        "identity_substrate_audit_replay_job_id": str(substrate_audit_job_id),
        "phase05_graph_projection_export_job_id": str(projection_job.id),
        "phase05_graph_projection_stable_hash_sha256": proj_summary.get("stable_hash_sha256"),
        "phase05_org_graph_traversal_verification_slice": slice_body,
        "phase05_org_graph_traversal_slice_hash": slice_hash,
    }
