"""Phase 03 Step 16 — canonical operator control-plane aggregate.

Substrate metrics and proof pointers. Normative:
`DOCS/cortex/03-canonical/phase-03-canonical-control-plane-doctrine.md`.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.ambiguity_runtime import build_ambiguity_aggregates
from vector.domains.cortex.canonical.canonical_coverage_matrix import build_canonical_coverage_matrix
from vector.domains.cortex.canonical.failure_remediation_runtime import sync_canonical_failure_cases
from vector.domains.cortex.canonical.mapping_bundle_registry import (
    build_tenant_mapping_registry_public_document,
)
from vector.infrastructure.db.models.cortex_canonical_failure_case import CortexCanonicalFailureCase
from vector.infrastructure.db.models.cortex_canonical_field_lineage import (
    CortexCanonicalFieldLineage,
)
from vector.infrastructure.db.models.cortex_canonical_provenance_record import (
    CortexCanonicalProvenanceRecord,
)
from vector.infrastructure.db.models.cortex_canonical_remediation_validation import (
    CortexCanonicalRemediationValidation,
)
from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob
from vector.infrastructure.db.models.cortex_canonical_temporal_supersession import (
    CortexCanonicalTemporalSupersession,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_canonical_verification_run import (
    CortexCanonicalVerificationRun,
)

CANONICAL_CONTROL_PLANE_SCHEMA_VERSION: Final[int] = 1

_VERIFICATION_STALE_HOURS: Final[int] = 48
_AMBIGUITY_EXPLOSION_THRESHOLD: Final[int] = 5000


def _replay_job_public(job: CortexCanonicalReplayJob) -> dict[str, Any]:
    sj = job.summary_json if isinstance(job.summary_json, dict) else {}
    return {
        "job_id": str(job.id),
        "status": job.status,
        "job_kind": job.job_kind,
        "pinned_bundle_id": job.pinned_bundle_id,
        "dry_run": job.dry_run,
        "engine_build_ref": job.engine_build_ref,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "counts_by_divergence_class": dict(sj.get("counts_by_divergence_class") or {}),
        "writes_applied": sj.get("writes_applied"),
        "writes_skipped": sj.get("writes_skipped"),
    }


def _verification_truth_from_run(
    row: CortexCanonicalVerificationRun | None,
) -> dict[str, Any] | None:
    if row is None:
        return None
    gates = row.gates_json if isinstance(row.gates_json, list) else []
    pass_n = sum(1 for g in gates if isinstance(g, dict) and g.get("passed") is True)
    fail_n = sum(1 for g in gates if isinstance(g, dict) and g.get("passed") is False)
    return {
        "last_run_id": row.id,
        "engine_schema_version": row.engine_schema_version,
        "passed": row.passed,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "gate_results_tally": {"pass": pass_n, "fail": fail_n, "total": len(gates)},
        "evidence_keys": (
            sorted((row.evidence_json or {}).keys()) if isinstance(row.evidence_json, dict) else []
        ),
    }


def build_canonical_control_plane(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    failures_sync = sync_canonical_failure_cases(session, tenant_id)
    active_failures = list(
        session.scalars(
            select(CortexCanonicalFailureCase).where(
                CortexCanonicalFailureCase.tenant_id == tenant_id,
                CortexCanonicalFailureCase.active.is_(True),
            )
        ).all()
    )
    failure_classes = Counter(c.failure_class for c in active_failures)

    mat_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    lineage_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalFieldLineage)
            .join(
                CortexCanonicalTransformMaterialization,
                CortexCanonicalFieldLineage.materialization_id
                == CortexCanonicalTransformMaterialization.id,
            )
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    prov_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalProvenanceRecord)
            .where(CortexCanonicalProvenanceRecord.tenant_id == tenant_id)
        )
        or 0
    )
    supersession_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTemporalSupersession)
            .where(CortexCanonicalTemporalSupersession.tenant_id == tenant_id)
        )
        or 0
    )

    replay_jobs = list(
        session.scalars(
            select(CortexCanonicalReplayJob)
            .where(CortexCanonicalReplayJob.tenant_id == tenant_id)
            .order_by(CortexCanonicalReplayJob.created_at.desc())
            .limit(25)
        ).all()
    )
    replay_status_counts = Counter(j.status for j in replay_jobs)

    div_totals: Counter[str] = Counter()
    for j in replay_jobs:
        if j.status != "completed":
            continue
        sj = j.summary_json if isinstance(j.summary_json, dict) else {}
        raw_c = sj.get("counts_by_divergence_class") or {}
        if isinstance(raw_c, dict):
            for k, v in raw_c.items():
                try:
                    div_totals[str(k)] += int(v)
                except (TypeError, ValueError):
                    continue

    last_ver = session.scalar(
        select(CortexCanonicalVerificationRun)
        .where(CortexCanonicalVerificationRun.tenant_id == tenant_id)
        .order_by(
            CortexCanonicalVerificationRun.created_at.desc(),
            CortexCanonicalVerificationRun.id.desc(),
        )
        .limit(1)
    )
    verification_truth = _verification_truth_from_run(last_ver)
    freshness = "never_run"
    if last_ver is not None and last_ver.created_at is not None:
        age = datetime.now(tz=UTC) - last_ver.created_at
        freshness = "stale" if age > timedelta(hours=_VERIFICATION_STALE_HOURS) else "fresh"

    registry = build_tenant_mapping_registry_public_document(db=session, tenant_id=tenant_id)
    bundle_ids = [
        b["bundle_id"]
        for b in registry.get("bundles", [])
        if isinstance(b, dict) and b.get("bundle_id")
    ]
    pins = registry.get("pins_for_tenant") or []
    pins_list = pins if isinstance(pins, list) else []

    ambiguity = build_ambiguity_aggregates(session, tenant_id=tenant_id)
    open_amb = int((ambiguity.get("by_status") or {}).get("open", 0))
    ambiguity_explosion_warn = open_amb >= _AMBIGUITY_EXPLOSION_THRESHOLD
    coverage = build_canonical_coverage_matrix(session, tenant_id=tenant_id)
    coverage_summary = coverage.get("summary") if isinstance(coverage.get("summary"), dict) else {}

    latest_remediation = session.scalar(
        select(CortexCanonicalRemediationValidation)
        .where(CortexCanonicalRemediationValidation.tenant_id == tenant_id)
        .order_by(
            CortexCanonicalRemediationValidation.created_at.desc(),
            CortexCanonicalRemediationValidation.id.desc(),
        )
        .limit(1)
    )

    base = f"/admin/tenants/{tenant_id}/cortex/canonical"
    logical_ia: dict[str, Any] = {
        "A_overview": {
            "doctrine_surface": "A",
            "summary": "Counts, pins, replay/verification freshness, ambiguity/drift pressure.",
            "admin_route_hints": [f"GET {base}/control-plane", f"GET {base}/ontology"],
        },
        "B_canonical_objects": {
            "doctrine_surface": "B",
            "summary": "Bounded canonical rows + per-object lineage (transform lineage list).",
            "admin_route_hints": [f"GET {base}/transform/lineage", f"GET {base}/query"],
        },
        "C_mapping": {
            "doctrine_surface": "C",
            "summary": "Bundles, pins, compatibility, changelog.",
            "admin_route_hints": [f"GET {base}/mapping-registry"],
        },
        "D_replay_rebuild": {
            "doctrine_surface": "D",
            "summary": "Replay jobs, receipts, divergence tallies.",
            "admin_route_hints": [
                f"GET {base}/replay-jobs",
                f"POST {base}/replay-jobs/run",
            ],
        },
        "E_ambiguity": {
            "doctrine_surface": "E",
            "summary": "Ambiguity records, lifecycle, aggregates.",
            "admin_route_hints": [f"GET {base}/ambiguity"],
        },
        "F_provenance": {
            "doctrine_surface": "F",
            "summary": "Raw↔canonical provenance pointers.",
            "admin_route_hints": [
                f"GET {base}/provenance/raw-records/{{raw_record_id}}",
                f"GET {base}/provenance/materializations/{{materialization_id}}",
            ],
        },
        "G_verification": {
            "doctrine_surface": "G",
            "summary": "Gate matrix + persisted verification ledger + Step 18 certification pack.",
            "admin_route_hints": [
                f"POST {base}/verification/run",
                f"GET {base}/verification/runs",
                f"GET {base}/certification-pack",
                f"POST {base}/certification-pack/archive",
                f"GET {base}/certification-pack/archives",
            ],
        },
        "H_recovery": {
            "doctrine_surface": "H",
            "summary": "Failure registry + remediation validation receipts.",
            "admin_route_hints": [
                f"GET {base}/failures",
                f"POST {base}/remediation/validate",
            ],
        },
    }

    checklist: list[dict[str, Any]] = [
        {
            "id": "mapping_registry_addressable",
            "passed": len(bundle_ids) > 0,
            "detail": {"bundle_inventory_count": len(bundle_ids)},
        },
        {
            "id": "tenant_mapping_pins_present",
            "passed": len(pins_list) > 0,
            "detail": {"pin_row_count": len(pins_list)},
        },
        {
            "id": "canonical_verification_ledger_reachable",
            "passed": last_ver is not None,
            "detail": freshness if last_ver is None else f"last_run_id={last_ver.id}",
        },
        {
            "id": "verification_last_run_passed",
            "passed": bool(last_ver.passed) if last_ver is not None else False,
            "detail": None if last_ver is None else last_ver.passed,
        },
        {
            "id": "verification_freshness_acceptable",
            "passed": freshness != "stale",
            "detail": freshness,
        },
        {
            "id": "canonical_failure_registry_synced",
            "passed": isinstance(failures_sync, dict)
            and "failure_remediation_runtime_schema_version" in failures_sync,
            "detail": failures_sync,
        },
        {
            "id": "ambiguity_explosion_within_threshold",
            "passed": not ambiguity_explosion_warn,
            "detail": {
                "open_ambiguity_count": open_amb,
                "threshold": _AMBIGUITY_EXPLOSION_THRESHOLD,
            },
        },
        {
            "id": "replay_forbidden_divergence_absent_in_recent_completed",
            "passed": sum(div_totals.get(k, 0) for k in ("C3", "C4", "C5")) == 0,
            "detail": {
                "recent_completed_jobs_scanned": sum(
                    1 for j in replay_jobs if j.status == "completed"
                ),
                "counts_by_divergence_class_totals": dict(div_totals),
            },
        },
        {
            "id": "certification_operator_surfaces_wired",
            "passed": True,
            "detail": "logical_information_architecture keys A–H present",
        },
    ]

    actions: list[dict[str, Any]] = [
        {
            "id": "run_canonical_verification",
            "method": "POST",
            "path": f"{base}/verification/run",
            "safe": True,
            "scope": "tenant",
            "expected_impact": (
                "recomputes gate matrix and optionally appends verification ledger row"
            ),
        },
        {
            "id": "list_canonical_verification_runs",
            "method": "GET",
            "path": f"{base}/verification/runs",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "read-only verification ledger tail",
        },
        {
            "id": "list_mapping_registry",
            "method": "GET",
            "path": f"{base}/mapping-registry",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "read-only registry snapshot",
        },
        {
            "id": "list_replay_jobs",
            "method": "GET",
            "path": f"{base}/replay-jobs",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "read-only replay job history",
        },
        {
            "id": "list_canonical_failures",
            "method": "GET",
            "path": f"{base}/failures",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "refreshes failure registry view",
        },
        {
            "id": "validate_remediation_receipt",
            "method": "POST",
            "path": f"{base}/remediation/validate",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "append-only remediation validation receipt when body provided",
        },
        {
            "id": "bounded_canonical_query",
            "method": "GET",
            "path": f"{base}/query",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "read-only bounded canonical projection slice",
        },
        {
            "id": "stabilization_proof_snapshot",
            "method": "GET",
            "path": f"{base}/stabilization-proof",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "read-only stabilization / economics proof snapshot",
        },
        {
            "id": "run_stabilization_proof_pass",
            "method": "POST",
            "path": f"{base}/stabilization-proof/run",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "recomputes proof checklist; optional append-only ledger row",
        },
        {
            "id": "list_stabilization_proof_runs",
            "method": "GET",
            "path": f"{base}/stabilization-proof/runs",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "read-only stabilization proof ledger tail",
        },
        {
            "id": "certification_pack_snapshot",
            "method": "GET",
            "path": f"{base}/certification-pack",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "read-only Step 18 certification pack + closure matrix",
        },
        {
            "id": "archive_certification_pack",
            "method": "POST",
            "path": f"{base}/certification-pack/archive",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "append-only certification archive when closure hard gates pass",
        },
        {
            "id": "list_certification_archives",
            "method": "GET",
            "path": f"{base}/certification-pack/archives",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "read-only certification archive ledger tail",
        },
    ]

    return {
        "tenant_id": str(tenant_id),
        "canonical_control_plane_schema_version": CANONICAL_CONTROL_PLANE_SCHEMA_VERSION,
        "health_overview": {
            "materialization_row_count": mat_count,
            "field_lineage_row_count": lineage_count,
            "provenance_record_row_count": prov_count,
            "temporal_supersession_row_count": supersession_count,
            "active_canonical_failure_count": len(active_failures),
            "active_canonical_failure_classes": dict(failure_classes),
            "replay_jobs_in_window": len(replay_jobs),
            "replay_job_status_counts": dict(replay_status_counts),
            "replay_divergence_class_totals_recent_completed": dict(div_totals),
            "mapping_bundle_inventory_count": len(bundle_ids),
            "mapping_pin_row_count": len(pins_list),
            "ambiguity_by_status": ambiguity.get("by_status"),
            "ambiguity_open_count": open_amb,
            "ambiguity_explosion_warn": ambiguity_explosion_warn,
            "verification_freshness_label": freshness,
            "last_verification_passed": bool(last_ver.passed) if last_ver is not None else None,
            "latest_remediation_validation": (
                {
                    "id": latest_remediation.id,
                    "result_status": latest_remediation.result_status,
                    "created_at": latest_remediation.created_at.isoformat(),
                }
                if latest_remediation is not None
                else None
            ),
            "replay_dependency_edge_count": int(coverage_summary.get("replay_dependency_edge_count", 0)),
            "replay_dependency_cycle_detected": bool(
                coverage_summary.get("replay_dependency_cycle_detected", False)
            ),
            "orphan_dependency_ref_count": int(coverage_summary.get("orphan_dependency_ref_count", 0)),
        },
        "inspectors": {
            "canonical_overview_inspector": {
                "materialization_row_count": mat_count,
                "bundle_inventory_head": bundle_ids[:12],
            },
            "mapping_inspector": {
                "registry_schema_version": registry.get("registry_schema_version"),
                "bundle_count": len(bundle_ids),
                "compatibility_edge_count": len(registry.get("compatibility_edges") or []),
                "pin_count": len(pins_list),
            },
            "replay_rebuild_inspector": {
                "recent_jobs": [_replay_job_public(j) for j in replay_jobs[:10]],
                "inflight_count": sum(1 for j in replay_jobs if j.status == "running"),
                "replay_dag_pressure": {
                    "dependency_edges": int(coverage_summary.get("replay_dependency_edge_count", 0)),
                    "cycle_detected": bool(coverage_summary.get("replay_dependency_cycle_detected", False)),
                    "orphan_pressure": int(coverage_summary.get("orphan_dependency_ref_count", 0)),
                },
            },
            "ambiguity_inspector": ambiguity,
            "provenance_inspector": {
                "provenance_record_row_count": prov_count,
                "field_lineage_row_count": lineage_count,
            },
            "verification_inspector": {
                "last_run": verification_truth,
                "freshness_label": freshness,
            },
            "coverage_inspector": {
                "summary": coverage_summary,
                "rows": list(coverage.get("rows") or [])[:80],
                "coverage_connector_rollups": list(coverage.get("connector_rollups") or []),
                "coverage_totals": dict(coverage.get("totals") or {}),
                "operational_truth": {
                    "canonical_coverage_matrix_schema_version": coverage.get(
                        "canonical_coverage_matrix_schema_version"
                    ),
                    "phase03_exit_audit_head": list(coverage.get("phase03_exit_audit") or [])[:40],
                    "dead_route_pair_count": coverage_summary.get("dead_route_pair_count"),
                    "dormant_route_pair_count": coverage_summary.get("dormant_route_pair_count"),
                    "replay_active_pair_count": coverage_summary.get("replay_active_pair_count"),
                    "topology_active_pair_count": coverage_summary.get("topology_active_pair_count"),
                    "determinism_drift_events": coverage_summary.get("determinism_drift_events"),
                    "orphan_backlog_pressure": coverage_summary.get("orphan_backlog_pressure"),
                },
            },
            "recovery_inspector": {
                "active_failure_exemplars": [
                    {
                        "gap_id": c.gap_id,
                        "failure_class": c.failure_class,
                        "degradation_state": c.degradation_state,
                        "scope_kind": c.scope_kind,
                    }
                    for c in active_failures[:40]
                ],
                "failure_sync": failures_sync,
            },
        },
        "verification_checklist": {
            "passed": all(bool(x["passed"]) for x in checklist),
            "items": checklist,
        },
        "verification_truth": verification_truth,
        "logical_information_architecture": logical_ia,
        "actions": actions,
        "warnings": {
            "must_not_assume": [
                "substrate counts are not semantic completeness",
                "PASS on last verification does not imply organizational truth",
                "absence of recorded ambiguity does not imply absence of provider-side ambiguity",
            ],
            "canonical_failure_sync": failures_sync,
        },
    }


def verify_phase03_step16_canonical_control_plane_contract(
    *,
    control_plane_payload: dict[str, Any],
) -> dict[str, Any]:
    required_top = {
        "tenant_id",
        "canonical_control_plane_schema_version",
        "health_overview",
        "inspectors",
        "verification_checklist",
        "verification_truth",
        "logical_information_architecture",
        "actions",
        "warnings",
    }
    required_health = {
        "materialization_row_count",
        "active_canonical_failure_count",
        "mapping_bundle_inventory_count",
        "verification_freshness_label",
        "ambiguity_open_count",
    }
    required_inspectors = {
        "canonical_overview_inspector",
        "mapping_inspector",
        "replay_rebuild_inspector",
        "ambiguity_inspector",
        "provenance_inspector",
        "verification_inspector",
        "coverage_inspector",
        "recovery_inspector",
    }
    required_ia = {
        "A_overview",
        "B_canonical_objects",
        "C_mapping",
        "D_replay_rebuild",
        "E_ambiguity",
        "F_provenance",
        "G_verification",
        "H_recovery",
    }
    top_ok = required_top.issubset(control_plane_payload.keys())
    health = control_plane_payload.get("health_overview", {})
    inspectors = control_plane_payload.get("inspectors", {})
    checklist = control_plane_payload.get("verification_checklist", {})
    actions = control_plane_payload.get("actions", [])
    ia = control_plane_payload.get("logical_information_architecture", {})
    vt = control_plane_payload.get("verification_truth")

    health_ok = isinstance(health, dict) and required_health.issubset(health.keys())
    inspectors_ok = isinstance(inspectors, dict) and required_inspectors.issubset(inspectors.keys())
    checklist_ok = isinstance(checklist, dict) and isinstance(checklist.get("items"), list)
    actions_ok = isinstance(actions, list) and len(actions) >= 5
    ia_ok = isinstance(ia, dict) and required_ia.issubset(ia.keys())
    vt_ok = vt is None or isinstance(vt, dict)

    passed = bool(
        top_ok and health_ok and inspectors_ok and checklist_ok and actions_ok and ia_ok and vt_ok
    )
    return {
        "passed": passed,
        "state": "healthy" if passed else "degraded",
        "checks": [
            {"id": "s16_control_plane_top_level_contract", "passed": bool(top_ok)},
            {"id": "s16_health_overview_contract", "passed": bool(health_ok)},
            {"id": "s16_inspector_surfaces_contract", "passed": bool(inspectors_ok)},
            {"id": "s16_verification_checklist_surface", "passed": bool(checklist_ok)},
            {"id": "s16_operator_actions_surface", "passed": bool(actions_ok)},
            {"id": "s16_logical_ia_surfaces_A_through_H", "passed": bool(ia_ok)},
            {"id": "s16_verification_truth_shape", "passed": bool(vt_ok)},
        ],
    }
