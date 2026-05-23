"""Phase D step D2 — prod ECS GitHub ingest caps aligned to code defaults (10/16/120)."""

from __future__ import annotations

import inspect
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.execution_ingest_deferral_monitoring import (
    build_deferral_release_monitor_v1,
    snapshot_github_ingest_caps_extended_v1,
)
from vector.domains.cortex.ingestion.github_ingest_caps_code_defaults import (
    GITHUB_CAP_CODE_DEFAULTS_V1,
    evaluate_ecs_env_matches_code_defaults_v1,
    extract_github_cap_env_from_ecs_task_definition_v1,
    merge_github_caps_into_ecs_task_definition_v1,
    settings_defaults_match_code_v1,
    verify_infra_ecs_task_json_github_caps_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    AWS_REGION_DEFAULT,
    ECS_API_SERVICE_DEFAULT,
    ECS_CLUSTER_DEFAULT,
    ECS_WORKER_SERVICE_DEFAULT,
)
from vector.domains.cortex.unlock.step12_track_b_p3 import (
    evaluate_fix6_github_ingest_caps_v1,
    snapshot_fix6_github_ingest_caps_v1,
)
from vector.settings import Settings, get_settings

P0_D2_STEP: str = "step_d2_github_caps_code_defaults"
PHASE_D2_GITHUB_CAPS_SCHEMA_VERSION: int = 1
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_d2_github_caps_align_wiring_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[6]
    errors: list[str] = []

    defaults = settings_defaults_match_code_v1()
    if not defaults["ok"]:
        errors.append(f"settings_defaults_mismatch:{','.join(defaults['mismatches'])}")

    infra = verify_infra_ecs_task_json_github_caps_v1(repo_root=root)
    if not infra["ok"]:
        errors.extend(infra["errors"])

    deploy_yml = root / ".github" / "workflows" / "deploy.yml"
    if not deploy_yml.is_file():
        errors.append("missing_deploy_yml")
    else:
        wf = deploy_yml.read_text(encoding="utf-8")
        if "ecs_align_github_ingest_caps.py" not in wf:
            errors.append("deploy_workflow_missing_github_cap_align")
        if "Align GitHub ingest caps" not in wf:
            errors.append("deploy_workflow_missing_github_cap_align_label")

    align_script = root / "backend" / "scripts" / "ecs_align_github_ingest_caps.py"
    if not align_script.is_file():
        errors.append("missing_ecs_align_github_ingest_caps_script")

    from vector.domains.cortex.unlock import step12_track_b_p3 as s12

    s12_mod_src = inspect.getsource(s12)
    if '"CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO", 5)' in s12_mod_src:
        errors.append("fix6_env_aliases_still_legacy_low_5")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_d2_schema_version": PHASE_D2_GITHUB_CAPS_SCHEMA_VERSION,
        "code_defaults": dict(GITHUB_CAP_CODE_DEFAULTS_V1),
        "settings_defaults_ok": defaults["ok"],
        "infra_ecs_json_ok": infra["ok"],
    }


def _describe_service_task_definition_arn_v1(
    *,
    service_name: str,
    aws_region: str = AWS_REGION_DEFAULT,
    ecs_cluster: str = ECS_CLUSTER_DEFAULT,
) -> str:
    return subprocess.check_output(
        [
            "aws",
            "ecs",
            "describe-services",
            "--cluster",
            ecs_cluster,
            "--services",
            service_name,
            "--region",
            aws_region,
            "--query",
            "services[0].taskDefinition",
            "--output",
            "text",
        ],
        text=True,
    ).strip()


def _fetch_task_definition_json_v1(
    task_definition_arn: str,
    *,
    aws_region: str = AWS_REGION_DEFAULT,
) -> dict[str, Any]:
    raw = subprocess.check_output(
        [
            "aws",
            "ecs",
            "describe-task-definition",
            "--task-definition",
            task_definition_arn,
            "--region",
            aws_region,
            "--query",
            "taskDefinition",
            "--output",
            "json",
        ],
        text=True,
    )
    return json.loads(raw)


def probe_prod_ecs_github_cap_env_v1(
    *,
    aws_region: str = AWS_REGION_DEFAULT,
    ecs_cluster: str = ECS_CLUSTER_DEFAULT,
    api_service: str = ECS_API_SERVICE_DEFAULT,
    worker_service: str = ECS_WORKER_SERVICE_DEFAULT,
) -> dict[str, Any]:
    """Live ECS task definitions — env overrides for Fix-6 trio."""
    api_td_arn = _describe_service_task_definition_arn_v1(
        service_name=api_service, aws_region=aws_region, ecs_cluster=ecs_cluster
    )
    worker_td_arn = _describe_service_task_definition_arn_v1(
        service_name=worker_service, aws_region=aws_region, ecs_cluster=ecs_cluster
    )
    api_td = _fetch_task_definition_json_v1(api_td_arn, aws_region=aws_region)
    worker_td = _fetch_task_definition_json_v1(worker_td_arn, aws_region=aws_region)
    api_env = extract_github_cap_env_from_ecs_task_definition_v1(api_td)
    worker_env = extract_github_cap_env_from_ecs_task_definition_v1(worker_td)
    return {
        "api_task_definition_arn": api_td_arn,
        "worker_task_definition_arn": worker_td_arn,
        "api": evaluate_ecs_env_matches_code_defaults_v1(api_env),
        "worker": evaluate_ecs_env_matches_code_defaults_v1(worker_env),
        "api_env": api_env,
        "worker_env": worker_env,
    }


def snapshot_d2_github_caps_truth_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    probe_ecs: bool = True,
) -> dict[str, Any]:
    settings = get_settings()
    fix6 = snapshot_fix6_github_ingest_caps_v1(settings=settings)
    extended = snapshot_github_ingest_caps_extended_v1(settings=settings)
    fix6_ok, fix6_detail, _ = evaluate_fix6_github_ingest_caps_v1(
        settings=settings, require_recommended=True
    )
    deferral = build_deferral_release_monitor_v1(session, tenant_id=tenant_id)
    deferral_counts = dict(deferral.get("deferral_counts") or {})

    ecs_probe: dict[str, Any] = {"skipped": True}
    if probe_ecs:
        try:
            ecs_probe = probe_prod_ecs_github_cap_env_v1()
            ecs_probe["skipped"] = False
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as exc:
            ecs_probe = {"skipped": True, "error": str(exc)[:500]}

    return {
        "tenant_id": str(tenant_id),
        "code_defaults": dict(GITHUB_CAP_CODE_DEFAULTS_V1),
        "settings_caps": {
            "fix6": fix6,
            "extended": extended,
            "meets_fix6_recommended": bool(extended.get("meets_fix6_recommended")),
            "fix6_require_recommended_pass": fix6_ok,
            "fix6_detail": fix6_detail,
        },
        "deferral_totals": {
            "deferred_total": int(deferral_counts.get("deferred_total") or 0),
            "deferred_retry_ready": int(deferral_counts.get("deferred_retry_ready") or 0),
            "deferred_permanent_orphan": int(
                deferral_counts.get("deferred_permanent_orphan") or 0
            ),
            "deferred_waiting_cooldown": int(
                deferral_counts.get("deferred_waiting_cooldown") or 0
            ),
        },
        "ecs_github_cap_env": ecs_probe,
        "merge_helper_present": callable(merge_github_caps_into_ecs_task_definition_v1),
    }


def evaluate_p0_d2_github_caps_align_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    wiring: dict[str, Any] | None = None,
    deploy_recorded_at: Any = None,
    trace_only: bool = False,
    require_prod_ecs_aligned: bool = True,
) -> dict[str, Any]:
    wiring = dict(wiring or snapshot.get("wiring") or {})
    settings_caps = dict(snapshot.get("settings_caps") or {})
    ecs = dict(snapshot.get("ecs_github_cap_env") or {})
    deferral = dict(snapshot.get("deferral_totals") or {})

    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    api_match = bool((ecs.get("api") or {}).get("matches_code_defaults"))
    worker_match = bool((ecs.get("worker") or {}).get("matches_code_defaults"))
    ecs_skipped = bool(ecs.get("skipped"))
    api_legacy = bool((ecs.get("api") or {}).get("has_legacy_low_override"))
    worker_legacy = bool((ecs.get("worker") or {}).get("has_legacy_low_override"))

    prod_ecs_ok = (api_match and worker_match) if not ecs_skipped else False
    if not require_prod_ecs_aligned and ecs_skipped:
        prod_ecs_ok = True

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "settings_defaults_match_code": bool(wiring.get("settings_defaults_ok")),
        "infra_ecs_json_has_code_defaults": bool(wiring.get("infra_ecs_json_ok")),
        "local_settings_meets_fix6_recommended": bool(
            settings_caps.get("meets_fix6_recommended")
        ),
        "fix6_require_recommended_pass": bool(settings_caps.get("fix6_require_recommended_pass")),
        "prod_api_ecs_caps_match_code_defaults": (
            api_match if require_prod_ecs_aligned and not ecs_skipped else prod_ecs_ok or trace_only
        ),
        "prod_worker_ecs_caps_match_code_defaults": (
            worker_match
            if require_prod_ecs_aligned and not ecs_skipped
            else prod_ecs_ok or trace_only
        ),
        "no_legacy_low_override_api": (
            (not api_legacy) if require_prod_ecs_aligned and not ecs_skipped else True
        ),
        "no_legacy_low_override_worker": (
            (not worker_legacy) if require_prod_ecs_aligned and not ecs_skipped else True
        ),
        "deferral_totals_snapshot_present": "deferred_total" in deferral,
        "phase_d2_schema_version": int(wiring.get("phase_d2_schema_version") or 0)
        >= PHASE_D2_GITHUB_CAPS_SCHEMA_VERSION,
    }
    checks_advisory = {
        "deferral_totals": deferral,
        "fix6_detail": settings_caps.get("fix6_detail"),
        "ecs_probe_skipped": ecs_skipped,
        "ecs_api_env": ecs.get("api_env"),
        "ecs_worker_env": ecs.get("worker_env"),
        "api_legacy_low": api_legacy,
        "worker_legacy_low": worker_legacy,
        "code_defaults": snapshot.get("code_defaults"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)

    p0_d2_pass = all(checks.values())
    return {
        "step": P0_D2_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_d2_pass": p0_d2_pass,
        "verification": {
            "step_d2_pass": p0_d2_pass,
            "cleared_for_phase_d3": p0_d2_pass,
            "github_caps_at_code_defaults": checks.get("prod_api_ecs_caps_match_code_defaults"),
        },
    }
