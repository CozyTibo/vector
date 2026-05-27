"""ECS deploy image tag probe — no cortex substrate dependencies."""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from typing import Any


def _image_tag(image: str) -> str:
    if ":" not in image:
        return image
    return image.rsplit(":", 1)[-1]


def _tag_matches_deploy(tag: str, sha: str) -> bool:
    return tag == sha or tag.startswith(sha[:12])


def _service_image(
    *,
    aws_region: str,
    ecs_cluster: str,
    service_name: str,
) -> tuple[str, str]:
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


def probe_prod_ecs_deploy_v1(
    *,
    expected_sha: str,
    aws_region: str | None = None,
    ecs_cluster: str | None = None,
    api_service: str | None = None,
    worker_service: str | None = None,
    substrate_worker_service: str | None = None,
) -> dict[str, Any]:
    """Verify prod API + ingestion worker + default-lane worker images match ``expected_sha``."""
    region = (aws_region or os.environ.get("AWS_REGION", "eu-west-1")).strip()
    cluster = (ecs_cluster or os.environ.get("ECS_CLUSTER", "vector-prod")).strip()
    api_svc = (api_service or os.environ.get("ECS_SERVICE", "vector-backend-service")).strip()
    worker_svc = (worker_service or os.environ.get("ECS_WORKER_SERVICE", "vector-worker-service")).strip()
    substrate_svc = (
        substrate_worker_service
        or os.environ.get("ECS_SUBSTRATE_WORKER_SERVICE", "vector-substrate-worker-service")
    ).strip()

    api_td, api_image = _service_image(aws_region=region, ecs_cluster=cluster, service_name=api_svc)
    worker_td, worker_image = _service_image(
        aws_region=region,
        ecs_cluster=cluster,
        service_name=worker_svc,
    )
    substrate_td, substrate_image = _service_image(
        aws_region=region,
        ecs_cluster=cluster,
        service_name=substrate_svc,
    )

    api_tag = _image_tag(api_image)
    worker_tag = _image_tag(worker_image)
    substrate_tag = _image_tag(substrate_image)
    api_ok = _tag_matches_deploy(api_tag, expected_sha)
    worker_ok = _tag_matches_deploy(worker_tag, expected_sha)
    substrate_ok = _tag_matches_deploy(substrate_tag, expected_sha)
    same_tag = api_tag == worker_tag == substrate_tag
    closure_ok = api_ok and worker_ok and substrate_ok and same_tag

    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "aws_region": region,
        "ecs_cluster": cluster,
        "api": {
            "service": api_svc,
            "task_definition": api_td,
            "image": api_image,
            "image_tag": api_tag,
        },
        "worker": {
            "service": worker_svc,
            "task_definition": worker_td,
            "image": worker_image,
            "image_tag": worker_tag,
        },
        "substrate_worker": {
            "service": substrate_svc,
            "task_definition": substrate_td,
            "image": substrate_image,
            "image_tag": substrate_tag,
        },
        "git_sha_full": expected_sha,
        "git_sha_short": expected_sha[:12],
        "verification": {
            "api_image_matches_closure_sha": api_ok,
            "worker_image_matches_closure_sha": worker_ok,
            "substrate_worker_image_matches_closure_sha": substrate_ok,
            "all_services_on_same_tag": same_tag,
            "deploy_matches_closure_sha": closure_ok,
        },
    }
