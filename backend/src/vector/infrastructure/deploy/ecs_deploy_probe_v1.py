"""ECS deploy image tag probe — no cortex substrate dependencies."""

from __future__ import annotations

import json
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


def _service_task_definition(
    *,
    aws_region: str,
    ecs_cluster: str,
    service_name: str,
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


def _task_container_images(
    *,
    aws_region: str,
    task_definition: str,
) -> list[str]:
    raw = subprocess.check_output(
        [
            "aws",
            "ecs",
            "describe-task-definition",
            "--task-definition",
            task_definition,
            "--region",
            aws_region,
            "--query",
            "taskDefinition.containerDefinitions[*].image",
            "--output",
            "json",
        ],
        text=True,
    ).strip()
    images = json.loads(raw or "[]")
    return [str(i) for i in images]


def _service_image(
    *,
    aws_region: str,
    ecs_cluster: str,
    service_name: str,
) -> tuple[str, str]:
    """Return task definition ARN and primary (first) container image."""
    raw = _service_task_definition(
        aws_region=aws_region,
        ecs_cluster=ecs_cluster,
        service_name=service_name,
    )
    images = _task_container_images(aws_region=aws_region, task_definition=raw)
    image = images[0] if images else ""
    return raw, image


def _all_container_tags_match(*, images: list[str], expected_sha: str) -> bool:
    if not images:
        return False
    tags = [_image_tag(i) for i in images]
    return all(_tag_matches_deploy(t, expected_sha) for t in tags)


def probe_prod_ecs_deploy_v1(
    *,
    expected_sha: str,
    aws_region: str | None = None,
    ecs_cluster: str | None = None,
    api_service: str | None = None,
    worker_service: str | None = None,
    cortex_worker_service: str | None = None,
    substrate_worker_service: str | None = None,
    **_legacy: Any,
) -> dict[str, Any]:
    """Verify prod API + two worker fleets (ingestion + cortex) match ``expected_sha``."""
    region = (aws_region or os.environ.get("AWS_REGION", "eu-west-1")).strip()
    cluster = (ecs_cluster or os.environ.get("ECS_CLUSTER", "vector-prod")).strip()
    api_svc = (api_service or os.environ.get("ECS_SERVICE", "vector-backend-service")).strip()
    worker_svc = (worker_service or os.environ.get("ECS_WORKER_SERVICE", "vector-worker-service")).strip()
    cortex_svc = (
        cortex_worker_service
        or substrate_worker_service
        or os.environ.get("ECS_CORTEX_WORKER_SERVICE")
        or os.environ.get("ECS_SUBSTRATE_WORKER_SERVICE", "vector-substrate-worker-service")
    ).strip()

    api_td, api_image = _service_image(aws_region=region, ecs_cluster=cluster, service_name=api_svc)
    worker_td = _service_task_definition(aws_region=region, ecs_cluster=cluster, service_name=worker_svc)
    worker_images = _task_container_images(aws_region=region, task_definition=worker_td)
    cortex_td = _service_task_definition(aws_region=region, ecs_cluster=cluster, service_name=cortex_svc)
    cortex_images = _task_container_images(aws_region=region, task_definition=cortex_td)
    worker_image = worker_images[0] if worker_images else ""
    cortex_image = cortex_images[0] if cortex_images else ""

    api_tag = _image_tag(api_image)
    worker_tag = _image_tag(worker_image)
    cortex_tag = _image_tag(cortex_image)
    api_ok = _tag_matches_deploy(api_tag, expected_sha)
    worker_ok = _all_container_tags_match(images=worker_images, expected_sha=expected_sha)
    cortex_ok = _all_container_tags_match(images=cortex_images, expected_sha=expected_sha)
    worker_tags = [_image_tag(i) for i in worker_images]
    cortex_tags = [_image_tag(i) for i in cortex_images]
    same_tag = (
        api_tag == worker_tag == cortex_tag
        and len(set(worker_tags)) <= 1
        and len(set(cortex_tags)) <= 1
    )
    closure_ok = api_ok and worker_ok and cortex_ok and same_tag

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
            "container_images": worker_images,
            "container_image_tags": worker_tags,
        },
        "cortex_worker": {
            "service": cortex_svc,
            "task_definition": cortex_td,
            "image": cortex_image,
            "image_tag": cortex_tag,
            "container_images": cortex_images,
            "container_image_tags": cortex_tags,
        },
        "git_sha_full": expected_sha,
        "git_sha_short": expected_sha[:12],
        "verification": {
            "api_image_matches_closure_sha": api_ok,
            "worker_image_matches_closure_sha": worker_ok,
            "worker_all_containers_match_closure_sha": worker_ok,
            "cortex_worker_image_matches_closure_sha": cortex_ok,
            "cortex_worker_all_containers_match_closure_sha": cortex_ok,
            "all_services_on_same_tag": same_tag,
            "deploy_matches_closure_sha": closure_ok,
        },
    }
