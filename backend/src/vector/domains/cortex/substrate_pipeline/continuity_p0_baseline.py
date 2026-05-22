"""Phase 0 continuity baseline — load/merge, ECS deploy probe, step 0.5 closure."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PHASE0_BASELINE_PREFIX = "continuity_p0_"
P0_A_SCHEMA_COMMIT = "789b25fbcc360488975b9fabb0ae90960fca54c1"

AWS_REGION_DEFAULT = "eu-west-1"
ECS_CLUSTER_DEFAULT = "vector-prod"
ECS_API_SERVICE_DEFAULT = "vector-backend-service"
ECS_WORKER_SERVICE_DEFAULT = "vector-worker-service"


def continuity_p0_baseline_path_v1(
    *,
    repo_root: Path,
    date_suffix: str | None = None,
) -> Path:
    suffix = date_suffix or datetime.now(UTC).strftime("%Y-%m-%d")
    return repo_root / "DOCS" / "audits" / "baselines" / f"{PHASE0_BASELINE_PREFIX}{suffix}.json"


def load_continuity_p0_baseline_v1(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_continuity_p0_baseline_v1(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _image_tag(image: str) -> str:
    if ":" not in image:
        return image
    return image.rsplit(":", 1)[-1]


def _tag_matches_deploy(tag: str, sha: str) -> bool:
    return tag == sha or tag.startswith(sha[:12])


def probe_prod_ecs_deploy_v1(
    *,
    expected_sha: str,
    aws_region: str = AWS_REGION_DEFAULT,
    ecs_cluster: str = ECS_CLUSTER_DEFAULT,
    api_service: str = ECS_API_SERVICE_DEFAULT,
    worker_service: str = ECS_WORKER_SERVICE_DEFAULT,
) -> dict[str, Any]:
    """Describe prod API + worker ECS images and whether tags match ``expected_sha``."""

    def _service_image(service_name: str) -> tuple[str, str]:
        raw = subprocess.check_output(
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
        image = subprocess.check_output(
            [
                "aws",
                "ecs",
                "describe-task-definition",
                "--task-definition",
                raw,
                "--region",
                aws_region,
                "--query",
                "taskDefinition.containerDefinitions[0].image",
                "--output",
                "text",
            ],
            text=True,
        ).strip()
        return raw, image

    api_td, api_image = _service_image(api_service)
    worker_td, worker_image = _service_image(worker_service)
    api_tag = _image_tag(api_image)
    worker_tag = _image_tag(worker_image)
    api_ok = _tag_matches_deploy(api_tag, expected_sha)
    worker_ok = _tag_matches_deploy(worker_tag, expected_sha)
    same_tag = api_tag == worker_tag
    closure_ok = api_ok and worker_ok and same_tag

    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "git_sha_full": expected_sha,
        "git_sha_short": expected_sha[:12],
        "aws_region": aws_region,
        "ecs_cluster": ecs_cluster,
        "api": {
            "service": api_service,
            "task_definition": api_td,
            "image": api_image,
            "image_tag": api_tag,
        },
        "worker": {
            "service": worker_service,
            "task_definition": worker_td,
            "image": worker_image,
            "image_tag": worker_tag,
        },
        "verification": {
            "api_image_matches_closure_sha": api_ok,
            "worker_image_matches_closure_sha": worker_ok,
            "both_services_on_same_tag": same_tag,
            "deploy_matches_closure_sha": closure_ok,
        },
    }


def merge_step_0_2_deploy_into_baseline_v1(
    baseline: dict[str, Any],
    deploy: dict[str, Any],
) -> dict[str, Any]:
    """Update root deploy fields and ``step_0_2_deploy`` without dropping other steps."""
    ver = dict(deploy.get("verification") or {})
    closure_ok = bool(ver.get("deploy_matches_closure_sha"))
    ver["deploy_step_02_pass"] = closure_ok
    step = {**deploy, "step": "0.2_deploy_backend_worker", "verification": ver}
    baseline["phase"] = "continuity_p0"
    baseline["step"] = "0.2_deploy_backend_worker"
    baseline["recorded_at"] = deploy.get("recorded_at")
    baseline["git_sha_full"] = deploy["git_sha_full"]
    baseline["git_sha_short"] = deploy["git_sha_short"]
    baseline["aws_region"] = deploy["aws_region"]
    baseline["ecs_cluster"] = deploy["ecs_cluster"]
    baseline["api"] = deploy["api"]
    baseline["worker"] = deploy["worker"]
    baseline["verification"] = step["verification"]
    baseline["p0_a_schema_packaging_commit"] = baseline.get(
        "p0_a_schema_packaging_commit", P0_A_SCHEMA_COMMIT
    )
    baseline["step_0_2_deploy"] = step
    return baseline


def evaluate_phase0_prerequisites_v1(baseline: dict[str, Any]) -> dict[str, bool]:
    s03 = baseline.get("step_0_3_pipeline_recovery") or {}
    s04 = baseline.get("step_0_4_phase05_proof") or {}
    s02 = baseline.get("step_0_2_deploy") or {}
    v03 = s03.get("verification") or {}
    v04 = s04.get("verification") or {}
    return {
        "step_02_artifact_present": bool(s02 or baseline.get("git_sha_full")),
        "step_03_pass": bool(v03.get("step_03_pass")),
        "step_04_pass": bool(v04.get("step_04_pass") or s04.get("p0_b_pass")),
    }


def build_step_0_5_phase0_closure_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    baseline: dict[str, Any],
    phase0_commits: dict[str, str] | None = None,
) -> dict[str, Any]:
    prerequisites = evaluate_phase0_prerequisites_v1(baseline)
    deploy_ok = bool(
        (prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha")
    )
    prereq_ok = all(prerequisites.values())
    step_05_pass = deploy_ok and prereq_ok

    return {
        "step": "0.5_phase0_closure",
        "recorded_at": datetime.now(UTC).isoformat(),
        "closure_git_sha": closure_git_sha,
        "closure_git_sha_short": closure_git_sha[:12],
        "phase0_commits": phase0_commits
        or {
            "p0_a_schema_packaging": P0_A_SCHEMA_COMMIT,
            "p0_2_deploy": baseline.get("git_sha_full"),
            "p0_3_recovery": "3cd8561539656d6c1196144755bb457b8b415103",
            "p0_4_phase05_proof": closure_git_sha,
        },
        "prod_deploy": prod_deploy,
        "prerequisites": prerequisites,
        "verification": {
            "step_05_pass": step_05_pass,
            "phase_0_complete": step_05_pass,
            "artifact_ready_for_phase_1": step_05_pass,
        },
        "notes": (
            "Step 0.5 records the Phase 0 closure deploy SHA in the committed baseline artifact. "
            "Both ECS services must run the same ECR tag equal to closure_git_sha."
        ),
    }


def apply_step_0_5_to_baseline_v1(
    baseline: dict[str, Any],
    closure: dict[str, Any],
) -> dict[str, Any]:
    baseline["step_0_5_phase0_closure"] = closure
    baseline["phase0_closure_git_sha"] = closure["closure_git_sha"]
    baseline["phase0_complete"] = closure["verification"]["phase_0_complete"]
    return baseline
