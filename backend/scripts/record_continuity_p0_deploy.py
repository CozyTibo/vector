#!/usr/bin/env python3
"""Record Phase 0 deploy SHA + verify prod ECS images match (step 0.2 / 0.5 baseline)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")
ECS_CLUSTER = os.environ.get("ECS_CLUSTER", "vector-prod")
ECS_SERVICE = os.environ.get("ECS_SERVICE", "vector-backend-service")
ECS_WORKER_SERVICE = os.environ.get("ECS_WORKER_SERVICE", "vector-worker-service")
ECS_TASK_DEFINITION = os.environ.get("ECS_TASK_DEFINITION", "vector-backend")
ECS_WORKER_TASK_DEFINITION = os.environ.get("ECS_WORKER_TASK_DEFINITION", "vector-backend-worker")

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINES_DIR = REPO_ROOT / "DOCS" / "audits" / "baselines"


def _git_sha(expected: str | None) -> str:
    if expected:
        return expected.strip()
    out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True)
    return out.strip()


def _service_image(service_name: str) -> tuple[str, str]:
    """Return (task_definition_arn, container_image)."""
    raw = subprocess.check_output(
        [
            "aws",
            "ecs",
            "describe-services",
            "--cluster",
            ECS_CLUSTER,
            "--services",
            service_name,
            "--region",
            AWS_REGION,
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
            AWS_REGION,
            "--query",
            "taskDefinition.containerDefinitions[0].image",
            "--output",
            "text",
        ],
        text=True,
    ).strip()
    return raw, image


def _image_tag(image: str) -> str:
    if ":" not in image:
        return image
    return image.rsplit(":", 1)[-1]


def main() -> int:
    expected_sha = _git_sha(os.environ.get("CONTINUITY_DEPLOY_GIT_SHA"))
    short = expected_sha[:12]

    api_td, api_image = _service_image(ECS_SERVICE)
    worker_td, worker_image = _service_image(ECS_WORKER_SERVICE)
    api_tag = _image_tag(api_image)
    worker_tag = _image_tag(worker_image)

    def _tag_matches_deploy(tag: str, sha: str) -> bool:
        return tag == sha or tag.startswith(sha[:12])

    images_match = _tag_matches_deploy(api_tag, expected_sha) and _tag_matches_deploy(
        worker_tag, expected_sha
    )

    record = {
        "phase": "continuity_p0",
        "step": "0.2_deploy_backend_worker",
        "recorded_at": datetime.now(UTC).isoformat(),
        "git_sha_full": expected_sha,
        "git_sha_short": short,
        "aws_region": AWS_REGION,
        "ecs_cluster": ECS_CLUSTER,
        "api": {
            "service": ECS_SERVICE,
            "task_definition": api_td,
            "image": api_image,
            "image_tag": api_tag,
        },
        "worker": {
            "service": ECS_WORKER_SERVICE,
            "task_definition": worker_td,
            "image": worker_image,
            "image_tag": worker_tag,
        },
        "verification": {
            "api_image_matches_git_sha": _tag_matches_deploy(api_tag, expected_sha),
            "worker_image_matches_git_sha": _tag_matches_deploy(worker_tag, expected_sha),
            "both_services_on_same_tag": api_tag == worker_tag,
            "deploy_step_02_pass": images_match and api_tag == worker_tag,
        },
        "p0_a_schema_packaging_commit": "789b25fbcc360488975b9fabb0ae90960fca54c1",
        "notes": (
            "Step 0.2 complete when both ECS services run ECR tags equal deploy git SHA "
            "(includes bundled OCTS walk policy under traversal/schemas)."
        ),
    }

    date_suffix = datetime.now(UTC).strftime("%Y-%m-%d")
    out_path = BASELINES_DIR / f"continuity_p0_{date_suffix}.json"
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    print(f"wrote {out_path}", file=sys.stderr)

    if not record["verification"]["deploy_step_02_pass"]:
        print(
            f"FAIL: expected both images tagged {expected_sha}, "
            f"got api={api_tag} worker={worker_tag}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
