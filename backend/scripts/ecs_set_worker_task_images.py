#!/usr/bin/env python3
"""Set the same worker image (and VECTOR_GIT_SHA) on every ECS worker task container.

Ingestion/substrate worker task definitions run ``worker`` and ``celery-beat`` sidecars.
Deploy must refresh both; updating only ``containerDefinitions[0]`` leaves Beat on an
old image without new beat_schedule entries (e.g. canon materialization tick).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def apply_worker_image_to_all_containers(
    task_def: dict[str, Any],
    *,
    image: str,
    git_sha: str,
) -> dict[str, Any]:
    out = dict(task_def)
    containers: list[dict[str, Any]] = []
    for raw in out.get("containerDefinitions") or []:
        container = dict(raw)
        container["image"] = image
        env = [dict(e) for e in container.get("environment") or []]
        env = [e for e in env if e.get("name") != "VECTOR_GIT_SHA"]
        env.append({"name": "VECTOR_GIT_SHA", "value": git_sha})
        container["environment"] = env
        containers.append(container)
    if not containers:
        msg = "task definition has no containerDefinitions"
        raise ValueError(msg)
    out["containerDefinitions"] = containers
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Align all worker ECS container images")
    parser.add_argument("input", type=Path, help="Source ECS task definition JSON")
    parser.add_argument("output", type=Path, help="Output JSON path")
    parser.add_argument("--image", required=True, help="Full ECR image URI including tag")
    parser.add_argument("--git-sha", required=True, help="Deploy git SHA (VECTOR_GIT_SHA)")
    args = parser.parse_args()

    task_def = json.loads(args.input.read_text(encoding="utf-8"))
    updated = apply_worker_image_to_all_containers(
        task_def,
        image=args.image,
        git_sha=args.git_sha,
    )
    args.output.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
