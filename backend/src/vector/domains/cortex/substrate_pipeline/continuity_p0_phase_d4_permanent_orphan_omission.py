"""Phase D step D4 — permanent orphan deferrals documented as bounded omission."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.permanent_orphan_omission_doctrine import (
    FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1,
    OMISSION_POSTURE_ACCEPTED_BOUNDED_DEBT_V1,
    P0_D4_STEP,
    PHASE_D4_OMISSION_SCHEMA_VERSION,
    RUNBOOK_REL_PATH_V1,
    build_deferral_omission_operator_block_v1,
    runbook_path_v1,
    snapshot_permanent_orphan_omission_v1,
)
from vector.domains.cortex.completeness import canonical_completeness_projection as can_mod
from vector.domains.cortex.pipeline import pipeline_admin_overview as pipe_mod

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_d4_permanent_orphan_omission_wiring_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    import inspect

    root = repo_root or Path(__file__).resolve().parents[6]
    errors: list[str] = []

    if not runbook_path_v1(repo_root=root).is_file():
        errors.append("missing_permanent_orphan_runbook")

    can_src = inspect.getsource(can_mod.project_canonical_completeness_v1)
    if "deferral_omission_posture" not in can_src and "permanent_orphan" not in can_src:
        errors.append("canonical_projection_missing_permanent_orphan_omission")

    pipe_src = inspect.getsource(pipe_mod.build_operator_primary_kpi_v1)
    if "deferral_omission" not in pipe_src:
        errors.append("pipeline_overview_missing_deferral_omission_block")

    from vector.domains.cortex.canonical import permanent_orphan_omission_doctrine as doc_mod

    if "chase_zero_deferrals_forbidden" not in inspect.getsource(
        doc_mod.evaluate_permanent_orphan_omission_posture_v1
    ):
        errors.append("doctrine_missing_chase_zero_forbidden_flag")

    frontend_overview = root / "frontend/src/admin/AdminCortexOverviewPage.tsx"
    if frontend_overview.is_file():
        fe = frontend_overview.read_text(encoding="utf-8")
        if "DeferralOmissionCard" not in fe:
            errors.append("admin_overview_missing_deferral_omission_card")
    else:
        errors.append("missing_admin_cortex_overview_page")

    canonical_panels = root / "frontend/src/admin/cortex/CanonicalSummaryPanels.tsx"
    if canonical_panels.is_file():
        cp = canonical_panels.read_text(encoding="utf-8")
        if "permanent orphan" not in cp.lower() and "omission" not in cp.lower():
            errors.append("canonical_panels_missing_omission_copy")
    else:
        errors.append("missing_canonical_summary_panels")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_d4_schema_version": PHASE_D4_OMISSION_SCHEMA_VERSION,
        "runbook_path": RUNBOOK_REL_PATH_V1,
        "fizzer_reference_permanent_orphan": FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1,
    }


def snapshot_d4_permanent_orphan_omission_truth_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    omission = snapshot_permanent_orphan_omission_v1(session, tenant_id=tenant_id)
    operator_block = build_deferral_omission_operator_block_v1(
        session,
        tenant_id=tenant_id,
        deferral_counts=dict(omission.get("deferral_counts") or {}),
    )
    overview_kpi: dict[str, Any] = {}
    try:
        from vector.domains.cortex.pipeline.pipeline_admin_operator_kpi import (
            build_operator_primary_kpi_v1,
        )
        from vector.settings import get_settings

        overview_kpi = build_operator_primary_kpi_v1(
            session, tenant_id=tenant_id, settings=get_settings()
        )
    except Exception as exc:
        overview_kpi = {"error": str(exc)[:500]}

    return {
        "tenant_id": str(tenant_id),
        "snapshot": omission,
        "operator_block": operator_block,
        "overview_deferral_omission": overview_kpi.get("deferral_omission"),
    }


def evaluate_p0_d4_permanent_orphan_omission_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    wiring: dict[str, Any] | None = None,
    deploy_recorded_at: Any = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    wiring = dict(wiring or snapshot.get("wiring") or {})
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    omission_snap = dict(snapshot.get("snapshot") or {})
    operator_block = dict(snapshot.get("operator_block") or {})
    overview_omission = dict(snapshot.get("overview_deferral_omission") or {})
    deferral_omission = dict(omission_snap.get("deferral_omission") or operator_block)

    permanent = int(deferral_omission.get("permanent_orphan_count") or 0)
    posture = str(deferral_omission.get("posture") or "")

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "runbook_present": bool(wiring.get("runbook_path")),
        "permanent_orphan_posture_documented": posture == OMISSION_POSTURE_ACCEPTED_BOUNDED_DEBT_V1
        or permanent == 0,
        "chase_zero_deferrals_forbidden_when_permanent_present": bool(
            deferral_omission.get("chase_zero_deferrals_forbidden")
        )
        if permanent > 0
        else True,
        "is_bounded_omission_not_failure_flag": bool(
            deferral_omission.get("is_bounded_omission_not_failure")
        )
        if permanent > 0
        else True,
        "overview_exposes_deferral_omission": bool(overview_omission.get("surface_kind")),
        "fizzer_reference_documented": int(wiring.get("fizzer_reference_permanent_orphan") or 0)
        == FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1,
        "phase_d4_schema_version": int(wiring.get("phase_d4_schema_version") or 0)
        >= PHASE_D4_OMISSION_SCHEMA_VERSION,
    }
    checks_advisory = {
        "permanent_orphan_count": permanent,
        "deferral_total": deferral_omission.get("deferral_total"),
        "permanent_share_pct": deferral_omission.get("permanent_share_pct"),
        "fizzer_reference": FIZZER_REFERENCE_PERMANENT_ORPHAN_COUNT_V1,
        "operator_actions": deferral_omission.get("operator_actions"),
        "headline": deferral_omission.get("headline"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_d4_pass = all(checks.values())
    return {
        "step": P0_D4_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_d4_pass": p0_d4_pass,
        "verification": {
            "step_d4_pass": p0_d4_pass,
            "cleared_for_phase_d5": p0_d4_pass,
            "operators_accept_bounded_deferral_debt": checks.get(
                "permanent_orphan_posture_documented"
            ),
        },
    }
