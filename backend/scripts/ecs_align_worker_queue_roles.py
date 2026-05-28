#!/usr/bin/env python3
"""Write ingestion and merged cortex ECS worker task defs (two-service model)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_ROLES_MODULE_PATH = (
    REPO_ROOT
    / "backend/src/vector/domains/cortex/ingestion/worker_queue_roles_v1.py"
)


def _load_roles_module():
    """Load queue role helpers without importing ``vector.domains.cortex.ingestion`` package."""
    spec = importlib.util.spec_from_file_location("worker_queue_roles_v1", _ROLES_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_ROLES_MODULE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="Split ECS worker Celery queue bindings (2 services)")
    parser.add_argument("input", type=Path, help="Source ECS task definition JSON (worker)")
    parser.add_argument("ingestion_out", type=Path, help="Ingestion worker task def output")
    parser.add_argument("cortex_out", type=Path, help="Cortex worker task def output (Beat + passes)")
    parser.add_argument("--ingestion-family", default="", help="Optional task family override")
    parser.add_argument("--cortex-family", default="vector-substrate-worker")
    args = parser.parse_args()

    roles = _load_roles_module()
    task_def = json.loads(args.input.read_text(encoding="utf-8"))
    ingestion = roles.apply_worker_role_to_task_definition_v1(task_def, role="ingestion")
    cortex = roles.apply_worker_role_to_task_definition_v1(task_def, role="cortex")
    if args.ingestion_family:
        ingestion["family"] = args.ingestion_family
    if args.cortex_family:
        cortex["family"] = args.cortex_family

    args.ingestion_out.write_text(json.dumps(ingestion, indent=2) + "\n", encoding="utf-8")
    args.cortex_out.write_text(json.dumps(cortex, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
