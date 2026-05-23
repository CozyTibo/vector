"""Phase D step D1 — admin primary KPI = drainable_routable + execution island list."""

from __future__ import annotations

import inspect
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.pipeline.pipeline_admin_operator_kpi import (
    P0_D1_STEP,
    PHASE_D1_OPERATOR_KPI_SCHEMA_VERSION,
    build_operator_primary_kpi_v1,
    is_admin_primary_kpi_drainable_enabled_v1,
)
from vector.domains.cortex.unlock.step12_track_b_p3 import evaluate_fix7_admin_metric_truth_v1
from vector.settings import Settings, get_settings

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_d1_admin_operator_primary_kpi_wiring_v1() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.completeness import canonical_completeness_projection as can_mod
    from vector.domains.cortex.pipeline import pipeline_admin_overview as pipe_mod

    can_src = inspect.getsource(can_mod.project_canonical_completeness_v1)
    pipe_src = inspect.getsource(pipe_mod)
    for needle in (
        "drainable_routable_estimate",
        "operator_kpi_primary",
        "operator_primary_kpi",
        "build_operator_primary_kpi_v1",
        "_canonical_operator_backlog_count",
    ):
        if needle not in can_src and needle not in pipe_src:
            errors.append(f"wiring_missing_{needle}")

    fix7_ok, fix7_detail = evaluate_fix7_admin_metric_truth_v1()
    if not fix7_ok:
        errors.append(f"fix7_admin_metric_truth:{fix7_detail}")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_d1_schema_version": PHASE_D1_OPERATOR_KPI_SCHEMA_VERSION,
        "drainable_primary_enabled": bool(
            Settings.model_fields["cortex_admin_primary_kpi_drainable"].default
        ),
        "fix7_detail": fix7_detail,
    }


def snapshot_d1_operator_primary_kpi_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    kpi = build_operator_primary_kpi_v1(session, tenant_id=tenant_id, settings=get_settings())
    phases_payload: dict[str, Any] = {}
    try:
        from vector.domains.cortex.pipeline.pipeline_admin_overview import (
            build_pipeline_overview_phases_v1,
        )

        phases_payload = build_pipeline_overview_phases_v1(
            session, get_settings(), tenant_id=tenant_id
        )
    except Exception as exc:
        phases_payload = {"error": str(exc)[:500]}

    canonical_phase = next(
        (p for p in phases_payload.get("phases") or [] if p.get("phase") == "canonical"),
        None,
    )
    overview_kpi = phases_payload.get("operator_primary_kpi") or {}

    return {
        "operator_primary_kpi": kpi,
        "overview_operator_primary_kpi": overview_kpi,
        "canonical_phase_backlog_count": (canonical_phase or {}).get("backlog_count"),
        "canonical_phase_headline": (canonical_phase or {}).get("headline"),
        "canonical_signals": [
            s.get("key") for s in (canonical_phase or {}).get("signals") or [] if isinstance(s, dict)
        ],
        "execution_island_count": kpi.get("execution_island_count"),
        "execution_islands_len": len(kpi.get("execution_islands") or []),
    }


def evaluate_p0_d1_admin_operator_primary_kpi_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    deploy_recorded_at: Any = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    wiring = dict(snapshot.get("wiring") or {})
    kpi = dict(snapshot.get("operator_primary_kpi") or {})
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))

    primary_key = str(kpi.get("primary_metric_key") or "")
    signals = list(snapshot.get("canonical_signals") or [])
    backlog = snapshot.get("canonical_phase_backlog_count")
    drainable = int(kpi.get("drainable_routable_estimate") or 0)

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "fix7_admin_metric_truth": bool(wiring.get("wiring_ok")),
        "primary_metric_is_drainable": primary_key == "drainable_routable_estimate",
        "raw_minus_mat_banner_deprecated": bool(kpi.get("raw_minus_mat_banner_deprecated")),
        "operator_primary_kpi_on_overview": bool(snapshot.get("overview_operator_primary_kpi")),
        "canonical_backlog_matches_drainable": backlog == drainable,
        "canonical_first_signal_drainable": signals and signals[0] == "drainable_routable",
        "execution_islands_exposed": isinstance(kpi.get("execution_islands"), list),
        "phase_d1_schema_version": int(kpi.get("schema_version") or 0)
        >= PHASE_D1_OPERATOR_KPI_SCHEMA_VERSION,
    }
    checks_advisory = {
        "primary_metric_value": kpi.get("primary_metric_value"),
        "raw_minus_mat_admin_gap": kpi.get("raw_minus_mat_admin_gap"),
        "untreated_routable_estimate": kpi.get("untreated_routable_estimate"),
        "execution_island_count": snapshot.get("execution_island_count"),
        "canonical_phase_headline": snapshot.get("canonical_phase_headline"),
        "fix7_detail": wiring.get("fix7_detail"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_d1_pass = all(checks.values())
    return {
        "step": P0_D1_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_d1_pass": p0_d1_pass,
        "verification": {
            "step_d1_pass": p0_d1_pass,
            "cleared_for_phase_d2": p0_d1_pass,
            "admin_shows_drainable_not_raw_mat_hero": checks.get("primary_metric_is_drainable"),
        },
    }
