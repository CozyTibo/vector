#!/usr/bin/env python3
"""Write ingestion-only and substrate-only ECS worker task definition JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from vector.domains.cortex.ingestion.worker_queue_roles_v1 import (  # noqa: E402
    apply_worker_role_to_task_definition_v1,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Split ECS worker Celery queue bindings")
    parser.add_argument("input", type=Path, help="Source ECS task definition JSON (worker)")
    parser.add_argument("ingestion_out", type=Path, help="Ingestion worker task def output")
    parser.add_argument("substrate_out", type=Path, help="Substrate worker task def output")
    parser.add_argument("--ingestion-family", default="", help="Optional task family override")
    parser.add_argument("--substrate-family", default="vector-substrate-worker")
    args = parser.parse_args()

    task_def = json.loads(args.input.read_text(encoding="utf-8"))
    ingestion = apply_worker_role_to_task_definition_v1(task_def, role="ingestion")
    substrate = apply_worker_role_to_task_definition_v1(task_def, role="substrate")
    if args.ingestion_family:
        ingestion["family"] = args.ingestion_family
    if args.substrate_family:
        substrate["family"] = args.substrate_family

    args.ingestion_out.write_text(json.dumps(ingestion, indent=2) + "\n", encoding="utf-8")
    args.substrate_out.write_text(json.dumps(substrate, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
