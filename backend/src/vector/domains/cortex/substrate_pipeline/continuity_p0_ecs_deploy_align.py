"""Phase A step A2 — ECS API + worker deploy alignment proof (generic closure SHA)."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    AWS_REGION_DEFAULT,
    ECS_API_SERVICE_DEFAULT,
    ECS_CLUSTER_DEFAULT,
    ECS_WORKER_SERVICE_DEFAULT,
    probe_prod_ecs_deploy_v1,
    snapshot_prod_ecs_deploy_v1,
)

ECS_WORKER_TASK_DEFINITION_DEFAULT = "vector-backend-worker"

P0_A2_STEP = "step_a2_ecs_deploy_align"

REPO_ROOT_HINT = "vector"


def verify_a2_ecs_deploy_align_wiring_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    """Static wiring: deploy workflow + local prod deploy script + post-deploy verify."""
    root = repo_root
    if root is None:
        root = Path(__file__).resolve().parents[6]
    errors: list[str] = []
    workflow = root / ".github" / "workflows" / "deploy.yml"
    deploy_sh = root / "backend" / "scripts" / "prod_deploy_backend_worker.sh"
    if not workflow.is_file():
        errors.append("missing_deploy_workflow")
    else:
        wf = workflow.read_text(encoding="utf-8")
        if "Verify prod image tags match deploy SHA" not in wf:
            errors.append("deploy_workflow_missing_sha_verify_step")
        if "vector-worker-service" not in wf or "services-stable" not in wf:
            errors.append("deploy_workflow_missing_worker_stable_wait")
    if not deploy_sh.is_file():
        errors.append("missing_prod_deploy_backend_worker_sh")
    else:
        sh = deploy_sh.read_text(encoding="utf-8")
        if "services-stable" not in sh:
            errors.append("prod_deploy_script_missing_stable_wait")
        if "WORKER_REPOSITORY" not in sh:
            errors.append("prod_deploy_script_missing_worker_repo")
    return {"wiring_ok": not errors, "errors": errors}


def realign_ecs_worker_to_api_image_tag_v1(
    *,
    aws_region: str = AWS_REGION_DEFAULT,
    ecs_cluster: str = ECS_CLUSTER_DEFAULT,
    api_service: str = ECS_API_SERVICE_DEFAULT,
    worker_service: str = ECS_WORKER_SERVICE_DEFAULT,
    worker_task_family: str = ECS_WORKER_TASK_DEFINITION_DEFAULT,
) -> dict[str, Any]:
    """ECS-only: point worker service at the same image tag as API (no docker build)."""
    before = snapshot_prod_ecs_deploy_v1(
        aws_region=aws_region,
        ecs_cluster=ecs_cluster,
        api_service=api_service,
        worker_service=worker_service,
    )
    api_tag = str(before["api"]["image_tag"])
    worker_tag = str(before["worker"]["image_tag"])
    if api_tag == worker_tag:
        return {
            "realigned": False,
            "reason": "already_aligned",
            "api_image_tag": api_tag,
            "worker_image_tag": worker_tag,
            "snapshot_before": before,
        }

    worker_image_uri = str(before["worker"]["image"])
    repo_uri = worker_image_uri.rsplit(":", 1)[0]
    new_image = f"{repo_uri}:{api_tag}"

    td_arn = str(before["worker"]["task_definition"])
    raw = subprocess.check_output(
        [
            "aws",
            "ecs",
            "describe-task-definition",
            "--task-definition",
            td_arn,
            "--region",
            aws_region,
            "--query",
            "taskDefinition",
            "--output",
            "json",
        ],
        text=True,
    )
    td = json.loads(raw)
    for key in (
        "taskDefinitionArn",
        "revision",
        "status",
        "requiresAttributes",
        "compatibilities",
        "registeredAt",
        "registeredBy",
    ):
        td.pop(key, None)
    td["containerDefinitions"][0]["image"] = new_image

    registered = subprocess.check_output(
        [
            "aws",
            "ecs",
            "register-task-definition",
            "--cli-input-json",
            json.dumps(td),
            "--region",
            aws_region,
            "--query",
            "taskDefinition.taskDefinitionArn",
            "--output",
            "text",
        ],
        text=True,
    ).strip()

    subprocess.check_call(
        [
            "aws",
            "ecs",
            "update-service",
            "--cluster",
            ecs_cluster,
            "--service",
            worker_service,
            "--task-definition",
            registered,
            "--force-new-deployment",
            "--region",
            aws_region,
        ],
        stdout=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [
            "aws",
            "ecs",
            "wait",
            "services-stable",
            "--cluster",
            ecs_cluster,
            "--services",
            worker_service,
            "--region",
            aws_region,
        ],
    )
    after = snapshot_prod_ecs_deploy_v1(
        aws_region=aws_region,
        ecs_cluster=ecs_cluster,
        api_service=api_service,
        worker_service=worker_service,
    )
    return {
        "realigned": True,
        "reason": "worker_updated_to_api_tag",
        "api_image_tag": api_tag,
        "worker_image_tag_before": worker_tag,
        "new_worker_image": new_image,
        "registered_task_definition": registered,
        "snapshot_before": before,
        "snapshot_after": after,
    }


def wait_for_prod_ecs_deploy_v1(
    *,
    expected_sha: str,
    timeout_seconds: int = 600,
    poll_interval_seconds: int = 30,
    aws_region: str = AWS_REGION_DEFAULT,
    ecs_cluster: str = ECS_CLUSTER_DEFAULT,
    api_service: str = ECS_API_SERVICE_DEFAULT,
    worker_service: str = ECS_WORKER_SERVICE_DEFAULT,
) -> dict[str, Any]:
    """Poll until API + worker ECS images match ``expected_sha`` and share the same tag."""
    deadline = time.monotonic() + max(0, timeout_seconds)
    last: dict[str, Any] = {}
    polls = 0
    while True:
        polls += 1
        last = probe_prod_ecs_deploy_v1(
            expected_sha=expected_sha,
            aws_region=aws_region,
            ecs_cluster=ecs_cluster,
            api_service=api_service,
            worker_service=worker_service,
        )
        last["poll_count"] = polls
        if last["verification"]["deploy_matches_closure_sha"]:
            last["wait_outcome"] = "matched"
            return last
        if time.monotonic() >= deadline:
            last["wait_outcome"] = "timeout"
            return last
        time.sleep(poll_interval_seconds)


def drive_prod_ecs_deploy_align_v1(
    *,
    repo_root: Path,
    closure_sha: str,
) -> dict[str, Any]:
    """Run ``prod_deploy_backend_worker.sh`` to build/push/register/update both ECS services."""
    script = repo_root / "backend" / "scripts" / "prod_deploy_backend_worker.sh"
    if not script.is_file():
        return {"acquired": False, "reason": "prod_deploy_script_missing", "path": str(script)}
    cmd = [str(script), closure_sha]
    started = datetime.now(UTC)
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return {
            "acquired": False,
            "reason": "prod_deploy_exec_failed",
            "error": str(exc),
        }
    return {
        "acquired": proc.returncode == 0,
        "closure_sha": closure_sha,
        "started_at": started.isoformat(),
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }


def evaluate_p0_a2_ecs_deploy_align_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    wiring: dict[str, Any] | None = None,
    deploy_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step A2: API and worker ECS services run the same image tag as closure SHA."""
    ver = dict(prod_deploy.get("verification") or {})
    api_tag = str((prod_deploy.get("api") or {}).get("image_tag") or "")
    worker_tag = str((prod_deploy.get("worker") or {}).get("image_tag") or "")
    w = dict(wiring or {})

    checks = {
        "ecs_deploy_matches_closure_sha": bool(ver.get("deploy_matches_closure_sha")) or trace_only,
        "api_image_matches_closure_sha": bool(ver.get("api_image_matches_closure_sha")) or trace_only,
        "worker_image_matches_closure_sha": bool(ver.get("worker_image_matches_closure_sha"))
        or trace_only,
        "both_services_on_same_tag": bool(ver.get("both_services_on_same_tag")),
        "static_wiring_ok": bool(w.get("wiring_ok")) if w else True,
        "deploy_drive_ok": bool((deploy_drive or {}).get("acquired")) if deploy_drive else True,
    }
    checks_advisory = {
        "api_image_tag": api_tag,
        "worker_image_tag": worker_tag,
        "closure_git_sha_short": closure_git_sha[:12],
        "wait_outcome": prod_deploy.get("wait_outcome"),
        "poll_count": prod_deploy.get("poll_count"),
        "deploy_exit_code": (deploy_drive or {}).get("exit_code"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    step_a2_pass = all(checks.values())
    return {
        "step": P0_A2_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "wiring": w,
        "deploy_drive": deploy_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_a2_pass": step_a2_pass,
        "verification": {
            "step_a2_pass": step_a2_pass,
            "cleared_for_a3": step_a2_pass,
            "deploy_matches_closure_sha": bool(ver.get("deploy_matches_closure_sha")),
        },
    }
